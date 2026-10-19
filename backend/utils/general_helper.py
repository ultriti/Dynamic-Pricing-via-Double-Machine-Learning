from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
import pandas as pd
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
MODEL_PATH = BASE_DIR / "models" / "conversion_causal_forest_v1.joblib"
RAW_HILLSTROM_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


# ---------------------------
# General helper functions


def json_records(df: pd.DataFrame) -> list[dict]:
    """Convert missing values to JSON nulls."""
    safe = df.astype(object).where(pd.notna(df), None)
    return jsonable_encoder(safe.to_dict(orient="records"))


def safe_dataset_id(dataset_id: str) -> str:
    if not re.fullmatch(r"[a-f0-9-]{36}", dataset_id):
        raise HTTPException(status_code=400, detail="Invalid dataset ID.")
    return dataset_id


def dataset_path(dataset_id: str) -> Path:
    path = UPLOAD_DIR / f"{safe_dataset_id(dataset_id)}.csv"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return path
