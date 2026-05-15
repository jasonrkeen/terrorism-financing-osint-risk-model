"""
Conflict data supplement for the terrorism financing OSINT risk model.

This module adds a supplemental conflict-exposure layer using the UCDP
Country-Year Dataset on Organized Violence within Country Borders.

The conflict supplement does not replace the main terrorism-financing
vulnerability score. It creates additional context tables and a chart that can
be used in future report versions.
"""

from __future__ import annotations

import io
import math
import re
import unicodedata
import zipfile
from typing import Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd
import requests

from src.config import (
    STUDY_YEAR,
    RISK_RANKINGS_FILE,
    RAW_DATA_DIR,
    TABLES_DIR,
    CHARTS_DIR,
    RISK_SCORE_WEIGHTS,
    UCDP_ORGANIZED_VIOLENCE_URL,
    UCDP_CONFLICT_RAW_FILE,
    CONFLICT_DATA_SUPPLEMENT_FILE,
    TOP_RISK_DRIVERS_FILE,
    TOP_15_CONFLICT_FATALITIES_CHART_FILE,
)


# ---------------------------------------------------
# Risk-driver labels
# ---------------------------------------------------

RISK_DRIVER_LABELS = {
    "corruption_risk_scaled": "Corruption risk",
    "rule_of_law_risk_scaled": "Rule of law risk",
    "political_instability_risk_scaled": "Political instability risk",
    "low_income_risk_scaled": "Low income risk",
    "inflation_risk_scaled": "Inflation risk",
    "unemployment_risk_scaled": "Unemployment risk",
}


# ---------------------------------------------------
# Country-name aliases
# ---------------------------------------------------
# World Bank and UCDP use different country naming conventions. These aliases
# handle the most common differences observed in the project outputs.

COUNTRY_NAME_ALIASES = {
    "Bahamas, The": "Bahamas",
    "Bolivia": "Bolivia",
    "Brunei Darussalam": "Brunei",
    "Cabo Verde": "Cape Verde",
    "Congo, Dem. Rep.": "DR Congo (Zaire)",
    "Congo, Rep.": "Congo",
    "Cote d'Ivoire": "Ivory Coast",
    "Egypt, Arab Rep.": "Egypt",
    "Gambia, The": "Gambia",
    "Hong Kong SAR, China": "Hong Kong",
    "Iran, Islamic Rep.": "Iran",
    "Korea, Dem. People's Rep.": "North Korea",
    "Korea, Rep.": "South Korea",
    "Kyrgyz Republic": "Kyrgyzstan",
    "Lao PDR": "Laos",
    "Macao SAR, China": "Macao",
    "Micronesia, Fed. Sts.": "Micronesia",
    "Russian Federation": "Russia",
    "Slovak Republic": "Slovakia",
    "Syrian Arab Republic": "Syria",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "United States": "United States of America",
    "Venezuela, RB": "Venezuela",
    "Viet Nam": "Vietnam",
    "Vietnam": "Vietnam",
    "West Bank and Gaza": "Palestine",
    "Yemen, Rep.": "Yemen (North Yemen)",
}


# Additional fallback aliases. These are used when the first alias is not
# present in the downloaded UCDP file.
FALLBACK_ALIASES = {
    "Bosnia and Herzegovina": [
        "Bosnia-Herzegovina",
        "Bosnia Herzegovina",
    ],
    "Cambodia": [
        "Cambodia (Kampuchea)",
        "Kampuchea",
    ],
    "Congo, Dem. Rep.": [
        "Democratic Republic of the Congo",
        "DR Congo",
        "Zaire",
    ],
    "Cote d'Ivoire": [
        "Côte d'Ivoire",
        "Cote d Ivoire",
        "Ivory Coast",
    ],
    "Czechia": [
        "Czech Republic",
        "Czechoslovakia",
    ],
    "Eswatini": [
        "Swaziland",
    ],
    "Madagascar": [
        "Madagascar (Malagasy)",
        "Malagasy",
    ],
    "Myanmar": [
        "Myanmar (Burma)",
        "Burma",
    ],
    "Russian Federation": [
        "Russia",
        "Soviet Union",
    ],
    "Samoa": [
        "Western Samoa",
    ],
    "Serbia": [
        "Serbia (Yugoslavia)",
        "Yugoslavia",
    ],
    "St. Lucia": [
        "Saint Lucia",
    ],
    "St. Vincent and the Grenadines": [
        "Saint Vincent and the Grenadines",
    ],
    "Timor-Leste": [
        "East Timor",
    ],
    "United States": [
        "USA",
        "United States",
    ],
    "Viet Nam": [
        "Vietnam",
    ],
    "Yemen, Rep.": [
        "Yemen",
        "Yemen Arab Republic",
    ],
    "Zimbabwe": [
        "Zimbabwe (Rhodesia)",
        "Rhodesia",
    ],
}


# ---------------------------------------------------
# Loading and downloading
# ---------------------------------------------------

def load_rankings() -> pd.DataFrame:
    """
    Load the final country risk rankings dataset.
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
        "tf_vulnerability_score",
    ] + list(RISK_SCORE_WEIGHTS.keys())

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required columns for conflict "
            f"supplement analysis: {missing_columns}"
        )

    print("Risk rankings loaded.")
    print(f"Shape: {df.shape}")

    return df


def download_ucdp_zip() -> bytes:
    """
    Download the UCDP organized-violence country-year zip file.
    """

    print("Downloading UCDP country-year organized-violence data...")
    print(UCDP_ORGANIZED_VIOLENCE_URL)

    try:
        response = requests.get(UCDP_ORGANIZED_VIOLENCE_URL, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "Could not download UCDP organized-violence data. "
            "Check the URL in src/config.py or your internet connection."
        ) from error

    return response.content


def read_ucdp_csv_from_zip(zip_content: bytes) -> pd.DataFrame:
    """
    Read the first CSV file found inside the UCDP zip archive.
    """

    with zipfile.ZipFile(io.BytesIO(zip_content)) as archive:
        csv_files = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            raise ValueError("No CSV file was found inside the UCDP zip archive.")

        csv_name = csv_files[0]
        print(f"Reading CSV from archive: {csv_name}")

        with archive.open(csv_name) as file:
            df = pd.read_csv(file)

    return df


def save_raw_ucdp_data(df: pd.DataFrame) -> None:
    """
    Save the raw UCDP country-year data to data/raw/.
    """

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(UCDP_CONFLICT_RAW_FILE, index=False)

    print("UCDP raw country-year data saved to:")
    print(UCDP_CONFLICT_RAW_FILE)


# ---------------------------------------------------
# UCDP standardization
# ---------------------------------------------------

def get_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """
    Return the first candidate column that exists in a dataframe.
    """

    for column in candidates:
        if column in df.columns:
            return column

    return None


def ensure_numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Return a numeric series for a column, using zeros when the column is missing.
    """

    if column not in df.columns:
        return pd.Series(0, index=df.index)

    return pd.to_numeric(df[column], errors="coerce").fillna(0)


def classify_conflict_intensity(deaths: float) -> str:
    """
    Classify organized-violence fatality intensity for report readability.
    """

    if deaths <= 0:
        return "No recorded organized-violence deaths"
    if deaths < 25:
        return "Low recorded conflict exposure"
    if deaths < 1000:
        return "Moderate recorded conflict exposure"

    return "High recorded conflict exposure"


def standardize_ucdp_data(raw_df: pd.DataFrame, study_year: int) -> pd.DataFrame:
    """
    Standardize the UCDP country-year dataset for project use.

    The UCDP organized-violence country-year v25.1 file uses *_cy column names,
    including country_cy, year_cy, region_cy, and fatality columns such as
    sb_total_deaths_best_cy, ns_total_deaths_best_cy, and
    os_total_deaths_best_cy.
    """

    print(f"Raw UCDP shape: {raw_df.shape}")
    print("UCDP columns:")
    print(list(raw_df.columns))

    country_column = get_first_existing_column(
        raw_df,
        ["country_cy", "country", "country_name", "location"],
    )
    year_column = get_first_existing_column(
        raw_df,
        ["year_cy", "year"],
    )
    region_column = get_first_existing_column(
        raw_df,
        ["region_cy", "region"],
    )

    if country_column is None or year_column is None:
        raise ValueError(
            "Could not identify required UCDP year/country columns. "
            f"Columns found: {list(raw_df.columns)}"
        )

    df = raw_df.copy()
    df[year_column] = pd.to_numeric(df[year_column], errors="coerce")
    df = df[df[year_column].notna()].copy()
    df[year_column] = df[year_column].astype(int)

    # Keep the selected study year when available. If future versions are used,
    # this function still supports latest available <= study year.
    df = df[df[year_column] <= study_year].copy()

    if df.empty:
        raise ValueError(
            f"No UCDP observations were found for years <= {study_year}."
        )

    df = (
        df.sort_values([country_column, year_column], ascending=[True, False])
        .drop_duplicates(subset=[country_column], keep="first")
        .reset_index(drop=True)
    )

    standardized_df = pd.DataFrame()
    standardized_df["ucdp_country"] = df[country_column]
    standardized_df["ucdp_year"] = df[year_column]

    if region_column is not None:
        standardized_df["ucdp_region"] = df[region_column]
    else:
        standardized_df["ucdp_region"] = "Unknown"

    standardized_df["state_based_deaths"] = ensure_numeric_column(
        df,
        "sb_total_deaths_best_cy",
    )
    standardized_df["non_state_deaths"] = ensure_numeric_column(
        df,
        "ns_total_deaths_best_cy",
    )
    standardized_df["one_sided_deaths"] = ensure_numeric_column(
        df,
        "os_total_deaths_best_cy",
    )

    standardized_df["state_based_dyad_count"] = ensure_numeric_column(
        df,
        "sb_dyad_count_cy",
    )
    standardized_df["non_state_dyad_count"] = ensure_numeric_column(
        df,
        "ns_dyad_count_cy",
    )
    standardized_df["one_sided_dyad_count"] = ensure_numeric_column(
        df,
        "os_dyad_count_cy",
    )

    standardized_df["state_based_active"] = ensure_numeric_column(
        df,
        "sb_exist_cy",
    )
    standardized_df["non_state_active"] = ensure_numeric_column(
        df,
        "ns_exist_cy",
    )
    standardized_df["one_sided_active"] = ensure_numeric_column(
        df,
        "os_exist_cy",
    )

    standardized_df["conflict_deaths_total"] = (
        standardized_df["state_based_deaths"]
        + standardized_df["non_state_deaths"]
        + standardized_df["one_sided_deaths"]
    )

    standardized_df["conflict_dyad_count"] = (
        standardized_df["state_based_dyad_count"]
        + standardized_df["non_state_dyad_count"]
        + standardized_df["one_sided_dyad_count"]
    )

    standardized_df["organized_violence_active"] = (
        (
            standardized_df["state_based_active"]
            + standardized_df["non_state_active"]
            + standardized_df["one_sided_active"]
            + standardized_df["conflict_deaths_total"]
        )
        > 0
    ).astype(int)

    standardized_df["conflict_intensity_category"] = standardized_df[
        "conflict_deaths_total"
    ].apply(classify_conflict_intensity)

    print("\nStandardized UCDP conflict data created.")
    print(f"Shape: {standardized_df.shape}")
    print("Year coverage in standardized conflict data:")
    print(
        standardized_df["ucdp_year"]
        .value_counts()
        .sort_index(ascending=False)
        .head()
    )

    return standardized_df


# ---------------------------------------------------
# Country matching
# ---------------------------------------------------

def normalize_country_name(name: object) -> str:
    """
    Normalize country names for cross-source matching.
    """

    if pd.isna(name):
        return ""

    text = str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    text = text.lower()
    text = text.replace("&", "and")
    text = re.sub(r"[()'.,-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    replacements = {
        "republic of": "",
        "democratic": "dem",
        "arab republic": "",
        "islamic rep": "",
        "fed rep": "",
        "fed sts": "",
        "rep": "",
        "rb": "",
        "the": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def build_ucdp_lookup(ucdp_df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Build a normalized-name lookup for UCDP rows.
    """

    lookup: Dict[str, pd.Series] = {}

    for _, row in ucdp_df.iterrows():
        key = normalize_country_name(row["ucdp_country"])

        if key:
            lookup[key] = row

    return lookup


def find_ucdp_match(
    country: str,
    ucdp_lookup: Dict[str, pd.Series],
) -> Optional[pd.Series]:
    """
    Find a UCDP row for a World Bank country name.
    """

    direct_key = normalize_country_name(country)

    if direct_key in ucdp_lookup:
        return ucdp_lookup[direct_key]

    alias = COUNTRY_NAME_ALIASES.get(country)

    if alias:
        alias_key = normalize_country_name(alias)

        if alias_key in ucdp_lookup:
            return ucdp_lookup[alias_key]

    for fallback_alias in FALLBACK_ALIASES.get(country, []):
        fallback_key = normalize_country_name(fallback_alias)

        if fallback_key in ucdp_lookup:
            return ucdp_lookup[fallback_key]

    return None


# ---------------------------------------------------
# Supplement creation
# ---------------------------------------------------

def calculate_conflict_intensity_risk(conflict_df: pd.DataFrame) -> pd.Series:
    """
    Calculate normalized conflict-intensity risk using log-scaled deaths.

    The output ranges from 0 to 1:
    - 0 means no recorded organized-violence deaths
    - 1 means the highest recorded death count in the supplement
    """

    deaths = pd.to_numeric(
        conflict_df["conflict_deaths_total"],
        errors="coerce",
    ).fillna(0)

    deaths = deaths.clip(lower=0)
    max_deaths = float(deaths.max())

    if max_deaths <= 0:
        return pd.Series(0, index=conflict_df.index)

    return deaths.apply(
        lambda value: math.log1p(value) / math.log1p(max_deaths)
    )


def merge_conflict_data(
    rankings_df: pd.DataFrame,
    ucdp_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge standardized UCDP conflict data into the risk rankings dataset.
    """

    ucdp_lookup = build_ucdp_lookup(ucdp_df)
    records = []
    unmatched_countries = []

    for _, ranking_row in rankings_df.iterrows():
        country = ranking_row["country"]
        match = find_ucdp_match(country, ucdp_lookup)

        if match is None:
            unmatched_countries.append(country)
            conflict_record = {
                "ucdp_match_found": 0,
                "ucdp_country": None,
                "ucdp_region": None,
                "ucdp_year": None,
                "state_based_deaths": 0,
                "non_state_deaths": 0,
                "one_sided_deaths": 0,
                "conflict_deaths_total": 0,
                "state_based_dyad_count": 0,
                "non_state_dyad_count": 0,
                "one_sided_dyad_count": 0,
                "conflict_dyad_count": 0,
                "organized_violence_active": 0,
                "conflict_intensity_category": "No UCDP country match found",
            }
        else:
            conflict_record = {
                "ucdp_match_found": 1,
                "ucdp_country": match["ucdp_country"],
                "ucdp_region": match["ucdp_region"],
                "ucdp_year": match["ucdp_year"],
                "state_based_deaths": match["state_based_deaths"],
                "non_state_deaths": match["non_state_deaths"],
                "one_sided_deaths": match["one_sided_deaths"],
                "conflict_deaths_total": match["conflict_deaths_total"],
                "state_based_dyad_count": match["state_based_dyad_count"],
                "non_state_dyad_count": match["non_state_dyad_count"],
                "one_sided_dyad_count": match["one_sided_dyad_count"],
                "conflict_dyad_count": match["conflict_dyad_count"],
                "organized_violence_active": match["organized_violence_active"],
                "conflict_intensity_category": match["conflict_intensity_category"],
            }

        combined_record = ranking_row.to_dict()
        combined_record.update(conflict_record)
        records.append(combined_record)

    supplement_df = pd.DataFrame(records)

    numeric_conflict_columns = [
        "state_based_deaths",
        "non_state_deaths",
        "one_sided_deaths",
        "conflict_deaths_total",
        "state_based_dyad_count",
        "non_state_dyad_count",
        "one_sided_dyad_count",
        "conflict_dyad_count",
        "organized_violence_active",
    ]

    for column in numeric_conflict_columns:
        supplement_df[column] = pd.to_numeric(
            supplement_df[column],
            errors="coerce",
        ).fillna(0)

    supplement_df["conflict_intensity_risk"] = calculate_conflict_intensity_risk(
        supplement_df
    )

    if unmatched_countries:
        print("\nCountries not matched to UCDP names:")
        for country in unmatched_countries:
            print(f"- {country}")
    else:
        print("\nAll modeled countries were matched to UCDP country names.")

    return supplement_df


def create_top_risk_drivers(rankings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a table showing the top three weighted risk-score drivers per country.
    """

    required_columns = [
        "risk_rank",
        "country",
        "tf_vulnerability_score",
    ] + list(RISK_SCORE_WEIGHTS.keys())

    missing_columns = [
        column for column in required_columns
        if column not in rankings_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required columns for risk-driver analysis: "
            f"{missing_columns}"
        )

    records = []

    for _, row in rankings_df.iterrows():
        contributions = []

        for feature, weight in RISK_SCORE_WEIGHTS.items():
            contribution = float(row[feature]) * float(weight) * 100

            contributions.append(
                {
                    "feature": feature,
                    "driver": RISK_DRIVER_LABELS.get(feature, feature),
                    "contribution": contribution,
                }
            )

        contributions = sorted(
            contributions,
            key=lambda item: item["contribution"],
            reverse=True,
        )

        record = {
            "risk_rank": int(row["risk_rank"]),
            "country": row["country"],
            "tf_vulnerability_score": row["tf_vulnerability_score"],
            "driver_1": contributions[0]["driver"],
            "driver_1_contribution": contributions[0]["contribution"],
            "driver_2": contributions[1]["driver"],
            "driver_2_contribution": contributions[1]["contribution"],
            "driver_3": contributions[2]["driver"],
            "driver_3_contribution": contributions[2]["contribution"],
        }

        records.append(record)

    drivers_df = (
        pd.DataFrame(records)
        .sort_values("risk_rank")
        .reset_index(drop=True)
    )

    return drivers_df


# ---------------------------------------------------
# Saving and charting
# ---------------------------------------------------

def save_conflict_outputs(
    conflict_df: pd.DataFrame,
    top_risk_drivers_df: pd.DataFrame,
) -> None:
    """
    Save conflict supplement and top risk driver tables.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    conflict_df.to_csv(CONFLICT_DATA_SUPPLEMENT_FILE, index=False)
    top_risk_drivers_df.to_csv(TOP_RISK_DRIVERS_FILE, index=False)

    print("\nConflict data supplement saved to:")
    print(CONFLICT_DATA_SUPPLEMENT_FILE)

    print("Top risk drivers saved to:")
    print(TOP_RISK_DRIVERS_FILE)


def save_top_15_conflict_fatalities_chart(conflict_df: pd.DataFrame) -> None:
    """
    Save a chart of the top 15 countries by recorded organized-violence deaths.
    """

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    chart_df = (
        conflict_df.sort_values(
            "conflict_deaths_total",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    if chart_df.empty:
        print("No conflict supplement rows available for charting.")
        return

    plt.figure(figsize=(12, 7))
    plt.barh(chart_df["country"], chart_df["conflict_deaths_total"])
    plt.gca().invert_yaxis()
    plt.title(
        "Top 15 Countries by UCDP Organized-Violence Deaths "
        f"Through Target Study Year {STUDY_YEAR}"
    )
    plt.xlabel("Recorded Organized-Violence Deaths")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(TOP_15_CONFLICT_FATALITIES_CHART_FILE, dpi=300)
    plt.close()

    print("Top 15 conflict fatalities chart saved to:")
    print(TOP_15_CONFLICT_FATALITIES_CHART_FILE)


# ---------------------------------------------------
# Summary printing
# ---------------------------------------------------

def print_conflict_summary(
    conflict_df: pd.DataFrame,
    top_risk_drivers_df: pd.DataFrame,
) -> None:
    """
    Print a concise summary of conflict supplement outputs.
    """

    matched_count = int(conflict_df["ucdp_match_found"].sum())
    active_count = int(conflict_df["organized_violence_active"].sum())
    total_deaths = float(conflict_df["conflict_deaths_total"].sum())

    print("\nConflict data supplement summary:")
    print(f"Countries in model dataset: {len(conflict_df)}")
    print(f"Countries matched to UCDP: {matched_count}")
    print(f"Countries with recorded organized violence: {active_count}")
    print(f"Total recorded organized-violence deaths in supplement: {total_deaths:,.0f}")

    print("\nTop 10 countries by recorded organized-violence deaths:")
    print(
        conflict_df.sort_values("conflict_deaths_total", ascending=False)[
            [
                "country",
                "risk_rank",
                "tf_vulnerability_score",
                "ucdp_country",
                "ucdp_year",
                "conflict_deaths_total",
                "conflict_intensity_category",
                "conflict_intensity_risk",
            ]
        ].head(10)
    )

    print("\nTop 10 risk-driver records:")
    print(
        top_risk_drivers_df[
            [
                "risk_rank",
                "country",
                "tf_vulnerability_score",
                "driver_1",
                "driver_2",
                "driver_3",
            ]
        ].head(10)
    )


# ---------------------------------------------------
# Validation
# ---------------------------------------------------

def validate_conflict_outputs(
    conflict_df: pd.DataFrame,
    top_risk_drivers_df: pd.DataFrame,
) -> None:
    """
    Validate conflict supplement outputs before saving.
    """

    if conflict_df.empty:
        raise ValueError("Conflict supplement output is empty.")

    if top_risk_drivers_df.empty:
        raise ValueError("Top risk drivers output is empty.")

    required_conflict_columns = [
        "country",
        "risk_rank",
        "tf_vulnerability_score",
        "ucdp_match_found",
        "ucdp_country",
        "ucdp_year",
        "conflict_deaths_total",
        "organized_violence_active",
        "conflict_intensity_category",
        "conflict_intensity_risk",
    ]

    missing_conflict_columns = [
        column for column in required_conflict_columns
        if column not in conflict_df.columns
    ]

    if missing_conflict_columns:
        raise ValueError(
            "Conflict supplement is missing required columns: "
            f"{missing_conflict_columns}"
        )

    required_driver_columns = [
        "risk_rank",
        "country",
        "tf_vulnerability_score",
        "driver_1",
        "driver_1_contribution",
        "driver_2",
        "driver_2_contribution",
        "driver_3",
        "driver_3_contribution",
    ]

    missing_driver_columns = [
        column for column in required_driver_columns
        if column not in top_risk_drivers_df.columns
    ]

    if missing_driver_columns:
        raise ValueError(
            "Top risk drivers output is missing required columns: "
            f"{missing_driver_columns}"
        )

    if conflict_df["conflict_intensity_risk"].min() < 0:
        raise ValueError("conflict_intensity_risk contains values below 0.")

    if conflict_df["conflict_intensity_risk"].max() > 1:
        raise ValueError("conflict_intensity_risk contains values above 1.")

    print("\nConflict supplement output validation passed.")


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the conflict data supplement workflow.
    """

    print("=" * 70)
    print("Running conflict data supplement")
    print("=" * 70)

    rankings_df = load_rankings()

    zip_content = download_ucdp_zip()
    raw_ucdp_df = read_ucdp_csv_from_zip(zip_content)
    save_raw_ucdp_data(raw_ucdp_df)

    standardized_ucdp_df = standardize_ucdp_data(
        raw_df=raw_ucdp_df,
        study_year=STUDY_YEAR,
    )

    conflict_df = merge_conflict_data(
        rankings_df=rankings_df,
        ucdp_df=standardized_ucdp_df,
    )

    top_risk_drivers_df = create_top_risk_drivers(rankings_df)

    validate_conflict_outputs(conflict_df, top_risk_drivers_df)

    save_conflict_outputs(conflict_df, top_risk_drivers_df)
    save_top_15_conflict_fatalities_chart(conflict_df)
    print_conflict_summary(conflict_df, top_risk_drivers_df)

    print("\nConflict data supplement complete.")


if __name__ == "__main__":
    main()