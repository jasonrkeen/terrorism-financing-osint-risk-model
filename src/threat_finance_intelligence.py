"""
Threat finance intelligence gap and collection prioritization module.

This module extends the terrorism financing OSINT model by identifying:
1. Intelligence gaps
2. Source coverage weaknesses
3. Source staleness
4. Collection priorities
5. Analyst review notes

The module does not identify terrorists, determine criminality, or make
sanctions determinations. Outputs are intended for public-source analyst review.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROCESSED_DIR = Path("data/processed")
OUTPUT_TABLES_DIR = Path("outputs/tables")

INPUT_CANDIDATES = [
    OUTPUT_TABLES_DIR / "terrorism_financing_country_risk_rankings.csv",
    OUTPUT_TABLES_DIR / "additional_risk_factor_summary.csv",
    OUTPUT_TABLES_DIR / "sanctions_exposure_supplement.csv",
    OUTPUT_TABLES_DIR / "current_data_supplement.csv",
    OUTPUT_TABLES_DIR / "conflict_data_supplement.csv",
    OUTPUT_TABLES_DIR / "current_fatf_status_comparison.csv",
    OUTPUT_TABLES_DIR / "additional_risk_factors.csv",
    OUTPUT_TABLES_DIR / "enhanced_risk_analysis.csv",
    OUTPUT_TABLES_DIR / "country_risk_scores.csv",
    OUTPUT_TABLES_DIR / "risk_scores.csv",
    PROCESSED_DIR / "processed_country_risk_data.csv",
    PROCESSED_DIR / "processed_country_data.csv",
]

SUPPLEMENT_FILES = {
    "conflict": OUTPUT_TABLES_DIR / "conflict_data_supplement.csv",
    "acled": OUTPUT_TABLES_DIR / "acled_signal_enrichment.csv",
    "organized_crime": OUTPUT_TABLES_DIR / "organized_crime_enrichment.csv",
    "gdelt": OUTPUT_TABLES_DIR / "gdelt_news_signal_enrichment.csv",
    "current_fatf": OUTPUT_TABLES_DIR / "current_fatf_status_comparison.csv",
    "sanctions": OUTPUT_TABLES_DIR / "sanctions_exposure_supplement.csv",
    "mutual_eval": OUTPUT_TABLES_DIR / "fatf_mutual_evaluation_supplement.csv",
    "regional": OUTPUT_TABLES_DIR / "regional_risk_summary.csv",
}

OUTPUT_PATH = OUTPUT_TABLES_DIR / "threat_finance_collection_priorities.csv"
SOURCE_REGISTER_PATH = OUTPUT_TABLES_DIR / "source_register.csv"


REQUIRED_COLLECTION_AREAS = [
    "sanctions",
    "conflict",
    "aml_cft",
    "organized_crime",
    "gdelt",
    "governance",
    "crypto_risk",
    "enforcement_actions",
    "terrorism_financing_reporting",
]


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def find_existing_input_file() -> Path:
    """
    Find the best available input file from the existing project outputs.
    """
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path

    raise FileNotFoundError(
        "No suitable input file found for threat finance intelligence analysis. "
        "Expected one of: "
        + ", ".join(str(path) for path in INPUT_CANDIDATES)
    )


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    """
    Read a CSV if it exists. Return None if unavailable or unreadable.
    """
    if not Path(path).exists():
        return None

    try:
        return pd.read_csv(path)
    except Exception as error:
        print(f"Could not read optional supplement {path}: {error}")
        return None


def get_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    Return the first column name that exists in the dataframe.
    """
    for col in candidates:
        if col in df.columns:
            return col
    return None


def normalize_series(series: pd.Series) -> pd.Series:
    """
    Normalize a numeric series to a 0-100 scale.
    """
    numeric = pd.to_numeric(series, errors="coerce")

    min_value = numeric.min()
    max_value = numeric.max()

    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series(50, index=series.index)

    return ((numeric - min_value) / (max_value - min_value) * 100).clip(0, 100)


def preserve_or_normalize_score(series: pd.Series) -> pd.Series:
    """
    Preserve an existing 0-100 score when it is already on that scale.

    The baseline model already produces tf_vulnerability_score on a 0-100 scale.
    This helper avoids min-max re-scaling those values into a different score.
    If a future input column is not on a 0-100 scale, the helper normalizes it.
    """
    numeric = pd.to_numeric(series, errors="coerce")

    min_value = numeric.min()
    max_value = numeric.max()

    if pd.isna(min_value) or pd.isna(max_value):
        return pd.Series(50, index=series.index)

    if min_value >= 0 and max_value <= 100:
        return numeric.fillna(50).clip(0, 100)

    return normalize_series(numeric)


def classify_risk_level(score: float) -> str:
    """
    Classify a 0-100 score into a risk/gap level.
    """
    if pd.isna(score):
        return "Unknown"
    if score >= 80:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 45:
        return "Moderate"
    return "Low"


def classify_collection_priority(score: float) -> str:
    """
    Classify a 0-100 collection priority score.
    """
    if pd.isna(score):
        return "Unknown"
    if score >= 80:
        return "Immediate Review"
    if score >= 65:
        return "High Priority"
    if score >= 45:
        return "Moderate Priority"
    return "Routine Monitoring"


def yes_no_flag(value: object) -> int:
    """
    Convert common 0/1, boolean, and text flags into 0 or 1.
    """
    if pd.isna(value):
        return 0

    text = str(value).strip().lower()

    if text in ["1", "1.0", "true", "yes", "y", "high", "active"]:
        return 1

    try:
        return 1 if int(float(text)) == 1 else 0
    except (TypeError, ValueError):
        return 0


def calculate_staleness_score(days_since_update: float) -> float:
    """
    Higher score means the source is more stale.
    """
    if pd.isna(days_since_update):
        return 100
    if days_since_update <= 30:
        return 10
    if days_since_update <= 90:
        return 30
    if days_since_update <= 180:
        return 55
    if days_since_update <= 365:
        return 75
    return 95


# ---------------------------------------------------------------------
# Data integration
# ---------------------------------------------------------------------

def standardize_keys(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add standard country and ISO3 columns for merging.
    """
    df = df.copy()

    country_col = get_first_existing_column(
        df,
        ["country", "Country", "country_name", "Country Name"],
    )
    iso_col = get_first_existing_column(
        df,
        ["iso3", "ISO3", "country_code", "Country Code"],
    )

    if country_col and "country" not in df.columns:
        df["country"] = df[country_col]
    elif not country_col and "country" not in df.columns:
        df["country"] = "Unknown"

    if iso_col and "iso3" not in df.columns:
        df["iso3"] = df[iso_col]
    elif "iso3" not in df.columns:
        df["iso3"] = ""

    df["country_merge_key"] = df["country"].astype(str).str.strip().str.lower()
    df["iso3_merge_key"] = df["iso3"].astype(str).str.strip().str.upper()

    return df


def select_merge_columns(
    supplement_df: pd.DataFrame,
    candidate_columns: list[str],
    prefix: str,
) -> pd.DataFrame:
    """
    Prepare a supplement dataframe for left-merge into the main country table.

    The function keeps merge keys plus any candidate columns that exist, then
    prefixes non-key columns to avoid name collisions where needed.
    """
    supplement_df = standardize_keys(supplement_df)

    keep_cols = ["country_merge_key", "iso3_merge_key"]
    keep_cols += [col for col in candidate_columns if col in supplement_df.columns]

    supplement_df = supplement_df[keep_cols].copy()
    supplement_df = supplement_df.drop_duplicates(
        subset=["iso3_merge_key", "country_merge_key"],
        keep="first",
    )

    rename_map = {}
    for col in supplement_df.columns:
        if col in ["country_merge_key", "iso3_merge_key"]:
            continue
        if not col.startswith(prefix):
            rename_map[col] = f"{prefix}_{col}"

    return supplement_df.rename(columns=rename_map)


def merge_supplement(
    df: pd.DataFrame,
    supplement_df: pd.DataFrame | None,
    candidate_columns: list[str],
    prefix: str,
) -> pd.DataFrame:
    """
    Merge one optional supplement into the main dataframe.

    The function first tries ISO-style keys and then fills unmatched rows by
    country-name keys. This matters for ACLED because the API export may use
    numeric ISO codes while the main model uses ISO3 alpha codes.
    """
    if supplement_df is None or supplement_df.empty:
        return df

    df = standardize_keys(df)
    prepared = select_merge_columns(supplement_df, candidate_columns, prefix)

    value_cols = [
        col
        for col in prepared.columns
        if col not in ["country_merge_key", "iso3_merge_key"]
    ]

    if not value_cols:
        return df

    merged = df.merge(
        prepared.drop(columns=["country_merge_key"], errors="ignore"),
        on="iso3_merge_key",
        how="left",
    )

    country_merged = df[["country_merge_key"]].merge(
        prepared.drop(columns=["iso3_merge_key"], errors="ignore"),
        on="country_merge_key",
        how="left",
    )

    for col in value_cols:
        if col not in merged.columns and col in country_merged.columns:
            merged[col] = country_merged[col]
        elif col in merged.columns and col in country_merged.columns:
            merged[col] = merged[col].combine_first(country_merged[col])

    return merged

def load_and_merge_supplements(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add supplemental columns from existing project outputs.

    This makes live_signal_score and intelligence_gap_score more meaningful
    without requiring new APIs yet.
    """
    df = standardize_keys(df)

    conflict_df = read_csv_if_exists(SUPPLEMENT_FILES["conflict"])
    acled_df = read_csv_if_exists(SUPPLEMENT_FILES["acled"])
    organized_crime_df = read_csv_if_exists(SUPPLEMENT_FILES["organized_crime"])
    gdelt_df = read_csv_if_exists(SUPPLEMENT_FILES["gdelt"])
    current_fatf_df = read_csv_if_exists(SUPPLEMENT_FILES["current_fatf"])
    sanctions_df = read_csv_if_exists(SUPPLEMENT_FILES["sanctions"])
    mutual_eval_df = read_csv_if_exists(SUPPLEMENT_FILES["mutual_eval"])

    df = merge_supplement(
        df,
        conflict_df,
        [
            "ucdp_match_found",
            "ucdp_year",
            "organized_violence_active",
            "conflict_deaths_total",
            "conflict_dyad_count",
            "conflict_event_count",
            "conflict_intensity_category",
        ],
        "conflict",
    )

    df = merge_supplement(
        df,
        acled_df,
        [
            "acled_event_count",
            "acled_fatalities",
            "acled_fatal_event_count",
            "acled_political_violence_events",
            "acled_unrest_events",
            "acled_strategic_development_events",
            "acled_latest_event_date",
            "acled_event_count_score",
            "acled_fatality_score",
            "acled_fatal_event_score",
            "acled_political_violence_score",
            "acled_unrest_score",
            "acled_strategic_development_score",
            "acled_conflict_signal_score",
            "acled_signal_level",
            "acled_source_present",
            "acled_confidence",
        ],
        "acled",
    )

    df = merge_supplement(
        df,
        organized_crime_df,
        [
            "oc_index_year",
            "criminality_score",
            "criminal_markets_score",
            "criminal_actors_score",
            "resilience_score",
            "organized_crime_exposure_score",
            "organized_crime_resilience_gap_score",
            "organized_crime_score",
            "organized_crime_level",
            "organized_crime_source_present",
            "organized_crime_confidence",
            "organized_crime_days_since_update",
        ],
        "organized_crime",
    )

    df = merge_supplement(
        df,
        gdelt_df,
        [
            "gdelt_batch_file_count",
            "gdelt_matching_record_count",
            "gdelt_matching_source_count",
            "gdelt_average_tone",
            "gdelt_record_count_score",
            "gdelt_source_diversity_score",
            "gdelt_negative_tone_score",
            "gdelt_news_signal_score",
            "gdelt_news_signal_level",
            "gdelt_source_present",
            "gdelt_confidence",
            "gdelt_days_since_update",
            "gdelt_latest_file_timestamp",
            "gdelt_latest_file_datetime",
            "gdelt_query_status",
            "gdelt_article_count",
        ],
        "gdelt",
    )

    df = merge_supplement(
        df,
        current_fatf_df,
        [
            "current_fatf_increased_monitoring",
            "fatf_status_changed",
            "model_signal_matches_current_fatf",
            "predicted_grey_list_probability",
            "tf_vulnerability_score",
        ],
        "current_fatf",
    )

    df = merge_supplement(
        df,
        sanctions_df,
        [
            "sanctions_exposure_score",
            "sanctions_count",
            "terrorism_related_sanctions_count",
            "sanctions_source_present",
        ],
        "sanctions",
    )

    df = merge_supplement(
        df,
        mutual_eval_df,
        [
            "fatf_mutual_eval_score",
            "technical_compliance_score",
            "effectiveness_score",
            "mutual_eval_source_present",
        ],
        "mutual_eval",
    )

    return df


# ---------------------------------------------------------------------
# Baseline risk and signal scoring
# ---------------------------------------------------------------------

def add_baseline_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create standardized baseline risk columns from the existing project outputs.
    """
    df = standardize_keys(df)

    risk_col = get_first_existing_column(
        df,
        [
            "tf_vulnerability_score",
            "tf_risk_score",
            "terrorism_financing_risk_score",
            "terrorism_financing_vulnerability_score",
            "vulnerability_score",
            "risk_score",
            "overall_risk_score",
            "final_risk_score",
            "composite_risk_score",
            "country_risk_score",
        ],
    )

    level_col = get_first_existing_column(
        df,
        [
            "tf_risk_level",
            "terrorism_financing_risk_level",
            "terrorism_financing_vulnerability_level",
            "risk_level",
            "vulnerability_level",
            "overall_risk_level",
            "risk_category",
        ],
    )

    if risk_col:
        df["baseline_tf_risk_score"] = preserve_or_normalize_score(df[risk_col])
    else:
        df["baseline_tf_risk_score"] = 50

    if level_col:
        df["baseline_tf_risk_level"] = df[level_col].astype(str)
    else:
        df["baseline_tf_risk_level"] = df["baseline_tf_risk_score"].apply(
            classify_risk_level
        )

    return df


def get_numeric_column(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    """
    Return the first matching numeric column as a Series.
    """
    for col in candidates:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
    return None


def add_live_signal_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a more dynamic live/recent signal score from existing supplement outputs.

    Version 2 derives signal from:
    - Current FATF increased-monitoring status
    - FATF status changes
    - Predicted FATF grey-list probability
    - Conflict exposure / deaths / active organized violence
    - ACLED recent conflict and unrest signal
    - Global Organized Crime Index context
    - GDELT 2.0 batch public-news signal
    - Sanctions template values when populated

    This is still a public-source review signal, not a terrorism determination.
    """
    df = df.copy()

    signal_components = []

    # Current FATF monitoring is a strong public AML/CFT signal.
    fatf_col = get_first_existing_column(
        df,
        [
            "current_fatf_current_fatf_increased_monitoring",
            "current_fatf_increased_monitoring",
            "fatf_grey_list",
        ],
    )

    if fatf_col:
        fatf_signal = df[fatf_col].apply(yes_no_flag).map({1: 85, 0: 35})
        signal_components.append(fatf_signal.rename("fatf_monitoring_signal"))

    # FATF status changes are useful review triggers even when not high risk.
    changed_col = get_first_existing_column(
        df,
        [
            "current_fatf_fatf_status_changed",
            "fatf_status_changed",
        ],
    )

    if changed_col:
        changed_signal = df[changed_col].apply(yes_no_flag).map({1: 75, 0: 35})
        signal_components.append(changed_signal.rename("fatf_change_signal"))

    # Predicted probability provides model-derived signal.
    prob_col = get_first_existing_column(
        df,
        [
            "predicted_grey_list_probability",
            "current_fatf_predicted_grey_list_probability",
        ],
    )

    if prob_col:
        probability_signal = (
            pd.to_numeric(df[prob_col], errors="coerce").fillna(0.5) * 100
        ).clip(0, 100)
        signal_components.append(probability_signal.rename("model_probability_signal"))

    # Conflict signal from deaths and active violence.
    deaths = get_numeric_column(
        df,
        [
            "conflict_conflict_deaths_total",
            "conflict_deaths_total",
        ],
    )

    if deaths is not None:
        # Log transform keeps Ukraine-style outliers from dominating.
        conflict_death_signal = normalize_series(np.log1p(deaths.fillna(0)))
        signal_components.append(conflict_death_signal.rename("conflict_death_signal"))

    active_col = get_first_existing_column(
        df,
        [
            "conflict_organized_violence_active",
            "organized_violence_active",
        ],
    )

    if active_col:
        active_signal = df[active_col].apply(yes_no_flag).map({1: 70, 0: 30})
        signal_components.append(active_signal.rename("active_conflict_signal"))

    # ACLED recent event signal provides a near-real-time conflict/unrest layer.
    acled_signal_col = get_first_existing_column(
        df,
        [
            "acled_acled_conflict_signal_score",
            "acled_conflict_signal_score",
        ],
    )

    if acled_signal_col:
        acled_signal = pd.to_numeric(
            df[acled_signal_col],
            errors="coerce",
        ).fillna(0).clip(0, 100)
        signal_components.append(acled_signal.rename("acled_recent_signal"))

    # Organized-crime exposure is a supplemental convergence signal.
    organized_crime_signal_col = get_first_existing_column(
        df,
        [
            "organized_crime_organized_crime_score",
            "organized_crime_score",
            "organized_crime_organized_crime_exposure_score",
            "organized_crime_exposure_score",
        ],
    )

    if organized_crime_signal_col:
        organized_crime_signal = pd.to_numeric(
            df[organized_crime_signal_col],
            errors="coerce",
        ).fillna(0).clip(0, 100)
        signal_components.append(
            organized_crime_signal.rename("organized_crime_signal")
        )

    # GDELT 2.0 batch public-news signal provides media-reporting context.
    gdelt_signal_col = get_first_existing_column(
        df,
        [
            "gdelt_gdelt_news_signal_score",
            "gdelt_news_signal_score",
            "gdelt_gdelt_record_count_score",
            "gdelt_record_count_score",
        ],
    )

    if gdelt_signal_col:
        gdelt_signal = pd.to_numeric(
            df[gdelt_signal_col],
            errors="coerce",
        ).fillna(0).clip(0, 100)
        signal_components.append(gdelt_signal.rename("gdelt_public_news_signal"))

    # Sanctions signal only contributes if the supplement has populated values.
    sanctions_signal_col = get_first_existing_column(
        df,
        [
            "sanctions_sanctions_exposure_score",
            "sanctions_exposure_score",
            "sanctions_terrorism_related_sanctions_count",
            "terrorism_related_sanctions_count",
            "sanctions_sanctions_count",
            "sanctions_count",
        ],
    )

    if sanctions_signal_col:
        sanctions_signal = normalize_series(df[sanctions_signal_col])
        signal_components.append(sanctions_signal.rename("sanctions_signal"))

    if signal_components:
        component_df = pd.concat(signal_components, axis=1)
        df["live_signal_score"] = component_df.mean(axis=1).round(2)
        df["live_signal_driver_count"] = component_df.notna().sum(axis=1)
    else:
        df["live_signal_score"] = 50
        df["live_signal_driver_count"] = 0

    return df


# ---------------------------------------------------------------------
# Collection source coverage and intelligence gaps
# ---------------------------------------------------------------------

def has_populated_source_value(row: pd.Series, candidates: list[str]) -> int:
    """
    Return 1 if any candidate column exists and has a non-zero/non-empty value.
    """
    for col in candidates:
        if col not in row:
            continue

        value = row.get(col)

        if pd.isna(value):
            continue

        text = str(value).strip().lower()

        if text in ["", "0", "0.0", "none", "nan", "false", "no", "n/a"]:
            continue

        return 1

    return 0


def add_collection_source_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add source coverage, staleness, and confidence fields.

    Version 2 makes coverage more realistic:
    - Governance is present because it is a core model input.
    - AML/CFT is present if FATF/status columns exist.
    - Conflict is present if UCDP/conflict supplement matched the country.
    - Sanctions is present only if a sanctions supplement has populated values.
    - GDELT is present when the batch enrichment finds matched public-news signals.
    - Crypto, enforcement, and terrorism-financing reporting stay as source gaps
      until dedicated public-source modules are added.
    """
    df = df.copy()

    # Governance source coverage is a core input.
    df["governance_source_present"] = 1
    df["governance_days_since_update"] = 365
    df["governance_confidence"] = "High"

    # AML/CFT source coverage from FATF target/current FATF supplement.
    fatf_cols = [
        "fatf_grey_list",
        "current_fatf_current_fatf_increased_monitoring",
        "current_fatf_fatf_status_changed",
        "current_fatf_model_signal_matches_current_fatf",
        "current_fatf_increased_monitoring",
        "fatf_status_changed",
    ]

    df["aml_cft_source_present"] = df.apply(
        lambda row: 1 if any(col in row.index and not pd.isna(row.get(col)) for col in fatf_cols) else 0,
        axis=1,
    )
    df["aml_cft_days_since_update"] = 90
    df["aml_cft_confidence"] = np.where(
        df["aml_cft_source_present"] == 1,
        "High",
        "Unknown",
    )

    # Conflict source coverage from UCDP/conflict supplement and ACLED.
    conflict_match_col = get_first_existing_column(
        df,
        ["conflict_ucdp_match_found", "ucdp_match_found"],
    )
    conflict_year_col = get_first_existing_column(
        df,
        ["conflict_ucdp_year", "ucdp_year"],
    )
    conflict_deaths_col = get_first_existing_column(
        df,
        ["conflict_conflict_deaths_total", "conflict_deaths_total"],
    )
    acled_signal_col = get_first_existing_column(
        df,
        ["acled_acled_conflict_signal_score", "acled_conflict_signal_score"],
    )
    acled_event_col = get_first_existing_column(
        df,
        ["acled_acled_event_count", "acled_event_count"],
    )

    ucdp_present = pd.Series(0, index=df.index)
    if conflict_match_col:
        ucdp_present = df[conflict_match_col].apply(yes_no_flag)
    elif conflict_year_col:
        ucdp_present = pd.to_numeric(
            df[conflict_year_col],
            errors="coerce",
        ).notna().astype(int)
    elif conflict_deaths_col:
        ucdp_present = pd.to_numeric(
            df[conflict_deaths_col],
            errors="coerce",
        ).notna().astype(int)

    acled_present = pd.Series(0, index=df.index)
    if acled_signal_col:
        acled_present = pd.to_numeric(
            df[acled_signal_col],
            errors="coerce",
        ).notna().astype(int)
    elif acled_event_col:
        acled_present = (
            pd.to_numeric(df[acled_event_col], errors="coerce").fillna(0) > 0
        ).astype(int)

    df["conflict_source_present"] = np.where(
        (ucdp_present == 1) | (acled_present == 1),
        1,
        0,
    )

    df["conflict_days_since_update"] = np.where(
        acled_present == 1,
        30,
        np.where(ucdp_present == 1, 365, np.nan),
    )

    df["conflict_confidence"] = np.where(
        (ucdp_present == 1) & (acled_present == 1),
        "High",
        np.where(df["conflict_source_present"] == 1, "Moderate", "Unknown"),
    )

    # Sanctions source coverage only if the supplement is populated.
    sanctions_cols = [
        "sanctions_sanctions_exposure_score",
        "sanctions_exposure_score",
        "sanctions_terrorism_related_sanctions_count",
        "terrorism_related_sanctions_count",
        "sanctions_sanctions_count",
        "sanctions_count",
        "sanctions_sanctions_source_present",
    ]

    df["sanctions_source_present"] = df.apply(
        lambda row: has_populated_source_value(row, sanctions_cols),
        axis=1,
    )
    df["sanctions_days_since_update"] = np.where(
        df["sanctions_source_present"] == 1,
        90,
        np.nan,
    )
    df["sanctions_confidence"] = np.where(
        df["sanctions_source_present"] == 1,
        "Moderate",
        "Unknown",
    )

    # FATF mutual evaluation source coverage if populated.
    mutual_eval_cols = [
        "mutual_eval_fatf_mutual_eval_score",
        "fatf_mutual_eval_score",
        "mutual_eval_technical_compliance_score",
        "technical_compliance_score",
        "mutual_eval_effectiveness_score",
        "effectiveness_score",
    ]
    mutual_eval_present = df.apply(
        lambda row: has_populated_source_value(row, mutual_eval_cols),
        axis=1,
    )

    # Organized-crime source remains a planned enrichment unless populated.
    organized_crime_cols = [
        "organized_crime_organized_crime_source_present",
        "organized_crime_source_present",
        "organized_crime_organized_crime_score",
        "organized_crime_score",
        "organized_crime_organized_crime_exposure_score",
        "organized_crime_exposure_score",
        "organized_crime_criminality_score",
        "criminality_score",
        "organized_crime_resilience_score",
        "resilience_score",
    ]

    existing_organized_crime_flag = get_first_existing_column(
        df,
        [
            "organized_crime_organized_crime_source_present",
            "organized_crime_source_present",
        ],
    )

    if existing_organized_crime_flag:
        df["organized_crime_source_present"] = df[
            existing_organized_crime_flag
        ].apply(yes_no_flag)
    else:
        df["organized_crime_source_present"] = df.apply(
            lambda row: has_populated_source_value(row, organized_crime_cols),
            axis=1,
        )

    organized_crime_days_col = get_first_existing_column(
        df,
        [
            "organized_crime_organized_crime_days_since_update",
            "organized_crime_days_since_update",
        ],
    )

    if organized_crime_days_col:
        df["organized_crime_days_since_update"] = pd.to_numeric(
            df[organized_crime_days_col],
            errors="coerce",
        )
    else:
        df["organized_crime_days_since_update"] = np.where(
            df["organized_crime_source_present"] == 1,
            365,
            np.nan,
        )

    organized_crime_confidence_col = get_first_existing_column(
        df,
        [
            "organized_crime_organized_crime_confidence",
            "organized_crime_confidence",
        ],
    )

    if organized_crime_confidence_col:
        df["organized_crime_confidence"] = df[
            organized_crime_confidence_col
        ].fillna("Unknown")
    else:
        df["organized_crime_confidence"] = np.where(
            df["organized_crime_source_present"] == 1,
            "Moderate to High",
            "Unknown",
        )

    # GDELT 2.0 batch public-news source coverage.
    gdelt_present_col = get_first_existing_column(
        df,
        [
            "gdelt_gdelt_source_present",
            "gdelt_source_present",
        ],
    )
    gdelt_score_col = get_first_existing_column(
        df,
        [
            "gdelt_gdelt_news_signal_score",
            "gdelt_news_signal_score",
            "gdelt_gdelt_matching_record_count",
            "gdelt_matching_record_count",
        ],
    )

    if gdelt_present_col:
        df["gdelt_source_present"] = df[gdelt_present_col].apply(yes_no_flag)
    elif gdelt_score_col:
        gdelt_values = pd.to_numeric(df[gdelt_score_col], errors="coerce").fillna(0)
        df["gdelt_source_present"] = (gdelt_values > 0).astype(int)
    else:
        df["gdelt_source_present"] = 0

    gdelt_days_col = get_first_existing_column(
        df,
        [
            "gdelt_gdelt_days_since_update",
            "gdelt_days_since_update",
        ],
    )

    if gdelt_days_col:
        df["gdelt_days_since_update"] = pd.to_numeric(
            df[gdelt_days_col],
            errors="coerce",
        )
    else:
        df["gdelt_days_since_update"] = np.where(
            df["gdelt_source_present"] == 1,
            1,
            np.nan,
        )

    gdelt_confidence_col = get_first_existing_column(
        df,
        [
            "gdelt_gdelt_confidence",
            "gdelt_confidence",
        ],
    )

    if gdelt_confidence_col:
        df["gdelt_confidence"] = df[gdelt_confidence_col].fillna("Unknown")
    else:
        df["gdelt_confidence"] = np.where(
            df["gdelt_source_present"] == 1,
            "Moderate",
            "Unknown",
        )

    # Treat populated mutual-evaluation data as a higher-confidence AML/CFT subsource.
    df["fatf_mutual_evaluation_source_present"] = mutual_eval_present

    # Planned future source categories.
    planned_sources = [
        "crypto_risk",
        "enforcement_actions",
        "terrorism_financing_reporting",
    ]

    for area in planned_sources:
        present_col = f"{area}_source_present"
        days_col = f"{area}_days_since_update"
        confidence_col = f"{area}_confidence"

        if present_col not in df.columns:
            df[present_col] = 0
        if days_col not in df.columns:
            df[days_col] = np.nan
        if confidence_col not in df.columns:
            df[confidence_col] = "Unknown"

    # Fill any accidental omissions for required collection areas.
    for area in REQUIRED_COLLECTION_AREAS:
        present_col = f"{area}_source_present"
        days_col = f"{area}_days_since_update"
        confidence_col = f"{area}_confidence"

        if present_col not in df.columns:
            df[present_col] = 0
        if days_col not in df.columns:
            df[days_col] = np.nan
        if confidence_col not in df.columns:
            df[confidence_col] = "Unknown"

    return df


def calculate_intelligence_gap_score(row: pd.Series) -> float:
    """
    Calculate a score for missing, stale, or weak intelligence coverage.
    """
    missing_source_count = 0
    stale_source_scores = []
    weak_confidence_count = 0

    for area in REQUIRED_COLLECTION_AREAS:
        present_col = f"{area}_source_present"
        days_col = f"{area}_days_since_update"
        confidence_col = f"{area}_confidence"

        present = yes_no_flag(row.get(present_col, 0))

        if present == 0:
            missing_source_count += 1
            stale_source_scores.append(100)
        else:
            stale_source_scores.append(
                calculate_staleness_score(row.get(days_col, np.nan))
            )

        confidence = row.get(confidence_col, "Unknown")
        if pd.isna(confidence) or str(confidence).strip().lower() in [
            "low",
            "unknown",
            "none",
            "",
        ]:
            weak_confidence_count += 1

    missing_score = (missing_source_count / len(REQUIRED_COLLECTION_AREAS)) * 100
    stale_score = float(np.nanmean(stale_source_scores))
    confidence_gap_score = (weak_confidence_count / len(REQUIRED_COLLECTION_AREAS)) * 100

    score = (
        0.45 * missing_score
        + 0.35 * stale_score
        + 0.20 * confidence_gap_score
    )

    return round(float(score), 2)


def add_intelligence_gap_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add intelligence gap score, gap level, and source staleness score.
    """
    df = df.copy()

    df["intelligence_gap_score"] = df.apply(
        calculate_intelligence_gap_score,
        axis=1,
    )

    df["intelligence_gap_level"] = df["intelligence_gap_score"].apply(
        classify_risk_level
    )

    staleness_cols = [
        f"{area}_days_since_update"
        for area in REQUIRED_COLLECTION_AREAS
        if f"{area}_days_since_update" in df.columns
    ]

    if staleness_cols:
        df["source_staleness_score"] = df.apply(
            lambda row: np.nanmean(
                [
                    calculate_staleness_score(row[col])
                    if yes_no_flag(row.get(col.replace("_days_since_update", "_source_present"), 0)) == 1
                    else 100
                    for col in staleness_cols
                ]
            ),
            axis=1,
        )
    else:
        df["source_staleness_score"] = 100

    source_present_cols = [
        f"{area}_source_present"
        for area in REQUIRED_COLLECTION_AREAS
        if f"{area}_source_present" in df.columns
    ]

    if source_present_cols:
        source_present_flags = df[source_present_cols].apply(
            lambda col: col.map(yes_no_flag)
        )
        df["source_coverage_score"] = (
            source_present_flags.mean(axis=1) * 100
        ).round(2)
    else:
        df["source_coverage_score"] = 0

    return df


def recommend_collection_focus(row: pd.Series) -> str:
    """
    Recommend the next collection focus based on missing/stale areas and signals.
    """
    gaps = []

    if yes_no_flag(row.get("sanctions_source_present", 0)) == 0:
        gaps.append("sanctions exposure")
    if yes_no_flag(row.get("conflict_source_present", 0)) == 0:
        gaps.append("conflict activity")
    if yes_no_flag(row.get("crypto_risk_source_present", 0)) == 0:
        gaps.append("crypto or virtual-asset risk")
    if yes_no_flag(row.get("enforcement_actions_source_present", 0)) == 0:
        gaps.append("terrorism-financing enforcement actions")
    if yes_no_flag(row.get("aml_cft_source_present", 0)) == 0:
        gaps.append("AML/CFT effectiveness")
    if yes_no_flag(row.get("organized_crime_source_present", 0)) == 0:
        gaps.append("organized crime exposure")
    if yes_no_flag(row.get("gdelt_source_present", 0)) == 0:
        gaps.append("GDELT/public-news reporting")
    if yes_no_flag(row.get("terrorism_financing_reporting_source_present", 0)) == 0:
        gaps.append("recent terrorism-financing reporting")

    if row.get("live_signal_score", 50) >= 65 and gaps:
        return (
            "Validate recent live signals and collect or refresh: "
            + ", ".join(gaps[:3])
            + "."
        )

    if row.get("baseline_tf_risk_score", 0) >= 65 and gaps:
        return (
            "High baseline risk; collect or validate: "
            + ", ".join(gaps[:3])
            + "."
        )

    if gaps:
        return "Collect or validate: " + ", ".join(gaps[:3]) + "."

    if row.get("intelligence_gap_score", 0) >= 65:
        return (
            "Refresh recent sanctions, conflict, GDELT/public-news, enforcement, "
            "and terrorism-financing reporting."
        )

    if row.get("live_signal_score", 50) >= 65:
        return (
            "Validate recent live signals against sanctions, conflict, GDELT/public-news, "
            "and enforcement sources."
        )

    return "Continue routine monitoring and refresh high-priority public sources."


def add_collection_priority(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate collection priority score and recommended collection focus.
    """
    df = df.copy()

    df["decision_relevance_score"] = df["baseline_tf_risk_score"]

    df["collection_priority_score"] = (
        0.35 * df["baseline_tf_risk_score"]
        + 0.25 * df["intelligence_gap_score"]
        + 0.20 * df["live_signal_score"]
        + 0.10 * df["source_staleness_score"]
        + 0.10 * df["decision_relevance_score"]
    ).round(2)

    df["collection_priority_level"] = df["collection_priority_score"].apply(
        classify_collection_priority
    )

    df["recommended_collection_focus"] = df.apply(
        recommend_collection_focus,
        axis=1,
    )

    return df


def generate_analyst_note(row: pd.Series) -> str:
    """
    Generate a human-readable analyst review note.
    """
    country = row.get("country", "Unknown country")
    risk_score = row.get("baseline_tf_risk_score", "Unknown")
    risk_level = row.get("baseline_tf_risk_level", "Unknown")
    gap_level = row.get("intelligence_gap_level", "Unknown")
    priority = row.get("collection_priority_level", "Unknown")
    live_signal = row.get("live_signal_score", "Unknown")
    coverage = row.get("source_coverage_score", "Unknown")

    focus = row.get(
        "recommended_collection_focus",
        "Review available public-source terrorism-financing indicators.",
    )

    return (
        f"{country} has a baseline terrorism-financing risk assessment of "
        f"{risk_level} with a score of {risk_score}. "
        f"The live/recent signal score is {live_signal}, and source coverage is "
        f"{coverage}. The intelligence gap level is {gap_level}, resulting in a "
        f"collection priority of {priority}. Recommended next step: {focus} "
        "This output is intended for analyst review and does not constitute "
        "a determination of terrorism, criminality, sanctions exposure, "
        "or illicit activity."
    )


def add_analyst_notes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add analyst notes to the dataframe.
    """
    df = df.copy()
    df["analyst_note"] = df.apply(generate_analyst_note, axis=1)
    return df


# ---------------------------------------------------------------------
# Source register and outputs
# ---------------------------------------------------------------------

def build_source_register() -> pd.DataFrame:
    """
    Build a source register for methodology transparency.
    """
    sources = [
        {
            "source_name": "FATF High-Risk and Other Monitored Jurisdictions",
            "source_type": "AML/CFT monitoring",
            "coverage": "Country-level",
            "use_in_model": "AML/CFT strategic deficiency indicator and current monitoring signal",
            "confidence_level": "High",
            "limitations": "List status does not represent all terrorism-financing risk.",
        },
        {
            "source_name": "OFAC Sanctions Lists",
            "source_type": "Sanctions",
            "coverage": "Entity, individual, vessel, aircraft, and country-related sanctions",
            "use_in_model": "Sanctions exposure and terrorism-related designation signal",
            "confidence_level": "High",
            "limitations": "Sanctions data identifies designated parties, not broader unlisted risk.",
        },
        {
            "source_name": "OpenSanctions",
            "source_type": "Aggregated sanctions and watchlist data",
            "coverage": "Global",
            "use_in_model": "Sanctions enrichment and entity-list context",
            "confidence_level": "Moderate to High",
            "limitations": "Dependent on source coverage and update timing.",
        },
        {
            "source_name": "World Bank Worldwide Governance Indicators",
            "source_type": "Governance indicators",
            "coverage": "Country-level",
            "use_in_model": (
                "Rule of law, control of corruption, government effectiveness, "
                "and stability indicators"
            ),
            "confidence_level": "High",
            "limitations": "Annual data may lag current conditions.",
        },
        {
            "source_name": "Global Organized Crime Index",
            "source_type": "Organized crime exposure",
            "coverage": "Country-level",
            "use_in_model": (
                "Supplemental organized-crime convergence and illicit-market "
                "vulnerability layer for source coverage, live-signal context, "
                "and collection-priority scoring."
            ),
            "confidence_level": "Moderate to High",
            "limitations": (
                "Index-based methodology may not capture fast-moving changes, "
                "subnational variation, or case-level organized-crime activity. "
                "The score is contextual and is not evidence of terrorism financing "
                "or criminal activity."
            ),
        },
        {
            "source_name": "GDELT 2.0 Global Knowledge Graph Batch Files",
            "source_type": "Open-source public-news signal",
            "coverage": "Global public reporting",
            "use_in_model": (
                "Supplemental GDELT 2.0 batch public-news signal layer for "
                "live-signal context, source coverage, intelligence-gap scoring, "
                "and collection-priority scoring."
            ),
            "confidence_level": "Moderate",
            "limitations": (
                "Public reporting may include media bias, duplication, translation "
                "artifacts, false positives, and uneven country coverage. The signal "
                "is contextual and is not evidence of terrorism financing, criminality, "
                "sanctions exposure, or illicit activity."
            ),
        },
        {
            "source_name": "Treasury / DOJ / FinCEN Enforcement Releases",
            "source_type": "Public enforcement reporting",
            "coverage": "Case-level public releases",
            "use_in_model": "Planned terrorism-financing enforcement and typology signal",
            "confidence_level": "High",
            "limitations": "Public releases are event-driven and do not represent all activity.",
        },
        {
            "source_name": "ACLED / UCDP Conflict Event Data",
            "source_type": "Conflict and instability indicators",
            "coverage": "Country and event-level",
            "use_in_model": (
                "UCDP provides structured annual conflict exposure context; "
                "ACLED provides recent conflict, unrest, and political-violence "
                "signals for the live-signal and collection-priority layer."
            ),
            "confidence_level": "Moderate to High",
            "limitations": (
                "Coverage, coding, reporting density, and licensing constraints "
                "vary by country. These signals are used as early-warning context, "
                "not evidence of terrorism-financing activity."
            ),
        },
    ]

    return pd.DataFrame(sources)


def save_outputs(df: pd.DataFrame) -> None:
    """
    Save collection priority outputs and source register.
    """
    OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    output_columns = [
        "country",
        "iso3",
        "baseline_tf_risk_score",
        "baseline_tf_risk_level",
        "live_signal_score",
        "live_signal_driver_count",
        "source_coverage_score",
        "acled_acled_conflict_signal_score",
        "acled_acled_signal_level",
        "acled_acled_event_count",
        "acled_acled_fatalities",
        "organized_crime_organized_crime_score",
        "organized_crime_criminality_score",
        "organized_crime_resilience_score",
        "organized_crime_organized_crime_level",
        "gdelt_gdelt_news_signal_score",
        "gdelt_gdelt_news_signal_level",
        "gdelt_gdelt_matching_record_count",
        "gdelt_gdelt_matching_source_count",
        "gdelt_gdelt_average_tone",
        "gdelt_gdelt_batch_file_count",
        "source_staleness_score",
        "intelligence_gap_score",
        "intelligence_gap_level",
        "collection_priority_score",
        "collection_priority_level",
        "recommended_collection_focus",
        "analyst_note",
    ]

    available_columns = [col for col in output_columns if col in df.columns]

    output_df = df[available_columns].sort_values(
        "collection_priority_score",
        ascending=False,
    )

    output_df.to_csv(OUTPUT_PATH, index=False)

    source_register = build_source_register()
    source_register.to_csv(SOURCE_REGISTER_PATH, index=False)


def main() -> None:
    """
    Run the threat finance intelligence gap and collection priority analysis.
    """
    print("Running threat finance intelligence gap analysis...")

    input_path = find_existing_input_file()
    print(f"Using input file: {input_path}")

    df = pd.read_csv(input_path)

    df = add_baseline_columns(df)
    df = load_and_merge_supplements(df)
    df = add_live_signal_score(df)
    df = add_collection_source_flags(df)
    df = add_intelligence_gap_scores(df)
    df = add_collection_priority(df)
    df = add_analyst_notes(df)

    save_outputs(df)

    print(f"Threat finance collection priorities saved to: {OUTPUT_PATH}")
    print(f"Source register saved to: {SOURCE_REGISTER_PATH}")


if __name__ == "__main__":
    main()
