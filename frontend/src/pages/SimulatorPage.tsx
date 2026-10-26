import { useEffect, useState } from 'react'
import { evaluateScenarios, errorMessage } from '../services/api'
import { useAppState } from '../hooks/useAppState'
import { Empty, Metric, Notice, PageTitle, Panel } from '../components/UI'
import AnalysisCharts from '../components/analysis/AnalysisCharts'
import { ScenarioComparisonChart } from '../components/analysis/EvidencePlots'
import { fmt, formatINR } from '../lib/utils'
import type { ScenarioResponse } from '../types'
export default function SimulatorPage() {
  const { state, dispatch } = useAppState()
  const [price, setPrice] = useState(String(state.scenarioConfig.currentPrice ?? state.optimizationResult?.optimal_price ?? state.pMin))
  const [baseline, setBaseline] = useState(String(state.scenarioConfig.baselinePrice ?? state.pMin))
  const [comparison, setComparison] = useState(state.scenarioConfig.comparisonPrices.join(', '))
  const [multiplier, setMultiplier] = useState(String(state.scenarioConfig.demandMultiplier))
  const [result, setResult] = useState<{ key: string; data?: ScenarioResponse; error?: string }>({ key: '' })
  const recommendedPrice = state.optimizationResult?.optimal_price ?? undefined
  const key = `${state.revision}|${state.selectedModel}|${price}|${baseline}|${comparison}|${multiplier}|${recommendedPrice}`
  const model = state.regressionResult?.[state.selectedModel]
  const comparisonPrices = comparison.split(',').filter(p => p.trim()).map(Number)
  const values = [Number(price), ...comparisonPrices]
  const invalid = !price.trim() || !baseline.trim() || !multiplier.trim() || [...values, Number(baseline)].some(p => !Number.isFinite(p) || p < state.pMin || p > state.pMax) || values.length > 20 || !Number.isFinite(Number(multiplier)) || Number(multiplier) <= 0 || Number(multiplier) > 10
  useEffect(() => {
    if (!model?.is_numerically_stable || invalid) return
    const controller = new AbortController()
    const timer = setTimeout(() => {
      const extras = comparison.split(',').filter(p => p.trim()).map(Number)
      const prices = Array.from(new Set([Number(price), ...extras, Number(baseline), ...(recommendedPrice == null ? [] : [recommendedPrice])]))
      evaluateScenarios({ observations: state.observations, model_type: state.selectedModel,
        prices, baseline_price: Number(baseline), capacity: state.capacity ?? undefined,
        recommended_price: recommendedPrice, demand_multiplier: Number(multiplier) }, controller.signal)
        .then(data => {
          if (controller.signal.aborted) return
          setResult({ key, data })
          dispatch({ type: 'SET_SCENARIO_CONFIG', payload: { currentPrice: Number(price), baselinePrice: Number(baseline), comparisonPrices: extras, demandMultiplier: Number(multiplier) } })
        }).catch(error => { if (!controller.signal.aborted) setResult({ key, error: errorMessage(error) }) })
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [key, price, baseline, comparison, multiplier, recommendedPrice, state.observations, state.selectedModel, state.capacity, model, invalid, dispatch])
  const current = result.key === key ? result : null
  const point = current?.data?.scenarios[0]
  return <><PageTitle eyebrow="TURN A RECOMMENDATION INTO A DECISION" title="What happens at this price?">Explore predicted sales and revenue before choosing a ticket price.</PageTitle>{!model ? <Empty text="Fit a demand model before simulating ticket prices." link="#/regression" label="Open Demand Modeling"/> : <><Panel title="Scenario controls" note={`${state.selectedModel} model · capacity ${state.capacity ?? 'unconstrained'}`}><div className="form-grid"><label>Ticket price (₹)<input type="number" min={state.pMin} max={state.pMax} step="any" value={price} onChange={e => setPrice(e.target.value)}/></label><label>Baseline price (₹)<input type="number" min={state.pMin} max={state.pMax} step="any" value={baseline} onChange={e => setBaseline(e.target.value)}/></label><label>Additional comparison prices<input value={comparison} placeholder="e.g. 90, 110, 130" onChange={e => setComparison(e.target.value)}/></label><label>Hypothetical demand multiplier<input type="number" min="0.01" max="10" step="0.05" value={multiplier} onChange={e => setMultiplier(e.target.value)} aria-describedby="demand-multiplier-help"/></label></div><p className="muted small" id="demand-multiplier-help">1× uses fitted demand. Other values are hypothetical sensitivity assumptions applied before the capacity cap. They are not observed evidence and do not change the base pricing recommendation.</p><label className="slider-label">Explore the configured price range<input type="range" min={state.pMin} max={state.pMax} step="0.01" value={Number(price) || state.pMin} onChange={e => setPrice(e.target.value)}/><span>{formatINR(state.pMin)}<span>{formatINR(state.pMax)}</span></span></label><p className="muted small">Up to 19 additional comparison prices. Baseline and the base optimum are included automatically. All entered prices must lie within the active optimization range. Valid evaluated scenarios are retained for reports and exports.</p></Panel>
  {invalid && <Notice error>Enter finite ticket prices within {formatINR(state.pMin)}–{formatINR(state.pMax)}, a finite demand multiplier greater than zero and at most 10, and no more than 19 additional comparison prices.</Notice>}{current?.error && <Notice error>{current.error}</Notice>}{!invalid && !current && <p role="status" className="chart-loading">Evaluating the updated price…</p>}
  {point && <>{Number(multiplier) !== 1 && <Notice>Hypothetical sensitivity scenario: demand is scaled by {multiplier}× before capacity constraints. Results are assumptions-based simulations; the original optimization recommendation is unchanged.</Notice>}<div className="metrics four"><Metric label="Predicted demand" value={fmt(point.predicted_demand, 2)} note="Tickets · scenario model output"/><Metric label="Feasible expected sales" value={fmt(point.realized_demand, 2)} note="After demand and capacity constraints"/><Metric label="Predicted realized revenue" value={formatINR(point.realized_revenue, 2)} accent/><Metric label="Revenue vs baseline" value={point.revenue_pct_vs_baseline == null ? 'Undefined' : `${fmt(point.revenue_pct_vs_baseline, 2)}%`} note={formatINR(point.revenue_vs_baseline, 2)}/></div><div className="scenario-reference"><span>Price difference from the base recommendation:</span><strong>{formatINR(point.difference_from_recommended_price, 2)}</strong><span className="muted small">{recommendedPrice == null ? 'Run revenue optimization to establish a base recommendation.' : `Base recommendation: ${formatINR(recommendedPrice, 2)}`}</span></div>{!point.is_feasible && <Notice error>This price has infeasible predicted demand. It cannot support a valid pricing recommendation.</Notice>}{point.notes !== 'OK' && <Notice>{point.notes}</Notice>}<ScenarioComparisonChart scenarios={current.data!.scenarios} currentPrice={Number(price)} baselinePrice={Number(baseline)} recommendedPrice={recommendedPrice}/><Panel title="Scenario comparison"><div className="table-scroll"><table><thead><tr><th>Price</th><th>Predicted demand</th><th>Realized sales</th><th>Realized revenue</th><th>Change from baseline</th><th>Price vs base optimum</th><th>Status</th></tr></thead><tbody>{current?.data?.scenarios.map((p, i) => <tr key={i}><td>{formatINR(p.price, 2)}</td><td>{fmt(p.predicted_demand, 2)}</td><td>{fmt(p.realized_demand, 2)}</td><td>{formatINR(p.realized_revenue, 2)}</td><td>{p.revenue_pct_vs_baseline == null ? 'Undefined' : `${fmt(p.revenue_pct_vs_baseline)}%`}</td><td>{formatINR(p.difference_from_recommended_price, 2)}</td><td><span className={`badge ${p.is_feasible ? 'success' : 'error'}`}>{p.is_feasible ? 'Feasible' : 'Infeasible'}</span><span className="small">{p.notes}</span></td></tr>)}</tbody></table></div></Panel></>}
  {!invalid && <AnalysisCharts selectedPrice={Number(price)} demandMultiplier={Number(multiplier)}/>}<Notice>These are model-based scenarios, not observed results or guarantees. Expected ticket counts are continuous estimates rather than guaranteed integer sales.</Notice></>}</>
}

