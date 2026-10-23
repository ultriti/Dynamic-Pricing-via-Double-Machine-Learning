# EconoCausal: Dynamic Pricing via Double Machine Learning

EconoCausal provides a small full-stack workspace for uploading and exploring the Hillstrom email marketing dataset. The Week 2 interface focuses on dataset management, exploratory data analysis, and preparing clean data for later causal analysis. The dashboard does not claim to estimate price or discount effects.

## Week 2 scope

- Upload and validate a Hillstrom CSV.
- Review dataset dimensions, missing values, summary statistics, and a bounded 10-row preview.
- Explore marketing treatment groups, numerical distributions, correlations, and sampled scatter plots.
- Keep the existing saved-model API separate from the Week 2 dashboard.

The Hillstrom dataset contains email campaign treatment groups (`segment`), customer characteristics, visits, conversions, and spend. It does not contain randomized discount amounts. `visit` occurs after campaign treatment, so it should not be used as a pre-treatment feature when estimating the total effect on conversion.

## Technology

- Frontend: React, Vite, React Router, Axios, Tailwind CSS, Recharts, Lucide React
- Backend: FastAPI, Pandas, NumPy, Uvicorn

## Project structure

```text
backend/
  main.py
  requirements.txt
  data/
  models/
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

Uploads must be CSV files no larger than 20 MB and include the Hillstrom columns:

`recency, history_segment, history, mens, womens, zip_code, newbie, channel, segment, visit, conversion, spend`

The existing backend stores uploaded CSVs under `backend/data/uploads` and selects the most recently uploaded dataset unless a `dataset_id` is supplied. This storage is shared by users of the same backend and persists across server restarts; it is intended only for local development and is not production-ready. There is no authentication or per-user access control. Do not expose this development server to untrusted users.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API welcome response |
| GET | `/api/health` | Backend health check |
| POST | `/api/dataset/upload` | Validate and store a Hillstrom CSV |
| GET | `/api/dataset/list` | List uploaded datasets |
| GET | `/api/dataset/preview` | Return the first 10 rows |
| GET | `/api/dataset/summary` | Dataset-level descriptive metrics |
| GET | `/api/dataset/columns` | Descriptive statistics by column |
| GET | `/api/dataset/value-counts/{column}` | Counts by value |
| GET | `/api/dataset/distribution/{column}` | Numeric histogram or category counts |
| GET | `/api/dataset/correlation` | Numeric-column correlation matrix |
| GET | `/api/dataset/scatter` | Sampled numeric X/Y records |
| GET | `/api/model/list` | List saved model files |
| GET | `/api/model/status` | Saved-model availability |
| GET | `/api/model/info` | Saved-model metadata |
| POST | `/api/model/ite` | Run a saved model against compatible uploaded data |

Dataset endpoints accept an optional `dataset_id` query parameter. The Week 2 dashboard uses only the dataset endpoints. The separate Model Analysis page calls the saved-model endpoints only when a model is available; it shows model output, not discount recommendations. Model predictions require the same feature encoding and preprocessing used for training.

## Known limitations

- Uploaded datasets are shared and stored on local disk without authentication or user isolation.
- Uploads accept the Hillstrom schema only.
- The preview endpoint returns at most 10 rows; scatter data is sampled and capped.
- Correlation is descriptive, not causal.
- Model inference depends on a compatible saved `.joblib` bundle and matching preprocessing.
- No treatment effects, uplift scores, or discount allocations are fabricated by the Week 2 dashboard.