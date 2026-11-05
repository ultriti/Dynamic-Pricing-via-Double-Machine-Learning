import numpy as np
import pandas as pd
import networkx as nx

from backend.causal_engine_exp import (
    _dowhy_refutation_audit,
    _uplift_evaluation,
    train_dml_analysis,
)
from backend.dowhy_compat import load_causal_model


def test_dowhy_identification_supports_networkx_without_legacy_api(monkeypatch):
    monkeypatch.delattr(nx.algorithms, "d_separated", raising=False)
    data = pd.DataFrame(
        {
            "confounder": [0, 1, 0, 1],
            "treatment": [0, 0, 1, 1],
            "outcome": [0, 1, 0, 1],
        }
    )
    model = load_causal_model()(
        data=data,
        treatment="treatment",
        outcome="outcome",
        graph=(
            "digraph { confounder -> treatment; confounder -> outcome; "
            "treatment -> outcome; }"
        ),
    )

    assert model.identify_effect() is not None


def test_uplift_evaluation_returns_random_baseline_and_deciles():
    treatment = np.array([1, 0] * 20)
    outcome = np.array([1, 0, 0, 0] * 10)
    effects = np.linspace(1, -1, len(treatment))

    result = _uplift_evaluation(treatment, outcome, effects)

    assert result["qini_curve"][0]["population_fraction"] == 0
    assert result["qini_curve"][0]["strategy_gain"] == 0
    assert result["qini_curve"][-1]["population_fraction"] == 1
    assert result["qini_curve"][-1]["strategy_gain"] == result["qini_curve"][-1]["random_gain"]
    assert result["qini_curve"][0]["strategy_gain_lower"] <= 0
    assert result["qini_curve"][0]["strategy_gain_upper"] >= 0
    assert result["qini_bootstrap_samples"] == 200
    assert len(result["uplift_by_decile"]) == 10
    assert result["evaluation_customers"] == len(treatment)
    assert result["evaluation_method"].startswith("Stratified 3-fold")


def test_dowhy_estimation_failure_is_reported_in_audit(monkeypatch):
    class BrokenCausalModel:
        def __init__(self, **_kwargs):
            pass

        def identify_effect(self):
            return object()

        def estimate_effect(self, *_args, **_kwargs):
            raise KeyError(0)

    monkeypatch.setattr(
        "backend.dowhy_compat.load_causal_model",
        lambda: BrokenCausalModel,
    )

    result = _dowhy_refutation_audit(
        np.array([[0.0], [1.0], [2.0], [3.0]]),
        ["feature_0"],
        np.array([0, 0, 1, 1]),
        np.array([0, 1, 0, 1]),
    )

    assert result["backdoor_effect"] is None
    assert len(result["refutations"]) == 3
    assert all(item["status"] == "error" for item in result["refutations"])
    assert all("KeyError: 0" in item["message"] for item in result["refutations"])
    assert "out-of-fold evaluation completed" in result["interpretation"]


def test_train_dml_analysis_returns_oof_evaluation_and_effect_intervals():
    rng = np.random.default_rng(42)
    row_count = 300
    treatment = rng.integers(0, 2, size=row_count)
    newbie = rng.integers(0, 2, size=row_count)
    conversion_probability = 0.1 + 0.55 * treatment * newbie
    conversion = rng.binomial(1, conversion_probability)
    frame = pd.DataFrame(
        {
            "recency": rng.integers(1, 13, size=row_count),
            "history_segment": rng.choice(["A", "B", "C"], size=row_count),
            "history": rng.uniform(0, 1000, size=row_count),
            "mens": rng.integers(0, 2, size=row_count),
            "womens": rng.integers(0, 2, size=row_count),
            "zip_code": rng.choice(["Urban", "Rural"], size=row_count),
            "newbie": newbie,
            "channel": rng.choice(["Web", "Phone"], size=row_count),
            "segment": np.where(treatment, "Womens E-Mail", "No E-Mail"),
            "conversion": conversion,
        }
    )

    result = train_dml_analysis(
        frame,
        [
            "recency",
            "history_segment",
            "history",
            "mens",
            "womens",
            "zip_code",
            "newbie",
            "channel",
        ],
    )

    assert result["estimator"] == "EconML CausalForestDML"
    assert result["evaluation_customers"] == row_count
    assert result["customers_scored"] == row_count
    assert result["customer_rows_returned"] == row_count
    assert len(result["customers"]) == row_count
    assert all(np.isfinite(customer["ite"]) for customer in result["customers"])
    assert all(
        customer["ite_lower_90"] <= customer["ite"] <= customer["ite_upper_90"]
        for customer in result["customers"]
    )
    assert result["rct_benchmark"]["ci_90_lower"] < result["rct_benchmark"]["ci_90_upper"]
    assert len(result["covariate_balance"]) == 8
    assert len(result["causal_audit"]["refutations"]) == 3
    assert result["qini_curve"][0]["strategy_gain"] == 0
