import importlib
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.dataset_inspection import inspect_uploaded_dataset


def test_inspection_previews_selected_dataset_and_reports_missing_causal_columns(
    tmp_path,
):
    path = tmp_path / "uploaded.csv"
    pd.DataFrame(
        [
            {"customer_id": "a", "purchase": 1},
            {"customer_id": "b", "purchase": None},
        ]
    ).to_csv(path, index=False)

    details = inspect_uploaded_dataset(
        path,
        "selected-dataset",
        causal_required_columns=["segment", "conversion"],
        hillstrom_required_columns=["segment", "conversion", "recency"],
    )

    assert details["dataset_id"] == "selected-dataset"
    assert details["rows"] == 2
    assert details["columns"] == ["customer_id", "purchase"]
    assert details["missing_values"] == 1
    assert details["preview"][0] == {"customer_id": "a", "purchase": 1}
    assert details["causal_compatibility"] == {
        "compatible": False,
        "missing_columns": ["segment", "conversion"],
        "required_columns": ["segment", "conversion"],
    }
    assert details["hillstrom_compatibility"]["missing_columns"] == [
        "segment",
        "conversion",
        "recency",
    ]


def test_inspection_marks_hillstrom_causal_schema_compatible(tmp_path):
    path = tmp_path / "hillstrom.csv"
    columns = ["recency", "segment", "conversion"]
    pd.DataFrame([["1", "Womens E-Mail", 1]], columns=columns).to_csv(
        path, index=False
    )

    details = inspect_uploaded_dataset(
        path,
        "selected-dataset",
        causal_required_columns=columns,
        hillstrom_required_columns=columns,
    )

    assert details["causal_compatibility"]["compatible"] is True
    assert details["hillstrom_compatibility"]["compatible"] is True


def test_inspection_api_uses_requested_dataset_and_causal_training_requires_id(
    tmp_path, monkeypatch
):
    backend_path = str(Path(__file__).resolve().parents[1])
    monkeypatch.syspath_prepend(backend_path)
    main = importlib.import_module("main")
    selected_path = tmp_path / "selected.csv"
    pd.DataFrame([{"customer_id": "selected-row", "purchase": 1}]).to_csv(
        selected_path, index=False
    )
    monkeypatch.setattr(main, "dataset_path", lambda _: selected_path)
    client = TestClient(main.app)

    response = client.get(
        "/api/dataset/inspect", params={"dataset_id": "selected-dataset"}
    )
    missing_id_response = client.post("/api/causal/train")

    assert response.status_code == 200
    assert response.json()["dataset_id"] == "selected-dataset"
    assert response.json()["preview"][0]["customer_id"] == "selected-row"
    assert response.json()["causal_compatibility"]["compatible"] is False
    assert missing_id_response.status_code == 422
