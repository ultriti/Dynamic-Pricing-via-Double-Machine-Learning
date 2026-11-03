# EconoCausal: Dynamic Pricing via Double Machine Learning

<<<<<<<<< Temporary merge branch 1
This is the frontend application for the **EconoCausal** project. It provides an interactive dashboard for marketing directors to visualize causal treatment effects, analyze customer segments, and optimize discount allocation using Double Machine Learning (DML).

## 🚀 Features Built
- **Overview Dashboard:** Displays the core business metrics, a custom `ExecutiveSummary` component translating ML results into plain language, and the interactive Plotly **Uplift Curve** (proving the Causal Model outperforms random targeting).
- **Data Upload:** A fully functional drag-and-drop CSV uploader that connects to the FastAPI backend, with loading states and error handling.
- **Exploratory Data Analysis (EDA):** A dynamic analysis page that fetches backend data to render KPI cards, treatment group distributions, and a correlation matrix.
- **Allocation Matrix:** A prescriptive table showing the optimal discount assignment for specific user segments (e.g., "Persuadable" vs. "Sure Thing").
- **User Experience:** Custom error boundaries and empty states (e.g., graceful fallback when the backend is disconnected).

## 🛠️ Tech Stack
- **Framework:** React 18 (powered by Vite)
- **Routing:** React Router DOM
- **Data Visualization:** Plotly.js (`react-plotly.js`)
- **Styling:** Custom CSS with CSS Variables for a consistent design system
- **API Integration:** Fetch API connecting to a local FastAPI server (`http://localhost:8000`)

## 💻 How to Run Locally

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
=========
EconoCausal is a full-stack causal-analysis workspace for the first two project weeks. It supports historical campaign data upload, a Week 1 DoWhy causal graph, Week 2 EconML Double Machine Learning, and held-out Qini/uplift visualizations.

## Implemented scope: Weeks 1–2

### Week 1 — Causal graphing and dashboard setup

- Upload a Hillstrom campaign CSV and inspect its schema, missing values, and sample rows.
- Set a campaign budget constraint in the upload view. The value is saved in the current browser for the later allocation phase; this version does not allocate discounts.
- View the causal DAG for customer confounders, the email-treatment assignment, and conversion.
- Ask DoWhy to identify the estimand implied by the graph.
- Exclude `visit` from the graph and model features because it occurs after treatment.

### Week 2 — Double Machine Learning and uplift curves

- Fit an EconML `CausalForestDML` using random-forest outcome and treatment nuisance models with cross-fitting.
- Compare `Womens E-Mail` (treatment) with `No E-Mail` (control), using conversion as the outcome and pre-treatment customer characteristics as confounders.
- Evaluate ITE ranking on a held-out split; display Qini and observed uplift-by-decile charts using Plotly.
- Filter and page through held-out customer-level treatment-effect estimates.

The Hillstrom dataset is an email-marketing experiment: it does not contain $10/$20 discount treatments. The dashboard therefore estimates the email-assignment effect on conversion, not discount-level effects. ITEs are model estimates rather than known individual counterfactuals. The Qini comparison uses held-out observations and a random-rollout baseline; results depend on the assignment and measurement assumptions and are not proof that hidden confounding is absent.

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
