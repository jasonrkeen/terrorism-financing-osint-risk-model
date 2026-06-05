"""
ACLED signal enrichment module for the terrorism financing OSINT risk model.

This module converts raw ACLED event data into country-level recent conflict,
unrest, and political-violence signal scores.

The output is designed for the threat finance intelligence gap layer. It does
not identify terrorism financing, terrorist actors, illicit transactions,
criminality, or sanctions exposure. It provides supplemental early-warning
context for analyst review.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    ACLED_RAW_FILE,
    ACLED_SIGNAL_ENRICHMENT_FILE,
    ACLED_EVENT_TYPES,
    ACLED_LOOKBACK_DAYS,
)


# ---------------------------------------------------
# Event type groups
# ---------------------------------------------------

POLITICAL_VIOLENCE_EVENT_TYPES = {
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
}

UNREST_EVENT_TYPES = {
    "Protests",
    "Riots",
}

STRATEGIC_EVENT_TYPES = {
    "Strategic developments",
}


# ---------------------------------------------------
# Helper functions
# ---------------------------------------------------

def get_first_existing_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """
    Return the first matching column name from a list of candidates.
    """

    for column in candidates:
        if column in df.columns:
            return column

    return None


def normalize_series(series: pd.Series) -> pd.Series:
    """
    Normalize a numeric series to a 0-100 scale.

    If the input has no variation, return zeros. This avoids creating artificial
    signal where all countries have the same value.
    """

    numeric = pd.to_numeric(series, errors="coerce").fillna(0)

    min_value = numeric.min()
    max_value = numeric.max()

    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series(0, index=series.index)

    return ((numeric - min_value) / (max_value - min_value) * 100).clip(0, 100)


def classify_acled_signal_level(score: float) -> str:
    """
    Classify ACLED conflict signal score.

    Thresholds are calibrated for a global country-level signal where a single
    extreme conflict environment can dominate the normalized distribution.
    These levels are early-warning categories for analyst review, not
    determinations of terrorism financing, criminality, or sanctions exposure.
    """

    if pd.isna(score):
        return "Unknown"

    if score >= 80:
        return "Severe"

    if score >= 35:
        return "High"

    if score >= 20:
        return "Moderate"

    if score > 0:
        return "Low"

    return "No Recorded Recent Signal"


def yes_no_flag(value) -> int:
    """
    Convert truthy values to 1/0.
    """

    if pd.isna(value):
        return 0

    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"1", "true", "yes", "y"}:
            return 1
        return 0

    try:
        return 1 if int(value) == 1 else 0
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------
# Data loading
# ---------------------------------------------------

def load_acled_events(input_path: Path = ACLED_RAW_FILE) -> pd.DataFrame:
    """
    Load raw ACLED events created by the ACLED data collection module.
    """

    if not input_path.exists():
        print(f"ACLED raw file not found: {input_path}")
        print("Skipping ACLED enrichment and writing an empty output table.")
        return pd.DataFrame()

    events = pd.read_csv(input_path, low_memory=False)

    if events.empty:
        print(f"ACLED raw file is empty: {input_path}")
        print("Skipping ACLED enrichment and writing an empty output table.")
        return pd.DataFrame()

    events.columns = [str(column).strip() for column in events.columns]

    print(f"Loaded ACLED raw events from: {input_path}")
    print(f"Shape: {events.shape}")

    return events


def standardize_acled_events(events: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize common ACLED columns.

    The function is tolerant of slight column-name differences between ACLED
    exports or API pulls.
    """

    if events.empty:
        return events

    events = events.copy()

    country_col = get_first_existing_column(
        events,
        ["country", "Country", "COUNTRY"],
    )

    iso_col = get_first_existing_column(
        events,
        ["iso", "ISO", "iso3", "ISO3", "country_code", "Country Code"],
    )

    event_type_col = get_first_existing_column(
        events,
        ["event_type", "Event Type", "EVENT_TYPE"],
    )

    sub_event_type_col = get_first_existing_column(
        events,
        ["sub_event_type", "Sub Event Type", "SUB_EVENT_TYPE"],
    )

    fatalities_col = get_first_existing_column(
        events,
        ["fatalities", "Fatalities", "FATALITIES"],
    )

    event_date_col = get_first_existing_column(
        events,
        ["event_date", "Event Date", "EVENT_DATE", "date", "Date"],
    )

    required_columns = {
        "country": country_col,
        "event_type": event_type_col,
        "fatalities": fatalities_col,
    }

    missing = [
        logical_name
        for logical_name, actual_column in required_columns.items()
        if actual_column is None
    ]

    if missing:
        raise ValueError(
            "ACLED raw data is missing required columns or recognizable aliases: "
            f"{missing}. Available columns: {list(events.columns)}"
        )

    standardized = pd.DataFrame()

    standardized["country"] = events[country_col].astype(str).str.strip()

    if iso_col:
        standardized["iso3"] = events[iso_col].astype(str).str.strip()
    else:
        standardized["iso3"] = ""

    standardized["event_type"] = events[event_type_col].astype(str).str.strip()

    if sub_event_type_col:
        standardized["sub_event_type"] = (
            events[sub_event_type_col].astype(str).str.strip()
        )
    else:
        standardized["sub_event_type"] = ""

    standardized["fatalities"] = pd.to_numeric(
        events[fatalities_col],
        errors="coerce",
    ).fillna(0)

    if event_date_col:
        standardized["event_date"] = pd.to_datetime(
            events[event_date_col],
            errors="coerce",
        )
    else:
        standardized["event_date"] = pd.NaT

    standardized = standardized.dropna(subset=["country"])
    standardized = standardized[standardized["country"].str.lower() != "nan"]

    return standardized


def filter_configured_event_types(events: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only ACLED event types configured in src.config.
    """

    if events.empty:
        return events

    events = events.copy()

    if not ACLED_EVENT_TYPES:
        return events

    before_count = len(events)

    filtered = events[events["event_type"].isin(ACLED_EVENT_TYPES)].copy()

    after_count = len(filtered)

    print(
        f"Filtered ACLED event types: {before_count:,} rows -> "
        f"{after_count:,} rows"
    )

    return filtered


def filter_recent_events(events: pd.DataFrame, lookback_days: int = 180) -> pd.DataFrame:
    """
    Keep events within a recent lookback window.

    The lookback uses the most recent event date in the ACLED file rather than
    today's date. This makes the module reproducible when using stored exports.
    """

    if events.empty:
        return events

    events = events.copy()

    if "event_date" not in events.columns or events["event_date"].isna().all():
        print("ACLED event dates unavailable. Using all ACLED rows.")
        return events

    max_date = events["event_date"].max()

    if pd.isna(max_date):
        print("ACLED event dates could not be parsed. Using all ACLED rows.")
        return events

    cutoff_date = max_date - pd.Timedelta(days=lookback_days)

    recent_events = events[events["event_date"] >= cutoff_date].copy()

    print(f"ACLED max event date: {max_date.date()}")
    print(f"ACLED lookback cutoff: {cutoff_date.date()}")
    print(f"ACLED recent events retained: {len(recent_events):,}")

    return recent_events


# ---------------------------------------------------
# Signal scoring
# ---------------------------------------------------

def add_event_type_flags(events: pd.DataFrame) -> pd.DataFrame:
    """
    Add event-category flags used in ACLED signal scoring.
    """

    events = events.copy()

    events["is_political_violence"] = events["event_type"].isin(
        POLITICAL_VIOLENCE_EVENT_TYPES
    ).astype(int)

    events["is_unrest"] = events["event_type"].isin(
        UNREST_EVENT_TYPES
    ).astype(int)

    events["is_strategic_development"] = events["event_type"].isin(
        STRATEGIC_EVENT_TYPES
    ).astype(int)

    events["has_fatality"] = (events["fatalities"] > 0).astype(int)

    return events


def build_country_acled_signals(events: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate ACLED events to country-level signal features.
    """

    if events.empty:
        return build_empty_acled_signal_table()

    events = add_event_type_flags(events)

    grouped = (
        events.groupby(["country", "iso3"], dropna=False)
        .agg(
            acled_event_count=("event_type", "size"),
            acled_fatalities=("fatalities", "sum"),
            acled_fatal_event_count=("has_fatality", "sum"),
            acled_political_violence_events=("is_political_violence", "sum"),
            acled_unrest_events=("is_unrest", "sum"),
            acled_strategic_development_events=(
                "is_strategic_development",
                "sum",
            ),
            acled_latest_event_date=("event_date", "max"),
        )
        .reset_index()
    )

    grouped["acled_event_count_score"] = normalize_series(
        grouped["acled_event_count"]
    )

    grouped["acled_fatality_score"] = normalize_series(
        np.log1p(grouped["acled_fatalities"])
    )

    grouped["acled_fatal_event_score"] = normalize_series(
        grouped["acled_fatal_event_count"]
    )

    grouped["acled_political_violence_score"] = normalize_series(
        grouped["acled_political_violence_events"]
    )

    grouped["acled_unrest_score"] = normalize_series(
        grouped["acled_unrest_events"]
    )

    grouped["acled_strategic_development_score"] = normalize_series(
        grouped["acled_strategic_development_events"]
    )

    grouped["acled_conflict_signal_score"] = (
        0.20 * grouped["acled_event_count_score"]
        + 0.25 * grouped["acled_fatality_score"]
        + 0.15 * grouped["acled_fatal_event_score"]
        + 0.25 * grouped["acled_political_violence_score"]
        + 0.10 * grouped["acled_unrest_score"]
        + 0.05 * grouped["acled_strategic_development_score"]
    ).round(2)

    grouped["acled_signal_level"] = grouped["acled_conflict_signal_score"].apply(
        classify_acled_signal_level
    )

    grouped["acled_source_present"] = 1
    grouped["acled_confidence"] = "Moderate to High"

    grouped = grouped.sort_values(
        "acled_conflict_signal_score",
        ascending=False,
    ).reset_index(drop=True)

    return grouped


def build_empty_acled_signal_table() -> pd.DataFrame:
    """
    Build an empty ACLED signal output table with expected columns.
    """

    columns = [
        "country",
        "iso3",
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
    ]

    return pd.DataFrame(columns=columns)


# ---------------------------------------------------
# Output
# ---------------------------------------------------

def save_acled_signal_output(signal_df: pd.DataFrame) -> None:
    """
    Save ACLED country-level signal output.
    """

    ACLED_SIGNAL_ENRICHMENT_FILE.parent.mkdir(parents=True, exist_ok=True)

    signal_df.to_csv(ACLED_SIGNAL_ENRICHMENT_FILE, index=False)

    print(f"ACLED signal enrichment saved to: {ACLED_SIGNAL_ENRICHMENT_FILE}")
    print(f"Shape: {signal_df.shape}")


def print_acled_summary(signal_df: pd.DataFrame) -> None:
    """
    Print a short ACLED enrichment summary.
    """

    if signal_df.empty:
        print("ACLED signal enrichment table is empty.")
        return

    print("\nACLED signal summary:")
    print(f"Countries with ACLED signals: {len(signal_df):,}")

    if "acled_fatalities" in signal_df.columns:
        total_fatalities = int(
            pd.to_numeric(
                signal_df["acled_fatalities"],
                errors="coerce",
            ).fillna(0).sum()
        )
        print(f"Total fatalities in ACLED signal window: {total_fatalities:,}")

    if "acled_signal_level" in signal_df.columns:
        print("\nACLED signal levels:")
        print(signal_df["acled_signal_level"].value_counts(dropna=False))

    top_columns = [
        "country",
        "iso3",
        "acled_event_count",
        "acled_fatalities",
        "acled_political_violence_events",
        "acled_unrest_events",
        "acled_conflict_signal_score",
        "acled_signal_level",
    ]

    available_columns = [
        column for column in top_columns if column in signal_df.columns
    ]

    print("\nTop 10 ACLED country signals:")
    print(signal_df[available_columns].head(10))


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run ACLED signal enrichment.
    """

    print("=" * 70)
    print("Running ACLED signal enrichment")
    print("=" * 70)

    raw_events = load_acled_events()

    if raw_events.empty:
        empty_output = build_empty_acled_signal_table()
        save_acled_signal_output(empty_output)
        print("\nACLED enrichment complete with no input data.")
        return

    standardized_events = standardize_acled_events(raw_events)
    configured_events = filter_configured_event_types(standardized_events)
    recent_events = filter_recent_events(
        configured_events,
        lookback_days=ACLED_LOOKBACK_DAYS,
    )

    signal_df = build_country_acled_signals(recent_events)

    save_acled_signal_output(signal_df)
    print_acled_summary(signal_df)

    print("\nACLED signal enrichment complete.")


if __name__ == "__main__":
    main()