import type { ReactNode } from 'react'
import katex from 'katex'
import { AlertTriangle, ArrowRight, Calculator } from 'lucide-react'
import { fmt, formatINR } from '../lib/utils'
import type { OptimizationResponse } from '../types'

export function PageTitle({ eyebrow, title, children, action }: { eyebrow?: string; title: string; children: ReactNode; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1><p className="lede">{children}</p></div>{action}</div>
}
export function Panel({ title, note, children, className = '' }: { title?: string; note?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{title && <div className="panel-heading"><h2>{title}</h2>{note && <span className="muted small">{note}</span>}</div>}{children}</section>
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={`notice ${error ? 'error' : ''}`} role={error ? 'alert' : 'note'}><AlertTriangle size={17} aria-hidden="true"/><div>{children}</div></div>
}
export function Warnings({ items }: { items: (string | null | undefined)[] }) {
  return <>{Array.from(new Set(items.filter((i): i is string => !!i))).map(text => <Notice key={text}>{text}</Notice>)}</>
}
export function Empty({ text = 'Load and validate a dataset, then fit its demand models to begin.', link = '#/dataset', label = 'Open Dataset Studio' }: { text?: string; link?: string; label?: string }) {
  return <div className="empty"><Calculator size={32} aria-hidden="true"/><h2>Start with evidence.</h2><p>{text}</p><a className="button" href={link}>{label}<ArrowRight size={15}/></a></div>
}
export function Formula({ value }: { value: string }) {
  const html = katex.renderToString(value, { throwOnError: false, displayMode: true, strict: 'ignore', trust: false })
  return <div className="formula" dangerouslySetInnerHTML={{ __html: html }} />
}
export function Metric({ label, value, note, accent = false }: { label: string; value: ReactNode; note?: ReactNode; accent?: boolean }) {
  return <div className={`metric ${accent ? 'accent' : ''}`}><p>{label}</p><strong>{value}</strong>{note && <span>{note}</span>}</div>
}
export function ResultCards({ opt }: { opt: OptimizationResponse }) {
  return <><div className="metrics three"><Metric label="Recommended ticket price" value={formatINR(opt.optimal_price, 2)} note={opt.optimal_source} accent/><Metric label="Maximum predicted revenue" value={formatINR(opt.optimal_realized_revenue, 2)} note="After demand and capacity constraints"/><Metric label="Expected ticket sales" value={fmt(opt.optimal_realized_demand, 2)} note="Continuous estimate · tickets"/></div><p className="result-caption">{opt.optimal_classification}. Configured range: {formatINR(opt.price_min)}–{formatINR(opt.price_max)}.</p></>
}

