"""Compute exports from the same full-data fits and configuration as the UI."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import math

import numpy as np

from app.core.regression import compare_models
from app.core.optimization import run_optimization
from app.core.simulation import evaluate_scenarios
from app.schemas.schemas import AnalysisRequest


def json_finite(value: Any) -> Any:
    """Undefined numeric evidence is null, never a fabricated zero."""
    if isinstance(value, dict):
        return {k: json_finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_finite(v) for v in value]
    if isinstance(value, (float, np.floating)) and not math.isfinite(value):
        return None
    return value


@dataclass
class Analysis:
    comparison: Any
    fit: Any
    optimization: Any
    configuration: dict
    request: AnalysisRequest
    warnings: list[str]
    scenarios: list

    def to_dict(self) -> dict:
        comparison = asdict(self.comparison)
        return json_finite({
            'format_version': 1,
            'n_observations': len(self.request.observations),
            'provenance': {'dataset_name': self.request.dataset_name,
                           'is_synthetic': self.request.is_synthetic,
                           'note': 'User-supplied provenance; no independent real-world validation.'},
            'configuration': self.configuration,
            'observations': [o.model_dump(exclude_none=True) for o in self.request.observations],
            **comparison,
            'optimization': asdict(self.optimization) if self.optimization else None,
            'scenario_configuration': {'prices': [s.price for s in self.scenarios],
                'baseline_price': self.request.baseline_price or self.configuration['p_min'],
                'demand_multiplier': self.request.demand_multiplier},
            'scenarios': [asdict(point) for point in self.scenarios],
            'warnings': self.warnings,
        })


def build_analysis(request: AnalysisRequest) -> Analysis:
    p = np.array([o.ticket_price for o in request.observations], dtype=float)
    d = np.array([o.tickets_sold for o in request.observations], dtype=float)
    comparison = compare_models(p, d, request.quadratic_eligible, request.quadratic_recommended,
                                groups=[o.event_id for o in request.observations])
    chosen = request.model_type or comparison.recommended_model
    fit = comparison.linear if chosen == 'linear' else comparison.quadratic if chosen == 'quadratic' else None
    if fit is None or not fit.is_numerically_stable:
        raise ValueError('The selected model cannot be fitted reliably. Add independent price observations.')
    p_min = request.p_min if request.p_min is not None else float(np.min(p))
    p_max = request.p_max if request.p_max is not None else float(np.max(p))
    if p_min >= p_max:
        raise ValueError('The feasible interval must have p_min < p_max.')
    if request.p0 is not None and not p_min <= request.p0 <= p_max:
        raise ValueError('Initial Newton price must lie inside the feasible interval.')
    config = dict(model_type=chosen, p_min=p_min, p_max=p_max,
                  capacity=request.capacity, p0=request.p0,
                  price_increment=request.price_increment,
                  max_iterations=request.max_iterations,
                  price_tolerance=request.price_tolerance,
                  derivative_tolerance=request.derivative_tolerance)
    opt = run_optimization(fit.coefficients, **{k:v for k,v in config.items() if k != 'model_type'})
    warnings = list(comparison.warnings) + list(fit.warnings) + list(opt.warnings)
    if any(o.venue_capacity is not None and o.tickets_sold == o.venue_capacity for o in request.observations):
        warnings.append('Sold-out observations censor demand; ordinary least squares does not correct censoring.')
    if len({o.event_id for o in request.observations}) > 1:
        warnings.append('Pooled events must be comparable; matching categories alone does not establish this.')
    if p_min < np.min(p) or p_max > np.max(p):
        warnings.append('The feasible price interval extends beyond observed prices; extrapolation is uncertain.')
    scenario_prices = request.scenario_prices or list(dict.fromkeys(
        [p_min] + ([opt.optimal_price] if opt.optimal_price is not None else []) + [p_max]))
    baseline = request.baseline_price or p_min
    if any(not p_min <= price <= p_max for price in scenario_prices + [baseline]):
        raise ValueError('Scenario and baseline prices must lie within the active feasible interval.')
    scenarios = evaluate_scenarios(scenario_prices, fit.coefficients, request.capacity,
        baseline, request.demand_multiplier, opt.optimal_price)
    return Analysis(comparison, fit, opt, config, request, list(dict.fromkeys(warnings)), scenarios)
