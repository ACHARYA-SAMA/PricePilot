import { useState } from 'react'
import { ArrowRight, Play } from 'lucide-react'
import { useAppState } from '../hooks/useAppState'
import type { Config } from '../lib/analysisState'
import { runOptimization, optimizationParams } from '../services/api'
import { Empty, Formula, Notice, PageTitle, Panel, ResultCards, Warnings } from '../components/UI'
import AnalysisCharts from '../components/analysis/AnalysisCharts'
import { NewtonConvergenceChart } from '../components/analysis/EvidencePlots'
import { fmt, formatINR, sourceLabel } from '../lib/utils'
import type { WorkProps } from '../lib/workflow'
interface Props extends WorkProps { optimize: () => Promise<void> }
const draftFromState = (s: Config) => ({ pMin: String(s.pMin), pMax: String(s.pMax), capacity: s.capacity == null ? '' : String(s.capacity), p0: s.p0 == null ? '' : String(s.p0), priceIncrement: s.priceIncrement == null ? '' : String(s.priceIncrement), maxIterations: String(s.maxIterations), priceTolerance: String(s.priceTolerance), derivativeTolerance: String(s.derivativeTolerance) })
export default function OptimizationPage({ busy, work }: Props) {
  const { state, dispatch } = useAppState()
  const [draft, setDraft] = useState(() => draftFromState(state))
  const [fieldError, setFieldError] = useState('')
  const dirty = JSON.stringify(draft) !== JSON.stringify(draftFromState(state))
  const model = state.regressionResult?.[state.selectedModel]
  const opt = dirty ? null : state.optimizationResult
  const run = () => {
    setFieldError('')
    const config: Config = { pMin: Number(draft.pMin), pMax: Number(draft.pMax), capacity: draft.capacity ? Number(draft.capacity) : null,
      p0: draft.p0 ? Number(draft.p0) : null, priceIncrement: draft.priceIncrement ? Number(draft.priceIncrement) : null,
      maxIterations: Number(draft.maxIterations), priceTolerance: Number(draft.priceTolerance), derivativeTolerance: Number(draft.derivativeTolerance) }
    if (Object.values(config).some(v => v != null && (!Number.isFinite(v) || v <= 0)) || config.pMax <= config.pMin || !Number.isInteger(config.maxIterations) || config.maxIterations > 500) {
      setFieldError('Enter finite positive values, a maximum price greater than the minimum, and an integer iteration limit between 1 and 500.'); return
    }
    if (config.p0 != null && (config.p0 < config.pMin || config.p0 > config.pMax)) { setFieldError('The starting price must be within the feasible price range.'); return }
    void work('Running Newton–Raphson and comparing feasible candidates…', async () => {
      const revision = state.revision + 1
      dispatch({ type: 'SET_CONFIG', payload: config })
      const result = await runOptimization(optimizationParams({ ...state, ...config }))
      dispatch({ type: 'SET_OPTIMIZATION', payload: result, revision })
    })
  }
  return <><PageTitle eyebrow="UNIT II · NEWTON–RAPHSON METHOD" title="Make the revenue case.">Find stationary points, classify them, and compare every valid boundary and capacity transition.</PageTitle>
  {!model ? <Empty text="Fit demand models before running revenue optimization." link="#/regression" label="Open Demand Modeling"/> : <><Panel title="Configure your pricing decision" note={`Active demand model: ${state.selectedModel}`}><p className="equation-text">{model.equation}</p><form onSubmit={e => { e.preventDefault(); run() }} noValidate><div className="form-grid four">{([
    ['pMin', 'Minimum price (₹)', '1'], ['pMax', 'Maximum price (₹)', '1'], ['capacity', 'Event capacity (optional)', '1'], ['p0', 'Starting price (optional)', '1'],
    ['priceIncrement', 'Price increment (optional)', '0.01'], ['maxIterations', 'Maximum iterations', '1'], ['priceTolerance', 'Price tolerance', 'any'], ['derivativeTolerance', 'Derivative residual tolerance', 'any'],
  ] as const).map(([key, label, step]) => <label key={key}>{label}<input type="number" step={step} min="0" value={draft[key]} placeholder={key === 'p0' ? 'Midpoint of range' : key === 'capacity' ? 'No capacity cap' : key === 'priceIncrement' ? 'Continuous price' : undefined} disabled={busy} aria-invalid={!!fieldError} onChange={e => { setDraft(d => ({ ...d, [key]: e.target.value })); setFieldError('') }}/></label>)}</div><p className="muted small">Capacity constrains predicted sales. A price increment requests discrete prices; permitted prices are multiples of that increment within your bounds.</p>{fieldError && <Notice error>{fieldError}</Notice>}<div className="actions spaced"><button className="button" disabled={busy || !model.is_numerically_stable} type="submit"><Play size={15}/>Run optimization</button><a className="text-link" href="#/regression">Change demand model<ArrowRight size={14}/></a></div></form></Panel>
  {dirty && <Notice>Pricing inputs have changed. Run optimization to calculate a result for these settings.</Notice>}
  {opt && <><ResultCards opt={opt}/><Warnings items={opt.warnings}/><AnalysisCharts/><div className="two-col"><Panel title="Newton–Raphson outcome"><span className={`badge ${opt.newton_converged ? 'success' : 'warning'}`}>{opt.newton_converged ? 'Converged' : 'Did not converge'}</span><p>{opt.newton_status}</p><dl className="key-values"><dt>Stationary price</dt><dd>{formatINR(opt.newton_stationary_price, 6)}</dd><dt>Classification</dt><dd>{opt.newton_stationary_type}</dd><dt>Derivative residual at root</dt><dd>{fmt(opt.newton_derivative_residual, 10)}</dd><dt>Second derivative</dt><dd>{fmt(opt.newton_second_derivative, 8)}</dd><dt>Dense scan agreement</dt><dd>{opt.scan_agrees ? 'Agrees within tolerance' : 'Check warnings'}</dd><dt>Scan maximum revenue</dt><dd>{formatINR(opt.scan_max_revenue, 2)}</dd></dl><p className="muted small">A failed Newton run does not invalidate an independently verified boundary maximum. A local minimum is never promoted to a maximum.</p></Panel><Panel title="The iteration being performed"><Formula value="f(p)=R'(p),\qquad p_{n+1}=p_n-\frac{f(p_n)}{f'(p_n)}"/><Formula value={state.selectedModel === 'linear' ? String.raw`R'(p)=a+2bp,\quad R''(p)=2b` : String.raw`R'(p)=a+2bp+3cp^2,\quad R''(p)=2b+6cp`}/><p>For smooth interior candidates, a small derivative residual establishes a root; a negative second derivative identifies a local maximum. Feasible global candidates are compared by realized revenue.</p></Panel></div><NewtonConvergenceChart iterations={opt.iterations}/><Panel title="Actual numerical iterations" note={`${opt.iterations.length} recorded steps`}><div className="table-scroll"><table><thead><tr><th>n</th><th>pₙ</th><th>f(pₙ)</th><th>f′(pₙ)</th><th>Correction</th><th>pₙ₊₁</th><th>|Δp|</th><th>Outcome</th></tr></thead><tbody>{opt.iterations.map(it => <tr key={it.iteration}><td>{it.iteration}</td><td>{fmt(it.price, 8)}</td><td>{fmt(it.f_value, 8)}</td><td>{fmt(it.f_prime, 8)}</td><td>{fmt(it.correction, 8)}</td><td>{fmt(it.next_price, 8)}</td><td>{fmt(it.abs_error, 8)}</td><td className="wide-cell">{it.convergence_note}</td></tr>)}</tbody></table></div>{!opt.iterations.length && <p className="muted">No Newton steps were recorded. See the numerical status above.</p>}</Panel><Panel title="Feasible candidate comparison"><div className="table-scroll"><table><thead><tr><th>Candidate</th><th>Price</th><th>Raw demand</th><th>Realized demand</th><th>Realized revenue</th><th>Status & reasoning</th></tr></thead><tbody>{opt.candidates.map((c, i) => <tr key={i}><td>{sourceLabel(c.source)}</td><td>{formatINR(c.price, 4)}</td><td>{fmt(c.demand, 3)}</td><td>{fmt(c.realized_demand, 3)}</td><td>{formatINR(c.realized_revenue, 2)}</td><td className="wide-cell"><span className={`badge ${c.is_feasible ? 'success' : 'error'}`}>{c.is_feasible ? 'Feasible' : 'Rejected'}</span>{c.notes}</td></tr>)}</tbody></table></div></Panel><div className="actions right"><a className="button" href="#/simulator">Explore pricing scenarios<ArrowRight size={15}/></a></div></>}
  </>}
  </>
}




