"""
Configuration file for the terrorism financing OSINT risk model.

This file stores project-wide settings, data paths, World Bank indicators,
risk model weights, FATF grey-list countries, current FATF monitoring context,
conflict-data supplement settings, additional risk factor settings,
and output file locations.
"""

from pathlib import Path


# ---------------------------------------------------
# Project information
# ---------------------------------------------------

PROJECT_TITLE = "A Quantitative OSINT Model for Country-Level Terrorism Financing Risk"


# ---------------------------------------------------
# Project paths
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

OUTPUTS_DIR = BASE_DIR / "outputs"
CHARTS_DIR = OUTPUTS_DIR / "charts"
TABLES_DIR = OUTPUTS_DIR / "tables"
REPORTS_DIR = OUTPUTS_DIR / "reports"


# ---------------------------------------------------
# Study year
# ---------------------------------------------------
# The project uses 2024 as the target study year because it is the most
# recent year that can be supported consistently by the core public
# country-level indicator framework.
#
# The data collection module uses the latest available observation up to
# STUDY_YEAR when exact 2024 data is unavailable for a country or indicator.
# Indicator-year columns are preserved in the outputs for transparency.

STUDY_YEAR = 2024


# ---------------------------------------------------
# World Bank indicators
# ---------------------------------------------------
# WGI indicators:
# CC.EST = Control of Corruption
# RL.EST = Rule of Law
# PV.EST = Political Stability and Absence of Violence/Terrorism
#
# Economic indicators:
# NY.GDP.PCAP.CD = GDP per capita, current US$
# FP.CPI.TOTL.ZG = Inflation, consumer prices, annual %
# SL.UEM.TOTL.ZS = Unemployment, total % of labor force

WORLD_BANK_INDICATORS = {
    "CC.EST": "control_of_corruption",
    "RL.EST": "rule_of_law",
    "PV.EST": "political_stability",
    "NY.GDP.PCAP.CD": "gdp_per_capita",
    "FP.CPI.TOTL.ZG": "inflation",
    "SL.UEM.TOTL.ZS": "unemployment",
}


# ---------------------------------------------------
# FATF grey-list countries
# ---------------------------------------------------
# These countries are used as the model validation target.
#
# FATF grey-list status changes over time. This list should represent the
# FATF increased-monitoring jurisdictions selected for the study's validation
# date and should be updated if the study scope changes.

FATF_GREY_LIST_COUNTRIES = [
    "Algeria",
    "Angola",
    "Bolivia",
    "Bulgaria",
    "Cameroon",
    "Cote d'Ivoire",
    "Democratic Republic of Congo",
    "Haiti",
    "Kenya",
    "Kuwait",
    "Lao PDR",
    "Lebanon",
    "Monaco",
    "Namibia",
    "Nepal",
    "Papua New Guinea",
    "South Sudan",
    "Syrian Arab Republic",
    "Venezuela, RB",
    "Vietnam",
    "British Virgin Islands",
    "Yemen, Rep.",
]


# ---------------------------------------------------
# Risk model feature names
# ---------------------------------------------------

RISK_FEATURES = [
    "corruption_risk",
    "rule_of_law_risk",
    "political_instability_risk",
    "low_income_risk",
    "inflation_risk",
    "unemployment_risk",
]


SCALED_RISK_FEATURES = [
    "corruption_risk_scaled",
    "rule_of_law_risk_scaled",
    "political_instability_risk_scaled",
    "low_income_risk_scaled",
    "inflation_risk_scaled",
    "unemployment_risk_scaled",
]


# ---------------------------------------------------
# Risk score weights
# ---------------------------------------------------
# These weights sum to 1.00.
#
# The model intentionally keeps the scoring framework transparent and simple.
# Alternative weighting assumptions are tested in the sensitivity analysis.

RISK_SCORE_WEIGHTS = {
    "corruption_risk_scaled": 0.25,
    "rule_of_law_risk_scaled": 0.20,
    "political_instability_risk_scaled": 0.25,
    "low_income_risk_scaled": 0.10,
    "inflation_risk_scaled": 0.10,
    "unemployment_risk_scaled": 0.10,
}


# ---------------------------------------------------
# Sensitivity analysis scenarios
# ---------------------------------------------------
# These alternate weighting scenarios test whether the top country rankings
# remain stable when model assumptions change.

SENSITIVITY_SCENARIOS = {
    "baseline": {
        "corruption_risk_scaled": 0.25,
        "rule_of_law_risk_scaled": 0.20,
        "political_instability_risk_scaled": 0.25,
        "low_income_risk_scaled": 0.10,
        "inflation_risk_scaled": 0.10,
        "unemployment_risk_scaled": 0.10,
    },
    "equal_weight": {
        "corruption_risk_scaled": 1 / 6,
        "rule_of_law_risk_scaled": 1 / 6,
        "political_instability_risk_scaled": 1 / 6,
        "low_income_risk_scaled": 1 / 6,
        "inflation_risk_scaled": 1 / 6,
        "unemployment_risk_scaled": 1 / 6,
    },
    "governance_heavy": {
        "corruption_risk_scaled": 0.30,
        "rule_of_law_risk_scaled": 0.30,
        "political_instability_risk_scaled": 0.20,
        "low_income_risk_scaled": 0.10,
        "inflation_risk_scaled": 0.05,
        "unemployment_risk_scaled": 0.05,
    },
    "political_instability_heavy": {
        "corruption_risk_scaled": 0.20,
        "rule_of_law_risk_scaled": 0.15,
        "political_instability_risk_scaled": 0.40,
        "low_income_risk_scaled": 0.10,
        "inflation_risk_scaled": 0.075,
        "unemployment_risk_scaled": 0.075,
    },
    "economic_stress_heavy": {
        "corruption_risk_scaled": 0.15,
        "rule_of_law_risk_scaled": 0.15,
        "political_instability_risk_scaled": 0.15,
        "low_income_risk_scaled": 0.20,
        "inflation_risk_scaled": 0.20,
        "unemployment_risk_scaled": 0.15,
    },
}


# ---------------------------------------------------
# Data files
# ---------------------------------------------------

RAW_WORLD_BANK_DATA_FILE = RAW_DATA_DIR / "world_bank_country_indicators.csv"
PROCESSED_COUNTRY_DATA_FILE = PROCESSED_DATA_DIR / "processed_country_risk_data.csv"


# ---------------------------------------------------
# Additional risk factor settings
# ---------------------------------------------------
# These settings support supplemental regional, sanctions, and FATF mutual
# evaluation layers. They do not replace the main country-level vulnerability
# score.

WORLD_BANK_COUNTRY_METADATA_URL = (
    "https://api.worldbank.org/v2/country?format=json&per_page=400"
)


# ---------------------------------------------------
# Additional risk factor raw input templates
# ---------------------------------------------------

SANCTIONS_EXPOSURE_TEMPLATE_FILE = RAW_DATA_DIR / "sanctions_exposure_input_template.csv"
FATF_MUTUAL_EVALUATION_TEMPLATE_FILE = (
    RAW_DATA_DIR / "fatf_mutual_evaluation_input_template.csv"
)


# ---------------------------------------------------
# Main table outputs
# ---------------------------------------------------

RISK_RANKINGS_FILE = TABLES_DIR / "terrorism_financing_country_risk_rankings.csv"
CORRELATION_MATRIX_FILE = TABLES_DIR / "terrorism_financing_risk_correlation_matrix.csv"


# ---------------------------------------------------
# Enhanced analysis table outputs
# ---------------------------------------------------

RISK_TIER_SUMMARY_FILE = TABLES_DIR / "risk_tier_summary.csv"
RISK_TIER_COUNTRY_FILE = TABLES_DIR / "risk_tier_country_rankings.csv"

MODEL_PERFORMANCE_FILE = TABLES_DIR / "model_performance_summary.csv"
CONFUSION_MATRIX_FILE = TABLES_DIR / "model_confusion_matrix.csv"
CLASSIFICATION_REPORT_FILE = TABLES_DIR / "classification_report.csv"

FALSE_POSITIVES_FILE = TABLES_DIR / "false_positive_countries.csv"
FALSE_NEGATIVES_FILE = TABLES_DIR / "false_negative_countries.csv"

SENSITIVITY_RANKINGS_FILE = TABLES_DIR / "sensitivity_rankings.csv"
SENSITIVITY_TOP_20_FILE = TABLES_DIR / "sensitivity_top_20_by_scenario.csv"
SENSITIVITY_OVERLAP_FILE = TABLES_DIR / "sensitivity_top_20_overlap.csv"


# ---------------------------------------------------
# Current data supplement settings
# ---------------------------------------------------
# The primary quantitative model uses STUDY_YEAR.
#
# These settings are used only for supplemental current-context analysis
# and FATF current-status comparison. The supplement does not replace the
# primary model-year score.

CURRENT_ECONOMIC_YEAR = 2024

CURRENT_ECONOMIC_INDICATORS = {
    "NY.GDP.PCAP.CD": "gdp_per_capita_current",
    "FP.CPI.TOTL.ZG": "inflation_current",
    "SL.UEM.TOTL.ZS": "unemployment_current",
}


# ---------------------------------------------------
# Current FATF increased-monitoring jurisdictions
# ---------------------------------------------------
# FATF increased-monitoring status changes over time.
#
# ISO3 codes are used here to avoid country-name matching issues.
# This current-status list is used only for supplemental comparison.

CURRENT_FATF_INCREASED_MONITORING_ISO3 = [
    "DZA",  # Algeria
    "AGO",  # Angola
    "BOL",  # Bolivia
    "BGR",  # Bulgaria
    "CMR",  # Cameroon
    "CIV",  # Cote d'Ivoire
    "COD",  # Democratic Republic of Congo
    "HTI",  # Haiti
    "KEN",  # Kenya
    "KWT",  # Kuwait
    "LAO",  # Lao PDR
    "LBN",  # Lebanon
    "MCO",  # Monaco
    "NAM",  # Namibia
    "NPL",  # Nepal
    "PNG",  # Papua New Guinea
    "SSD",  # South Sudan
    "SYR",  # Syrian Arab Republic
    "VEN",  # Venezuela
    "VNM",  # Vietnam
    "VGB",  # British Virgin Islands
    "YEM",  # Yemen
]


# ---------------------------------------------------
# Current data supplement outputs
# ---------------------------------------------------

CURRENT_ECONOMIC_DATA_FILE = TABLES_DIR / "current_economic_indicators.csv"
CURRENT_DATA_SUPPLEMENT_FILE = TABLES_DIR / "current_data_supplement.csv"
CURRENT_FATF_STATUS_COMPARISON_FILE = TABLES_DIR / "current_fatf_status_comparison.csv"


# ---------------------------------------------------
# Conflict data supplement settings
# ---------------------------------------------------
# UCDP Country-Year Dataset on Organized Violence within Country Borders v25.1.
# This dataset is used as a supplemental conflict-exposure layer. It does not
# replace the main terrorism-financing vulnerability score.

UCDP_ORGANIZED_VIOLENCE_URL = (
    "https://ucdp.uu.se/downloads/organizedviolencecy/"
    "organizedviolencecy-251-csv.zip"
)


# ---------------------------------------------------
# Conflict data supplement outputs
# ---------------------------------------------------

UCDP_CONFLICT_RAW_FILE = RAW_DATA_DIR / "ucdp_conflict_country_year_raw.csv"
CONFLICT_DATA_SUPPLEMENT_FILE = TABLES_DIR / "conflict_data_supplement.csv"
TOP_RISK_DRIVERS_FILE = TABLES_DIR / "top_risk_drivers.csv"


# ---------------------------------------------------
# Additional risk factor table outputs
# ---------------------------------------------------

COUNTRY_REGION_MAPPING_FILE = TABLES_DIR / "country_region_mapping.csv"
REGIONAL_RISK_SUMMARY_FILE = TABLES_DIR / "regional_risk_summary.csv"

SANCTIONS_EXPOSURE_SUPPLEMENT_FILE = (
    TABLES_DIR / "sanctions_exposure_supplement.csv"
)

FATF_MUTUAL_EVALUATION_SUPPLEMENT_FILE = (
    TABLES_DIR / "fatf_mutual_evaluation_supplement.csv"
)

ADDITIONAL_RISK_FACTOR_SUMMARY_FILE = (
    TABLES_DIR / "additional_risk_factor_summary.csv"
)


# ---------------------------------------------------
# Report outputs
# ---------------------------------------------------

LOGIT_SUMMARY_FILE = REPORTS_DIR / "terrorism_financing_logit_summary.txt"

WORD_REPORT_FILE = REPORTS_DIR / "terrorism_financing_osint_model_report.docx"
PDF_REPORT_FILE = REPORTS_DIR / "terrorism_financing_osint_model_report.pdf"


# ---------------------------------------------------
# Chart outputs
# ---------------------------------------------------

TOP_15_RISK_CHART_FILE = CHARTS_DIR / "top_15_tf_risk_scores.png"

RISK_SCORE_PROBABILITY_CHART_FILE = (
    CHARTS_DIR / "risk_score_vs_grey_list_probability.png"
)

GREY_LIST_PROBABILITY_TOP_20_CHART_FILE = (
    CHARTS_DIR / "grey_list_probability_top_20.png"
)

RISK_TIER_DISTRIBUTION_CHART_FILE = CHARTS_DIR / "risk_tier_distribution.png"

SENSITIVITY_OVERLAP_CHART_FILE = CHARTS_DIR / "sensitivity_top_20_overlap.png"

TOP_15_CONFLICT_FATALITIES_CHART_FILE = (
    CHARTS_DIR / "top_15_conflict_fatalities.png"
)

REGIONAL_AVERAGE_RISK_CHART_FILE = CHARTS_DIR / "regional_average_risk_score.png"

REGIONAL_FATF_COUNT_CHART_FILE = CHARTS_DIR / "regional_fatf_count.png"

CURRENT_FATF_STATUS_COMPARISON_CHART_FILE = (
    CHARTS_DIR / "current_fatf_status_comparison.png"
)


# ---------------------------------------------------
# Config validation helper
# ---------------------------------------------------

def validate_config() -> None:
    """
    Validate key configuration settings.

    This helper catches common project configuration issues before the full
    pipeline runs. It is intentionally lightweight and does not create files
    or call external APIs.
    """

    if not isinstance(STUDY_YEAR, int):
        raise TypeError("STUDY_YEAR must be an integer.")

    if STUDY_YEAR < 2000:
        raise ValueError("STUDY_YEAR appears invalid.")

    if not WORLD_BANK_INDICATORS:
        raise ValueError("WORLD_BANK_INDICATORS cannot be empty.")

    if not FATF_GREY_LIST_COUNTRIES:
        raise ValueError("FATF_GREY_LIST_COUNTRIES cannot be empty.")

    if not RISK_FEATURES:
        raise ValueError("RISK_FEATURES cannot be empty.")

    if not SCALED_RISK_FEATURES:
        raise ValueError("SCALED_RISK_FEATURES cannot be empty.")

    expected_scaled_features = [
        f"{feature}_scaled" for feature in RISK_FEATURES
    ]

    missing_scaled_features = [
        feature
        for feature in expected_scaled_features
        if feature not in SCALED_RISK_FEATURES
    ]

    if missing_scaled_features:
        raise ValueError(
            "SCALED_RISK_FEATURES is missing expected scaled features: "
            f"{missing_scaled_features}"
        )

    missing_weight_features = [
        feature
        for feature in SCALED_RISK_FEATURES
        if feature not in RISK_SCORE_WEIGHTS
    ]

    if missing_weight_features:
        raise ValueError(
            "RISK_SCORE_WEIGHTS is missing scaled features: "
            f"{missing_weight_features}"
        )

    extra_weight_features = [
        feature
        for feature in RISK_SCORE_WEIGHTS
        if feature not in SCALED_RISK_FEATURES
    ]

    if extra_weight_features:
        raise ValueError(
            "RISK_SCORE_WEIGHTS contains features not listed in "
            f"SCALED_RISK_FEATURES: {extra_weight_features}"
        )

    weight_total = sum(RISK_SCORE_WEIGHTS.values())

    if round(weight_total, 6) != 1.0:
        raise ValueError(
            "RISK_SCORE_WEIGHTS must sum to 1.00. "
            f"Current total: {weight_total}"
        )

    if not SENSITIVITY_SCENARIOS:
        raise ValueError("SENSITIVITY_SCENARIOS cannot be empty.")

    for scenario_name, weights in SENSITIVITY_SCENARIOS.items():
        missing_features = [
            feature
            for feature in SCALED_RISK_FEATURES
            if feature not in weights
        ]

        if missing_features:
            raise ValueError(
                f"Sensitivity scenario '{scenario_name}' is missing features: "
                f"{missing_features}"
            )

        extra_features = [
            feature
            for feature in weights
            if feature not in SCALED_RISK_FEATURES
        ]

        if extra_features:
            raise ValueError(
                f"Sensitivity scenario '{scenario_name}' contains extra features: "
                f"{extra_features}"
            )

        scenario_total = sum(weights.values())

        if round(scenario_total, 6) != 1.0:
            raise ValueError(
                f"Sensitivity scenario '{scenario_name}' must sum to 1.00. "
                f"Current total: {scenario_total}"
            )

    required_directories = [
        DATA_DIR,
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        OUTPUTS_DIR,
        CHARTS_DIR,
        TABLES_DIR,
        REPORTS_DIR,
    ]

    for directory in required_directories:
        if not isinstance(directory, Path):
            raise TypeError(f"Directory setting is not a pathlib.Path: {directory}")

    required_files = [
        RAW_WORLD_BANK_DATA_FILE,
        PROCESSED_COUNTRY_DATA_FILE,
        RISK_RANKINGS_FILE,
        CORRELATION_MATRIX_FILE,
        WORD_REPORT_FILE,
        PDF_REPORT_FILE,
    ]

    for file_path in required_files:
        if not isinstance(file_path, Path):
            raise TypeError(f"File setting is not a pathlib.Path: {file_path}")

    print("Config validation passed.")


if __name__ == "__main__":
    validate_config()