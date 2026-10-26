"""Grouped evaluation prevents rows of the same event crossing the holdout."""
import numpy as np
import pytest

from app.core.regression import compare_models, fit_linear
from app.core.diagnostics import compute_diagnostics


def grouped_data(n_groups=10):
    p = np.tile(np.array([50, 75, 100, 125, 150], dtype=float), n_groups)
    y = 500-2*p + np.repeat(np.arange(n_groups), 5)
    groups = [f"event-{i}" for i in range(n_groups) for _ in range(5)]
    return p, y, groups


def test_event_groups_cannot_leak_between_training_and_holdout():
    p, y, groups = grouped_data()
    result = compare_models(p, y, groups=groups)
    assert result.has_validation
    assert result.split_strategy == "random_groups"
    train_groups = {groups[i] for i in result.train_indices}
    val_groups = {groups[i] for i in result.val_indices}
    assert train_groups.isdisjoint(val_groups)
    assert len(train_groups) == 8
    assert len(val_groups) == 2
    assert result.linear.n_samples == len(p)
    assert result.linear_val.n_samples == len(result.val_indices)
    np.testing.assert_allclose(result.linear_val.prices_train, p[result.val_indices])
    same = compare_models(p, y, groups=groups)
    assert result.train_indices == same.train_indices
    assert result.val_indices == same.val_indices


def test_insufficient_independent_event_groups_disables_holdout():
    p, y, groups = grouped_data(4)
    result = compare_models(p, y, groups=groups)
    assert not result.has_validation
    assert result.split_strategy == "none"
    assert result.linear_val is None
    assert result.quadratic_val is None
    assert result.val_indices == []
    assert result.train_indices == list(range(len(p)))
    assert any("independent event groups" in w for w in result.warnings)


def test_short_grouped_history_reports_group_and_row_limitations():
    p = np.tile(np.array([50, 100, 150], dtype=float), 4)
    groups = [str(i) for i in range(4) for _ in range(3)]
    result = compare_models(p, 500-2*p, groups=groups)
    assert not result.has_validation
    assert any("independent event groups" in w for w in result.warnings)
    assert any("only 12 observations" in w for w in result.warnings)


def test_group_holdout_without_price_variation_is_explicitly_unavailable():
    # Every event contains the same single price, so holding out one or two
    # events cannot support quadratic independent-price rank in both sets.
    p = np.repeat(np.array([50, 75, 100, 125, 150], dtype=float), 5)
    groups = [f"event-{i}" for i in range(5) for _ in range(5)]
    result = compare_models(p, 500-2*p, groups=groups)
    assert not result.has_validation
    assert any("price variation" in w for w in result.warnings)
    assert result.linear.n_samples == len(p)


def test_unique_event_ids_preserve_existing_seeded_row_split():
    p = np.linspace(50, 180, 40)
    y = 500-2*p+np.random.default_rng(8).normal(0, 5, len(p))
    baseline = compare_models(p, y)
    result = compare_models(p, y, groups=[str(i) for i in range(len(p))])
    assert result.split_strategy == "random_rows"
    assert result.train_indices == baseline.train_indices
    assert result.val_indices == baseline.val_indices
    assert result.linear_val.rmse == baseline.linear_val.rmse
    assert result.recommended_model == baseline.recommended_model


def test_diagnostic_plot_data_is_computed_by_backend():
    p = np.array([50, 75, 100, 125, 150], dtype=float)
    y = np.array([400, 353, 298, 251, 200], dtype=float)
    fit = fit_linear(p, y)
    result = compute_diagnostics(fit)
    assert len(result.actual_vs_predicted) == len(p)
    assert result.actual_vs_predicted[0] == {
        "actual": float(y[0]), "predicted": fit.demand_predicted[0]}
    assert len(result.diagonal) == 2
    assert all(point["actual"] == point["predicted"] for point in result.diagonal)
    assert sum(bin["count"] for bin in result.histogram) == len(p)
    assert all(bin["right"] >= bin["left"] for bin in result.histogram)


def test_constant_residual_histogram_remains_finite_and_counts_every_observation():
    p = np.array([50, 75, 100, 125, 150], dtype=float)
    result = compute_diagnostics(fit_linear(p, 500-2*p))
    assert sum(bin["count"] for bin in result.histogram) == len(p)
    assert all(np.isfinite(bin["left"]) and np.isfinite(bin["right"]) for bin in result.histogram)
