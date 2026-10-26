import { useEffect, useRef, useState } from 'react'
import { Menu, X, Database, Upload, ArrowUpRight, ChartNoAxesCombined, LayoutDashboard, SlidersHorizontal, FlaskConical, ScanLine, Sigma, FileDown, Info, ArrowRight } from 'lucide-react'
import { AppProvider } from './lib/store'
import { useAppState } from './hooks/useAppState'
import { reducer } from './lib/analysisState'
import type { SampleDatasetMeta, ValidationResponse } from './types'
import { errorMessage, fitRegression, getSampleDataset, listSampleDatasets, optimizationParams, runOptimization, sampleOptimizationParams, sourceRowsFromValidation, validateDataset, validateRows } from './services/api'
import DashboardPage from './pages/DashboardPage'
import DatasetPage from './pages/DatasetPage'
import ModelingPage from './pages/ModelingPage'
import OptimizationPage from './pages/OptimizationPage'
import SimulatorPage from './pages/SimulatorPage'
import DiagnosticsPage from './pages/DiagnosticsPage'
import WalkthroughPage from './pages/WalkthroughPage'
import ReportsPage from './pages/ReportsPage'
import AboutPage from './pages/AboutPage'
import { Notice } from './components/UI'
import type { Work } from './lib/workflow'

const pages = [
  ['overview', 'Overview', LayoutDashboard], ['dataset', 'Dataset Studio', Database],
  ['regression', 'Demand Modeling', ChartNoAxesCombined], ['optimization', 'Revenue Optimization', SlidersHorizontal],
  ['simulator', 'Scenario Simulator', FlaskConical], ['diagnostics', 'Model Diagnostics', ScanLine],
  ['walkthrough', 'Math Walkthrough', Sigma], ['reports', 'Reports & Exports', FileDown], ['about', 'About the Project', Info],
] as const
function currentRoute() { const path = location.hash.replace(/^#\/?/, '').split('?')[0]; return pages.some(p => p[0] === path) ? path : 'overview' }
function Application() {
  const { state, dispatch } = useAppState()
  const [route, setRoute] = useState(currentRoute)
  const [menuOpen, setMenuOpen] = useState(false)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [samples, setSamples] = useState<SampleDatasetMeta[]>([])
  const [sampleError, setSampleError] = useState('')
  const [sourceFile, setSourceFile] = useState<File | null>(null)
  const [mobile, setMobile] = useState(() => matchMedia('(max-width: 760px)').matches)
  const lock = useRef(false)
  const uploadRef = useRef<HTMLInputElement>(null)
  const mainRef = useRef<HTMLElement>(null)
  const sidebarRef = useRef<HTMLElement>(null)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    const media = matchMedia('(max-width: 760px)')
    const changed = () => setMobile(media.matches)
    media.addEventListener('change', changed)
    return () => media.removeEventListener('change', changed)
  }, [])
  useEffect(() => {
    if (!menuOpen || !mobile) return
    const controls = () => Array.from(sidebarRef.current?.querySelectorAll<HTMLElement>('a[href],button:not([disabled])') ?? [])
    sidebarRef.current?.querySelector<HTMLButtonElement>('.mobile-close')?.focus()
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setMenuOpen(false); menuButtonRef.current?.focus() }
      if (event.key === 'Tab') {
        const list = controls(), first = list[0], last = list.at(-1)
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    document.addEventListener('keydown', keyboard)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', keyboard); document.body.style.overflow = previousOverflow }
  }, [menuOpen, mobile])
  useEffect(() => {
    const handler = () => { setRoute(currentRoute()); setMenuOpen(false); mainRef.current?.focus() }
    addEventListener('hashchange', handler); return () => removeEventListener('hashchange', handler)
  }, [])
  useEffect(() => { let live = true; listSampleDatasets().then(data => { if (live) setSamples(data) }).catch(e => { if (live) setSampleError(errorMessage(e)) }); return () => { live = false } }, [])
  const work: Work = async (label, task) => {
    if (lock.current) return
    lock.current = true; setBusy(label); setError('')
    try { await task() } catch (e) { setError(errorMessage(e)) } finally { lock.current = false; setBusy('') }
  }
  const retrySamples = () => work('Loading sample dataset catalog…', async () => {
    setSampleError('')
    try { setSamples(await listSampleDatasets()) } catch (error) { setSampleError(errorMessage(error)) }
  })
  const install = (validation: ValidationResponse, name: string, id: string | null, synthetic: boolean, sourceRows?: Record<string, unknown>[]) => {
    const rows = sourceRows ?? sourceRowsFromValidation(validation)
    const action = { type: 'SET_DATASET' as const, payload: { name, id, isSynthetic: synthetic, observations: validation.valid_rows_data, validation, sourceRows: rows } }
    dispatch(action)
    return reducer(state, action)
  }
  const loadSample = (id: string, analyze = false) => work('Loading and validating sample data…', async () => {
    setSourceFile(null)
    const data = await getSampleDataset(id)
    const validation = await validateRows(data.rows as unknown as Record<string, unknown>[])
    const installed = install(validation, data.name, id, true, data.rows as unknown as Record<string, unknown>[])
    if (analyze && validation.linear_eligible) {
      const revision = state.revision + 1
      const reg = await fitRegression(validation.valid_rows_data, validation.quadratic_eligible, validation.quadratic_recommended)
      dispatch({ type: 'SET_REGRESSION', payload: reg, revision })
      if (reg.recommended_model !== 'none' && validation.price_min != null && validation.price_max != null) {
        const opt = await runOptimization(sampleOptimizationParams(installed, reg.recommended_model))
        dispatch({ type: 'SET_OPTIMIZATION', payload: opt, revision })
      }
      location.hash = '/overview'
    } else location.hash = '/dataset'
  })
  const upload = (file: File, mapping?: Record<string, string>) => work('Validating CSV…', async () => {
    setSourceFile(file)
    const result = await validateDataset(file, mapping)
    install(result, file.name, null, false)
    location.hash = '/dataset'
  })
  const fit = () => work('Fitting and comparing demand models…', async () => {
    const val = state.validationResult
    if (!val?.linear_eligible) throw new Error('At least two independent valid ticket prices are required. Check Dataset Studio.')
    const reg = await fitRegression(state.observations, val.quadratic_eligible, val.quadratic_recommended)
    dispatch({ type: 'SET_REGRESSION', payload: reg, revision: state.revision })
  })
  const optimize = () => work('Comparing feasible revenue candidates…', async () => {
    const opt = await runOptimization(optimizationParams(state))
    dispatch({ type: 'SET_OPTIMIZATION', payload: opt, revision: state.revision })
  })
  const selectedTitle = pages.find(p => p[0] === route)?.[1]
  const common = { busy: !!busy, work }
  let content
  switch (route) {
    case 'dataset': content = <DatasetPage {...common} samples={samples} sampleError={sampleError} retrySamples={retrySamples} sourceFile={sourceFile} loadSample={loadSample} upload={upload}/>; break
    case 'regression': content = <ModelingPage {...common} fit={fit}/>; break
    case 'optimization': content = <OptimizationPage key={state.revision} {...common} optimize={optimize}/>; break
    case 'simulator': content = <SimulatorPage/>; break
    case 'diagnostics': content = <DiagnosticsPage/>; break
    case 'walkthrough': content = <WalkthroughPage/>; break
    case 'reports': content = <ReportsPage {...common}/>; break
    case 'about': content = <AboutPage/>; break
    default: content = <DashboardPage {...common} fit={fit} optimize={optimize} loadSample={id => loadSample(id, true)} standardId={samples.find(s => s.id === 'standard')?.id ?? samples[0]?.id} upload={() => { location.hash = '/dataset'; uploadRef.current?.click() }}/>
  }
  return <div className="application"><a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); mainRef.current?.focus() }}>Skip to main content</a><aside ref={sidebarRef} className={`sidebar ${menuOpen ? 'open' : ''}`} aria-label="Main navigation" inert={mobile && !menuOpen} role={mobile && menuOpen ? 'dialog' : undefined} aria-modal={mobile && menuOpen ? true : undefined}><a className="brand" href="#/overview"><span className="brand-mark"><ChartNoAxesCombined size={22}/></span><span>PricePilot<small>EVENT REVENUE OPTIMIZER</small></span></a><button className="mobile-close icon-button" onClick={() => { setMenuOpen(false); menuButtonRef.current?.focus() }} aria-label="Close navigation"><X size={20}/></button><div className="nav-label">YOUR WORKSPACE</div><nav>{pages.map(([id, title, Icon]) => <a key={id} href={`#/${id}`} onClick={() => { setMenuOpen(false); mainRef.current?.focus() }} className={route === id ? 'active' : ''} aria-current={route === id ? 'page' : undefined}><Icon size={18} aria-hidden="true"/>{title}{route === id && <span className="nav-dot"/>}</a>)}</nav><div className="sidebar-note"><Sigma size={22}/><p>Every recommendation<br/><strong>has a working.</strong></p><span>Least squares + Newton–Raphson</span><a href="#/walkthrough">Explore the mathematics <ArrowUpRight size={14}/></a></div><div className="local-label"><span/>Local analysis · no account needed</div></aside>{menuOpen && <button className="nav-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}
  <div className="workspace"><header className="topbar"><div className="topbar-context"><button ref={menuButtonRef} className="mobile-menu icon-button" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Menu size={20}/></button><span className="breadcrumb">Workspace <span>/</span> <strong>{selectedTitle}</strong></span></div><div className="toolbar"><span className="dataset-chip" title={state.datasetName ?? 'No dataset loaded'}><span className={state.datasetName ? 'status-dot' : 'status-dot inactive'}/>{state.datasetName ?? 'No dataset loaded'}</span><button className="button subtle compact" disabled={!!busy || !samples.length} onClick={() => loadSample(samples.find(s => s.id === 'standard')?.id ?? samples[0].id)}><Database size={14}/>Sample data</button><button className="button compact" disabled={!!busy} onClick={() => uploadRef.current?.click()}><Upload size={14}/>Upload CSV</button><input ref={uploadRef} aria-label="Upload historical ticket sales CSV" type="file" accept=".csv" hidden onChange={e => { const file = e.target.files?.[0]; if (file) void upload(file); e.target.value = '' }}/></div></header>
  <main id="main-content" ref={mainRef} tabIndex={-1}><div className="status-region" aria-live="polite" aria-atomic="true">{busy && <span><span className="spinner"/>{busy}</span>}</div>{error && <div className="global-error"><Notice error>{error}</Notice><button className="button subtle compact" onClick={() => setError('')}>Dismiss message</button></div>}{content}<footer><span>PricePilot <span className="footer-dot">·</span> Understand the price behind the prediction.</span><a href="#/about">Methods & limitations <ArrowRight size={12}/></a></footer></main></div></div>
}
export default function App() { return <AppProvider><Application/></AppProvider> }


