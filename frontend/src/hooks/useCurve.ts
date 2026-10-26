import { useEffect, useState } from 'react'
import { evaluateScenarios, errorMessage } from '../services/api'
import type { AnalysisState, ScenarioResponse } from '../types'
export function useCurve(state: AnalysisState, demandMultiplier = 1) {
  const [result, setResult] = useState<{ key: string; data?: ScenarioResponse; error?: string }>({ key: '' })
  const model = state.regressionResult?.[state.selectedModel]
  const key = JSON.stringify([state.revision, state.selectedModel, model?.a, model?.b, model?.c, state.pMin, state.pMax, state.capacity, demandMultiplier])
  useEffect(() => {
    if (!model || !model.is_numerically_stable || !(state.pMax > state.pMin)) return
    const controller = new AbortController()
    evaluateScenarios({ observations: state.observations, model_type: state.selectedModel,
      prices: [state.pMin, state.pMax], capacity: state.capacity ?? undefined, demand_multiplier: demandMultiplier }, controller.signal)
      .then(data => setResult({ key, data }))
      .catch(error => { if (!controller.signal.aborted) setResult({ key, error: errorMessage(error) }) })
    return () => controller.abort()
  }, [key, state.observations, state.selectedModel, state.capacity, state.pMin, state.pMax, model, demandMultiplier])
  return result.key === key ? result : { key }
}
