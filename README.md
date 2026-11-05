# EconoCausal

EconoCausal is a local full-stack application for exploring campaign data, identifying a causal effect, estimating heterogeneous treatment effects, evaluating uplift, and optimizing a binary customer-intervention allocation under a budget.

The current causal-analysis demonstration uses the Hillstrom email-marketing experiment. Generic uploaded CSVs can be explored, but an upload is not automatically suitable for causal analysis or allocation.

## Contents

- [Features and implementation status](#features-and-implementation-status)
- [Architecture and data flow](#architecture-and-data-flow)
- [Hillstrom analysis configuration](#hillstrom-analysis-configuration)
- [Causal concepts and assumptions](#causal-concepts-and-assumptions)
- [Budget optimization](#budget-optimization)
- [Model persistence and compatibility](#model-persistence-and-compatibility)
- [Backend API](#backend-api)
- [Run locally](#run-locally)
- [Train the archive campaign model](#train-the-archive-campaign-model)
- [Tests and quality checks](#tests-and-quality-checks)
- [Known limitations and security](#known-limitations-and-security)

## Features and implementation status

| Area | Current implementation |
| --- | --- |
| Dataset management | Draft-style Data workspace for uploading/selecting data, previewing rows, checking selected treatment/outcome/features, and opening descriptive EDA. Generic exploration does not require Hillstrom fields. |
| Week 1: DoWhy | A Hillstrom DAG and effect-identification endpoint for Womens E-Mail versus No E-Mail. The displayed estimand is conditional on the supplied graph and its assumptions. |
| Week 2: EconML | Cross-fitted `CausalForestDML`, stratified holdout evaluation, a final refit for population scoring, ATE/ITE summaries, held-out Qini and uplift-by-decile output. |
| Week 2: model persistence | Versioned model bundles and metadata sidecars; scoring and allocation check training dataset ID, feature order/types, treatment, and outcome. |
| Week 3: allocation | Binary SciPy mixed-integer optimization with budget, per-customer costs, optional overall customer bounds, and optional per-segment bounds. |
| Week 3: prescriptions | Allocation summary, segment summaries, filterable/paginated results, sorting, selected-only view, and CSV export. |
| Robustness checks | Refutation checks exist in the separate retail archive-campaign analysis. They are not integrated into the Hillstrom Causal Lab. |

## Architecture and data flow

- **Frontend:** React, Vite, React Router, Axios, Plotly.js, Recharts, and the existing CSS design system in `frontend/`.
- **Backend:** FastAPI, Pandas, NumPy, scikit-learn, EconML, DoWhy, SciPy, and joblib in `backend/`.
- **Primary frontend routes:** Data workspace (`/upload`), Uplift analysis (`/uplift`), and Budget allocation (`/allocation`). Dataset preview and exploratory analysis are available from the Data workspace.
- **Uploads:** `backend/data/uploads/`.
- **Versioned causal models:** `backend/models/versions/`.
- **Allocation result CSV and JSON metadata:** `backend/data/allocations/`.
- **Archive-campaign analysis outputs:** `backend/data/processed/` and `backend/data/outputs/`.

The interactive API schema is served by FastAPI at `http://localhost:8000/docs`.

### Main workflow

1. Upload a CSV and select the dataset in the frontend.
2. Inspect its columns and missing values. Generic exploration works without causal fields.
3. For a Hillstrom-compatible dataset, inspect the causal DAG and ask DoWhy to identify the estimand.
4. Train the EconML model. Training returns held-out evaluation results and customer-level model scores, then saves a versioned model bundle.
5. Open Budget allocation, configure a campaign budget and intervention cost, and run binary allocation.
6. Review allocation summaries and customer prescriptions; retrieve or export the persisted results.

Training and optimization currently implement only the Hillstrom comparison described below. A generic CSV upload is not sufficient to enable those steps.

## Hillstrom analysis configuration

The active demonstration comparison is:

- **Treatment:** `Womens E-Mail` (`T=1`).
- **Control:** `No E-Mail` (`T=0`).
- **Outcome:** binary `conversion` (`0` or `1`).
- **Pre-treatment adjustment features:** `recency`, `history_segment`, `history`, `mens`, `womens`, `zip_code`, `newbie`, and `channel`.
- **Excluded treatment arm:** `Mens E-Mail`; it is not folded into either arm.
- **Excluded post-treatment variable:** `visit`; it is not used as a pre-treatment adjustment feature for the total email-treatment effect.

The Hillstrom causal endpoints require the demonstration feature columns plus `segment` and `conversion`. The Data workspace checks this compatibility before enabling the analysis. Its treatment, outcome, and customer-feature selectors are for data-quality review only; they do not reconfigure the Hillstrom causal model. Uploads that do not match can still be inspected and explored.

CSV upload accepts `.csv` files up to 20 MB. The backend rejects empty files, duplicate/blank column names, and files it cannot parse. Dataset IDs are generated by the server.

## Causal concepts and assumptions

These stages answer different questions and should not be treated as interchangeable:

1. **DoWhy identification** constructs a causal model from the configured Hillstrom DAG and returns the estimand implied by that graph. It addresses whether the effect is identifiable under the graph, not whether the graph is true.
2. **EconML estimation** fits a cross-fitted `CausalForestDML` to estimate heterogeneous effects. The preprocessing pipeline imputes numeric/categorical missing values and one-hot encodes categories. A stratified holdout split is reserved for uplift evaluation; the estimator is refit on the eligible data to score customers.
3. **ATE/CATE/ITE reporting** summarizes predicted conditional treatment effects. Customer ITEs are model estimates, not directly observed individual counterfactual outcomes. The reported population ATE is the mean of the final model's customer-level effect predictions.
4. **Uplift/Qini evaluation** ranks held-out customers by predicted effect and reports a cumulative Qini curve, random-targeting reference, Qini area/coefficient, treatment propensity, and treated/control conversion rates and observed uplift by decile.
5. **Refutation checks** in the separate archive workflow probe sensitivity to selected alternative data-generating scenarios. Passing a refutation test does not prove causal assumptions.
6. **SciPy optimization** uses the estimated effects and explicit intervention costs to make a budget-constrained selection. It does not identify or estimate causal effects itself.

The held-out Hillstrom evaluation uses the empirical treatment share in inverse-propensity weighting. This is appropriate for the dataset's randomized assignment design; it is **not** an estimated propensity model and should not be applied blindly to observational data where assignment probabilities vary with customer characteristics.

## Budget optimization

For eligible customer \(i\), let \(\tau_i\) be the predicted conversion treatment effect, \(c_i\) the supplied intervention cost, and \(z_i \in \{0,1\}\) the decision to target that customer. The Hillstrom objective is:

```text
maximize    sum(tau_i * z_i)
subject to  sum(c_i * z_i) <= budget
            z_i is binary
```

The implementation calls `scipy.optimize.milp`; it does not round fractional results from a continuous optimizer. Optional constraints include an overall minimum/maximum number of selected customers and per-segment minimum/maximum counts. Inputs are validated before solving. Invalid costs, empty eligible populations, infeasible constraints, and solver failures are returned as errors rather than successful-looking allocations.

The Hillstrom model estimates email assignment effects, not discount-level effects. An intervention cost must be supplied either as one positive fixed cost per customer or as the name of a positive finite cost column in the CSV. The model does not assume that marketing cost is a discount amount.

Because the current outcome is conversion and the application has no reliable per-customer revenue input, the objective and summary are labeled **expected incremental conversions**, not profit. Estimated profit is not reported. No revenue values are invented.

The allocation API returns all result rows for its saved CSV, plus an initial page. Prescription rows include customer ID, optional segment, predicted ITE, expected incremental benefit, intervention cost, selection status, and a reason. The UI can filter/paginate results, toggle selected-only, sort columns, inspect segment summaries, and export the complete result CSV.

### Allocation request example

```json
{
  "dataset_id": "UPLOAD_DATASET_UUID",
  "budget": 5000,
  "intervention_cost": 15,
  "max_customers": 250,
  "min_customers": 0,
  "customer_id_column": "customer_id",
  "segment_column": "history_segment",
  "segment_limits": {
    "A": {
      "min_customers": 0,
      "max_customers": 100
    }
  }
}
```

Provide exactly one of `intervention_cost` and `intervention_cost_column`. If `customer_id_column` is supplied, its values must be non-empty and unique. Segment constraints require a valid `segment_column`, and every segment named in `segment_limits` must occur in the eligible comparison population.

## Model persistence and compatibility

Every successful DML training run writes a separate pair of files under `backend/models/versions/`:

- `causal_forest_<version>.joblib`: fitted EconML estimator, fitted preprocessing pipeline, feature names/order, and metadata.
- `causal_forest_<version>.json`: human-readable model metadata sidecar.

Metadata includes the version and training time, dataset ID, feature names/order and source dtypes, treatment/outcome definitions, model type, training configuration, and evaluation metrics. `/api/model/list` reports available versions and `/api/model/info` reports the active version's metadata.

The active model is the newest versioned bundle. Inference and allocation require the requested dataset ID to match the model's training dataset and validate the treatment, outcome, feature names/order, and feature dtypes. A model trained on a different upload is rejected; retrain for that dataset before scoring it. Older legacy model files without compatibility metadata cannot pass these checks.

Joblib model files use Python pickle serialization. Load only model files created by a trusted local run; do not load untrusted model artifacts.

## Backend API

All routes are documented interactively at `http://localhost:8000/docs`. Dataset-scoped exploration accepts `dataset_id`; causal identification and training require it. The model inference and allocation operations use the compatible active model.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API welcome and active model filename |
| GET | `/api/health` | Health check |
| POST | `/api/dataset/upload` | Validate and store any CSV |
| GET | `/api/dataset/list` | List uploaded datasets |
| GET | `/api/dataset/inspect?dataset_id=...` | Preview rows, column types, missing counts, and Hillstrom compatibility |
| GET | `/api/dataset/preview?dataset_id=...` | Generic first-10-row preview |
| GET | `/api/dataset/filter?dataset_id=...&column=...&values=...` | Filter by one or more exact categorical values; paginated |
| GET | `/api/dataset/summary?dataset_id=...` | Dataset-level descriptive metrics |
| GET | `/api/dataset/columns?dataset_id=...` | Descriptive column statistics |
| GET | `/api/dataset/value-counts/{column}?dataset_id=...` | Value counts, including missing values |
| GET | `/api/dataset/distribution/{column}?dataset_id=...` | Numeric histogram or categorical distribution |
| GET | `/api/dataset/correlation?dataset_id=...` | Numeric feature correlation matrix |
| GET | `/api/dataset/scatter?dataset_id=...&x=...&y=...` | Sampled numeric scatter data |
| GET | `/api/causal/dag` | Hillstrom demonstration graph and assumptions note |
| GET | `/api/causal/identify?dataset_id=...` | DoWhy identification for the Hillstrom contrast |
| POST | `/api/causal/train?dataset_id=...` | Fit DML, evaluate held-out uplift, score customers, and save a model version |
| GET | `/api/model/status` | Active model status |
| GET | `/api/model/list` | List versioned models and metadata |
| GET | `/api/model/info` | Active model type, dataset, treatment, outcome, and feature metadata |
| GET | `/api/model/ite?dataset_id=...` | Estimate effects for the compatible active dataset |
| GET | `/api/model/uplift-data?dataset_id=...` | Return scores and observed data for the compatible active dataset |
| POST | `/api/allocation/optimize` | Optimize and persist a binary allocation |
| GET | `/api/allocation/{allocation_id}` | Retrieve, filter, sort, and paginate prescription rows |
| GET | `/api/allocation/{allocation_id}/export` | Download the full prescription CSV |
| POST | `/api/archive-campaign/train` | Run the separate local retail archive analysis |
| GET | `/api/archive-campaign/report` | Read the saved archive-campaign report |
| GET | `/api/archive-campaign/scores` | Filter and page through archive-campaign scores |

Common API errors include:

- **400/404:** invalid or missing upload/dataset/result.
- **409:** active model does not match the dataset or lacks required compatibility metadata.
- **413:** uploaded file exceeds 20 MB.
- **422:** invalid causal schema, allocation input, or infeasible allocation constraints.
- **503:** a required optional library/model is unavailable or the optimization solver fails.

## Run locally

Use separate PowerShell terminals for the backend and frontend. From the repository root:

### Backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

The API is available at `http://localhost:8000`; OpenAPI docs are at `http://localhost:8000/docs`.

### Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`, upload or select a dataset in **Data workspace**, then open **Uplift analysis** to identify the effect and train the model. For the Hillstrom workflow, train the model on the selected upload before running allocation. Enter a total budget and an explicit intervention cost in **Budget allocation**.

## Train the archive campaign model

The separate local retail archive workflow expects these files in `backend/data/archive (2)/`:

- `campaign_desc.csv`
- `campaign_table.csv`
- `hh_demographic.csv`
- `transaction_data.csv`

From `backend/` with the project's Python environment active:

```powershell
python train_archive_campaign.py
```

The training script generates the archive model, report, and scores in local `backend/models/` and `backend/data/processed/` paths. The archive data and generated outputs are local artifacts, not application fixtures. This workflow is distinct from the Hillstrom email-treatment DML/allocation model; its scores are not automatically discount recommendations.

## Tests and quality checks

From the repository root:

```powershell
python -m pytest backend\tests -q
```

Frontend checks, from `frontend/`:

```powershell
npm run lint
npm run build
```

The backend tests include deterministic checks for dataset inspection, DML/uplift behavior, binary optimization, budget constraints, infeasible inputs, allocation persistence/retrieval/export, model compatibility, and model metadata persistence. They do not require training a full production model for every unit test.

## Known limitations and security

- DoWhy identification, DML training, inference, and allocation are currently Hillstrom-specific; the generic dataset endpoints do not make an arbitrary dataset causally valid.
- The DAG is configured in backend code, not editable from the UI. The Data workspace's role/feature selectors validate dataset columns only; treatment, outcome, control/treatment values, and model feature sets remain fixed for Hillstrom.
- The current dashboard does not expose DoWhy refutation controls. Refutation functionality belongs to the separate archive-campaign workflow, and its checks do not prove assumptions.
- The Hillstrom uplift calculation uses the experiment's overall assignment share. An observational analysis with heterogeneous treatment propensity needs an appropriate propensity model and diagnostics.
- Multi-treatment or discount-level optimization is not implemented. Do not interpret the binary email-assignment model as estimating discount responses.
- The frontend does not have a dedicated automated test suite configured. A full workspace lint may also report pre-existing issues in files outside the allocation workflow.
- Long-running model training is currently handled by synchronous route logic and may occupy an API worker while it runs.
- This local-development application has no authentication or per-user data isolation. Do not expose it to untrusted networks.
