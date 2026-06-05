"""
Streamlit dashboard for the terrorism financing OSINT risk model.

Run from the project root with:

    streamlit run app.py

This dashboard reads the generated outputs from:
- outputs/tables/
- outputs/charts/
- outputs/reports/

It does not recalculate the model. Run main.py first to refresh the data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import (
    PROJECT_TITLE,
    STUDY_YEAR,
    RISK_RANKINGS_FILE,
    RISK_TIER_SUMMARY_FILE,
    MODEL_PERFORMANCE_FILE,
    FALSE_POSITIVES_FILE,
    FALSE_NEGATIVES_FILE,
    SENSITIVITY_OVERLAP_FILE,
    CURRENT_FATF_STATUS_COMPARISON_FILE,
    CONFLICT_DATA_SUPPLEMENT_FILE,
    TOP_RISK_DRIVERS_FILE,
    REGIONAL_RISK_SUMMARY_FILE,
    ADDITIONAL_RISK_FACTOR_SUMMARY_FILE,
    WORD_REPORT_FILE,
    PDF_REPORT_FILE,
    TOP_15_RISK_CHART_FILE,
    RISK_SCORE_PROBABILITY_CHART_FILE,
    GREY_LIST_PROBABILITY_TOP_20_CHART_FILE,
    RISK_TIER_DISTRIBUTION_CHART_FILE,
    SENSITIVITY_OVERLAP_CHART_FILE,
    TOP_15_CONFLICT_FATALITIES_CHART_FILE,
    REGIONAL_AVERAGE_RISK_CHART_FILE,
    REGIONAL_FATF_COUNT_CHART_FILE,
    CURRENT_FATF_STATUS_COMPARISON_CHART_FILE,
    TOP_15_COLLECTION_PRIORITY_CHART_FILE,
    INTELLIGENCE_GAP_DISTRIBUTION_CHART_FILE,
    ACLED_SIGNAL_TOP_15_CHART_FILE,
    ACLED_SIGNAL_ENRICHMENT_FILE,
    ORGANIZED_CRIME_ENRICHMENT_FILE,
    TOP_15_ORGANIZED_CRIME_CHART_FILE,
    GDELT_NEWS_SIGNAL_ENRICHMENT_FILE,
    TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE,
)


# ---------------------------------------------------
# Threat finance intelligence output files
# ---------------------------------------------------

THREAT_FINANCE_COLLECTION_PRIORITIES_FILE = Path(
    "outputs/tables/threat_finance_collection_priorities.csv"
)

THREAT_FINANCE_SOURCE_REGISTER_FILE = Path(
    "outputs/tables/source_register.csv"
)

ORGANIZED_CRIME_ENRICHMENT_FILE = Path(
    "outputs/tables/organized_crime_enrichment.csv"
)

TOP_15_ORGANIZED_CRIME_CHART_FILE = Path(
    "outputs/charts/top_15_organized_crime_vulnerability_scores.png"
)

GDELT_NEWS_SIGNAL_ENRICHMENT_FILE = Path(
    "outputs/tables/gdelt_news_signal_enrichment.csv"
)

TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE = Path(
    "outputs/charts/top_15_gdelt_news_signal_scores.png"
)


# ---------------------------------------------------
# Page setup
# ---------------------------------------------------

st.set_page_config(
    page_title="Terrorism Financing OSINT Risk Dashboard",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------
# Helper functions
# ---------------------------------------------------

@st.cache_data
def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    """
    Read a CSV file if it exists.
    """

    if not Path(path).exists():
        return None

    try:
        return pd.read_csv(path)
    except Exception:
        return None


def display_dataframe(
    df: pd.DataFrame | None,
    title: str,
    max_rows: int | None = None,
) -> None:
    """
    Display a dataframe safely.
    """

    st.subheader(title)

    if df is None or df.empty:
        st.warning("Data file not available. Run the full pipeline first.")
        return

    if max_rows is not None:
        st.dataframe(df.head(max_rows), width="stretch")
    else:
        st.dataframe(df, width="stretch")


def display_chart(image_path: Path, caption: str) -> None:
    """
    Display a chart image if available.
    """

    if Path(image_path).exists():
        st.image(str(image_path), caption=caption, width="stretch")
    else:
        st.info(f"Chart not found: {image_path}")


def format_percent(value: float | int | str | None) -> str:
    """
    Format a decimal probability as a percentage.
    """

    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_number(value: float | int | str | None, decimals: int = 2) -> str:
    """
    Format numeric values safely.
    """

    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def yes_no(value: float | int | str | bool | None) -> str:
    """
    Convert 0/1 values to No/Yes.
    """

    try:
        return "Yes" if int(value) == 1 else "No"
    except (TypeError, ValueError):
        return "N/A"


def add_download_button(path: Path, label: str, mime_type: str) -> None:
    """
    Add a file download button if the file exists.
    """

    if not Path(path).exists():
        st.info(f"{label} not available yet.")
        return

    with open(path, "rb") as file:
        st.download_button(
            label=label,
            data=file,
            file_name=Path(path).name,
            mime=mime_type,
        )


# ---------------------------------------------------
# Load data
# ---------------------------------------------------

rankings_df = read_csv_if_exists(RISK_RANKINGS_FILE)
risk_tier_df = read_csv_if_exists(RISK_TIER_SUMMARY_FILE)
performance_df = read_csv_if_exists(MODEL_PERFORMANCE_FILE)
false_positive_df = read_csv_if_exists(FALSE_POSITIVES_FILE)
false_negative_df = read_csv_if_exists(FALSE_NEGATIVES_FILE)
sensitivity_df = read_csv_if_exists(SENSITIVITY_OVERLAP_FILE)
current_fatf_df = read_csv_if_exists(CURRENT_FATF_STATUS_COMPARISON_FILE)
conflict_df = read_csv_if_exists(CONFLICT_DATA_SUPPLEMENT_FILE)
top_drivers_df = read_csv_if_exists(TOP_RISK_DRIVERS_FILE)
regional_df = read_csv_if_exists(REGIONAL_RISK_SUMMARY_FILE)
additional_summary_df = read_csv_if_exists(ADDITIONAL_RISK_FACTOR_SUMMARY_FILE)
collection_priority_df = read_csv_if_exists(THREAT_FINANCE_COLLECTION_PRIORITIES_FILE)
source_register_df = read_csv_if_exists(THREAT_FINANCE_SOURCE_REGISTER_FILE)
acled_signal_df = read_csv_if_exists(ACLED_SIGNAL_ENRICHMENT_FILE)
organized_crime_df = read_csv_if_exists(ORGANIZED_CRIME_ENRICHMENT_FILE)
gdelt_news_df = read_csv_if_exists(GDELT_NEWS_SIGNAL_ENRICHMENT_FILE)


# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select section",
    [
        "Overview",
        "Country Rankings",
        "Model Results",
        "Enhanced Analysis",
        "Intelligence Gap Analysis",
        "ACLED Signal Layer",
        "Organized Crime Layer",
        "GDELT 2.0 Batch News Signal Layer",
        "Current FATF Context",
        "Conflict Supplement",
        "Regional Analysis",
        "Charts",
        "Downloads",
        "Methodology Notes",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("Run `python main.py` before opening the dashboard.")


# ---------------------------------------------------
# Header
# ---------------------------------------------------

st.title("Terrorism Financing OSINT Risk Dashboard")
st.caption(PROJECT_TITLE)

st.markdown(
    f"""
    **Target study year:** {STUDY_YEAR}

    This dashboard presents a defensive, country-level open-source intelligence
    model for terrorism-financing vulnerability screening. It is not evidence of
    terrorism-financing activity and does not identify individuals, entities,
    transactions, wallets, accounts, or networks.
    """
)


# ---------------------------------------------------
# Overview
# ---------------------------------------------------

if page == "Overview":
    st.header("Project Overview")

    if rankings_df is None or rankings_df.empty:
        st.warning("Risk rankings are not available. Run the full pipeline first.")
    else:
        total_countries = len(rankings_df)
        fatf_count = int(rankings_df["fatf_grey_list"].sum())
        top_row = rankings_df.sort_values(
            "tf_vulnerability_score",
            ascending=False,
        ).iloc[0]

        average_score = rankings_df["tf_vulnerability_score"].mean()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Countries", f"{total_countries:,}")
        col2.metric("FATF Grey-List Cases", f"{fatf_count:,}")
        col3.metric("Average Score", format_number(average_score, 2))
        col4.metric(
            "Highest-Risk Country",
            str(top_row["country"]),
            format_number(top_row["tf_vulnerability_score"], 2),
        )

        st.subheader("Top 10 Countries by Vulnerability Score")

        top_display = rankings_df.sort_values(
            "tf_vulnerability_score",
            ascending=False,
        ).head(10).copy()

        if "predicted_grey_list_probability" in top_display.columns:
            top_display["predicted_probability_pct"] = top_display[
                "predicted_grey_list_probability"
            ].apply(format_percent)

        top_display["fatf_grey_list_label"] = top_display["fatf_grey_list"].apply(
            yes_no
        )

        st.dataframe(
            top_display[
                [
                    "risk_rank",
                    "country",
                    "country_code",
                    "tf_vulnerability_score",
                    "fatf_grey_list_label",
                    "predicted_probability_pct",
                ]
            ].rename(
                columns={
                    "risk_rank": "Rank",
                    "country": "Country",
                    "country_code": "ISO3",
                    "tf_vulnerability_score": "Risk Score",
                    "fatf_grey_list_label": "FATF Grey List",
                    "predicted_probability_pct": "Predicted Probability",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Core Interpretation")

    st.markdown(
        """
        The score is based on public governance and economic indicators:
        corruption risk, rule-of-law risk, political instability risk, low-income
        risk, inflation stress, and unemployment stress.

        UCDP conflict exposure, ACLED recent conflict and unrest signals,
        Global Organized Crime Index context, GDELT 2.0 batch public-news signals,
        sanctions, regional summaries, current FATF status, and policy context
        are supplemental layers. They improve interpretation and collection
        prioritization but do not replace the baseline vulnerability score.
        """
    )


# ---------------------------------------------------
# Country Rankings
# ---------------------------------------------------

elif page == "Country Rankings":
    st.header("Country Rankings")

    if rankings_df is None or rankings_df.empty:
        st.warning("Risk rankings are not available. Run the full pipeline first.")
    else:
        country_options = sorted(rankings_df["country"].dropna().unique().tolist())

        selected_countries = st.multiselect(
            "Filter by country",
            options=country_options,
            default=[],
        )

        min_score, max_score = st.slider(
            "Risk score range",
            min_value=0.0,
            max_value=100.0,
            value=(0.0, 100.0),
            step=1.0,
        )

        fatf_filter = st.selectbox(
            "FATF grey-list filter",
            ["All", "Grey-listed only", "Not grey-listed"],
        )

        filtered = rankings_df.copy()

        filtered = filtered[
            filtered["tf_vulnerability_score"].between(min_score, max_score)
        ]

        if selected_countries:
            filtered = filtered[filtered["country"].isin(selected_countries)]

        if fatf_filter == "Grey-listed only":
            filtered = filtered[filtered["fatf_grey_list"] == 1]
        elif fatf_filter == "Not grey-listed":
            filtered = filtered[filtered["fatf_grey_list"] == 0]

        display_df = filtered.copy()

        if "predicted_grey_list_probability" in display_df.columns:
            display_df["predicted_probability_pct"] = display_df[
                "predicted_grey_list_probability"
            ].apply(format_percent)

        display_df["fatf_grey_list_label"] = display_df["fatf_grey_list"].apply(
            yes_no
        )

        columns_to_show = [
            "risk_rank",
            "country",
            "country_code",
            "tf_vulnerability_score",
            "fatf_grey_list_label",
            "predicted_probability_pct",
            "corruption_risk_scaled",
            "rule_of_law_risk_scaled",
            "political_instability_risk_scaled",
            "low_income_risk_scaled",
            "inflation_risk_scaled",
            "unemployment_risk_scaled",
        ]

        available_columns = [
            column for column in columns_to_show if column in display_df.columns
        ]

        st.dataframe(
            display_df[available_columns].rename(
                columns={
                    "risk_rank": "Rank",
                    "country": "Country",
                    "country_code": "ISO3",
                    "tf_vulnerability_score": "Risk Score",
                    "fatf_grey_list_label": "FATF Grey List",
                    "predicted_probability_pct": "Predicted Probability",
                    "corruption_risk_scaled": "Corruption Risk",
                    "rule_of_law_risk_scaled": "Rule of Law Risk",
                    "political_instability_risk_scaled": "Instability Risk",
                    "low_income_risk_scaled": "Low Income Risk",
                    "inflation_risk_scaled": "Inflation Risk",
                    "unemployment_risk_scaled": "Unemployment Risk",
                }
            ),
            width="stretch",
            hide_index=True,
        )


# ---------------------------------------------------
# Model Results
# ---------------------------------------------------

elif page == "Model Results":
    st.header("Model Results")

    st.markdown(
        """
        The model estimates FATF grey-list probability using the scaled core
        vulnerability indicators. Because FATF grey-listed jurisdictions are a
        minority of the dataset, the classification model uses balanced class
        weights.
        """
    )

    display_dataframe(performance_df, "Model Performance")

    if rankings_df is not None and not rankings_df.empty:
        st.subheader("Top Predicted Grey-List Probabilities")

        probability_df = rankings_df.sort_values(
            "predicted_grey_list_probability",
            ascending=False,
        ).head(20).copy()

        probability_df["Predicted Probability"] = probability_df[
            "predicted_grey_list_probability"
        ].apply(format_percent)

        probability_df["FATF Grey List"] = probability_df["fatf_grey_list"].apply(
            yes_no
        )

        st.dataframe(
            probability_df[
                [
                    "country",
                    "country_code",
                    "tf_vulnerability_score",
                    "FATF Grey List",
                    "Predicted Probability",
                ]
            ].rename(
                columns={
                    "country": "Country",
                    "country_code": "ISO3",
                    "tf_vulnerability_score": "Risk Score",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    display_chart(
        RISK_SCORE_PROBABILITY_CHART_FILE,
        "Risk Score vs Predicted FATF Grey-List Probability",
    )


# ---------------------------------------------------
# Enhanced Analysis
# ---------------------------------------------------

elif page == "Enhanced Analysis":
    st.header("Enhanced Analysis")

    display_dataframe(risk_tier_df, "Risk Tier Summary")
    display_dataframe(sensitivity_df, "Sensitivity Overlap Summary")

    tab1, tab2, tab3 = st.tabs(
        ["Top Risk Drivers", "False Positives", "False Negatives"]
    )

    with tab1:
        display_dataframe(top_drivers_df, "Top Risk Drivers", max_rows=25)

    with tab2:
        display_dataframe(false_positive_df, "False Positives", max_rows=25)

    with tab3:
        display_dataframe(false_negative_df, "False Negatives", max_rows=25)



# ---------------------------------------------------
# Intelligence Gap Analysis
# ---------------------------------------------------

elif page == "Intelligence Gap Analysis":
    st.header("Threat Finance Intelligence Gap Analysis")

    st.markdown(
        """
        This section adds an intelligence-cycle layer to the model. The baseline
        score estimates country-level structural vulnerability. The intelligence
        gap layer asks what public-source information an analyst should collect
        next to validate, challenge, or update the assessment.

        The output is a collection-priority aid for analyst review. It is not a
        terrorism determination, sanctions finding, or allegation of illicit
        activity.
        """
    )

    if collection_priority_df is None or collection_priority_df.empty:
        st.warning(
            "Threat finance collection-priority data is not available. "
            "Run `python main.py` first."
        )
    else:
        display_df = collection_priority_df.copy()

        immediate_count = (
            int(
                (
                    display_df["collection_priority_level"]
                    == "Immediate Review"
                ).sum()
            )
            if "collection_priority_level" in display_df.columns
            else 0
        )

        high_count = (
            int(
                (
                    display_df["collection_priority_level"]
                    == "High Priority"
                ).sum()
            )
            if "collection_priority_level" in display_df.columns
            else 0
        )

        avg_gap = (
            display_df["intelligence_gap_score"].mean()
            if "intelligence_gap_score" in display_df.columns
            else None
        )

        avg_priority = (
            display_df["collection_priority_score"].mean()
            if "collection_priority_score" in display_df.columns
            else None
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Country Records", f"{len(display_df):,}")
        col2.metric("Immediate Review", f"{immediate_count:,}")
        col3.metric("High Priority", f"{high_count:,}")
        col4.metric(
            "Avg. Collection Priority",
            format_number(avg_priority, 2),
            f"Avg. gap {format_number(avg_gap, 2)}",
        )

        if "collection_priority_score" in display_df.columns:
            display_df = display_df.sort_values(
                "collection_priority_score",
                ascending=False,
            )

        st.subheader("Top Collection Priorities")

        table_columns = [
            "country",
            "iso3",
            "baseline_tf_risk_score",
            "baseline_tf_risk_level",
            "live_signal_score",
            "acled_acled_conflict_signal_score",
            "acled_acled_signal_level",
            "organized_crime_organized_crime_score",
            "organized_crime_organized_crime_level",
            "gdelt_gdelt_news_signal_score",
            "gdelt_gdelt_news_signal_level",
            "source_staleness_score",
            "intelligence_gap_score",
            "intelligence_gap_level",
            "collection_priority_score",
            "collection_priority_level",
            "recommended_collection_focus",
        ]

        available_columns = [
            column for column in table_columns if column in display_df.columns
        ]

        renamed = display_df[available_columns].rename(
            columns={
                "country": "Country",
                "iso3": "ISO3",
                "baseline_tf_risk_score": "Baseline Risk",
                "baseline_tf_risk_level": "Risk Level",
                "live_signal_score": "Live Signal",
                "acled_acled_conflict_signal_score": "ACLED Signal",
                "acled_acled_signal_level": "ACLED Level",
                "organized_crime_organized_crime_score": "OC Score",
                "organized_crime_organized_crime_level": "OC Level",
                "gdelt_gdelt_news_signal_score": "GDELT Signal",
                "gdelt_gdelt_news_signal_level": "GDELT Level",
                "source_staleness_score": "Source Staleness",
                "intelligence_gap_score": "Intel Gap",
                "intelligence_gap_level": "Gap Level",
                "collection_priority_score": "Collection Priority",
                "collection_priority_level": "Priority Level",
                "recommended_collection_focus": "Recommended Focus",
            }
        )

        st.dataframe(
            renamed.head(50),
            width="stretch",
            hide_index=True,
        )

        st.subheader("Analyst Notes")

        if "analyst_note" in display_df.columns:
            selected_country = st.selectbox(
                "Select a country to view the generated analyst note",
                options=display_df["country"].dropna().tolist()
                if "country" in display_df.columns
                else [],
            )

            if selected_country and "country" in display_df.columns:
                note_rows = display_df[display_df["country"] == selected_country]
                if not note_rows.empty:
                    st.info(str(note_rows.iloc[0]["analyst_note"]))
        else:
            st.info("Analyst notes were not found in the collection-priority file.")

        st.subheader("Source Register")

        if source_register_df is None or source_register_df.empty:
            st.info("Source register is not available.")
        else:
            st.dataframe(source_register_df, width="stretch", hide_index=True)

        st.subheader("Download Intelligence Outputs")

        col1, col2 = st.columns(2)

        with col1:
            add_download_button(
                THREAT_FINANCE_COLLECTION_PRIORITIES_FILE,
                "Download Collection Priorities",
                "text/csv",
            )

        with col2:
            add_download_button(
                THREAT_FINANCE_SOURCE_REGISTER_FILE,
                "Download Source Register",
                "text/csv",
            )


# ---------------------------------------------------
# ACLED Signal Layer
# ---------------------------------------------------

elif page == "ACLED Signal Layer":
    st.header("ACLED Recent Conflict and Unrest Signal Layer")

    st.markdown(
        """
        This section summarizes the ACLED recent conflict, unrest, and
        political-violence signal layer. ACLED is used as early-warning context
        for analyst review and collection prioritization. It is not evidence of
        terrorism-financing activity, criminality, sanctions exposure, or illicit
        finance.
        """
    )

    if acled_signal_df is None or acled_signal_df.empty:
        st.warning(
            "ACLED signal enrichment data is not available. Run `python main.py` first."
        )
    else:
        display_df = acled_signal_df.copy()

        countries_count = len(display_df)

        total_events = (
            int(pd.to_numeric(display_df["acled_event_count"], errors="coerce").fillna(0).sum())
            if "acled_event_count" in display_df.columns
            else 0
        )

        total_fatalities = (
            int(pd.to_numeric(display_df["acled_fatalities"], errors="coerce").fillna(0).sum())
            if "acled_fatalities" in display_df.columns
            else 0
        )

        high_or_above = 0
        if "acled_signal_level" in display_df.columns:
            high_or_above = int(
                display_df["acled_signal_level"].isin(["High", "Severe"]).sum()
            )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Country / Territory Records", f"{countries_count:,}")
        col2.metric("Recent ACLED Events", f"{total_events:,}")
        col3.metric("Recorded Fatalities", f"{total_fatalities:,}")
        col4.metric("High or Severe Signals", f"{high_or_above:,}")

        if "acled_conflict_signal_score" in display_df.columns:
            display_df["acled_conflict_signal_score"] = pd.to_numeric(
                display_df["acled_conflict_signal_score"],
                errors="coerce",
            )
            display_df = display_df.sort_values(
                "acled_conflict_signal_score",
                ascending=False,
            )

        st.subheader("Top ACLED Recent Signal Records")

        table_columns = [
            "country",
            "iso3",
            "acled_event_count",
            "acled_fatalities",
            "acled_political_violence_events",
            "acled_unrest_events",
            "acled_conflict_signal_score",
            "acled_signal_level",
            "acled_latest_event_date",
        ]

        available_columns = [
            column for column in table_columns if column in display_df.columns
        ]

        st.dataframe(
            display_df[available_columns].head(50).rename(
                columns={
                    "country": "Country / Territory",
                    "iso3": "ISO",
                    "acled_event_count": "Events",
                    "acled_fatalities": "Fatalities",
                    "acled_political_violence_events": "Political Violence Events",
                    "acled_unrest_events": "Unrest Events",
                    "acled_conflict_signal_score": "ACLED Signal Score",
                    "acled_signal_level": "Signal Level",
                    "acled_latest_event_date": "Latest Event Date",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        display_chart(
            ACLED_SIGNAL_TOP_15_CHART_FILE,
            "Top 15 ACLED Recent Conflict and Unrest Signals",
        )

        add_download_button(
            ACLED_SIGNAL_ENRICHMENT_FILE,
            "Download ACLED Signal Enrichment",
            "text/csv",
        )


# ---------------------------------------------------
# Organized Crime Layer
# ---------------------------------------------------

elif page == "Organized Crime Layer":
    st.header("Global Organized Crime Index Layer")

    st.markdown(
        """
        This section summarizes the Global Organized Crime Index enrichment layer.
        It is used as supplemental organized-crime convergence context for
        analyst review and collection prioritization. It is not evidence of
        terrorism-financing activity, criminality, sanctions exposure, illicit
        finance, or activity by any specific person, entity, account, wallet, or
        network.
        """
    )

    if organized_crime_df is None or organized_crime_df.empty:
        st.warning(
            "Organized-crime enrichment data is not available. Run `python main.py` first."
        )
    else:
        display_df = organized_crime_df.copy()

        record_count = len(display_df)

        matched_count = (
            int(
                pd.to_numeric(
                    display_df["organized_crime_source_present"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )
            if "organized_crime_source_present" in display_df.columns
            else int(display_df["organized_crime_score"].notna().sum())
            if "organized_crime_score" in display_df.columns
            else 0
        )

        average_score = (
            display_df["organized_crime_score"].mean()
            if "organized_crime_score" in display_df.columns
            else None
        )

        high_or_above = 0
        if "organized_crime_level" in display_df.columns:
            high_or_above = int(
                display_df["organized_crime_level"].isin(["High", "Very High"]).sum()
            )

        latest_year = "N/A"
        if (
            "oc_index_year" in display_df.columns
            and display_df["oc_index_year"].notna().any()
        ):
            latest_year = str(int(display_df["oc_index_year"].max()))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Country Records", f"{record_count:,}")
        col2.metric("Matched Records", f"{matched_count:,}")
        col3.metric("Avg. OC Score", format_number(average_score, 2))
        col4.metric("High / Very High", f"{high_or_above:,}", f"Index year {latest_year}")

        if "organized_crime_score" in display_df.columns:
            display_df["organized_crime_score"] = pd.to_numeric(
                display_df["organized_crime_score"],
                errors="coerce",
            )
            display_df = display_df.sort_values(
                "organized_crime_score",
                ascending=False,
            )

        st.subheader("Top Organized-Crime Vulnerability Records")

        table_columns = [
            "country",
            "country_code",
            "oc_index_year",
            "criminality_score",
            "criminal_markets_score",
            "criminal_actors_score",
            "resilience_score",
            "organized_crime_exposure_score",
            "organized_crime_resilience_gap_score",
            "organized_crime_score",
            "organized_crime_level",
        ]

        available_columns = [
            column for column in table_columns if column in display_df.columns
        ]

        st.dataframe(
            display_df[available_columns].head(50).rename(
                columns={
                    "country": "Country",
                    "country_code": "ISO3",
                    "oc_index_year": "Index Year",
                    "criminality_score": "Criminality",
                    "criminal_markets_score": "Markets",
                    "criminal_actors_score": "Actors",
                    "resilience_score": "Resilience",
                    "organized_crime_exposure_score": "Exposure",
                    "organized_crime_resilience_gap_score": "Resilience Gap",
                    "organized_crime_score": "OC Vulnerability Score",
                    "organized_crime_level": "OC Level",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        display_chart(
            TOP_15_ORGANIZED_CRIME_CHART_FILE,
            "Top 15 Organized Crime Vulnerability Scores",
        )

        add_download_button(
            ORGANIZED_CRIME_ENRICHMENT_FILE,
            "Download Organized Crime Enrichment",
            "text/csv",
        )


# ---------------------------------------------------
# GDELT 2.0 Batch News Signal Layer
# ---------------------------------------------------

elif page == "GDELT 2.0 Batch News Signal Layer":
    st.header("GDELT 2.0 Batch Public-News Signal Layer")

    st.markdown(
        """
        This section summarizes the GDELT 2.0 batch public-news signal layer.
        Recent Global Knowledge Graph batch files are downloaded or reused,
        filtered locally for threat-finance-related terms, matched to modeled
        countries, and converted into a supplemental media-reporting signal.

        The GDELT signal is used for analyst review and collection
        prioritization. It is not evidence of terrorism-financing activity,
        criminality, sanctions exposure, illicit finance, or activity by any
        specific person, entity, account, wallet, or network.

        Public-news signals can include media bias, duplication, translation
        artifacts, false positives, and uneven country coverage.
        """
    )

    if gdelt_news_df is None or gdelt_news_df.empty:
        st.warning(
            "GDELT 2.0 batch news signal enrichment data is not available. "
            "Run `python main.py` first."
        )
    else:
        display_df = gdelt_news_df.copy()

        record_count = len(display_df)

        matched_country_count = (
            int(
                (
                    pd.to_numeric(
                        display_df["gdelt_source_present"],
                        errors="coerce",
                    ).fillna(0)
                    == 1
                ).sum()
            )
            if "gdelt_source_present" in display_df.columns
            else int(
                (
                    pd.to_numeric(
                        display_df["gdelt_matching_record_count"],
                        errors="coerce",
                    ).fillna(0)
                    > 0
                ).sum()
            )
            if "gdelt_matching_record_count" in display_df.columns
            else 0
        )

        batch_file_count = (
            int(
                pd.to_numeric(
                    display_df["gdelt_batch_file_count"],
                    errors="coerce",
                ).max()
            )
            if "gdelt_batch_file_count" in display_df.columns
            and display_df["gdelt_batch_file_count"].notna().any()
            else 0
        )

        matched_records = (
            pd.to_numeric(
                display_df["gdelt_matching_record_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
            if "gdelt_matching_record_count" in display_df.columns
            else 0
        )

        matched_sources = (
            pd.to_numeric(
                display_df["gdelt_matching_source_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
            if "gdelt_matching_source_count" in display_df.columns
            else 0
        )

        average_signal = (
            display_df["gdelt_news_signal_score"].mean()
            if "gdelt_news_signal_score" in display_df.columns
            else None
        )

        high_or_above = 0
        if "gdelt_news_signal_level" in display_df.columns:
            high_or_above = int(
                display_df["gdelt_news_signal_level"].isin(["High", "Very High"]).sum()
            )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Country Records", f"{record_count:,}")
        col2.metric("Countries With Signal", f"{matched_country_count:,}")
        col3.metric("Matched GKG Records", f"{matched_records:,.0f}", f"{batch_file_count:,} files")
        col4.metric("Avg. GDELT Signal", format_number(average_signal, 2), f"High+ {high_or_above:,}")

        col5, col6 = st.columns(2)
        col5.metric("Matched Source References", f"{matched_sources:,.0f}")

        latest_file = "N/A"
        if (
            "gdelt_latest_file_datetime" in display_df.columns
            and display_df["gdelt_latest_file_datetime"].notna().any()
        ):
            latest_file = str(display_df["gdelt_latest_file_datetime"].dropna().max())

        col6.metric("Latest GDELT File", latest_file)

        if "gdelt_news_signal_score" in display_df.columns:
            display_df["gdelt_news_signal_score"] = pd.to_numeric(
                display_df["gdelt_news_signal_score"],
                errors="coerce",
            )
            display_df = display_df.sort_values(
                "gdelt_news_signal_score",
                ascending=False,
            )

        st.subheader("Top GDELT 2.0 Batch Public-News Signal Records")

        table_columns = [
            "country",
            "country_code",
            "gdelt_batch_file_count",
            "gdelt_matching_record_count",
            "gdelt_matching_source_count",
            "gdelt_average_tone",
            "gdelt_record_count_score",
            "gdelt_source_diversity_score",
            "gdelt_negative_tone_score",
            "gdelt_news_signal_score",
            "gdelt_news_signal_level",
            "gdelt_query_status",
            "gdelt_confidence",
            "gdelt_latest_file_datetime",
            "gdelt_days_since_update",
        ]

        available_columns = [
            column for column in table_columns if column in display_df.columns
        ]

        st.dataframe(
            display_df[available_columns].head(50).rename(
                columns={
                    "country": "Country",
                    "country_code": "ISO3",
                    "gdelt_batch_file_count": "Batch Files",
                    "gdelt_matching_record_count": "Matched Records",
                    "gdelt_matching_source_count": "Matched Sources",
                    "gdelt_average_tone": "Average Tone",
                    "gdelt_record_count_score": "Record Score",
                    "gdelt_source_diversity_score": "Source Score",
                    "gdelt_negative_tone_score": "Tone Score",
                    "gdelt_news_signal_score": "GDELT Signal Score",
                    "gdelt_news_signal_level": "Signal Level",
                    "gdelt_query_status": "Batch Status",
                    "gdelt_confidence": "Confidence",
                    "gdelt_latest_file_datetime": "Latest GDELT File",
                    "gdelt_days_since_update": "Days Since Update",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        display_chart(
            TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE,
            "Top 15 GDELT 2.0 Batch Public-News Signal Scores",
        )

        add_download_button(
            GDELT_NEWS_SIGNAL_ENRICHMENT_FILE,
            "Download GDELT 2.0 Batch News Signal Enrichment",
            "text/csv",
        )


# ---------------------------------------------------
# Current FATF Context
# ---------------------------------------------------

elif page == "Current FATF Context":
    st.header("Current FATF Context")

    st.markdown(
        """
        This section compares model outputs with the project's current FATF
        increased-monitoring supplement. It is a forward-looking comparison
        layer and does not replace the baseline model year.
        """
    )

    if current_fatf_df is None or current_fatf_df.empty:
        st.warning("Current FATF comparison data is not available.")
    else:
        current_count = (
            int(current_fatf_df["current_fatf_increased_monitoring"].sum())
            if "current_fatf_increased_monitoring" in current_fatf_df.columns
            else 0
        )

        changed_count = (
            int(current_fatf_df["fatf_status_changed"].sum())
            if "fatf_status_changed" in current_fatf_df.columns
            else 0
        )

        match_count = (
            int(current_fatf_df["model_signal_matches_current_fatf"].sum())
            if "model_signal_matches_current_fatf" in current_fatf_df.columns
            else 0
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Current FATF Monitored", f"{current_count:,}")
        col2.metric("Status Differences", f"{changed_count:,}")
        col3.metric("Model Signal Matches", f"{match_count:,}")

        display_df = current_fatf_df.copy()

        if "current_fatf_increased_monitoring" in display_df.columns:
            display_df = display_df[
                display_df["current_fatf_increased_monitoring"] == 1
            ]

        if "predicted_grey_list_probability" in display_df.columns:
            display_df["Predicted Probability"] = display_df[
                "predicted_grey_list_probability"
            ].apply(format_percent)

        st.dataframe(display_df, width="stretch", hide_index=True)

    display_chart(
        CURRENT_FATF_STATUS_COMPARISON_CHART_FILE,
        "Current FATF Status Comparison",
    )


# ---------------------------------------------------
# Conflict Supplement
# ---------------------------------------------------

elif page == "Conflict Supplement":
    st.header("Conflict Supplement")

    st.markdown(
        """
        Conflict exposure is supplemental context. It does not replace the
        baseline country-level vulnerability score and is not evidence of
        terrorism-financing activity.
        """
    )

    if conflict_df is None or conflict_df.empty:
        st.warning("Conflict supplement data is not available.")
    else:
        total_deaths = (
            int(conflict_df["conflict_deaths_total"].sum())
            if "conflict_deaths_total" in conflict_df.columns
            else 0
        )

        active_count = (
            int(conflict_df["organized_violence_active"].sum())
            if "organized_violence_active" in conflict_df.columns
            else 0
        )

        matched_count = (
            int(conflict_df["ucdp_match_found"].sum())
            if "ucdp_match_found" in conflict_df.columns
            else len(conflict_df)
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Matched Countries", f"{matched_count:,}")
        col2.metric("Countries with Active Violence", f"{active_count:,}")
        col3.metric("Recorded Deaths", f"{total_deaths:,}")

        sort_column = (
            "conflict_deaths_total"
            if "conflict_deaths_total" in conflict_df.columns
            else "tf_vulnerability_score"
        )

        display_dataframe(
            conflict_df.sort_values(sort_column, ascending=False),
            "Conflict Supplement Table",
            max_rows=50,
        )

    display_chart(
        TOP_15_CONFLICT_FATALITIES_CHART_FILE,
        "Top 15 Countries by Recorded Organized-Violence Deaths",
    )


# ---------------------------------------------------
# Regional Analysis
# ---------------------------------------------------

elif page == "Regional Analysis":
    st.header("Regional Analysis")

    display_dataframe(regional_df, "Regional Risk Summary")
    display_dataframe(additional_summary_df, "Additional Risk Factor Output Summary")

    col1, col2 = st.columns(2)

    with col1:
        display_chart(
            REGIONAL_AVERAGE_RISK_CHART_FILE,
            "Regional Average Terrorism-Financing Vulnerability Score",
        )

    with col2:
        display_chart(
            REGIONAL_FATF_COUNT_CHART_FILE,
            "Current FATF Increased-Monitoring Count by Region",
        )


# ---------------------------------------------------
# Charts
# ---------------------------------------------------

elif page == "Charts":
    st.header("Charts")

    chart_items = [
        (
            TOP_15_RISK_CHART_FILE,
            "Top 15 Countries by Terrorism-Financing Vulnerability Score",
        ),
        (
            RISK_SCORE_PROBABILITY_CHART_FILE,
            "Risk Score vs Predicted FATF Grey-List Probability",
        ),
        (
            GREY_LIST_PROBABILITY_TOP_20_CHART_FILE,
            "Top 20 Countries by Predicted FATF Grey-List Probability",
        ),
        (
            RISK_TIER_DISTRIBUTION_CHART_FILE,
            "Risk Tier Distribution",
        ),
        (
            SENSITIVITY_OVERLAP_CHART_FILE,
            "Top-20 Sensitivity Overlap by Scenario",
        ),
        (
            TOP_15_CONFLICT_FATALITIES_CHART_FILE,
            "Top 15 Countries by Recorded Organized-Violence Deaths",
        ),
        (
            REGIONAL_AVERAGE_RISK_CHART_FILE,
            "Regional Average Terrorism-Financing Vulnerability Score",
        ),
        (
            REGIONAL_FATF_COUNT_CHART_FILE,
            "Current FATF Increased-Monitoring Count by Region",
        ),
        (
            CURRENT_FATF_STATUS_COMPARISON_CHART_FILE,
            "Current FATF Status Comparison",
        ),
        (
            TOP_15_COLLECTION_PRIORITY_CHART_FILE,
            "Top 15 Threat Finance Collection Priorities",
        ),
        (
            INTELLIGENCE_GAP_DISTRIBUTION_CHART_FILE,
            "Threat Finance Intelligence Gap Distribution",
        ),
        (
            ACLED_SIGNAL_TOP_15_CHART_FILE,
            "Top 15 ACLED Recent Conflict and Unrest Signals",
        ),
        (
            TOP_15_ORGANIZED_CRIME_CHART_FILE,
            "Top 15 Organized Crime Vulnerability Scores",
        ),
        (
            TOP_15_GDELT_NEWS_SIGNAL_CHART_FILE,
            "Top 15 GDELT 2.0 Batch Public-News Signal Scores",
        ),
    ]

    for image_path, caption in chart_items:
        st.subheader(caption)
        display_chart(image_path, caption)


# ---------------------------------------------------
# Downloads
# ---------------------------------------------------

elif page == "Downloads":
    st.header("Downloads")

    st.markdown(
        """
        Download the generated report files and major output tables.
        Run `python main.py` first to refresh all outputs.
        """
    )

    st.subheader("Reports")

    col1, col2 = st.columns(2)

    with col1:
        add_download_button(
            WORD_REPORT_FILE,
            "Download Word Report",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    with col2:
        add_download_button(
            PDF_REPORT_FILE,
            "Download PDF Report",
            "application/pdf",
        )

    st.subheader("Core Tables")

    table_downloads = [
        (RISK_RANKINGS_FILE, "Download Risk Rankings"),
        (RISK_TIER_SUMMARY_FILE, "Download Risk Tier Summary"),
        (MODEL_PERFORMANCE_FILE, "Download Model Performance"),
        (FALSE_POSITIVES_FILE, "Download False Positives"),
        (FALSE_NEGATIVES_FILE, "Download False Negatives"),
        (SENSITIVITY_OVERLAP_FILE, "Download Sensitivity Overlap"),
        (CURRENT_FATF_STATUS_COMPARISON_FILE, "Download Current FATF Comparison"),
        (CONFLICT_DATA_SUPPLEMENT_FILE, "Download Conflict Supplement"),
        (TOP_RISK_DRIVERS_FILE, "Download Top Risk Drivers"),
        (REGIONAL_RISK_SUMMARY_FILE, "Download Regional Summary"),
        (
            THREAT_FINANCE_COLLECTION_PRIORITIES_FILE,
            "Download Threat Finance Collection Priorities",
        ),
        (
            THREAT_FINANCE_SOURCE_REGISTER_FILE,
            "Download Threat Finance Source Register",
        ),
        (
            ACLED_SIGNAL_ENRICHMENT_FILE,
            "Download ACLED Signal Enrichment",
        ),
        (
            ORGANIZED_CRIME_ENRICHMENT_FILE,
            "Download Organized Crime Enrichment",
        ),
        (
            GDELT_NEWS_SIGNAL_ENRICHMENT_FILE,
            "Download GDELT 2.0 Batch News Signal Enrichment",
        ),
        (
            ADDITIONAL_RISK_FACTOR_SUMMARY_FILE,
            "Download Additional Risk Factor Summary",
        ),
    ]

    for path, label in table_downloads:
        add_download_button(path, label, "text/csv")


# ---------------------------------------------------
# Methodology Notes
# ---------------------------------------------------

elif page == "Methodology Notes":
    st.header("Methodology Notes")

    st.markdown(
        f"""
        ### Study year

        The target study year is **{STUDY_YEAR}**. The model uses the latest
        available World Bank observations up to the study year when exact
        country-year data are unavailable.

        ### Core score

        The terrorism-financing vulnerability score is based on six public
        indicator groups:

        1. Corruption risk
        2. Rule-of-law risk
        3. Political-instability risk
        4. Low-income risk
        5. Inflation stress
        6. Unemployment stress

        ### Supplemental layers

        The following are supplemental interpretation layers:

        - UCDP annual conflict exposure
        - ACLED recent conflict and unrest signal enrichment
        - Global Organized Crime Index enrichment
        - GDELT 2.0 batch public-news signal enrichment
        - Regional risk summaries
        - Current FATF increased-monitoring comparison
        - Sanctions exposure templates
        - FATF mutual-evaluation templates
        - Official AML/CFT policy context
        - Threat finance intelligence gaps and collection priorities
        - Source staleness and analyst-review notes

        ### Intelligence gap layer

        The intelligence gap layer converts the baseline risk output into a
        collection-priority workflow. It helps identify where analysts should
        refresh sanctions, conflict, organized-crime, GDELT/public-news,
        enforcement, AML/CFT, crypto-risk, or terrorism-financing reporting
        sources.

        ### Limitations

        This dashboard is for defensive screening and research. It is not a
        determination of terrorism-financing activity. It does not identify
        individuals, entities, transactions, accounts, wallets, or networks.
        """
    )