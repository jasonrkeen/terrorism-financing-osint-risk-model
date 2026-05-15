# A Quantitative OSINT Model for Country-Level Terrorism Financing Risk

## Project Overview

This project builds a defensive open-source intelligence (OSINT) model for assessing **country-level terrorism financing vulnerability**. The model uses public governance and economic indicators to create a transparent country-level risk score, compares that score against FATF grey-list status, and adds supplemental context from conflict data, current FATF monitoring status, regional summaries, sanctions templates, FATF mutual-evaluation templates, official AML/CFT policy sources, virtual-assets context, and an interactive Streamlit dashboard.

The project is intended for academic research, defensive intelligence analysis, financial-crime risk screening, AML/CFT model documentation, country-risk prioritization, and portfolio/project demonstration.

It is **not** designed to identify individual actors, entities, transactions, terrorist networks, wallets, accounts, or operational financing methods.

---

## Research Question

Can publicly available governance and economic indicators be used to estimate country-level terrorism financing vulnerability and partially explain FATF grey-list status?

---

## Important Safety and Scope Notes

This project is a **defensive screening and prioritization framework**.

The model:

- Uses country-level public data only
- Does not analyze individual people, organizations, wallets, accounts, or transactions
- Does not provide operational terrorism-financing methods
- Does not determine whether terrorist financing is occurring
- Does not replace suspicious activity reporting, law enforcement investigations, or institutional AML/CFT risk assessments
- Does not substitute for FATF mutual evaluation reports, national risk assessments, or regulated-sector compliance obligations
- Does not provide legal, compliance, investigative, or law-enforcement conclusions

The risk score should be interpreted as a **structural vulnerability indicator**, not evidence of terrorism financing activity.

---

## Target Study Year

The project uses:

```python
STUDY_YEAR = 2024
```

The model uses 2024 as the target study year because it is the most recent year that can be supported consistently by the core public country-level indicator framework.

When exact 2024 data is unavailable for a country or indicator, the pipeline uses the latest available observation up to 2024 and preserves the indicator year in the output tables.

The model does **not** use 2025 or 2026 as the primary model year because the core World Bank governance and economic indicator panel is not consistently available as a complete comparable country-year dataset for those years.

More recent 2025 and 2026 official sources may be used as **context**, but not as replacement model-year observations.

---

## FATF Grey-List Background

The Financial Action Task Force (FATF) is the global standard-setting body for anti-money laundering, countering the financing of terrorism, and countering proliferation financing.

The term **grey list** commonly refers to FATF's list of jurisdictions under increased monitoring. These jurisdictions are working with FATF to address strategic deficiencies in their AML/CFT/CPF regimes. Grey-list status does **not** mean that terrorist financing is occurring in a jurisdiction, and it should not be interpreted as evidence of terrorist-financing activity.

In this project, FATF grey-list status is used as a **comparison and validation target**. The baseline vulnerability score is calculated from governance and economic indicators. FATF status is not used as a direct scoring input in the baseline score.

This distinction matters because:

- A country may have elevated structural vulnerability but not be grey-listed.
- A country may be grey-listed because of legal, supervisory, enforcement, beneficial ownership, financial-intelligence, or institutional deficiencies that broad public indicators do not fully capture.
- FATF status is a policy and regulatory monitoring outcome, not a direct measurement of terrorism-financing activity.

---

## Model Inputs and Analytical Role

The model separates inputs into three categories:

1. **Core quantitative inputs** used directly in the baseline score:
   - Governance indicators
   - Political stability
   - GDP per capita
   - Inflation
   - Unemployment

2. **Validation/comparison target**:
   - FATF grey-list status

3. **Supplemental interpretation layers**:
   - UCDP conflict exposure
   - Risk tiers
   - Top risk drivers
   - Current FATF monitoring comparison
   - Regional summaries
   - Sanctions exposure templates
   - FATF mutual-evaluation templates
   - Official AML/CFT policy context
   - Virtual-assets and Travel Rule context

This separation keeps the baseline score transparent and reproducible. Supplemental layers improve interpretation but do not change the baseline score unless explicitly added in a future model version.

---

## Data Sources

The core model uses:

| Source | Indicator | Variable | Purpose |
|---|---|---|---|
| World Bank WGI | Control of Corruption | `control_of_corruption` | Governance integrity and corruption vulnerability |
| World Bank WGI | Rule of Law | `rule_of_law` | Legal and institutional enforcement strength |
| World Bank WGI | Political Stability | `political_stability` | Political instability and violence risk |
| World Bank WDI | GDP per Capita | `gdp_per_capita` | Economic development and income vulnerability |
| World Bank WDI | Inflation | `inflation` | Macroeconomic stress |
| World Bank WDI | Unemployment | `unemployment` | Labor-market stress |
| FATF | Grey-list status | `fatf_grey_list` | Validation/comparison target |
| UCDP | Organized violence country-year data | `conflict_deaths_total` | Supplemental conflict exposure |
| World Bank Metadata | Region and income metadata | `world_bank_region` | Regional grouping and summary analysis |
| Manual Templates | Sanctions and FATF mutual-evaluation inputs | Supplemental templates | Future structured AML/CFT enhancement layers |

---

## Core Risk Features

The model converts governance and economic indicators into risk-oriented variables.

| Original Indicator | Risk Feature | Interpretation |
|---|---|---|
| Control of Corruption | `corruption_risk` | Lower control of corruption means higher risk |
| Rule of Law | `rule_of_law_risk` | Lower rule of law means higher risk |
| Political Stability | `political_instability_risk` | Lower political stability means higher risk |
| GDP per Capita | `low_income_risk` | Lower income means higher risk |
| Inflation | `inflation_risk` | Higher inflation means higher risk |
| Unemployment | `unemployment_risk` | Higher unemployment means higher risk |

The risk features are normalized to a 0-to-1 scale before scoring.

---

## Risk Score Weights

The baseline risk score uses the following weights:

| Feature | Weight |
|---|---:|
| Corruption risk | 25% |
| Rule of law risk | 20% |
| Political instability risk | 25% |
| Low income risk | 10% |
| Inflation risk | 10% |
| Unemployment risk | 10% |

The final vulnerability score is scaled from 0 to 100.

---

## Process Summary

The pipeline follows this workflow:

1. Collect World Bank governance and economic data from public API endpoints.
2. Select the latest available observation up to the target study year for each indicator.
3. Preserve indicator-year fields for transparency.
4. Remove regional aggregates and retain modeled country-level observations.
5. Convert raw indicators into risk-oriented variables.
6. Normalize all risk features to a 0-to-1 scale.
7. Apply transparent baseline weights.
8. Rank countries by the final 0-to-100 terrorism-financing vulnerability score.
9. Fit a logistic classification model to compare risk indicators against FATF grey-list status.
10. Add supplemental interpretation layers such as risk tiers, sensitivity analysis, conflict exposure, regional summaries, and current FATF comparison.
11. Generate charts, tables, a Word report, a PDF report, and an optional Streamlit dashboard.

---

## Sensitivity Analysis Scenarios

The project includes alternate weighting scenarios to test whether top country rankings remain stable when model assumptions change.

Current scenarios:

- Baseline
- Equal weight
- Governance heavy
- Political instability heavy
- Economic stress heavy

Outputs include:

- Full sensitivity rankings
- Top 20 countries by scenario
- Top-20 overlap with the baseline scenario

---

## Project Structure

```text
terrorism_financing_osint_model/
│
├── data/
│   ├── raw/
│   ├── processed/
│
├── outputs/
│   ├── charts/
│   ├── tables/
│   ├── reports/
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_collection.py
│   ├── data_processing.py
│   ├── risk_scoring.py
│   ├── modeling.py
│   ├── enhanced_analysis.py
│   ├── current_data_supplement.py
│   ├── conflict_data_supplement.py
│   ├── additional_risk_factors.py
│   ├── visualization.py
│   ├── report_generator.py
│
├── notebooks/
│   ├── exploratory_analysis.ipynb
│
├── app.py
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install required packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Requirements

```text
pandas
numpy
requests
matplotlib
statsmodels
scikit-learn
python-docx
docx2pdf
streamlit
```

Notes:

- `docx2pdf` works best on Windows when Microsoft Word is installed.
- If PDF conversion fails, the Word report should still be created.
- Streamlit is required for the optional dashboard in `app.py`.

---

## Main Pipeline

The full project pipeline runs the following steps:

1. Data Collection
2. Data Processing
3. Risk Scoring
4. Modeling
5. Enhanced Analysis
6. Current Data Supplement
7. Conflict Data Supplement
8. Additional Risk Factor Analysis
9. Visualization
10. Report Generation

Run the full pipeline with:

```powershell
.\.venv\Scripts\python.exe main.py
```

You can also run:

```powershell
python main.py
```

if your active interpreter is already the project virtual environment.

---

## Running Individual Modules

From the project root, run any module individually:

```powershell
.\.venv\Scripts\python.exe -m src.data_collection
.\.venv\Scripts\python.exe -m src.data_processing
.\.venv\Scripts\python.exe -m src.risk_scoring
.\.venv\Scripts\python.exe -m src.modeling
.\.venv\Scripts\python.exe -m src.enhanced_analysis
.\.venv\Scripts\python.exe -m src.current_data_supplement
.\.venv\Scripts\python.exe -m src.conflict_data_supplement
.\.venv\Scripts\python.exe -m src.additional_risk_factors
.\.venv\Scripts\python.exe -m src.visualization
.\.venv\Scripts\python.exe -m src.report_generator
```

---

## Streamlit Dashboard

The project includes an optional Streamlit dashboard in `app.py`.

Run the full pipeline first so the dashboard has generated tables, charts, and reports to read:

```powershell
.\.venv\Scripts\python.exe main.py
```

Then launch the dashboard:

```powershell
streamlit run app.py
```

The dashboard includes:

- Overview metrics
- Country rankings
- Model results
- Enhanced analysis
- Current FATF context
- Conflict supplement
- Regional analysis
- Chart gallery
- Report and table downloads
- Methodology notes

If VS Code shows `Import "streamlit" could not be resolved`, install Streamlit into the active virtual environment and select the correct interpreter:

```powershell
.\.venv\Scripts\Activate.ps1
pip install streamlit
```

Then in VS Code:

```text
Ctrl + Shift + P
Python: Select Interpreter
Choose .venv\Scripts\python.exe
```

---

## Key Outputs

### Raw and Processed Data

| Output | Description |
|---|---|
| `data/raw/world_bank_country_indicators.csv` | Raw World Bank indicator dataset |
| `data/raw/ucdp_conflict_country_year_raw.csv` | Raw UCDP organized-violence country-year dataset |
| `data/processed/processed_country_risk_data.csv` | Cleaned country-level model dataset |

### Tables

| Output | Description |
|---|---|
| `outputs/tables/terrorism_financing_country_risk_rankings.csv` | Final ranked country risk scores |
| `outputs/tables/terrorism_financing_risk_correlation_matrix.csv` | Correlation matrix |
| `outputs/tables/risk_tier_summary.csv` | Risk tier summary |
| `outputs/tables/risk_tier_country_rankings.csv` | Country-level risk tier output |
| `outputs/tables/model_performance_summary.csv` | Classification model performance |
| `outputs/tables/model_confusion_matrix.csv` | Confusion matrix |
| `outputs/tables/classification_report.csv` | Full classification report |
| `outputs/tables/false_positive_countries.csv` | Countries above model threshold but not FATF grey-listed |
| `outputs/tables/false_negative_countries.csv` | FATF grey-listed countries below model threshold |
| `outputs/tables/sensitivity_rankings.csv` | Full sensitivity rankings |
| `outputs/tables/sensitivity_top_20_by_scenario.csv` | Top 20 by sensitivity scenario |
| `outputs/tables/sensitivity_top_20_overlap.csv` | Top-20 overlap by scenario |
| `outputs/tables/current_economic_indicators.csv` | Current economic indicator supplement |
| `outputs/tables/current_data_supplement.csv` | Current data supplement |
| `outputs/tables/current_fatf_status_comparison.csv` | Current FATF comparison |
| `outputs/tables/conflict_data_supplement.csv` | UCDP conflict exposure supplement |
| `outputs/tables/top_risk_drivers.csv` | Largest weighted score contributors |
| `outputs/tables/country_region_mapping.csv` | Country-to-region mapping |
| `outputs/tables/regional_risk_summary.csv` | Regional risk summary |
| `outputs/tables/sanctions_exposure_supplement.csv` | Sanctions exposure supplement |
| `outputs/tables/fatf_mutual_evaluation_supplement.csv` | FATF mutual-evaluation supplement |
| `outputs/tables/additional_risk_factor_summary.csv` | Additional factor output summary |

### Charts

| Output | Description |
|---|---|
| `outputs/charts/top_15_tf_risk_scores.png` | Top 15 risk scores |
| `outputs/charts/risk_score_vs_grey_list_probability.png` | Risk score vs predicted FATF probability |
| `outputs/charts/grey_list_probability_top_20.png` | Top 20 predicted probabilities |
| `outputs/charts/risk_tier_distribution.png` | Risk tier distribution |
| `outputs/charts/sensitivity_top_20_overlap.png` | Sensitivity overlap |
| `outputs/charts/top_15_conflict_fatalities.png` | Top conflict fatalities |
| `outputs/charts/regional_average_risk_score.png` | Regional average risk score |
| `outputs/charts/regional_fatf_count.png` | Current FATF increased-monitoring count by region |
| `outputs/charts/current_fatf_status_comparison.png` | Current FATF status comparison |

### Reports

| Output | Description |
|---|---|
| `outputs/reports/terrorism_financing_osint_model_report.docx` | Word report |
| `outputs/reports/terrorism_financing_osint_model_report.pdf` | PDF report |
| `outputs/reports/terrorism_financing_logit_summary.txt` | Logistic regression summary |

---

## Report Sections

The generated report includes:

- Executive Summary
- Project Overview
- Research Question
- Data Sources
- Model Inputs and Analytical Role
- Methodology
- Process Summary
- Risk Feature Construction
- Risk Score Weights
- Indicator Year Coverage
- Top Country Risk Rankings
- How to Read the Rankings
- FATF Grey-List Background
- Modeling Results
- Practical Use Case for AML/CFT Screening
- Enhanced Analysis
- False Positive and False Negative Review
- Sensitivity Analysis
- Top Risk Drivers
- Conflict Event Data Supplement
- Additional Risk Factor Analysis
- Current Data Supplement and Forward-Looking Risk Context
- Official Terrorism Designation Context by Region
- South Africa Case Study: FATF Grey-List Remediation and FIU Context
- U.S. Treasury 2024 National Terrorist Financing Risk Assessment Context
- U.S. Treasury 2024 Illicit Finance Strategy Context
- Virtual Assets Context: Privacy Coins and Illicit-Finance Risk
- UAE AML/CFT/CPF National Strategy 2024-2027 Context
- Australia AML/CTF Amendment Act 2024 Context
- European Banking Authority Travel Rule Guidelines Context
- Congressional Research Service AML/CFT Policy Overview Context
- GAO Illicit-Finance Progress Assessment Context
- RUSI 2025 Terrorist-Financing Reassessment Context
- Charts and Visual Outputs
- Correlation Analysis
- Limitations
- Conclusion
- Future Improvements
- References and Data Sources
- Appendix: Logistic Regression Output

---

## Chart Interpretation

The generated report includes chart explanations for all major visuals:

1. **Top 15 vulnerability scores** — identifies countries with the highest structural vulnerability scores.
2. **Risk score vs. predicted FATF probability** — compares the weighted score with estimated FATF grey-list probability.
3. **Top predicted FATF probabilities** — highlights countries with the highest modeled probability of FATF grey-list status.
4. **Risk tier distribution** — converts the 0-to-100 score into easier-to-communicate risk categories.
5. **Sensitivity overlap** — tests whether the top 20 remains stable across alternate model weights.
6. **Conflict fatalities** — adds supplemental UCDP organized-violence context.
7. **Regional average risk** — compares average vulnerability across World Bank regions.
8. **Current FATF count by region** — summarizes current increased-monitoring jurisdictions by region.
9. **Current FATF status comparison** — compares model-year FATF target coding with the current FATF monitoring supplement.

---

## Supplemental Context Layers

The project includes several supplemental layers that improve interpretation without changing the baseline risk score.

### Conflict Event Data Supplement

Uses UCDP country-year organized violence data as supplemental instability context.

This layer provides:

- UCDP country matching
- Conflict deaths total
- Organized violence active flag
- Conflict intensity category
- Conflict exposure chart

Conflict exposure does not prove terrorism financing activity. It is used as contextual instability information.

### Regional Risk Summary

Uses World Bank country metadata to summarize risk by region.

This layer provides:

- Country count by region
- Average and median risk score by region
- FATF grey-list count by region
- Current FATF monitoring count by region
- Highest-risk country by region

### Sanctions Exposure Template

Creates a structured template for future sanctions exposure indicators.

This template can later be populated with official sanctions-related variables.

The template rows should not be interpreted as evidence of sanctions exposure, FATF deficiencies, or terrorism-financing activity.

### FATF Mutual Evaluation Template

Creates a structured template for future FATF technical compliance and effectiveness indicators.

This template can later be populated with:

- Technical compliance ratings
- Effectiveness ratings
- Immediate Outcome scores
- Mutual evaluation dates
- Follow-up report status

The template rows should not be interpreted as evidence of FATF deficiencies until structured source values are populated.

### Official Terrorism Designation Context

This layer should be treated as designation context only.

Recommended framing:

```text
Official Terrorism Designation Context by Region
```

This should use official sources, such as:

- UN Security Council ISIL/Da'esh and Al-Qaida sanctions list
- U.S. Department of State Foreign Terrorist Organizations list
- Other official government designation lists where relevant

This should not be treated as a list of “confirmed terrorist groups.” Terrorism designations depend on the official list, jurisdiction, legal framework, and date of designation.

---

## Interpretation Guidance

The model is best used for early-stage screening.

Possible use cases:

- Country-risk screening and geographic AML/CFT review
- Prioritizing countries for deeper qualitative review
- Comparing internal risk views against public indicators
- Supporting risk committee discussion
- Supporting academic model documentation
- Adding context to FATF monitoring, conflict exposure, and regional analysis
- Creating a transparent portfolio project for financial-crime, intelligence, and risk analytics roles

The model should not be used for:

- Final country-risk decisions without human review
- Operational targeting
- Law enforcement conclusions
- Transaction monitoring decisions by itself
- Entity-level or customer-level conclusions
- Terrorist-financing determinations

---

## Model Limitations

Key limitations include:

- The model uses country-level indicators and does not identify individual actors, entities, or transactions.
- FATF grey-list status is a policy and regulatory outcome, not a direct measure of terrorism financing activity.
- The model does not include detailed legal, supervisory, enforcement, or financial intelligence data.
- Some countries may have missing or delayed economic data.
- The model does not use 2025 or 2026 as the primary model year because complete comparable country-level data is not available across the core indicators.
- Conflict event data is supplemental context and is not evidence of terrorism financing activity.
- UCDP country matching depends on country-name harmonization.
- Sanctions exposure and FATF mutual-evaluation supplements are template-based unless structured values are manually populated.
- The model does not directly measure virtual-asset activity, privacy-coin exposure, wallet-level behavior, crowdfunding, or online fundraising appeals.
- The model does not directly measure Travel Rule compliance, originator and beneficiary information quality, missing or incomplete transfer information, PSP controls, or CASP controls.
- The model does not directly measure domestic AML/CFT statutory coverage, beneficial ownership implementation, FinCEN-style reporting systems, supervisory examinations, enforcement actions, or congressional policy developments.
- The model does not measure interagency coordination, investigative case outcomes, prosecution results, asset forfeiture, task-force disruption metrics, or government-wide performance tracking for illicit-finance strategies.
- The model does not directly measure fintech-platform controls, instant-payment exposure, online crowdfunding activity, online-gaming financial flows, public-private partnership maturity, or cross-sector intelligence-sharing capacity.
- The current data supplement is a comparison layer and should not be treated as definitive proof of current terrorist-financing activity or absence of risk.
- The model is intended for defensive screening and academic analysis, not operational targeting.

---

## Future Improvements

Potential future extensions include:

- Add sanctions exposure indicators with populated source data.
- Add a virtual-assets and payments compliance supplement using Travel Rule, payment-transfer, and crypto-asset transfer implementation indicators.
- Add a legal and regulatory framework supplement covering AML/CFT statutory scope, beneficial ownership transparency, supervisory coverage, enforcement activity, and digital-asset AML/CFT regulation.
- Add an emerging terrorist-financing typologies supplement covering fintech, instant payments, virtual assets, online crowdfunding, online gaming, and public-private information-sharing maturity.
- Add model-governance tracking that evaluates whether supplemental indicators improve screening performance, ranking stability, and alignment with official illicit-finance strategy benchmarks over time.
- Refine conflict event data matching with a country-name crosswalk.
- Add AML/CFT mutual evaluation data with technical compliance and effectiveness ratings.
- Expand sensitivity analysis with additional weighting scenarios.
- Refine risk-tier interpretation with regional and peer-group comparisons.
- Add additional current FATF comparison visuals over multiple FATF update cycles.
- Expand the Streamlit dashboard with searchable country profiles and downloadable country briefs.
- Add time-series analysis across multiple years.
- Compare results across FATF grey-list updates.

---

## Git and Repository Notes

The recommended `.gitignore` excludes generated outputs, data files, local virtual environments, reports, and system files.

Recommended tracked files include:

- Source code in `src/`
- `app.py`
- `main.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- Empty `.gitkeep` files to preserve folder structure

Recommended generated files to exclude:

- `data/raw/`
- `data/processed/`
- `outputs/charts/`
- `outputs/tables/`
- `outputs/reports/`
- `.venv/`

To keep empty folders in Git, create `.gitkeep` files:

```powershell
New-Item -ItemType File -Force data/raw/.gitkeep
New-Item -ItemType File -Force data/processed/.gitkeep
New-Item -ItemType File -Force outputs/charts/.gitkeep
New-Item -ItemType File -Force outputs/tables/.gitkeep
New-Item -ItemType File -Force outputs/reports/.gitkeep
```

---

## References and Data Sources

The project uses and references sources such as:

1. World Bank Worldwide Governance Indicators
2. World Bank WGI 2025 Revision / WGI 2.0
3. World Bank Reproducibility Package for the WGI 2025 Update
4. World Bank DataBank Worldwide Governance Indicators
5. World Bank API / World Development Indicators
6. Uppsala Conflict Data Program Country-Year Dataset on Organized Violence
7. Financial Action Task Force official sources
8. FATF Black and Grey Lists
9. FATF Recommendations
10. FATF Comprehensive Update on Terrorist Financing Risks
11. U.S. Department of the Treasury National Terrorist Financing Risk Assessment
12. U.S. Department of the Treasury 2024 National Strategy for Combating Terrorist and Other Illicit Financing
13. National Counterterrorism Center, DHS, and FBI public guidance
14. INTERPOL Global Counter-Terrorism Strategy
15. Basel Committee on Banking Supervision AML/CFT risk management guidance
16. South Africa Financial Intelligence Centre Annual Report 2024/25
17. UN Security Council ISIL/Da'esh and Al-Qaida sanctions list
18. U.S. Department of State Foreign Terrorist Organizations list
19. GNET research on privacy coins and illicit-finance risk
20. UAE AML/CFT/CPF National Strategy 2024-2027 context
21. Australia AML/CTF Amendment Act 2024 context
22. European Banking Authority Travel Rule Guidelines
23. Congressional Research Service AML/CFT policy overview
24. U.S. Government Accountability Office illicit-finance progress assessment
25. RUSI 2025 terrorist-financing reassessment context

---

## Disclaimer

This project is for academic, defensive, and financial-crime risk research purposes only.

It does not provide operational guidance, investigative conclusions, terrorist-financing determinations, or compliance advice. Outputs should be reviewed with appropriate qualitative context and official sources before any practical use.
