"""
Collection priority model for the terrorism financing OSINT risk model.

This module calculates collection-priority scores and recommended public-source
collection focus areas for analyst review.

The output is a prioritization aid. It does not determine terrorism financing,
criminality, sanctions exposure, or illicit activity.
"""

from __future__ import annotations

import pandas as pd


REQUIRED_COLLECTION_AREAS = [
    "sanctions",
    "conflict",
    "aml_cft",
    "organized_crime",
    "governance",
    "crypto_risk",
    "enforcement_actions",
    "terrorism_financing_reporting",
]


def yes_no_flag(value: object) -> int:
    """
    Convert common 0/1, boolean, and text flags into 0 or 1.
    """
    if pd.isna(value):
        return 0

    text = str(value).strip().lower()

    if text in {"1", "1.0", "true", "yes", "y", "high", "active"}:
        return 1

    try:
        return 1 if int(float(text)) == 1 else 0
    except (TypeError, ValueError):
        return 0


def safe_numeric(value: object, default: float = 50.0) -> float:
    """
    Convert a value to float with a safe fallback.
    """
    try:
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric):
            return default
        return float(numeric)
    except Exception:
        return default


def classify_priority(score: float) -> str:
    """
    Classify a 0-100 collection-priority score.
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


def calculate_collection_priority(row: pd.Series) -> float:
    """
    Calculate a collection-priority score.

    The score combines:
    - baseline country-level terrorism-financing vulnerability
    - recent/live signal strength
    - intelligence gap severity
    - source staleness
    - decision relevance

    This score is for analyst collection planning only.
    """

    baseline_risk = safe_numeric(
        row.get(
            "baseline_tf_risk_score",
            row.get("tf_vulnerability_score", row.get("tf_risk_score", 50)),
        ),
        default=50,
    )

    live_signal = safe_numeric(row.get("live_signal_score", 50), default=50)

    intelligence_gap = safe_numeric(
        row.get("intelligence_gap_score", 50),
        default=50,
    )

    source_staleness = safe_numeric(
        row.get("source_staleness_score", intelligence_gap),
        default=intelligence_gap,
    )

    decision_relevance = safe_numeric(
        row.get("decision_relevance_score", baseline_risk),
        default=baseline_risk,
    )

    score = (
        0.35 * baseline_risk
        + 0.25 * intelligence_gap
        + 0.20 * live_signal
        + 0.10 * source_staleness
        + 0.10 * decision_relevance
    )

    return round(float(score), 2)


def get_missing_collection_gaps(row: pd.Series) -> list[str]:
    """
    Identify missing or unvalidated collection areas.
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

    if yes_no_flag(row.get("terrorism_financing_reporting_source_present", 0)) == 0:
        gaps.append("recent terrorism-financing reporting")

    return gaps


def recommend_collection_focus(row: pd.Series) -> str:
    """
    Recommend the next collection focus based on source gaps and live signals.
    """

    gaps = get_missing_collection_gaps(row)

    baseline_risk = safe_numeric(
        row.get(
            "baseline_tf_risk_score",
            row.get("tf_vulnerability_score", row.get("tf_risk_score", 0)),
        ),
        default=0,
    )

    live_signal = safe_numeric(row.get("live_signal_score", 50), default=50)
    intelligence_gap = safe_numeric(row.get("intelligence_gap_score", 0), default=0)

    acled_signal = safe_numeric(
        row.get(
            "acled_acled_conflict_signal_score",
            row.get("acled_conflict_signal_score", 0),
        ),
        default=0,
    )

    if live_signal >= 65 and gaps:
        return (
            "Validate recent live signals and collect or refresh: "
            + ", ".join(gaps[:3])
            + "."
        )

    if acled_signal >= 35 and gaps:
        return (
            "Review recent ACLED conflict or unrest signals and collect or refresh: "
            + ", ".join(gaps[:3])
            + "."
        )

    if baseline_risk >= 65 and gaps:
        return (
            "High baseline risk; collect or validate: "
            + ", ".join(gaps[:3])
            + "."
        )

    if gaps:
        return "Collect or validate: " + ", ".join(gaps[:3]) + "."

    if intelligence_gap >= 65:
        return (
            "Refresh recent sanctions, conflict, enforcement, and "
            "terrorism-financing reporting."
        )

    if live_signal >= 65:
        return (
            "Validate recent live signals against sanctions, conflict, "
            "and enforcement sources."
        )

    return "Continue routine monitoring and refresh high-priority public sources."


def add_decision_relevance_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add decision relevance score if missing.

    Version 1 uses baseline risk as the decision-relevance proxy.
    """

    df = df.copy()

    if "decision_relevance_score" not in df.columns:
        if "baseline_tf_risk_score" in df.columns:
            df["decision_relevance_score"] = pd.to_numeric(
                df["baseline_tf_risk_score"],
                errors="coerce",
            ).fillna(50)
        elif "tf_vulnerability_score" in df.columns:
            df["decision_relevance_score"] = pd.to_numeric(
                df["tf_vulnerability_score"],
                errors="coerce",
            ).fillna(50)
        else:
            df["decision_relevance_score"] = 50

    return df


def add_collection_priority(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add collection priority score, level, and recommended collection focus.
    """

    df = df.copy()
    df = add_decision_relevance_score(df)

    df["collection_priority_score"] = df.apply(
        calculate_collection_priority,
        axis=1,
    )

    df["collection_priority_level"] = df["collection_priority_score"].apply(
        classify_priority,
    )

    df["recommended_collection_focus"] = df.apply(
        recommend_collection_focus,
        axis=1,
    )

    return df