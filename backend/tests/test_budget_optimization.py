import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import importlib

from backend.budget_optimization import optimize_allocation


def test_optimizer_selects_best_binary_allocation_without_exceeding_budget():
    customers = pd.DataFrame(
        {
            "customer_id": ["a", "b", "c"],
            "ite": [0.2, 0.1, 0.35],
        }
    )

    result = optimize_allocation(
        customers,
        budget=20,
        intervention_costs=np.array([10, 10, 20]),
    )

    rows = result["customers"]
    assert rows.loc[rows["selected"], "customer_id"].tolist() == ["c"]
    assert result["summary"]["allocated_budget"] == 20
    assert result["summary"]["remaining_budget"] == 0
    assert result["summary"]["expected_incremental_conversions"] == pytest.approx(0.35)


def test_optimizer_obeys_customer_and_segment_constraints():
    customers = pd.DataFrame(
        {
            "customer_id": ["a", "b", "c", "d"],
            "ite": [0.5, 0.4, 0.3, 0.2],
            "segment": ["A", "A", "B", "B"],
        }
    )

    result = optimize_allocation(
        customers,
        budget=30,
        intervention_costs=np.repeat(10, 4),
        max_customers=3,
        min_customers=2,
        segment_column="segment",
        segment_limits={"A": {"min_customers": 1, "max_customers": 1}},
    )

    chosen = result["customers"].loc[result["customers"]["selected"]]
    assert len(chosen) == 3
    assert chosen["segment"].value_counts().to_dict() == {"A": 1, "B": 2}
    assert result["summary"]["allocated_budget"] <= 30


@pytest.mark.parametrize(
    ("budget", "costs", "message"),
    [
        (0, np.array([1.0]), "Budget"),
        (10, np.array([0.0]), "Intervention costs"),
        (10, np.array([np.nan]), "Intervention costs"),
    ],
)
def test_optimizer_rejects_invalid_budget_and_costs(budget, costs, message):
    with pytest.raises(ValueError, match=message):
        optimize_allocation(
            pd.DataFrame({"ite": [0.2]}), budget, costs
        )


def test_optimizer_reports_infeasible_minimum_allocation():
    with pytest.raises(ValueError, match="infeasible"):
        optimize_allocation(
            pd.DataFrame({"ite": [0.2, 0.1]}),
            budget=5,
            intervention_costs=np.array([10.0, 10.0]),
            min_customers=1,
        )


def test_optimizer_rejects_empty_customer_population():
    with pytest.raises(ValueError, match="No eligible customers"):
        optimize_allocation(pd.DataFrame({"ite": []}), 10, np.array([]))


def test_allocation_api_saves_retrievable_results_and_csv(tmp_path, monkeypatch):
    backend_path = str(Path(__file__).resolve().parents[1])
    monkeypatch.syspath_prepend(backend_path)
    main = importlib.import_module("main")

    frame = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3", "c4"],
            "recency": [4, 3, 2, 1],
            "history_segment": ["A", "A", "B", "B"],
            "history": [40, 30, 20, 10],
            "mens": [0, 0, 0, 0],
            "womens": [1, 1, 1, 1],
            "zip_code": ["Urban", "Urban", "Rural", "Rural"],
            "newbie": [1, 1, 0, 0],
            "channel": ["Web", "Web", "Phone", "Phone"],
            "segment": ["Womens E-Mail", "No E-Mail", "Womens E-Mail", "No E-Mail"],
        }
    )

    class FakeModel:
        def effect(self, features, T0, T1):
            return features["recency"].to_numpy(dtype=float) / 10

    dataset_id = "allocation-test"
    monkeypatch.setattr(main, "load_dataset", lambda _: (dataset_id, frame))
    monkeypatch.setattr(
        main,
        "load_model",
        lambda: (
            FakeModel(),
            main.DEFAULT_FEATURE_COLUMNS,
            None,
            {
                "dataset_id": dataset_id,
                "feature_columns": main.DEFAULT_FEATURE_COLUMNS,
                "feature_schema": {
                    column: str(frame[column].dtype)
                    for column in main.DEFAULT_FEATURE_COLUMNS
                },
                "outcome": "conversion",
                "treatment_definition": "Womens E-Mail (T=1) vs No E-Mail (T=0)",
            },
        ),
    )
    allocation_dir = tmp_path / "allocations"
    allocation_dir.mkdir()
    monkeypatch.setattr(main, "ALLOCATION_DIR", allocation_dir)
    monkeypatch.setattr(main, "active_model_path", lambda: tmp_path / "model.joblib")
    client = TestClient(main.app)

    optimized = client.post(
        "/api/allocation/optimize",
        json={
            "dataset_id": dataset_id,
            "budget": 10,
            "intervention_cost": 10,
            "max_customers": 1,
            "customer_id_column": "customer_id",
            "segment_column": "history_segment",
        },
    )

    assert optimized.status_code == 200
    response = optimized.json()
    assert response["summary"]["allocated_budget"] <= 10
    assert response["summary"]["customers_selected"] == 1
    allocation_id = response["allocation_id"]
    selected_rows = client.get(
        f"/api/allocation/{allocation_id}",
        params={"selected_only": True, "limit": 10},
    )
    csv = client.get(f"/api/allocation/{allocation_id}/export")

    assert selected_rows.status_code == 200
    assert selected_rows.json()["total_customers"] == 1
    assert selected_rows.json()["customers"][0]["customer_id"] == "c1"
    assert csv.status_code == 200
    assert "customer_id" in csv.text

    monkeypatch.setattr(
        main,
        "load_model",
        lambda: (
            FakeModel(),
            main.DEFAULT_FEATURE_COLUMNS,
            None,
            {
                "dataset_id": "different-dataset",
                "feature_columns": main.DEFAULT_FEATURE_COLUMNS,
                "feature_schema": {
                    column: str(frame[column].dtype)
                    for column in main.DEFAULT_FEATURE_COLUMNS
                },
                "outcome": "conversion",
                "treatment_definition": "Womens E-Mail (T=1) vs No E-Mail (T=0)",
            },
        ),
    )
    incompatible = client.post(
        "/api/allocation/optimize",
        json={
            "dataset_id": dataset_id,
            "budget": 10,
            "intervention_cost": 10,
        },
    )
    assert incompatible.status_code == 409


def test_training_endpoint_persists_versioned_model_metadata(tmp_path, monkeypatch):
    backend_path = str(Path(__file__).resolve().parents[1])
    monkeypatch.syspath_prepend(backend_path)
    main = importlib.import_module("main")
    frame = pd.DataFrame(
        {
            **{feature: [1, 2] for feature in main.DEFAULT_FEATURE_COLUMNS},
            "segment": ["Womens E-Mail", "No E-Mail"],
            "conversion": [1, 0],
        }
    )
    dataset_id = "version-test"

    monkeypatch.setattr(main, "load_dataset", lambda _: (dataset_id, frame))
    monkeypatch.setattr(main, "MODEL_VERSIONS_DIR", tmp_path / "versions")
    monkeypatch.setattr(
        main,
        "train_dml_analysis",
        lambda *_: {
            "_model": {"estimator": "test"},
            "_preprocessor": {"transformer": "test"},
            "_feature_columns": main.DEFAULT_FEATURE_COLUMNS,
            "customers": [],
            "estimator": "EconML CausalForestDML",
            "treatment": "Womens E-Mail (T=1) vs No E-Mail (T=0)",
            "outcome": "conversion",
            "qini_coefficient": 0.1,
            "holdout_customers": 1,
            "treatment_propensity": 0.5,
        },
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/causal/train", params={"dataset_id": dataset_id}
    )

    assert response.status_code == 200
    result = response.json()
    model_path = tmp_path / "versions" / f"{result['model_id']}.joblib"
    metadata_path = model_path.with_suffix(".json")
    assert model_path.is_file()
    assert metadata_path.is_file()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["dataset_id"] == dataset_id
    assert metadata["feature_columns"] == main.DEFAULT_FEATURE_COLUMNS
    assert client.get("/api/model/list").json()["total"] == 1
