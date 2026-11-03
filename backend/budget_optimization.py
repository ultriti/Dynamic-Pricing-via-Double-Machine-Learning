from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


def optimize_allocation(
    customers: pd.DataFrame,
    budget: float,
    intervention_costs: np.ndarray,
    *,
    max_customers: int | None = None,
    min_customers: int = 0,
    segment_column: str | None = None,
    segment_limits: dict[str, dict[str, int | None]] | None = None,
) -> dict[str, Any]:
    """Choose a binary customer allocation maximizing expected incremental outcomes."""
    if customers.empty:
        raise ValueError("No eligible customers are available for allocation.")
    if "ite" not in customers:
        raise ValueError("Customer treatment-effect scores are required.")
    if not np.isfinite(budget) or budget <= 0:
        raise ValueError("Budget must be a finite positive amount.")

    effects = pd.to_numeric(customers["ite"], errors="coerce").to_numpy(dtype=float)
    costs = np.asarray(intervention_costs, dtype=float).reshape(-1)
    if len(costs) != len(customers):
        raise ValueError("Each customer must have exactly one intervention cost.")
    if not np.isfinite(costs).all() or (costs <= 0).any():
        raise ValueError("Intervention costs must be finite positive amounts.")
    if not np.isfinite(effects).all():
        raise ValueError("Treatment-effect scores must be finite numbers.")
    if min_customers < 0:
        raise ValueError("Minimum customer allocation cannot be negative.")
    if max_customers is not None and max_customers < min_customers:
        raise ValueError("Maximum customers cannot be less than the minimum.")
    if min_customers > len(customers):
        raise ValueError("Minimum customer allocation exceeds the eligible population.")
    if segment_limits and segment_column not in customers:
        raise ValueError("A segment column is required when segment limits are set.")

    constraints: list[tuple[np.ndarray, float, float]] = []
    constraints.append((costs, -np.inf, budget))
    constraints.append(
        (
            np.ones(len(customers), dtype=float),
            float(min_customers),
            float(max_customers) if max_customers is not None else np.inf,
        )
    )

    for segment, limits in (segment_limits or {}).items():
        segment_mask = customers[segment_column].astype(str).eq(str(segment)).to_numpy()
        if not segment_mask.any():
            raise ValueError(f"Allocation limit references unknown segment '{segment}'.")
        lower = limits.get("min_customers") or 0
        upper = limits.get("max_customers")
        if lower < 0 or (upper is not None and upper < lower):
            raise ValueError(f"Invalid allocation bounds for segment '{segment}'.")
        if lower > int(segment_mask.sum()):
            raise ValueError(f"Minimum allocation exceeds segment '{segment}' population.")
        constraints.append(
            (
                segment_mask.astype(float),
                float(lower),
                float(upper) if upper is not None else np.inf,
            )
        )

    matrix = lil_matrix((len(constraints), len(customers)), dtype=float)
    lower_bounds = np.empty(len(constraints), dtype=float)
    upper_bounds = np.empty(len(constraints), dtype=float)
    for row_index, (coefficients, lower, upper) in enumerate(constraints):
        matrix[row_index, :] = coefficients
        lower_bounds[row_index] = lower
        upper_bounds[row_index] = upper

    result = milp(
        c=-effects,
        integrality=np.ones(len(customers), dtype=int),
        bounds=Bounds(np.zeros(len(customers)), np.ones(len(customers))),
        constraints=LinearConstraint(matrix.tocsr(), lower_bounds, upper_bounds),
        options={"disp": False},
    )
    if result.status == 2:
        raise ValueError("The budget and allocation constraints are infeasible.")
    if not result.success or result.x is None:
        raise RuntimeError(f"SciPy allocation solver failed: {result.message}")

    selected = np.rint(result.x).astype(bool)
    if not np.allclose(result.x, selected.astype(float), atol=1e-6):
        raise RuntimeError("SciPy returned a non-binary allocation.")
    allocated_budget = float(costs[selected].sum())
    if allocated_budget > budget + 1e-7:
        raise RuntimeError("SciPy allocation exceeds the configured budget.")

    rows = customers.copy().reset_index(drop=True)
    rows["intervention_cost"] = costs
    rows["expected_incremental_benefit"] = effects
    rows["selected"] = selected
    rows["allocation_reason"] = np.where(
        selected,
        "Selected by the budget-constrained expected-uplift optimization.",
        np.where(
            effects <= 0,
            "Not selected because predicted incremental benefit is non-positive.",
            "Not selected because budget or allocation capacity favored other customers.",
        ),
    )

    chosen_effects = effects[selected]
    return {
        "customers": rows,
        "summary": {
            "objective": "incremental_conversions",
            "budget": float(budget),
            "allocated_budget": allocated_budget,
            "remaining_budget": float(max(0.0, budget - allocated_budget)),
            "customers_evaluated": int(len(customers)),
            "customers_selected": int(selected.sum()),
            "expected_incremental_conversions": float(chosen_effects.sum()),
            "average_selected_uplift": (
                float(chosen_effects.mean()) if len(chosen_effects) else 0.0
            ),
            "estimated_incremental_profit": None,
        },
    }
