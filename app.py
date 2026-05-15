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

        Conflict, sanctions, regional summaries, current FATF status, and policy
        context are supplemental layers. They improve interpretation but do not
        replace the baseline vulnerability score.
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

        - Conflict exposure
        - Regional risk summaries
        - Current FATF increased-monitoring comparison
        - Sanctions exposure templates
        - FATF mutual-evaluation templates
        - Official AML/CFT policy context

        ### Limitations

        This dashboard is for defensive screening and research. It is not a
        determination of terrorism-financing activity. It does not identify
        individuals, entities, transactions, accounts, wallets, or networks.
        """
    )