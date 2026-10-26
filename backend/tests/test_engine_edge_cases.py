"""Acceptance regressions for numerical results that cross API/page boundaries."""
import math

import numpy as np
import pytest

from app.core.optimization import ConvergenceStatus, newton_raphson, run_optimization, revenue_derivative
from app.core.regression import RegressionCoefficients, compare_models, fit_linear, fit_quadratic
from app.core.validation import validate_csv_bytes
from app.core.diagnostics import compute_diagnostics


def linear(a=500, b=-2):
    return RegressionCoefficients(a, b, None, "linear")


def test_comparison_returns_full_data_fits_without_leaking_holdout():
    p = np.linspace(50, 200, 25)
    y = 500 - 2*p + np.random.default_rng(11).normal(0, 4, len(p))
    result = compare_models(p, y)
    assert result.has_validation
    assert result.linear.n_samples == len(p)
    np.testing.assert_allclose(result.linear.demand_predicted, fit_linear(p, y).demand_predicted)
    assert result.linear_val.n_samples == result.val_size
    assert result.linear_val.coefficients != result.linear.coefficients


@pytest.mark.parametrize("f,p,y", [
    (fit_linear, [100, 100, 100], [20, 30, 40]),
    (fit_quadratic, [100, 100, 200, 200], [20, 30, 40, 50]),
    (fit_linear, [100, float('inf')], [20, 30]),
    (fit_linear, [100, 200], [20, float('nan')]),
])
def test_invalid_regression_arrays_fail_explicitly(f, p, y):
    with pytest.raises(ValueError):
        f(np.array(p), np.array(y))


def test_tiny_newton_step_is_not_convergence_with_large_residual():
    c = linear(a=1e20, b=-1e20)
    _, status, root = newton_raphson(c, p0=0.50000000001, p_min=0.1, p_max=2,
                                  price_tolerance=1e-6, derivative_tolerance=1e-8)
    if status == ConvergenceStatus.CONVERGED:
        assert abs(revenue_derivative(root, c)) <= 1e-8


def test_nonconverged_newton_iterate_not_classified_as_stationary():
    c = RegressionCoefficients(800, -3.5, -0.005, "quadratic")
    result = run_optimization(c, p0=290, p_min=50, p_max=300, max_iterations=1)
    assert not result.newton_converged
    assert result.newton_stationary_price is None
    assert result.newton_stationary_type in ("", "not_stationary")


def test_discrete_range_with_no_multiples_has_no_optimum():
    result = run_optimization(linear(), p_min=121, p_max=124, price_increment=10)
    assert result.optimal_price is None


def test_discrete_optimum_is_present_in_candidate_evidence():
    result = run_optimization(linear(), p_min=50, p_max=250, price_increment=10)
    assert any(c.source == "discrete" and c.price == result.optimal_price for c in result.candidates)


def test_capacity_transition_is_true_optimum():
    result = run_optimization(linear(), p_min=50, p_max=250, capacity=150)
    assert result.optimal_price == pytest.approx(175)
    assert result.optimal_realized_revenue == pytest.approx(26250)


@pytest.mark.parametrize("kwargs", [
    {"p_min": 200, "p_max": 100}, {"capacity": -10},
    {"price_increment": 0}, {"p_max": float("inf")},
])
def test_invalid_optimizer_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        run_optimization(linear(), **kwargs)


def test_noninteger_sales_rejected_instead_of_rounded():
    result = validate_csv_bytes(b'event_id,ticket_price,tickets_sold\na,100,20.5\nb,150,20\nc,200,10\n')
    assert result.rejected_rows == 1


def test_ambiguous_aliases_report_error_instead_of_crashing():
    result = validate_csv_bytes(b'event_id,price,cost,tickets_sold\na,100,200,20\n')
    assert any(i.code == "AMBIGUOUS_COLUMN" for i in result.issues)
    assert not result.linear_eligible


def test_comma_numeric_is_parsed_consistently():
    result = validate_csv_bytes(b'event_id,ticket_price,tickets_sold\na,"1,000",20\nb,1500,15\nc,2000,10\n')
    assert result.valid_dataframe.ticket_price.tolist() == [1000, 1500, 2000]


def test_invalid_optional_capacity_cannot_survive_as_negative_value():
    result = validate_csv_bytes(b'event_id,ticket_price,tickets_sold,venue_capacity\na,100,20,-5\nb,150,20,100\nc,200,10,100\n')
    assert result.rejected_rows == 1


def test_invalid_optional_date_produces_warning():
    result = validate_csv_bytes(b'event_id,ticket_price,tickets_sold,event_date\na,100,20,not-a-date\nb,150,20,2026-01-01\nc,200,10,2026-02-01\n')
    assert any(i.code == "INVALID_DATE" for i in result.issues)


def test_diagnostics_check_quadratic_vertex_not_only_sampled_prices():
    p = np.linspace(1, 200, 20)
    fit = fit_quadratic(p, (p-100.3)**2-0.001)
    result = compute_diagnostics(fit)
    assert not result.demand_always_positive


def test_diagnostics_do_not_equate_zero_linear_correlation_with_no_pattern():
    p = np.linspace(1, 200, 20)
    result = compute_diagnostics(fit_linear(p, (p-100)**2))
    assert not any("no strong systematic pattern" in message for message in result.interpretation)


def test_small_quadratic_coefficient_is_not_discarded_at_large_prices():
    c = RegressionCoefficients(600, -2e-7, -1e-16, "quadratic")
    result = run_optimization(c, p_min=1e8, p_max=2e9)
    # Independently solve derivative: 600 - 4e-7 p - 3e-16 p² = 0.
    expected = (-4e-7 + math.sqrt((4e-7)**2+4*3e-16*600))/(6e-16)
    assert result.optimal_price == pytest.approx(expected, rel=1e-7)


def test_capacity_transition_with_tiny_curvature_has_exact_candidate():
    c = RegressionCoefficients(500, -2e-7, -1e-16, "quadratic")
    result = run_optimization(c, p_min=1e8, p_max=2e9, capacity=150)
    expected = (-2e-7 + math.sqrt((2e-7)**2+4*1e-16*350))/(2e-16)
    assert result.optimal_price == pytest.approx(expected, rel=1e-7)


def test_stationary_point_at_configured_boundary_is_labeled_boundary():
    result = run_optimization(linear(), p_min=125, p_max=200)
    assert result.optimal_price == pytest.approx(125)
    assert result.optimal_classification == "Lower Boundary Maximum"


def test_newton_detects_leaving_configured_interval():
    _, status, point = newton_raphson(linear(), p0=150, p_min=140, p_max=200)
    assert status != ConvergenceStatus.CONVERGED
    assert point is None


def test_scaled_fit_cannot_silently_lose_precision_in_original_basis():
    p = 1e12 + np.arange(20, dtype=float)
    y = 500 - 2*(p-1e12) - 0.001*(p-1e12)**2
    with pytest.raises(ValueError, match="precision"):
        fit_quadratic(p, y)


def test_zero_demand_does_not_receive_strict_interior_maximum_label():
    result = run_optimization(linear(a=0, b=0), p_min=1, p_max=100)
    assert result.optimal_classification != "Interior Maximum"


def test_no_feasible_result_does_not_claim_scan_agreement():
    result = run_optimization(linear(a=-10, b=-2), p_min=1, p_max=100)
    assert result.optimal_price is None
    assert not result.scan_agrees


def test_decimal_price_increment_preserves_upper_boundary_multiple():
    result = run_optimization(linear(a=100, b=-2), p_min=0.29, p_max=0.3, price_increment=0.1)
    assert result.optimal_price == pytest.approx(0.3)
