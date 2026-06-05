"""
Source register for the terrorism financing OSINT risk model.

This module documents the public-source datasets and source categories used or
planned in the project. The register supports transparency, reproducibility,
and analyst review.

The listed sources support risk screening, intelligence-gap analysis, and
public-source collection prioritization. They do not independently determine
terrorism financing, criminality, sanctions exposure, or illicit activity.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_SOURCE_REGISTER_PATH = Path("outputs/tables/source_register.csv")


def build_source_register() -> pd.DataFrame:
    """
    Build the project source register.
    """

    sources = [
        {
            "source_name": "World Bank Worldwide Governance Indicators",
            "source_type": "Governance indicators",
            "coverage": "Country-level",
            "use_in_model": (
                "Core baseline indicators for control of corruption, rule of law, "
                "and political stability."
            ),
            "confidence_level": "High",
            "status": "Active",
            "limitations": "Annual data may lag current political or governance conditions.",
        },
        {
            "source_name": "World Bank Economic Indicators",
            "source_type": "Economic indicators",
            "coverage": "Country-level",
            "use_in_model": (
                "Core baseline indicators for GDP per capita, inflation, and "
                "unemployment."
            ),
            "confidence_level": "High",
            "status": "Active",
            "limitations": (
                "Country coverage and reporting years vary. The model uses the "
                "latest available value up to the configured study year."
            ),
        },
        {
            "source_name": "FATF High-Risk and Other Monitored Jurisdictions",
            "source_type": "AML/CFT monitoring",
            "coverage": "Country-level",
            "use_in_model": (
                "Validation target, current AML/CFT monitoring context, and "
                "public-source AML/CFT strategic deficiency signal."
            ),
            "confidence_level": "High",
            "status": "Active",
            "limitations": (
                "FATF list status does not represent all terrorism-financing risk "
                "and should not be treated as a country-level determination of "
                "terrorism financing."
            ),
        },
        {
            "source_name": "UCDP Country-Year Organized Violence Dataset",
            "source_type": "Conflict and organized-violence data",
            "coverage": "Country-year",
            "use_in_model": (
                "Structured annual conflict-exposure supplement using organized "
                "violence deaths, active violence indicators, and conflict intensity."
            ),
            "confidence_level": "Moderate to High",
            "status": "Active",
            "limitations": (
                "Annual data may lag current conditions. Country naming and coding "
                "can require matching aliases."
            ),
        },
        {
            "source_name": "ACLED Conflict and Political Violence Event Data",
            "source_type": "Recent conflict, unrest, and political-violence event data",
            "coverage": "Event-level and country-level",
            "use_in_model": (
                "Recent conflict and unrest signal enrichment for live-signal scoring "
                "and collection-priority analysis."
            ),
            "confidence_level": "Moderate to High",
            "status": "Active",
            "limitations": (
                "Coverage, coding, reporting density, and licensing constraints may "
                "vary by country. ACLED signals are used as early-warning context, "
                "not evidence of terrorism-financing activity."
            ),
        },
        {
            "source_name": "OFAC Sanctions Lists",
            "source_type": "Sanctions",
            "coverage": "Entity, individual, vessel, aircraft, and country-related sanctions",
            "use_in_model": (
                "Planned or manual sanctions exposure and terrorism-related designation "
                "context."
            ),
            "confidence_level": "High",
            "status": "Planned / Manual Supplement",
            "limitations": (
                "Sanctions data identifies designated parties and programs; it does "
                "not capture broader unlisted risk or prove country-level illicit activity."
            ),
        },
        {
            "source_name": "OpenSanctions",
            "source_type": "Aggregated sanctions and watchlist data",
            "coverage": "Global",
            "use_in_model": (
                "Planned sanctions enrichment and entity-list context for future "
                "country or entity-level supplements."
            ),
            "confidence_level": "Moderate to High",
            "status": "Planned",
            "limitations": "Dependent on upstream source coverage, matching quality, and update timing.",
        },
        {
            "source_name": "Global Organized Crime Index",
            "source_type": "Organized crime exposure and resilience context",
            "coverage": "Country-level",
            "use_in_model": (
                "Active supplemental organized-crime convergence layer using "
                "criminality, criminal-market, criminal-actor, resilience, exposure, "
                "and resilience-gap indicators. Used for live-signal context, source "
                "coverage, intelligence-gap scoring, and collection-priority analysis."
            ),
            "confidence_level": "Moderate to High",
            "status": "Active",
            "limitations": (
                "Index-based methodology may not capture fast-moving changes, "
                "subnational variation, or case-level organized-crime activity. "
                "The score is contextual and is not evidence of terrorism financing, "
                "criminality, sanctions exposure, or illicit activity."
            ),
        },
        {
            "source_name": "GDELT 2.0 Global Knowledge Graph Batch Files",
            "source_type": "Open-source public-news signal",
            "coverage": "Global public reporting from GDELT 2.0 GKG batch files",
            "use_in_model": (
                "Active supplemental public-news signal layer. Recent GDELT 2.0 "
                "Global Knowledge Graph batch files are downloaded, filtered locally "
                "for threat-finance-related terms, matched to modeled countries, and "
                "converted into a public-news signal score for live-signal context, "
                "source coverage, intelligence-gap scoring, and collection-priority "
                "analysis."
            ),
            "confidence_level": "Moderate",
            "status": "Active",
            "limitations": (
                "Public reporting may include media bias, duplication, translation "
                "artifacts, false positives, and uneven country coverage. GDELT "
                "signals are media-reporting context only and are not evidence of "
                "terrorism financing, criminality, sanctions exposure, or illicit "
                "activity."
            ),
        },
        {
            "source_name": "Treasury / DOJ / FinCEN Enforcement Releases",
            "source_type": "Public enforcement reporting",
            "coverage": "Case-level public releases",
            "use_in_model": (
                "Planned terrorism-financing enforcement, typology, and case-context "
                "signal."
            ),
            "confidence_level": "High",
            "status": "Planned",
            "limitations": (
                "Public releases are event-driven and do not represent all activity. "
                "They should be used as case-context indicators, not comprehensive "
                "country-level measures."
            ),
        },
        {
            "source_name": "FATF Mutual Evaluation Reports",
            "source_type": "AML/CFT effectiveness and technical compliance",
            "coverage": "Country-level report assessments",
            "use_in_model": (
                "Manual supplement for technical compliance, effectiveness, and "
                "AML/CFT control maturity."
            ),
            "confidence_level": "High",
            "status": "Manual Supplement",
            "limitations": (
                "Report dates vary by country, and mutual evaluations may not reflect "
                "the most current legal or enforcement environment."
            ),
        },
    ]

    columns = [
        "source_name",
        "source_type",
        "coverage",
        "use_in_model",
        "confidence_level",
        "status",
        "limitations",
    ]

    return pd.DataFrame(sources)[columns]


def save_source_register(
    output_path: str | Path = DEFAULT_SOURCE_REGISTER_PATH,
) -> pd.DataFrame:
    """
    Save the project source register to CSV.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = build_source_register()
    df.to_csv(output_path, index=False)

    return df


if __name__ == "__main__":
    save_source_register()