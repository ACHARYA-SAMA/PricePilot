import { useEffect, useState } from 'react'
import { evaluateDiagnostics, errorMessage } from '../services/api'
import type { AnalysisState, DiagnosticsResponse } from '../types'
export function useDiagnostics(state: AnalysisState) {
  const [result, setResult] = useState<{ key: string; data?: DiagnosticsResponse; error?: string }>({ key: '' })
  const model = state.regressionResult?.[state.selectedModel]
  const key = JSON.stringify([state.revision, state.selectedModel, model?.a, model?.b, model?.c])
  useEffect(() => {
    if (!model?.is_numerically_stable) return
    const controller = new AbortController()
    evaluateDiagnostics(state.observations, state.selectedModel, controller.signal)
      .then(data => setResult({ key, data }))
      .catch(error => { if (!controller.signal.aborted) setResult({ key, error: errorMessage(error) }) })
    return () => controller.abort()
  }, [key, state.observations, state.selectedModel, model])
  return result.key === key ? result : { key }
}
