"""
Enhanced analysis module for the terrorism financing OSINT risk model.

This script expands the core model analysis by adding:
1. Risk tier classification
2. False positive and false negative analysis
3. Model performance summary
4. Sensitivity analysis across alternate weighting scenarios

The outputs are saved to outputs/tables/.

Conflict, sanctions, FATF mutual evaluation, and regional outputs are handled
as supplemental analytical layers in separate modules.
"""

from __future__ import annotations

import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import (
    RISK_RANKINGS_FILE,
    TABLES_DIR,
    SCALED_RISK_FEATURES,
    SENSITIVITY_SCENARIOS,
    RISK_TIER_SUMMARY_FILE,
    RISK_TIER_COUNTRY_FILE,
    MODEL_PERFORMANCE_FILE,
    CONFUSION_MATRIX_FILE,
    CLASSIFICATION_REPORT_FILE,
    FALSE_POSITIVES_FILE,
    FALSE_NEGATIVES_FILE,
    SENSITIVITY_RANKINGS_FILE,
    SENSITIVITY_TOP_20_FILE,
    SENSITIVITY_OVERLAP_FILE,
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
            "Run risk_scoring.py and modeling.py first."
        )

    df = pd.read_csv(RISK_RANKINGS_FILE)

    print("Risk rankings loaded.")
    print(f"Shape: {df.shape}")

    return df


def validate_enhanced_analysis_data(df: pd.DataFrame) -> None:
    """
    Validate that the rankings dataset contains the required columns.
    """

    required_columns = SCALED_RISK_FEATURES + [
        "country",
        "country_code",
        "risk_rank",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required enhanced-analysis columns: "
            f"{missing_columns}. Run the main pipeline through src.modeling first."
        )

    if df.empty:
        raise ValueError("Risk rankings file is empty.")

    missing_values = df[required_columns].isna().sum()

    if missing_values.sum() > 0:
        raise ValueError(
            "Enhanced-analysis columns contain missing values:\n"
            f"{missing_values}"
        )

    target_values = sorted(df["fatf_grey_list"].unique().tolist())

    if target_values != [0, 1]:
        raise ValueError(
            "fatf_grey_list must be a binary 0/1 column. "
            f"Found values: {target_values}"
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

    print("\nEnhanced analysis data validation passed.")


# ---------------------------------------------------
# Risk tier analysis
# ---------------------------------------------------

def assign_risk_tier(score: float) -> str:
    """
    Assign a qualitative risk tier based on the vulnerability score.
    """

    if score >= 70:
        return "Very High"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Moderate"
    if score >= 20:
        return "Low"

    return "Very Low"


def add_risk_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a risk tier column to the country rankings dataset.
    """

    df = df.copy()

    df["risk_tier"] = df["tf_vulnerability_score"].apply(assign_risk_tier)

    print("\nRisk tiers added.")

    return df


def save_risk_tier_outputs(df: pd.DataFrame) -> None:
    """
    Save country-level risk tiers and tier summary.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    tier_order = ["Very High", "High", "Moderate", "Low", "Very Low"]

    tier_summary = (
        df.groupby("risk_tier")
        .agg(
            country_count=("country", "count"),
            average_score=("tf_vulnerability_score", "mean"),
            median_score=("tf_vulnerability_score", "median"),
            min_score=("tf_vulnerability_score", "min"),
            max_score=("tf_vulnerability_score", "max"),
            average_predicted_probability=(
                "predicted_grey_list_probability",
                "mean",
            ),
            fatf_grey_list_count=("fatf_grey_list", "sum"),
        )
        .reindex(tier_order)
        .reset_index()
    )

    count_columns = [
        "country_count",
        "fatf_grey_list_count",
    ]

    for column in count_columns:
        tier_summary[column] = tier_summary[column].fillna(0).astype(int)

    numeric_columns = [
        "average_score",
        "median_score",
        "min_score",
        "max_score",
        "average_predicted_probability",
    ]

    for column in numeric_columns:
        tier_summary[column] = pd.to_numeric(
            tier_summary[column],
            errors="coerce",
        ).round(4)

    country_columns = [
        "risk_rank",
        "country",
        "country_code",
        "risk_tier",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
    ]

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in df.columns
    ]

    country_columns = country_columns + available_year_columns

    df[country_columns].to_csv(RISK_TIER_COUNTRY_FILE, index=False)
    tier_summary.to_csv(RISK_TIER_SUMMARY_FILE, index=False)

    print("Risk tier country rankings saved to:")
    print(RISK_TIER_COUNTRY_FILE)

    print("Risk tier summary saved to:")
    print(RISK_TIER_SUMMARY_FILE)


# ---------------------------------------------------
# Model performance analysis
# ---------------------------------------------------

def run_model_performance_analysis(df: pd.DataFrame) -> None:
    """
    Re-run the classification model and save model performance outputs.

    The settings match src.modeling so that performance summaries remain
    consistent across the project.
    """

    X = df[SCALED_RISK_FEATURES]
    y = df["fatf_grey_list"]

    class_counts = y.value_counts()

    if len(class_counts) < 2:
        raise ValueError(
            "Model performance analysis requires both FATF and non-FATF classes."
        )

    if class_counts.min() < 2:
        raise ValueError(
            "Model performance analysis requires at least two observations "
            "in each class for stratified train/test splitting."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "logistic_regression",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    performance = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision_class_1": precision_score(y_test, y_pred, zero_division=0),
        "recall_class_1": recall_score(y_test, y_pred, zero_division=0),
        "f1_class_1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "test_set_size": len(y_test),
        "positive_cases_in_test_set": int(y_test.sum()),
        "negative_cases_in_test_set": int((y_test == 0).sum()),
        "positive_cases_total": int(y.sum()),
        "negative_cases_total": int((y == 0).sum()),
    }

    performance_df = pd.DataFrame(
        list(performance.items()),
        columns=["metric", "value"],
    )

    confusion = confusion_matrix(y_test, y_pred)

    confusion_df = pd.DataFrame(
        confusion,
        index=["Actual 0", "Actual 1"],
        columns=["Predicted 0", "Predicted 1"],
    )

    report_df = pd.DataFrame(
        classification_report(
            y_test,
            y_pred,
            output_dict=True,
            zero_division=0,
        )
    ).transpose()

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    performance_df.to_csv(MODEL_PERFORMANCE_FILE, index=False)
    confusion_df.to_csv(CONFUSION_MATRIX_FILE)
    report_df.to_csv(CLASSIFICATION_REPORT_FILE)

    print("\nModel performance summary saved to:")
    print(MODEL_PERFORMANCE_FILE)

    print("Confusion matrix saved to:")
    print(CONFUSION_MATRIX_FILE)

    print("Classification report saved to:")
    print(CLASSIFICATION_REPORT_FILE)


# ---------------------------------------------------
# False positive and false negative analysis
# ---------------------------------------------------

def save_false_positive_negative_outputs(
    df: pd.DataFrame,
    threshold: float = 0.50,
) -> None:
    """
    Save false positive and false negative country lists.

    False positive:
        Model probability is above threshold, but country is not FATF grey-listed.

    False negative:
        Model probability is below threshold, but country is FATF grey-listed.
    """

    df = df.copy()

    df["predicted_class"] = (
        df["predicted_grey_list_probability"] >= threshold
    ).astype(int)

    false_positives = df[
        (df["predicted_class"] == 1) & (df["fatf_grey_list"] == 0)
    ].sort_values("predicted_grey_list_probability", ascending=False)

    false_negatives = df[
        (df["predicted_class"] == 0) & (df["fatf_grey_list"] == 1)
    ].sort_values("predicted_grey_list_probability", ascending=True)

    base_output_columns = [
        "country",
        "country_code",
        "risk_rank",
        "risk_tier",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
        "predicted_class",
        "control_of_corruption",
        "rule_of_law",
        "political_stability",
        "gdp_per_capita",
        "inflation",
        "unemployment",
    ]

    available_output_columns = [
        column for column in base_output_columns if column in df.columns
    ]

    available_year_columns = [
        column for column in INDICATOR_YEAR_COLUMNS if column in df.columns
    ]

    output_columns = available_output_columns + available_year_columns

    false_positives[output_columns].to_csv(FALSE_POSITIVES_FILE, index=False)
    false_negatives[output_columns].to_csv(FALSE_NEGATIVES_FILE, index=False)

    print("\nFalse positives saved to:")
    print(FALSE_POSITIVES_FILE)
    print(f"False positives: {len(false_positives)}")

    print("False negatives saved to:")
    print(FALSE_NEGATIVES_FILE)
    print(f"False negatives: {len(false_negatives)}")


# ---------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------

def validate_sensitivity_scenarios() -> None:
    """
    Validate that all sensitivity scenarios use known scaled features
    and have weights that sum to 1.00.
    """

    if not SENSITIVITY_SCENARIOS:
        raise ValueError("SENSITIVITY_SCENARIOS cannot be empty.")

    for scenario_name, weights in SENSITIVITY_SCENARIOS.items():
        missing_features = [
            feature for feature in SCALED_RISK_FEATURES
            if feature not in weights
        ]

        extra_features = [
            feature for feature in weights
            if feature not in SCALED_RISK_FEATURES
        ]

        if missing_features:
            raise ValueError(
                f"Sensitivity scenario '{scenario_name}' is missing weights "
                f"for: {missing_features}"
            )

        if extra_features:
            raise ValueError(
                f"Sensitivity scenario '{scenario_name}' contains unknown "
                f"features: {extra_features}"
            )

        total_weight = sum(weights.values())

        if round(total_weight, 6) != 1.0:
            raise ValueError(
                f"Sensitivity scenario '{scenario_name}' weights must sum to "
                f"1.00. Current total: {total_weight}"
            )


def calculate_scenario_score(
    df: pd.DataFrame,
    scenario_name: str,
    weights: dict,
) -> pd.DataFrame:
    """
    Calculate a risk score for a single weighting scenario.
    """

    scenario_df = df.copy()

    score_column = f"{scenario_name}_score"
    rank_column = f"{scenario_name}_rank"

    scenario_df[score_column] = 0.0

    for feature, weight in weights.items():
        scenario_df[score_column] += scenario_df[feature] * weight

    scenario_df[score_column] = scenario_df[score_column] * 100

    scenario_df = scenario_df.sort_values(
        score_column,
        ascending=False,
    ).reset_index(drop=True)

    scenario_df[rank_column] = scenario_df.index + 1

    return scenario_df[
        [
            "country",
            "country_code",
            "fatf_grey_list",
            "tf_vulnerability_score",
            "predicted_grey_list_probability",
            score_column,
            rank_column,
        ]
    ]


def run_sensitivity_analysis(df: pd.DataFrame) -> None:
    """
    Run sensitivity analysis across alternative weighting scenarios.
    """

    validate_sensitivity_scenarios()

    scenario_frames = []

    for scenario_name, weights in SENSITIVITY_SCENARIOS.items():
        scenario_df = calculate_scenario_score(
            df=df,
            scenario_name=scenario_name,
            weights=weights,
        )

        scenario_frames.append(scenario_df)

    if not scenario_frames:
        raise ValueError("No sensitivity scenario outputs were created.")

    sensitivity_df = scenario_frames[0]

    for scenario_df in scenario_frames[1:]:
        sensitivity_df = sensitivity_df.merge(
            scenario_df,
            on=[
                "country",
                "country_code",
                "fatf_grey_list",
                "tf_vulnerability_score",
                "predicted_grey_list_probability",
            ],
            how="outer",
        )

    if "baseline_rank" not in sensitivity_df.columns:
        raise ValueError(
            "Sensitivity analysis requires a 'baseline' scenario that creates "
            "baseline_rank. Add a baseline scenario to SENSITIVITY_SCENARIOS."
        )

    sensitivity_df = sensitivity_df.sort_values(
        "baseline_rank",
        ascending=True,
    ).reset_index(drop=True)

    sensitivity_df.to_csv(SENSITIVITY_RANKINGS_FILE, index=False)

    top_20_rows = []

    for scenario_name in SENSITIVITY_SCENARIOS:
        score_column = f"{scenario_name}_score"
        rank_column = f"{scenario_name}_rank"

        scenario_top_20 = sensitivity_df.sort_values(rank_column).head(20)

        for _, row in scenario_top_20.iterrows():
            top_20_rows.append(
                {
                    "scenario": scenario_name,
                    "rank": int(row[rank_column]),
                    "country": row["country"],
                    "country_code": row["country_code"],
                    "scenario_score": row[score_column],
                    "baseline_score": row["tf_vulnerability_score"],
                    "fatf_grey_list": row["fatf_grey_list"],
                    "predicted_grey_list_probability": row[
                        "predicted_grey_list_probability"
                    ],
                }
            )

    sensitivity_top_20_df = pd.DataFrame(top_20_rows)
    sensitivity_top_20_df.to_csv(SENSITIVITY_TOP_20_FILE, index=False)

    overlap_summary = []

    baseline_top_20 = set(
        sensitivity_df.sort_values("baseline_rank").head(20)["country"]
    )

    for scenario_name in SENSITIVITY_SCENARIOS:
        rank_column = f"{scenario_name}_rank"

        scenario_top_20 = set(
            sensitivity_df.sort_values(rank_column).head(20)["country"]
        )

        overlap_count = len(baseline_top_20.intersection(scenario_top_20))

        overlap_summary.append(
            {
                "scenario": scenario_name,
                "top_20_overlap_with_baseline": overlap_count,
                "baseline_top_20_count": 20,
                "overlap_percentage": overlap_count / 20,
            }
        )

    overlap_df = pd.DataFrame(overlap_summary)
    overlap_df.to_csv(SENSITIVITY_OVERLAP_FILE, index=False)

    print("\nSensitivity rankings saved to:")
    print(SENSITIVITY_RANKINGS_FILE)

    print("Sensitivity top 20 by scenario saved to:")
    print(SENSITIVITY_TOP_20_FILE)

    print("Sensitivity overlap summary saved to:")
    print(SENSITIVITY_OVERLAP_FILE)


# ---------------------------------------------------
# Output validation
# ---------------------------------------------------

def validate_enhanced_outputs() -> None:
    """
    Validate that key enhanced-analysis outputs were created.
    """

    expected_files = [
        RISK_TIER_SUMMARY_FILE,
        RISK_TIER_COUNTRY_FILE,
        MODEL_PERFORMANCE_FILE,
        CONFUSION_MATRIX_FILE,
        CLASSIFICATION_REPORT_FILE,
        FALSE_POSITIVES_FILE,
        FALSE_NEGATIVES_FILE,
        SENSITIVITY_RANKINGS_FILE,
        SENSITIVITY_TOP_20_FILE,
        SENSITIVITY_OVERLAP_FILE,
    ]

    missing_files = [
        file_path for file_path in expected_files if not file_path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Enhanced analysis did not create the expected output files: "
            f"{missing_files}"
        )

    print("\nEnhanced analysis output validation passed.")


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the enhanced analysis workflow.
    """

    print("=" * 70)
    print("Running enhanced terrorism-financing risk analysis")
    print("=" * 70)

    df = load_rankings()

    validate_enhanced_analysis_data(df)

    df = add_risk_tiers(df)

    save_risk_tier_outputs(df)
    run_model_performance_analysis(df)
    save_false_positive_negative_outputs(df)
    run_sensitivity_analysis(df)
    validate_enhanced_outputs()

    print("\nEnhanced analysis complete.")


if __name__ == "__main__":
    main()