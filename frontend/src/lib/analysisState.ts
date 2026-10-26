import type { AnalysisState, ObservationRow, OptimizationResponse, RegressionResponse, ScenarioConfig, ValidationResponse } from '../types'

export const initialState: AnalysisState = {
  datasetName: null, datasetId: null, isSynthetic: false, observations: [], sourceRows: [], originalRows: [],
  validationResult: null, regressionResult: null, optimizationResult: null,
  selectedModel: 'linear', pMin: 50, pMax: 500, capacity: null, p0: null,
  priceIncrement: null, maxIterations: 50, priceTolerance: 1e-6, derivativeTolerance: 1e-6,
  revision: 0, groupLabel: 'All observations',
  scenarioConfig: { currentPrice: null, baselinePrice: null, comparisonPrices: [], demandMultiplier: 1 },
}
export type Config = Pick<AnalysisState, 'pMin' | 'pMax' | 'capacity' | 'p0' | 'priceIncrement' | 'maxIterations' | 'priceTolerance' | 'derivativeTolerance'>
export type Action =
  | { type: 'SET_DATASET'; payload: { name: string; id: string | null; isSynthetic: boolean; observations: ObservationRow[]; validation: ValidationResponse; sourceRows: Record<string, unknown>[]; originalRows?: Record<string, unknown>[]; groupLabel?: string } }
  | { type: 'SET_REGRESSION'; payload: RegressionResponse; revision: number }
  | { type: 'SET_OPTIMIZATION'; payload: OptimizationResponse; revision: number }
  | { type: 'SET_SELECTED_MODEL'; payload: 'linear' | 'quadratic' }
  | { type: 'SET_CONFIG'; payload: Config }
  | { type: 'SET_SCENARIO_CONFIG'; payload: ScenarioConfig }
  | { type: 'RESET' }
export function reducer(state: AnalysisState, action: Action): AnalysisState {
  switch (action.type) {
    case 'SET_DATASET': return { ...initialState, datasetName: action.payload.name, datasetId: action.payload.id,
      isSynthetic: action.payload.isSynthetic, observations: action.payload.observations,
      sourceRows: action.payload.sourceRows, originalRows: action.payload.originalRows ?? action.payload.sourceRows, validationResult: action.payload.validation,
      pMin: action.payload.validation.price_min ?? 50, pMax: action.payload.validation.price_max ?? 500,
      groupLabel: action.payload.groupLabel ?? 'All observations', revision: state.revision + 1 }
    case 'SET_REGRESSION': return action.revision !== state.revision ? state : {
      ...state, regressionResult: action.payload, optimizationResult: null, scenarioConfig: initialState.scenarioConfig,
      selectedModel: action.payload.recommended_model === 'none' ? state.selectedModel : action.payload.recommended_model }
    case 'SET_OPTIMIZATION': return action.revision !== state.revision ? state : { ...state, optimizationResult: action.payload }
    case 'SET_SELECTED_MODEL': return { ...state, selectedModel: action.payload, optimizationResult: null, scenarioConfig: initialState.scenarioConfig, revision: state.revision + 1 }
    case 'SET_CONFIG': return { ...state, ...action.payload, optimizationResult: null, scenarioConfig: initialState.scenarioConfig, revision: state.revision + 1 }
    case 'SET_SCENARIO_CONFIG': return { ...state, scenarioConfig: action.payload }
    case 'RESET': return { ...initialState, revision: state.revision + 1 }
  }
}

