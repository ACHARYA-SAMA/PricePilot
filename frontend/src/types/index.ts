// PricePilot — TypeScript type definitions

export interface SampleDatasetMeta {
  id: string
  name: string
  description: string
  warning: string | null
  n_rows: number
  generating_equation: string
  random_seed: number
  noise_distribution: string
  capacity_note: string
}

export interface ObservationRow {
  event_id: string
  ticket_price: number
  tickets_sold: number
  venue_capacity?: number
  event_name?: string
  event_category?: string
  event_date?: string
  location?: string
  promotion_type?: string
  observed_revenue?: number
}

export interface RowIssue {
  row_index: number
  column: string | null
  severity: 'error' | 'warning' | 'info'
  code: string
  message: string
}

export interface ValidationResponse {
  total_rows: number
  valid_rows: number
  rejected_rows: number
  warning_count: number
  duplicate_count: number
  unique_prices: number
  unique_event_ids: number
  price_min: number | null
  price_max: number | null
  price_mean: number | null
  capacity_available: boolean
  sellout_count: number
  has_sellout_warning: boolean
  sellout_warning_message: string | null
  linear_eligible: boolean
  quadratic_eligible: boolean
  quadratic_recommended: boolean
  eligibility_notes: string[]
  column_mapping: Record<string, string>
  issues: RowIssue[]
  valid_rows_data: ObservationRow[]
  rejected_rows_data: Record<string, unknown>[]
}

export interface NormalEqSums {
  n: number
  sum_p: number
  sum_p2: number
  sum_p3: number
  sum_p4: number
  sum_D: number
  sum_pD: number
  sum_p2D: number
  price_mean: number
  price_std: number
}

export interface ModelFit {
  model_type: 'linear' | 'quadratic'
  equation: string
  a: number
  b: number
  c: number | null
  n_samples: number
  n_params: number
  n_predictors: number
  price_min: number
  price_max: number
  price_mean: number
  price_std: number
  sse: number
  sst: number
  mae: number
  rmse: number
  r_squared: number | null
  adjusted_r_squared: number | null
  condition_number: number | null
  is_numerically_stable: boolean
  warnings: string[]
  prices_train: number[]
  demand_actual: number[]
  demand_predicted: number[]
  residuals: number[]
  normal_eq_sums: NormalEqSums | null
  design_matrix_columns: string[]
  normal_equation_matrix: number[][]
  normal_equation_rhs: number[]
}

export interface RegressionResponse {
  linear: ModelFit | null
  quadratic: ModelFit | null
  linear_val: ModelFit | null
  quadratic_val: ModelFit | null
  recommended_model: 'linear' | 'quadratic' | 'none'
  recommendation_reason: string
  has_validation: boolean
  train_size: number
  val_size: number
  warnings: string[]
}

export interface NewtonIteration {
  iteration: number
  price: number
  f_value: number
  f_prime: number
  correction: number | null
  next_price: number | null
  abs_error: number | null
  convergence_note: string
}

export interface OptimizationCandidate {
  source: string
  price: number
  demand: number
  realized_demand: number
  revenue: number
  realized_revenue: number
  is_feasible: boolean
  notes: string
}

export interface OptimizationResponse {
  iterations: NewtonIteration[]
  newton_converged: boolean
  newton_status: string
  newton_stationary_price: number | null
  newton_stationary_type: string
  newton_second_derivative: number | null
  newton_derivative_residual: number | null
  candidates: OptimizationCandidate[]
  optimal_price: number | null
  optimal_demand: number | null
  optimal_realized_demand: number | null
  optimal_revenue: number | null
  optimal_realized_revenue: number | null
  optimal_source: string
  optimal_classification: string
  scan_max_price: number | null
  scan_max_revenue: number | null
  scan_agrees: boolean
  scan_tolerance_pct: number
  price_min: number
  price_max: number
  p0: number
  model_type: string
  warnings: string[]
}

export interface ScenarioPoint {
  price: number
  predicted_demand: number
  realized_demand: number
  predicted_revenue: number
  realized_revenue: number
  revenue_vs_baseline: number | null
  revenue_pct_vs_baseline: number | null
  is_feasible: boolean
  notes: string
  difference_from_recommended_price?: number | null
}

export interface ScenarioResponse {
  scenarios: ScenarioPoint[]
  revenue_curve: {
    prices: number[]
    demand: number[]
    realized_demand: number[]
    revenue: number[]
    realized_revenue: number[]
  }
}

export interface DiagnosticsResponse {
  actual_vs_predicted: { actual: number; predicted: number }[]
  diagonal: { actual: number; predicted: number }[]
  histogram: { left: number; right: number; count: number; label: string }[]
  interpretation: string[]
  warnings: string[]
}

export interface ScenarioConfig {
  currentPrice: number | null
  baselinePrice: number | null
  comparisonPrices: number[]
  demandMultiplier: number
}

export interface SampleDataResponse {
  dataset_id: string
  name: string
  description: string
  warning: string | null
  generating_equation: string
  random_seed: number
  noise_distribution: string
  rows: ObservationRow[]
  column_names: string[]
}

// App state
export interface AnalysisState {
  datasetName: string | null
  datasetId: string | null
  isSynthetic: boolean
  observations: ObservationRow[]
  validationResult: ValidationResponse | null
  regressionResult: RegressionResponse | null
  optimizationResult: OptimizationResponse | null
  selectedModel: 'linear' | 'quadratic'
  pMin: number
  pMax: number
  capacity: number | null
  p0: number | null
  priceIncrement: number | null
  maxIterations: number
  priceTolerance: number
  derivativeTolerance: number
  revision: number
  sourceRows: Record<string, unknown>[]
  originalRows: Record<string, unknown>[]
  groupLabel: string
  scenarioConfig: ScenarioConfig
}
