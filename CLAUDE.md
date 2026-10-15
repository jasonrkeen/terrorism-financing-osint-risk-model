> This file mirrors `.github/copilot-instructions.md`; keep both in sync when either changes.

# CLAUDE.md — A Quantitative OSINT Model for Country-Level Terrorism Financing Risk

## Purpose
A defensive OSINT model for country-level terrorism financing vulnerability screening using public governance, economic, FATF, conflict, and AML/CFT context indicators.

## Tech stack
- Python; dependencies in `requirements.txt`
- Key libraries: `pandas`, `numpy`, `requests`, `matplotlib`, `statsmodels`, `scikit-learn`, `python-docx`, `docx2pdf`, `streamlit`, `python-dotenv`, `openpyxl`

## Folder structure
- `docs/` (1 files)
- `src/` (21 files)
- `README.md`
- `app.py`
- `main.py`
- `requirements.txt`

## Setup, run, test
- `pip install -r requirements.txt`
- Entry point present: `main.py`
- Entry point present: `app.py`
- No automated tests exist yet; if adding them, use pytest under `tests/`.

## Conventions observed
- Functions use type hints; keep annotating new code.
- Config lives in: `src/config.py`; avoid hardcoding parameters elsewhere.
- API keys are loaded from a local `.env` via python-dotenv; `.env` must stay uncommitted.
- Raw data (`data/raw/`) is gitignored; download/fetch it via the pipeline, do not commit it.
- Public data sources referenced: ACLED, World Bank, OFAC, FATF, GDELT.
- Write paths relative to the repo root (no absolute local paths).

## Output artifacts
- A PDF report is produced; keep it in sync with model changes.
- Streamlit dashboard: `app.py` (run with `streamlit run <file>`).
- Charts are generated with matplotlib.

## Guardrails
- Never commit secrets, API keys, tokens, or `.env` files.
- Do not commit large raw datasets or binaries; keep data fetched or documented with its source.
- Keep analysis source-backed: cite data sources and assumptions; label scenario/forecast outputs as model estimates, not facts.
- Preserve reproducibility: no unseeded randomness, no hidden manual steps.
