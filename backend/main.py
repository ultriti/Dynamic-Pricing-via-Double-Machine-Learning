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



# ---------------------------
# Paths and application setup

BASE_DIR = Path(__file__).resolve().parent

print("path :",BASE_DIR)


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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hillstrom columns expected for the complete dataset.
HILLSTROM_COLUMNS = [
    "recency",
    "history_segment",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
    "segment",
    "visit",
    "conversion",
    "spend",
]

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

# These category codes were verified against the persisted X.pkl training matrix.
MODEL_CATEGORY_CODES = {
    "zip_code": {
        "rural": 0,
        "surburban": 1,
        "suburban": 1,
        "urban": 2,
    },
    "channel": {
        "multichannel": 0,
        "phone": 1,
        "web": 2,
    },
}

# --------------------------
# load dataset 


def load_dataset(
    dataset_id: str | None = None,
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

def load_model():
    """Load a trusted model bundle or estimator from the configured file."""
    if not MODEL_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Saved model not found at: {MODEL_PATH}",
        )
    try:
        saved = joblib.load(MODEL_PATH)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load model: {exc}")

    # Preferred format: a dictionary with model and training metadata.
    if isinstance(saved, dict) and "model" in saved:
        model = saved["model"]
        features = saved.get("feature_columns", DEFAULT_FEATURE_COLUMNS)
        preprocessor = saved.get("preprocessor")
        metadata = saved
    else:
        # Supports a directly saved estimator, but cannot infer its preprocessing.
        model = saved
        features = DEFAULT_FEATURE_COLUMNS
        preprocessor = None
        metadata = {}

    return model, list(features), preprocessor, metadata


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
    """Apply the category codes used to build the saved model's training matrix."""
    encoded = features.copy()

    for column, category_codes in MODEL_CATEGORY_CODES.items():
        if column not in encoded.columns:
            continue

        numeric_values = pd.to_numeric(encoded[column], errors="coerce")
        normalized_labels = encoded[column].astype("string").str.strip().str.casefold()
        category_values = normalized_labels.map(category_codes)
        encoded[column] = numeric_values.where(numeric_values.notna(), category_values)

    for column in encoded.columns:
        encoded[column] = pd.to_numeric(encoded[column], errors="coerce")

    invalid_columns = {
        column: {
            "rows": encoded.loc[encoded[column].isna()].index.tolist()[:5],
            "values": features.loc[encoded[column].isna(), column]
            .astype(str)
            .unique()
            .tolist()[:5],
        }
        for column in encoded.columns
        if encoded[column].isna().any()
    }
    if invalid_columns:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Model features contain missing or unsupported values after "
                    "applying the training category codes."
                ),
                "invalid_features": invalid_columns,
                "supported_categories": {
                    column: sorted(category_codes)
                    for column, category_codes in MODEL_CATEGORY_CODES.items()
                    if column in invalid_columns
                },
            },
        )

    return encoded


# ---------------------------
# Basic endpoints
# ---------------------------


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


@app.get("/api/dataset/summary")
def dataset_summary(dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)
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
    return {"dataset_id": dataset_id, "stats": jsonable_encoder(stats.to_dict())}


@app.get("/api/dataset/value-counts/{column}")
def dataset_value_counts(column: str, dataset_id: str | None = None):
    dataset_id, df = load_dataset(dataset_id)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found.")
    counts = df[column].value_counts(dropna=False)
    return {
        "dataset_id": dataset_id,
        "column": column,
        "counts": {
            str(key) if pd.notna(key) else "(Missing)": int(value)
            for key, value in counts.items()
        },
    }


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
    return {
        "dataset_id": dataset_id,
        "column": column,
        "type": "categorical",
        "labels": counts.index.tolist(),
        "values": counts.astype(int).tolist(),
    }


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
    return {
        "treatment": "email_treatment (Womens E-Mail=1, No E-Mail=0)",
        "outcome": "conversion",
        "confounders": DEFAULT_FEATURE_COLUMNS,
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
# Week 2: saved model and ITE inference
# ---------------------------


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
