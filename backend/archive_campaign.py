from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import joblib
from scipy.linalg import qr
import numpy as np
import pandas as pd
from econml.dml import CausalForestDML
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from scipy.optimize import linear_sum_assignment


BACKEND_DIR = Path(__file__).resolve().parent
ARCHIVE_DIR = BACKEND_DIR / "data" / "archive (2)"
ARTIFACT_DIR = BACKEND_DIR / "models"
REPORT_DIR = BACKEND_DIR / "data" / "processed"
CAMPAIGN_ID = 18
LOOKBACK_DAYS = 56
RANDOM_STATE = 42


def _require_archive(archive_dir: Path) -> None:
    required = [
        "campaign_desc.csv",
        "campaign_table.csv",
        "hh_demographic.csv",
        "transaction_data.csv",
    ]
    missing = [name for name in required if not (archive_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Archive dataset is missing required files in {archive_dir}: "
            f"{', '.join(missing)}"
        )


def prepare_archive_cohort(archive_dir: Path = ARCHIVE_DIR) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a household-level campaign cohort from pre- and post-campaign records."""
    _require_archive(archive_dir)

    campaigns = pd.read_csv(archive_dir / "campaign_desc.csv")
    target = campaigns.loc[campaigns["CAMPAIGN"].eq(CAMPAIGN_ID)]
    if len(target) != 1:
        raise ValueError(f"Expected one campaign description for campaign {CAMPAIGN_ID}.")
    target_row = target.iloc[0]
    start_day = int(target_row["START_DAY"])
    end_day = int(target_row["END_DAY"])
    overlapping_campaigns = campaigns.loc[
        campaigns["START_DAY"].le(end_day)
        & campaigns["END_DAY"].ge(start_day),
        "CAMPAIGN",
    ].astype(int)
    overlapping_campaign_ids = sorted(
        set(overlapping_campaigns.tolist()) - {CAMPAIGN_ID}
    )

    assignments = pd.read_csv(archive_dir / "campaign_table.csv")
    assignments["CAMPAIGN"] = pd.to_numeric(assignments["CAMPAIGN"], errors="raise").astype(int)
    if assignments.duplicated(["household_key", "CAMPAIGN"]).any():
        raise ValueError("Campaign data contains duplicate household/campaign assignments.")
    target_households = set(
        assignments.loc[
            assignments["CAMPAIGN"].eq(CAMPAIGN_ID), "household_key"
        ].astype(int)
    )
    overlapping_households = set(
        assignments.loc[
            assignments["CAMPAIGN"].isin(overlapping_campaign_ids), "household_key"
        ].astype(int)
    )

    transaction_path = archive_dir / "transaction_data.csv"
    households: set[int] = set()
    pre_totals: dict[int, dict[str, float]] = {}
    post_totals: dict[int, dict[str, float]] = {}
    post_baskets: dict[int, set[int]] = {}
    pre_start = start_day - LOOKBACK_DAYS
    usecols = [
        "household_key",
        "BASKET_ID",
        "DAY",
        "QUANTITY",
        "SALES_VALUE",
        "RETAIL_DISC",
        "COUPON_DISC",
        "COUPON_MATCH_DISC",
    ]
    for chunk in pd.read_csv(transaction_path, usecols=usecols, chunksize=250_000):
        chunk["household_key"] = pd.to_numeric(
            chunk["household_key"], errors="raise"
        ).astype(int)
        chunk["DAY"] = pd.to_numeric(chunk["DAY"], errors="coerce")
        households.update(chunk["household_key"].unique().tolist())
        pre = chunk.loc[chunk["DAY"].between(pre_start, start_day - 1)].copy()
        post = chunk.loc[chunk["DAY"].between(start_day, end_day)].copy()

        for frame, totals, prefix in (
            (pre, pre_totals, "pre"),
            (post, post_totals, "campaign"),
        ):
            if frame.empty:
                continue
            for column in ["SALES_VALUE", "QUANTITY", "RETAIL_DISC", "COUPON_DISC", "COUPON_MATCH_DISC"]:
                frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
            aggregates = frame.groupby("household_key").agg(
                sales=("SALES_VALUE", "sum"),
                quantity=("QUANTITY", "sum"),
                lines=("DAY", "size"),
                retail_discount=("RETAIL_DISC", "sum"),
                coupon_discount=("COUPON_DISC", "sum"),
                coupon_match_discount=("COUPON_MATCH_DISC", "sum"),
                last_day=("DAY", "max"),
            )
            for household, values in aggregates.iterrows():
                totals.setdefault(int(household), {}).update(
                    {
                        f"{prefix}_sales": float(values["sales"]),
                        f"{prefix}_quantity": float(values["quantity"]),
                        f"{prefix}_lines": float(values["lines"]),
                        f"{prefix}_retail_discount": float(values["retail_discount"]),
                        f"{prefix}_coupon_discount": float(
                            values["coupon_discount"] + values["coupon_match_discount"]
                        ),
                        f"{prefix}_last_day": float(values["last_day"]),
                    }
                )
        if not post.empty:
            basket_pairs = post[["household_key", "BASKET_ID"]].dropna().drop_duplicates()
            for household, basket_id in basket_pairs.itertuples(index=False, name=None):
                post_baskets.setdefault(int(household), set()).add(int(basket_id))

    if not households:
        raise ValueError("The transaction data contains no household records.")

    cohort = pd.DataFrame({"household_key": sorted(households)})
    cohort["treatment"] = cohort["household_key"].isin(target_households).astype(int)
    cohort["overlapping_campaign"] = cohort["household_key"].isin(
        overlapping_households
    )
    cohort = cohort.loc[~cohort["overlapping_campaign"]].drop(
        columns="overlapping_campaign"
    )

    pre_frame = pd.DataFrame.from_dict(pre_totals, orient="index").rename_axis(
        "household_key"
    )
    post_frame = pd.DataFrame.from_dict(post_totals, orient="index").rename_axis(
        "household_key"
    )
    cohort = cohort.merge(pre_frame, on="household_key", how="left").merge(
        post_frame, on="household_key", how="left"
    )
    cohort["pre_recency_days"] = start_day - cohort.pop("pre_last_day")
    cohort["campaign_baskets"] = cohort["household_key"].map(
        lambda household: len(post_baskets.get(int(household), set()))
    )
    for column in ["pre_sales", "pre_quantity", "pre_lines", "pre_recency_days"]:
        cohort[column] = cohort[column].fillna(
            LOOKBACK_DAYS if column == "pre_recency_days" else 0
        )
    for column in [
        "campaign_sales",
        "campaign_quantity",
        "campaign_lines",
        "campaign_retail_discount",
        "campaign_coupon_discount",
        "campaign_last_day",
        "campaign_baskets",
    ]:
        if column not in cohort:
            cohort[column] = 0
        cohort[column] = cohort[column].fillna(0)

    demographics = pd.read_csv(archive_dir / "hh_demographic.csv")
    cohort = cohort.merge(demographics, on="household_key", how="left")
    feature_columns = [
        "pre_sales",
        "pre_quantity",
        "pre_lines",
        "pre_recency_days",
        "AGE_DESC",
        "MARITAL_STATUS_CODE",
        "INCOME_DESC",
        "HOMEOWNER_DESC",
        "HH_COMP_DESC",
        "HOUSEHOLD_SIZE_DESC",
        "KID_CATEGORY_DESC",
    ]
    cohort = cohort.reset_index(drop=True)
    if cohort["treatment"].nunique() != 2:
        raise ValueError("The campaign cohort must contain treated and control households.")
    if cohort["treatment"].value_counts().min() < 30:
        raise ValueError("The campaign cohort is too small for a stable DML evaluation.")

    metadata = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_type": str(target_row["DESCRIPTION"]),
        "start_day": start_day,
        "end_day": end_day,
        "lookback_days": LOOKBACK_DAYS,
        "overlapping_campaign_ids_excluded": overlapping_campaign_ids,
        "excluded_households_with_concurrent_campaigns": int(
            len(households) - cohort.shape[0]
        ),
        "feature_columns": feature_columns,
        "outcome": "household sales value during the campaign window",
        "treatment": f"household assigned campaign {CAMPAIGN_ID} vs not assigned",
        "discount_treatment_available": False,
    }
    return cohort, metadata


def _make_preprocessor(feature_frame: pd.DataFrame) -> ColumnTransformer:
    numeric = feature_frame.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical = [column for column in feature_frame.columns if column not in numeric]
    return ColumnTransformer(
        [
            ("numeric", SimpleImputer(strategy="median"), numeric),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore", drop="first")),
                    ]
                ),
                categorical,
            ),
        ],
        sparse_threshold=0,
    )


def _uplift_evaluation(
    treatment: np.ndarray, outcome: np.ndarray, effects: np.ndarray
) -> dict[str, Any]:
    order = np.argsort(-effects, kind="stable")
    ranked_treatment = treatment[order]
    ranked_outcome = outcome[order]
    propensity = float(treatment.mean())
    if not 0 < propensity < 1:
        raise ValueError("Both campaign and control households are required.")
    incremental = (
        ranked_treatment * ranked_outcome / propensity
        - (1 - ranked_treatment) * ranked_outcome / (1 - propensity)
    )
    gain = np.concatenate(([0.0], np.cumsum(incremental)))
    fraction = np.linspace(0.0, 1.0, len(gain))
    random_endpoint = float(incremental.sum())
    random_gain = fraction * random_endpoint
    step = max(1, int(np.ceil(len(order) / 200)))
    indices = np.unique(np.append(np.arange(0, len(order) + 1, step), len(order)))
    strategy_area = float(
        np.sum((gain[:-1] + gain[1:]) * np.diff(fraction) / 2)
    )
    deciles = np.array_split(np.argsort(-effects, kind="stable"), min(10, len(effects)))
    uplift_by_decile = []
    for number, group in enumerate(deciles, start=1):
        treated_outcomes = outcome[group][treatment[group] == 1]
        control_outcomes = outcome[group][treatment[group] == 0]
        uplift_by_decile.append(
            {
                "decile": number,
                "households": int(len(group)),
                "treated_mean_sales": (
                    float(treated_outcomes.mean()) if len(treated_outcomes) else None
                ),
                "control_mean_sales": (
                    float(control_outcomes.mean()) if len(control_outcomes) else None
                ),
                "observed_sales_difference": (
                    float(treated_outcomes.mean() - control_outcomes.mean())
                    if len(treated_outcomes) and len(control_outcomes)
                    else None
                ),
            }
        )
    return {
        "uplift_curve": [
            {
                "population_fraction": float(fraction[index]),
                "strategy_gain": float(gain[index]),
                "random_gain": float(random_gain[index]),
            }
            for index in indices
        ],
        "uplift_by_decile": uplift_by_decile,
        "uplift_area": strategy_area - random_endpoint / 2,
        "random_baseline_area": random_endpoint / 2,
        "outperforms_random": strategy_area > random_endpoint / 2,
        "heldout_households": int(len(outcome)),
        "heldout_treatment_fraction": propensity,
    }


def _standardized_mean_differences(
    values: np.ndarray,
    treated: np.ndarray,
    control: np.ndarray,
    reference_treated: np.ndarray,
    reference_control: np.ndarray,
) -> np.ndarray:
    pooled_std = np.sqrt((np.var(values[treated], axis=0) + np.var(values[control], axis=0)) / 2)
    pooled_std[pooled_std == 0] = 1
    treated_mean = values[reference_treated].mean(axis=0)
    control_mean = values[reference_control].mean(axis=0)
    return (treated_mean - control_mean) / pooled_std


def _propensity_matching(
    feature_matrix: np.ndarray,
    treatment: np.ndarray,
    outcome: np.ndarray,
) -> dict[str, Any]:
    propensity_model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logistic",
                LogisticRegression(max_iter=2000, random_state=RANDOM_STATE),
            ),
        ]
    )
    propensity_model.fit(feature_matrix, treatment)
    propensity = np.clip(propensity_model.predict_proba(feature_matrix)[:, 1], 1e-5, 1 - 1e-5)
    logits = np.log(propensity / (1 - propensity))
    treated_indices = np.flatnonzero(treatment == 1)
    control_indices = np.flatnonzero(treatment == 0)
    standard_deviation = float(np.std(logits))
    caliper = 0.2 * standard_deviation
    if not np.isfinite(caliper) or caliper <= 0:
        raise ValueError("Could not compute a positive propensity-score caliper.")
    distances = np.abs(logits[treated_indices, None] - logits[control_indices])
    unmatched_penalty = caliper + 1
    costs = np.full(
        (len(treated_indices), len(control_indices) + len(treated_indices)),
        unmatched_penalty,
    )
    costs[:, : len(control_indices)] = np.where(
        distances <= caliper, distances, unmatched_penalty * 2
    )
    row_indices, column_indices = linear_sum_assignment(costs)
    matched = column_indices < len(control_indices)
    matched_treated = treated_indices[row_indices[matched]]
    matched_controls = control_indices[column_indices[matched]]
    if len(matched_treated) < 20:
        raise ValueError(
            f"Only {len(matched_treated)} treated households matched within the caliper."
        )

    all_treated = np.flatnonzero(treatment == 1)
    all_control = np.flatnonzero(treatment == 0)
    smd_before = _standardized_mean_differences(
        feature_matrix, treatment == 1, treatment == 0, all_treated, all_control
    )
    smd_after = _standardized_mean_differences(
        feature_matrix, treatment == 1, treatment == 0, matched_treated, matched_controls
    )
    return {
        "method": "1:1 nearest-neighbor propensity matching without replacement",
        "caliper_standard_deviations_of_logit": 0.2,
        "treated_matched": int(len(matched_treated)),
        "unique_controls_matched": int(np.unique(matched_controls).size),
        "treated_unmatched": int(len(treated_indices) - len(matched_treated)),
        "matched_average_sales_difference": float(
            outcome[matched_treated].mean() - outcome[matched_controls].mean()
        ),
        "max_abs_smd_before": float(np.max(np.abs(smd_before))),
        "max_abs_smd_after": float(np.max(np.abs(smd_after))),
        "features_with_abs_smd_over_0_1_after": int(
            np.count_nonzero(np.abs(smd_after) > 0.1)
        ),
        "propensity_overlap": {
            "treated_min": float(propensity[treated_indices].min()),
            "treated_max": float(propensity[treated_indices].max()),
            "control_min": float(propensity[control_indices].min()),
            "control_max": float(propensity[control_indices].max()),
        },
    }


def _dowhy_audit(
    feature_matrix: np.ndarray,
    feature_names: list[str],
    treatment: np.ndarray,
    outcome: np.ndarray,
) -> dict[str, Any]:
    from dowhy import CausalModel

    standardized_features = StandardScaler().fit_transform(feature_matrix)
    _, triangular, pivots = qr(standardized_features, mode="economic", pivoting=True)
    diagonal = np.abs(np.diag(triangular))
    tolerance = (
        np.finfo(float).eps
        * max(standardized_features.shape)
        * (diagonal[0] if len(diagonal) else 0)
    )
    rank = int(np.count_nonzero(diagonal > tolerance))
    selected_features = sorted(pivots[:rank].tolist())
    selected_names = [feature_names[index] for index in selected_features]
    encoded = pd.DataFrame(
        standardized_features[:, selected_features], columns=selected_names
    )
    causal_data = encoded.assign(treatment=treatment, outcome=outcome)
    graph_edges = "\n".join(
        f"{feature} -> treatment; {feature} -> outcome;"
        for feature in selected_names
    )
    graph = f"digraph {{ {graph_edges} treatment -> outcome; }}"
    model = CausalModel(
        data=causal_data,
        treatment="treatment",
        outcome="outcome",
        graph=graph,
    )
    estimand = model.identify_effect()
    estimate = model.estimate_effect(
        estimand,
        method_name="backdoor.linear_regression",
        test_significance=False,
    )
    audit: dict[str, Any] = {
        "estimand": str(estimand),
        "linear_backdoor_effect": float(estimate.value),
        "linearly_independent_confounders": len(selected_features),
        "dropped_collinear_features": len(feature_names) - len(selected_features),
        "refutations": [],
        "interpretation": (
            "Refutation checks probe model stability under specified perturbations; "
            "they cannot prove that all hidden confounding is absent."
        ),
    }
    for name, kwargs in [
        ("random_common_cause", {"random_seed": RANDOM_STATE}),
        (
            "placebo_treatment_refuter",
            {"random_seed": RANDOM_STATE, "num_simulations": 10},
        ),
        (
            "data_subset_refuter",
            {
                "random_seed": RANDOM_STATE,
                "num_simulations": 10,
                "subset_fraction": 0.8,
            },
        ),
    ]:
        try:
            result = model.refute_estimate(
                estimand,
                estimate,
                method_name=name,
                **kwargs,
            )
            refuted_value = getattr(result, "new_effect", None)
            summary = str(result)
            p_value_match = re.search(
                r"p value:\s*([0-9.eE+-]+)", summary, re.IGNORECASE
            )
            audit["refutations"].append(
                {
                    "method": name,
                    "status": "completed",
                    "original_effect": float(estimate.value),
                    "refuted_effect": (
                        float(refuted_value) if refuted_value is not None else None
                    ),
                    "p_value": (
                        float(p_value_match.group(1)) if p_value_match else None
                    ),
                    "summary": summary,
                }
            )
        except Exception as exc:
            audit["refutations"].append(
                {
                    "method": name,
                    "status": "error",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
    audit["completed_refutations"] = sum(
        refutation["status"] == "completed" for refutation in audit["refutations"]
    )
    return audit


def _unobserved_confounder_sensitivity(
    feature_matrix: np.ndarray,
    treatment: np.ndarray,
    outcome: np.ndarray,
) -> dict[str, Any]:
    """Bound linear-model omitted-confounder bias at stated partial-R2 strengths."""
    design = np.column_stack((np.ones(len(treatment)), treatment, feature_matrix))
    coefficients, _, rank, _ = np.linalg.lstsq(design, outcome, rcond=None)
    residuals = outcome - design @ coefficients
    degrees_of_freedom = len(outcome) - rank
    if degrees_of_freedom <= 0:
        raise ValueError("Insufficient residual degrees of freedom for sensitivity analysis.")
    residual_variance = float(residuals @ residuals / degrees_of_freedom)
    covariance = residual_variance * np.linalg.pinv(design.T @ design)
    standard_error = float(np.sqrt(max(covariance[1, 1], 0)))
    effect = float(coefficients[1])
    if not np.isfinite(standard_error) or standard_error == 0:
        raise ValueError("Could not estimate uncertainty for sensitivity analysis.")
    f_statistic = abs(effect / standard_error) / np.sqrt(degrees_of_freedom)
    robustness_value = float(
        0.5 * (np.sqrt(f_statistic**4 + 4 * f_statistic**2) - f_statistic**2)
    )
    scenarios = []
    for partial_r2 in [0.01, 0.05, 0.1]:
        bias = standard_error * np.sqrt(
            degrees_of_freedom
            * partial_r2**2
            / (1 - partial_r2)
        )
        scenarios.append(
            {
                "partial_r2_treatment": partial_r2,
                "partial_r2_outcome": partial_r2,
                "maximum_absolute_bias": float(bias),
                "lower_effect_bound": float(effect - bias),
                "upper_effect_bound": float(effect + bias),
                "includes_zero": bool(effect - bias <= 0 <= effect + bias),
            }
        )
    return {
        "method": "linear omitted-confounder partial-R2 sensitivity",
        "adjusted_linear_effect": effect,
        "standard_error": standard_error,
        "degrees_of_freedom": int(degrees_of_freedom),
        "robustness_value_to_zero": robustness_value,
        "scenarios": scenarios,
        "interpretation": (
            "Each scenario assumes a hypothetical unobserved confounder has equal "
            "partial R-squared with treatment and outcome, conditional on measured "
            "covariates. These are sensitivity bounds, not evidence that such a "
            "confounder exists or does not exist."
        ),
    }


def train_archive_campaign_model(
    archive_dir: Path = ARCHIVE_DIR, persist: bool = True
) -> dict[str, Any]:
    cohort, metadata = prepare_archive_cohort(archive_dir)
    feature_columns = metadata["feature_columns"]
    features = cohort[feature_columns]
    treatment = cohort["treatment"].to_numpy(dtype=int)
    outcome = cohort["campaign_sales"].to_numpy(dtype=float)
    train_indices, test_indices = train_test_split(
        np.arange(len(cohort)),
        test_size=0.3,
        random_state=RANDOM_STATE,
        stratify=treatment,
    )

    preprocessor = _make_preprocessor(features)
    train_features = preprocessor.fit_transform(features.iloc[train_indices])
    test_features = preprocessor.transform(features.iloc[test_indices])
    feature_names = [
        f"feature_{index}" for index in range(train_features.shape[1])
    ]
    estimator = CausalForestDML(
        model_y=RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=5,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        model_t=RandomForestClassifier(
            n_estimators=100,
            min_samples_leaf=5,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        discrete_treatment=True,
        cv=3,
        n_estimators=100,
        min_samples_leaf=10,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    estimator.fit(
        outcome[train_indices],
        treatment[train_indices],
        X=train_features,
    )
    heldout_effects = np.asarray(
        estimator.effect(test_features, T0=0, T1=1), dtype=float
    ).reshape(-1)
    if not np.isfinite(heldout_effects).all():
        raise ValueError("The DML model returned non-finite held-out effects.")
    uplift = _uplift_evaluation(
        treatment[test_indices], outcome[test_indices], heldout_effects
    )

    fitted_preprocessor = _make_preprocessor(features)
    full_features = fitted_preprocessor.fit_transform(features)
    estimator.fit(outcome, treatment, X=full_features)
    individual_effects = np.asarray(
        estimator.effect(full_features, T0=0, T1=1), dtype=float
    ).reshape(-1)
    if not np.isfinite(individual_effects).all():
        raise ValueError("The DML model returned non-finite customer effects.")

    propensity_diagnostics = _propensity_matching(
        full_features, treatment, outcome
    )
    dowhy_audit = _dowhy_audit(
        full_features,
        [f"feature_{index}" for index in range(full_features.shape[1])],
        treatment,
        outcome,
    )
    sensitivity = _unobserved_confounder_sensitivity(
        full_features, treatment, outcome
    )
    order = np.argsort(-individual_effects, kind="stable")
    scores = [
        {
            "household_key": int(cohort.iloc[index]["household_key"]),
            "treatment_assigned": int(treatment[index]),
            "campaign_sales": float(outcome[index]),
            "estimated_sales_effect": float(individual_effects[index]),
            "effect_rank": rank,
        }
        for rank, index in enumerate(order, start=1)
    ]
    report = {
        **metadata,
        "cohort_rows": int(len(cohort)),
        "treated_households": int(treatment.sum()),
        "control_households": int(len(treatment) - treatment.sum()),
        "households_with_preperiod_transactions": int(
            (cohort["pre_lines"] > 0).sum()
        ),
        "households_with_campaign_window_purchase": int(
            (cohort["campaign_baskets"] > 0).sum()
        ),
        "mean_campaign_sales_treated": float(outcome[treatment == 1].mean()),
        "mean_campaign_sales_control": float(outcome[treatment == 0].mean()),
        "raw_sales_difference": float(
            outcome[treatment == 1].mean() - outcome[treatment == 0].mean()
        ),
        "estimator": "EconML CausalForestDML",
        "base_estimators": "RandomForestRegressor + RandomForestClassifier",
        "outcome_mean_ite": float(individual_effects.mean()),
        "positive_effect_households": int((individual_effects > 0).sum()),
        "negative_effect_households": int((individual_effects < 0).sum()),
        "holdout_evaluation": uplift,
        "propensity_matching": propensity_diagnostics,
        "dowhy_audit": dowhy_audit,
        "unobserved_confounder_sensitivity": sensitivity,
        "caveats": [
            "Treatment is assignment to campaign 18 (TypeA), not an assigned dollar discount.",
            "Campaigns with windows overlapping campaign 18 are excluded from the cohort.",
            "Campaign assignment is observational; matching and refutations do not prove no hidden confounding.",
            "The sales outcome is household sales during the campaign window; coupon redemptions and realized transaction discounts are not randomized discount offers.",
            "The individual sales effects are model estimates and are not known individual counterfactuals.",
        ],
    }
    if persist:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "estimator": estimator,
                "preprocessor": fitted_preprocessor,
                "feature_columns": feature_columns,
                "metadata": metadata,
            },
            ARTIFACT_DIR / "archive_campaign_18_dml.joblib",
        )
        (REPORT_DIR / "archive_campaign_18_review.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        pd.DataFrame(scores).to_csv(
            REPORT_DIR / "archive_campaign_18_scores.csv", index=False
        )
    return {"report": report, "scores": scores}
