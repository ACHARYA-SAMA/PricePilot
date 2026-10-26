"""
PricePilot — API Routes

/api/v1/health
/api/v1/sample-datasets
/api/v1/sample-datasets/{id}
/api/v1/datasets/validate
/api/v1/regression/fit
/api/v1/optimization/run
/api/v1/scenarios/evaluate
/api/v1/reports/pdf
/api/v1/exports/*
"""

from __future__ import annotations

import io
import json
import math
import csv as csv_module
from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.core.data_generation import SAMPLE_DATASETS, get_sample_dataframe
from app.core.diagnostics import compute_diagnostics
from app.core.optimization import run_optimization
from app.core.regression import (
    RegressionCoefficients,
    compare_models,
    fit_linear,
    fit_quadratic,
)
from app.core.simulation import build_revenue_curve, evaluate_scenarios, scenario_coefficients
from app.core.validation import validate_csv_bytes, MAX_FILE_SIZE_BYTES
from app.services.analysis import build_analysis, json_finite
from app.schemas.schemas import (
    AnalysisRequest,
    CleanedDataRequest,
    DiagnosticsRequest,
    HealthResponse,
    ModelFitOut,
    NormalEqSumsOut,
    NewtonIterationOut,
    OptimizationCandidateOut,
    OptimizationRequest,
    OptimizationResponse,
    RegressionRequest,
    RegressionResponse,
    SampleDataResponse,
    SampleDatasetMeta,
    ScenarioPointOut,
    ScenarioRequest,
    ScenarioResponse,
    ValidationResponse,
    RowIssueOut,
)

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v: float | None) -> float | None:
    """Return None for NaN/Inf values that cannot be serialized as JSON."""
    if v is None:
        return None
    if not math.isfinite(v):
        return None
    return v


def _required_finite(value: float) -> float:
    """Reject invalid numerical evidence instead of replacing it with zero."""
    if not math.isfinite(value):
        raise HTTPException(status_code=422, detail='The numerical calculation produced a non-finite value. Review the price range and model stability.')
    return value


def _model_fit_to_out(fit) -> ModelFitOut | None:
    if fit is None:
        return None
    ne = fit.normal_eq_sums
    ne_out = None
    if ne is not None:
        ne_out = NormalEqSumsOut(
            n=ne.n, sum_p=ne.sum_p, sum_p2=ne.sum_p2,
            sum_p3=ne.sum_p3, sum_p4=ne.sum_p4,
            sum_D=ne.sum_D, sum_pD=ne.sum_pD, sum_p2D=ne.sum_p2D,
            price_mean=ne.price_mean, price_std=ne.price_std,
        )
    return ModelFitOut(
        model_type=fit.model_type,
        equation=fit.coefficients.equation_str,
        a=fit.coefficients.a,
        b=fit.coefficients.b,
        c=fit.coefficients.c,
        n_samples=fit.n_samples,
        n_params=fit.n_params,
        n_predictors=fit.n_predictors,
        price_min=fit.price_min,
        price_max=fit.price_max,
        price_mean=fit.price_mean,
        price_std=fit.price_std,
        sse=fit.sse,
        sst=fit.sst,
        mae=fit.mae,
        rmse=fit.rmse,
        r_squared=_safe_float(fit.r_squared),
        adjusted_r_squared=_safe_float(fit.adjusted_r_squared),
        condition_number=_safe_float(fit.condition_number),
        is_numerically_stable=fit.is_numerically_stable,
        warnings=fit.warnings,
        prices_train=fit.prices_train,
        demand_actual=fit.demand_actual,
        demand_predicted=fit.demand_predicted,
        residuals=fit.residuals,
        normal_eq_sums=ne_out,
        design_matrix_columns=fit.design_matrix_columns,
        normal_equation_matrix=fit.normal_equation_matrix,
        normal_equation_rhs=fit.normal_equation_rhs,
    )


def _extract_arrays(observations, model_type: str) -> tuple[np.ndarray, np.ndarray]:
    """Extract already-validated observations without rounding or imputing."""
    prices = np.array([o.ticket_price for o in observations], dtype=float)
    demand = np.array([o.tickets_sold for o in observations], dtype=float)
    return prices, demand


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        backend="PricePilot FastAPI",
    )


# ---------------------------------------------------------------------------
# Sample datasets
# ---------------------------------------------------------------------------

@router.get("/sample-datasets", response_model=list[SampleDatasetMeta])
async def list_sample_datasets():
    return [
        SampleDatasetMeta(
            id=ds.id,
            name=ds.name,
            description=ds.description,
            warning=ds.warning,
            n_rows=ds.n_rows,
            generating_equation=ds.generating_equation,
            random_seed=ds.random_seed,
            noise_distribution=ds.noise_distribution,
            capacity_note=ds.capacity_note,
        )
        for ds in SAMPLE_DATASETS
    ]


@router.get("/sample-datasets/{dataset_id}", response_model=SampleDataResponse)
async def get_sample_dataset(dataset_id: str):
    ds_info = next((ds for ds in SAMPLE_DATASETS if ds.id == dataset_id), None)
    if ds_info is None:
        raise HTTPException(status_code=404, detail=f"Sample dataset '{dataset_id}' not found.")

    df = get_sample_dataframe(dataset_id)

    # Remove internal columns
    display_cols = [c for c in df.columns if not c.startswith("_")]
    df = df[display_cols]

    # Replace NaN with None for JSON serialization
    rows = json.loads(df.to_json(orient="records"))

    return SampleDataResponse(
        dataset_id=dataset_id,
        name=ds_info.name,
        description=ds_info.description,
        warning=ds_info.warning,
        generating_equation=ds_info.generating_equation,
        random_seed=ds_info.random_seed,
        noise_distribution=ds_info.noise_distribution,
        rows=rows,
        column_names=display_cols,
    )


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------

@router.post("/datasets/validate", response_model=ValidationResponse)
async def validate_dataset(file: UploadFile = File(...), column_mapping: str | None = Form(default=None)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    explicit_mapping = {}
    if column_mapping:
        try:
            explicit_mapping = json.loads(column_mapping)
            if not isinstance(explicit_mapping, dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in explicit_mapping.items()):
                raise ValueError('Column mapping must be a JSON object of source to target headers.')
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise ValueError('File exceeds 5 MB upload limit.')
            raw = list(csv_module.reader(io.StringIO(content.decode('utf-8-sig'))))
            if not raw:
                raise ValueError('CSV is empty.')
            if set(explicit_mapping) - set(raw[0]):
                raise ValueError('A mapped source column does not exist in the CSV.')
            new_headers = [explicit_mapping.get(h,h) for h in raw[0]]
            if len(set(new_headers)) != len(new_headers):
                raise ValueError('Mapping creates duplicate headers. Select each field once.')
            output = io.StringIO()
            writer = csv_module.writer(output)
            writer.writerow(new_headers)
            writer.writerows(raw[1:])
            content = output.getvalue().encode('utf-8')
        except (ValueError, UnicodeDecodeError, csv_module.Error) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = validate_csv_bytes(content, file.filename)
    result.column_mapping.update(explicit_mapping)

    # Prepare row data for response (replace NaN with None)
    def df_to_rows(df: pd.DataFrame | None) -> list[dict]:
        if df is None or df.empty:
            return []
        return json.loads(df.to_json(orient="records"))

    issues_out = [
        RowIssueOut(
            row_index=i.row_index,
            column=i.column,
            severity=i.severity.value,
            code=i.code,
            message=i.message,
        )
        for i in result.issues
    ]

    return ValidationResponse(
        total_rows=result.total_rows,
        valid_rows=result.valid_rows,
        rejected_rows=result.rejected_rows,
        warning_count=result.warning_count,
        duplicate_count=result.duplicate_count,
        unique_prices=result.unique_prices,
        unique_event_ids=result.unique_event_ids,
        price_min=result.price_min,
        price_max=result.price_max,
        price_mean=result.price_mean,
        capacity_available=result.capacity_available,
        sellout_count=result.sellout_count,
        has_sellout_warning=result.has_sellout_warning,
        sellout_warning_message=result.sellout_warning_message,
        linear_eligible=result.linear_eligible,
        quadratic_eligible=result.quadratic_eligible,
        quadratic_recommended=result.quadratic_recommended,
        eligibility_notes=result.eligibility_notes,
        column_mapping=result.column_mapping,
        issues=issues_out,
        valid_rows_data=df_to_rows(result.valid_dataframe),
        rejected_rows_data=df_to_rows(result.rejected_dataframe),
    )


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

@router.post("/regression/fit", response_model=RegressionResponse)
@router.post("/regression/compare", response_model=RegressionResponse)
async def fit_regression(request: RegressionRequest):
    prices, demand = _extract_arrays(request.observations, "linear")

    try:
        comparison = compare_models(
            prices=prices,
            demand=demand,
            quadratic_eligible=request.quadratic_eligible,
            quadratic_recommended=request.quadratic_recommended,
            groups=[o.event_id for o in request.observations],
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Regression failed: {exc}")

    return RegressionResponse(
        linear=_model_fit_to_out(comparison.linear),
        quadratic=_model_fit_to_out(comparison.quadratic),
        linear_val=_model_fit_to_out(comparison.linear_val),
        quadratic_val=_model_fit_to_out(comparison.quadratic_val),
        recommended_model=comparison.recommended_model,
        recommendation_reason=comparison.recommendation_reason,
        has_validation=comparison.has_validation,
        train_size=comparison.train_size,
        val_size=comparison.val_size,
        warnings=comparison.warnings,
        split_strategy=comparison.split_strategy,
        train_indices=comparison.train_indices,
        val_indices=comparison.val_indices,
    )


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------

@router.post("/optimization/run", response_model=OptimizationResponse)
async def run_optimization_endpoint(request: OptimizationRequest):
    prices, demand = _extract_arrays(request.observations, request.model_type)

    # Fit the requested model
    try:
        if request.model_type == "linear":
            fit = fit_linear(prices, demand)
        else:
            fit = fit_quadratic(prices, demand)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Model fitting failed: {exc}")

    coeffs = fit.coefficients
    if not fit.is_numerically_stable:
        raise HTTPException(status_code=422, detail='Selected model is rank deficient or numerically unstable.')

    try:
        opt = run_optimization(
            coeffs=coeffs,
            p0=request.p0,
            p_min=request.p_min,
            p_max=request.p_max,
            max_iterations=request.max_iterations,
            price_tolerance=request.price_tolerance,
            derivative_tolerance=request.derivative_tolerance,
            capacity=request.capacity,
            price_increment=request.price_increment,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Optimization failed: {exc}")

    def safe_iter(it):
        return NewtonIterationOut(
            iteration=it.iteration,
            price=_required_finite(it.price),
            f_value=_required_finite(it.f_value),
            f_prime=_required_finite(it.f_prime),
            correction=_safe_float(it.correction),
            next_price=_safe_float(it.next_price),
            abs_error=_safe_float(it.abs_error),
            convergence_note=it.convergence_note,
        )

    return OptimizationResponse(
        iterations=[safe_iter(it) for it in opt.iterations],
        newton_converged=opt.newton_converged,
        newton_status=opt.newton_status,
        newton_stationary_price=_safe_float(opt.newton_stationary_price),
        newton_stationary_type=opt.newton_stationary_type,
        newton_second_derivative=_safe_float(opt.newton_second_derivative),
        newton_derivative_residual=_safe_float(getattr(opt, 'newton_derivative_residual', None)),
        candidates=[
            OptimizationCandidateOut(
                source=c.source,
                price=c.price,
                demand=_required_finite(c.demand),
                realized_demand=c.realized_demand,
                revenue=_required_finite(c.revenue),
                realized_revenue=c.realized_revenue,
                is_feasible=c.is_feasible,
                notes=c.notes,
            )
            for c in opt.candidates
        ],
        optimal_price=_safe_float(opt.optimal_price),
        optimal_demand=_safe_float(opt.optimal_demand),
        optimal_realized_demand=_safe_float(opt.optimal_realized_demand),
        optimal_revenue=_safe_float(opt.optimal_revenue),
        optimal_realized_revenue=_safe_float(opt.optimal_realized_revenue),
        optimal_source=opt.optimal_source,
        optimal_classification=opt.optimal_classification,
        scan_max_price=_safe_float(opt.scan_max_price),
        scan_max_revenue=_safe_float(opt.scan_max_revenue),
        scan_agrees=opt.scan_agrees,
        scan_tolerance_pct=_required_finite(opt.scan_tolerance_pct),
        price_min=opt.price_min,
        price_max=opt.price_max,
        p0=opt.p0,
        model_type=opt.model_type,
        warnings=opt.warnings,
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

@router.post("/scenarios/evaluate", response_model=ScenarioResponse)
async def evaluate_scenarios_endpoint(request: ScenarioRequest):
    prices, demand = _extract_arrays(request.observations, request.model_type)

    try:
        if request.model_type == "linear":
            fit = fit_linear(prices, demand)
        else:
            fit = fit_quadratic(prices, demand)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Model fitting failed: {exc}")

    scenarios = evaluate_scenarios(
        prices=request.prices,
        coeffs=fit.coefficients,
        capacity=request.capacity,
        baseline_price=request.baseline_price,
        demand_multiplier=request.demand_multiplier,
        recommended_price=request.recommended_price,
    )

    p_min = float(min(request.prices))
    p_max = float(max(request.prices))
    curve = build_revenue_curve(scenario_coefficients(fit.coefficients, request.demand_multiplier), p_min, p_max, request.capacity)

    return ScenarioResponse(
        scenarios=[
            ScenarioPointOut(
                price=s.price,
                predicted_demand=_required_finite(s.predicted_demand),
                realized_demand=s.realized_demand,
                predicted_revenue=_required_finite(s.predicted_revenue),
                realized_revenue=s.realized_revenue,
                revenue_vs_baseline=_safe_float(s.revenue_vs_baseline),
                revenue_pct_vs_baseline=_safe_float(s.revenue_pct_vs_baseline),
                is_feasible=s.is_feasible,
                notes=s.notes,
                difference_from_recommended_price=s.difference_from_recommended_price,
            )
            for s in scenarios
        ],
        revenue_curve=curve,
    )


@router.post('/diagnostics/evaluate')
def evaluate_diagnostics(request: DiagnosticsRequest):
    """Extended residual evidence, including backend-generated chart bins."""
    prices, demand = _extract_arrays(request.observations, request.model_type)
    try:
        fit = fit_linear(prices, demand) if request.model_type == 'linear' else fit_quadratic(prices, demand)
        return json_finite(asdict(compute_diagnostics(fit)))
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Reproducible reports and exports
# ---------------------------------------------------------------------------


def _analysis_or_error(request: AnalysisRequest):
    try:
        return build_analysis(request)
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _download(content: bytes | str, media_type: str, filename: str):
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


def _csv_response(headers: list[str], rows: list[list], filename: str):
    output = io.StringIO()
    writer = csv_module.writer(output)
    writer.writerow(headers)
    for row in rows:
        # Neutralize formula text while preserving actual numeric values.
        writer.writerow(["'" + v if isinstance(v,str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in row])
    return _download(output.getvalue(), 'text/csv; charset=utf-8', filename)


@router.post('/reports/pdf')
def generate_pdf_report(request: AnalysisRequest):
    from app.core.reporting import generate_analysis_pdf
    analysis = _analysis_or_error(request)
    return _download(generate_analysis_pdf(analysis), 'application/pdf', 'pricepilot_report.pdf')


@router.post('/exports/predictions-csv')
def export_predictions(request: AnalysisRequest):
    analysis = _analysis_or_error(request)
    p = np.array([o.ticket_price for o in request.observations])
    d = np.array([o.tickets_sold for o in request.observations])
    headers = ['ticket_price', 'actual_demand', 'observed_revenue']
    fits = [m for m in (analysis.comparison.linear, analysis.comparison.quadratic) if m is not None]
    for model in fits:
        headers += [model.model_type + '_predicted', model.model_type + '_residual']
    predictions = [model.coefficients.predict(p) for model in fits]
    rows = []
    for i in range(len(p)):
        row = [p[i], d[i], p[i]*d[i]]
        for values in predictions:
            row += [values[i], d[i]-values[i]]
        rows.append(row)
    return _csv_response(headers, rows, 'pricepilot_predictions.csv')


@router.post('/exports/cleaned-csv')
def export_cleaned(request: CleanedDataRequest):
    records = [o.model_dump(exclude_none=True) for o in request.observations]
    headers = list(dict.fromkeys(k for row in records for k in row)) + ['observed_revenue']
    rows = [[row.get(k, '') if k != 'observed_revenue' else row['ticket_price']*row['tickets_sold'] for k in headers] for row in records]
    return _csv_response(headers, rows, 'pricepilot_cleaned.csv')


@router.post('/exports/analysis-json')
def export_analysis_json(request: AnalysisRequest):
    analysis = _analysis_or_error(request)
    return _download(json.dumps(analysis.to_dict(), indent=2, allow_nan=False),
                     'application/json', 'pricepilot_analysis.json')


@router.post('/exports/chart-svg')
def export_chart_svg(request: AnalysisRequest):
    from app.core.reporting import render_analysis_chart
    analysis = _analysis_or_error(request)
    return _download(render_analysis_chart(analysis, 'svg'), 'image/svg+xml', 'pricepilot_curves.svg')


@router.post('/exports/chart-png')
def export_chart_png(request: AnalysisRequest):
    from app.core.reporting import render_analysis_chart
    return _download(render_analysis_chart(_analysis_or_error(request), 'png'), 'image/png', 'pricepilot_curves.png')


@router.post('/exports/residuals-csv')
def export_residuals(request: AnalysisRequest):
    response = export_predictions(request)
    response.headers['Content-Disposition'] = 'attachment; filename=pricepilot_residuals.csv'
    return response


@router.post('/exports/scenarios-csv')
def export_scenarios(request: AnalysisRequest):
    analysis = _analysis_or_error(request)
    records = [asdict(point) for point in analysis.scenarios]
    headers = list(records[0])
    return _csv_response(headers, [[record[key] for key in headers] for record in records], 'pricepilot_scenarios.csv')
