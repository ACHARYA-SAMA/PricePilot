"""
PricePilot — Regression Module

Implements least-squares curve fitting for:
  1. Linear demand model:    D(p) = a + bp
  2. Quadratic demand model: D(p) = a + bp + cp²

Mathematical approach:
  - Build design matrix X (n × k)
  - Form normal equations: XᵀXβ = Xᵀy
  - Solve using NumPy's lstsq (QR/SVD based) for numerical stability
  - DO NOT directly invert XᵀX (ill-conditioned for clustered prices)
  - Scale prices internally for conditioning; recover original-basis coefficients

Units:
  - p: ticket price (₹)
  - D: tickets sold (integer count)
  - Coefficients reported in original price units

Course focus: Unit V, least-squares curve fitting and regression.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class RegressionCoefficients:
    """Fitted polynomial coefficients in original price units."""
    a: float          # intercept
    b: float          # linear coefficient
    c: float | None   # quadratic coefficient (None for linear model)
    model_type: Literal["linear", "quadratic"]

    def predict(self, prices: np.ndarray) -> np.ndarray:
        """Predict demand at given prices using fitted coefficients."""
        if self.model_type == "linear":
            return self.a + self.b * prices
        else:
            c = self.c if self.c is not None else 0.0
            return self.a + self.b * prices + c * prices ** 2

    @property
    def equation_str(self) -> str:
        b_sign = "+" if self.b >= 0 else "-"
        if self.model_type == "linear":
            return f"D(p) = {self.a:.4f} {b_sign} {abs(self.b):.6f}p"
        else:
            c = self.c if self.c is not None else 0.0
            c_sign = "+" if c >= 0 else "-"
            return (
                f"D(p) = {self.a:.4f} {b_sign} {abs(self.b):.6f}p "
                f"{c_sign} {abs(c):.8f}p²"
            )


@dataclass
class NormalEquationSums:
    """Intermediate sums used in the normal equations — for academic display."""
    n: int
    sum_p: float
    sum_p2: float
    sum_p3: float
    sum_p4: float
    sum_D: float
    sum_pD: float
    sum_p2D: float
    price_mean: float
    price_std: float


@dataclass
class ModelFitResult:
    """Result of fitting one demand model."""
    model_type: Literal["linear", "quadratic"]
    coefficients: RegressionCoefficients
    n_samples: int
    n_params: int          # including intercept
    n_predictors: int      # k, excluding intercept (1 for linear, 2 for quadratic)
    price_min: float
    price_max: float
    price_mean: float
    price_std: float

    # Predictions and residuals on training data
    prices_train: list[float] = field(default_factory=list)
    demand_actual: list[float] = field(default_factory=list)
    demand_predicted: list[float] = field(default_factory=list)
    residuals: list[float] = field(default_factory=list)

    # Diagnostics
    sse: float = 0.0
    sst: float = 0.0
    mae: float = 0.0
    rmse: float = 0.0
    r_squared: float = 0.0
    adjusted_r_squared: float | None = None

    # Stability
    condition_number: float = 0.0
    is_numerically_stable: bool = True
    warnings: list[str] = field(default_factory=list)

    # Normal equation sums (for display)
    normal_eq_sums: NormalEquationSums | None = None

    # Design matrix details
    design_matrix_columns: list[str] = field(default_factory=list)
    normal_equation_matrix: list[list[float]] = field(default_factory=list)
    normal_equation_rhs: list[float] = field(default_factory=list)


@dataclass
class ModelComparisonResult:
    """Result of comparing linear vs. quadratic models."""
    linear: ModelFitResult | None
    quadratic: ModelFitResult | None

    # Validation set results (when train/val split is used)
    linear_val: ModelFitResult | None = None
    quadratic_val: ModelFitResult | None = None

    recommended_model: Literal["linear", "quadratic", "none"] = "none"
    recommendation_reason: str = ""
    has_validation: bool = False
    train_size: int = 0
    val_size: int = 0
    warnings: list[str] = field(default_factory=list)
    split_strategy: str = "none"
    train_indices: list[int] = field(default_factory=list)
    val_indices: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_arrays(prices, demand, n_params: int) -> tuple[np.ndarray, np.ndarray]:
    prices = np.asarray(prices, dtype=float)
    demand = np.asarray(demand, dtype=float)
    if prices.ndim != 1 or demand.ndim != 1 or len(prices) != len(demand):
        raise ValueError("Prices and demand must be one-dimensional arrays of equal length.")
    if len(prices) < n_params:
        raise ValueError(f"Regression requires at least {n_params} observations.")
    if not np.all(np.isfinite(prices)) or not np.all(np.isfinite(demand)):
        raise ValueError("Prices and demand must contain only finite values.")
    if len(np.unique(prices)) < n_params:
        raise ValueError(f"Regression requires at least {n_params} distinct ticket prices.")
    # Above this bound raw fourth-power normal-equation sums may overflow.
    if np.max(np.abs(prices)) > 1e60 or np.max(np.abs(demand)) > 1e60:
        raise ValueError("Input magnitudes exceed the supported numerical range (1e60).")
    return prices, demand


def _check_original_basis_precision(original: np.ndarray, scaled: np.ndarray) -> None:
    """Reject catastrophic cancellation after converting coefficients back.

    A well-conditioned scaled solve does not guarantee that its original price
    basis is safe to evaluate. Every consumer uses that basis; accepting a fit
    whose original-basis predictions disagree would corrupt optimization too.
    """
    tolerance = 1e-6 * (1.0 + float(np.max(np.abs(scaled))))
    if not np.all(np.isfinite(original)) or np.max(np.abs(original-scaled)) > tolerance:
        raise ValueError(
            "Converting coefficients to the original price units loses numerical precision. "
            "Rescale the price units or use a wider, representative observed price range."
        )

def _compute_diagnostics(
    y_actual: np.ndarray,
    y_pred: np.ndarray,
    n_predictors: int,
) -> dict:
    """Compute regression diagnostics from actual and predicted arrays."""
    residuals = y_actual - y_pred
    n = len(y_actual)

    sse = float(np.sum(residuals ** 2))
    mean_y = float(np.mean(y_actual))
    sst = float(np.sum((y_actual - mean_y) ** 2))

    if sst == 0.0:
        # Zero variance in actual demand — R² is undefined
        r2 = float("nan")
        adj_r2 = None
    else:
        r2 = 1.0 - sse / sst
        denom_adj = n - n_predictors - 1
        if denom_adj <= 0:
            adj_r2 = None
        else:
            adj_r2 = float(1.0 - (1.0 - r2) * (n - 1) / denom_adj)

    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "sse": sse,
        "sst": sst,
        "mae": mae,
        "rmse": rmse,
        "r_squared": r2,
        "adjusted_r_squared": adj_r2,
        "residuals": residuals.tolist(),
        "mean_y": mean_y,
    }


def _build_normal_eq_sums(prices: np.ndarray, demand: np.ndarray) -> NormalEquationSums:
    """Compute the sums needed for the normal equations — used for academic display."""
    p, D = prices, demand
    return NormalEquationSums(
        n=len(p),
        sum_p=float(np.sum(p)),
        sum_p2=float(np.sum(p ** 2)),
        sum_p3=float(np.sum(p ** 3)),
        sum_p4=float(np.sum(p ** 4)),
        sum_D=float(np.sum(D)),
        sum_pD=float(np.sum(p * D)),
        sum_p2D=float(np.sum(p ** 2 * D)),
        price_mean=float(np.mean(p)),
        price_std=float(np.std(p, ddof=1)) if len(p) > 1 else 0.0,
    )


# ---------------------------------------------------------------------------
# Linear regression
# ---------------------------------------------------------------------------

def fit_linear(
    prices: np.ndarray,
    demand: np.ndarray,
) -> ModelFitResult:
    """
    Fit linear demand model D(p) = a + bp via least squares.

    Design matrix X = [[1, p₁], [1, p₂], ..., [1, pₙ]]
    Solve: XᵀXβ = Xᵀy  (normal equations)
    Implementation: numpy.linalg.lstsq (QR/SVD, numerically stable)

    Internal scaling:
        t = (p - μ_p) / σ_p
    Coefficients converted back to original price basis before returning.
    """
    prices, demand = _validate_arrays(prices, demand, 2)
    n = len(prices)
    if n < 2:
        raise ValueError(f"Linear regression requires at least 2 observations; got {n}.")

    # Price scaling for numerical conditioning
    mu_p = np.mean(prices)
    sigma_p = np.std(prices, ddof=1)
    if sigma_p == 0.0 or not np.isfinite(sigma_p):
        sigma_p = 1.0  # fallback: no scale needed when all prices identical

    t = (prices - mu_p) / sigma_p

    # Build design matrix in scaled space: D = α + βt
    X = np.column_stack([np.ones(n), t])

    # Solve normal equations via lstsq
    alpha_beta, residuals_lstsq, rank, sv = np.linalg.lstsq(X, demand, rcond=None)
    alpha, beta_t = alpha_beta

    # Check rank
    warnings: list[str] = []
    is_stable = True
    cond = float(np.max(sv) / np.min(sv)) if np.min(sv) > 0 else float("inf")

    if rank < 2:
        warnings.append("Design matrix is rank-deficient. Regression results are unreliable.")
        is_stable = False
    if cond > 1e8:
        warnings.append(f"Design matrix is ill-conditioned (condition number ≈ {cond:.2e}).")
        is_stable = False

    # Convert scaled coefficients back to original price basis
    # D = α + β*(p - μ)/σ = (α - β*μ/σ) + (β/σ)*p
    a_orig = float(alpha - beta_t * mu_p / sigma_p)
    b_orig = float(beta_t / sigma_p)

    coeffs = RegressionCoefficients(a=a_orig, b=b_orig, c=None, model_type="linear")

    # Predictions on training data
    y_pred = coeffs.predict(prices)
    _check_original_basis_precision(y_pred, X @ alpha_beta)

    # Check for nonfinite predictions
    if not np.all(np.isfinite(y_pred)):
        warnings.append("Some predicted values are not finite.")
        is_stable = False

    # Diagnostics
    diag = _compute_diagnostics(demand, y_pred, n_predictors=1)

    # Normal equation sums for display
    ne_sums = _build_normal_eq_sums(prices, demand)

    # Normal equation matrices (in original basis, for display)
    XᵀX = np.array([
        [n,               float(np.sum(prices))],
        [float(np.sum(prices)), float(np.sum(prices ** 2))],
    ])
    Xᵀy = np.array([float(np.sum(demand)), float(np.sum(prices * demand))])

    return ModelFitResult(
        model_type="linear",
        coefficients=coeffs,
        n_samples=n,
        n_params=2,
        n_predictors=1,
        price_min=float(np.min(prices)),
        price_max=float(np.max(prices)),
        price_mean=float(np.mean(prices)),
        price_std=float(sigma_p),
        prices_train=prices.tolist(),
        demand_actual=demand.tolist(),
        demand_predicted=y_pred.tolist(),
        residuals=diag["residuals"],
        sse=diag["sse"],
        sst=diag["sst"],
        mae=diag["mae"],
        rmse=diag["rmse"],
        r_squared=diag["r_squared"],
        adjusted_r_squared=diag["adjusted_r_squared"],
        condition_number=cond,
        is_numerically_stable=is_stable,
        warnings=warnings,
        normal_eq_sums=ne_sums,
        design_matrix_columns=["1 (intercept)", "p (price)"],
        normal_equation_matrix=XᵀX.tolist(),
        normal_equation_rhs=Xᵀy.tolist(),
    )


# ---------------------------------------------------------------------------
# Quadratic regression
# ---------------------------------------------------------------------------

def fit_quadratic(
    prices: np.ndarray,
    demand: np.ndarray,
) -> ModelFitResult:
    """
    Fit quadratic demand model D(p) = a + bp + cp² via least squares.

    Design matrix X = [[1, p₁, p₁²], ..., [1, pₙ, pₙ²]]
    Solve: XᵀXβ = Xᵀy  (3×3 normal equations)
    Implementation: numpy.linalg.lstsq

    Internal scaling:
        t = (p - μ_p) / σ_p
        D = α + βt + γt²
    Coefficients converted back to original price basis.

    Transformation:
        t = (p - μ)/σ
        p = σt + μ
        D = α + β*((p-μ)/σ) + γ*((p-μ)/σ)²
          = α + (β/σ)*p - (β*μ/σ) + γ*(p² - 2μp + μ²)/σ²
          = [α - β*μ/σ + γ*μ²/σ²]
            + [β/σ - 2γ*μ/σ²] * p
            + [γ/σ²] * p²
    So:
        a = α - β*μ/σ + γ*μ²/σ²
        b = β/σ - 2γ*μ/σ²
        c = γ/σ²
    """
    prices, demand = _validate_arrays(prices, demand, 3)
    n = len(prices)
    if n < 3:
        raise ValueError(f"Quadratic regression requires at least 3 observations; got {n}.")

    mu_p = np.mean(prices)
    sigma_p = np.std(prices, ddof=1)
    if sigma_p == 0.0 or not np.isfinite(sigma_p):
        sigma_p = 1.0

    t = (prices - mu_p) / sigma_p

    # Design matrix in scaled space
    X = np.column_stack([np.ones(n), t, t ** 2])

    alpha_beta_gamma, _, rank, sv = np.linalg.lstsq(X, demand, rcond=None)
    alpha, beta_t, gamma_t = alpha_beta_gamma

    warnings: list[str] = []
    is_stable = True
    cond = float(np.max(sv) / np.min(sv)) if np.min(sv) > 0 else float("inf")

    if rank < 3:
        warnings.append(
            f"Design matrix is rank-{rank} (expected 3). "
            "Quadratic fit may be unreliable — check for insufficient price variation."
        )
        is_stable = False
    if cond > 1e8:
        warnings.append(f"Design matrix is ill-conditioned (condition number ≈ {cond:.2e}).")
        is_stable = False

    # Convert scaled → original basis
    mu, sigma = mu_p, sigma_p
    a_orig = float(alpha - beta_t * mu / sigma + gamma_t * mu ** 2 / sigma ** 2)
    b_orig = float(beta_t / sigma - 2 * gamma_t * mu / sigma ** 2)
    c_orig = float(gamma_t / sigma ** 2)

    # Sanity check
    if not all(math.isfinite(v) for v in [a_orig, b_orig, c_orig]):
        warnings.append("Regression produced non-finite coefficients.")
        is_stable = False

    coeffs = RegressionCoefficients(a=a_orig, b=b_orig, c=c_orig, model_type="quadratic")
    y_pred = coeffs.predict(prices)
    _check_original_basis_precision(y_pred, X @ alpha_beta_gamma)

    if not np.all(np.isfinite(y_pred)):
        warnings.append("Some predicted demand values are not finite.")
        is_stable = False

    diag = _compute_diagnostics(demand, y_pred, n_predictors=2)

    # Normal equation sums for display
    ne_sums = _build_normal_eq_sums(prices, demand)

    # Full 3×3 normal equation matrix (original basis, for academic display)
    p = prices
    XᵀX = np.array([
        [n,             float(np.sum(p)),     float(np.sum(p**2))],
        [float(np.sum(p)),   float(np.sum(p**2)),  float(np.sum(p**3))],
        [float(np.sum(p**2)), float(np.sum(p**3)), float(np.sum(p**4))],
    ])
    Xᵀy = np.array([
        float(np.sum(demand)),
        float(np.sum(p * demand)),
        float(np.sum(p**2 * demand)),
    ])

    return ModelFitResult(
        model_type="quadratic",
        coefficients=coeffs,
        n_samples=n,
        n_params=3,
        n_predictors=2,
        price_min=float(np.min(prices)),
        price_max=float(np.max(prices)),
        price_mean=float(np.mean(prices)),
        price_std=float(sigma_p),
        prices_train=prices.tolist(),
        demand_actual=demand.tolist(),
        demand_predicted=y_pred.tolist(),
        residuals=diag["residuals"],
        sse=diag["sse"],
        sst=diag["sst"],
        mae=diag["mae"],
        rmse=diag["rmse"],
        r_squared=diag["r_squared"],
        adjusted_r_squared=diag["adjusted_r_squared"],
        condition_number=cond,
        is_numerically_stable=is_stable,
        warnings=warnings,
        normal_eq_sums=ne_sums,
        design_matrix_columns=["1 (intercept)", "p (price)", "p² (price squared)"],
        normal_equation_matrix=XᵀX.tolist(),
        normal_equation_rhs=Xᵀy.tolist(),
    )


# ---------------------------------------------------------------------------
# Model comparison with train/validation split
# ---------------------------------------------------------------------------

def compare_models(
    prices: np.ndarray,
    demand: np.ndarray,
    quadratic_eligible: bool = True,
    quadratic_recommended: bool = True,
    random_seed: int = 42,
    *,
    groups: list[str] | None = None,
) -> ModelComparisonResult:
    """
    Fit and compare linear vs. quadratic demand models.

    When data is sufficient (n ≥ 15), performs an 80/20 train/val split
    using a reproducible random seed. Repeated event IDs use entire-group
    holdout when at least five independent event groups exist. Held-out metrics use training-only
    coefficients. Returned active fits are refitted on all observations.

    Selection logic:
    1. If quadratic is not eligible → select linear if eligible.
    2. If validation data exists:
       - Prefer quadratic if val_RMSE(quad) < val_RMSE(linear) * 0.95 (5% threshold)
         AND quadratic is recommended AND demand shape is plausible.
    3. Otherwise prefer linear (simpler model).
    4. If both models have similar performance → prefer linear.
    """
    prices, demand = _validate_arrays(prices, demand, 2)
    warnings: list[str] = []
    n = len(prices)

    if groups is not None and (len(groups) != n or any(not isinstance(g, str) for g in groups)):
        raise ValueError("Groups must contain one event-ID string per observation.")
    unique_groups = list(dict.fromkeys(groups)) if groups is not None else []
    repeated_groups = groups is not None and len(unique_groups) < n

    has_validation = n >= 15
    train_size = n
    val_size = 0
    linear_result = quadratic_result = None
    linear_val = quadratic_val = None
    split_strategy = "none"
    train_idx = np.arange(n)
    val_idx = np.array([], dtype=int)

    if repeated_groups and len(unique_groups) < 5:
        has_validation = False
        warnings.append(
            f"Only {len(unique_groups)} independent event groups are available; at least 5 "
            "are required for a grouped holdout. Validation is unavailable; final fits use all rows."
        )

    if has_validation:
        rng = np.random.default_rng(random_seed)
        if repeated_groups:
            group_order = rng.permutation(len(unique_groups))
            split_idx = int(0.8 * len(unique_groups))
            training_groups = {unique_groups[i] for i in group_order[:split_idx]}
            train_idx = np.array([i for i, g in enumerate(groups) if g in training_groups])
            val_idx = np.array([i for i, g in enumerate(groups) if g not in training_groups])
            split_strategy = "random_groups"
        else:
            indices = rng.permutation(n)
            split_idx = int(0.8 * n)
            train_idx = indices[:split_idx]
            val_idx = indices[split_idx:]
            split_strategy = "random_rows"

        # A split with inadequate independent prices is not presented as
        # reliable validation. Check feature rank without using holdout demand.
        rank_needed = 3 if quadratic_eligible and len(np.unique(prices)) >= 3 else 2
        for idx in (train_idx, val_idx):
            rank_ok = len(idx) >= rank_needed and len(np.unique(prices[idx])) >= rank_needed
            if rank_ok:
                partition = prices[idx]
                scaled = (partition-np.mean(partition))/np.std(partition)
                design = np.column_stack([scaled**power for power in range(rank_needed)])
                rank_ok = np.linalg.matrix_rank(design) == rank_needed and np.linalg.cond(design) <= 1e8
            if not rank_ok:
                has_validation = False
                warnings.append(
                    "The seeded holdout lacks sufficient independent price variation in "
                    "one partition. Validation is unavailable; final fits use all rows."
                )
                break

    if has_validation:

        p_train = prices[train_idx]
        d_train = demand[train_idx]
        p_val = prices[val_idx]
        d_val = demand[val_idx]

        train_size = len(train_idx)
        val_size = len(val_idx)
    else:
        split_strategy = "none"
        train_idx = np.arange(n)
        val_idx = np.array([], dtype=int)
        p_train = prices
        d_train = demand
        p_val = np.array([])
        d_val = np.array([])
        if n < 15:
            warnings.append(
                f"Dataset has only {n} observations. "
                "A train/validation split cannot be performed reliably. "
                "All metrics are training-set metrics."
            )

    # --- Fit linear
    try:
        linear_result = fit_linear(p_train, d_train)
        if has_validation and len(p_val) > 0:
            y_pred_val = linear_result.coefficients.predict(p_val)
            diag_val = _compute_diagnostics(d_val, y_pred_val, n_predictors=1)
            linear_val = ModelFitResult(
                model_type="linear",
                coefficients=linear_result.coefficients,
                n_samples=len(p_val),
                n_params=2, n_predictors=1,
                price_min=float(np.min(p_val)), price_max=float(np.max(p_val)),
                price_mean=float(np.mean(p_val)), price_std=float(np.std(p_val, ddof=1)),
                prices_train=p_val.tolist(),
                demand_actual=d_val.tolist(),
                demand_predicted=y_pred_val.tolist(),
                residuals=diag_val["residuals"],
                sse=diag_val["sse"], sst=diag_val["sst"],
                mae=diag_val["mae"], rmse=diag_val["rmse"],
                r_squared=diag_val["r_squared"],
                adjusted_r_squared=diag_val["adjusted_r_squared"],
            )
    except Exception as exc:
        warnings.append(f"Linear model fitting failed: {exc}")

    # --- Fit quadratic
    if quadratic_eligible:
        try:
            quadratic_result = fit_quadratic(p_train, d_train)
            if has_validation and len(p_val) > 0:
                y_pred_val = quadratic_result.coefficients.predict(p_val)
                diag_val = _compute_diagnostics(d_val, y_pred_val, n_predictors=2)
                quadratic_val = ModelFitResult(
                    model_type="quadratic",
                    coefficients=quadratic_result.coefficients,
                    n_samples=len(p_val),
                    n_params=3, n_predictors=2,
                    price_min=float(np.min(p_val)), price_max=float(np.max(p_val)),
                    price_mean=float(np.mean(p_val)), price_std=float(np.std(p_val, ddof=1)),
                    prices_train=p_val.tolist(),
                    demand_actual=d_val.tolist(),
                    demand_predicted=y_pred_val.tolist(),
                    residuals=diag_val["residuals"],
                    sse=diag_val["sse"], sst=diag_val["sst"],
                    mae=diag_val["mae"], rmse=diag_val["rmse"],
                    r_squared=diag_val["r_squared"],
                    adjusted_r_squared=diag_val["adjusted_r_squared"],
                )
        except Exception as exc:
            warnings.append(f"Quadratic model fitting failed: {exc}")

    # --- Selection logic
    recommended = "none"
    reason = ""

    if linear_result is None and quadratic_result is None:
        reason = "Both models failed to fit. Check data quality."
    elif linear_result is None:
        recommended = "quadratic"
        reason = "Linear model fitting failed; quadratic selected as the only available model."
    elif quadratic_result is None:
        recommended = "linear"
        reason = (
            "Quadratic model is not available (insufficient data or fitting failure). "
            "Linear model selected."
        )
    else:
        # Both fitted — compare
        lin_rmse = linear_result.rmse
        quad_rmse = quadratic_result.rmse
        adj_r2_lin = linear_result.adjusted_r_squared
        adj_r2_quad = quadratic_result.adjusted_r_squared

        # Check quadratic demand shape over observed range
        quad_plausible = _check_demand_shape(quadratic_result.coefficients, linear_result.price_min, linear_result.price_max)

        if has_validation and linear_val is not None and quadratic_val is not None:
            val_rmse_lin = linear_val.rmse
            val_rmse_quad = quadratic_val.rmse

            if not quadratic_recommended:
                recommended = "linear"
                reason = (
                    f"Quadratic model is not well-supported by the data ({linear_result.n_samples} training rows). "
                    "Linear model selected for reliability."
                )
            elif val_rmse_quad < val_rmse_lin * 0.95 and quad_plausible:
                recommended = "quadratic"
                reason = (
                    f"Quadratic demand was selected because it produced lower validation RMSE "
                    f"({val_rmse_quad:.2f} vs {val_rmse_lin:.2f} for linear) "
                    "while maintaining economically plausible demand behavior."
                )
            else:
                recommended = "linear"
                reason = (
                    f"Linear model was selected. Validation RMSE: linear={val_rmse_lin:.2f}, "
                    f"quadratic={val_rmse_quad:.2f}. "
                    "The quadratic model does not provide meaningful improvement in generalization."
                )
        else:
            # No validation — use training metrics, prefer simpler model
            if not quadratic_recommended or not quad_plausible:
                recommended = "linear"
                reason = (
                    "Linear model selected (insufficient data for reliable quadratic comparison, "
                    "or quadratic demand shape is implausible)."
                )
            elif adj_r2_quad is not None and adj_r2_lin is not None and adj_r2_quad > adj_r2_lin + 0.05:
                recommended = "quadratic"
                reason = (
                    f"Quadratic model selected based on higher adjusted R² "
                    f"({adj_r2_quad:.4f} vs {adj_r2_lin:.4f}). "
                    "No validation split available."
                )
            else:
                recommended = "linear"
                reason = (
                    "Linear model selected (simpler; no meaningful improvement from quadratic "
                    "based on adjusted R²)."
                )

    # Keep held-out predictions untouched: refitting happens only after selection.
    # Every active fit now matches the model fitted by optimization and simulation.
    if has_validation:
        if linear_result is not None:
            linear_result = fit_linear(prices, demand)
        if quadratic_result is not None:
            quadratic_result = fit_quadratic(prices, demand)
        warnings.append(
            "Active models are refitted on all valid observations. Validation metrics "
            f"come from separate training-only fits using a seeded random 80/20 "
            f"{'event-group' if repeated_groups else 'row'} split; "
            "they do not validate the final refit against independent real-world data."
        )

    for model in (linear_result, quadratic_result):
        if model is not None:
            if not _check_demand_shape(model.coefficients, model.price_min, model.price_max):
                model.warnings.append("Demand does not decrease over the entire observed price range; pricing recommendations are exploratory.")
            if model.rmse > 0 and model.r_squared < 0.5:
                model.warnings.append("Weak in-sample fit: R² is below 0.5; predictions are exploratory.")

    if recommended != "none":
        selected = linear_result if recommended == "linear" else quadratic_result
        if selected is None or not selected.is_numerically_stable:
            recommended = "none"
            reason = "No numerically stable model is available for a reliable recommendation."

    return ModelComparisonResult(
        linear=linear_result,
        quadratic=quadratic_result,
        linear_val=linear_val,
        quadratic_val=quadratic_val,
        recommended_model=recommended,
        recommendation_reason=reason,
        has_validation=has_validation,
        train_size=train_size,
        val_size=val_size,
        warnings=warnings,
        split_strategy=split_strategy,
        train_indices=train_idx.tolist(),
        val_indices=val_idx.tolist(),
    )


def _check_demand_shape(coeffs: RegressionCoefficients, p_min: float, p_max: float) -> bool:
    """
    For quadratic demand D(p) = a + bp + cp²,
    check that D'(p) = b + 2cp < 0 over all of [p_min, p_max]
    (demand should generally decrease with price).
    Returns True if plausible (mostly decreasing).
    """
    if coeffs.model_type == "linear":
        return coeffs.b < 0

    c = coeffs.c if coeffs.c is not None else 0.0
    derivatives = coeffs.b + 2 * c * np.array([p_min, p_max])
    return bool(np.all(derivatives < 0))
