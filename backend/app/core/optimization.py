"""
PricePilot — Optimization Module

Implements Newton–Raphson method to find stationary points of the revenue function,
then performs a global feasible comparison to identify the true revenue maximum.

Revenue function:
    R(p) = p · D(p)

For linear demand D(p) = a + bp:
    R(p)  = ap + bp²
    R'(p) = a + 2bp        ← f(p)
    R''(p)= 2b             ← f'(p)

For quadratic demand D(p) = a + bp + cp²:
    R(p)  = ap + bp² + cp³
    R'(p) = a + 2bp + 3cp²  ← f(p)
    R''(p)= 2b + 6cp        ← f'(p)

Newton–Raphson iteration:
    p_{n+1} = p_n - f(p_n) / f'(p_n)

Convergence requires |R'(p_returned)| <= derivative_tolerance.
Small steps alone do not establish a derivative root.

Reference:
    Chapra & Canale, "Numerical Methods for Engineers", Unit II.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from app.core.regression import RegressionCoefficients


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NewtonIteration:
    """One row in the Newton–Raphson iteration table."""
    iteration: int
    price: float          # p_n
    f_value: float        # f(p_n) = R'(p_n)
    f_prime: float        # f'(p_n) = R''(p_n)
    correction: float     # -f(p_n)/f'(p_n)
    next_price: float     # p_{n+1}
    abs_error: float      # |p_{n+1} - p_n|
    convergence_note: str


class ConvergenceStatus(str):
    CONVERGED = "converged"
    FAILED_MAX_ITER = "failed_max_iterations"
    FAILED_ZERO_DERIVATIVE = "failed_zero_derivative"
    FAILED_NONFINITE = "failed_nonfinite"
    FAILED_DIVERGENCE = "failed_divergence"
    FAILED_STAGNATION = "failed_stagnation"
    FAILED_OUT_OF_BOUNDS = "failed_out_of_bounds"
    BOUNDARY_OPTIMUM = "boundary_optimum"
    INVALID_START = "invalid_start"


class StationaryType(str):
    MAXIMUM = "maximum"
    MINIMUM = "minimum"
    INCONCLUSIVE = "inconclusive"
    NOT_STATIONARY = "not_stationary"


@dataclass
class StationaryPoint:
    price: float
    revenue: float
    demand: float
    second_derivative: float
    stationary_type: str   # ConvergenceStatus values
    is_feasible: bool
    notes: str


@dataclass
class OptimizationCandidate:
    """One candidate for the global revenue maximum."""
    source: str           # 'newton', 'boundary_lower', 'boundary_upper', 'capacity_transition', 'polynomial_root'
    price: float
    demand: float
    realized_demand: float  # after capacity constraint
    revenue: float
    realized_revenue: float
    is_feasible: bool
    notes: str


@dataclass
class OptimizationResult:
    """Full result of revenue optimization."""
    # Newton–Raphson output
    iterations: list[NewtonIteration] = field(default_factory=list)
    newton_converged: bool = False
    newton_status: str = ""
    newton_stationary_price: float | None = None
    newton_stationary_type: str = ""
    newton_second_derivative: float | None = None
    newton_derivative_residual: float | None = None

    # All candidates considered
    candidates: list[OptimizationCandidate] = field(default_factory=list)

    # Global optimum
    optimal_price: float | None = None
    optimal_demand: float | None = None
    optimal_realized_demand: float | None = None
    optimal_revenue: float | None = None
    optimal_realized_revenue: float | None = None
    optimal_source: str = ""
    optimal_classification: str = ""

    # Verification
    scan_max_price: float | None = None
    scan_max_revenue: float | None = None
    scan_agrees: bool = True
    scan_tolerance_pct: float = 1.0

    # Configuration echoed back
    price_min: float = 0.0
    price_max: float = 0.0
    p0: float = 0.0
    max_iterations: int = 100
    price_tolerance: float = 1e-6
    derivative_tolerance: float = 1e-8
    capacity: float | None = None
    price_increment: float | None = None

    warnings: list[str] = field(default_factory=list)
    model_type: str = ""


# ---------------------------------------------------------------------------
# Revenue and derivative functions
# ---------------------------------------------------------------------------

def revenue(p: float, coeffs: RegressionCoefficients) -> float:
    """R(p) = p · D(p)"""
    return p * float(coeffs.predict(np.array([p]))[0])


def revenue_derivative(p: float, coeffs: RegressionCoefficients) -> float:
    """
    R'(p), the first derivative of revenue w.r.t. price.
    Linear:    R'(p) = a + 2bp
    Quadratic: R'(p) = a + 2bp + 3cp²
    """
    a, b = coeffs.a, coeffs.b
    if coeffs.model_type == "linear":
        return a + 2.0 * b * p
    else:
        c = coeffs.c if coeffs.c is not None else 0.0
        return a + 2.0 * b * p + 3.0 * c * p ** 2


def revenue_second_derivative(p: float, coeffs: RegressionCoefficients) -> float:
    """
    R''(p), the second derivative of revenue w.r.t. price.
    Linear:    R''(p) = 2b
    Quadratic: R''(p) = 2b + 6cp
    """
    if coeffs.model_type == "linear":
        return 2.0 * coeffs.b
    else:
        c = coeffs.c if coeffs.c is not None else 0.0
        return 2.0 * coeffs.b + 6.0 * c * p


def demand_at(p: float, coeffs: RegressionCoefficients) -> float:
    return float(coeffs.predict(np.array([p]))[0])


# ---------------------------------------------------------------------------
# Analytical stationary points (for independent verification)
# ---------------------------------------------------------------------------

def find_analytical_stationary_points(
    coeffs: RegressionCoefficients,
    p_min: float,
    p_max: float,
) -> list[float]:
    """
    Find all real roots of R'(p) = 0 analytically.

    Linear demand: R'(p) = a + 2bp = 0  → p = -a/(2b)   [one root]
    Quadratic demand: R'(p) = a + 2bp + 3cp² = 0  [quadratic in p, up to 2 roots]

    Returns only real roots within or near [p_min, p_max].
    """
    c = coeffs.c if coeffs.model_type == "quadratic" and coeffs.c is not None else 0.0
    return _real_polynomial_roots(coeffs.a, 2.0 * coeffs.b, 3.0 * c)


def _real_polynomial_roots(a: float, b: float, c: float) -> list[float]:
    """Real roots of a + bx + cx² without discarding small curvature.

    Coefficient size alone cannot determine degeneracy: tiny c may be
    influential at large prices. Scale first and use a cancellation-resistant
    quadratic formula (q/c and a/q).
    """
    scale = max(abs(a), abs(b), abs(c))
    if scale == 0:
        return []  # Identically zero: boundaries already cover constant pieces.
    a, b, c = a / scale, b / scale, c / scale
    if c == 0:
        return [-a / b] if b != 0 and math.isfinite(-a / b) else []
    disc = b*b - 4*c*a
    if disc < 0:
        return []
    if disc == 0:
        r = -b/(2*c)
        return [r] if math.isfinite(r) else []
    q = -0.5 * (b + math.copysign(math.sqrt(disc), b))
    roots = [q/c, a/q] if q != 0 else [-b/(2*c)]
    return sorted(set(r for r in roots if math.isfinite(r)))


# ---------------------------------------------------------------------------
# Newton–Raphson implementation
# ---------------------------------------------------------------------------

def newton_raphson(
    coeffs: RegressionCoefficients,
    p0: float,
    p_min: float,
    p_max: float,
    max_iterations: int = 100,
    price_tolerance: float = 1e-6,
    derivative_tolerance: float = 1e-8,
    min_derivative_magnitude: float = 1e-12,
) -> tuple[list[NewtonIteration], str, float | None]:
    """
    Apply Newton–Raphson to find a root of f(p) = R'(p) = 0.

    p_{n+1} = p_n - f(p_n) / f'(p_n)

    Parameters
    ----------
    coeffs           : Fitted demand model coefficients.
    p0               : Initial price estimate.
    p_min, p_max     : Feasible price bounds.
    max_iterations   : Stop after this many iterations.
    price_tolerance  : Convergence when |Δp| < price_tolerance.
    derivative_tolerance : Convergence when |f(p)| < derivative_tolerance.
    min_derivative_magnitude : Abort when |f'(p)| < this value (near-zero denominator).

    Returns
    -------
    iterations : list of NewtonIteration
    status     : ConvergenceStatus string
    p_star     : Converged price (or None)
    """
    iterations: list[NewtonIteration] = []
    p_n = float(p0)
    if not math.isfinite(p_n) or not (p_min <= p_n <= p_max):
        return iterations, ConvergenceStatus.INVALID_START, None
    if max_iterations < 1 or price_tolerance <= 0 or derivative_tolerance <= 0:
        raise ValueError("Iteration limit and convergence tolerances must be positive.")

    for k in range(max_iterations):
        try:
            f_n = revenue_derivative(p_n, coeffs)
            fp_n = revenue_second_derivative(p_n, coeffs)
        except OverflowError:
            return iterations, ConvergenceStatus.FAILED_NONFINITE, None
        if not all(math.isfinite(v) for v in (f_n, fp_n)):
            return iterations, ConvergenceStatus.FAILED_NONFINITE, None

        # A root is valid even if its second derivative is zero; classification
        # is a separate step. Residual convergence must be checked at the price
        # actually returned, never inferred solely from a tiny Newton step.
        if abs(f_n) <= derivative_tolerance:
            iterations.append(NewtonIteration(k, p_n, f_n, fp_n, 0.0, p_n, 0.0,
                                             f"Converged: derivative residual {abs(f_n):.3e}"))
            return iterations, ConvergenceStatus.CONVERGED, p_n
        if abs(fp_n) < min_derivative_magnitude:
            iterations.append(NewtonIteration(k, p_n, f_n, fp_n, float("nan"),
                                             float("nan"), float("nan"),
                                             "Near-zero second derivative; Newton division is undefined."))
            return iterations, ConvergenceStatus.FAILED_ZERO_DERIVATIVE, None

        correction = -f_n / fp_n
        p_next = p_n + correction
        abs_error = abs(p_next - p_n)
        if not all(math.isfinite(v) for v in (correction, p_next, abs_error)):
            return iterations, ConvergenceStatus.FAILED_NONFINITE, None
        try:
            next_residual = abs(revenue_derivative(p_next, coeffs))
        except OverflowError:
            next_residual = float("inf")
        converged = math.isfinite(next_residual) and next_residual <= derivative_tolerance
        note = (f"Converged: residual at next price {next_residual:.3e}" if converged
                else f"Step {abs_error:.3e}; residual at next price {next_residual:.3e}")
        iterations.append(NewtonIteration(k, p_n, f_n, fp_n, correction, p_next, abs_error, note))
        if not (p_min <= p_next <= p_max):
            iterations[-1].convergence_note = "Newton step left the configured feasible interval."
            return iterations, ConvergenceStatus.FAILED_OUT_OF_BOUNDS, None
        if converged:
            return iterations, ConvergenceStatus.CONVERGED, p_next
        if abs_error <= price_tolerance:
            iterations[-1].convergence_note += "; price step is small but derivative residual has not converged."
            return iterations, ConvergenceStatus.FAILED_STAGNATION, None
        p_n = p_next
    return iterations, ConvergenceStatus.FAILED_MAX_ITER, None


# ---------------------------------------------------------------------------
# Candidate evaluation
# ---------------------------------------------------------------------------

def _build_candidate(
    source: str,
    price: float,
    coeffs: RegressionCoefficients,
    p_min: float,
    p_max: float,
    capacity: float | None,
) -> OptimizationCandidate:
    d = demand_at(price, coeffs)
    realized_d = max(0.0, d)
    if capacity is not None:
        realized_d = min(realized_d, capacity)

    rev = price * d
    realized_rev = price * realized_d
    is_feasible = (p_min <= price <= p_max) and d >= 0 and all(
        math.isfinite(v) for v in (price, d, rev, realized_d, realized_rev)
    )

    notes_parts = []
    if d < 0:
        notes_parts.append("Predicted demand is negative at this price.")
        is_feasible = False
    if not (p_min <= price <= p_max):
        notes_parts.append("Price is outside the feasible range.")
        is_feasible = False
    if capacity is not None and d > capacity:
        notes_parts.append(f"Demand ({d:.1f}) exceeds capacity ({capacity:.0f}); capped.")

    return OptimizationCandidate(
        source=source,
        price=price,
        demand=d,
        realized_demand=realized_d,
        revenue=rev,
        realized_revenue=realized_rev,
        is_feasible=is_feasible,
        notes="; ".join(notes_parts) if notes_parts else "OK",
    )


def _demand_zero_crossing(
    coeffs: RegressionCoefficients,
    p_min: float,
    p_max: float,
) -> list[float]:
    """Find prices where D(p) = 0 within [p_min, p_max]."""
    c = coeffs.c if coeffs.model_type == "quadratic" and coeffs.c is not None else 0.0
    return [r for r in _real_polynomial_roots(coeffs.a, coeffs.b, c) if p_min < r < p_max]


def _capacity_transition_prices(
    coeffs: RegressionCoefficients,
    capacity: float,
    p_min: float,
    p_max: float,
) -> list[float]:
    """Find prices where D(p) = capacity (transition point for constrained revenue)."""
    c = coeffs.c if coeffs.model_type == "quadratic" and coeffs.c is not None else 0.0
    return [r for r in _real_polynomial_roots(coeffs.a-capacity, coeffs.b, c) if p_min < r < p_max]


# ---------------------------------------------------------------------------
# Fine scan for verification
# ---------------------------------------------------------------------------

def _scan_revenue(
    coeffs: RegressionCoefficients,
    p_min: float,
    p_max: float,
    capacity: float | None,
    n_points: int = 5000,
) -> tuple[float, float]:
    """
    Scan the revenue function over [p_min, p_max] on a fine grid.
    Returns (best_price, best_realized_revenue).
    Used as independent verification, not as primary optimization.
    """
    prices = np.linspace(p_min, p_max, n_points)
    demands = coeffs.predict(prices)
    realized = np.maximum(0.0, demands)
    if capacity is not None:
        realized = np.minimum(realized, capacity)
    revenues = prices * realized

    idx = int(np.argmax(revenues))
    return float(prices[idx]), float(revenues[idx])


# ---------------------------------------------------------------------------
# Main optimization function
# ---------------------------------------------------------------------------

def run_optimization(
    coeffs: RegressionCoefficients,
    p0: float | None = None,
    p_min: float = 50.0,
    p_max: float = 500.0,
    max_iterations: int = 100,
    price_tolerance: float = 1e-6,
    derivative_tolerance: float = 1e-8,
    capacity: float | None = None,
    price_increment: float | None = None,
) -> OptimizationResult:
    """
    Full revenue optimization pipeline:
    1. Run Newton–Raphson to find stationary candidate.
    2. Collect boundary candidates (p_min, p_max).
    3. Collect demand-zero-crossing candidates.
    4. If capacity given, collect capacity-transition candidates.
    5. Evaluate realized revenue for all candidates.
    6. Select global maximum.
    7. Verify with fine numerical scan.
    8. If price_increment specified, discretize result.
    """
    values = [coeffs.a, coeffs.b, coeffs.c or 0.0, p_min, p_max,
              price_tolerance, derivative_tolerance]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Model coefficients, bounds and tolerances must be finite.")
    if p_min <= 0 or p_max <= p_min:
        raise ValueError("Price bounds must satisfy 0 < minimum < maximum.")
    if max_iterations < 1 or price_tolerance <= 0 or derivative_tolerance <= 0:
        raise ValueError("Iteration limit and tolerances must be positive.")
    if capacity is not None and (not math.isfinite(capacity) or capacity <= 0):
        raise ValueError("Capacity must be finite and positive.")
    if price_increment is not None and (not math.isfinite(price_increment) or price_increment <= 0):
        raise ValueError("Price increment must be finite and positive.")
    warnings: list[str] = []
    result = OptimizationResult(
        scan_agrees=False,
        optimal_classification="No Reliable Recommendation",
        price_min=p_min,
        price_max=p_max,
        p0=p0 if p0 is not None else (p_min + p_max) / 2,
        max_iterations=max_iterations,
        price_tolerance=price_tolerance,
        derivative_tolerance=derivative_tolerance,
        capacity=capacity,
        price_increment=price_increment,
        model_type=coeffs.model_type,
    )

    # --- Determine initial guess
    if p0 is None or not math.isfinite(p0) or not (p_min <= p0 <= p_max):
        p0 = (p_min + p_max) / 2.0
        warnings.append(f"Initial guess adjusted to midpoint: ₹{p0:.2f}")
    result.p0 = p0

    # --- Newton–Raphson
    iterations, nr_status, nr_price = newton_raphson(
        coeffs=coeffs,
        p0=p0,
        p_min=p_min,
        p_max=p_max,
        max_iterations=max_iterations,
        price_tolerance=price_tolerance,
        derivative_tolerance=derivative_tolerance,
    )

    result.iterations = iterations
    result.newton_converged = (nr_status == ConvergenceStatus.CONVERGED)
    result.newton_status = nr_status
    if not result.newton_converged:
        warnings.append(
            f"Newton–Raphson status: {nr_status}. Any optimum reported below comes from "
            "the separately evaluated polynomial, boundary and capacity candidates."
        )

    result.newton_stationary_type = StationaryType.NOT_STATIONARY
    if result.newton_converged and nr_price is not None and math.isfinite(nr_price):
        r2nd = revenue_second_derivative(nr_price, coeffs)
        result.newton_second_derivative = r2nd
        result.newton_stationary_price = nr_price
        result.newton_derivative_residual = abs(revenue_derivative(nr_price, coeffs))

        if r2nd < -1e-10:
            result.newton_stationary_type = StationaryType.MAXIMUM
        elif r2nd > 1e-10:
            result.newton_stationary_type = StationaryType.MINIMUM
            warnings.append(
                f"Newton–Raphson converged to a local minimum at ₹{nr_price:.4f} "
                f"(R''(p) = {r2nd:.4f} > 0). This is not the revenue maximum."
            )
        else:
            result.newton_stationary_type = StationaryType.INCONCLUSIVE
            warnings.append(
                f"Second derivative R''(₹{nr_price:.4f}) ≈ 0. "
                "The second derivative test is inconclusive."
            )

    # --- Analytical verification of stationary points
    analytical_roots = find_analytical_stationary_points(coeffs, p_min, p_max)

    # --- Build candidate list
    candidates: list[OptimizationCandidate] = []

    # Newton candidate (if converged and in range)
    if nr_price is not None and math.isfinite(nr_price) and result.newton_converged:
        cand = _build_candidate("newton", nr_price, coeffs, p_min, p_max, capacity)
        candidates.append(cand)

    # Analytical root candidates
    for r in analytical_roots:
        source = "polynomial_root"
        cand = _build_candidate(source, r, coeffs, p_min, p_max, capacity)
        # Avoid exact duplicates with newton result
        if not any(abs(c.price - r) < 1e-3 and c.source == "newton" for c in candidates):
            candidates.append(cand)

    # Boundary candidates
    candidates.append(_build_candidate("boundary_lower", p_min, coeffs, p_min, p_max, capacity))
    candidates.append(_build_candidate("boundary_upper", p_max, coeffs, p_min, p_max, capacity))

    # Demand zero-crossing (boundary of feasible demand region)
    for p_z in _demand_zero_crossing(coeffs, p_min, p_max):
        candidates.append(_build_candidate("demand_zero_boundary", p_z, coeffs, p_min, p_max, capacity))

    # Capacity transition candidates
    if capacity is not None:
        for p_t in _capacity_transition_prices(coeffs, capacity, p_min, p_max):
            candidates.append(_build_candidate("capacity_transition", p_t, coeffs, p_min, p_max, capacity))

    result.candidates = candidates

    # --- Find best feasible candidate
    feasible = [c for c in candidates if c.is_feasible]
    if not feasible:
        warnings.append("No feasible revenue candidate found. Check price range and demand model.")
        result.warnings = warnings
        return result

    best = max(feasible, key=lambda c: c.realized_revenue)
    if best.realized_revenue <= 0:
        result.warnings = warnings + ["All feasible candidates have zero revenue; no meaningful pricing recommendation is supported."]
        return result

    # A polynomial is monotone between successive derivative roots and kinks.
    # The best grid point therefore neighbors a continuous candidate or bound.
    # This avoids allocating an unbounded array for a very small increment.
    if price_increment is not None:
        increment_decimal = Decimal(str(price_increment))
        lower_tick = int((Decimal(str(p_min))/increment_decimal).to_integral_value(rounding=ROUND_CEILING))
        upper_tick = int((Decimal(str(p_max))/increment_decimal).to_integral_value(rounding=ROUND_FLOOR))
        if lower_tick > upper_tick:
            result.scan_agrees = False
            result.warnings = warnings + ["No permitted price-increment multiple lies inside the configured bounds."]
            return result
        ticks = {lower_tick, upper_tick}
        for candidate in candidates:
            q = Decimal(str(candidate.price)) / increment_decimal
            ticks.update((int(q.to_integral_value(rounding=ROUND_FLOOR)),
                          int(q.to_integral_value(rounding=ROUND_CEILING))))
        disc_cands = [
            _build_candidate("discrete", float(t * increment_decimal), coeffs, p_min, p_max, capacity)
            for t in sorted(ticks) if lower_tick <= t <= upper_tick
        ]
        result.candidates.extend(disc_cands)
        disc_feasible = [c for c in disc_cands if c.is_feasible]
        if not disc_feasible:
            result.scan_agrees = False
            result.warnings = warnings + ["No permitted discrete price has nonnegative predicted demand."]
            return result
        best = max(disc_feasible, key=lambda c: c.realized_revenue)
        warnings.append(f"Evaluated grid neighbors of every continuous candidate using price increment {price_increment:g}.")

    # --- Set optimal result
    result.optimal_price = best.price
    result.optimal_demand = best.demand
    result.optimal_realized_demand = best.realized_demand
    result.optimal_revenue = best.revenue
    result.optimal_realized_revenue = best.realized_revenue
    result.optimal_source = best.source

    # Classification
    src = best.source
    if best.price == p_min and src != "discrete":
        result.optimal_classification = "Lower Boundary Maximum"
    elif best.price == p_max and src != "discrete":
        result.optimal_classification = "Upper Boundary Maximum"
    elif src in ("newton", "polynomial_root"):
        result.optimal_classification = "Interior Maximum"
    elif src == "boundary_lower":
        result.optimal_classification = "Lower Boundary Maximum"
    elif src == "boundary_upper":
        result.optimal_classification = "Upper Boundary Maximum"
    elif src == "capacity_transition":
        result.optimal_classification = "Capacity-Constrained Maximum"
    elif src == "discrete":
        result.optimal_classification = "Discrete Price Optimum"
    else:
        result.optimal_classification = "Boundary Maximum"

    # --- Independent verification via fine scan
    if price_increment is not None:
        count = upper_tick - lower_tick + 1
        scan_ticks = np.unique(np.linspace(lower_tick, upper_tick, min(count, 100_000)).round())
        scan_prices = np.array([float(int(t) * increment_decimal) for t in scan_ticks])
        scan_demands = coeffs.predict(scan_prices)
        scan_realized = np.maximum(0.0, scan_demands)
        if capacity is not None:
            scan_realized = np.minimum(scan_realized, capacity)
        scan_revenues = np.where(scan_demands >= 0, scan_prices * scan_realized, -np.inf)
        i = int(np.argmax(scan_revenues))
        scan_price, scan_rev = float(scan_prices[i]), float(scan_revenues[i])
        if count > 100_000:
            warnings.append("Independent discrete scan samples 100,000 grid points; it is an approximate cross-check.")
    else:
        scan_price, scan_rev = _scan_revenue(coeffs, p_min, p_max, capacity)
    result.scan_max_price = scan_price
    result.scan_max_revenue = scan_rev

    if best.realized_revenue > 0:
        pct_diff = abs(scan_rev - best.realized_revenue) / best.realized_revenue * 100
        result.scan_tolerance_pct = pct_diff
        result.scan_agrees = pct_diff < 2.0  # agree within 2%
        if not result.scan_agrees:
            warnings.append(
                f"Independent scan found a higher revenue at ₹{scan_price:.2f} "
                f"(₹{scan_rev:.2f} vs ₹{best.realized_revenue:.2f}). "
                f"Difference: {pct_diff:.1f}%. Optimization result may be suboptimal."
            )
    else:
        result.scan_agrees = True

    result.warnings = warnings
    return result
