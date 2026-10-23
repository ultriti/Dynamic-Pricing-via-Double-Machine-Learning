# EconoCausal — Dynamic Pricing via Double Machine Learning

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

- Frontend: React, Vite, React Router, Axios, Tailwind CSS, Plotly.js, Recharts, Lucide React
- Backend: FastAPI, Pandas, NumPy, scikit-learn, EconML, DoWhy, Uvicorn

## Project structure

```text
backend/
  causal_engine.py
  main.py
  requirements.txt
  data/
  models/
  tests/
frontend/
  src/
    components/
    pages/
    services/api.js
    App.jsx
README.md
```

## Run locally

### Backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend runs at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

### Frontend

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Dataset requirements and storage

Uploads must be CSV files no larger than 20 MB. Causal analysis expects the Hillstrom columns:

`recency, history_segment, history, mens, womens, zip_code, newbie, channel, segment, conversion`

The full sample dataset also has `visit` and `spend`. Uploaded CSVs are stored under `backend/data/uploads`; each browser remembers its active dataset ID, while the backend's storage is shared and persists across server restarts. This setup is for local development only: it has no authentication or per-user access control and should not be exposed to untrusted users.

The campaign budget is stored in browser local storage and is not sent to the backend. It is a Week 1 planning constraint only; optimization and personalized discount allocation are outside the Weeks 1–2 scope.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API welcome response |
| GET | `/api/health` | Backend health check |
| POST | `/api/dataset/upload` | Validate and store a CSV |
| GET | `/api/dataset/list` | List uploaded datasets |
| GET | `/api/dataset/preview` | Return the first 10 rows |
| GET | `/api/dataset/summary` | Dataset-level descriptive metrics |
| GET | `/api/dataset/columns` | Descriptive statistics by column |
| GET | `/api/dataset/value-counts/{column}` | Counts by value |
| GET | `/api/dataset/distribution/{column}` | Numeric histogram or category counts |
| GET | `/api/dataset/correlation` | Numeric-column correlation matrix |
| GET | `/api/dataset/scatter` | Sampled numeric X/Y records |
| GET | `/api/causal/dag` | Causal graph nodes, edges, and assumptions |
| GET | `/api/causal/identify` | Identify the graph estimand with DoWhy |
| POST | `/api/causal/train` | Fit DML and return held-out ITE and uplift evaluation |
| GET | `/api/model/status` | Check legacy saved-model availability |
| GET | `/api/model/info` | Inspect legacy saved-model metadata |
| GET | `/api/model/ite` | Run legacy saved-model inference |

Dataset endpoints and causal training accept an optional `dataset_id`; the frontend supplies the active uploaded dataset automatically.

## Tests

From the repository root, with backend dependencies installed:

```powershell
python -m pytest backend\tests -q
```

The frontend can be checked with:

```powershell
cd frontend
npm run lint
npm run build
```
