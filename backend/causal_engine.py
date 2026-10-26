from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


NUMERIC_FEATURES = ["recency", "history", "mens", "womens", "newbie"]
CATEGORICAL_FEATURES = ["history_segment", "zip_code", "channel"]
TREATMENT_GROUPS = ["Womens E-Mail", "No E-Mail"]


def _uplift_evaluation(
    treatment: np.ndarray, outcome: np.ndarray, effects: np.ndarray
) -> dict[str, Any]:
    """Build inverse-propensity-weighted Qini and held-out uplift-decile data."""
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
    random_endpoint = float(incremental_outcomes.sum())
    random_gain = population_fraction * random_endpoint

    step = max(1, int(np.ceil(len(order) / 200)))
    curve_indices = np.unique(
        np.append(np.arange(0, len(order) + 1, step), len(order))
    )
    strategy_area = float(
        np.sum(
            (cumulative_gain[:-1] + cumulative_gain[1:])
            * np.diff(population_fraction)
            / 2
        )
    )
    random_area = random_endpoint / 2

    ranked_indices = order
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
            }
            for index in curve_indices
        ],
        "uplift_by_decile": uplift_by_decile,
        "qini_area": strategy_area,
        "random_baseline_area": random_area,
        "qini_coefficient": strategy_area - random_area,
        "outperforms_random": strategy_area > random_area,
        "holdout_customers": int(len(outcome)),
        "treatment_propensity": propensity,
    }


def train_dml_analysis(
    frame: pd.DataFrame, feature_columns: list[str]
) -> dict[str, Any]:
    """Fit a cross-fitted causal forest and evaluate it on a held-out split."""
    try:
        from econml.dml import CausalForestDML
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
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
    categorical = [column for column in CATEGORICAL_FEATURES if column in features]
    numeric = [column for column in NUMERIC_FEATURES if column in features]
    other = [column for column in feature_columns if column not in categorical + numeric]
    categorical.extend(other)
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                SimpleImputer(strategy="median"),
                numeric,
            ),
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

    treatment = selected["email_treatment"].to_numpy(dtype=int)
    outcome = selected["conversion"].to_numpy(dtype=float)
    row_indices = np.arange(len(selected))
    train_indices, test_indices = train_test_split(
        row_indices,
        test_size=0.3,
        random_state=42,
        stratify=treatment,
    )
    train_features = preprocessor.fit_transform(features.iloc[train_indices])
    test_features = preprocessor.transform(features.iloc[test_indices])

    estimator = CausalForestDML(
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
    estimator.fit(
        outcome[train_indices],
        treatment[train_indices],
        X=train_features,
    )
    holdout_effects = np.asarray(
        estimator.effect(test_features, T0=0, T1=1), dtype=float
    ).reshape(-1)
    if not np.isfinite(holdout_effects).all():
        raise ValueError("The DML model produced non-finite holdout treatment effects.")

    evaluation = _uplift_evaluation(
        treatment[test_indices], outcome[test_indices], holdout_effects
    )

    population_features = preprocessor.fit_transform(features)
    estimator.fit(outcome, treatment, X=population_features)
    population_effects = np.asarray(
        estimator.effect(population_features, T0=0, T1=1), dtype=float
    ).reshape(-1)
    if not np.isfinite(population_effects).all():
        raise ValueError("The DML model produced non-finite population treatment effects.")

    ranked_order = np.argsort(-population_effects, kind="stable")
    customer_limit = 20_000
    returned_order = ranked_order[:customer_limit]
    customers = [
        {
            "row_id": str(selected.index[index]),
            "treatment_group": str(selected.iloc[index]["segment"]),
            "ite": float(population_effects[index]),
            "effect_percentage_points": float(population_effects[index] * 100),
            "conversion": int(outcome[index]),
        }
        for index in returned_order
    ]

    return {
        "treatment": "Womens E-Mail (T=1) vs No E-Mail (T=0)",
        "outcome": "conversion",
        "estimator": "EconML CausalForestDML",
        "base_estimators": "RandomForestRegressor + RandomForestClassifier",
        "customers_scored": int(len(population_effects)),
        "customer_rows_returned": int(len(customers)),
        "mean_ite": float(population_effects.mean()),
        "positive_effect_count": int((population_effects > 0).sum()),
        "negative_effect_count": int((population_effects < 0).sum()),
        "customers": customers,
        **evaluation,
        "warning": (
            "Customer ITEs come from a final model refit on the eligible comparison "
            "cohort; held-out Qini and uplift metrics use a separate untouched split. "
            "ITE estimates are not known individual counterfactuals. Causal interpretation "
            "depends on the DAG and treatment-assignment assumptions. This "
            "Hillstrom analysis compares email assignment, not discount amounts."
        ),
    }
