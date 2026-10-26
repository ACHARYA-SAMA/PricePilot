"""
PricePilot — Pydantic Schemas for API request/response validation.
All float fields use finite checks; None is used for undefined values.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PositiveFinite = Annotated[float, Field(gt=0, le=1e12, allow_inf_nan=False)]
NonnegativeFinite = Annotated[float, Field(ge=0, le=1e12, allow_inf_nan=False)]


# ---------------------------------------------------------------------------
# Shared / primitives
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    backend: str


class SampleDatasetMeta(BaseModel):
    id: str
    name: str
    description: str
    warning: str | None
    n_rows: int
    generating_equation: str
    random_seed: int
    noise_distribution: str
    capacity_note: str


class RowIssueOut(BaseModel):
    row_index: int
    column: str | None
    severity: str
    code: str
    message: str


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationResponse(BaseModel):
    total_rows: int
    valid_rows: int
    rejected_rows: int
    warning_count: int
    duplicate_count: int
    unique_prices: int
    unique_event_ids: int
    price_min: float | None
    price_max: float | None
    price_mean: float | None
    capacity_available: bool
    sellout_count: int
    has_sellout_warning: bool
    sellout_warning_message: str | None
    linear_eligible: bool
    quadratic_eligible: bool
    quadratic_recommended: bool
    eligibility_notes: list[str]
    column_mapping: dict[str, str]
    issues: list[RowIssueOut]
    valid_rows_data: list[dict[str, Any]]
    rejected_rows_data: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class ObservationIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)
    event_id: str = Field(min_length=1, max_length=500)
    ticket_price: PositiveFinite
    tickets_sold: NonnegativeFinite
    venue_capacity: PositiveFinite | None = None
    event_name: str | None = Field(default=None, max_length=500)
    event_category: str | None = Field(default=None, max_length=500)
    event_date: str | None = Field(default=None, max_length=100)
    sales_period: str | int | float | None = None
    location: str | None = Field(default=None, max_length=500)
    promotion_type: str | None = Field(default=None, max_length=500)

    @field_validator("ticket_price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("ticket_price must be positive")
        return v

    @field_validator("tickets_sold")
    @classmethod
    def sold_nonneg(cls, v: float) -> float:
        if v < 0 or not v.is_integer():
            raise ValueError("tickets_sold must be a nonnegative integer")
        return v

    @model_validator(mode="after")
    def valid_capacity(self):
        if self.venue_capacity is not None:
            if not self.venue_capacity.is_integer():
                raise ValueError("venue_capacity must be an integer")
            if self.tickets_sold > self.venue_capacity:
                raise ValueError("tickets_sold exceeds venue_capacity")
        return self


class NormalEqSumsOut(BaseModel):
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


class ModelFitOut(BaseModel):
    model_type: str
    equation: str
    a: float
    b: float
    c: float | None
    n_samples: int
    n_params: int
    n_predictors: int
    price_min: float
    price_max: float
    price_mean: float
    price_std: float
    sse: float
    sst: float
    mae: float
    rmse: float
    r_squared: float | None
    adjusted_r_squared: float | None
    condition_number: float | None
    is_numerically_stable: bool
    warnings: list[str]
    prices_train: list[float]
    demand_actual: list[float]
    demand_predicted: list[float]
    residuals: list[float]
    normal_eq_sums: NormalEqSumsOut | None
    design_matrix_columns: list[str]
    normal_equation_matrix: list[list[float]]
    normal_equation_rhs: list[float]


class RegressionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    observations: list[ObservationIn] = Field(min_length=2, max_length=10000)
    quadratic_eligible: bool = True
    quadratic_recommended: bool = True

    @field_validator("observations")
    @classmethod
    def min_observations(cls, v: list) -> list:
        if len(v) < 2:
            raise ValueError("At least 2 observations are required for regression.")
        return v


class RegressionResponse(BaseModel):
    linear: ModelFitOut | None
    quadratic: ModelFitOut | None
    linear_val: ModelFitOut | None
    quadratic_val: ModelFitOut | None
    recommended_model: str
    recommendation_reason: str
    has_validation: bool
    train_size: int
    val_size: int
    warnings: list[str]
    split_strategy: str = 'none'
    train_indices: list[int] = Field(default_factory=list)
    val_indices: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------

class OptimizationRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    observations: list[ObservationIn] = Field(min_length=2, max_length=10000)
    model_type: Literal["linear", "quadratic"] = "linear"
    p0: PositiveFinite | None = None
    p_min: PositiveFinite = 50.0
    p_max: PositiveFinite = 500.0
    max_iterations: int = Field(default=100, ge=1, le=500)
    price_tolerance: float = Field(default=1e-6, gt=0)
    derivative_tolerance: float = Field(default=1e-8, gt=0)
    capacity: PositiveFinite | None = None
    price_increment: PositiveFinite | None = None

    @model_validator(mode="after")
    def p_range_valid(self) -> "OptimizationRequest":
        if self.p_min >= self.p_max:
            raise ValueError("p_min must be less than p_max")
        if self.p0 is not None and not self.p_min <= self.p0 <= self.p_max:
            raise ValueError("p0 must be within the feasible price range")
        return self


class AnalysisRequest(RegressionRequest):
    """Reproducible report/export input: identical data and configuration to UI."""
    model_type: Literal['linear', 'quadratic'] | None = None
    p_min: PositiveFinite | None = None
    p_max: PositiveFinite | None = None
    capacity: PositiveFinite | None = None
    p0: PositiveFinite | None = None
    price_increment: PositiveFinite | None = None
    max_iterations: int = Field(default=100, ge=1, le=500)
    price_tolerance: PositiveFinite = 1e-6
    derivative_tolerance: PositiveFinite = 1e-8
    dataset_name: str = Field(default='Uploaded dataset', max_length=500)
    is_synthetic: bool = False
    scenario_prices: list[PositiveFinite] | None = Field(default=None, max_length=1000)
    baseline_price: PositiveFinite | None = None
    demand_multiplier: float = Field(default=1.0, gt=0, le=10)

    @model_validator(mode='after')
    def bounds_valid(self):
        if self.p_min is not None and self.p_max is not None and self.p_min >= self.p_max:
            raise ValueError('p_min must be less than p_max')
        return self


class CleanedDataRequest(BaseModel):
    observations: list[ObservationIn] = Field(min_length=1, max_length=10000)


class DiagnosticsRequest(RegressionRequest):
    model_type: Literal['linear', 'quadratic'] = 'linear'


class NewtonIterationOut(BaseModel):
    iteration: int
    price: float
    f_value: float
    f_prime: float
    correction: float | None
    next_price: float | None
    abs_error: float | None
    convergence_note: str


class OptimizationCandidateOut(BaseModel):
    source: str
    price: float
    demand: float
    realized_demand: float
    revenue: float
    realized_revenue: float
    is_feasible: bool
    notes: str


class OptimizationResponse(BaseModel):
    iterations: list[NewtonIterationOut]
    newton_converged: bool
    newton_status: str
    newton_stationary_price: float | None
    newton_stationary_type: str
    newton_second_derivative: float | None
    newton_derivative_residual: float | None = None
    candidates: list[OptimizationCandidateOut]
    optimal_price: float | None
    optimal_demand: float | None
    optimal_realized_demand: float | None
    optimal_revenue: float | None
    optimal_realized_revenue: float | None
    optimal_source: str
    optimal_classification: str
    scan_max_price: float | None
    scan_max_revenue: float | None
    scan_agrees: bool
    scan_tolerance_pct: float
    price_min: float
    price_max: float
    p0: float
    model_type: str
    warnings: list[str]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class ScenarioRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    observations: list[ObservationIn] = Field(min_length=2, max_length=10000)
    model_type: Literal["linear", "quadratic"] = "linear"
    prices: list[PositiveFinite] = Field(min_length=1, max_length=1000)
    capacity: PositiveFinite | None = None
    baseline_price: PositiveFinite | None = None
    recommended_price: PositiveFinite | None = None
    demand_multiplier: float = Field(default=1.0, gt=0, le=10)


class ScenarioPointOut(BaseModel):
    price: float
    predicted_demand: float
    realized_demand: float
    predicted_revenue: float
    realized_revenue: float
    revenue_vs_baseline: float | None
    revenue_pct_vs_baseline: float | None
    is_feasible: bool
    notes: str
    difference_from_recommended_price: float | None = None


class ScenarioResponse(BaseModel):
    scenarios: list[ScenarioPointOut]
    revenue_curve: dict[str, list[float]]


# ---------------------------------------------------------------------------
# Sample dataset response
# ---------------------------------------------------------------------------

class SampleDataResponse(BaseModel):
    dataset_id: str
    name: str
    description: str
    warning: str | None
    generating_equation: str
    random_seed: int
    noise_distribution: str
    rows: list[dict[str, Any]]
    column_names: list[str]
