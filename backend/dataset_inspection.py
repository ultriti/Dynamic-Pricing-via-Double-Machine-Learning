from pathlib import Path

import pandas as pd


def inspect_uploaded_dataset(
    path: Path,
    dataset_id: str,
    causal_required_columns: list[str],
    hillstrom_required_columns: list[str],
) -> dict:
    frame = pd.read_csv(path)
    frame.columns = frame.columns.astype(str).str.strip()
    columns = frame.columns.tolist()
    missing_causal_columns = [
        column for column in causal_required_columns if column not in columns
    ]
    missing_hillstrom_columns = [
        column for column in hillstrom_required_columns if column not in columns
    ]
    column_details = [
        {
            "name": column,
            "dtype": str(frame[column].dtype),
            "missing_values": int(frame[column].isna().sum()),
            "unique_values": int(frame[column].nunique(dropna=True)),
        }
        for column in columns
    ]
    preview = frame.head(10).astype(object).where(pd.notna(frame.head(10)), None)

    return {
        "dataset_id": dataset_id,
        "filename": path.name,
        "rows": int(len(frame)),
        "columns": columns,
        "missing_values": int(frame.isna().sum().sum()),
        "causal_compatibility": {
            "compatible": not missing_causal_columns,
            "missing_columns": missing_causal_columns,
            "required_columns": causal_required_columns,
        },
        "hillstrom_compatibility": {
            "compatible": not missing_hillstrom_columns,
            "missing_columns": missing_hillstrom_columns,
            "required_columns": hillstrom_required_columns,
        },
        "column_details": column_details,
        "preview": preview.to_dict(orient="records"),
    }
