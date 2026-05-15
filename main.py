"""
Main pipeline for the terrorism financing OSINT risk model.

Running this file executes the full workflow:
1. Collect World Bank data
2. Process country-level data
3. Create vulnerability risk scores
4. Model FATF grey-list status
5. Run enhanced analysis
6. Run current data supplement
7. Run conflict data supplement
8. Run additional risk factor analysis
9. Generate charts and correlation outputs
10. Generate Word and PDF reports

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
from src import additional_risk_factors
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
    run_step(7, "Conflict Data Supplement", conflict_data_supplement.main)
    run_step(8, "Additional Risk Factor Analysis", additional_risk_factors.main)
    run_step(9, "Visualization", visualization.main)
    run_step(10, "Report Generation", report_generator.main)

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