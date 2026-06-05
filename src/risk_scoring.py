"""
Risk scoring module for the terrorism financing OSINT risk model.

This script normalizes risk-oriented features, applies model weights,
creates a country-level terrorism-financing vulnerability score, and
saves ranked country results.

The score is based on the core model indicators only:
- governance weakness
- political instability
- income vulnerability
- inflation stress
- unemployment stress

UCDP conflict, ACLED recent-event signals, sanctions, FATF mutual evaluation,
and regional outputs are treated as supplemental analytical layers in separate
modules. They do not replace the main vulnerability score.
"""

from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from src.config import (
    PROCESSED_COUNTRY_DATA_FILE,
    RISK_RANKINGS_FILE,
    TABLES_DIR,
    RISK_FEATURES,
    SCALED_RISK_FEATURES,
    RISK_SCORE_WEIGHTS,
)


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
# Required output columns
# ---------------------------------------------------

BASE_RANKING_COLUMNS = [
    "risk_rank",
    "country",
    "country_code",
    "tf_vulnerability_score",
    "fatf_grey_list",

    # Original World Bank indicators
    "control_of_corruption",
    "rule_of_law",
    "political_stability",
    "gdp_per_capita",
    "inflation",
    "unemployment",

    # Original risk-oriented variables
    "corruption_risk",
    "rule_of_law_risk",
    "political_instability_risk",
    "low_income_risk",
    "inflation_risk",
    "unemployment_risk",

    # Scaled risk variables
    "corruption_risk_scaled",
    "rule_of_law_risk_scaled",
    "political_instability_risk_scaled",
    "low_income_risk_scaled",
    "inflation_risk_scaled",
    "unemployment_risk_scaled",
]


# ---------------------------------------------------
# Data loading and validation
# ---------------------------------------------------

def load_processed_data() -> pd.DataFrame:
    """
    Load the processed country risk dataset.
    """

    if not PROCESSED_COUNTRY_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Processed country data file not found: {PROCESSED_COUNTRY_DATA_FILE}. "
            "Run src.data_processing before src.risk_scoring."
        )

    df = pd.read_csv(PROCESSED_COUNTRY_DATA_FILE)

    print("Processed data loaded.")
    print(f"Shape: {df.shape}")

    return df


def validate_processed_data(df: pd.DataFrame) -> None:
    """
    Validate that the processed dataset contains the required risk feature columns.
    """

    if df.empty:
        raise ValueError("Processed country data is empty.")

    required_columns = RISK_FEATURES + [
        "country",
        "country_code",
        "fatf_grey_list",
        "control_of_corruption",
        "rule_of_law",
        "political_stability",
        "gdp_per_capita",
        "inflation",
        "unemployment",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Processed data is missing required columns: "
            f"{missing_columns}. Run src.data_processing before src.risk_scoring."
        )

    missing_values = df[RISK_FEATURES].isna().sum()

    if missing_values.sum() > 0:
        raise ValueError(
            "Risk feature columns contain missing values:\n"
            f"{missing_values}"
        )

    duplicate_codes = int(df["country_code"].duplicated().sum())

    if duplicate_codes > 0:
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Processed data contains duplicate country codes. "
            f"Duplicate count: {duplicate_codes}\n"
            f"{duplicate_df}"
        )

    target_values = sorted(df["fatf_grey_list"].dropna().unique().tolist())

    if not set(target_values).issubset({0, 1}):
        raise ValueError(
            "fatf_grey_list must contain only binary 0/1 values. "
            f"Found values: {target_values}"
        )

    print("\nProcessed data validation passed.")


def validate_risk_weights() -> None:
    """
    Validate that risk score weights match the scaled risk features and sum to 1.00.
    """

    missing_weight_features = [
        feature for feature in SCALED_RISK_FEATURES
        if feature not in RISK_SCORE_WEIGHTS
    ]

    extra_weight_features = [
        feature for feature in RISK_SCORE_WEIGHTS
        if feature not in SCALED_RISK_FEATURES
    ]

    if missing_weight_features:
        raise ValueError(
            "Risk score weights are missing scaled feature weights: "
            f"{missing_weight_features}"
        )

    if extra_weight_features:
        raise ValueError(
            "Risk score weights include unknown scaled features: "
            f"{extra_weight_features}"
        )

    total_weight = sum(RISK_SCORE_WEIGHTS.values())

    if round(total_weight, 6) != 1.0:
        raise ValueError(
            "Risk score weights must sum to 1.00. "
            f"Current total: {total_weight}"
        )

    print("\nRisk score weights validation passed.")


# ---------------------------------------------------
# Scoring functions
# ---------------------------------------------------

def normalize_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize risk features to a 0-1 scale.

    Higher values should represent higher risk for every feature.
    """

    df = df.copy()

    scaler = MinMaxScaler()

    scaled_values = scaler.fit_transform(df[RISK_FEATURES])

    scaled_df = pd.DataFrame(
        scaled_values,
        columns=SCALED_RISK_FEATURES,
        index=df.index,
    )

    df = pd.concat([df, scaled_df], axis=1)

    df = validate_scaled_features(df)

    print("\nRisk features normalized.")
    print("Scaled columns created:")
    print(SCALED_RISK_FEATURES)

    return df


def validate_scaled_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate that scaled risk features were created and are within 0-1.

    A small tolerance is allowed because MinMaxScaler can produce values such as
    1.0000000000000002 because of floating-point precision.
    """

    df = df.copy()
    tolerance = 1e-9

    missing_columns = [
        column for column in SCALED_RISK_FEATURES if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Scaled risk features were not created correctly. "
            f"Missing columns: {missing_columns}"
        )

    missing_values = df[SCALED_RISK_FEATURES].isna().sum()

    if missing_values.sum() > 0:
        raise ValueError(
            "Scaled risk features contain missing values:\n"
            f"{missing_values}"
        )

    for column in SCALED_RISK_FEATURES:
        min_value = float(df[column].min())
        max_value = float(df[column].max())

        if min_value < -tolerance or max_value > 1 + tolerance:
            raise ValueError(
                f"Scaled feature {column} contains values outside the 0-1 range. "
                f"Minimum: {min_value}; Maximum: {max_value}"
            )

    # Clip tiny floating-point artifacts back into the expected range.
    df[SCALED_RISK_FEATURES] = df[SCALED_RISK_FEATURES].clip(
        lower=0,
        upper=1,
    )

    print("\nScaled risk feature validation passed.")

    return df


def calculate_vulnerability_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the final terrorism-financing vulnerability score.

    The score is scaled from 0 to 100.
    """

    df = df.copy()

    df["tf_vulnerability_score"] = 0.0

    for feature, weight in RISK_SCORE_WEIGHTS.items():
        df["tf_vulnerability_score"] += df[feature] * weight

    df["tf_vulnerability_score"] = df["tf_vulnerability_score"] * 100

    if df["tf_vulnerability_score"].isna().any():
        raise ValueError("tf_vulnerability_score contains missing values.")

    below_zero = int((df["tf_vulnerability_score"] < 0).sum())
    above_100 = int((df["tf_vulnerability_score"] > 100).sum())

    if below_zero > 0 or above_100 > 0:
        raise ValueError(
            "tf_vulnerability_score must be between 0 and 100. "
            f"Below zero: {below_zero}; Above 100: {above_100}"
        )

    print("\nTerrorism-financing vulnerability score calculated.")

    return df


# ---------------------------------------------------
# Ranking output
# ---------------------------------------------------

def get_ranking_columns(df: pd.DataFrame) -> list[str]:
    """
    Build the final ranking column list.

    Indicator year columns are included when available.
    """

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in df.columns
    ]

    return BASE_RANKING_COLUMNS + available_year_columns


def create_country_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort countries by terrorism-financing vulnerability score.
    """

    ranked_df = df.sort_values(
        "tf_vulnerability_score",
        ascending=False,
    ).reset_index(drop=True)

    ranked_df["risk_rank"] = ranked_df.index + 1

    ranking_columns = get_ranking_columns(ranked_df)

    missing_columns = [
        column for column in ranking_columns if column not in ranked_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Ranked dataset is missing expected output columns: "
            f"{missing_columns}"
        )

    ranked_df = ranked_df[ranking_columns]

    validate_rankings_output(ranked_df)

    print("\nCountry rankings created.")

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in ranked_df.columns
    ]

    if available_year_columns:
        print("Indicator year columns preserved:")
        print(available_year_columns)

    return ranked_df


def validate_rankings_output(df: pd.DataFrame) -> None:
    """
    Validate the final rankings output before saving.
    """

    if df.empty:
        raise ValueError("Risk rankings output is empty.")

    required_columns = BASE_RANKING_COLUMNS

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings output is missing required columns: "
            f"{missing_columns}"
        )

    if df["risk_rank"].duplicated().any():
        raise ValueError("risk_rank contains duplicate values.")

    if df["country_code"].duplicated().any():
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["risk_rank", "country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Risk rankings output contains duplicate country codes:\n"
            f"{duplicate_df}"
        )

    if df["tf_vulnerability_score"].isna().any():
        raise ValueError("tf_vulnerability_score contains missing values.")

    if not df["tf_vulnerability_score"].between(0, 100).all():
        raise ValueError(
            "tf_vulnerability_score should be scaled between 0 and 100."
        )

    if not df["risk_rank"].is_monotonic_increasing:
        raise ValueError("risk_rank should be monotonic increasing.")

    sorted_scores = df["tf_vulnerability_score"].sort_values(
        ascending=False,
    ).reset_index(drop=True)

    current_scores = df["tf_vulnerability_score"].reset_index(drop=True)

    if not current_scores.equals(sorted_scores):
        raise ValueError(
            "Risk rankings output is not sorted by vulnerability score descending."
        )

    print("\nRisk rankings output validation passed.")


def save_rankings(df: pd.DataFrame) -> None:
    """
    Save the ranked country risk output.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(RISK_RANKINGS_FILE, index=False)

    print("\nRisk rankings saved to:")
    print(RISK_RANKINGS_FILE)


# ---------------------------------------------------
# Console summary
# ---------------------------------------------------

def print_risk_scoring_summary(ranked_df: pd.DataFrame) -> None:
    """
    Print a concise scoring summary to the console.
    """

    print("\nTop 20 countries by vulnerability score:")
    print(
        ranked_df[
            [
                "risk_rank",
                "country",
                "tf_vulnerability_score",
                "fatf_grey_list",
            ]
        ].head(20)
    )

    print("\nScore summary:")
    print(ranked_df["tf_vulnerability_score"].describe())

    print("\nFATF grey-list count in rankings:")
    print(int(ranked_df["fatf_grey_list"].sum()))

    print("\nRisk feature weight summary:")
    for feature, weight in RISK_SCORE_WEIGHTS.items():
        print(f"{feature}: {weight:.2%}")


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the risk scoring pipeline.
    """

    print("=" * 70)
    print("Creating terrorism-financing vulnerability risk scores")
    print("=" * 70)

    df = load_processed_data()

    validate_processed_data(df)
    validate_risk_weights()

    df = normalize_risk_features(df)
    df = calculate_vulnerability_score(df)
    ranked_df = create_country_rankings(df)

    print_risk_scoring_summary(ranked_df)

    save_rankings(ranked_df)

    print("\nRisk scoring complete.")


if __name__ == "__main__":
    main()