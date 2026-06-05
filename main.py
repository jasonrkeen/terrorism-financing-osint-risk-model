"""
Main pipeline for the terrorism financing OSINT risk model.

Running this file executes the full workflow:

1. Collect World Bank data
2. Process country-level data
3. Create vulnerability risk scores
4. Model FATF grey-list status
5. Run enhanced analysis
6. Run current data supplement
7. Run UCDP conflict data supplement
8. Run ACLED data collection
9. Run ACLED signal enrichment
10. Run Global Organized Crime Index enrichment
11. Run GDELT 2.0 batch public-news signal enrichment
12. Run additional risk factor analysis
13. Run threat finance intelligence gap analysis
14. Generate charts and correlation outputs
15. Generate Word and PDF reports

Each step depends on the outputs created by the previous step.
"""

from __future__ import annotations

from src import data_collection
from src import data_processing
from src import risk_scoring
from src import modeling
from src import enhanced_analysis
from src import current_data_supplement
from src import conflict_data_supplement
from src import acled_data_collection
from src import acled_enrichment
from src import organized_crime_enrichment
from src import gdelt_batch_enrichment
from src import additional_risk_factors
from src import threat_finance_intelligence
from src import visualization
from src import report_generator


def run_step(step_number: int, step_name: str, step_function) -> None:
    """
    Run one pipeline step with consistent console formatting.
    """
    print("\n" + "-" * 70)
    print(f"STEP {step_number}: {step_name}")
    print("-" * 70)
    step_function()


def main() -> None:
    """
    Run the full project pipeline.
    """
    print("=" * 70)
    print("A Quantitative OSINT Model for Country-Level Terrorism Financing Risk")
    print("=" * 70)

    run_step(1, "Data Collection", data_collection.main)
    run_step(2, "Data Processing", data_processing.main)
    run_step(3, "Risk Scoring", risk_scoring.main)
    run_step(4, "Modeling", modeling.main)
    run_step(5, "Enhanced Analysis", enhanced_analysis.main)
    run_step(6, "Current Data Supplement", current_data_supplement.main)
    run_step(7, "UCDP Conflict Data Supplement", conflict_data_supplement.main)
    run_step(8, "ACLED Data Collection", acled_data_collection.main)
    run_step(9, "ACLED Signal Enrichment", acled_enrichment.main)

    run_step(
        10,
        "Global Organized Crime Index Enrichment",
        organized_crime_enrichment.main,
    )

    run_step(
        11,
        "GDELT 2.0 Batch Public-News Signal Enrichment",
        gdelt_batch_enrichment.main,
    )

    run_step(12, "Additional Risk Factor Analysis", additional_risk_factors.main)

    run_step(
        13,
        "Threat Finance Intelligence Gap Analysis",
        threat_finance_intelligence.main,
    )

    run_step(14, "Visualization", visualization.main)
    run_step(15, "Report Generation", report_generator.main)

    print("\n" + "=" * 70)
    print("Full project pipeline complete.")
    print("=" * 70)

    print("\nFinal outputs should be available in:")
    print("data/raw/")
    print("data/processed/")
    print("outputs/tables/")
    print("outputs/charts/")
    print("outputs/reports/")


if __name__ == "__main__":
    main()
