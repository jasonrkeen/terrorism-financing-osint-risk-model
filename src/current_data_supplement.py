"""
Current data supplement module for the terrorism financing OSINT risk model.

The primary quantitative model is controlled by STUDY_YEAR in src/config.py.

This module adds a supplemental current-context layer using:
1. Latest available World Bank economic indicators up to CURRENT_ECONOMIC_YEAR
2. Current FATF increased-monitoring status by ISO3 country code
3. Comparison between model signals and current FATF status

This module does not replace the baseline model score.
It creates supplemental CSV outputs for interpretation and reporting.
"""

from __future__ import annotations

import pandas as pd
import requests

from src.config import (
    RISK_RANKINGS_FILE,
    TABLES_DIR,
    CURRENT_ECONOMIC_YEAR,
    CURRENT_ECONOMIC_INDICATORS,
    CURRENT_FATF_INCREASED_MONITORING_ISO3,
    CURRENT_ECONOMIC_DATA_FILE,
    CURRENT_DATA_SUPPLEMENT_FILE,
    CURRENT_FATF_STATUS_COMPARISON_FILE,
)


# ---------------------------------------------------
# World Bank API settings
# ---------------------------------------------------

WORLD_BANK_API_BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"


# ---------------------------------------------------
# World Bank API helpers
# ---------------------------------------------------

def build_world_bank_url(indicator_code: str) -> str:
    """
    Build a World Bank API URL for standard economic indicators.
    """

    return (
        f"{WORLD_BANK_API_BASE_URL}/{indicator_code}"
        f"?format=json&per_page=20000"
    )


def request_world_bank_data(
    url: str,
    max_retries: int = 3,
    timeout: int = 90,
) -> list:
    """
    Request data from the World Bank API and return the JSON response.

    The World Bank API can occasionally be slow or temporarily unavailable.
    This helper uses a longer timeout and retry logic so the full pipeline
    does not fail on a single slow request.
    """

    import time

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"World Bank request attempt {attempt}/{max_retries}")

            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            try:
                json_data = response.json()
            except ValueError as error:
                raise RuntimeError(
                    f"World Bank API response was not valid JSON for URL: {url}"
                ) from error

            if not isinstance(json_data, list):
                raise RuntimeError(
                    f"World Bank API response had an unexpected format for URL: {url}"
                )

            return json_data

        except requests.exceptions.RequestException as error:
            last_error = error
            print(f"World Bank request failed on attempt {attempt}: {error}")

            if attempt < max_retries:
                sleep_seconds = 5 * attempt
                print(f"Retrying in {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)

        except RuntimeError as error:
            last_error = error
            print(f"World Bank response validation failed on attempt {attempt}: {error}")

            if attempt < max_retries:
                sleep_seconds = 5 * attempt
                print(f"Retrying in {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)

    raise RuntimeError(
        f"World Bank API request failed after {max_retries} attempts for URL: {url}"
    ) from last_error


# ---------------------------------------------------
# Data loading
# ---------------------------------------------------

def load_rankings() -> pd.DataFrame:
    """
    Load the model country risk rankings.
    """

    if not RISK_RANKINGS_FILE.exists():
        raise FileNotFoundError(
            f"Risk rankings file not found: {RISK_RANKINGS_FILE}. "
            "Run risk_scoring.py and modeling.py first."
        )

    df = pd.read_csv(RISK_RANKINGS_FILE)

    required_columns = [
        "country",
        "country_code",
        "risk_rank",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
        "gdp_per_capita",
        "inflation",
        "unemployment",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required columns: "
            f"{missing_columns}. Run the main pipeline through src.modeling first."
        )

    print("Model risk rankings loaded.")
    print(f"Shape: {df.shape}")

    return df


# ---------------------------------------------------
# Current economic data
# ---------------------------------------------------

def fetch_latest_available_indicator(
    indicator_code: str,
    indicator_name: str,
    target_year: int,
) -> pd.DataFrame:
    """
    Fetch the latest available value for a World Bank indicator up to target_year.

    Some countries may not have target_year data available. In that case, this
    function uses the most recent available year before target_year.
    """

    url = build_world_bank_url(indicator_code)

    print(
        f"Fetching current supplement indicator: "
        f"{indicator_code} - {indicator_name}"
    )
    print(f"Target year: {target_year}")
    print(f"URL: {url}")

    json_data = request_world_bank_data(url)

    if len(json_data) < 2 or json_data[1] is None:
        raise ValueError(f"No data returned for indicator: {indicator_code}")

    rows = []

    for item in json_data[1]:
        country_code = item.get("countryiso3code")
        value = item.get("value")
        date = item.get("date")
        country_info = item.get("country", {}) or {}

        if not country_code or len(country_code) != 3:
            continue

        if value is None or date is None:
            continue

        try:
            year = int(date)
        except (TypeError, ValueError):
            continue

        if year <= target_year:
            rows.append(
                {
                    "country": country_info.get("value"),
                    "country_code": country_code,
                    f"{indicator_name}_year": year,
                    indicator_name: value,
                }
            )

    indicator_df = pd.DataFrame(rows)

    if indicator_df.empty:
        available_years = sorted(
            {
                item.get("date")
                for item in json_data[1]
                if item.get("date") is not None
            },
            reverse=True,
        )

        print("\nNo rows matched the selected current economic year or earlier.")
        print(f"Requested year: {target_year}")
        print("Available years from API:")
        print(available_years[:10])

        raise ValueError(
            f"No usable data found for indicator {indicator_code} "
            f"up to year {target_year}."
        )

    indicator_df = (
        indicator_df.sort_values(
            ["country_code", f"{indicator_name}_year"],
            ascending=[True, False],
        )
        .drop_duplicates(subset=["country_code"], keep="first")
        .reset_index(drop=True)
    )

    exact_year_count = int(
        (indicator_df[f"{indicator_name}_year"] == target_year).sum()
    )

    print(f"Collected latest available rows: {len(indicator_df)}")
    print(f"Rows using exact {target_year} data: {exact_year_count}")

    return indicator_df


def build_country_lookup(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Build one country-name lookup table by ISO3 country code.

    World Bank indicator endpoints may return slightly different country names
    across indicators. The supplement therefore merges by country_code and uses
    one lookup table for display names.
    """

    lookup_frames = []

    for frame in frames:
        if {"country_code", "country"}.issubset(frame.columns):
            lookup_frames.append(frame[["country_code", "country"]].copy())

    if not lookup_frames:
        raise ValueError("Could not build country lookup from current economic frames.")

    country_lookup = pd.concat(lookup_frames, ignore_index=True)

    country_lookup = country_lookup.dropna(subset=["country_code", "country"])
    country_lookup["country_code"] = country_lookup["country_code"].astype(str)
    country_lookup["country"] = country_lookup["country"].astype(str)

    country_lookup = (
        country_lookup.sort_values(["country_code", "country"])
        .drop_duplicates(subset=["country_code"], keep="first")
        .reset_index(drop=True)
    )

    return country_lookup


def collect_current_economic_data() -> pd.DataFrame:
    """
    Collect latest available economic indicators up to CURRENT_ECONOMIC_YEAR.
    """

    if not CURRENT_ECONOMIC_INDICATORS:
        raise ValueError("No current economic indicators were configured.")

    frames = []

    for indicator_code, indicator_name in CURRENT_ECONOMIC_INDICATORS.items():
        indicator_df = fetch_latest_available_indicator(
            indicator_code=indicator_code,
            indicator_name=indicator_name,
            target_year=CURRENT_ECONOMIC_YEAR,
        )

        frames.append(indicator_df)

    country_lookup = build_country_lookup(frames)

    # Merge on country_code only to avoid World Bank naming mismatches.
    current_df = frames[0].drop(columns=["country"], errors="ignore")

    for frame in frames[1:]:
        current_df = current_df.merge(
            frame.drop(columns=["country"], errors="ignore"),
            on="country_code",
            how="outer",
        )

    current_df = current_df.merge(
        country_lookup,
        on="country_code",
        how="left",
    )

    ordered_columns = ["country", "country_code"] + [
        column
        for column in current_df.columns
        if column not in ["country", "country_code"]
    ]

    current_df = current_df[ordered_columns]
    current_df = current_df.sort_values("country").reset_index(drop=True)

    validate_current_economic_data(current_df)

    return current_df


def validate_current_economic_data(df: pd.DataFrame) -> None:
    """
    Validate current economic supplement data before merging with rankings.
    """

    if df.empty:
        raise ValueError("Current economic data is empty.")

    required_columns = ["country", "country_code"]

    for indicator_name in CURRENT_ECONOMIC_INDICATORS.values():
        required_columns.append(indicator_name)
        required_columns.append(f"{indicator_name}_year")

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Current economic dataset is missing expected columns: "
            f"{missing_columns}"
        )

    duplicate_codes = int(df["country_code"].duplicated().sum())

    if duplicate_codes > 0:
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Current economic dataset contains duplicate country codes. "
            f"Duplicate count: {duplicate_codes}\n"
            f"{duplicate_df}"
        )

    print("\nCurrent economic data validation passed.")


def save_current_economic_data(df: pd.DataFrame) -> None:
    """
    Save current economic indicator supplement.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(CURRENT_ECONOMIC_DATA_FILE, index=False)

    print("\nCurrent economic data saved to:")
    print(CURRENT_ECONOMIC_DATA_FILE)


# ---------------------------------------------------
# FATF current status supplement
# ---------------------------------------------------

def add_current_fatf_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add current FATF increased-monitoring status using ISO3 country codes.
    """

    df = df.copy()

    current_fatf_set = set(CURRENT_FATF_INCREASED_MONITORING_ISO3)

    df["current_fatf_increased_monitoring"] = (
        df["country_code"].isin(current_fatf_set).astype(int)
    )

    return df


def create_current_status_comparison(
    baseline_df: pd.DataFrame,
    current_economic_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine model outputs with current economic data and current FATF status.
    """

    required_columns = [
        "country",
        "country_code",
        "risk_rank",
        "tf_vulnerability_score",
        "fatf_grey_list",
        "predicted_grey_list_probability",
        "gdp_per_capita",
        "inflation",
        "unemployment",
    ]

    missing_columns = [
        column for column in required_columns if column not in baseline_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required columns: "
            f"{missing_columns}. Run the main pipeline through src.modeling first."
        )

    baseline_subset = baseline_df[required_columns].copy()

    # Keep the baseline model country name as the primary display name.
    supplement_df = baseline_subset.merge(
        current_economic_df.drop(columns=["country"], errors="ignore"),
        on="country_code",
        how="left",
    )

    supplement_df = add_current_fatf_status(supplement_df)

    supplement_df["model_fatf_grey_list"] = supplement_df["fatf_grey_list"]

    supplement_df["fatf_status_changed"] = (
        supplement_df["model_fatf_grey_list"]
        != supplement_df["current_fatf_increased_monitoring"]
    ).astype(int)

    supplement_df["model_probability_signal_50pct"] = (
        supplement_df["predicted_grey_list_probability"] >= 0.50
    ).astype(int)

    supplement_df["model_signal_matches_current_fatf"] = (
        supplement_df["model_probability_signal_50pct"]
        == supplement_df["current_fatf_increased_monitoring"]
    ).astype(int)

    required_current_columns = [
        "gdp_per_capita_current",
        "gdp_per_capita_current_year",
        "inflation_current",
        "inflation_current_year",
        "unemployment_current",
        "unemployment_current_year",
    ]

    missing_current_columns = [
        column for column in required_current_columns
        if column not in supplement_df.columns
    ]

    if missing_current_columns:
        raise ValueError(
            "Current economic supplement is missing required columns after merge: "
            f"{missing_current_columns}"
        )

    supplement_df["gdp_per_capita_change_pct"] = (
        (
            supplement_df["gdp_per_capita_current"]
            - supplement_df["gdp_per_capita"]
        )
        / supplement_df["gdp_per_capita"]
    ) * 100

    supplement_df["inflation_change_points"] = (
        supplement_df["inflation_current"] - supplement_df["inflation"]
    )

    supplement_df["unemployment_change_points"] = (
        supplement_df["unemployment_current"] - supplement_df["unemployment"]
    )

    output_columns = [
        "risk_rank",
        "country",
        "country_code",
        "tf_vulnerability_score",
        "predicted_grey_list_probability",
        "model_fatf_grey_list",
        "current_fatf_increased_monitoring",
        "fatf_status_changed",
        "model_probability_signal_50pct",
        "model_signal_matches_current_fatf",
        "gdp_per_capita",
        "gdp_per_capita_current",
        "gdp_per_capita_current_year",
        "gdp_per_capita_change_pct",
        "inflation",
        "inflation_current",
        "inflation_current_year",
        "inflation_change_points",
        "unemployment",
        "unemployment_current",
        "unemployment_current_year",
        "unemployment_change_points",
    ]

    supplement_df = supplement_df[output_columns]

    validate_current_status_comparison(supplement_df)

    return supplement_df


def validate_current_status_comparison(df: pd.DataFrame) -> None:
    """
    Validate the final current data supplement before saving.
    """

    if df.empty:
        raise ValueError("Current data supplement is empty.")

    required_columns = [
        "risk_rank",
        "country",
        "country_code",
        "tf_vulnerability_score",
        "predicted_grey_list_probability",
        "model_fatf_grey_list",
        "current_fatf_increased_monitoring",
        "fatf_status_changed",
        "model_probability_signal_50pct",
        "model_signal_matches_current_fatf",
        "gdp_per_capita_current",
        "inflation_current",
        "unemployment_current",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Current data supplement is missing required columns: "
            f"{missing_columns}"
        )

    binary_columns = [
        "model_fatf_grey_list",
        "current_fatf_increased_monitoring",
        "fatf_status_changed",
        "model_probability_signal_50pct",
        "model_signal_matches_current_fatf",
    ]

    for column in binary_columns:
        values = sorted(df[column].dropna().unique().tolist())

        if not set(values).issubset({0, 1}):
            raise ValueError(
                f"{column} must contain only binary 0/1 values. "
                f"Found values: {values}"
            )

    duplicate_codes = int(df["country_code"].duplicated().sum())

    if duplicate_codes > 0:
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Current data supplement contains duplicate country codes. "
            f"Duplicate count: {duplicate_codes}\n"
            f"{duplicate_df}"
        )

    print("\nCurrent status comparison validation passed.")


def save_current_status_outputs(df: pd.DataFrame) -> None:
    """
    Save current supplement and current FATF comparison outputs.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(CURRENT_DATA_SUPPLEMENT_FILE, index=False)

    fatf_comparison_columns = [
        "risk_rank",
        "country",
        "country_code",
        "tf_vulnerability_score",
        "predicted_grey_list_probability",
        "model_fatf_grey_list",
        "current_fatf_increased_monitoring",
        "fatf_status_changed",
        "model_probability_signal_50pct",
        "model_signal_matches_current_fatf",
    ]

    fatf_comparison_df = df[fatf_comparison_columns].copy()

    fatf_comparison_df = fatf_comparison_df.sort_values(
        [
            "current_fatf_increased_monitoring",
            "predicted_grey_list_probability",
        ],
        ascending=[False, False],
    ).reset_index(drop=True)

    fatf_comparison_df.to_csv(
        CURRENT_FATF_STATUS_COMPARISON_FILE,
        index=False,
    )

    print("\nCurrent data supplement saved to:")
    print(CURRENT_DATA_SUPPLEMENT_FILE)

    print("Current FATF status comparison saved to:")
    print(CURRENT_FATF_STATUS_COMPARISON_FILE)


# ---------------------------------------------------
# Summary
# ---------------------------------------------------

def print_current_status_summary(df: pd.DataFrame) -> None:
    """
    Print summary statistics for the current supplement.
    """

    current_count = int(df["current_fatf_increased_monitoring"].sum())
    model_fatf_count = int(df["model_fatf_grey_list"].sum())
    changed_count = int(df["fatf_status_changed"].sum())
    match_count = int(df["model_signal_matches_current_fatf"].sum())

    print("\nCurrent data supplement summary:")
    print(f"Model FATF grey-list countries in modeled dataset: {model_fatf_count}")
    print(
        "Current FATF increased-monitoring countries in modeled dataset: "
        f"{current_count}"
    )
    print(f"Countries with changed FATF status flag: {changed_count}")
    print(
        "Model 50% probability signal matches current FATF status for: "
        f"{match_count} countries"
    )
    print(f"Total countries in supplement: {len(df)}")

    print("\nTop 15 current FATF monitored jurisdictions by model probability:")
    print(
        df[df["current_fatf_increased_monitoring"] == 1]
        .sort_values("predicted_grey_list_probability", ascending=False)
        [
            [
                "country",
                "risk_rank",
                "tf_vulnerability_score",
                "predicted_grey_list_probability",
                "model_fatf_grey_list",
                "current_fatf_increased_monitoring",
            ]
        ]
        .head(15)
    )

    print("\nCurrent economic change summary:")
    change_columns = [
        "gdp_per_capita_change_pct",
        "inflation_change_points",
        "unemployment_change_points",
    ]

    available_change_columns = [
        column for column in change_columns if column in df.columns
    ]

    if available_change_columns:
        print(df[available_change_columns].describe())


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the current data supplement workflow.
    """

    print("=" * 70)
    print("Running current data supplement")
    print("=" * 70)

    baseline_df = load_rankings()

    current_economic_df = collect_current_economic_data()
    save_current_economic_data(current_economic_df)

    supplement_df = create_current_status_comparison(
        baseline_df=baseline_df,
        current_economic_df=current_economic_df,
    )

    save_current_status_outputs(supplement_df)
    print_current_status_summary(supplement_df)

    print("\nCurrent data supplement complete.")


if __name__ == "__main__":
    main()