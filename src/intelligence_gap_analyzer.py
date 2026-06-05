"""
Intelligence gap analyzer for the terrorism financing OSINT risk model.

This module scores whether a country-level terrorism-financing vulnerability
assessment has missing, stale, or weak public-source coverage.

The output is intended for analyst review and collection planning. It does not
identify terrorism financing, determine criminality, confirm sanctions exposure,
or allege illicit activity.
"""

from __future__ import annotations

import numpy as np
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


def normalize_score(value: object, min_value: float = 0, max_value: float = 100) -> float:
    """
    Normalize a numeric value to a 0-100 score.
    """

    if pd.isna(value):
        return np.nan

    if max_value == min_value:
        return 0

    numeric = pd.to_numeric(value, errors="coerce")

    if pd.isna(numeric):
        return np.nan

    score = ((numeric - min_value) / (max_value - min_value)) * 100

    return round(float(max(0, min(100, score))), 2)


def classify_gap_level(score: float) -> str:
    """
    Classify a 0-100 intelligence-gap score.
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


def calculate_staleness_score(days_since_update: object) -> float:
    """
    Calculate source staleness.

    Higher score means the source is more stale or unavailable.
    """

    if pd.isna(days_since_update):
        return 100

    days = pd.to_numeric(days_since_update, errors="coerce")

    if pd.isna(days):
        return 100

    if days <= 30:
        return 10

    if days <= 90:
        return 30

    if days <= 180:
        return 55

    if days <= 365:
        return 75

    return 95


def is_weak_confidence(value: object) -> bool:
    """
    Return True when a source confidence value is weak or unknown.
    """

    if pd.isna(value):
        return True

    text = str(value).strip().lower()

    return text in {"", "low", "unknown", "none", "n/a", "nan"}


def calculate_intelligence_gap_score(row: pd.Series) -> float:
    """
    Score whether a country assessment has missing, stale, or weak evidence.

    The score combines:
    - missing source coverage
    - stale source coverage
    - weak or unknown confidence

    Higher scores indicate larger intelligence gaps.
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

        if is_weak_confidence(confidence):
            weak_confidence_count += 1

    missing_score = normalize_score(
        missing_source_count,
        min_value=0,
        max_value=len(REQUIRED_COLLECTION_AREAS),
    )

    stale_score = (
        float(np.nanmean(stale_source_scores))
        if stale_source_scores
        else 100
    )

    confidence_gap_score = normalize_score(
        weak_confidence_count,
        min_value=0,
        max_value=len(REQUIRED_COLLECTION_AREAS),
    )

    intelligence_gap_score = (
        0.45 * missing_score
        + 0.35 * stale_score
        + 0.20 * confidence_gap_score
    )

    return round(float(intelligence_gap_score), 2)


def calculate_source_coverage_score(row: pd.Series) -> float:
    """
    Calculate the percentage of required source areas that are present.
    """

    present_flags = []

    for area in REQUIRED_COLLECTION_AREAS:
        present_col = f"{area}_source_present"
        present_flags.append(yes_no_flag(row.get(present_col, 0)))

    if not present_flags:
        return 0.0

    return round(float(np.mean(present_flags) * 100), 2)


def calculate_source_staleness_score(row: pd.Series) -> float:
    """
    Calculate average source staleness across required collection areas.
    """

    staleness_scores = []

    for area in REQUIRED_COLLECTION_AREAS:
        present_col = f"{area}_source_present"
        days_col = f"{area}_days_since_update"

        present = yes_no_flag(row.get(present_col, 0))

        if present == 0:
            staleness_scores.append(100)
        else:
            staleness_scores.append(
                calculate_staleness_score(row.get(days_col, np.nan))
            )

    if not staleness_scores:
        return 100.0

    return round(float(np.nanmean(staleness_scores)), 2)


def add_intelligence_gap_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add intelligence-gap, source-coverage, and source-staleness scores.
    """

    df = df.copy()

    df["intelligence_gap_score"] = df.apply(
        calculate_intelligence_gap_score,
        axis=1,
    )

    df["intelligence_gap_level"] = df["intelligence_gap_score"].apply(
        classify_gap_level
    )

    df["source_coverage_score"] = df.apply(
        calculate_source_coverage_score,
        axis=1,
    )

    df["source_staleness_score"] = df.apply(
        calculate_source_staleness_score,
        axis=1,
    )

    return df