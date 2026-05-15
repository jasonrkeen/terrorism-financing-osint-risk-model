"""
Modeling module for the terrorism financing OSINT risk model.

This script uses the scaled core risk indicators to model FATF grey-list status.
It includes both a statsmodels logistic regression summary and a scikit-learn
classification model.

The model uses the core vulnerability indicators only:
- corruption risk
- rule of law risk
- political instability risk
- low income risk
- inflation risk
- unemployment risk

Conflict, sanctions, FATF mutual evaluation, and regional outputs are treated
as supplemental analytical layers in separate modules. They are not used as
predictors in this core model.
"""

from __future__ import annotations

import pandas as pd
import statsmodels.api as sm

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import (
    RISK_RANKINGS_FILE,
    LOGIT_SUMMARY_FILE,
    REPORTS_DIR,
    SCALED_RISK_FEATURES,
)


# ---------------------------------------------------
# Data loading and validation
# ---------------------------------------------------

def load_ranked_data() -> pd.DataFrame:
    """
    Load the country risk rankings dataset.
    """

    if not RISK_RANKINGS_FILE.exists():
        raise FileNotFoundError(
            f"Risk rankings file not found: {RISK_RANKINGS_FILE}. "
            "Run src.risk_scoring before src.modeling."
        )

    df = pd.read_csv(RISK_RANKINGS_FILE)

    print("Risk rankings data loaded.")
    print(f"Shape: {df.shape}")

    print("\nAvailable columns:")
    print(df.columns.tolist())

    return df


def validate_modeling_data(df: pd.DataFrame) -> None:
    """
    Validate that the rankings dataset contains the required modeling columns.
    """

    required_columns = SCALED_RISK_FEATURES + [
        "fatf_grey_list",
        "country",
        "country_code",
        "tf_vulnerability_score",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required modeling columns: "
            f"{missing_columns}. Run src.risk_scoring before src.modeling."
        )

    if df.empty:
        raise ValueError("Risk rankings dataset is empty.")

    missing_values = df[required_columns].isna().sum()

    if missing_values.sum() > 0:
        raise ValueError(
            "Modeling columns contain missing values:\n"
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

    positive_count = int(df["fatf_grey_list"].sum())
    negative_count = int((df["fatf_grey_list"] == 0).sum())

    if positive_count < 2:
        raise ValueError(
            "Not enough positive FATF grey-list cases to run the model."
        )

    if negative_count < 2:
        raise ValueError(
            "Not enough negative FATF grey-list cases to run the model."
        )

    print("\nModeling data validation passed.")
    print(f"Positive FATF grey-list cases: {positive_count}")
    print(f"Negative FATF grey-list cases: {negative_count}")


def validate_class_balance_for_split(y: pd.Series) -> None:
    """
    Validate that the target variable can support stratified train/test split.
    """

    class_counts = y.value_counts()

    if len(class_counts) < 2:
        raise ValueError(
            "Modeling requires both FATF and non-FATF classes."
        )

    if class_counts.min() < 2:
        raise ValueError(
            "Modeling requires at least two observations in each class "
            "for stratified train/test splitting."
        )


# ---------------------------------------------------
# Statsmodels logistic regression
# ---------------------------------------------------

def run_statsmodels_logit(df: pd.DataFrame):
    """
    Run a statsmodels logistic regression.

    Dependent variable:
        fatf_grey_list

    Independent variables:
        scaled risk indicators from SCALED_RISK_FEATURES

    Returns
    -------
    statsmodels result or None
        Returns None if statsmodels fails because of convergence, separation,
        multicollinearity, or another numerical issue. The scikit-learn model
        still runs afterward.
    """

    X = df[SCALED_RISK_FEATURES]
    y = df["fatf_grey_list"]

    X = sm.add_constant(X)

    try:
        logit_model = sm.Logit(y, X).fit(disp=False)
    except Exception as error:
        print("\nStatsmodels logistic regression failed.")
        print(f"Reason: {error}")
        return None

    print("\nStatsmodels logistic regression complete.")
    print(logit_model.summary())

    return logit_model


def save_logit_summary(logit_model) -> None:
    """
    Save the logistic regression summary to a text file.

    If the statsmodels model fails, write a clear note instead of stopping
    the full pipeline.
    """

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(LOGIT_SUMMARY_FILE, "w", encoding="utf-8") as file:
        if logit_model is None:
            file.write(
                "Statsmodels logistic regression summary was not available.\n\n"
                "The statsmodels Logit model may have failed because of one "
                "or more numerical issues, such as class imbalance, "
                "quasi-separation, multicollinearity, or limited positive "
                "FATF grey-list cases.\n\n"
                "This does not prevent the project from producing model "
                "probabilities. The scikit-learn logistic regression model "
                "still runs with class_weight='balanced' and provides "
                "predicted FATF grey-list probabilities in the rankings file.\n"
            )
        else:
            file.write(logit_model.summary().as_text())

    print("\nLogistic regression summary saved to:")
    print(LOGIT_SUMMARY_FILE)


# ---------------------------------------------------
# Scikit-learn logistic model
# ---------------------------------------------------

def run_sklearn_logistic_model(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run a scikit-learn logistic classification model.

    The model uses class_weight='balanced' because FATF grey-listed countries
    are a small minority of the dataset.
    """

    X = df[SCALED_RISK_FEATURES]
    y = df["fatf_grey_list"]

    validate_class_balance_for_split(y)

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

    print("\nScikit-learn logistic classification results:")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nROC AUC:")
    print(roc_auc_score(y_test, y_prob))

    df = df.copy()
    df["predicted_grey_list_probability"] = model.predict_proba(X)[:, 1]

    validate_modeling_output(df)

    return df


# ---------------------------------------------------
# Output validation and saving
# ---------------------------------------------------

def validate_modeling_output(df: pd.DataFrame) -> None:
    """
    Validate the modeled output before saving it back to the rankings file.
    """

    required_columns = [
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
            "Modeled output is missing required columns: "
            f"{missing_columns}"
        )

    missing_probabilities = int(df["predicted_grey_list_probability"].isna().sum())

    if missing_probabilities > 0:
        raise ValueError(
            "Predicted grey-list probability contains missing values. "
            f"Missing count: {missing_probabilities}"
        )

    below_zero = int((df["predicted_grey_list_probability"] < 0).sum())
    above_one = int((df["predicted_grey_list_probability"] > 1).sum())

    if below_zero > 0 or above_one > 0:
        raise ValueError(
            "Predicted grey-list probabilities must be between 0 and 1. "
            f"Below zero: {below_zero}; Above one: {above_one}"
        )

    print("\nModeling output validation passed.")


def save_modeling_output(df: pd.DataFrame) -> None:
    """
    Save the rankings file again with predicted grey-list probabilities added.
    """

    df.to_csv(RISK_RANKINGS_FILE, index=False)

    print("\nUpdated risk rankings with model probabilities saved to:")
    print(RISK_RANKINGS_FILE)


def print_top_predicted_probabilities(df: pd.DataFrame) -> None:
    """
    Print the top 20 countries by predicted FATF grey-list probability.
    """

    print("\nTop 20 countries by predicted FATF grey-list probability:")
    print(
        df.sort_values(
            "predicted_grey_list_probability",
            ascending=False,
        )[
            [
                "country",
                "tf_vulnerability_score",
                "fatf_grey_list",
                "predicted_grey_list_probability",
            ]
        ].head(20)
    )


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the modeling pipeline.
    """

    print("=" * 70)
    print("Modeling FATF grey-list status")
    print("=" * 70)

    df = load_ranked_data()
    validate_modeling_data(df)

    logit_model = run_statsmodels_logit(df)
    save_logit_summary(logit_model)

    df_with_predictions = run_sklearn_logistic_model(df)
    save_modeling_output(df_with_predictions)

    print_top_predicted_probabilities(df_with_predictions)

    print("\nModeling complete.")


if __name__ == "__main__":
    main()