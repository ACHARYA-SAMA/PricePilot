"""
PricePilot — pytest tests for regression module.

Tests known synthetic datasets where correct coefficients are known.
"""

import math
import numpy as np
import pytest
from app.core.regression import fit_linear, fit_quadratic, compare_models


# ---------------------------------------------------------------------------
# Linear regression tests
# ---------------------------------------------------------------------------

class TestLinearRegression:
    def test_exact_linear_no_noise(self):
        """D(p) = 500 - 2p: exact observations should recover coefficients exactly."""
        prices = np.array([50, 75, 100, 125, 150, 200, 250], dtype=float)
        demand = 500 - 2 * prices
        result = fit_linear(prices, demand)

        assert abs(result.coefficients.a - 500.0) < 1e-6, f"a={result.coefficients.a}"
        assert abs(result.coefficients.b - (-2.0)) < 1e-6, f"b={result.coefficients.b}"
        # Perfect fit
        assert result.r_squared > 0.9999
        assert result.rmse < 1e-8

    def test_linear_reference_optimum(self):
        """
        Reference test from specification:
        D(p) = 500 - 2p
        Expected p* = 125, D* = 250, R* = 31250
        """
        from app.core.optimization import run_optimization
        prices = np.array([50, 75, 100, 125, 150, 175, 200, 225, 250], dtype=float)
        demand = 500 - 2 * prices
        result = fit_linear(prices, demand)

        opt = run_optimization(
            coeffs=result.coefficients,
            p_min=50.0,
            p_max=250.0,
        )

        assert opt.optimal_price is not None
        assert abs(opt.optimal_price - 125.0) < 0.1, f"p*={opt.optimal_price}"
        assert abs(opt.optimal_demand - 250.0) < 0.5, f"D*={opt.optimal_demand}"
        assert abs(opt.optimal_realized_revenue - 31250.0) < 1.0, f"R*={opt.optimal_realized_revenue}"
        assert opt.optimal_classification == "Interior Maximum"

    def test_linear_with_noise(self):
        """Noisy linear data should recover approximate coefficients."""
        rng = np.random.default_rng(0)
        prices = np.linspace(50, 300, 50)
        demand = 600 - 2.5 * prices + rng.normal(0, 10, size=50)
        result = fit_linear(prices, demand)

        assert abs(result.coefficients.a - 600) < 30
        assert abs(result.coefficients.b - (-2.5)) < 0.3
        assert result.r_squared > 0.85

    def test_linear_requires_minimum_observations(self):
        with pytest.raises(ValueError, match="at least"):
            fit_linear(np.array([100.0]), np.array([200.0]))

    def test_linear_adjusted_r2_defined(self):
        prices = np.linspace(50, 200, 20)
        demand = 400 - 1.5 * prices + np.random.default_rng(1).normal(0, 5, 20)
        result = fit_linear(prices, demand)
        assert result.adjusted_r_squared is not None
        assert result.adjusted_r_squared <= result.r_squared


# ---------------------------------------------------------------------------
# Quadratic regression tests
# ---------------------------------------------------------------------------

class TestQuadraticRegression:
    def test_exact_quadratic_no_noise(self):
        """D(p) = 600 - 2p - 0.001p²: exact observations should recover coefficients."""
        prices = np.linspace(50, 400, 30)
        demand = 600 - 2 * prices - 0.001 * prices ** 2
        result = fit_quadratic(prices, demand)

        assert abs(result.coefficients.a - 600.0) < 1e-4, f"a={result.coefficients.a}"
        assert abs(result.coefficients.b - (-2.0)) < 1e-6, f"b={result.coefficients.b}"
        assert result.coefficients.c is not None
        assert abs(result.coefficients.c - (-0.001)) < 1e-8, f"c={result.coefficients.c}"
        assert result.r_squared > 0.9999

    def test_quadratic_requires_minimum_observations(self):
        with pytest.raises(ValueError, match="at least 3"):
            fit_quadratic(np.array([100.0, 200.0]), np.array([200.0, 150.0]))

    def test_quadratic_with_noise(self):
        """Noisy quadratic data should recover approximate coefficients."""
        rng = np.random.default_rng(42)
        prices = np.linspace(50, 300, 60)
        demand = 800 - 3.5 * prices - 0.005 * prices ** 2 + rng.normal(0, 15, 60)
        result = fit_quadratic(prices, demand)

        assert abs(result.coefficients.a - 800) < 50
        assert abs(result.coefficients.b - (-3.5)) < 0.5
        assert result.coefficients.c is not None
        assert abs(result.coefficients.c - (-0.005)) < 0.002
        assert result.r_squared > 0.85

    def test_quadratic_adjusted_r2(self):
        prices = np.linspace(50, 300, 40)
        demand = 600 - 2 * prices - 0.001 * prices ** 2
        result = fit_quadratic(prices, demand)
        assert result.adjusted_r_squared is not None
        assert result.adjusted_r_squared > 0.99

    def test_quadratic_predictions_match_actuals_noiseless(self):
        prices = np.linspace(100, 500, 10)
        demand = 1000 - 3 * prices - 0.002 * prices ** 2
        result = fit_quadratic(prices, demand)
        pred = result.coefficients.predict(prices)
        np.testing.assert_allclose(pred, demand, atol=1e-4)


# ---------------------------------------------------------------------------
# Diagnostics tests
# ---------------------------------------------------------------------------

class TestDiagnostics:
    def test_residuals_sum_to_zero_linear(self):
        """For OLS, residuals should sum to approximately zero (mean zero)."""
        prices = np.linspace(50, 250, 30)
        demand = 500 - 2 * prices + np.random.default_rng(5).normal(0, 8, 30)
        result = fit_linear(prices, demand)
        assert abs(sum(result.residuals)) < 1e-6

    def test_sse_matches_manual(self):
        prices = np.array([100, 150, 200, 250], dtype=float)
        demand = np.array([300, 200, 150, 100], dtype=float)
        result = fit_linear(prices, demand)
        manual_sse = sum((a - p) ** 2 for a, p in zip(result.demand_actual, result.demand_predicted))
        assert abs(result.sse - manual_sse) < 1e-6

    def test_r2_range(self):
        prices = np.linspace(50, 300, 20)
        demand = 500 - 2 * prices + np.random.default_rng(7).normal(0, 5, 20)
        result = fit_linear(prices, demand)
        assert result.r_squared is not None
        assert not math.isnan(result.r_squared)
        assert result.r_squared <= 1.0

    def test_mae_nonneg(self):
        prices = np.linspace(50, 250, 15)
        demand = 400 - 1.5 * prices
        result = fit_linear(prices, demand)
        assert result.mae >= 0


# ---------------------------------------------------------------------------
# Model comparison tests
# ---------------------------------------------------------------------------

class TestModelComparison:
    def test_compare_returns_both_models(self):
        prices = np.linspace(50, 300, 40)
        demand = 700 - 3 * prices - 0.003 * prices ** 2
        cmp = compare_models(prices, demand)
        assert cmp.linear is not None
        assert cmp.quadratic is not None

    def test_compare_recommends_model(self):
        prices = np.linspace(50, 300, 40)
        demand = 700 - 3 * prices
        cmp = compare_models(prices, demand)
        assert cmp.recommended_model in ("linear", "quadratic", "none")

    def test_compare_insufficient_data_no_quadratic(self):
        prices = np.array([100, 150, 200], dtype=float)
        demand = np.array([300, 200, 100], dtype=float)
        cmp = compare_models(prices, demand, quadratic_eligible=False)
        assert cmp.quadratic is None
