from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"


# ---------------------------
# General helper functions


def json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert missing values to JSON nulls."""
    safe = df.astype(object).where(pd.notna(df), None)
    return jsonable_encoder(safe.to_dict(orient="records"))


def safe_dataset_id(dataset_id: str) -> str:
    if not isinstance(dataset_id, str):
        raise HTTPException(status_code=400, detail="Invalid dataset ID.")

    try:
        parsed_id = UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID.") from None

    if str(parsed_id) != dataset_id:
        raise HTTPException(status_code=400, detail="Invalid dataset ID.")

    return dataset_id


def dataset_path(dataset_id: str) -> Path:
    path = UPLOAD_DIR / f"{safe_dataset_id(dataset_id)}.csv"
    if path.is_symlink() or not path.is_file():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return path
