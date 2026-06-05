"""
Global Organized Crime Index enrichment module.

This module adds a supplemental organized-crime exposure layer to the terrorism
financing OSINT risk model.

The Global Organized Crime Index is used as country-level context for organized
crime exposure and resilience. It does not replace the baseline terrorism-
financing vulnerability score and does not constitute evidence of terrorism
financing, criminality, sanctions exposure, or illicit activity.

Expected output:
- outputs/tables/organized_crime_enrichment.csv
- outputs/charts/top_15_organized_crime_vulnerability_scores.png
"""

from __future__ import annotations

from pathlib import Path
import re
import tempfile
import unicodedata
from typing import Iterable

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

RAW_DATA_DIR = getattr(
    config,
    "RAW_DATA_DIR",
    BASE_DIR / "data" / "raw",
)

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

RISK_RANKINGS_FILE = getattr(
    config,
    "RISK_RANKINGS_FILE",
    TABLES_DIR / "terrorism_financing_country_risk_rankings.csv",
)

GLOBAL_ORGANIZED_CRIME_INDEX_URL = getattr(
    config,
    "GLOBAL_ORGANIZED_CRIME_INDEX_URL",
    "https://ocindex.net/assets/downloads/global_oc_index.xlsx",
)

GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE = getattr(
    config,
    "GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE",
    RAW_DATA_DIR / "global_oc_index.xlsx",
)

ORGANIZED_CRIME_ENRICHMENT_FILE = getattr(
    config,
    "ORGANIZED_CRIME_ENRICHMENT_FILE",
    TABLES_DIR / "organized_crime_enrichment.csv",
)

TOP_15_ORGANIZED_CRIME_CHART_FILE = getattr(
    config,
    "TOP_15_ORGANIZED_CRIME_CHART_FILE",
    CHARTS_DIR / "top_15_organized_crime_vulnerability_scores.png",
)

TARGET_OC_INDEX_YEAR = getattr(config, "TARGET_OC_INDEX_YEAR", None)


COUNTRY_ALIASES = {
    "bahamas the": "bahamas",
    "bolivia": "bolivia",
    "bolivia plurinational state of": "bolivia",
    "brunei darussalam": "brunei",
    "cape verde": "cabo verde",
    "czechia": "czech republic",
    "congo dem rep": "democratic republic of congo",
    "congo democratic republic": "democratic republic of congo",
    "congo democratic republic of": "democratic republic of congo",
    "democratic republic of the congo": "democratic republic of congo",
    "congo rep": "republic of congo",
    "congo republic": "republic of congo",
    "egypt arab rep": "egypt",
    "gambia the": "gambia",
    "hong kong sar china": "hong kong",
    "iran islamic rep": "iran",
    "iran islamic republic of": "iran",
    "korea dem peoples rep": "north korea",
    "korea republic of": "south korea",
    "korea rep": "south korea",
    "kyrgyz republic": "kyrgyzstan",
    "lao pdr": "laos",
    "micronesia fed sts": "micronesia",
    "russian federation": "russia",
    "slovak republic": "slovakia",
    "st kitts and nevis": "saint kitts and nevis",
    "st lucia": "saint lucia",
    "st vincent and the grenadines": "saint vincent and the grenadines",
    "syrian arab republic": "syria",
    "turkiye": "turkey",
    "venezuela rb": "venezuela",
    "venezuela bolivarian republic of": "venezuela",
    "viet nam": "vietnam",
    "yemen rep": "yemen",
}


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def normalize_text(value: object) -> str:
    """
    Normalize strings for matching.

    This removes accents before applying the normal text cleanup. That matters
    for country names such as "Côte d'Ivoire" in the Global Organized Crime
    Index and "Cote d'Ivoire" in the World Bank / model output.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_country_key(value: object) -> str:
    """
    Normalize country names and apply common World Bank / index aliases.
    """

    key = normalize_text(value)

    return COUNTRY_ALIASES.get(key, key)


def normalize_column_name(value: object) -> str:
    """
    Normalize a dataframe column name.
    """

    return normalize_text(value).replace(" ", "_")


def safe_numeric(series: pd.Series) -> pd.Series:
    """
    Convert a series to numeric and preserve missing values.
    """

    return pd.to_numeric(series, errors="coerce")


def classify_score(score: float) -> str:
    """
    Classify a 0-100 score.
    """

    if pd.isna(score):
        return "Unknown"

    if score >= 80:
        return "Very High"

    if score >= 65:
        return "High"

    if score >= 45:
        return "Moderate"

    if score > 0:
        return "Low"

    return "No Data"


def find_column(
    columns: Iterable[str],
    include_any: Iterable[str],
    exclude_any: Iterable[str] | None = None,
) -> str | None:
    """
    Return the first column whose normalized name contains one of the include
    terms and none of the exclude terms.
    """

    exclude_any = exclude_any or []

    for column in columns:
        normalized = normalize_column_name(column)

        if any(term in normalized for term in include_any) and not any(
            term in normalized for term in exclude_any
        ):
            return column

    return None


# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------

def download_index_file(
    force_refresh: bool = False,
    timeout: int = 90,
) -> Path:
    """
    Download the Global Organized Crime Index workbook if needed.
    """

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE.exists() and not force_refresh:
        print("Using existing Global Organized Crime Index workbook:")
        print(GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE)
        return GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE

    print("Downloading Global Organized Crime Index workbook...")
    print(GLOBAL_ORGANIZED_CRIME_INDEX_URL)

    response = requests.get(GLOBAL_ORGANIZED_CRIME_INDEX_URL, timeout=timeout)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        tmp_file.write(response.content)
        tmp_path = Path(tmp_file.name)

    GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE.write_bytes(tmp_path.read_bytes())
    tmp_path.unlink(missing_ok=True)

    print("Saved Global Organized Crime Index workbook to:")
    print(GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE)

    return GLOBAL_ORGANIZED_CRIME_INDEX_RAW_FILE


def infer_sheet_year(sheet_name: str) -> int | None:
    """
    Infer an index year from an Excel sheet name.
    """

    match = re.search(r"(20\d{2})", str(sheet_name))

    if match:
        return int(match.group(1))

    return None


def candidate_columns_exist(df: pd.DataFrame) -> bool:
    """
    Check whether a sheet appears to contain country-level OC Index data.
    """

    columns = list(df.columns)

    country_col = find_column(
        columns,
        ["country", "jurisdiction", "state"],
        ["region", "continent", "rank"],
    )

    criminality_col = find_column(
        columns,
        ["criminality"],
        ["rank", "change"],
    )

    resilience_col = find_column(
        columns,
        ["resilience"],
        ["rank", "change"],
    )

    return country_col is not None and (
        criminality_col is not None or resilience_col is not None
    )


def read_sheet_with_header_detection(
    workbook_path: Path,
    sheet_name: str,
    max_header_rows: int = 8,
) -> pd.DataFrame | None:
    """
    Try several header rows and return the first dataframe that looks usable.
    """

    for header_row in range(max_header_rows + 1):
        try:
            df = pd.read_excel(
                workbook_path,
                sheet_name=sheet_name,
                header=header_row,
            )
        except Exception:
            continue

        if df.empty:
            continue

        df = df.dropna(how="all").copy()
        df.columns = [str(column).strip() for column in df.columns]

        if candidate_columns_exist(df):
            return df

    return None


def extract_country_level_records(workbook_path: Path) -> pd.DataFrame:
    """
    Extract country-level criminality and resilience records from the workbook.

    The official workbook can change sheet names or header rows between index
    releases. This function searches all sheets and keeps the sheets that have
    recognizable country, criminality, and/or resilience columns.
    """

    excel = pd.ExcelFile(workbook_path)

    records = []

    for sheet_name in excel.sheet_names:
        sheet_df = read_sheet_with_header_detection(workbook_path, sheet_name)

        if sheet_df is None or sheet_df.empty:
            continue

        columns = list(sheet_df.columns)

        country_col = find_column(
            columns,
            ["country", "jurisdiction", "state"],
            ["region", "continent", "rank"],
        )
        iso_col = find_column(
            columns,
            ["iso3", "iso_3", "iso", "code"],
            ["region", "rank"],
        )
        year_col = find_column(
            columns,
            ["year", "edition", "assessment"],
            ["change"],
        )
        criminality_col = find_column(
            columns,
            ["criminality"],
            ["rank", "change"],
        )
        criminal_markets_col = find_column(
            columns,
            ["criminal_markets", "markets"],
            ["rank", "change"],
        )
        criminal_actors_col = find_column(
            columns,
            ["criminal_actors", "actors"],
            ["rank", "change"],
        )
        resilience_col = find_column(
            columns,
            ["resilience"],
            ["rank", "change"],
        )

        if country_col is None:
            continue

        output = pd.DataFrame()
        output["country"] = sheet_df[country_col].astype(str).str.strip()

        if iso_col is not None:
            output["iso3"] = sheet_df[iso_col].astype(str).str.strip().str.upper()
        else:
            output["iso3"] = ""

        if year_col is not None:
            output["oc_index_year"] = safe_numeric(sheet_df[year_col])
        else:
            output["oc_index_year"] = infer_sheet_year(sheet_name)

        if criminality_col is not None:
            output["criminality_score"] = safe_numeric(sheet_df[criminality_col])
        else:
            output["criminality_score"] = np.nan

        if criminal_markets_col is not None:
            output["criminal_markets_score"] = safe_numeric(
                sheet_df[criminal_markets_col]
            )
        else:
            output["criminal_markets_score"] = np.nan

        if criminal_actors_col is not None:
            output["criminal_actors_score"] = safe_numeric(
                sheet_df[criminal_actors_col]
            )
        else:
            output["criminal_actors_score"] = np.nan

        if resilience_col is not None:
            output["resilience_score"] = safe_numeric(sheet_df[resilience_col])
        else:
            output["resilience_score"] = np.nan

        output["source_sheet"] = str(sheet_name)
        output["country_merge_key"] = output["country"].apply(normalize_country_key)

        output = output[
            output["country_merge_key"].ne("")
            & output["country"].notna()
            & (
                output["criminality_score"].notna()
                | output["resilience_score"].notna()
            )
        ].copy()

        if not output.empty:
            records.append(output)

    if not records:
        raise ValueError(
            "Could not identify country-level criminality/resilience records "
            "in the Global Organized Crime Index workbook."
        )

    combined = pd.concat(records, ignore_index=True)

    # Remove aggregate or metadata rows if they slipped through.
    combined = combined[
        ~combined["country_merge_key"].isin(
            {
                "country",
                "global",
                "world",
                "average",
                "regional average",
                "continent",
                "region",
            }
        )
    ].copy()

    return combined


def select_latest_index_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    Select the target or latest available Organized Crime Index year.
    """

    df = df.copy()

    if TARGET_OC_INDEX_YEAR is not None and "oc_index_year" in df.columns:
        target_df = df[df["oc_index_year"] == TARGET_OC_INDEX_YEAR].copy()

        if not target_df.empty:
            df = target_df

    elif "oc_index_year" in df.columns and df["oc_index_year"].notna().any():
        latest_year = int(df["oc_index_year"].max())
        df = df[df["oc_index_year"] == latest_year].copy()
    else:
        # Prefer records from a sheet name that contains 2025 if no explicit year
        # column exists.
        preferred = df[
            df["source_sheet"].astype(str).str.contains("2025", case=False, na=False)
        ].copy()

        if not preferred.empty:
            df = preferred

    df = df.sort_values(
        ["country_merge_key", "criminality_score", "resilience_score"],
        ascending=[True, False, True],
    )

    df = df.drop_duplicates(subset=["country_merge_key"], keep="first")

    return df


# ---------------------------------------------------------------------
# Scoring and merge
# ---------------------------------------------------------------------

def add_organized_crime_scores(index_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create organized-crime exposure and vulnerability fields.

    The OC Index criminality and resilience scores are generally expressed on
    0-10 style scales. The output scores are converted to 0-100 for consistency
    with the project.
    """

    df = index_df.copy()

    criminality = df["criminality_score"].clip(lower=0, upper=10)
    resilience = df["resilience_score"].clip(lower=0, upper=10)

    # Criminality is direct exposure. Lower resilience increases vulnerability.
    df["organized_crime_exposure_score"] = (criminality * 10).round(2)
    df["organized_crime_resilience_gap_score"] = ((10 - resilience) * 10).round(2)

    df["organized_crime_score"] = (
        0.65 * df["organized_crime_exposure_score"].fillna(50)
        + 0.35 * df["organized_crime_resilience_gap_score"].fillna(50)
    ).round(2)

    df["organized_crime_level"] = df["organized_crime_score"].apply(classify_score)
    df["organized_crime_source_present"] = 1
    df["organized_crime_confidence"] = "Moderate to High"
    df["organized_crime_days_since_update"] = 365

    return df


def load_rankings() -> pd.DataFrame:
    """
    Load the project risk rankings file for country matching.
    """

    if not RISK_RANKINGS_FILE.exists():
        raise FileNotFoundError(
            f"Risk rankings file not found: {RISK_RANKINGS_FILE}. "
            "Run main.py through the risk scoring/modeling steps first."
        )

    rankings_df = pd.read_csv(RISK_RANKINGS_FILE)
    rankings_df["country_merge_key"] = rankings_df["country"].apply(
        normalize_country_key
    )

    if "country_code" in rankings_df.columns:
        rankings_df["iso3"] = rankings_df["country_code"].astype(str).str.upper()
    elif "iso3" not in rankings_df.columns:
        rankings_df["iso3"] = ""

    return rankings_df


def merge_with_project_countries(
    rankings_df: pd.DataFrame,
    index_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge OC Index data with modeled project countries.

    ISO3 matching is used first where possible. Country-name matching is used as
    a fallback because some OC Index workbooks or exports may not expose ISO3.
    """

    ranking_cols = ["country", "country_code", "tf_vulnerability_score", "iso3", "country_merge_key"]
    ranking_cols = [col for col in ranking_cols if col in rankings_df.columns]

    base = rankings_df[ranking_cols].copy()

    index_cols = [
        "country_merge_key",
        "iso3",
        "oc_index_year",
        "criminality_score",
        "criminal_markets_score",
        "criminal_actors_score",
        "resilience_score",
        "organized_crime_exposure_score",
        "organized_crime_resilience_gap_score",
        "organized_crime_score",
        "organized_crime_level",
        "organized_crime_source_present",
        "organized_crime_confidence",
        "organized_crime_days_since_update",
        "source_sheet",
    ]

    index_cols = [col for col in index_cols if col in index_df.columns]
    prepared = index_df[index_cols].copy()

    iso_merge = base.merge(
        prepared.drop(columns=["country_merge_key"], errors="ignore"),
        on="iso3",
        how="left",
        suffixes=("", "_oc"),
    )

    name_merge = base[["country_merge_key"]].merge(
        prepared.drop(columns=["iso3"], errors="ignore"),
        on="country_merge_key",
        how="left",
        suffixes=("", "_name"),
    )

    value_cols = [
        col
        for col in prepared.columns
        if col not in {"country_merge_key", "iso3"}
    ]

    for col in value_cols:
        if col in iso_merge.columns and col in name_merge.columns:
            iso_merge[col] = iso_merge[col].combine_first(name_merge[col])
        elif col not in iso_merge.columns and col in name_merge.columns:
            iso_merge[col] = name_merge[col]

    iso_merge["organized_crime_source_present"] = iso_merge[
        "organized_crime_source_present"
    ].fillna(0).astype(int)

    iso_merge["organized_crime_confidence"] = iso_merge[
        "organized_crime_confidence"
    ].fillna("Unknown")

    return iso_merge


def save_outputs(df: pd.DataFrame) -> None:
    """
    Save organized-crime enrichment table and chart.
    """

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    output_columns = [
        "country",
        "country_code",
        "iso3",
        "tf_vulnerability_score",
        "oc_index_year",
        "criminality_score",
        "criminal_markets_score",
        "criminal_actors_score",
        "resilience_score",
        "organized_crime_exposure_score",
        "organized_crime_resilience_gap_score",
        "organized_crime_score",
        "organized_crime_level",
        "organized_crime_source_present",
        "organized_crime_confidence",
        "organized_crime_days_since_update",
        "source_sheet",
    ]

    output_columns = [col for col in output_columns if col in df.columns]

    output_df = df[output_columns].sort_values(
        "organized_crime_score",
        ascending=False,
        na_position="last",
    )

    output_df.to_csv(ORGANIZED_CRIME_ENRICHMENT_FILE, index=False)

    print("Saved organized-crime enrichment table:")
    print(ORGANIZED_CRIME_ENRICHMENT_FILE)

    chart_df = output_df[
        output_df["organized_crime_score"].notna()
    ].head(15)

    if chart_df.empty:
        print("No organized-crime scores available for charting.")
        return

    plt.figure(figsize=(12, 7))
    plt.barh(chart_df["country"], chart_df["organized_crime_score"])
    plt.gca().invert_yaxis()
    plt.title("Top 15 Organized Crime Vulnerability Scores")
    plt.xlabel("Organized Crime Vulnerability Score, 0-100")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(TOP_15_ORGANIZED_CRIME_CHART_FILE, dpi=300)
    plt.close()

    print("Saved organized-crime chart:")
    print(TOP_15_ORGANIZED_CRIME_CHART_FILE)


def print_summary(df: pd.DataFrame) -> None:
    """
    Print a concise summary.
    """

    matched = int(df["organized_crime_source_present"].sum())
    total = len(df)

    print("\nOrganized crime enrichment summary:")
    print(f"Matched records: {matched:,} of {total:,}")

    if "organized_crime_score" in df.columns:
        print("\nTop 10 organized crime vulnerability scores:")
        print(
            df.sort_values("organized_crime_score", ascending=False)
            [
                [
                    "country",
                    "oc_index_year",
                    "criminality_score",
                    "resilience_score",
                    "organized_crime_score",
                    "organized_crime_level",
                ]
            ]
            .head(10)
        )


def main() -> None:
    """
    Run the Global Organized Crime Index enrichment workflow.
    """

    print("=" * 70)
    print("Global Organized Crime Index Enrichment")
    print("=" * 70)

    workbook_path = download_index_file(force_refresh=False)
    raw_index_df = extract_country_level_records(workbook_path)
    latest_index_df = select_latest_index_records(raw_index_df)
    scored_index_df = add_organized_crime_scores(latest_index_df)

    rankings_df = load_rankings()
    merged_df = merge_with_project_countries(rankings_df, scored_index_df)

    save_outputs(merged_df)
    print_summary(merged_df)

    print("\nGlobal Organized Crime Index enrichment complete.")


if __name__ == "__main__":
    main()
