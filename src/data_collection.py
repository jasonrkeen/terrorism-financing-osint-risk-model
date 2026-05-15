"""
Data collection module for the terrorism financing OSINT risk model.

This script pulls country-level indicators from the World Bank API and
saves the combined raw dataset to data/raw/.

The primary model year is controlled by STUDY_YEAR in src/config.py.

For WGI governance indicators, the script uses the World Bank WGI API source.
For economic indicators, the script uses the World Bank indicator endpoint.

If an indicator does not have exact STUDY_YEAR data for a country, the script
uses the latest available value before STUDY_YEAR and records the year used.
This supports a 2024 model when some indicators are not yet fully available
for every country.
"""

import pandas as pd
import requests

from src.config import (
    STUDY_YEAR,
    WORLD_BANK_INDICATORS,
    RAW_WORLD_BANK_DATA_FILE,
    RAW_DATA_DIR,
)


# ---------------------------------------------------
# World Bank API settings
# ---------------------------------------------------

WORLD_BANK_API_BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"

# World Bank Worldwide Governance Indicators are accessed through source 75.
WGI_SOURCE_ID = 75

WGI_INDICATORS = {
    "CC.EST",
    "RL.EST",
    "PV.EST",
}


# ---------------------------------------------------
# API helpers
# ---------------------------------------------------

def build_world_bank_url(indicator_code: str) -> str:
    """
    Build the correct World Bank API URL for each indicator.

    WGI governance indicators are pulled from World Bank source 75.
    Standard economic indicators use the normal World Bank indicator endpoint.
    """

    base_url = f"{WORLD_BANK_API_BASE_URL}/{indicator_code}"

    if indicator_code in WGI_INDICATORS:
        return f"{base_url}?format=json&per_page=20000&source={WGI_SOURCE_ID}"

    return f"{base_url}?format=json&per_page=20000"


def request_world_bank_data(url: str) -> list:
    """
    Request data from the World Bank API and return the JSON response.
    """

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"World Bank API request failed for URL: {url}"
        ) from error

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


# ---------------------------------------------------
# Indicator collection
# ---------------------------------------------------

def fetch_world_bank_indicator(
    indicator_code: str,
    indicator_name: str,
    year: int,
) -> pd.DataFrame:
    """
    Fetch one World Bank indicator for all countries.

    The function keeps the latest available value up to the requested study year.
    This is useful because some World Bank indicators may not have complete
    country coverage for the most recent year.

    Parameters
    ----------
    indicator_code : str
        World Bank indicator code, such as "NY.GDP.PCAP.CD".
    indicator_name : str
        Clean column name to use in the final dataset.
    year : int
        Target study year.

    Returns
    -------
    pd.DataFrame
        DataFrame with country, country_code, indicator value, and year used.
    """

    url = build_world_bank_url(indicator_code)

    print(f"Fetching {indicator_code} - {indicator_name}...")
    print(f"Target year: {year}")
    print(f"URL: {url}")

    json_data = request_world_bank_data(url)

    if len(json_data) < 2 or json_data[1] is None:
        print("\nAPI response:")
        print(json_data)
        raise ValueError(f"No data returned for indicator: {indicator_code}")

    rows = []

    for item in json_data[1]:
        country_code = item.get("countryiso3code")
        value = item.get("value")
        date = item.get("date")
        country_info = item.get("country", {})

        if not country_code or len(country_code) != 3:
            continue

        if value is None or date is None:
            continue

        try:
            observation_year = int(date)
        except (TypeError, ValueError):
            continue

        if observation_year <= year:
            rows.append(
                {
                    "country": country_info.get("value"),
                    "country_code": country_code,
                    f"{indicator_name}_year": observation_year,
                    indicator_name: value,
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        available_years = sorted(
            {
                item.get("date")
                for item in json_data[1]
                if item.get("date") is not None
            },
            reverse=True,
        )

        print("\nNo rows matched the selected study year or earlier.")
        print(f"Requested year: {year}")
        print("Available years from API:")
        print(available_years[:10])

        raise ValueError(
            f"No usable data found for indicator: {indicator_code}. "
            "Try checking STUDY_YEAR in src/config.py."
        )

    # Keep the latest available observation for each country up to STUDY_YEAR.
    df = (
        df.sort_values(
            ["country_code", f"{indicator_name}_year"],
            ascending=[True, False],
        )
        .drop_duplicates(subset=["country_code"], keep="first")
        .reset_index(drop=True)
    )

    exact_year_count = int((df[f"{indicator_name}_year"] == year).sum())

    print(f"Collected {len(df)} latest available rows for {indicator_name}.")
    print(f"Rows using exact {year} data: {exact_year_count}")

    return df


def build_country_lookup(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Build one country-name lookup table by ISO3 country code.

    World Bank sources sometimes use slightly different names for the same
    ISO3 country code. For example, one source may return "Somalia" while
    another returns "Somalia, Fed. Rep." This helper keeps one country name
    per country_code so the merged dataset remains one row per ISO3 code.
    """

    lookup_frames = []

    for frame in frames:
        if {"country_code", "country"}.issubset(frame.columns):
            lookup_frames.append(frame[["country_code", "country"]].copy())

    if not lookup_frames:
        raise ValueError("Could not build country lookup from indicator frames.")

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


def collect_world_bank_data(year: int = STUDY_YEAR) -> pd.DataFrame:
    """
    Collect and merge all World Bank indicators listed in config.py.

    Parameters
    ----------
    year : int
        Study year.

    Returns
    -------
    pd.DataFrame
        Combined country-level dataset.
    """

    if not WORLD_BANK_INDICATORS:
        raise ValueError("No World Bank indicators were configured.")

    frames = []

    for indicator_code, indicator_name in WORLD_BANK_INDICATORS.items():
        indicator_df = fetch_world_bank_indicator(
            indicator_code=indicator_code,
            indicator_name=indicator_name,
            year=year,
        )

        frames.append(indicator_df)

    country_lookup = build_country_lookup(frames)

    # Merge on country_code only to avoid duplicate rows caused by
    # source-specific country-name differences.
    combined_df = frames[0].drop(columns=["country"], errors="ignore")

    for frame in frames[1:]:
        combined_df = combined_df.merge(
            frame.drop(columns=["country"], errors="ignore"),
            on="country_code",
            how="outer",
        )

    combined_df = combined_df.merge(
        country_lookup,
        on="country_code",
        how="left",
    )

    # Put country identifiers first.
    ordered_columns = ["country", "country_code"] + [
        column
        for column in combined_df.columns
        if column not in ["country", "country_code"]
    ]

    combined_df = combined_df[ordered_columns]

    combined_df = combined_df.sort_values("country").reset_index(drop=True)

    return combined_df


# ---------------------------------------------------
# Validation
# ---------------------------------------------------

def validate_collected_data(df: pd.DataFrame) -> None:
    """
    Validate the combined raw World Bank dataset before saving.
    """

    if df.empty:
        raise ValueError("Collected World Bank dataset is empty.")

    required_columns = ["country", "country_code"]

    for indicator_name in WORLD_BANK_INDICATORS.values():
        required_columns.append(indicator_name)
        required_columns.append(f"{indicator_name}_year")

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Collected World Bank dataset is missing expected columns: "
            f"{missing_columns}"
        )

    duplicate_codes = int(df["country_code"].duplicated().sum())

    if duplicate_codes > 0:
        duplicate_df = df[df["country_code"].duplicated(keep=False)][
            ["country", "country_code"]
        ].sort_values("country_code")

        raise ValueError(
            "Collected World Bank dataset contains duplicate country codes. "
            f"Duplicate count: {duplicate_codes}\n"
            f"{duplicate_df}"
        )

    missing_country_names = int(df["country"].isna().sum())

    if missing_country_names > 0:
        raise ValueError(
            "Collected World Bank dataset contains missing country names. "
            f"Missing count: {missing_country_names}"
        )

    print("\nCollected data validation passed.")


# ---------------------------------------------------
# Output and summaries
# ---------------------------------------------------

def print_collection_summary(df: pd.DataFrame) -> None:
    """
    Print a summary of the collected dataset.
    """

    print("\nPreview of collected data:")
    print(df.head())

    print("\nDataset shape:")
    print(df.shape)

    print("\nMissing values by column:")
    print(df.isna().sum())

    year_columns = [column for column in df.columns if column.endswith("_year")]

    print("\nYears used by indicator:")

    if not year_columns:
        print("No indicator year columns found.")
        return

    for column in year_columns:
        print(f"\n{column}:")
        print(df[column].value_counts().sort_index(ascending=False).head(10))


def save_raw_data(df: pd.DataFrame) -> None:
    """
    Save the raw World Bank dataset to the raw data folder.
    """

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(RAW_WORLD_BANK_DATA_FILE, index=False)

    print("\nRaw World Bank data saved to:")
    print(RAW_WORLD_BANK_DATA_FILE)


# ---------------------------------------------------
# Main
# ---------------------------------------------------

def main() -> None:
    """
    Run the data collection process.
    """

    print("=" * 70)
    print("Collecting World Bank data")
    print("=" * 70)
    print(f"Study year: {STUDY_YEAR}")

    df = collect_world_bank_data(year=STUDY_YEAR)

    validate_collected_data(df)
    print_collection_summary(df)

    save_raw_data(df)

    print("\nData collection complete.")


if __name__ == "__main__":
    main()