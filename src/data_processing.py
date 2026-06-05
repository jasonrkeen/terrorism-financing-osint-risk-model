"""
Data processing module for the terrorism financing OSINT risk model.

This script cleans the raw World Bank dataset, removes incomplete records,
creates the FATF grey-list target variable, preserves indicator year fields,
and creates risk-oriented features.

The processed dataset supports the core vulnerability score. UCDP conflict,
ACLED recent-event signals, regional, sanctions, and FATF mutual evaluation
outputs are handled later as supplemental analytical layers.
"""

import numpy as np
import pandas as pd

from src.config import (
    FATF_GREY_LIST_COUNTRIES,
    RAW_WORLD_BANK_DATA_FILE,
    PROCESSED_COUNTRY_DATA_FILE,
    PROCESSED_DATA_DIR,
    RISK_FEATURES,
)


# ---------------------------------------------------
# Countries and aggregates to exclude
# ---------------------------------------------------
# The World Bank API includes regional and income-group aggregates.
# These are not individual countries, so we remove them from the country-level model.

WORLD_BANK_AGGREGATES = [
    "Africa Eastern and Southern",
    "Africa Western and Central",
    "Arab World",
    "Caribbean small states",
    "Central Europe and the Baltics",
    "Early-demographic dividend",
    "East Asia & Pacific",
    "East Asia & Pacific (excluding high income)",
    "East Asia & Pacific (IDA & IBRD countries)",
    "Euro area",
    "Europe & Central Asia",
    "Europe & Central Asia (excluding high income)",
    "Europe & Central Asia (IDA & IBRD countries)",
    "European Union",
    "Fragile and conflict affected situations",
    "Heavily indebted poor countries (HIPC)",
    "High income",
    "IBRD only",
    "IDA & IBRD total",
    "IDA blend",
    "IDA only",
    "IDA total",
    "Late-demographic dividend",
    "Latin America & Caribbean",
    "Latin America & Caribbean (excluding high income)",
    "Latin America & the Caribbean (IDA & IBRD countries)",
    "Least developed countries: UN classification",
    "Low & middle income",
    "Low income",
    "Lower middle income",
    "Middle East & North Africa",
    "Middle East & North Africa (excluding high income)",
    "Middle East & North Africa (IDA & IBRD countries)",
    "Middle income",
    "North America",
    "OECD members",
    "Other small states",
    "Pacific island small states",
    "Post-demographic dividend",
    "Pre-demographic dividend",
    "Small states",
    "South Asia",
    "South Asia (IDA & IBRD)",
    "Sub-Saharan Africa",
    "Sub-Saharan Africa (excluding high income)",
    "Sub-Saharan Africa (IDA & IBRD countries)",
    "Upper middle income",
    "World",
]


# ---------------------------------------------------
# Core required columns
# ---------------------------------------------------

REQUIRED_MODEL_COLUMNS = [
    "control_of_corruption",
    "rule_of_law",
    "political_stability",
    "gdp_per_capita",
    "inflation",
    "unemployment",
]


# ---------------------------------------------------
# Optional indicator year columns
# ---------------------------------------------------
# These columns are created by data_collection.py when the model uses
# the latest available observation up to STUDY_YEAR.

INDICATOR_YEAR_COLUMNS = [
    "control_of_corruption_year",
    "rule_of_law_year",
    "political_stability_year",
    "gdp_per_capita_year",
    "inflation_year",
    "unemployment_year",
]


# ---------------------------------------------------
# FATF country-name aliases
# ---------------------------------------------------
# World Bank and FATF naming conventions may differ. These aliases improve
# target matching without changing the underlying country name in the dataset.

FATF_COUNTRY_ALIASES = {
    "Congo, Dem. Rep.": "Democratic Republic of Congo",
    "Congo, Rep.": "Republic of Congo",
    "Cote d'Ivoire": "Cote d'Ivoire",
    "Côte d'Ivoire": "Cote d'Ivoire",
    "Egypt, Arab Rep.": "Egypt",
    "Gambia, The": "Gambia",
    "Iran, Islamic Rep.": "Iran",
    "Korea, Dem. People's Rep.": "North Korea",
    "Korea, Rep.": "South Korea",
    "Kyrgyz Republic": "Kyrgyzstan",
    "Lao PDR": "Lao PDR",
    "Russian Federation": "Russia",
    "Slovak Republic": "Slovakia",
    "Syrian Arab Republic": "Syrian Arab Republic",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "Venezuela, RB": "Venezuela, RB",
    "Yemen, Rep.": "Yemen, Rep.",
}


# ---------------------------------------------------
# Data loading
# ---------------------------------------------------

def load_raw_data() -> pd.DataFrame:
    """
    Load the raw World Bank country indicator dataset.
    """

    df = pd.read_csv(RAW_WORLD_BANK_DATA_FILE)

    print("Raw data loaded.")
    print(f"Shape: {df.shape}")

    return df


# ---------------------------------------------------
# Cleaning
# ---------------------------------------------------

def clean_country_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the raw dataset by removing regional aggregates and incomplete rows.
    """

    df = df.copy()

    required_identity_columns = ["country", "country_code"]

    missing_identity_columns = [
        column for column in required_identity_columns if column not in df.columns
    ]

    if missing_identity_columns:
        raise ValueError(
            "Raw data is missing required identity columns: "
            f"{missing_identity_columns}"
        )

    missing_model_columns = [
        column for column in REQUIRED_MODEL_COLUMNS if column not in df.columns
    ]

    if missing_model_columns:
        raise ValueError(
            "Raw data is missing required model columns: "
            f"{missing_model_columns}"
        )

    # Remove aggregate World Bank regions and income groups.
    df = df[~df["country"].isin(WORLD_BANK_AGGREGATES)]

    # Remove rows without valid ISO3 country codes.
    df = df[df["country_code"].notna()]
    df["country_code"] = df["country_code"].astype(str)
    df = df[df["country_code"].str.len() == 3]

    # Remove rows without valid country names.
    df = df[df["country"].notna()]
    df["country"] = df["country"].astype(str)

    # Drop rows missing the core model variables.
    df = df.dropna(subset=REQUIRED_MODEL_COLUMNS)

    # Remove countries with invalid GDP per capita values before log transformation.
    df = df[df["gdp_per_capita"] > 0]

    # Keep one row per ISO3 code.
    # This is a safeguard in case upstream World Bank naming differences remain.
    df = (
        df.sort_values(["country_code", "country"])
        .drop_duplicates(subset=["country_code"], keep="first")
        .reset_index(drop=True)
    )

    print("\nCleaned country data.")
    print(f"Shape: {df.shape}")

    return df


# ---------------------------------------------------
# FATF target
# ---------------------------------------------------

def add_fatf_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add FATF grey-list status as a binary target variable.

    1 = country appears in FATF_GREY_LIST_COUNTRIES
    0 = country does not appear in FATF_GREY_LIST_COUNTRIES

    Country-name aliases are used to reduce mismatches caused by
    World Bank naming conventions.
    """

    df = df.copy()

    df["fatf_match_name"] = df["country"].replace(FATF_COUNTRY_ALIASES)

    df["fatf_grey_list"] = (
        df["fatf_match_name"].isin(FATF_GREY_LIST_COUNTRIES).astype(int)
    )

    print("\nFATF grey-list target added.")
    print(df["fatf_grey_list"].value_counts())

    grey_list_matches = df[df["fatf_grey_list"] == 1][
        ["country", "fatf_match_name", "country_code"]
    ].sort_values("country")

    print("\nMatched FATF grey-list countries in processed dataset:")
    print(grey_list_matches.to_string(index=False))

    return df


# ---------------------------------------------------
# Risk feature construction
# ---------------------------------------------------

def create_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create risk-oriented variables.

    World Bank WGI governance estimates are higher when governance is stronger.
    For risk scoring, these values are inverted so that higher values represent
    higher structural vulnerability.
    """

    df = df.copy()

    df["corruption_risk"] = -df["control_of_corruption"]
    df["rule_of_law_risk"] = -df["rule_of_law"]
    df["political_instability_risk"] = -df["political_stability"]

    # Lower GDP per capita is treated as higher economic vulnerability.
    df["low_income_risk"] = -np.log(df["gdp_per_capita"])

    # Higher inflation and unemployment are treated as economic stress.
    df["inflation_risk"] = df["inflation"]
    df["unemployment_risk"] = df["unemployment"]

    print("\nRisk features created.")

    return df


# ---------------------------------------------------
# Validation
# ---------------------------------------------------

def validate_processed_data(df: pd.DataFrame) -> None:
    """
    Validate that the processed dataset contains the expected columns
    and has no missing values in risk feature columns.
    """

    required_columns = [
        "country",
        "country_code",
        "fatf_match_name",
        "fatf_grey_list",
    ] + REQUIRED_MODEL_COLUMNS + RISK_FEATURES

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Processed dataset is missing required columns: "
            f"{missing_columns}"
        )

    if df.empty:
        raise ValueError("Processed dataset is empty.")

    duplicate_codes = int(df["country_code"].duplicated().sum())

    if duplicate_codes > 0:
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Processed dataset contains duplicate country codes. "
            f"Duplicate count: {duplicate_codes}\n"
            f"{duplicate_df}"
        )

    missing_values = df[RISK_FEATURES].isna().sum()

    if missing_values.sum() > 0:
        raise ValueError(
            "Risk feature columns contain missing values:\n"
            f"{missing_values}"
        )

    fatf_values = sorted(df["fatf_grey_list"].dropna().unique().tolist())

    if fatf_values != [0, 1]:
        raise ValueError(
            "fatf_grey_list must contain binary 0/1 values after processing. "
            f"Found values: {fatf_values}"
        )

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in df.columns
    ]

    if available_year_columns:
        missing_year_values = df[available_year_columns].isna().sum()

        if missing_year_values.sum() > 0:
            raise ValueError(
                "Indicator year columns contain missing values:\n"
                f"{missing_year_values}"
            )

    print("\nProcessed data validation passed.")


# ---------------------------------------------------
# Reporting helpers
# ---------------------------------------------------

def print_indicator_year_summary(df: pd.DataFrame) -> None:
    """
    Print the year distribution for each indicator if year-tracking columns exist.
    """

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in df.columns
    ]

    if not available_year_columns:
        print("\nNo indicator year columns found in processed data.")
        return

    print("\nIndicator year summary after processing:")

    for column in available_year_columns:
        print(f"\n{column}:")
        print(df[column].value_counts().sort_index(ascending=False).head(10))


def print_processed_summary(df: pd.DataFrame) -> None:
    """
    Print summary statistics for the processed dataset.
    """

    print("\nPreview of processed data:")
    print(df.head())

    print("\nProcessed dataset columns:")
    print(df.columns.tolist())

    print("\nProcessed dataset shape:")
    print(df.shape)

    print("\nFATF target distribution:")
    print(df["fatf_grey_list"].value_counts())

    print("\nRisk feature summary:")
    print(df[RISK_FEATURES].describe())


# ---------------------------------------------------
# Output
# ---------------------------------------------------

def save_processed_data(df: pd.DataFrame) -> None:
    """
    Save processed country-level risk data.
    """

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(PROCESSED_COUNTRY_DATA_FILE, index=False)

    print("\nProcessed data saved to:")
    print(PROCESSED_COUNTRY_DATA_FILE)


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the data processing pipeline.
    """

    print("=" * 70)
    print("Processing country risk data")
    print("=" * 70)

    df = load_raw_data()
    df = clean_country_data(df)
    df = add_fatf_target(df)
    df = create_risk_features(df)

    validate_processed_data(df)
    print_processed_summary(df)
    print_indicator_year_summary(df)

    save_processed_data(df)

    print("\nData processing complete.")


if __name__ == "__main__":
    main()