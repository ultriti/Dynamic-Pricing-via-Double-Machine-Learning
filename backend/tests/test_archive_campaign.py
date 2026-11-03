import numpy as np
import pandas as pd

from backend.archive_campaign import (
    _propensity_matching,
    _unobserved_confounder_sensitivity,
    _uplift_evaluation,
    prepare_archive_cohort,
)


def test_prepare_archive_cohort_excludes_overlapping_campaign_households(tmp_path):
    pd.DataFrame(
        [
            {"CAMPAIGN": 18, "DESCRIPTION": "TypeA", "START_DAY": 10, "END_DAY": 20},
            {"CAMPAIGN": 19, "DESCRIPTION": "TypeB", "START_DAY": 15, "END_DAY": 25},
            {"CAMPAIGN": 17, "DESCRIPTION": "TypeB", "START_DAY": 1, "END_DAY": 8},
        ]
    ).to_csv(tmp_path / "campaign_desc.csv", index=False)
    assignments = [
        {"household_key": household, "CAMPAIGN": 18, "DESCRIPTION": "TypeA"}
        for household in range(1, 51)
    ]
    assignments.extend(
        [
            {"household_key": 1, "CAMPAIGN": 19, "DESCRIPTION": "TypeB"},
            {"household_key": 2, "CAMPAIGN": 17, "DESCRIPTION": "TypeB"},
            {"household_key": 51, "CAMPAIGN": 19, "DESCRIPTION": "TypeB"},
        ]
    )
    pd.DataFrame(assignments).to_csv(tmp_path / "campaign_table.csv", index=False)
    pd.DataFrame(
        [
            {"household_key": household, "AGE_DESC": "45-54"}
            for household in range(1, 101)
        ]
    ).to_csv(tmp_path / "hh_demographic.csv", index=False)
    pd.DataFrame(
        [
            {
                "household_key": household,
                "BASKET_ID": household * 100 + day,
                "DAY": day,
                "QUANTITY": 1,
                "SALES_VALUE": 10,
                "RETAIL_DISC": 0,
                "COUPON_DISC": 0,
                "COUPON_MATCH_DISC": 0,
            }
            for household in range(1, 101)
            for day in [9, 12]
        ]
    ).to_csv(tmp_path / "transaction_data.csv", index=False)

    cohort, metadata = prepare_archive_cohort(tmp_path)

    assert cohort["household_key"].tolist() == [*range(2, 51), *range(52, 101)]
    assert cohort["treatment"].value_counts().to_dict() == {1: 49, 0: 49}
    assert (cohort["campaign_sales"] == 10).all()
    assert metadata["overlapping_campaign_ids_excluded"] == [19]
    assert metadata["excluded_households_with_concurrent_campaigns"] == 2
    assert metadata["discount_treatment_available"] is False


def test_uplift_evaluation_returns_finite_curve_and_random_baseline():
    treatment = np.array([1, 0] * 20)
    outcome = np.linspace(0, 39, 40)
    effects = np.linspace(1, -1, 40)

    result = _uplift_evaluation(treatment, outcome, effects)

    assert result["heldout_households"] == len(treatment)
    assert result["uplift_curve"][0]["population_fraction"] == 0
    assert result["uplift_curve"][0]["strategy_gain"] == 0
    assert result["uplift_curve"][-1]["population_fraction"] == 1
    assert result["uplift_curve"][-1]["strategy_gain"] == result["uplift_curve"][-1]["random_gain"]
    assert len(result["uplift_by_decile"]) == 10


def test_propensity_matching_pairs_unique_controls_and_reports_balance():
    rng = np.random.default_rng(42)
    feature = rng.normal(size=400)
    treatment = rng.binomial(1, 1 / (1 + np.exp(-feature)))
    outcome = 2 * feature + rng.normal(size=len(feature))

    result = _propensity_matching(feature[:, None], treatment, outcome)

    assert result["treated_matched"] >= 20
    assert result["unique_controls_matched"] == result["treated_matched"]
    assert result["max_abs_smd_after"] < result["max_abs_smd_before"]


def test_unobserved_confounder_sensitivity_reports_partial_r2_bounds():
    rng = np.random.default_rng(7)
    feature = rng.normal(size=300)
    treatment = rng.binomial(1, 1 / (1 + np.exp(-feature)))
    outcome = 3 * treatment + 2 * feature + rng.normal(size=len(feature))

    result = _unobserved_confounder_sensitivity(
        feature[:, None], treatment, outcome
    )

    assert len(result["scenarios"]) == 3
    assert result["scenarios"][0]["partial_r2_treatment"] == 0.01
    assert result["scenarios"][-1]["maximum_absolute_bias"] > result["scenarios"][0]["maximum_absolute_bias"]
