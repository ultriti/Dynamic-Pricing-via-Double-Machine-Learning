# EconoCausal: Dynamic Pricing via Double Machine Learning

EconoCausal is a local research prototype for estimating heterogeneous effects of marketing campaign assignment using Double Machine Learning (DML), causal diagrams, propensity-score matching, and DoWhy refutation checks.

## Current review scope

The project has two distinct analysis paths:

1. **Selected-upload Hillstrom email analysis** (`/causal`): preview the active upload and, when its schema is compatible, compare Womens E-Mail with No E-Mail on conversion.
2. **Retail archive campaign analysis**: a separate backend workflow that compares assignment to campaign 18 (TypeA) with no assignment to campaign 18 on household sales during the campaign period. It is not mixed into the active-upload Causal Lab.

The archive is more relevant to retail promotions, but neither dataset records randomized $10 versus $20 discount assignments. The archive's transaction discounts are realized purchase-level amounts, not assigned offer levels. Consequently, neither path estimates discount-specific ITEs, chooses a discount, calculates a valid marketing-budget allocation, or establishes incremental profit.

## Implemented analysis

### Hillstrom path

- CSV upload, dataset selection, preview, summary, exploratory charts, and descriptive statistics.
- DoWhy causal graph and estimand identification.
- EconML `CausalForestDML` comparing Womens E-Mail (treatment) with No E-Mail (control) on conversion.
- Held-out Qini/uplift evaluation and customer-effect scores.

### Retail archive path

- Loads the archive in `backend/data/archive (2)`.
- Builds a household-level cohort for campaign 18, using a 56-day pre-campaign feature window and household sales during campaign days 587-642 as the outcome.
- Excludes households assigned to other campaigns whose campaign windows overlap campaign 18.
- Trains an EconML `CausalForestDML` with random-forest nuisance models; evaluates ranking on a stratified, held-out 30% split and refits on the full eligible cohort for household scores.
- Runs 1:1 propensity-score matching without replacement and reports common support, matched effect, and standardized mean differences before/after matching.
- Uses DoWhy to identify/estimate an adjusted linear effect and runs random-common-cause, placebo-treatment, data-subset, and unobserved-confounder sensitivity checks. Failed checks are surfaced in the report.
- Provides report and household-score APIs for a separately trained archive analysis. The active-upload Causal Lab does not display these archive-wide results.

The retail archive analysis is observational. Matching and refutation tests can reveal fragility but cannot prove that hidden confounding is absent. A positive mean ITE does not establish a useful targeting policy: the ranking must outperform a random baseline on held-out data, and balance/sensitivity diagnostics must be reviewed.

### First trained archive run

The saved campaign 18 run uses 1,761 households (510 assigned, 1,251 not assigned). Its raw sales difference was about $36.79 per household, compared with about $0.94 in the propensity-matched cohort. Matching retained 380 treated households; the maximum absolute standardized mean difference improved from 0.816 to 0.115 but remains above the common 0.1 balance guideline.

The DML mean estimated effect was about $2.92 per household, but its held-out ranking **did not outperform the random-targeting baseline**. The linear sensitivity analysis had a 1.33% robustness value to reduce the estimate to zero; under the illustrative 5%/5% partial-R-squared scenario, the adjusted bounds include zero. These results mean the current archive model is useful for demonstrating the analysis workflow, but its targeting signal is not validated for a business decision.

## Technology

- Frontend: React, Vite, React Router, Axios, Plotly.js, Recharts, Lucide React
- Backend: FastAPI, Pandas, NumPy, scikit-learn, EconML, DoWhy, SciPy, Uvicorn

## Run locally

### Backend

From the repository root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

### Frontend

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and navigate to **Causal Lab**.

## Train the retail archive model

Place the extracted archive files in `backend/data/archive (2)`. The analysis requires:

`campaign_desc.csv`, `campaign_table.csv`, `hh_demographic.csv`, and `transaction_data.csv`

Then, from the `backend` directory with its virtual environment active:

```powershell
python train_archive_campaign.py
```

Training reads transaction records in chunks and writes:

- `backend/models/archive_campaign_18_dml.joblib`
- `backend/data/processed/archive_campaign_18_review.json`
- `backend/data/processed/archive_campaign_18_scores.csv`

The archive and generated data/model outputs are local files and are not included in source control.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API welcome response |
| GET | `/api/health` | Backend health check |
| POST | `/api/dataset/upload` | Validate and store a CSV |
| GET | `/api/dataset/list` | List uploaded datasets |
| GET | `/api/dataset/inspect` | Preview and inspect any selected upload, including its causal-schema compatibility |
| GET | `/api/dataset/preview` | Return the first 10 rows |
| GET | `/api/dataset/summary` | Dataset-level descriptive metrics |
| GET | `/api/dataset/columns` | Descriptive statistics by column |
| GET | `/api/dataset/value-counts/{column}` | Counts by value |
| GET | `/api/dataset/distribution/{column}` | Numeric histogram or category counts |
| GET | `/api/dataset/correlation` | Numeric-column correlation matrix |
| GET | `/api/dataset/scatter` | Sampled numeric X/Y records |
| GET | `/api/causal/dag` | Hillstrom causal graph |
| GET | `/api/causal/identify` | Identify the Hillstrom graph estimand with DoWhy |
| POST | `/api/causal/train` | Fit Hillstrom DML and return held-out uplift results |
| GET | `/api/model/status` | Check legacy saved-model availability |
| GET | `/api/model/info` | Inspect legacy saved-model metadata |
| GET | `/api/model/ite` | Run legacy saved-model inference |
| POST | `/api/archive-campaign/train` | Train and audit the local retail archive analysis |
| GET | `/api/archive-campaign/report` | Read the saved retail archive review report |
| GET | `/api/archive-campaign/scores` | Filter and page household-level scores |

The Causal Lab reads preview and schema details for the active `dataset_id`. Its DoWhy and DML endpoints require an explicit `dataset_id` and accept only uploads containing the required Hillstrom feature, treatment, and outcome columns. Incompatible uploads still show their own preview and missing-column feedback, but cannot trigger Hillstrom analysis. Archive analysis uses campaign 18 from the local archive and is independent of the active upload.

## Tests

From the repository root:

```powershell
python -m pytest backend\tests -q
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Local-development caveat

Uploaded datasets and generated artifacts are stored locally. The application has no authentication or per-user access control and is intended for local review, not exposure to untrusted users.
