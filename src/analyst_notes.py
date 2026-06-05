"""
Analyst note helper module for the terrorism financing OSINT risk model.

This module creates conservative analyst-review notes for the threat finance
intelligence gap and collection-priority layer.

The notes are designed for defensive public-source review. They do not identify
terrorists, determine criminality, confirm sanctions exposure, or allege
terrorism-financing activity.
"""


def safe_value(row, keys, default="Unknown"):
    """
    Return the first available value from a row using a list of possible keys.
    """
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return default


def generate_analyst_note(row):
    """
    Generate a conservative analyst-review note for a country record.
    """

    country = safe_value(
        row,
        ["country", "Country", "country_name", "Country Name"],
        "Unknown country",
    )

    risk_score = safe_value(
        row,
        [
            "baseline_tf_risk_score",
            "tf_vulnerability_score",
            "tf_risk_score",
            "risk_score",
        ],
        "Unknown",
    )

    risk_level = safe_value(
        row,
        [
            "baseline_tf_risk_level",
            "tf_risk_level",
            "risk_level",
            "risk_category",
        ],
        "Unknown",
    )

    live_signal = safe_value(
        row,
        ["live_signal_score"],
        "Unknown",
    )

    source_coverage = safe_value(
        row,
        ["source_coverage_score"],
        "Unknown",
    )

    gap_score = safe_value(
        row,
        ["intelligence_gap_score"],
        "Unknown",
    )

    gap_level = safe_value(
        row,
        ["intelligence_gap_level"],
        "Unknown",
    )

    priority_score = safe_value(
        row,
        ["collection_priority_score"],
        "Unknown",
    )

    priority = safe_value(
        row,
        ["collection_priority_level"],
        "Unknown",
    )

    acled_signal = safe_value(
        row,
        [
            "acled_acled_conflict_signal_score",
            "acled_conflict_signal_score",
        ],
        "Not available",
    )

    acled_level = safe_value(
        row,
        [
            "acled_acled_signal_level",
            "acled_signal_level",
        ],
        "Not available",
    )

    focus = safe_value(
        row,
        ["recommended_collection_focus"],
        "Review available public-source terrorism-financing indicators.",
    )

    note = (
        f"{country} has a baseline terrorism-financing vulnerability assessment "
        f"of {risk_level} with a score of {risk_score}. The live/recent signal "
        f"score is {live_signal}, source coverage is {source_coverage}, and the "
        f"intelligence gap score is {gap_score} ({gap_level}). "
        f"The resulting collection-priority score is {priority_score}, classified "
        f"as {priority}. "
    )

    if acled_signal != "Not available":
        note += (
            f"ACLED recent conflict and unrest signal context is available with "
            f"a score of {acled_signal} and signal level of {acled_level}. "
        )

    note += (
        f"Recommended next step: {focus} "
        "This output is intended for analyst review and public-source collection "
        "planning. It does not constitute a determination of terrorism, criminality, "
        "sanctions exposure, illicit finance, or terrorism-financing activity."
    )

    return note


def add_analyst_notes(df):
    """
    Add analyst notes to a dataframe.
    """
    df = df.copy()
    df["analyst_note"] = df.apply(generate_analyst_note, axis=1)
    return df