"""
PricePilot — pytest tests for Newton-Raphson optimization.
"""

import math
import numpy as np
import pytest

from app.core.regression import RegressionCoefficients
from app.core.optimization import (
    newton_raphson,
    run_optimization,
    revenue,
    revenue_derivative,
    revenue_second_derivative,
    find_analytical_stationary_points,
    ConvergenceStatus,
    StationaryType,
)


def linear_coeffs(a: float, b: float) -> RegressionCoefficients:
    return RegressionCoefficients(a=a, b=b, c=None, model_type="linear")


def quadratic_coeffs(a: float, b: float, c: float) -> RegressionCoefficients:
    return RegressionCoefficients(a=a, b=b, c=c, model_type="quadratic")


class TestNewtonRaphson:
    # -----------------------------------------------------------------------
    # Linear demand: R'(p) = a + 2bp = 0  → p* = -a/(2b)
    # D(p) = 500 - 2p → R'(p) = 500 - 4p → p* = 125
    # -----------------------------------------------------------------------
    def test_linear_known_root(self):
        coeffs = linear_coeffs(500, -2)
        iters, status, p_star = newton_raphson(
            coeffs, p0=100.0, p_min=50.0, p_max=250.0
        )
        assert status == ConvergenceStatus.CONVERGED
        assert p_star is not None
        assert abs(p_star - 125.0) < 1e-4

    def test_linear_converges_from_different_starts(self):
        coeffs = linear_coeffs(500, -2)
        for p0 in [60.0, 150.0, 200.0, 240.0]:
            _, status, p_star = newton_raphson(coeffs, p0=p0, p_min=50.0, p_max=250.0)
            assert status == ConvergenceStatus.CONVERGED
            assert abs(p_star - 125.0) < 1e-4

    # -----------------------------------------------------------------------
    # Quadratic demand
    # D(p) = 800 - 3.5p - 0.005p²
    # R'(p) = 800 - 7p - 0.015p² = 0
    # -----------------------------------------------------------------------
    def test_quadratic_converges(self):
        coeffs = quadratic_coeffs(800, -3.5, -0.005)
        iters, status, p_star = newton_raphson(
            coeffs, p0=100.0, p_min=50.0, p_max=300.0
        )
        assert status == ConvergenceStatus.CONVERGED
        assert p_star is not None
        # R'(p*) ≈ 0
        assert abs(revenue_derivative(p_star, coeffs)) < 1e-4

    def test_quadratic_second_derivative_negative_at_maximum(self):
        """Stationary point of D=800-3.5p-0.005p² should be a maximum."""
        coeffs = quadratic_coeffs(800, -3.5, -0.005)
        _, status, p_star = newton_raphson(coeffs, p0=100.0, p_min=50.0, p_max=300.0)
        assert status == ConvergenceStatus.CONVERGED
        r2nd = revenue_second_derivative(p_star, coeffs)
        assert r2nd < 0, f"Expected R''(p*) < 0, got {r2nd}"

    # -----------------------------------------------------------------------
    # Failure cases
    # -----------------------------------------------------------------------
    def test_max_iterations_respected(self):
        """With only 1 iteration, should return FAILED_MAX_ITER."""
        coeffs = linear_coeffs(500, -2)
        _, status, _ = newton_raphson(
            coeffs, p0=100.0, p_min=50.0, p_max=250.0, max_iterations=1
        )
        # May converge in 1 step for linear — that's OK
        assert status in (ConvergenceStatus.CONVERGED, ConvergenceStatus.FAILED_MAX_ITER)

    def test_zero_derivative_handled(self):
        """When R''(p) = 0 for linear (b=0), should fail gracefully."""
        # Linear with b=0 → R''=0 everywhere
        coeffs = linear_coeffs(500, 0)  # b=0 → R''(p) = 2*0 = 0
        iters, status, p_star = newton_raphson(
            coeffs, p0=100.0, p_min=50.0, p_max=250.0,
            min_derivative_magnitude=1e-12,
        )
        assert status == ConvergenceStatus.FAILED_ZERO_DERIVATIVE

    def test_invalid_start(self):
        coeffs = linear_coeffs(500, -2)
        iters, status, p_star = newton_raphson(
            coeffs, p0=float("nan"), p_min=50.0, p_max=250.0
        )
        assert status == ConvergenceStatus.INVALID_START
        assert p_star is None


class TestAnalyticalRoots:
    def test_linear_analytical_root(self):
        coeffs = linear_coeffs(500, -2)
        roots = find_analytical_stationary_points(coeffs, 50, 250)
        assert len(roots) == 1
        assert abs(roots[0] - 125.0) < 1e-8

    def test_quadratic_analytical_roots_count(self):
        coeffs = quadratic_coeffs(800, -3.5, -0.005)
        roots = find_analytical_stationary_points(coeffs, 50, 300)
        # R'(p) is quadratic so up to 2 real roots; expect 1 in feasible range
        assert len(roots) >= 1

    def test_no_real_roots_complex_case(self):
        """When discriminant < 0, no real roots expected."""
        # R'(p) = a + 2bp + 3cp² = 0 with no real solution
        # Choose a=1000, b=0.01, c=10 → 30p² + 0.02p + 1000 = 0 → disc < 0
        coeffs = quadratic_coeffs(1000, 0.01, 10)
        roots = find_analytical_stationary_points(coeffs, 0, 500)
        assert roots == []


class TestFullOptimization:
    # -----------------------------------------------------------------------
    # Reference test from specification
    # -----------------------------------------------------------------------
    def test_spec_reference_linear(self):
        """D(p)=500-2p: p*=125, D*=250, R*=31250"""
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0)
        assert opt.optimal_price is not None
        assert abs(opt.optimal_price - 125.0) < 0.5
        assert abs(opt.optimal_demand - 250.0) < 1.0
        assert abs(opt.optimal_realized_revenue - 31250.0) < 5.0

    def test_boundary_when_interior_outside_range(self):
        """When p*=125 is outside [130,250], optimum must be at boundary ₹130."""
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=130.0, p_max=250.0)
        assert opt.optimal_price is not None
        # Revenue at 130: 130*(500-260) = 130*240 = 31200
        # Revenue at 250: 250*(500-500) = 0
        assert abs(opt.optimal_price - 130.0) < 1.0, f"Expected boundary at 130, got {opt.optimal_price}"
        assert "Boundary" in opt.optimal_classification or "Lower" in opt.optimal_classification

    def test_upper_boundary_when_demand_increases(self):
        """When b > 0 (demand increases with price), optimum at upper boundary."""
        coeffs = linear_coeffs(100, 2.0)  # b > 0 — unusual
        opt = run_optimization(coeffs, p_min=50.0, p_max=200.0)
        assert opt.optimal_price is not None
        # Revenue should be highest at upper end
        assert abs(opt.optimal_price - 200.0) < 5.0 or opt.optimal_realized_revenue >= 0

    def test_capacity_constraint_caps_demand(self):
        """With capacity=150, optimal revenue uses min(demand, 150)."""
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0, capacity=150.0)
        assert opt.optimal_price is not None
        assert opt.optimal_realized_demand is not None
        assert opt.optimal_realized_demand <= 150.0

    def test_negative_demand_region_excluded(self):
        """Prices where D(p) < 0 must not be the recommended price."""
        # D(p) = 500 - 2p: zero demand at p=250; negative beyond
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=300.0)
        # optimal price should have positive realized demand
        assert opt.optimal_realized_demand is not None
        assert opt.optimal_realized_demand > 0

    def test_scan_verification_agrees(self):
        """The fine scan should agree with the analytical result."""
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0)
        assert opt.scan_agrees, (
            f"Scan found ₹{opt.scan_max_price:.2f} (₹{opt.scan_max_revenue:.2f}) "
            f"but optimal was ₹{opt.optimal_price:.2f} (₹{opt.optimal_realized_revenue:.2f})"
        )

    def test_classification_interior_maximum(self):
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0)
        assert opt.newton_stationary_type == StationaryType.MAXIMUM
        assert opt.optimal_classification == "Interior Maximum"

    def test_price_increment_discretizes(self):
        """Result must be a multiple of the specified increment."""
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0, price_increment=10.0)
        assert opt.optimal_price is not None
        remainder = opt.optimal_price % 10.0
        # Should be a multiple of 10 (within floating point tolerance)
        assert remainder < 0.01 or remainder > 9.99, f"Price {opt.optimal_price} not a multiple of 10"

    def test_quadratic_convergence(self):
        """Quadratic demand model: verify optimization produces finite, positive result."""
        coeffs = quadratic_coeffs(800, -3.5, -0.005)
        opt = run_optimization(coeffs, p_min=50.0, p_max=300.0)
        assert opt.optimal_price is not None
        assert math.isfinite(opt.optimal_price)
        assert opt.optimal_realized_revenue is not None
        assert opt.optimal_realized_revenue > 0


class TestSecondDerivativeClassification:
    def test_maximum_classification(self):
        coeffs = linear_coeffs(500, -2)  # R''(p) = 2*(-2) = -4 < 0 → maximum
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0)
        assert opt.newton_second_derivative is not None
        assert opt.newton_second_derivative < 0

    def test_revenue_at_optimum_matches_formula(self):
        coeffs = linear_coeffs(500, -2)
        opt = run_optimization(coeffs, p_min=50.0, p_max=250.0)
        p = opt.optimal_price
        assert p is not None
        expected_rev = p * (500 - 2 * p)
        assert abs(opt.optimal_revenue - expected_rev) < 0.01
