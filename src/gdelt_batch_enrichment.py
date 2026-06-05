"""
GDELT 2.0 batch-file public-news signal enrichment module.

This module adds a supplemental public-news signal layer to the terrorism
financing OSINT risk model using GDELT 2.0 batch data files instead of sending
one DOC API request per country.

Why this approach:
- The DOC API can rate-limit high-volume country-by-country search.
- GDELT 2.0 publishes rolling batch files that can be downloaded and filtered
  locally.
- This is a better fit for repeatable model pipelines.

The GDELT layer is used as open-source media-reporting context for analyst
review and collection prioritization. It does not replace the baseline
terrorism-financing vulnerability score and does not constitute evidence of
terrorism financing, criminality, sanctions exposure, illicit finance, or
activity by any specific person, entity, account, wallet, or network.

Expected outputs:
- outputs/tables/gdelt_news_signal_enrichment.csv
- outputs/charts/top_15_gdelt_news_signal_scores.png
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import math
import re
import time
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


# ---------------------------------------------------------------------
# Config with safe fallbacks
# ---------------------------------------------------------------------

try:
    from src import config
except Exception:  # pragma: no cover
    config = None


BASE_DIR = Path(__file__).resolve().parent.parent

TABLES_DIR = getattr(
    config,
    "TABLES_DIR",
    BASE_DIR / "outputs" / "tables",
)

CHARTS_DIR = getattr(
    config,
    "CHARTS_DIR",
    BASE_DIR / "outputs" / "charts",
)

RAW_DATA_DIR = getattr(
    config,
    "RAW_DATA_DIR",
    BASE_DIR / "data" / "raw",
)

RISK_RANKINGS_FILE = getattr(
    config,
    "RISK_RANKINGS_FILE",
    TABLES_DIR / "terrorism_financing_country_risk_rankings.csv",
)

GDELT_MASTER_FILE_LIST_URL = getattr(
    config,
    "GDELT_MASTER_FILE_LIST_URL",
    "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
)

GDELT_BATCH_MAX_FILES = getattr(config, "GDELT_BATCH_MAX_FILES", 24)
GDELT_BATCH_SLEEP_SECONDS = getattr(config, "GDELT_BATCH_SLEEP_SECONDS", 0.5)
GDELT_BATCH_TIMEOUT_SECONDS = getattr(config, "GDELT_BATCH_TIMEOUT_SECONDS", 60)
GDELT_BATCH_REUSE_RAW_FILES = getattr(config, "GDELT_BATCH_REUSE_RAW_FILES", True)

GDELT_NEWS_SIGNAL_ENRICHMENT_FILE = getattr(
    config,
    "GDELT_NEWS_SIGNAL_ENRICHMENT_FILE",
    TABLES_DIR / "gdelt_news_signal_enrichment.csv",
)

TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE = getattr(
    config,
    "TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE",
    CHARTS_DIR / "top_15_gdelt_news_signal_scores.png",
)

GDELT_BATCH_RAW_DIR = getattr(
    config,
    "GDELT_BATCH_RAW_DIR",
    RAW_DATA_DIR / "gdelt_gkg",
)

GDELT_BATCH_KEYWORDS = getattr(
    config,
    "GDELT_BATCH_KEYWORDS",
    [
        "terrorist financing",
        "terrorism financing",
        "terror finance",
        "threat finance",
        "illicit finance",
        "money laundering",
        "aml",
        "cft",
        "countering the financing of terrorism",
        "counter terrorist financing",
        "sanctions",
        "financial crime",
        "hawala",
        "charity abuse",
        "front company",
        "beneficial ownership",
        "crypto sanctions",
        "virtual asset",
    ],
)


COUNTRY_ALIASES = {
    "Bahamas, The": ["Bahamas"],
    "Bolivia": ["Bolivia"],
    "Congo, Dem. Rep.": ["Democratic Republic of Congo", "DRC", "Congo Kinshasa"],
    "Congo, Rep.": ["Republic of Congo", "Congo Brazzaville"],
    "Cote d'Ivoire": ["Côte d'Ivoire", "Ivory Coast", "Cote d Ivoire"],
    "Egypt, Arab Rep.": ["Egypt"],
    "Gambia, The": ["Gambia"],
    "Iran, Islamic Rep.": ["Iran"],
    "Korea, Dem. People's Rep.": ["North Korea", "DPRK"],
    "Korea, Rep.": ["South Korea", "Republic of Korea"],
    "Kyrgyz Republic": ["Kyrgyzstan"],
    "Lao PDR": ["Laos", "Lao People's Democratic Republic"],
    "Russian Federation": ["Russia"],
    "Syrian Arab Republic": ["Syria"],
    "Turkiye": ["Turkey"],
    "Venezuela, RB": ["Venezuela"],
    "Viet Nam": ["Vietnam"],
    "Yemen, Rep.": ["Yemen"],
}


# GDELT 2.0 GKG column layout. The stream is tab-delimited and usually has no
# header row.
GKG_COLUMNS = [
    "GKGRECORDID",
    "DATE",
    "SourceCollectionIdentifier",
    "SourceCommonName",
    "DocumentIdentifier",
    "Counts",
    "V2Counts",
    "Themes",
    "V2Themes",
    "Locations",
    "V2Locations",
    "Persons",
    "V2Persons",
    "Organizations",
    "V2Organizations",
    "Tone",
    "EnhancedDates",
    "GCAM",
    "SharingImage",
    "RelatedImages",
    "SocialImageEmbeds",
    "SocialVideoEmbeds",
    "Quotations",
    "AllNames",
    "Amounts",
    "TranslationInfo",
    "Extras",
]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def normalize_text(value: object) -> str:
    """
    Normalize text for conservative matching.
    """

    if pd.isna(value):
        return ""

    text = str(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalized_phrase_in_text(phrase: str, text: str) -> bool:
    """
    Match a normalized phrase against normalized text using token boundaries.

    This avoids false positives such as matching "India" inside "Indian" or
    short acronyms inside longer words.
    """

    normalized_phrase = normalize_text(phrase)
    normalized_text = normalize_text(text)

    if not normalized_phrase or not normalized_text:
        return False

    return f" {normalized_phrase} " in f" {normalized_text} "


def classify_gdelt_signal(score: float) -> str:
    """
    Classify GDELT public-news signal score.
    """

    if pd.isna(score):
        return "Unknown"

    if score >= 80:
        return "Very High"

    if score >= 60:
        return "High"

    if score >= 35:
        return "Moderate"

    if score > 0:
        return "Low"

    return "No Recorded Recent Signal"


def parse_gdelt_datetime_from_url(url: str) -> str:
    """
    Extract YYYYMMDDHHMMSS timestamp from a GDELT URL when present.
    """

    match = re.search(r"(\d{14})\.gkg\.csv\.zip", url)

    if not match:
        return ""

    return match.group(1)


def gdelt_timestamp_to_iso(timestamp: str) -> str:
    """
    Convert GDELT timestamp to ISO date-time string.
    """

    if not timestamp:
        return ""

    try:
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
        return dt.isoformat()
    except ValueError:
        return timestamp


def build_country_alias_map(rankings_df: pd.DataFrame) -> dict[str, dict[str, object]]:
    """
    Build normalized aliases for each model country.
    """

    country_map: dict[str, dict[str, object]] = {}

    for _, row in rankings_df.iterrows():
        country = str(row["country"])
        country_code = str(row.get("country_code", ""))

        aliases = {country}
        aliases.update(COUNTRY_ALIASES.get(country, []))

        normalized_aliases = {
            normalize_text(alias)
            for alias in aliases
            if normalize_text(alias)
        }

        country_map[country] = {
            "country": country,
            "country_code": country_code,
            "aliases": normalized_aliases,
        }

    return country_map


def row_matches_keywords(row_text: str) -> bool:
    """
    Return True when GKG text contains one of the configured signal terms.

    Matching uses normalized token boundaries to reduce false positives from
    short terms appearing inside unrelated words.
    """

    for keyword in GDELT_BATCH_KEYWORDS:
        if normalized_phrase_in_text(keyword, row_text):
            return True

    return False


def find_matching_countries(
    location_text: str,
    country_map: dict[str, dict[str, object]],
) -> list[str]:
    """
    Match GKG location text to modeled countries.

    Matching uses token-boundary checks to reduce false positives from country
    names appearing inside longer words. For example, "India" should not match
    "Indian" unless "India" also appears as a standalone location term.
    """

    if not normalize_text(location_text):
        return []

    matches = []

    for country, metadata in country_map.items():
        aliases = metadata["aliases"]

        if any(normalized_phrase_in_text(str(alias), location_text) for alias in aliases):
            matches.append(country)

    return matches


def parse_tone(value: object) -> float:
    """
    Parse the first GDELT Tone value when available.
    """

    if pd.isna(value):
        return np.nan

    text = str(value)

    if not text:
        return np.nan

    first_value = text.split(",")[0]

    try:
        return float(first_value)
    except ValueError:
        return np.nan


# ---------------------------------------------------------------------
# GDELT file discovery and loading
# ---------------------------------------------------------------------

def fetch_master_file_list() -> list[str]:
    """
    Fetch the GDELT 2.0 master file list and return GKG CSV ZIP URLs.
    """

    response = requests.get(
        GDELT_MASTER_FILE_LIST_URL,
        timeout=GDELT_BATCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    urls = []

    for line in response.text.splitlines():
        parts = line.strip().split()

        if not parts:
            continue

        url = parts[-1]

        if url.endswith(".gkg.csv.zip"):
            urls.append(url)

    if not urls:
        raise ValueError("No GKG CSV ZIP URLs found in the GDELT master file list.")

    # Keep the most recent files.
    return urls[-int(GDELT_BATCH_MAX_FILES):]


def local_gkg_zip_path(url: str) -> Path:
    """
    Create a local cache path for a GDELT GKG ZIP URL.
    """

    filename = Path(url).name
    return GDELT_BATCH_RAW_DIR / filename


def download_gkg_zip(url: str) -> bytes:
    """
    Download or reuse a GDELT GKG ZIP file.
    """

    GDELT_BATCH_RAW_DIR.mkdir(parents=True, exist_ok=True)

    local_path = local_gkg_zip_path(url)

    if GDELT_BATCH_REUSE_RAW_FILES and local_path.exists():
        return local_path.read_bytes()

    response = requests.get(
        url,
        timeout=GDELT_BATCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    content = response.content
    local_path.write_bytes(content)

    return content


def read_gkg_zip(content: bytes, source_url: str) -> pd.DataFrame:
    """
    Read a GDELT GKG ZIP payload into a dataframe.
    """

    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = archive.namelist()

        if not names:
            return pd.DataFrame()

        with archive.open(names[0]) as file:
            df = pd.read_csv(
                file,
                sep="\t",
                header=None,
                names=GKG_COLUMNS,
                dtype=str,
                engine="python",
                quoting=3,
                on_bad_lines="skip",
            )

    df["source_file_url"] = source_url
    df["gdelt_file_timestamp"] = parse_gdelt_datetime_from_url(source_url)

    return df


# ---------------------------------------------------------------------
# Enrichment logic
# ---------------------------------------------------------------------

def load_rankings() -> pd.DataFrame:
    """
    Load the project risk rankings file.
    """

    if not Path(RISK_RANKINGS_FILE).exists():
        raise FileNotFoundError(
            f"Risk rankings file not found: {RISK_RANKINGS_FILE}. "
            "Run the main model pipeline through risk scoring first."
        )

    rankings_df = pd.read_csv(RISK_RANKINGS_FILE)

    required_columns = ["country", "country_code"]

    missing_columns = [
        column for column in required_columns if column not in rankings_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Risk rankings file is missing required columns: "
            f"{missing_columns}"
        )

    return rankings_df


def initialize_country_records(rankings_df: pd.DataFrame) -> dict[str, dict[str, object]]:
    """
    Initialize one GDELT output record per modeled country.
    """

    records = {}

    for _, row in rankings_df.iterrows():
        country = str(row["country"])
        country_code = str(row.get("country_code", ""))

        records[country] = {
            "country": country,
            "country_code": country_code,
            "gdelt_batch_file_count": 0,
            "gdelt_matching_record_count": 0,
            "gdelt_matching_source_count": 0,
            "gdelt_average_tone": np.nan,
            "gdelt_latest_file_timestamp": "",
            "gdelt_latest_file_datetime": "",
            "gdelt_source_present": 0,
            "gdelt_confidence": "Unknown",
            "gdelt_days_since_update": np.nan,
        }

    return records


def update_country_record(
    record: dict[str, object],
    source_name: str,
    tone: float,
    file_timestamp: str,
) -> None:
    """
    Update a country aggregation record with one matching GKG row.
    """

    record["gdelt_matching_record_count"] = int(
        record["gdelt_matching_record_count"]
    ) + 1

    sources = record.setdefault("_sources", set())
    if isinstance(sources, set) and source_name:
        sources.add(source_name)

    tones = record.setdefault("_tones", [])
    if isinstance(tones, list) and not pd.isna(tone):
        tones.append(tone)

    if file_timestamp and file_timestamp > str(record.get("gdelt_latest_file_timestamp", "")):
        record["gdelt_latest_file_timestamp"] = file_timestamp
        record["gdelt_latest_file_datetime"] = gdelt_timestamp_to_iso(file_timestamp)


def process_gkg_dataframe(
    df: pd.DataFrame,
    country_map: dict[str, dict[str, object]],
    country_records: dict[str, dict[str, object]],
) -> int:
    """
    Process one GDELT GKG dataframe and update country records.

    Returns the number of GKG rows that matched the configured keywords.
    """

    if df.empty:
        return 0

    # Build a compact search field. We do not use full article text because GKG
    # files do not contain article body text.
    search_fields = [
        "DocumentIdentifier",
        "Themes",
        "V2Themes",
        "Organizations",
        "V2Organizations",
        "AllNames",
        "Amounts",
        "V2Locations",
        "Locations",
        "Counts",
        "V2Counts",
    ]

    for column in search_fields:
        if column not in df.columns:
            df[column] = ""

    df["_signal_text"] = df[search_fields].fillna("").agg(" ".join, axis=1)

    signal_df = df[df["_signal_text"].apply(row_matches_keywords)].copy()

    if signal_df.empty:
        return 0

    for _, row in signal_df.iterrows():
        # Prefer GDELT's structured location fields for country matching. The
        # document URL is only used as a fallback because URLs can create noisy
        # country-name matches.
        structured_location_text = " ".join(
            [
                str(row.get("V2Locations", "")),
                str(row.get("Locations", "")),
            ]
        )

        matched_countries = find_matching_countries(
            structured_location_text,
            country_map,
        )

        if not matched_countries:
            matched_countries = find_matching_countries(
                str(row.get("DocumentIdentifier", "")),
                country_map,
            )

        if not matched_countries:
            continue

        source_name = str(row.get("SourceCommonName", ""))
        tone = parse_tone(row.get("Tone", np.nan))
        file_timestamp = str(row.get("gdelt_file_timestamp", ""))

        for country in matched_countries:
            update_country_record(
                country_records[country],
                source_name=source_name,
                tone=tone,
                file_timestamp=file_timestamp,
            )

    return len(signal_df)


def finalize_country_records(
    country_records: dict[str, dict[str, object]],
    processed_file_count: int,
) -> pd.DataFrame:
    """
    Convert aggregation records into final enrichment dataframe.
    """

    output_rows = []

    for record in country_records.values():
        source_set = record.pop("_sources", set())
        tone_values = record.pop("_tones", [])

        if isinstance(source_set, set):
            source_count = len(source_set)
        else:
            source_count = 0

        if isinstance(tone_values, list) and tone_values:
            average_tone = float(np.mean(tone_values))
        else:
            average_tone = np.nan

        record["gdelt_batch_file_count"] = processed_file_count
        record["gdelt_matching_source_count"] = source_count
        record["gdelt_average_tone"] = round(average_tone, 3) if not pd.isna(average_tone) else np.nan

        if int(record["gdelt_matching_record_count"]) > 0:
            record["gdelt_source_present"] = 1
            record["gdelt_confidence"] = "Moderate"
            record["gdelt_days_since_update"] = 1

        output_rows.append(record)

    output_df = pd.DataFrame(output_rows)

    return output_df


def add_gdelt_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert batch GKG match counts into a 0-100 public-news signal score.
    """

    output = df.copy()

    record_counts = pd.to_numeric(
        output["gdelt_matching_record_count"],
        errors="coerce",
    ).fillna(0)

    source_counts = pd.to_numeric(
        output["gdelt_matching_source_count"],
        errors="coerce",
    ).fillna(0)

    # Negative tone can indicate greater risk salience, but it is a weak signal.
    tone_values = pd.to_numeric(
        output["gdelt_average_tone"],
        errors="coerce",
    )

    negative_tone = tone_values.apply(
        lambda value: max(0.0, -float(value)) if not pd.isna(value) else 0.0
    )

    max_record_count = float(record_counts.max())
    max_source_count = float(source_counts.max())
    max_negative_tone = float(negative_tone.max())

    if max_record_count <= 0:
        record_score = record_counts * 0
    else:
        record_score = record_counts.apply(
            lambda value: (math.log1p(value) / math.log1p(max_record_count)) * 100
        )

    if max_source_count <= 0:
        source_score = source_counts * 0
    else:
        source_score = source_counts.apply(
            lambda value: (math.log1p(value) / math.log1p(max_source_count)) * 100
        )

    if max_negative_tone <= 0:
        tone_score = negative_tone * 0
    else:
        tone_score = negative_tone.apply(
            lambda value: (value / max_negative_tone) * 100
        )

    output["gdelt_record_count_score"] = record_score.round(2)
    output["gdelt_source_diversity_score"] = source_score.round(2)
    output["gdelt_negative_tone_score"] = tone_score.round(2)

    output["gdelt_news_signal_score"] = (
        0.65 * output["gdelt_record_count_score"]
        + 0.25 * output["gdelt_source_diversity_score"]
        + 0.10 * output["gdelt_negative_tone_score"]
    ).round(2)

    output["gdelt_news_signal_level"] = output["gdelt_news_signal_score"].apply(
        classify_gdelt_signal
    )

    # Backward-compatible aliases for the earlier DOC API prototype.
    output["gdelt_article_count"] = output["gdelt_matching_record_count"]
    output["gdelt_query_status"] = np.where(
        output["gdelt_source_present"] == 1,
        "batch_match",
        "no_batch_match",
    )
    output["gdelt_lookback_days"] = np.nan

    return output


def build_gdelt_batch_enrichment(rankings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build GDELT batch enrichment from recent GKG files.
    """

    country_map = build_country_alias_map(rankings_df)
    country_records = initialize_country_records(rankings_df)

    gkg_urls = fetch_master_file_list()

    print(f"GDELT GKG files selected: {len(gkg_urls):,}")
    print(f"GDELT batch raw cache: {GDELT_BATCH_RAW_DIR}")

    processed_file_count = 0
    total_signal_rows = 0

    for index, url in enumerate(gkg_urls, start=1):
        print(f"[{index}/{len(gkg_urls)}] Processing {url}")

        try:
            content = download_gkg_zip(url)
            gkg_df = read_gkg_zip(content, source_url=url)
        except Exception as error:
            print(f"Could not process GDELT file {url}: {error}")
            continue

        signal_rows = process_gkg_dataframe(
            gkg_df,
            country_map=country_map,
            country_records=country_records,
        )

        total_signal_rows += signal_rows
        processed_file_count += 1

        print(f"Signal rows in file: {signal_rows:,}")

        if GDELT_BATCH_SLEEP_SECONDS > 0:
            time.sleep(float(GDELT_BATCH_SLEEP_SECONDS))

    print(f"Processed GDELT files: {processed_file_count:,}")
    print(f"Total keyword-matched GKG rows before country matching: {total_signal_rows:,}")

    output_df = finalize_country_records(
        country_records,
        processed_file_count=processed_file_count,
    )

    output_df = add_gdelt_scores(output_df)

    return output_df


def save_outputs(df: pd.DataFrame) -> None:
    """
    Save the GDELT enrichment table and chart.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    output_df = df.sort_values(
        "gdelt_news_signal_score",
        ascending=False,
        na_position="last",
    )

    output_df.to_csv(GDELT_NEWS_SIGNAL_ENRICHMENT_FILE, index=False)

    print("Saved GDELT 2.0 batch news signal enrichment table:")
    print(GDELT_NEWS_SIGNAL_ENRICHMENT_FILE)

    chart_df = output_df[
        output_df["gdelt_news_signal_score"].notna()
    ].head(15)

    if chart_df.empty:
        print("No GDELT signal scores available for charting.")
        return

    plt.figure(figsize=(12, 7))
    plt.barh(chart_df["country"], chart_df["gdelt_news_signal_score"])
    plt.gca().invert_yaxis()
    plt.title("Top 15 GDELT 2.0 Batch Public-News Signal Scores")
    plt.xlabel("GDELT 2.0 Batch Public-News Signal Score, 0-100")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE, dpi=300)
    plt.close()

    print("Saved GDELT 2.0 batch news signal chart:")
    print(TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE)


def print_summary(df: pd.DataFrame) -> None:
    """
    Print a concise GDELT enrichment summary.
    """

    total = len(df)
    matched = int((df["gdelt_source_present"] == 1).sum())
    total_records = int(
        pd.to_numeric(df["gdelt_matching_record_count"], errors="coerce")
        .fillna(0)
        .sum()
    )

    print("\nGDELT batch enrichment summary:")
    print(f"Records: {total:,}")
    print(f"Countries with GDELT signal: {matched:,} of {total:,}")
    print(f"Total matched GKG country records: {total_records:,}")

    if matched == 0:
        print(
            "\nNo countries matched the filtered GDELT rows. This can happen if "
            "the selected batch window has low threat-finance coverage or if "
            "GDELT location extraction did not identify modeled country names."
        )

    if "gdelt_news_signal_score" in df.columns:
        print("\nTop 10 GDELT 2.0 batch public-news signal scores:")
        print(
            df.sort_values("gdelt_news_signal_score", ascending=False)
            [
                [
                    "country",
                    "gdelt_matching_record_count",
                    "gdelt_matching_source_count",
                    "gdelt_average_tone",
                    "gdelt_news_signal_score",
                    "gdelt_news_signal_level",
                ]
            ]
            .head(10)
        )


def main() -> None:
    """
    Run the GDELT 2.0 batch-file public-news enrichment workflow.
    """

    print("=" * 70)
    print("GDELT 2.0 Batch Public-News Signal Enrichment")
    print("=" * 70)

    rankings_df = load_rankings()
    output_df = build_gdelt_batch_enrichment(rankings_df)

    save_outputs(output_df)
    print_summary(output_df)

    print("\nGDELT 2.0 batch public-news signal enrichment complete.")


if __name__ == "__main__":
    main()
