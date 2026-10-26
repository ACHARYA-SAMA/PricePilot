import axios from 'axios'
import type { AnalysisState, DiagnosticsResponse, ObservationRow, OptimizationResponse, RegressionResponse, SampleDataResponse, SampleDatasetMeta, ScenarioResponse, ValidationResponse } from '../types'

const api = axios.create({ baseURL: '/api/v1', timeout: 60000 })
export const checkHealth = () => api.get('/health').then(r => r.data)
export const listSampleDatasets = (): Promise<SampleDatasetMeta[]> => api.get('/sample-datasets').then(r => r.data)
export const getSampleDataset = (id: string): Promise<SampleDataResponse> => api.get(`/sample-datasets/${id}`).then(r => r.data)
export const validateDataset = (file: File, mapping?: Record<string, string>): Promise<ValidationResponse> => {
  const form = new FormData()
  form.append('file', file)
  if (mapping) form.append('column_mapping', JSON.stringify(mapping))
  return api.post('/datasets/validate', form).then(r => r.data)
}
export const fitRegression = (observations: ObservationRow[], quadraticEligible: boolean, quadraticRecommended: boolean): Promise<RegressionResponse> =>
  api.post('/regression/fit', { observations, quadratic_eligible: quadraticEligible, quadratic_recommended: quadraticRecommended }).then(r => r.data)
export interface OptimizationParams {
  observations: ObservationRow[]; model_type: 'linear' | 'quadratic'; p0?: number; p_min: number; p_max: number;
  max_iterations?: number; price_tolerance?: number; derivative_tolerance?: number; capacity?: number; price_increment?: number;
}
export const runOptimization = (params: OptimizationParams): Promise<OptimizationResponse> => api.post('/optimization/run', params).then(r => r.data)
export const optimizationParams = (s: AnalysisState): OptimizationParams => ({ observations: s.observations, model_type: s.selectedModel,
  p_min: s.pMin, p_max: s.pMax, p0: s.p0 ?? undefined, capacity: s.capacity ?? undefined,
  price_increment: s.priceIncrement ?? undefined, max_iterations: s.maxIterations,
  price_tolerance: s.priceTolerance, derivative_tolerance: s.derivativeTolerance })
export const sampleOptimizationParams = (s: AnalysisState, model: 'linear' | 'quadratic'): OptimizationParams =>
  optimizationParams({ ...s, selectedModel: model })
export interface ScenarioParams { observations: ObservationRow[]; model_type: 'linear' | 'quadratic'; prices: number[]; capacity?: number; baseline_price?: number; demand_multiplier?: number; recommended_price?: number }
export const evaluateScenarios = (params: ScenarioParams, signal?: AbortSignal): Promise<ScenarioResponse> => api.post('/scenarios/evaluate', params, { signal }).then(r => r.data)
export const evaluateDiagnostics = (observations: ObservationRow[], model_type: 'linear' | 'quadratic', signal?: AbortSignal): Promise<DiagnosticsResponse> =>
  api.post('/diagnostics/evaluate', { observations, model_type }, { signal }).then(r => r.data)
export const exportPayload = (state: AnalysisState) => ({ ...optimizationParams(state),
  quadratic_eligible: state.validationResult?.quadratic_eligible ?? false,
  quadratic_recommended: state.validationResult?.quadratic_recommended ?? false,
  dataset_name: state.datasetName, is_synthetic: state.isSynthetic,
  scenario_prices: Array.from(new Set([state.scenarioConfig.currentPrice ?? state.optimizationResult?.optimal_price ?? state.pMin,
    ...state.scenarioConfig.comparisonPrices, state.scenarioConfig.baselinePrice ?? state.pMin,
    ...(state.optimizationResult?.optimal_price == null ? [] : [state.optimizationResult.optimal_price])])),
  baseline_price: state.scenarioConfig.baselinePrice ?? state.pMin,
  demand_multiplier: state.scenarioConfig.demandMultiplier })
export function saveBlob(data: BlobPart, filename: string, type: string) {
  const url = URL.createObjectURL(new Blob([data], { type }))
  const a = document.createElement('a'); a.href = url; a.download = filename
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export async function downloadExport(kind: 'pdf' | 'predictions-csv' | 'residuals-csv' | 'scenarios-csv' | 'analysis-json' | 'cleaned-csv' | 'chart-svg' | 'chart-png', state: AnalysisState) {
  const path = kind === 'pdf' ? '/reports/pdf' : `/exports/${kind}`
  let response
  try {
    response = await api.post(path, exportPayload(state), { responseType: 'blob' })
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
      try {
        const payload = JSON.parse(await error.response.data.text())
        if (typeof payload.detail === 'string') throw new Error(payload.detail)
        if (Array.isArray(payload.detail)) throw new Error(payload.detail.map((i: { msg: string }) => i.msg).join('; '))
      } catch (parsedError) { if (parsedError instanceof Error && !(parsedError instanceof SyntaxError)) throw parsedError }
    }
    throw error
  }
  const extension = kind === 'pdf' ? 'pdf' : kind === 'analysis-json' ? 'json' : kind === 'chart-svg' ? 'svg' : kind === 'chart-png' ? 'png' : 'csv'
  saveBlob(response.data, `pricepilot_${kind}.${extension}`, String(response.headers['content-type'] ?? 'application/octet-stream'))
}
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(i => `${i.loc?.slice(1).join('.') ?? 'Input'}: ${i.msg}`).join('; ')
    if (error.code === 'ECONNABORTED') return 'The calculation timed out. Try again with fewer observations.'
    return 'Cannot reach the calculation service. Start the Python backend on port 8000 and retry.'
  }
  return error instanceof Error ? error.message : 'The operation could not be completed. Please retry.'
}
export function rowsToCSV(rows: Record<string, unknown>[], secureText = false): string {
  const columns = Array.from(new Set(rows.flatMap(row => Object.keys(row)))).filter(c => !c.startsWith('_') && c !== 'observed_revenue')
  const cell = (value: unknown) => {
    let text = value == null ? '' : String(value)
    if (secureText && typeof value === 'string' && /^[=+\-@]/.test(text.trimStart())) text = `'${text}`
    return `"${text.replaceAll('"', '""')}"`
  }
  return [columns.map(cell).join(','), ...rows.map(row => columns.map(col => cell(row[col])).join(','))].join('\r\n')
}
export const validateRows = (rows: Record<string, unknown>[]) => validateDataset(new File([rowsToCSV(rows)], 'edited-dataset.csv', { type: 'text/csv' }))
export const sourceRowsFromValidation = (validation: ValidationResponse): Record<string, unknown>[] => {
  const rows = [...validation.valid_rows_data, ...validation.rejected_rows_data] as Record<string, unknown>[]
  return rows.sort((a, b) => Number(a._source_row ?? Number.MAX_SAFE_INTEGER) - Number(b._source_row ?? Number.MAX_SAFE_INTEGER))
}
export default api
