"""
PricePilot — Simulation Module

Evaluates ticket pricing scenarios using the active demand model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from app.core.regression import RegressionCoefficients
from app.core.optimization import demand_at, revenue as rev_at


@dataclass
class ScenarioPoint:
    price: float
    predicted_demand: float
    realized_demand: float
    predicted_revenue: float
    realized_revenue: float
    revenue_vs_baseline: float | None      # difference
    revenue_pct_vs_baseline: float | None  # percentage difference
    is_feasible: bool
    notes: str
    difference_from_recommended_price: float | None = None


def scenario_coefficients(coeffs: RegressionCoefficients, multiplier: float = 1.0) -> RegressionCoefficients:
    """Explicit hypothetical demand assumption; never changes a fitted model."""
    if not math.isfinite(multiplier) or not 0 < multiplier <= 10:
        raise ValueError('Hypothetical demand multiplier must be finite, greater than zero and at most 10.')
    return RegressionCoefficients(a=coeffs.a*multiplier, b=coeffs.b*multiplier,
        c=None if coeffs.c is None else coeffs.c*multiplier, model_type=coeffs.model_type)


def evaluate_scenario(
    price: float,
    coeffs: RegressionCoefficients,
    capacity: float | None = None,
    baseline_price: float | None = None,
) -> ScenarioPoint:
    """Evaluate a single ticket price under the given demand model."""
    d = demand_at(price, coeffs)
    realized_d = max(0.0, d)
    if capacity is not None:
        realized_d = min(realized_d, float(capacity))

    rev = price * d
    realized_rev = price * realized_d

    is_feasible = price > 0 and realized_d > 0
    notes_parts: list[str] = []
    if d < 0:
        notes_parts.append("Negative predicted demand.")
        is_feasible = False
    if capacity is not None and d > capacity:
        notes_parts.append(f"Demand capped at capacity ({int(capacity)}).")

    rev_diff: float | None = None
    rev_pct: float | None = None
    if baseline_price is not None:
        baseline_d = demand_at(baseline_price, coeffs)
        baseline_realized = max(0.0, baseline_d)
        if capacity is not None:
            baseline_realized = min(baseline_realized, float(capacity))
        baseline_rev = baseline_price * baseline_realized

        rev_diff = realized_rev - baseline_rev
        if baseline_rev != 0:
            rev_pct = (rev_diff / abs(baseline_rev)) * 100
        elif realized_rev != 0:
            rev_pct = None  # undefined when baseline is zero

    return ScenarioPoint(
        price=price,
        predicted_demand=d,
        realized_demand=realized_d,
        predicted_revenue=rev,
        realized_revenue=realized_rev,
        revenue_vs_baseline=rev_diff,
        revenue_pct_vs_baseline=rev_pct,
        is_feasible=is_feasible,
        notes="; ".join(notes_parts) if notes_parts else "OK",
    )


def evaluate_scenarios(
    prices: list[float],
    coeffs: RegressionCoefficients,
    capacity: float | None = None,
    baseline_price: float | None = None,
    demand_multiplier: float = 1.0,
    recommended_price: float | None = None,
) -> list[ScenarioPoint]:
    """Evaluate multiple ticket prices."""
    adjusted = scenario_coefficients(coeffs, demand_multiplier)
    results = [evaluate_scenario(p, adjusted, capacity, baseline_price) for p in prices]
    for point in results:
        if recommended_price is not None:
            point.difference_from_recommended_price = point.price - recommended_price
        if demand_multiplier != 1:
            point.notes += f'; Hypothetical demand multiplier {demand_multiplier:g}; this assumption is not a fitted causal estimate.'
    return results


def build_revenue_curve(
    coeffs: RegressionCoefficients,
    p_min: float,
    p_max: float,
    capacity: float | None = None,
    n_points: int = 300,
) -> dict:
    """
    Build a smooth revenue curve over [p_min, p_max].
    Returns dict with 'prices', 'demand', 'realized_demand', 'revenue', 'realized_revenue'.
    """
    prices = np.linspace(p_min, p_max, n_points)
    demand = coeffs.predict(prices)
    realized = np.maximum(0.0, demand)
    if capacity is not None:
        realized = np.minimum(realized, float(capacity))

    revenues = prices * demand
    realized_revenues = prices * realized

    return {
        "prices": prices.tolist(),
        "demand": demand.tolist(),
        "realized_demand": realized.tolist(),
        "revenue": revenues.tolist(),
        "realized_revenue": realized_revenues.tolist(),
    }
