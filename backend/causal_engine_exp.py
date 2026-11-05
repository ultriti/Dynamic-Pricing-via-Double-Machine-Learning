from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from scipy.linalg import qr
from scipy.stats import t as student_t
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC_FEATURES = ["recency", "history", "mens", "womens", "newbie"]
CATEGORICAL_FEATURES = ["history_segment", "zip_code", "channel"]
TREATMENT_GROUPS = ["Womens E-Mail", "No E-Mail"]


def _qini_values(
    treatment: np.ndarray, outcome: np.ndarray, effects: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float]:
    order = np.argsort(-effects, kind="stable")
    ranked_treatment = treatment[order]
    ranked_outcome = outcome[order]
    propensity = float(treatment.mean())
    if not 0 < propensity < 1:
        raise ValueError("Both treatment and control rows are required.")

    incremental_outcomes = (
        ranked_treatment * ranked_outcome / propensity
        - (1 - ranked_treatment) * ranked_outcome / (1 - propensity)
    )
    cumulative_gain = np.concatenate(([0.0], np.cumsum(incremental_outcomes)))
    population_fraction = np.linspace(0.0, 1.0, len(cumulative_gain))
    return population_fraction, cumulative_gain, float(incremental_outcomes.sum())


def _uplift_evaluation(
    treatment: np.ndarray,
    outcome: np.ndarray,
    effects: np.ndarray,
    bootstrap_samples: int = 200,
) -> dict[str, Any]:
    """Build Qini metrics and bootstrap bands from out-of-fold predictions."""
    propensity = float(treatment.mean())
    population_fraction, cumulative_gain, random_endpoint = _qini_values(
        treatment, outcome, effects
    )
    random_gain = population_fraction * random_endpoint

    step = max(1, int(np.ceil(len(effects) / 200)))
    curve_indices = np.unique(
        np.append(np.arange(0, len(effects) + 1, step), len(effects))
    )
    strategy_area = float(
        np.sum(
            (cumulative_gain[:-1] + cumulative_gain[1:])
            * np.diff(population_fraction)
            / 2
        )
    )
    random_area = random_endpoint / 2

    rng = np.random.default_rng(42)
    treated_indices = np.flatnonzero(treatment == 1)
    control_indices = np.flatnonzero(treatment == 0)
    bootstrap_curves = np.empty((bootstrap_samples, len(curve_indices)))
    for bootstrap_index in range(bootstrap_samples):
        sampled_indices = np.concatenate(
            (
                rng.choice(treated_indices, size=len(treated_indices), replace=True),
                rng.choice(control_indices, size=len(control_indices), replace=True),
            )
        )
        sampled_fraction, sampled_gain, _ = _qini_values(
            treatment[sampled_indices],
            outcome[sampled_indices],
            effects[sampled_indices],
        )
        bootstrap_curves[bootstrap_index] = np.interp(
            population_fraction[curve_indices], sampled_fraction, sampled_gain
        )
    lower_band, upper_band = np.quantile(bootstrap_curves, [0.05, 0.95], axis=0)

    ranked_indices = np.argsort(-effects, kind="stable")
    groups = np.array_split(ranked_indices, min(10, len(ranked_indices)))
    uplift_by_decile = []
    for decile, indices in enumerate(groups, start=1):
        group_treatment = treatment[indices]
        group_outcome = outcome[indices]
        treated_outcomes = group_outcome[group_treatment == 1]
        control_outcomes = group_outcome[group_treatment == 0]
        uplift_by_decile.append(
            {
                "decile": decile,
                "customers": int(len(indices)),
                "treated_conversion_rate": (
                    float(treated_outcomes.mean()) if len(treated_outcomes) else None
                ),
                "control_conversion_rate": (
                    float(control_outcomes.mean()) if len(control_outcomes) else None
                ),
                "observed_uplift": (
                    float(treated_outcomes.mean() - control_outcomes.mean())
                    if len(treated_outcomes) and len(control_outcomes)
                    else None
                ),
            }
        )

    return {
        "qini_curve": [
            {
                "population_fraction": float(population_fraction[index]),
                "strategy_gain": float(cumulative_gain[index]),
                "random_gain": float(random_gain[index]),
                "strategy_gain_lower": float(lower_band[position]),
                "strategy_gain_upper": float(upper_band[position]),
            }
            for position, index in enumerate(curve_indices)
        ],
        "uplift_by_decile": uplift_by_decile,
        "qini_area": strategy_area,
        "random_baseline_area": random_area,
        "qini_coefficient": strategy_area - random_area,
        "outperforms_random": strategy_area > random_area,
        "evaluation_customers": int(len(outcome)),
        "evaluation_method": "Stratified 3-fold out-of-fold treatment-effect predictions",
        "qini_band_confidence_level": 0.90,
        "qini_bootstrap_samples": int(bootstrap_samples),
        "treatment_propensity": propensity,
        "treatment_propensity_method": (
            "Empirical treatment fraction; appropriate for the randomized "
            "Hillstrom assignment, not a propensity model for observational data."
        ),
    }


def _make_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    categorical = [column for column in CATEGORICAL_FEATURES if column in features]
    numeric = [column for column in NUMERIC_FEATURES if column in features]
    other = [
        column
        for column in features.columns
        if column not in categorical + numeric
    ]
    categorical.extend(other)
    return ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median"), numeric),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ],
        sparse_threshold=0,
    )


def _new_estimator():
    from econml.dml import CausalForestDML
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    return CausalForestDML(
        model_y=RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        ),
        model_t=RandomForestClassifier(
            n_estimators=100,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        ),
        discrete_treatment=True,
        cv=3,
        n_estimators=100,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
    )


def _standardized_mean_differences(
    features: np.ndarray,
    feature_names: list[str],
    treatment: np.ndarray,
    feature_columns: list[str],
) -> list[dict[str, Any]]:
    treated = treatment == 1
    control = treatment == 0
    treated_values = features[treated]
    control_values = features[control]
    pooled_std = np.sqrt(
        (np.var(treated_values, axis=0) + np.var(control_values, axis=0)) / 2
    )
    pooled_std[pooled_std == 0] = 1
    differences = (treated_values.mean(axis=0) - control_values.mean(axis=0)) / pooled_std
    rows = []
    for feature in feature_columns:
        indices = [
            index
            for index, name in enumerate(feature_names)
            if name == f"numeric__{feature}"
            or name == f"categorical__{feature}"
            or name.startswith(f"categorical__{feature}_")
        ]
        if not indices:
            continue
        worst_index = max(indices, key=lambda index: abs(differences[index]))
        rows.append(
            {
                "covariate": feature,
                "largest_level": feature_names[worst_index].split("__", 1)[-1],
                "smd": float(differences[worst_index]),
                "absolute_smd": float(abs(differences[worst_index])),
                "balanced": bool(abs(differences[worst_index]) < 0.1),
            }
        )
    return rows


def _dowhy_refutation_audit(
    feature_matrix: np.ndarray,
    feature_names: list[str],
    treatment: np.ndarray,
    outcome: np.ndarray,
) -> dict[str, Any]:
    try:
        from .dowhy_compat import load_causal_model
    except ImportError:
        from dowhy_compat import load_causal_model

    standardized = StandardScaler().fit_transform(feature_matrix)
    _, triangular, pivots = qr(standardized, mode="economic", pivoting=True)
    diagonal = np.abs(np.diag(triangular))
    tolerance = (
        np.finfo(float).eps
        * max(standardized.shape)
        * (diagonal[0] if len(diagonal) else 0)
    )
    rank = int(np.count_nonzero(diagonal > tolerance))
    selected_features = sorted(pivots[:rank].tolist())
    selected_names = [feature_names[index] for index in selected_features]
    encoded = pd.DataFrame(
        standardized[:, selected_features], columns=selected_names
    )
    causal_data = encoded.assign(
        email_treatment=treatment, conversion=outcome
    )
    graph_edges = "\n".join(
        f"{feature} -> email_treatment; {feature} -> conversion;"
        for feature in selected_names
    )
    graph = (
        f"digraph {{ {graph_edges} "
        "email_treatment -> conversion; }"
    )
    refutation_methods = [
        ("placebo_treatment_refuter", {"num_simulations": 20}),
        ("random_common_cause", {}),
        (
            "data_subset_refuter",
            {"num_simulations": 20, "subset_fraction": 0.8},
        ),
    ]
    try:
        model = load_causal_model()(
            data=causal_data,
            treatment="email_treatment",
            outcome="conversion",
            graph=graph,
        )
        estimand = model.identify_effect()
        estimate = model.estimate_effect(
            estimand,
            method_name="backdoor.linear_regression",
            test_significance=False,
        )
    except Exception as exc:
        message = (
            "DoWhy backdoor estimation failed; refutations were not run. "
            f"{type(exc).__name__}: {exc}"
        )
        return {
            "backdoor_effect": None,
            "refutations": [
                {
                    "method": method,
                    "p_value": None,
                    "refuted_effect": None,
                    "passed": None,
                    "status": "error",
                    "message": message,
                }
                for method, _ in refutation_methods
            ],
            "alpha": 0.05,
            "interpretation": (
                "The DML model and out-of-fold evaluation completed, but the "
                f"DoWhy robustness audit could not run. {message}"
            ),
        }

    refutations = []
    for method, kwargs in refutation_methods:
        try:
            refutation = model.refute_estimate(
                estimand,
                estimate,
                method_name=method,
                random_seed=42,
                **kwargs,
            )
            summary = str(refutation)
            match = re.search(
                r"p value:\s*([0-9.eE+-]+)", summary, re.IGNORECASE
            )
            p_value = float(match.group(1)) if match else None
            refuted_effect = getattr(refutation, "new_effect", None)
            refutations.append(
                {
                    "method": method,
                    "p_value": p_value,
                    "refuted_effect": (
                        float(refuted_effect)
                        if refuted_effect is not None
                        else None
                    ),
                    "passed": p_value is not None and p_value >= 0.05,
                    "status": (
                        "passed"
                        if p_value is not None and p_value >= 0.05
                        else "failed"
                        if p_value is not None
                        else "inconclusive"
                    ),
                }
            )
        except Exception as exc:
            refutations.append(
                {
                    "method": method,
                    "p_value": None,
                    "refuted_effect": None,
                    "passed": None,
                    "status": "error",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "backdoor_effect": float(estimate.value),
        "refutations": refutations,
        "alpha": 0.05,
        "interpretation": (
            "A pass means this perturbation did not significantly change the "
            "estimate at alpha=0.05; refutations probe robustness and do not "
            "prove that hidden confounding is absent."
        ),
    }


def train_dml_analysis(
    frame: pd.DataFrame, feature_columns: list[str]
) -> dict[str, Any]:
    """Fit a causal forest, evaluate with outer-fold predictions, and score customers."""
    try:
        from econml.dml import CausalForestDML
    except ImportError as exc:
        raise RuntimeError(
            "EconML and scikit-learn are required for DML training."
        ) from exc

    required = [*feature_columns, "segment", "conversion"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    selected = frame.loc[frame["segment"].isin(TREATMENT_GROUPS)].copy()

    selected["conversion"] = pd.to_numeric(selected["conversion"], errors="coerce")
    selected = selected.dropna(subset=["conversion"])
    selected["email_treatment"] = selected["segment"].eq("Womens E-Mail").astype(int)

    observed_outcomes = set(selected["conversion"].unique())
    if not observed_outcomes.issubset({0, 1}):
        raise ValueError("The conversion outcome must contain only binary 0/1 values.")
    if selected["email_treatment"].nunique() != 2:
        raise ValueError("Both Womens E-Mail and No E-Mail rows are required.")
    if selected["email_treatment"].value_counts().min() < 10:
        raise ValueError(
            "At least 10 valid rows are required in each treatment group for a "
            "stable train/test split."
        )

    features = selected[feature_columns].copy()
    treatment = selected["email_treatment"].to_numpy(dtype=int)
    outcome = selected["conversion"].to_numpy(dtype=float)
    fold_count = min(3, int(np.bincount(treatment).min()))
    if fold_count < 2:
        raise ValueError("At least two rows per treatment group are required.")
    oof_effects = np.full(len(selected), np.nan, dtype=float)
    splitter = StratifiedKFold(
        n_splits=fold_count, shuffle=True, random_state=42
    )
    for train_indices, test_indices in splitter.split(features, treatment):
        fold_preprocessor = _make_preprocessor(features)
        train_features = fold_preprocessor.fit_transform(
            features.iloc[train_indices]
        )
        test_features = fold_preprocessor.transform(features.iloc[test_indices])
        fold_estimator = _new_estimator()
        fold_estimator.fit(
            outcome[train_indices],
            treatment[train_indices],
            X=train_features,
        )
        oof_effects[test_indices] = np.asarray(
            fold_estimator.effect(test_features, T0=0, T1=1), dtype=float
        ).reshape(-1)
    if not np.isfinite(oof_effects).all():
        raise ValueError("The DML model produced non-finite out-of-fold effects.")
    evaluation = _uplift_evaluation(
        treatment, outcome, oof_effects
    )
    evaluation["evaluation_folds"] = fold_count
    evaluation["evaluation_method"] = (
        f"Stratified {fold_count}-fold out-of-fold treatment-effect predictions"
    )

    preprocessor = _make_preprocessor(features)
    population_features = preprocessor.fit_transform(features)
    estimator = _new_estimator()
    estimator.fit(outcome, treatment, X=population_features)
    population_effects = np.asarray(
        estimator.effect(population_features, T0=0, T1=1), dtype=float
    ).reshape(-1)
    if not np.isfinite(population_effects).all():
        raise ValueError("The DML model produced non-finite population treatment effects.")
    interval_lower, interval_upper = estimator.effect_interval(
        population_features, T0=0, T1=1, alpha=0.1
    )
    interval_lower = np.asarray(interval_lower, dtype=float).reshape(-1)
    interval_upper = np.asarray(interval_upper, dtype=float).reshape(-1)
    if (
        len(interval_lower) != len(population_effects)
        or len(interval_upper) != len(population_effects)
        or not np.isfinite(interval_lower).all()
        or not np.isfinite(interval_upper).all()
    ):
        raise ValueError("The DML model produced invalid 90% effect intervals.")

    feature_names = preprocessor.get_feature_names_out().tolist()
    balance = _standardized_mean_differences(
        population_features, feature_names, treatment, feature_columns
    )
    treated_outcomes = outcome[treatment == 1]
    control_outcomes = outcome[treatment == 0]
    raw_difference = float(treated_outcomes.mean() - control_outcomes.mean())
    treated_variance = treated_outcomes.var(ddof=1) / len(treated_outcomes)
    control_variance = control_outcomes.var(ddof=1) / len(control_outcomes)
    variance_sum = treated_variance + control_variance
    raw_standard_error = float(np.sqrt(variance_sum))
    if variance_sum == 0:
        interval_critical = 0.0
    else:
        degrees_freedom = variance_sum**2 / (
            treated_variance**2 / (len(treated_outcomes) - 1)
            + control_variance**2 / (len(control_outcomes) - 1)
        )
        interval_critical = float(student_t.ppf(0.95, degrees_freedom))

    audit = _dowhy_refutation_audit(
        population_features,
        [f"feature_{index}" for index in range(population_features.shape[1])],
        treatment,
        outcome,
    )
    histogram_counts, histogram_edges = np.histogram(population_effects, bins=40)

    ranked_order = np.argsort(-population_effects, kind="stable")
    customer_limit = 20_000
    returned_order = ranked_order[:customer_limit]
    customers = [
        {
            "row_id": str(selected.index[index]),
            "treatment_group": str(selected.iloc[index]["segment"]),
            "ite": float(population_effects[index]),
            "effect_percentage_points": float(population_effects[index] * 100),
            "ite_lower_90": float(interval_lower[index]),
            "ite_upper_90": float(interval_upper[index]),
            "conversion": int(outcome[index]),
        }
        for index in returned_order
    ]

    return {
        "_model": estimator,
        "_preprocessor": preprocessor,
        "_feature_columns": feature_columns,
        "treatment": "Womens E-Mail (T=1) vs No E-Mail (T=0)",
        "outcome": "conversion",
        "estimator": "EconML CausalForestDML",
        "base_estimators": "RandomForestRegressor + RandomForestClassifier",
        "customers_scored": int(len(population_effects)),
        "customer_rows_returned": int(len(customers)),
        "customer_row_limit": int(customer_limit),
        "mean_ite": float(population_effects.mean()),
        "ate": float(population_effects.mean()),
        "rct_benchmark": {
            "mean_conversion_treated": float(treated_outcomes.mean()),
            "mean_conversion_control": float(control_outcomes.mean()),
            "raw_difference": raw_difference,
            "ci_90_lower": raw_difference
            - interval_critical * raw_standard_error,
            "ci_90_upper": raw_difference
            + interval_critical * raw_standard_error,
            "design": "Randomized Hillstrom email assignment; unadjusted difference in means",
        },
        "covariate_balance": balance,
        "causal_audit": audit,
        "ite_distribution": {
            "counts": histogram_counts.astype(int).tolist(),
            "bin_edges": histogram_edges.astype(float).tolist(),
            "minimum": float(population_effects.min()),
            "maximum": float(population_effects.max()),
            "p05": float(np.quantile(population_effects, 0.05)),
            "p50": float(np.quantile(population_effects, 0.50)),
            "p95": float(np.quantile(population_effects, 0.95)),
        },
        "positive_effect_count": int((population_effects > 0).sum()),
        "negative_effect_count": int((population_effects < 0).sum()),
        "customers": customers,
        **evaluation,
        "warning": (
            "Customer ITEs come from a final model refit on the eligible comparison "
            "cohort; Qini and uplift metrics use outer-fold out-of-fold predictions "
            "with stratified bootstrap 90% bands. "
            "ITE estimates are not known individual counterfactuals. Causal interpretation "
            "depends on the DAG and treatment-assignment assumptions. This "
            "Hillstrom analysis compares email assignment, not discount amounts. "
            "The average of conditional treatment-effect predictions is the model "
            "ATE estimate; the randomized difference in means is reported separately."
        ),
    }
