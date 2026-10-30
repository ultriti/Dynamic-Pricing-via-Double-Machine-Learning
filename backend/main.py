from io import BytesIO
from pathlib import Path
from uuid import uuid4
import re

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder

# ----------------------------- import
from utils.general_helper import json_records, safe_dataset_id, dataset_path
from causal_engine_exp import train_dml_analysis
from dependencies.Dataset_filtering import (
    load_dataset,
    check_hillstrom_schema,
    prepare_hillstrom_comparison,
    encode_model_features,
    prepare_hillstrom_comparison,
    load_model
)

# ---------------------------
# Paths and application setup

BASE_DIR = Path(__file__).resolve().parent

print("path :", BASE_DIR)


UPLOAD_DIR = BASE_DIR / "data" / "uploads"
MODEL_PATH = BASE_DIR / "models" / "conversion_causal_forest_v1.joblib"
RAW_HILLSTROM_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="EconoCausal API",
    description="Hillstrom dataset exploration and causal-effect analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):517\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ---------------------------
# Basic endpoints
@app.get("/")
def home():
    return {
        "message": "EconoCausal API is running",
        "docs": "/docs",
        "model_file": MODEL_PATH.name,
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


@app.get("/api/dataset/preview")
def dataset_preview(dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)
    return {
        "dataset_id": dataset_id,
        "rows": len(df),
        "columns": df.columns.tolist(),
        "data": json_records(df.head(10)),
    }


# -----------------------------------
# csv file summary
@app.get("/api/dataset/summary")
def dataset_summary(dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)

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
def dataset_columns(dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)
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
def dataset_value_counts(column: str, dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)
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
def dataset_correlation(dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)
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
    dataset_id: str | None = None,
    bins: int = Query(default=20, ge=1, le=100),
):
    dataset_id, df = load_dataset(dataset_id)
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
    dataset_id: str | None = None,
    sample: int = Query(default=500, ge=1, le=5000),
):
    dataset_id, df = load_dataset(dataset_id)
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
def identify_causal_effect(dataset_id: str | None = None):
    """Use DoWhy to identify an average effect for Womens E-Mail vs No E-Mail."""
    try:
        from dowhy import CausalModel
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
            "identified_estimand": str(estimand),
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
def train_causal_model(dataset_id: str | None = None):
    """Fit an EconML DML causal forest and evaluate uplift on held-out customers."""
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
            detail=f"DML training or held-out evaluation failed: {exc}",
        ) from exc

    return {
        "dataset_id": resolved_id,
        **result,
    }


@app.get("/api/model/status")
def model_status():
    return {
        "model_id": MODEL_PATH.stem,
        "model_file": str(MODEL_PATH),
        "exists": MODEL_PATH.is_file(),
    }


@app.get("/api/model/info")
def model_info():
    model, features, preprocessor, metadata = load_model()
    return {
        "model_id": MODEL_PATH.stem,
        "model_class": type(model).__name__,
        "feature_columns": features,
        "has_preprocessor": preprocessor is not None,
        "outcome": metadata.get(
            "outcome", "conversion (expected; verify training metadata)"
        ),
        "treatment_definition": metadata.get(
            "treatment_definition",
            "Expected: Womens E-Mail (T=1) vs No E-Mail (T=0); verify training code.",
        ),
        "metadata_available": bool(metadata),
    }


@app.get("/api/model/ite")
def model_ite(dataset_id: str | None = None):
    """Estimate ITEs for uploaded data using the saved model."""
    resolved_id, df = load_dataset(dataset_id)
    model, features, preprocessor, metadata = load_model()

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
        "model_id": MODEL_PATH.stem,
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
def uplift_data(dataset_id: str | None = None):
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
