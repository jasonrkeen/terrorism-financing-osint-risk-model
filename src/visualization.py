"""
Visualization module for the terrorism financing OSINT risk model.

This script creates charts and correlation outputs from the final
country risk rankings dataset and enhanced-analysis tables.

Some expanded-project charts are created by supplemental modules:
- src.conflict_data_supplement creates the conflict fatalities chart.
- src.additional_risk_factors creates regional and current FATF comparison charts.

This module creates the core model charts and verifies whether the supplemental
chart outputs are present.
"""

from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from src.config import (
    RISK_RANKINGS_FILE,
    CORRELATION_MATRIX_FILE,
    TOP_15_RISK_CHART_FILE,
    RISK_SCORE_PROBABILITY_CHART_FILE,
    GREY_LIST_PROBABILITY_TOP_20_CHART_FILE,
    RISK_TIER_SUMMARY_FILE,
    RISK_TIER_DISTRIBUTION_CHART_FILE,
    SENSITIVITY_OVERLAP_FILE,
    SENSITIVITY_OVERLAP_CHART_FILE,
    TOP_15_CONFLICT_FATALITIES_CHART_FILE,
    REGIONAL_AVERAGE_RISK_CHART_FILE,
    REGIONAL_FATF_COUNT_CHART_FILE,
    CURRENT_FATF_STATUS_COMPARISON_CHART_FILE,
    CHARTS_DIR,
    TABLES_DIR,
    SCALED_RISK_FEATURES,
)


# ---------------------------------------------------
# Optional indicator year columns
# ---------------------------------------------------

INDICATOR_YEAR_COLUMNS = [
    "control_of_corruption_year",
    "rule_of_law_year",
    "political_stability_year",
    "gdp_per_capita_year",
    "inflation_year",
    "unemployment_year",
]


# ---------------------------------------------------
# Data loading and validation
# ---------------------------------------------------

def load_rankings() -> pd.DataFrame:
    """
    Load the final country risk rankings dataset.
    """

    if not RISK_RANKINGS_FILE.exists():
        raise FileNotFoundError(
            f"Risk rankings file not found: {RISK_RANKINGS_FILE}. "
            "Run src.risk_scoring and src.modeling before src.visualization."
        )

    df = pd.read_csv(RISK_RANKINGS_FILE)

    print("Risk rankings loaded.")
    print(f"Shape: {df.shape}")

    return df


def validate_visualization_data(df: pd.DataFrame) -> None:
    """
    Validate that the rankings dataset contains the required visualization columns.
    """

    if df.empty:
        raise ValueError("Risk rankings file is empty.")

    required_columns = SCALED_RISK_FEATURES + [
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
            "Risk rankings file is missing required visualization columns: "
            f"{missing_columns}. Run the main pipeline through src.modeling "
            "before running src.visualization."
        )

    missing_values = df[required_columns].isna().sum()

    if missing_values.sum() > 0:
        raise ValueError(
            "Visualization columns contain missing values:\n"
            f"{missing_values}"
        )

    duplicate_codes = int(df["country_code"].duplicated().sum())

    if duplicate_codes > 0:
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Risk rankings file contains duplicate country codes. "
            f"Duplicate count: {duplicate_codes}\n"
            f"{duplicate_df}"
        )

    if not df["tf_vulnerability_score"].between(0, 100).all():
        raise ValueError("tf_vulnerability_score must be between 0 and 100.")

    if not df["predicted_grey_list_probability"].between(0, 1).all():
        raise ValueError(
            "predicted_grey_list_probability must be between 0 and 1."
        )

    target_values = sorted(df["fatf_grey_list"].dropna().unique().tolist())

    if not set(target_values).issubset({0, 1}):
        raise ValueError(
            "fatf_grey_list must contain only binary 0/1 values. "
            f"Found values: {target_values}"
        )

    print("\nVisualization data validation passed.")


def print_indicator_year_summary(df: pd.DataFrame) -> None:
    """
    Print year distributions for indicator year columns when available.
    """

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in df.columns
    ]

    if not available_year_columns:
        print("\nNo indicator year columns found in rankings file.")
        return

    print("\nIndicator year summary in rankings file:")

    for column in available_year_columns:
        print(f"\n{column}:")
        print(df[column].value_counts().sort_index(ascending=False).head(10))


# ---------------------------------------------------
# Core model charts
# ---------------------------------------------------

def save_top_15_risk_score_chart(df: pd.DataFrame) -> None:
    """
    Save a horizontal bar chart of the top 15 countries by vulnerability score.
    """

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    top_15 = df.sort_values(
        "tf_vulnerability_score",
        ascending=False,
    ).head(15)

    plt.figure(figsize=(12, 7))
    plt.barh(top_15["country"], top_15["tf_vulnerability_score"])
    plt.gca().invert_yaxis()
    plt.title("Top 15 Countries by Terrorism-Financing Vulnerability Score")
    plt.xlabel("Vulnerability Score, 0-100")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(TOP_15_RISK_CHART_FILE, dpi=300)
    plt.close()

    print("Saved chart:")
    print(TOP_15_RISK_CHART_FILE)


def save_risk_score_probability_chart(df: pd.DataFrame) -> None:
    """
    Save a scatter plot comparing vulnerability score and predicted grey-list probability.
    """

    plt.figure(figsize=(9, 6))
    plt.scatter(
        df["tf_vulnerability_score"],
        df["predicted_grey_list_probability"],
    )
    plt.title("Risk Score vs Predicted FATF Grey-List Probability")
    plt.xlabel("Terrorism-Financing Vulnerability Score")
    plt.ylabel("Predicted Grey-List Probability")
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.tight_layout()
    plt.savefig(RISK_SCORE_PROBABILITY_CHART_FILE, dpi=300)
    plt.close()

    print("Saved chart:")
    print(RISK_SCORE_PROBABILITY_CHART_FILE)


def save_top_20_probability_chart(df: pd.DataFrame) -> None:
    """
    Save a horizontal bar chart of the top 20 countries by predicted grey-list probability.
    """

    top_20 = df.sort_values(
        "predicted_grey_list_probability",
        ascending=False,
    ).head(20)

    plt.figure(figsize=(12, 8))
    plt.barh(top_20["country"], top_20["predicted_grey_list_probability"])
    plt.gca().invert_yaxis()
    plt.gca().xaxis.set_major_formatter(PercentFormatter(1.0))
    plt.title("Top 20 Countries by Predicted FATF Grey-List Probability")
    plt.xlabel("Predicted Probability")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(GREY_LIST_PROBABILITY_TOP_20_CHART_FILE, dpi=300)
    plt.close()

    print("Saved chart:")
    print(GREY_LIST_PROBABILITY_TOP_20_CHART_FILE)


def save_risk_tier_distribution_chart() -> None:
    """
    Save a bar chart showing the number of countries in each risk tier.
    """

    if not RISK_TIER_SUMMARY_FILE.exists():
        print("Risk tier summary file not found. Skipping risk-tier chart.")
        return

    tier_df = pd.read_csv(RISK_TIER_SUMMARY_FILE)

    required_columns = ["risk_tier", "country_count"]

    missing_columns = [
        column for column in required_columns if column not in tier_df.columns
    ]

    if missing_columns:
        print(
            "Risk tier summary file is missing required columns. "
            f"Skipping risk-tier chart: {missing_columns}"
        )
        return

    tier_order = ["Very High", "High", "Moderate", "Low", "Very Low"]

    tier_df["risk_tier"] = pd.Categorical(
        tier_df["risk_tier"],
        categories=tier_order,
        ordered=True,
    )

    tier_df = tier_df.sort_values("risk_tier")

    plt.figure(figsize=(9, 6))
    plt.bar(tier_df["risk_tier"].astype(str), tier_df["country_count"])
    plt.title("Country Count by Risk Tier")
    plt.xlabel("Risk Tier")
    plt.ylabel("Number of Countries")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(RISK_TIER_DISTRIBUTION_CHART_FILE, dpi=300)
    plt.close()

    print("Saved chart:")
    print(RISK_TIER_DISTRIBUTION_CHART_FILE)


def save_sensitivity_overlap_chart() -> None:
    """
    Save a bar chart showing top-20 overlap by sensitivity scenario.
    """

    if not SENSITIVITY_OVERLAP_FILE.exists():
        print("Sensitivity overlap file not found. Skipping sensitivity chart.")
        return

    overlap_df = pd.read_csv(SENSITIVITY_OVERLAP_FILE)

    required_columns = ["scenario", "overlap_percentage"]

    missing_columns = [
        column for column in required_columns if column not in overlap_df.columns
    ]

    if missing_columns:
        print(
            "Sensitivity overlap file is missing required columns. "
            f"Skipping sensitivity chart: {missing_columns}"
        )
        return

    overlap_df["scenario_label"] = (
        overlap_df["scenario"]
        .astype(str)
        .str.replace("_", " ", regex=False)
        .str.title()
    )

    plt.figure(figsize=(10, 6))
    plt.bar(overlap_df["scenario_label"], overlap_df["overlap_percentage"])
    plt.title("Top-20 Ranking Overlap by Sensitivity Scenario")
    plt.xlabel("Scenario")
    plt.ylabel("Overlap with Baseline Top 20")
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(SENSITIVITY_OVERLAP_CHART_FILE, dpi=300)
    plt.close()

    print("Saved chart:")
    print(SENSITIVITY_OVERLAP_CHART_FILE)


# ---------------------------------------------------
# Correlation output
# ---------------------------------------------------

def save_correlation_matrix(df: pd.DataFrame) -> None:
    """
    Save a correlation matrix for model features and target variables.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    columns = SCALED_RISK_FEATURES + [
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
    ]

    missing_columns = [
        column for column in columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Cannot create correlation matrix. Missing columns: "
            f"{missing_columns}"
        )

    corr = df[columns].corr()

    corr.to_csv(CORRELATION_MATRIX_FILE)

    print("Saved correlation matrix:")
    print(CORRELATION_MATRIX_FILE)

    print("\nCorrelation matrix:")
    print(corr)


# ---------------------------------------------------
# Supplemental chart checks
# ---------------------------------------------------

def verify_supplemental_charts() -> None:
    """
    Print whether supplemental charts from other modules are available.

    These charts are generated outside this module:
    - src.conflict_data_supplement
    - src.additional_risk_factors
    """

    supplemental_charts = [
        (
            TOP_15_CONFLICT_FATALITIES_CHART_FILE,
            "Top 15 conflict fatalities chart",
        ),
        (
            REGIONAL_AVERAGE_RISK_CHART_FILE,
            "Regional average risk chart",
        ),
        (
            REGIONAL_FATF_COUNT_CHART_FILE,
            "Regional FATF count chart",
        ),
        (
            CURRENT_FATF_STATUS_COMPARISON_CHART_FILE,
            "Current FATF status comparison chart",
        ),
    ]

    print("\nSupplemental chart check:")

    for chart_path, label in supplemental_charts:
        if chart_path.exists():
            print(f"Found {label}:")
            print(chart_path)
        else:
            print(f"Missing {label}:")
            print(chart_path)
            print(
                "Run the relevant supplemental module or the full main.py pipeline "
                "to create this chart."
            )


# ---------------------------------------------------
# Output validation
# ---------------------------------------------------

def validate_visualization_outputs() -> None:
    """
    Validate that the core visualization outputs were created.
    """

    expected_outputs = [
        TOP_15_RISK_CHART_FILE,
        RISK_SCORE_PROBABILITY_CHART_FILE,
        GREY_LIST_PROBABILITY_TOP_20_CHART_FILE,
        CORRELATION_MATRIX_FILE,
    ]

    optional_outputs = [
        RISK_TIER_DISTRIBUTION_CHART_FILE,
        SENSITIVITY_OVERLAP_CHART_FILE,
    ]

    missing_required = [
        output_path for output_path in expected_outputs if not output_path.exists()
    ]

    if missing_required:
        raise FileNotFoundError(
            "Visualization did not create the expected required outputs: "
            f"{missing_required}"
        )

    print("\nCore visualization output validation passed.")

    missing_optional = [
        output_path for output_path in optional_outputs if not output_path.exists()
    ]

    if missing_optional:
        print("\nOptional visualization outputs were not created:")
        for output_path in missing_optional:
            print(output_path)
        print(
            "This usually means enhanced_analysis.py has not been run yet. "
            "Run src.enhanced_analysis or the full main.py pipeline to create them."
        )
    else:
        print("Optional enhanced-analysis chart outputs are present.")


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run all visualizations.
    """

    print("=" * 70)
    print("Creating visualizations")
    print("=" * 70)

    df = load_rankings()

    validate_visualization_data(df)
    print_indicator_year_summary(df)

    save_top_15_risk_score_chart(df)
    save_risk_score_probability_chart(df)
    save_top_20_probability_chart(df)
    save_risk_tier_distribution_chart()
    save_sensitivity_overlap_chart()
    save_correlation_matrix(df)
    verify_supplemental_charts()
    validate_visualization_outputs()

    print("\nVisualization complete.")


if __name__ == "__main__":
    main()