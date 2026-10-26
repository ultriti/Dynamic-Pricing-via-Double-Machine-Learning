import numpy as np
import pandas as pd

from backend.causal_engine import _uplift_evaluation, train_dml_analysis


def test_uplift_evaluation_returns_random_baseline_and_deciles():
    treatment = np.array([1, 0] * 20)
    outcome = np.array([1, 0, 0, 0] * 10)
    effects = np.linspace(1, -1, len(treatment))

    result = _uplift_evaluation(treatment, outcome, effects)

    assert result["qini_curve"][0]["population_fraction"] == 0
    assert result["qini_curve"][0]["strategy_gain"] == 0
    assert result["qini_curve"][-1]["population_fraction"] == 1
    assert result["qini_curve"][-1]["strategy_gain"] == result["qini_curve"][-1]["random_gain"]
    assert len(result["uplift_by_decile"]) == 10
    assert result["holdout_customers"] == len(treatment)


def test_train_dml_analysis_returns_held_out_customer_effects():
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
    assert result["holdout_customers"] == 90
    assert result["customers_scored"] == row_count
    assert result["customer_rows_returned"] == row_count
    assert len(result["customers"]) == row_count
    assert all(np.isfinite(customer["ite"]) for customer in result["customers"])
    assert result["qini_curve"][0]["strategy_gain"] == 0
