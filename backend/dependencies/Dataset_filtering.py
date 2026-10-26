from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
from utils.general_helper import json_records, safe_dataset_id, dataset_path

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
            columns = set(pd.read_csv(path, nrows=0).columns.astype(str).str.strip())

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


# ---------------------
# load model ( pretrained model )
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
