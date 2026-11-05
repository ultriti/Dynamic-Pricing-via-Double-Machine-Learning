from __future__ import annotations
from typing import Optional
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone
import json
import logging

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

# ----------------------------- import
from utils.general_helper import json_records, dataset_path
from causal_engine_exp import train_dml_analysis
from dependencies.Dataset_filtering import HILLSTROM_COLUMNS
from dataset_inspection import inspect_uploaded_dataset
from archive_campaign import (
    REPORT_DIR as ARCHIVE_REPORT_DIR,
    train_archive_campaign_model,
)
from budget_optimization import optimize_allocation
from dowhy_compat import load_causal_model

# ---------------------------
# Paths and application setup

BASE_DIR = Path(__file__).resolve().parent

print("path :", BASE_DIR)


UPLOAD_DIR = BASE_DIR / "data" / "uploads"
MODEL_PATH = BASE_DIR / "models" / "conversion_causal_forest_v1.joblib"
MODEL_VERSIONS_DIR = BASE_DIR / "models" / "versions"
ALLOCATION_DIR = BASE_DIR / "data" / "allocations"
RAW_HILLSTROM_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOCATION_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="EconoCausal API",
    description="Hillstrom dataset exploration and causal-effect analysis",
    version="1.0.0",
)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):517\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/archive-campaign/report")
def archive_campaign_report():
    report_path = ARCHIVE_REPORT_DIR / "archive_campaign_18_review.json"
    if not report_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="No archive campaign analysis is available. Train it first.",
        )
    return json.loads(report_path.read_text(encoding="utf-8"))


@app.get("/api/archive-campaign/scores")
def archive_campaign_scores(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    minimum_effect: float | None = None,
    query: str | None = None,
):
    scores_path = ARCHIVE_REPORT_DIR / "archive_campaign_18_scores.csv"
    if not scores_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="No archive campaign scores are available. Train the model first.",
        )
    scores = pd.read_csv(scores_path)
    if minimum_effect is not None:
        scores = scores.loc[scores["estimated_sales_effect"].ge(minimum_effect)]
    if query:
        scores = scores.loc[
            scores["household_key"].astype(str).str.contains(query, case=False, regex=False)
        ]
    total = len(scores)
    page = scores.iloc[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "scores": json_records(page),
    }

# Features used for customer-level inference.
# IMPORTANT: These must match the features and preprocessing used to train the model.
DEFAULT_FEATURE_COLUMNS = [
    "recency",
    "history_segment",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
]
CAUSAL_REQUIRED_COLUMNS = DEFAULT_FEATURE_COLUMNS + ["segment", "conversion"]

# --------------------------
# load dataset 


def load_dataset(
    dataset_id: Optional[str] = None,
) -> tuple[str, pd.DataFrame]:
    """
    Load a dataset by ID if provided.
    Otherwise, find the latest uploaded CSV with the required features.
    """

    if dataset_id is not None:
        # Explicit ID: load that particular dataset.
        path = dataset_path(dataset_id)

        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        candidates = [(dataset_id, path)]

    else:
        # No ID: search all uploaded CSVs by their features.
        paths = list(UPLOAD_DIR.glob("*.csv"))

        if not paths:
            raise HTTPException(
                status_code=404,
                detail="No dataset uploaded yet.",
            )

        candidates = [
            (path.stem, path)
            for path in sorted(
                paths,
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        ]

    for candidate_id, path in candidates:
        try:
            # Read only the header first to check feature compatibility.
            columns = set(
                pd.read_csv(path, nrows=0).columns.astype(str).str.strip()
            )

            missing_features = set(DEFAULT_FEATURE_COLUMNS) - columns

            if missing_features:
                if dataset_id is not None:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "message": "Dataset does not have the required features.",
                            "missing_features": sorted(missing_features),
                        },
                    )
                continue

            df = pd.read_csv(path)
            df.columns = df.columns.astype(str).str.strip()

        except HTTPException:
            raise
        except Exception as exc:
            if dataset_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not read CSV: {exc}",
                )
            continue

        if df.empty:
            continue

        return candidate_id, df

    raise HTTPException(
        status_code=422,
        detail=(
            "No compatible dataset found. "
            "Upload a CSV containing all required features."
        ),
    )


def load_exploration_dataset(
    dataset_id: Optional[str] = None,
) -> tuple[str, pd.DataFrame]:
    """Load any uploaded CSV for generic descriptive exploration."""
    if dataset_id is not None:
        path = dataset_path(dataset_id)
        resolved_id = dataset_id
    else:
        paths = sorted(
            UPLOAD_DIR.glob("*.csv"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if not paths:
            raise HTTPException(status_code=404, detail="No dataset uploaded yet.")
        path = paths[0]
        resolved_id = path.stem
    try:
        frame = pd.read_csv(path)
        frame.columns = frame.columns.astype(str).str.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not read uploaded CSV: {exc}"
        ) from exc
    return resolved_id, frame


# --------------------------
#  check hailstraom schema 

def check_hillstrom_schema(df: pd.DataFrame) -> dict:
    missing = [col for col in HILLSTROM_COLUMNS if col not in df.columns]
    return {
        "compatible_columns": len(missing) == 0,
        "missing_columns": missing,
        "extra_columns": [col for col in df.columns if col not in HILLSTROM_COLUMNS],
        "message": (
            "All expected Hillstrom columns are present."
            if not missing
            else "This dataset is missing required Hillstrom columns."
        ),
    }

# --------------------------
# load trained model 

def active_model_path() -> Path:
    versions = sorted(
        MODEL_VERSIONS_DIR.glob("causal_forest_*.joblib"),
        key=lambda item: item.stat().st_mtime,
    )
    return versions[-1] if versions else MODEL_PATH


def load_model():
    """Load a trusted model bundle or estimator from the configured file."""
    model_path = active_model_path()
    if not model_path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Saved model not found at: {model_path}",
        )
    try:
        saved = joblib.load(model_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load model: {exc}")

    # Preferred format: a dictionary with model and training metadata.
    if isinstance(saved, dict) and "model" in saved:
        model = saved["model"]
        features = saved.get("feature_columns", DEFAULT_FEATURE_COLUMNS)
        preprocessor = saved.get("preprocessor")
        metadata = saved.get("metadata", {})
    else:
        # Supports a directly saved estimator, but cannot infer its preprocessing.
        model = saved
        features = DEFAULT_FEATURE_COLUMNS
        preprocessor = None
        metadata = {}

    return model, list(features), preprocessor, metadata


def validate_model_dataset(
    dataset_id: str, features: list[str], metadata: dict, frame: pd.DataFrame
) -> None:
    """Prevent inference against datasets other than the model's training upload."""
    expected_dataset_id = metadata.get("dataset_id")
    if not expected_dataset_id:
        raise HTTPException(
            status_code=409,
            detail="The saved model has no dataset compatibility metadata; retrain it.",
        )
    if expected_dataset_id != dataset_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "The saved model was trained on a different dataset. "
                "Train a model for the selected dataset before scoring or allocation."
            ),
        )
    if metadata.get("feature_columns") != features:
        raise HTTPException(
            status_code=409,
            detail="The saved model feature schema is incompatible; retrain the model.",
        )
    expected_schema = metadata.get("feature_schema")
    if not expected_schema or any(
        column not in frame.columns
        or str(frame[column].dtype) != expected_schema.get(column)
        for column in features
    ):
        raise HTTPException(
            status_code=409,
            detail="The selected dataset feature types do not match model training.",
        )
    if metadata.get("outcome") != "conversion" or metadata.get(
        "treatment_definition"
    ) != "Womens E-Mail (T=1) vs No E-Mail (T=0)":
        raise HTTPException(
            status_code=409,
            detail="The saved model treatment or outcome definition is incompatible.",
        )


class SegmentAllocationLimit(BaseModel):
    min_customers: int = Field(default=0, ge=0)
    max_customers: int | None = Field(default=None, ge=0)


class AllocationRequest(BaseModel):
    dataset_id: str = Field(min_length=1)
    budget: float = Field(gt=0)
    intervention_cost: float | None = Field(default=None, gt=0)
    intervention_cost_column: str | None = None
    max_customers: int | None = Field(default=None, ge=0)
    min_customers: int = Field(default=0, ge=0)
    customer_id_column: str | None = None
    segment_column: str | None = None
    segment_limits: dict[str, SegmentAllocationLimit] = Field(default_factory=dict)


# ----------------------------
# compae the given data wih hailstroam - make itgeneric to comapre

def prepare_hillstrom_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make a binary comparison:
    Womens E-Mail = T=1; No E-Mail = T=0.
    Exclude Mens E-Mail because it is a different treatment arm.
    """
    if "segment" not in df.columns:
        raise HTTPException(
            status_code=400, detail="Missing 'segment' treatment column."
        )

    allowed = ["Womens E-Mail", "No E-Mail"]
    selected = df[df["segment"].isin(allowed)].copy()
    if selected.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "No rows found for 'Womens E-Mail' or 'No E-Mail'. "
                "Check the exact values in the segment column."
            ),
        )

    selected["email_treatment"] = (
        selected["segment"].astype(str).str.strip().eq("Womens E-Mail")
    ).astype(int)
    return selected


def encode_model_features(features: pd.DataFrame) -> pd.DataFrame:
    """Keep raw features for the fitted training preprocessor."""
    return features.copy()


# ---------------------------
# Basic endpoints
@app.get("/")
def home():
    return {
        "message": "EconoCausal API is running",
        "docs": "/docs",
        "model_file": active_model_path().name,
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}


# ---------------------------
# Week 1: upload and explore data


@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload any CSV; report whether it has the expected Hillstrom columns."""

    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum upload size is 20 MB.")

    try:
        df = pd.read_csv(BytesIO(content))
        df.columns = df.columns.astype(str).str.strip()

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    if df.empty:
        raise HTTPException(
            status_code=400, detail="CSV must contain at least one data row."
        )
    if df.columns.duplicated().any():
        raise HTTPException(status_code=400, detail="CSV has duplicate column names.")
    if any(not col for col in df.columns):
        raise HTTPException(status_code=400, detail="Every column must have a name.")

    new_id = str(uuid4())
    (UPLOAD_DIR / f"{new_id}.csv").write_bytes(content)

    return {
        "message": "Dataset uploaded.",
        "dataset_id": new_id,
        "filename": Path(file.filename or "upload.csv").name,
        "rows": int(len(df)),
        "columns": df.columns.tolist(),
        "missing_values": int(df.isna().sum().sum()),
        "hillstrom_compatibility": check_hillstrom_schema(df),
    }


@app.get("/api/dataset/list")
def list_datasets():
    datasets = []
    for path in sorted(
        UPLOAD_DIR.glob("*.csv"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        try:
            columns = pd.read_csv(path, nrows=0).columns.tolist()
            datasets.append(
                {
                    "dataset_id": path.stem,
                    "filename": path.name,
                    "columns": columns,
                    "size_bytes": path.stat().st_size,
                }
            )
        except Exception:
            continue
    return {"total": len(datasets), "datasets": datasets}


@app.get("/api/dataset/inspect")
def inspect_dataset(dataset_id: str = Query(...)):
    """Inspect an uploaded CSV without imposing Hillstrom model requirements."""
    path = dataset_path(dataset_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    try:
        return inspect_uploaded_dataset(
            path,
            dataset_id,
            causal_required_columns=CAUSAL_REQUIRED_COLUMNS,
            hillstrom_required_columns=HILLSTROM_COLUMNS,
        )
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not inspect uploaded CSV: {exc}"
        ) from exc


@app.get("/api/dataset/preview")
def dataset_preview(dataset_id: Optional[str] = None):
    dataset_id, df = load_exploration_dataset(dataset_id)
    return {
        "dataset_id": dataset_id,
        "rows": len(df),
        "columns": df.columns.tolist(),
        "data": json_records(df.head(10)),
    }


@app.get("/api/dataset/filter")
def dataset_filter(
    column: str,
    values: list[str] = Query(..., min_length=1),
    dataset_id: Optional[str] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Filter any uploaded dataset by one or more exact categorical values."""
    resolved_id, df = load_exploration_dataset(dataset_id)
    if column not in df.columns:
        raise HTTPException(status_code=422, detail=f"Unknown dataset column '{column}'.")
    value_mask = df[column].astype(str).isin(
        [value for value in values if value != "(Missing)"]
    )
    if "(Missing)" in values:
        value_mask |= df[column].isna()
    selected = df.loc[value_mask]
    total = len(selected)
    return {
        "dataset_id": resolved_id,
        "column": column,
        "values": values,
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": json_records(selected.iloc[offset : offset + limit]),
    }


# -----------------------------------
# csv file summary
@app.get("/api/dataset/summary")
def dataset_summary(dataset_id: Optional[str] = None):
    dataset_id, df = load_exploration_dataset(dataset_id)

    # get all details of the csv ----
    result = {
        "dataset_id": dataset_id,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": int(df.isna().sum().sum()),
        "hillstrom_compatibility": check_hillstrom_schema(df),
    }

    for col in ["conversion", "visit"]:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            result[f"{col}_rate_percent"] = (
                round(float(values.mean() * 100), 2) if values.notna().any() else None
            )

    if "spend" in df.columns:
        spend = pd.to_numeric(df["spend"], errors="coerce")
        result["total_spend"] = round(float(spend.sum()), 2)
        result["average_spend"] = round(float(spend.mean()), 2)

    if "segment" in df.columns:
        result["treatment_group_counts"] = {
            str(key): int(value)
            for key, value in df["segment"].value_counts(dropna=False).items()
        }
    return result


@app.get("/api/dataset/columns")
def dataset_columns(dataset_id: Optional[str] = None):
    dataset_id, df = load_exploration_dataset(dataset_id)
    stats = (
        df.describe(include="all")
        .astype(object)
        .where(pd.notna(df.describe(include="all")), None)
    )
    # print({"dataset_id": dataset_id, "stats": jsonable_encoder(stats.to_dict())})
    return {"dataset_id": dataset_id, "stats": jsonable_encoder(stats.to_dict())}


# -----------------------------
# yet not implemented - frontend


@app.get("/api/dataset/value-counts/{column}")
def dataset_value_counts(column: str, dataset_id: Optional[str] = None):
    dataset_id, df = load_exploration_dataset(dataset_id)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found.")
    counts = df[column].value_counts(dropna=False)
    print(
        {
            "dataset_id": dataset_id,
            "column": column,
            "counts": {
                str(key) if pd.notna(key) else "(Missing)": int(value)
                for key, value in counts.items()
            },
        }
    )
    return {
        "dataset_id": dataset_id,
        "column": column,
        "counts": {
            str(key) if pd.notna(key) else "(Missing)": int(value)
            for key, value in counts.items()
        },
    }


# ----------------------------
# correlation matrix graph
@app.get("/api/dataset/correlation")
def dataset_correlation(dataset_id: Optional[str] = None):
    dataset_id, df = load_exploration_dataset(dataset_id)
    numeric = df.select_dtypes(include="number")
    corr = numeric.corr().round(3).astype(object)
    corr = corr.where(pd.notna(corr), None)
    return {
        "dataset_id": dataset_id,
        "columns": numeric.columns.tolist(),
        "correlation": jsonable_encoder(corr.to_dict()),
    }


@app.get("/api/dataset/distribution/{column}")
def dataset_distribution(
    column: str,
    dataset_id: Optional[str] = None,
    bins: int = Query(default=20, ge=1, le=100),
):
    dataset_id, df = load_exploration_dataset(dataset_id)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found.")

    values = df[column].dropna()
    numeric = pd.to_numeric(values, errors="coerce")
    if len(values) and numeric.notna().all():
        counts, edges = np.histogram(numeric, bins=bins)
        labels = [f"{edges[i]:.2f}-{edges[i + 1]:.2f}" for i in range(len(counts))]
        return {
            "dataset_id": dataset_id,
            "column": column,
            "type": "numeric",
            "labels": labels,
            "values": counts.astype(int).tolist(),
        }

    counts = values.astype(str).value_counts()

    # print(
    #     {
    #         "dataset_id": dataset_id,
    #         "column": column,
    #         "type": "categorical",
    #         "labels": counts.index.tolist(),
    #         "values": counts.astype(int).tolist(),
    #     }
    # )
    return {
        "dataset_id": dataset_id,
        "column": column,
        "type": "categorical",
        "labels": counts.index.tolist(),
        "values": counts.astype(int).tolist(),
    }

# -----------------------------
# scatter plot map
@app.get("/api/dataset/scatter")
def dataset_scatter(
    x: str = "history",
    y: str = "spend",
    dataset_id: Optional[str] = None,
    sample: int = Query(default=500, ge=1, le=5000),
):
    dataset_id, df = load_exploration_dataset(dataset_id)
    if x not in df.columns or y not in df.columns:
        raise HTTPException(
            status_code=400, detail="Requested x or y column not found."
        )

    plot = df[[x, y]].copy()
    plot[x] = pd.to_numeric(plot[x], errors="coerce")
    plot[y] = pd.to_numeric(plot[y], errors="coerce")
    plot = plot.replace([np.inf, -np.inf], np.nan).dropna()
    total = len(plot)
    if total > sample:
        plot = plot.sample(sample, random_state=42)
    return {
        "dataset_id": dataset_id,
        "x": x,
        "y": y,
        "valid_points": total,
        "data": json_records(plot),
    }


# ---------------------------
# Week 1: causal DAG and DoWhy identification
# ---------------------------


@app.get("/api/causal/dag")
def causal_dag():
    """
    DAG for the Hillstrom comparison:
    customer features -> treatment, customer features -> conversion,
    treatment -> conversion.
    `visit` is omitted because it occurs after treatment.
    """
    graph = """
    digraph {
        recency -> email_treatment;
        history -> email_treatment;
        history_segment -> email_treatment;
        mens -> email_treatment;
        womens -> email_treatment;
        zip_code -> email_treatment;
        newbie -> email_treatment;
        channel -> email_treatment;

        recency -> conversion;
        history -> conversion;
        history_segment -> conversion;
        mens -> conversion;
        womens -> conversion;
        zip_code -> conversion;
        newbie -> conversion;
        channel -> conversion;

        email_treatment -> conversion;
    }
    """
    nodes = [
        {"id": feature, "label": feature, "role": "confounder"}
        for feature in DEFAULT_FEATURE_COLUMNS
    ]
    nodes.extend(
        [
            {
                "id": "email_treatment",
                "label": "Email treatment",
                "role": "treatment",
            },
            {"id": "conversion", "label": "Conversion", "role": "outcome"},
        ]
    )
    edges = [
        {"source": feature, "target": target}
        for feature in DEFAULT_FEATURE_COLUMNS
        for target in ["email_treatment", "conversion"]
    ]
    edges.append({"source": "email_treatment", "target": "conversion"})
    return {
        "treatment": "email_treatment (Womens E-Mail=1, No E-Mail=0)",
        "outcome": "conversion",
        "confounders": DEFAULT_FEATURE_COLUMNS,
        "nodes": nodes,
        "edges": edges,
        "excluded_post_treatment_variable": "visit",
        "dot_graph": graph,
        "note": (
            "This graph encodes the chosen assumptions; it does not prove "
            "that all confounders have been measured."
        ),
    }


@app.get("/api/causal/identify")
def identify_causal_effect(dataset_id: str = Query(...)):
    """Use DoWhy to identify an average effect for Womens E-Mail vs No E-Mail."""
    try:
        CausalModel = load_causal_model()
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="DoWhy is not installed. Install it with: pip install dowhy",
        )

    resolved_id, df = load_dataset(dataset_id)
    required = DEFAULT_FEATURE_COLUMNS + ["segment", "conversion"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Dataset lacks columns needed for causal identification.",
                "missing": missing,
            },
        )

    selected = prepare_hillstrom_comparison(df)
    selected["conversion"] = pd.to_numeric(selected["conversion"], errors="coerce")
    selected = selected.dropna(subset=["conversion"])
    if selected.empty or selected["email_treatment"].nunique() < 2:
        raise HTTPException(
            status_code=400,
            detail="Need both treatment and control rows with valid conversion outcomes.",
        )

    # DoWhy's common_causes should be columns in the provided data.
    # Categorical features are retained as strings here for identification.
    causal_data = selected[
        DEFAULT_FEATURE_COLUMNS + ["email_treatment", "conversion"]
    ].copy()
    graph = """
    digraph {
        recency -> email_treatment; history -> email_treatment;
        history_segment -> email_treatment; mens -> email_treatment;
        womens -> email_treatment; zip_code -> email_treatment;
        newbie -> email_treatment; channel -> email_treatment;
        recency -> conversion; history -> conversion;
        history_segment -> conversion; mens -> conversion;
        womens -> conversion; zip_code -> conversion;
        newbie -> conversion; channel -> conversion;
        email_treatment -> conversion;
    }
    """
    try:
        model = CausalModel(
            data=causal_data,
            treatment="email_treatment",
            outcome="conversion",
            graph=graph,
        )
        estimand = model.identify_effect()
        
        return {
            "dataset_id": resolved_id,
            "treatment": "Womens E-Mail vs No E-Mail",
            "outcome": "conversion",
            "identified_estimand": (
                "E[conversion | email_treatment=1, X] - "
                "E[conversion | email_treatment=0, X]"
            ),
            "adjustment_set": DEFAULT_FEATURE_COLUMNS,
            "estimand_method": "Backdoor adjustment",
            "warning": "Identification depends on the supplied DAG and measured-confounder assumptions.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"DoWhy identification failed: {exc}"
        )


# ---------------------------
# Week 2: Double Machine Learning and held-out uplift evaluation
# ---------------------------


@app.post("/api/causal/train")
def train_causal_model(dataset_id: str = Query(...)):
    """Fit an EconML DML forest and evaluate uplift with out-of-fold predictions."""
    resolved_id, df = load_dataset(dataset_id)
    try:
        result = train_dml_analysis(df, DEFAULT_FEATURE_COLUMNS)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"DML training or out-of-fold evaluation failed: {exc}",
        ) from exc

    model = result.pop("_model")
    preprocessor = result.pop("_preprocessor")
    feature_columns = result.pop("_feature_columns")

    customers = result.pop("customers", [])
    result["customers"] = customers
    version_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid4().hex[:8]
    )
    model_path = MODEL_VERSIONS_DIR / f"causal_forest_{version_id}.joblib"
    MODEL_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    model_metadata = {
        "model_version": version_id,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": resolved_id,
        "treatment_definition": result.get("treatment"),
        "outcome": result.get("outcome"),
        "feature_columns": feature_columns,
        "feature_schema": {
            column: str(df[column].dtype) for column in feature_columns
        },
        "model_type": result.get("estimator"),
        "training_configuration": {
            "random_state": 42,
            "cross_fitting_folds": 3,
            "evaluation_folds": result.get("evaluation_folds"),
            "qini_bootstrap_samples": result.get("qini_bootstrap_samples"),
        },
        "evaluation_metrics": {
            "qini_coefficient": result.get("qini_coefficient"),
            "evaluation_customers": result.get("evaluation_customers"),
            "treatment_propensity": result.get("treatment_propensity"),
        },
    }
    joblib.dump(
        {
            "model": model,
            "preprocessor": preprocessor,
            "feature_columns": feature_columns,
            "metadata": model_metadata,
        },
        model_path,
    )
    model_path.with_suffix(".json").write_text(
        json.dumps(jsonable_encoder(model_metadata), allow_nan=False),
        encoding="utf-8",
    )

    return {
        "dataset_id": resolved_id,
        "model_id": model_path.stem,
        "model_version": version_id,
        **result,
    }


@app.get("/api/model/status")
def model_status():
    model_path = active_model_path()
    return {
        "model_id": model_path.stem,
        "model_file": str(model_path),
        "exists": model_path.is_file(),
    }


@app.get("/api/model/list")
def list_models():
    model_versions = []
    for metadata_path in sorted(
        MODEL_VERSIONS_DIR.glob("causal_forest_*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        model_path = metadata_path.with_suffix(".joblib")
        model_versions.append(
            {
                "model_id": model_path.stem,
                "model_file": model_path.name,
                "exists": model_path.is_file(),
                "metadata": json.loads(metadata_path.read_text(encoding="utf-8")),
            }
        )
    if not model_versions and MODEL_PATH.is_file():
        model_versions.append(
            {
                "model_id": MODEL_PATH.stem,
                "model_file": MODEL_PATH.name,
                "exists": True,
                "metadata": None,
            }
        )
    return {"total": len(model_versions), "models": model_versions}


@app.get("/api/model/info")
def model_info():
    model, features, preprocessor, metadata = load_model()
    return {
        "model_id": active_model_path().stem,
        "model_class": type(model).__name__,
        "feature_columns": features,
        "has_preprocessor": preprocessor is not None,
        "outcome": metadata.get("outcome"),
        "treatment_definition": metadata.get("treatment_definition"),
        "dataset_id": metadata.get("dataset_id"),
        "model_version": metadata.get("model_version"),
        "trained_at": metadata.get("trained_at"),
        "metadata_available": bool(metadata),
    }


@app.get("/api/model/ite")
def model_ite(dataset_id: Optional[str] = None):
    """Estimate ITEs for uploaded data using the saved model."""
    resolved_id, df = load_dataset(dataset_id)
    model, features, preprocessor, metadata = load_model()
    validate_model_dataset(resolved_id, features, metadata, df)

    missing = [col for col in features if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Dataset is missing model feature columns.",
                "missing_features": missing,
                "expected_features": features,
            },
        )

    # Only score the Women's Email and No Email rows for this binary model.
    selected = prepare_hillstrom_comparison(df)
    X = encode_model_features(selected[features])

    try:
        if preprocessor is not None:
            X = preprocessor.transform(X)
        effects = np.asarray(model.effect(X, T0=0, T1=1)).reshape(-1)
        if len(effects) != len(selected) or not np.isfinite(effects).all():
            raise ValueError("Model returned invalid treatment-effect values.")
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "ITE inference failed. The model must be an EconML estimator with "
                "an effect(X, T0=0, T1=1) method, and features/preprocessing must "
                f"match training. Details: {exc}"
            ),
        )

    results = pd.DataFrame(
        {
            "row_id": selected.index.astype(str),
            "treatment_group": selected["segment"].astype(str).values,
            "ite": effects,
        }
    )
    results["effect_percentage_points"] = results["ite"] * 100

    return {
        "model_id": active_model_path().stem,
        "dataset_id": resolved_id,
        "treatment": "Womens E-Mail (T=1) vs No E-Mail (T=0)",
        "outcome": "conversion",
        "customers_scored": int(len(results)),
        "mean_ite": float(results["ite"].mean()),
        "positive_effect_count": int((results["ite"] > 0).sum()),
        "negative_effect_count": int((results["ite"] < 0).sum()),
        "customers": json_records(results),
        "warning": (
            "ITE values are model estimates, not known individual counterfactuals. "
            "Use only if the uploaded dataset is compatible with training data."
        ),
    }


@app.get("/api/model/uplift-data")
def uplift_data(dataset_id: Optional[str] = None):
    """
    Return scored rows and observed outcomes to support frontend uplift/Qini charts.
    This endpoint supplies data; it does not claim that a Qini score has been validated.
    """
    resolved_id, df = load_dataset(dataset_id)
    required = ["segment", "conversion"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail={"missing_columns": missing})

    model, features, preprocessor, metadata = load_model()
    validate_model_dataset(resolved_id, features, metadata, df)
    missing_features = [col for col in features if col not in df.columns]
    if missing_features:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing model features.",
                "missing_features": missing_features,
            },
        )

    selected = prepare_hillstrom_comparison(df)
    selected["conversion"] = pd.to_numeric(selected["conversion"], errors="coerce")
    selected = selected.dropna(subset=["conversion"])
    X = encode_model_features(selected[features])

    try:
        if preprocessor is not None:
            X = preprocessor.transform(X)
        effects = np.asarray(model.effect(X, T0=0, T1=1)).reshape(-1)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not score rows for uplift analysis: {exc}"
        )

    result = pd.DataFrame(
        {
            "row_id": selected.index.astype(str),
            "treatment": selected["email_treatment"].astype(int).values,
            "outcome": selected["conversion"].astype(float).values,
            "ite": effects,
        }
    ).sort_values("ite", ascending=False)

    result["population_fraction"] = np.arange(1, len(result) + 1) / max(len(result), 1)
    return {
        "dataset_id": resolved_id,
        "rows": json_records(result),
        "note": (
            "Use this scored data to calculate uplift/Qini metrics with a validated "
            "method. Do not evaluate causal uplift on the same data used to fit the model."
        ),
    }


@app.post("/api/allocation/optimize")
def optimize_budget_allocation(request: AllocationRequest):
    """Optimize binary email-intervention assignment under the requested budget."""
    if (request.intervention_cost is None) == (
        request.intervention_cost_column is None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Provide exactly one of intervention_cost or "
                "intervention_cost_column."
            ),
        )

    resolved_id, df = load_dataset(request.dataset_id)
    model, features, preprocessor, metadata = load_model()
    validate_model_dataset(resolved_id, features, metadata, df)
    missing_features = [column for column in features if column not in df.columns]
    if missing_features:
        raise HTTPException(
            status_code=422,
            detail={"message": "Dataset is missing model features.", "missing_features": missing_features},
        )
    if request.customer_id_column and request.customer_id_column not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown customer ID column '{request.customer_id_column}'.",
        )
    if request.customer_id_column and (
        df[request.customer_id_column].isna().any()
        or df[request.customer_id_column].duplicated().any()
    ):
        raise HTTPException(
            status_code=422,
            detail="Customer ID values must be non-empty and unique.",
        )
    if request.segment_column and request.segment_column not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown segment column '{request.segment_column}'.",
        )
    if (
        request.intervention_cost_column
        and request.intervention_cost_column not in df.columns
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Unknown intervention cost column '{request.intervention_cost_column}'.",
        )

    selected = prepare_hillstrom_comparison(df)
    scoring_features = selected[features]
    try:
        transformed = (
            preprocessor.transform(scoring_features)
            if preprocessor is not None
            else scoring_features
        )
        effects = np.asarray(model.effect(transformed, T0=0, T1=1), dtype=float).reshape(-1)
        if len(effects) != len(selected) or not np.isfinite(effects).all():
            raise ValueError("The model returned invalid treatment-effect estimates.")
    except Exception as exc:
        logger.exception("Could not score customers for allocation")
        raise HTTPException(
            status_code=422,
            detail=f"Could not score customers for allocation: {exc}",
        ) from exc

    if request.intervention_cost_column:
        costs = pd.to_numeric(
            selected[request.intervention_cost_column], errors="coerce"
        ).to_numpy(dtype=float)
    else:
        costs = np.full(len(selected), request.intervention_cost, dtype=float)

    customer_ids = (
        selected[request.customer_id_column].astype(str).to_numpy()
        if request.customer_id_column
        else selected.index.astype(str).to_numpy()
    )
    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "ite": effects,
        }
    )
    if request.segment_column:
        customers["segment"] = selected[request.segment_column].fillna(
            "(missing)"
        ).astype(str).to_numpy()
    try:
        optimized = optimize_allocation(
            customers,
            request.budget,
            costs,
            max_customers=request.max_customers,
            min_customers=request.min_customers,
            segment_column="segment" if request.segment_column else None,
            segment_limits={
                segment: limit.model_dump()
                for segment, limit in request.segment_limits.items()
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("SciPy customer-allocation optimization failed")
        raise HTTPException(
            status_code=503, detail=f"Customer-allocation solver failed: {exc}"
        ) from exc

    result_rows = optimized["customers"].rename(
        columns={"ite": "predicted_ite"}
    ).sort_values("predicted_ite", ascending=False, kind="stable")
    allocation_id = str(uuid4())
    csv_path = ALLOCATION_DIR / f"{allocation_id}.csv"
    metadata_path = ALLOCATION_DIR / f"{allocation_id}.json"
    result_rows.to_csv(csv_path, index=False)
    segment_summaries = []
    if "segment" in result_rows:
        for segment, group in result_rows.groupby("segment", dropna=False):
            segment_summaries.append(
                {
                    "segment": str(segment),
                    "customers_evaluated": int(len(group)),
                    "customers_selected": int(group["selected"].sum()),
                    "allocated_budget": float(group.loc[group["selected"], "intervention_cost"].sum()),
                    "expected_incremental_conversions": float(
                        group.loc[group["selected"], "expected_incremental_benefit"].sum()
                    ),
                }
            )
    summary = {
        **optimized["summary"],
        "intervention_cost_model": (
            "dataset column"
            if request.intervention_cost_column
            else "fixed per-customer cost"
        ),
        "segment_summaries": segment_summaries,
    }
    metadata_payload = {
        "allocation_id": allocation_id,
        "dataset_id": resolved_id,
        "model_id": active_model_path().stem,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "total_customers": int(len(result_rows)),
    }
    metadata_path.write_text(
        json.dumps(jsonable_encoder(metadata_payload), allow_nan=False),
        encoding="utf-8",
    )
    return {
        **metadata_payload,
        "offset": 0,
        "limit": min(100, len(result_rows)),
        "customers": json_records(result_rows.head(100)),
        "objective_label": "Expected incremental conversions, not profit.",
        "warning": (
            "Treatment effects are estimates for Womens E-Mail versus No E-Mail. "
            "Intervention costs do not imply discount or revenue effects."
        ),
    }


@app.get("/api/allocation/{allocation_id}")
def get_allocation_result(
    allocation_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    selected_only: bool = False,
    query: str | None = None,
    segment: str | None = None,
    sort_by: str = "predicted_ite",
    sort_direction: str = "desc",
):
    try:
        canonical_id = str(UUID(allocation_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid allocation ID.") from exc
    csv_path = ALLOCATION_DIR / f"{canonical_id}.csv"
    metadata_path = ALLOCATION_DIR / f"{canonical_id}.json"
    if not csv_path.is_file() or not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Allocation result not found.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = pd.read_csv(csv_path)
    if selected_only:
        rows = rows.loc[rows["selected"].astype(bool)]
    if segment:
        if "segment" not in rows:
            raise HTTPException(
                status_code=422, detail="This allocation has no segment information."
            )
        rows = rows.loc[rows["segment"].astype(str).eq(segment)]
    if query:
        rows = rows.loc[
            rows["customer_id"].astype(str).str.contains(query, case=False, regex=False)
        ]
    sortable_columns = {
        "customer_id",
        "segment",
        "predicted_ite",
        "expected_incremental_benefit",
        "intervention_cost",
        "selected",
    }
    if sort_by not in sortable_columns or sort_by not in rows:
        raise HTTPException(status_code=422, detail="Invalid allocation sort column.")
    if sort_direction not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Sort direction must be asc or desc.")
    rows = rows.sort_values(
        sort_by, ascending=sort_direction == "asc", kind="stable"
    )
    total = len(rows)
    page = rows.iloc[offset : offset + limit]
    return {
        **metadata,
        "offset": offset,
        "limit": limit,
        "total_customers": total,
        "customers": json_records(page),
    }


@app.get("/api/allocation/{allocation_id}/export")
def export_allocation_csv(allocation_id: str):
    try:
        canonical_id = str(UUID(allocation_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid allocation ID.") from exc
    csv_path = ALLOCATION_DIR / f"{canonical_id}.csv"
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail="Allocation result not found.")
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"econocausal-allocation-{canonical_id}.csv",
    )


@app.post("/api/archive-campaign/train")
def train_archive_campaign():
    """Train and audit a household-level model on the local campaign archive."""
    try:
        result = train_archive_campaign_model()
        return {
            "report": result["report"],
            "scores_total": len(result["scores"]),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
