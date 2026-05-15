"""
Additional risk factor module for the terrorism financing OSINT risk model.

This module adds four project-expansion layers:
1. World Bank regional risk groupings
2. Sanctions exposure input template and optional supplement
3. FATF mutual evaluation input template and optional supplement
4. Current FATF status comparison visualization

The sanctions and FATF mutual-evaluation layers are designed as manual-data
supplements because the most useful public sources are not always available as
stable, direct-download country-year CSV files. If the input templates are left
blank, the module still creates them and continues the pipeline.

These supplemental factors do not replace the main terrorism-financing
vulnerability score. They provide additional context for future model versions.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
import requests

from src import config


# ---------------------------------------------------
# Config helpers with safe fallbacks
# ---------------------------------------------------

TABLES_DIR = config.TABLES_DIR
CHARTS_DIR = config.CHARTS_DIR
RAW_DATA_DIR = config.RAW_DATA_DIR

RISK_RANKINGS_FILE = config.RISK_RANKINGS_FILE
CURRENT_FATF_STATUS_COMPARISON_FILE = config.CURRENT_FATF_STATUS_COMPARISON_FILE

CONFLICT_DATA_SUPPLEMENT_FILE = getattr(
    config,
    "CONFLICT_DATA_SUPPLEMENT_FILE",
    TABLES_DIR / "conflict_data_supplement.csv",
)

WORLD_BANK_COUNTRY_METADATA_URL = getattr(
    config,
    "WORLD_BANK_COUNTRY_METADATA_URL",
    "https://api.worldbank.org/v2/country?format=json&per_page=400",
)

COUNTRY_REGION_MAPPING_FILE = getattr(
    config,
    "COUNTRY_REGION_MAPPING_FILE",
    TABLES_DIR / "country_region_mapping.csv",
)

REGIONAL_RISK_SUMMARY_FILE = getattr(
    config,
    "REGIONAL_RISK_SUMMARY_FILE",
    TABLES_DIR / "regional_risk_summary.csv",
)

SANCTIONS_EXPOSURE_TEMPLATE_FILE = getattr(
    config,
    "SANCTIONS_EXPOSURE_TEMPLATE_FILE",
    RAW_DATA_DIR / "sanctions_exposure_input_template.csv",
)

SANCTIONS_EXPOSURE_SUPPLEMENT_FILE = getattr(
    config,
    "SANCTIONS_EXPOSURE_SUPPLEMENT_FILE",
    TABLES_DIR / "sanctions_exposure_supplement.csv",
)

FATF_MUTUAL_EVALUATION_TEMPLATE_FILE = getattr(
    config,
    "FATF_MUTUAL_EVALUATION_TEMPLATE_FILE",
    RAW_DATA_DIR / "fatf_mutual_evaluation_input_template.csv",
)

FATF_MUTUAL_EVALUATION_SUPPLEMENT_FILE = getattr(
    config,
    "FATF_MUTUAL_EVALUATION_SUPPLEMENT_FILE",
    TABLES_DIR / "fatf_mutual_evaluation_supplement.csv",
)

ADDITIONAL_RISK_FACTOR_SUMMARY_FILE = getattr(
    config,
    "ADDITIONAL_RISK_FACTOR_SUMMARY_FILE",
    TABLES_DIR / "additional_risk_factor_summary.csv",
)

REGIONAL_AVERAGE_RISK_CHART_FILE = getattr(
    config,
    "REGIONAL_AVERAGE_RISK_CHART_FILE",
    CHARTS_DIR / "regional_average_risk_score.png",
)

REGIONAL_FATF_COUNT_CHART_FILE = getattr(
    config,
    "REGIONAL_FATF_COUNT_CHART_FILE",
    CHARTS_DIR / "regional_fatf_count.png",
)

CURRENT_FATF_STATUS_COMPARISON_CHART_FILE = getattr(
    config,
    "CURRENT_FATF_STATUS_COMPARISON_CHART_FILE",
    CHARTS_DIR / "current_fatf_status_comparison.png",
)


# ---------------------------------------------------
# Loading helpers
# ---------------------------------------------------

def ensure_output_dirs() -> None:
    """
    Create required output directories.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_rankings() -> pd.DataFrame:
    """
    Load final risk rankings.
    """

    if not RISK_RANKINGS_FILE.exists():
        raise FileNotFoundError(
            f"Risk rankings file not found: {RISK_RANKINGS_FILE}. "
            "Run risk_scoring.py and modeling.py first."
        )

    df = pd.read_csv(RISK_RANKINGS_FILE)

    required_columns = [
        "risk_rank",
        "country",
        "country_code",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required columns: "
            f"{missing_columns}"
        )

    print("Risk rankings loaded.")
    print(f"Shape: {df.shape}")

    return df


# ---------------------------------------------------
# World Bank regional metadata
# ---------------------------------------------------

def fetch_world_bank_country_metadata() -> pd.DataFrame:
    """
    Download World Bank country metadata and create a country-region mapping.
    """

    print("Fetching World Bank country metadata for regional groupings...")
    print(WORLD_BANK_COUNTRY_METADATA_URL)

    try:
        response = requests.get(WORLD_BANK_COUNTRY_METADATA_URL, timeout=30)
        response.raise_for_status()
        json_data = response.json()
    except requests.exceptions.RequestException as error:
        raise RuntimeError("World Bank country metadata request failed.") from error
    except ValueError as error:
        raise RuntimeError("World Bank country metadata response was not JSON.") from error

    if not isinstance(json_data, list) or len(json_data) < 2 or json_data[1] is None:
        raise ValueError("No country metadata returned from World Bank API.")

    rows: List[Dict[str, Any]] = []

    for item in json_data[1]:
        iso3 = item.get("id")
        name = item.get("name")
        region = item.get("region", {}) or {}
        income_level = item.get("incomeLevel", {}) or {}
        lending_type = item.get("lendingType", {}) or {}

        region_name = region.get("value")

        if not iso3 or not name or region_name == "Aggregates":
            continue

        rows.append(
            {
                "country_code": iso3,
                "world_bank_country_name": name,
                "world_bank_region": region_name,
                "world_bank_income_level": income_level.get("value"),
                "world_bank_lending_type": lending_type.get("value"),
            }
        )

    mapping_df = pd.DataFrame(rows)

    if mapping_df.empty:
        raise ValueError("World Bank country metadata mapping is empty.")

    mapping_df = (
        mapping_df.sort_values("country_code")
        .drop_duplicates(subset=["country_code"], keep="first")
        .reset_index(drop=True)
    )

    mapping_df.to_csv(COUNTRY_REGION_MAPPING_FILE, index=False)

    print("Country-region mapping saved to:")
    print(COUNTRY_REGION_MAPPING_FILE)
    print(f"Country-region rows: {len(mapping_df)}")

    return mapping_df


# ---------------------------------------------------
# Conflict supplement compatibility
# ---------------------------------------------------

def load_conflict_supplement() -> pd.DataFrame | None:
    """
    Load and normalize the conflict supplement if available.

    This function supports both older and newer conflict-supplement column names.

    Newer expected fields may include:
    - conflict_deaths_total
    - organized_violence_active
    - conflict_intensity_risk

    Older expected fields may include:
    - conflict_total_deaths_best
    - conflict_exposure_flag
    - conflict_deaths_per_million_proxy
    """

    if not CONFLICT_DATA_SUPPLEMENT_FILE.exists():
        print("Conflict supplement file not found. Regional conflict fields will default to zero.")
        return None

    conflict_df = pd.read_csv(CONFLICT_DATA_SUPPLEMENT_FILE)

    if "country_code" not in conflict_df.columns:
        print("Conflict supplement has no country_code column. Skipping conflict merge.")
        return None

    conflict_df = conflict_df.copy()

    rename_map = {
        "conflict_deaths_total": "conflict_total_deaths_best",
        "organized_violence_active": "conflict_exposure_flag",
    }

    conflict_df = conflict_df.rename(columns=rename_map)

    # Build a proxy death-rate column if it does not already exist.
    # This keeps compatibility with the regional summary output without requiring population data.
    if "conflict_deaths_per_million_proxy" not in conflict_df.columns:
        if "conflict_total_deaths_best" in conflict_df.columns:
            conflict_df["conflict_deaths_per_million_proxy"] = conflict_df[
                "conflict_total_deaths_best"
            ]
        else:
            conflict_df["conflict_deaths_per_million_proxy"] = 0

    if "conflict_intensity_risk" not in conflict_df.columns:
        conflict_df["conflict_intensity_risk"] = 0

    if "conflict_total_deaths_best" not in conflict_df.columns:
        conflict_df["conflict_total_deaths_best"] = 0

    if "conflict_exposure_flag" not in conflict_df.columns:
        conflict_df["conflict_exposure_flag"] = (
            conflict_df["conflict_total_deaths_best"].fillna(0) > 0
        ).astype(int)

    keep_columns = [
        "country_code",
        "conflict_total_deaths_best",
        "conflict_exposure_flag",
        "conflict_deaths_per_million_proxy",
        "conflict_intensity_risk",
    ]

    available_columns = [
        column for column in keep_columns if column in conflict_df.columns
    ]

    conflict_df = conflict_df[available_columns].copy()

    # Ensure one row per ISO3 code before merging.
    aggregation_map = {
        "conflict_total_deaths_best": "max",
        "conflict_exposure_flag": "max",
        "conflict_deaths_per_million_proxy": "max",
        "conflict_intensity_risk": "max",
    }

    aggregation_map = {
        key: value
        for key, value in aggregation_map.items()
        if key in conflict_df.columns
    }

    conflict_df = (
        conflict_df.groupby("country_code", as_index=False)
        .agg(aggregation_map)
        .reset_index(drop=True)
    )

    print("Conflict supplement loaded and normalized.")
    print(f"Shape: {conflict_df.shape}")

    return conflict_df


def add_conflict_fields_to_regional_df(regional_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge conflict supplement fields into the regional working dataset.
    """

    regional_df = regional_df.copy()

    conflict_df = load_conflict_supplement()

    if conflict_df is not None:
        regional_df = regional_df.merge(
            conflict_df,
            on="country_code",
            how="left",
        )

    conflict_columns = [
        "conflict_total_deaths_best",
        "conflict_exposure_flag",
        "conflict_deaths_per_million_proxy",
        "conflict_intensity_risk",
    ]

    for column in conflict_columns:
        if column not in regional_df.columns:
            regional_df[column] = 0

        regional_df[column] = pd.to_numeric(
            regional_df[column],
            errors="coerce",
        ).fillna(0)

    return regional_df


# ---------------------------------------------------
# Regional summaries
# ---------------------------------------------------

def create_regional_risk_summary(
    rankings_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create regional summaries from rankings and optional supplements.
    """

    regional_df = rankings_df.merge(
        mapping_df,
        on="country_code",
        how="left",
    )

    regional_df["world_bank_region"] = regional_df["world_bank_region"].fillna(
        "Unmatched / Not classified"
    )

    if CURRENT_FATF_STATUS_COMPARISON_FILE.exists():
        current_fatf_df = pd.read_csv(CURRENT_FATF_STATUS_COMPARISON_FILE)

        if "country_code" in current_fatf_df.columns:
            if "current_fatf_increased_monitoring" in current_fatf_df.columns:
                current_columns = [
                    "country_code",
                    "current_fatf_increased_monitoring",
                ]

                current_fatf_df = current_fatf_df[current_columns].drop_duplicates(
                    subset=["country_code"],
                    keep="first",
                )

                regional_df = regional_df.merge(
                    current_fatf_df,
                    on="country_code",
                    how="left",
                )
            else:
                regional_df["current_fatf_increased_monitoring"] = 0
        else:
            regional_df["current_fatf_increased_monitoring"] = 0
    else:
        regional_df["current_fatf_increased_monitoring"] = 0

    regional_df["current_fatf_increased_monitoring"] = pd.to_numeric(
        regional_df["current_fatf_increased_monitoring"],
        errors="coerce",
    ).fillna(0)

    regional_df = add_conflict_fields_to_regional_df(regional_df)

    summary = (
        regional_df.groupby("world_bank_region", dropna=False)
        .agg(
            country_count=("country", "count"),
            average_risk_score=("tf_vulnerability_score", "mean"),
            median_risk_score=("tf_vulnerability_score", "median"),
            highest_risk_score=("tf_vulnerability_score", "max"),
            fatf_grey_list_count=("fatf_grey_list", "sum"),
            current_fatf_monitoring_count=(
                "current_fatf_increased_monitoring",
                "sum",
            ),
            countries_with_conflict_exposure=("conflict_exposure_flag", "sum"),
            total_conflict_deaths_best=("conflict_total_deaths_best", "sum"),
            average_conflict_deaths_per_million_proxy=(
                "conflict_deaths_per_million_proxy",
                "mean",
            ),
            average_conflict_intensity_risk=(
                "conflict_intensity_risk",
                "mean",
            ),
        )
        .reset_index()
    )

    # Add highest-risk country by region.
    top_country_by_region = (
        regional_df.sort_values("tf_vulnerability_score", ascending=False)
        .drop_duplicates("world_bank_region")
        [["world_bank_region", "country"]]
        .rename(columns={"country": "highest_risk_country"})
    )

    summary = summary.merge(
        top_country_by_region,
        on="world_bank_region",
        how="left",
    )

    numeric_columns = [
        "average_risk_score",
        "median_risk_score",
        "highest_risk_score",
        "average_conflict_deaths_per_million_proxy",
        "average_conflict_intensity_risk",
    ]

    for column in numeric_columns:
        if column in summary.columns:
            summary[column] = pd.to_numeric(
                summary[column],
                errors="coerce",
            ).round(3)

    count_columns = [
        "country_count",
        "fatf_grey_list_count",
        "current_fatf_monitoring_count",
        "countries_with_conflict_exposure",
        "total_conflict_deaths_best",
    ]

    for column in count_columns:
        if column in summary.columns:
            summary[column] = pd.to_numeric(
                summary[column],
                errors="coerce",
            ).fillna(0)

    summary = summary.sort_values(
        "average_risk_score",
        ascending=False,
    ).reset_index(drop=True)

    summary.to_csv(REGIONAL_RISK_SUMMARY_FILE, index=False)

    print("Regional risk summary saved to:")
    print(REGIONAL_RISK_SUMMARY_FILE)

    return summary


# ---------------------------------------------------
# Sanctions and FATF mutual-evaluation templates
# ---------------------------------------------------

def create_sanctions_template(rankings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create or load a sanctions exposure input template.
    """

    template_columns = [
        "country",
        "country_code",
        "sanctions_case_count",
        "financial_sanctions_flag",
        "arms_sanctions_flag",
        "trade_sanctions_flag",
        "travel_sanctions_flag",
        "terrorism_related_sanctions_flag",
        "source_note",
    ]

    if SANCTIONS_EXPOSURE_TEMPLATE_FILE.exists():
        sanctions_df = pd.read_csv(SANCTIONS_EXPOSURE_TEMPLATE_FILE)
        print("Sanctions exposure input template loaded:")
        print(SANCTIONS_EXPOSURE_TEMPLATE_FILE)
    else:
        sanctions_df = rankings_df[["country", "country_code"]].copy()

        for column in template_columns:
            if column not in sanctions_df.columns:
                sanctions_df[column] = ""

        sanctions_df = sanctions_df[template_columns]
        sanctions_df.to_csv(SANCTIONS_EXPOSURE_TEMPLATE_FILE, index=False)

        print("Sanctions exposure input template created:")
        print(SANCTIONS_EXPOSURE_TEMPLATE_FILE)

    for column in template_columns:
        if column not in sanctions_df.columns:
            sanctions_df[column] = ""

    sanctions_df = sanctions_df[template_columns]

    return sanctions_df


def create_fatf_mutual_evaluation_template(rankings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create or load a FATF mutual-evaluation input template.
    """

    template_columns = [
        "country",
        "country_code",
        "technical_compliance_score",
        "effectiveness_score",
        "non_compliant_count",
        "partially_compliant_count",
        "low_effectiveness_outcomes_count",
        "mutual_evaluation_year",
        "source_note",
    ]

    if FATF_MUTUAL_EVALUATION_TEMPLATE_FILE.exists():
        fatf_df = pd.read_csv(FATF_MUTUAL_EVALUATION_TEMPLATE_FILE)
        print("FATF mutual-evaluation input template loaded:")
        print(FATF_MUTUAL_EVALUATION_TEMPLATE_FILE)
    else:
        fatf_df = rankings_df[["country", "country_code"]].copy()

        for column in template_columns:
            if column not in fatf_df.columns:
                fatf_df[column] = ""

        fatf_df = fatf_df[template_columns]
        fatf_df.to_csv(FATF_MUTUAL_EVALUATION_TEMPLATE_FILE, index=False)

        print("FATF mutual-evaluation input template created:")
        print(FATF_MUTUAL_EVALUATION_TEMPLATE_FILE)

    for column in template_columns:
        if column not in fatf_df.columns:
            fatf_df[column] = ""

    fatf_df = fatf_df[template_columns]

    return fatf_df


def save_sanctions_supplement(
    rankings_df: pd.DataFrame,
    sanctions_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge the sanctions template with model outputs and save a supplement.
    """

    base_columns = [
        "risk_rank",
        "country",
        "country_code",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
    ]

    supplement = rankings_df[base_columns].merge(
        sanctions_df.drop(columns=["country"], errors="ignore"),
        on="country_code",
        how="left",
    )

    supplement.to_csv(SANCTIONS_EXPOSURE_SUPPLEMENT_FILE, index=False)

    print("Sanctions exposure supplement saved to:")
    print(SANCTIONS_EXPOSURE_SUPPLEMENT_FILE)

    return supplement


def save_fatf_mutual_evaluation_supplement(
    rankings_df: pd.DataFrame,
    fatf_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge the FATF mutual-evaluation template with model outputs and save a supplement.
    """

    base_columns = [
        "risk_rank",
        "country",
        "country_code",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
    ]

    supplement = rankings_df[base_columns].merge(
        fatf_df.drop(columns=["country"], errors="ignore"),
        on="country_code",
        how="left",
    )

    supplement.to_csv(FATF_MUTUAL_EVALUATION_SUPPLEMENT_FILE, index=False)

    print("FATF mutual-evaluation supplement saved to:")
    print(FATF_MUTUAL_EVALUATION_SUPPLEMENT_FILE)

    return supplement


# ---------------------------------------------------
# Charts
# ---------------------------------------------------

def save_regional_average_risk_chart(regional_summary_df: pd.DataFrame) -> None:
    """
    Save a regional average risk score chart.
    """

    if regional_summary_df.empty:
        print("Regional summary is empty. Skipping regional average risk chart.")
        return

    chart_df = regional_summary_df.sort_values(
        "average_risk_score",
        ascending=True,
    )

    plt.figure(figsize=(11, 7))
    plt.barh(chart_df["world_bank_region"], chart_df["average_risk_score"])
    plt.title("Average Terrorism-Financing Vulnerability Score by Region")
    plt.xlabel("Average Vulnerability Score")
    plt.ylabel("World Bank Region")
    plt.tight_layout()
    plt.savefig(REGIONAL_AVERAGE_RISK_CHART_FILE, dpi=300)
    plt.close()

    print("Regional average risk chart saved to:")
    print(REGIONAL_AVERAGE_RISK_CHART_FILE)


def save_regional_fatf_count_chart(regional_summary_df: pd.DataFrame) -> None:
    """
    Save a regional FATF count chart.
    """

    if regional_summary_df.empty:
        print("Regional summary is empty. Skipping regional FATF chart.")
        return

    chart_df = regional_summary_df.sort_values(
        "current_fatf_monitoring_count",
        ascending=True,
    )

    plt.figure(figsize=(11, 7))
    plt.barh(
        chart_df["world_bank_region"],
        chart_df["current_fatf_monitoring_count"],
    )
    plt.title("Current FATF Increased-Monitoring Count by Region")
    plt.xlabel("Current FATF Increased-Monitoring Countries")
    plt.ylabel("World Bank Region")
    plt.tight_layout()
    plt.savefig(REGIONAL_FATF_COUNT_CHART_FILE, dpi=300)
    plt.close()

    print("Regional FATF count chart saved to:")
    print(REGIONAL_FATF_COUNT_CHART_FILE)


def save_current_fatf_status_comparison_chart() -> None:
    """
    Save a model-vs-current FATF status comparison chart.
    """

    if not CURRENT_FATF_STATUS_COMPARISON_FILE.exists():
        print("Current FATF status comparison file not found. Skipping chart.")
        return

    df = pd.read_csv(CURRENT_FATF_STATUS_COMPARISON_FILE)

    required_columns = [
        "model_fatf_grey_list",
        "current_fatf_increased_monitoring",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        print(
            "Current FATF comparison columns missing. Skipping chart. "
            f"Missing columns: {missing_columns}"
        )
        return

    matched_non_monitored = int(
        (
            (df["model_fatf_grey_list"] == 0)
            & (df["current_fatf_increased_monitoring"] == 0)
        ).sum()
    )
    model_only = int(
        (
            (df["model_fatf_grey_list"] == 1)
            & (df["current_fatf_increased_monitoring"] == 0)
        ).sum()
    )
    current_only = int(
        (
            (df["model_fatf_grey_list"] == 0)
            & (df["current_fatf_increased_monitoring"] == 1)
        ).sum()
    )
    matched_monitored = int(
        (
            (df["model_fatf_grey_list"] == 1)
            & (df["current_fatf_increased_monitoring"] == 1)
        ).sum()
    )

    labels = [
        "Matched\nnot monitored",
        "Model target\nonly",
        "Current FATF\nonly",
        "Matched\nmonitored",
    ]
    values = [
        matched_non_monitored,
        model_only,
        current_only,
        matched_monitored,
    ]

    plt.figure(figsize=(9, 6))
    plt.bar(labels, values)
    plt.title("Model FATF Target vs Current FATF Increased-Monitoring Status")
    plt.xlabel("Status Category")
    plt.ylabel("Number of Countries")
    plt.tight_layout()
    plt.savefig(CURRENT_FATF_STATUS_COMPARISON_CHART_FILE, dpi=300)
    plt.close()

    print("Current FATF status comparison chart saved to:")
    print(CURRENT_FATF_STATUS_COMPARISON_CHART_FILE)


# ---------------------------------------------------
# Summary table
# ---------------------------------------------------

def count_populated_rows(df: pd.DataFrame, value_columns: List[str]) -> int:
    """
    Count rows with at least one populated value among selected columns.
    """

    available_columns = [
        column for column in value_columns if column in df.columns
    ]

    if not available_columns:
        return 0

    temp = df[available_columns].copy()
    temp = temp.replace("", pd.NA)

    return int(temp.notna().any(axis=1).sum())


def save_additional_factor_summary(
    regional_summary_df: pd.DataFrame,
    sanctions_supplement_df: pd.DataFrame,
    fatf_supplement_df: pd.DataFrame,
) -> None:
    """
    Save a compact summary of additional-factor readiness.
    """

    sanctions_populated = count_populated_rows(
        sanctions_supplement_df,
        [
            "sanctions_case_count",
            "financial_sanctions_flag",
            "arms_sanctions_flag",
            "trade_sanctions_flag",
            "travel_sanctions_flag",
            "terrorism_related_sanctions_flag",
        ],
    )

    fatf_populated = count_populated_rows(
        fatf_supplement_df,
        [
            "technical_compliance_score",
            "effectiveness_score",
            "non_compliant_count",
            "partially_compliant_count",
            "low_effectiveness_outcomes_count",
            "mutual_evaluation_year",
        ],
    )

    summary_df = pd.DataFrame(
        [
            {
                "factor": "Regional risk groupings",
                "status": "Created from World Bank country metadata",
                "records_or_groups": len(regional_summary_df),
                "output_file": str(REGIONAL_RISK_SUMMARY_FILE),
            },
            {
                "factor": "Regional conflict context",
                "status": "Created if conflict supplement exists; defaults to zero otherwise",
                "records_or_groups": int(
                    regional_summary_df.get(
                        "countries_with_conflict_exposure",
                        pd.Series(dtype=float),
                    ).sum()
                )
                if "countries_with_conflict_exposure" in regional_summary_df.columns
                else 0,
                "output_file": str(REGIONAL_RISK_SUMMARY_FILE),
            },
            {
                "factor": "Sanctions exposure indicators",
                "status": "Template created; supplement updates when template is populated",
                "records_or_groups": sanctions_populated,
                "output_file": str(SANCTIONS_EXPOSURE_SUPPLEMENT_FILE),
            },
            {
                "factor": "FATF mutual evaluation indicators",
                "status": "Template created; supplement updates when template is populated",
                "records_or_groups": fatf_populated,
                "output_file": str(FATF_MUTUAL_EVALUATION_SUPPLEMENT_FILE),
            },
            {
                "factor": "Current FATF visualization",
                "status": "Chart created if current FATF comparison file exists",
                "records_or_groups": 1
                if CURRENT_FATF_STATUS_COMPARISON_FILE.exists()
                else 0,
                "output_file": str(CURRENT_FATF_STATUS_COMPARISON_CHART_FILE),
            },
        ]
    )

    summary_df.to_csv(ADDITIONAL_RISK_FACTOR_SUMMARY_FILE, index=False)

    print("Additional risk factor summary saved to:")
    print(ADDITIONAL_RISK_FACTOR_SUMMARY_FILE)


# ---------------------------------------------------
# Validation
# ---------------------------------------------------

def validate_outputs(
    regional_summary_df: pd.DataFrame,
    sanctions_supplement_df: pd.DataFrame,
    fatf_supplement_df: pd.DataFrame,
) -> None:
    """
    Validate core supplemental outputs before ending the module.
    """

    if regional_summary_df.empty:
        raise ValueError("Regional risk summary is empty.")

    required_regional_columns = [
        "world_bank_region",
        "country_count",
        "average_risk_score",
        "fatf_grey_list_count",
        "current_fatf_monitoring_count",
        "countries_with_conflict_exposure",
        "total_conflict_deaths_best",
        "average_conflict_intensity_risk",
        "highest_risk_country",
    ]

    missing_regional_columns = [
        column
        for column in required_regional_columns
        if column not in regional_summary_df.columns
    ]

    if missing_regional_columns:
        raise ValueError(
            "Regional summary is missing required columns: "
            f"{missing_regional_columns}"
        )

    if sanctions_supplement_df.empty:
        raise ValueError("Sanctions supplement is empty.")

    if fatf_supplement_df.empty:
        raise ValueError("FATF mutual-evaluation supplement is empty.")

    print("\nAdditional risk factor output validation passed.")


# ---------------------------------------------------
# Main workflow
# ---------------------------------------------------

def main() -> None:
    """
    Run additional risk factor outputs.
    """

    print("=" * 70)
    print("Running additional risk factor analysis")
    print("=" * 70)

    ensure_output_dirs()

    rankings_df = load_rankings()

    mapping_df = fetch_world_bank_country_metadata()
    regional_summary_df = create_regional_risk_summary(rankings_df, mapping_df)

    sanctions_df = create_sanctions_template(rankings_df)
    sanctions_supplement_df = save_sanctions_supplement(rankings_df, sanctions_df)

    fatf_df = create_fatf_mutual_evaluation_template(rankings_df)
    fatf_supplement_df = save_fatf_mutual_evaluation_supplement(rankings_df, fatf_df)

    save_regional_average_risk_chart(regional_summary_df)
    save_regional_fatf_count_chart(regional_summary_df)
    save_current_fatf_status_comparison_chart()

    save_additional_factor_summary(
        regional_summary_df=regional_summary_df,
        sanctions_supplement_df=sanctions_supplement_df,
        fatf_supplement_df=fatf_supplement_df,
    )

    validate_outputs(
        regional_summary_df=regional_summary_df,
        sanctions_supplement_df=sanctions_supplement_df,
        fatf_supplement_df=fatf_supplement_df,
    )

    print("\nAdditional risk factor analysis complete.")


if __name__ == "__main__":
    main()