"""
PricePilot — Diagnostics Module

Extended model diagnostics: residual analysis, demand shape checks,
model reliability assessment, and interpretive messages.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from app.core.regression import ModelFitResult, RegressionCoefficients


@dataclass
class ResidualDiagnostics:
    """Full residual analysis for one fitted model."""
    model_type: str
    n: int
    prices: list[float]
    actuals: list[float]
    predictions: list[float]
    residuals: list[float]

    # Metrics
    sse: float
    sst: float
    mae: float
    rmse: float
    r_squared: float
    adjusted_r_squared: float | None

    # Distribution info
    residual_mean: float
    residual_std: float
    residual_min: float
    residual_max: float

    # Shape checks
    demand_monotone_decreasing: bool      # D'(p) < 0 over full price range
    demand_always_positive: bool          # D(p) > 0 over full price range
    has_interior_optimum: bool            # Revenue has a stationary point in range

    # Interpretive messages
    interpretation: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    actual_vs_predicted: list[dict[str, float]] = field(default_factory=list)
    diagonal: list[dict[str, float]] = field(default_factory=list)
    histogram: list[dict] = field(default_factory=list)


def compute_diagnostics(fit: ModelFitResult) -> ResidualDiagnostics:
    """Compute extended diagnostics from a ModelFitResult."""
    prices = np.array(fit.prices_train)
    actuals = np.array(fit.demand_actual)
    preds = np.array(fit.demand_predicted)
    residuals = actuals - preds

    warnings: list[str] = []
    interpretation: list[str] = []

    # ---- R² interpretation
    r2 = fit.r_squared
    if math.isnan(r2):
        interpretation.append(
            "R² is undefined because the observed ticket sales have zero variance. "
            "All observations report identical ticket counts."
        )
        warnings.append("Zero variance in observed demand — R² is undefined.")
    elif r2 >= 0.90:
        interpretation.append(
            f"R² = {r2:.4f}: The model explains {r2*100:.1f}% of the variation in observed "
            "ticket sales. This is a strong fit on the training data."
        )
    elif r2 >= 0.70:
        interpretation.append(
            f"R² = {r2:.4f}: The model explains {r2*100:.1f}% of the variation in observed "
            "ticket sales. This is a moderate fit."
        )
    elif r2 >= 0.50:
        interpretation.append(
            f"R² = {r2:.4f}: The model explains {r2*100:.1f}% of the variation. "
            "Fit quality is marginal — interpret results cautiously."
        )
    else:
        interpretation.append(
            f"R² = {r2:.4f}: The model explains less than half the variation in observed "
            "ticket sales. Model uncertainty is high. The suggested price should be "
            "treated as exploratory only."
        )
        warnings.append(f"Low R² ({r2:.4f}): model fit is weak.")

    if r2 < 0:
        warnings.append(
            "R² is negative, indicating the model fits worse than a horizontal mean line. "
            "This usually means the model is inappropriate for this data."
        )

    # ---- RMSE interpretation
    mean_demand = float(np.mean(actuals)) if len(actuals) > 0 else 1.0
    pct_error = (fit.rmse / mean_demand * 100) if mean_demand > 0 else float("nan")
    if math.isfinite(pct_error):
        interpretation.append(
            f"RMSE = {fit.rmse:.2f} tickets (≈ {pct_error:.1f}% of mean observed demand {mean_demand:.1f}). "
            "This is the root mean square prediction error, expressed in tickets."
        )

    # ---- Residual pattern check
    if len(prices) >= 5:
        # Check if residuals correlate with price (systematic pattern)
        corr = float(np.corrcoef(prices, residuals)[0, 1]) if np.std(prices) > 0 and np.std(residuals) > 0 else 0.0
        if abs(corr) > 0.4:
            interpretation.append(
                f"Residuals show a correlation of {corr:.2f} with ticket price, "
                "suggesting the model may not fully capture the shape of the demand relationship. "
                "Consider the quadratic model if it is not already selected."
            )
        else:
            interpretation.append(
                "Residuals have low linear correlation with price, as expected for ordinary "
                "least squares with an intercept. This does not rule out nonlinear residual patterns; "
                "inspect the residual plot and held-out prediction errors."
            )

    # ---- Demand shape checks
    coeffs = fit.coefficients
    p_min, p_max = fit.price_min, fit.price_max
    critical_prices = [p_min, p_max]
    if coeffs.model_type == "quadratic" and coeffs.c not in (None, 0):
        vertex = -coeffs.b / (2 * coeffs.c)
        if p_min < vertex < p_max:
            critical_prices.append(vertex)
    test_prices = np.array(critical_prices)
    test_demand = coeffs.predict(test_prices)

    demand_always_positive = bool(np.all(test_demand > 0))
    if not demand_always_positive:
        first_negative = float(test_prices[test_demand <= 0][0]) if np.any(test_demand <= 0) else p_max
        warnings.append(
            f"Fitted demand becomes non-positive at approximately ₹{first_negative:.0f}. "
            "Revenue optimization will only consider prices with positive predicted demand."
        )

    # Monotonicity check
    if coeffs.model_type == "linear":
        demand_decreasing = coeffs.b < 0
    else:
        c = coeffs.c if coeffs.c is not None else 0.0
        deriv_at_prices = coeffs.b + 2 * c * test_prices
        demand_decreasing = bool(np.all(deriv_at_prices < 0))

    if not demand_decreasing:
        warnings.append(
            "The fitted demand curve predicts that ticket sales increase as prices rise "
            "over part of the feasible range. This is economically unusual and may indicate "
            "confounding factors, insufficient data, or an inappropriate model."
        )

    # Interior optimum check
    from app.core.optimization import find_analytical_stationary_points
    roots = find_analytical_stationary_points(coeffs, p_min, p_max)
    has_interior = len([r for r in roots if p_min < r < p_max]) > 0

    # Plot coordinates and histogram counts are mathematical output and are
    # generated here so every frontend and export can use the same values.
    paired_points = [{"actual": float(actual), "predicted": float(prediction)}
                     for actual, prediction in zip(actuals, preds)]
    axis_min = float(min(np.min(actuals), np.min(preds)))
    axis_max = float(max(np.max(actuals), np.max(preds)))
    if axis_min == axis_max:
        axis_min -= 0.5
        axis_max += 0.5
    diagonal = [{"actual": axis_min, "predicted": axis_min},
                {"actual": axis_max, "predicted": axis_max}]
    counts, edges = np.histogram(residuals, bins=min(10, max(1, math.ceil(math.sqrt(len(residuals))))))
    histogram = [{"left": float(edges[i]), "right": float(edges[i+1]),
                  "count": int(count), "label": f"{edges[i]:.3g} to {edges[i+1]:.3g}"}
                 for i, count in enumerate(counts)]

    return ResidualDiagnostics(
        model_type=fit.model_type,
        n=fit.n_samples,
        prices=fit.prices_train,
        actuals=fit.demand_actual,
        predictions=fit.demand_predicted,
        residuals=residuals.tolist(),
        sse=fit.sse,
        sst=fit.sst,
        mae=fit.mae,
        rmse=fit.rmse,
        r_squared=fit.r_squared,
        adjusted_r_squared=fit.adjusted_r_squared,
        residual_mean=float(np.mean(residuals)),
        residual_std=float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0,
        residual_min=float(np.min(residuals)),
        residual_max=float(np.max(residuals)),
        demand_monotone_decreasing=demand_decreasing,
        demand_always_positive=demand_always_positive,
        has_interior_optimum=has_interior,
        interpretation=interpretation,
        warnings=warnings,
        actual_vs_predicted=paired_points,
        diagonal=diagonal,
        histogram=histogram,
    )
