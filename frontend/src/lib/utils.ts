// PricePilot — Utility functions

/** Format a number as Indian Rupees */
export function formatINR(v: number | null | undefined, decimals = 0): string {
  if (v == null || !isFinite(v)) return '—'
  return `₹${v.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}

/** Format a number with fixed decimal places, showing — for null/undefined */
export function fmt(v: number | null | undefined, decimals = 2): string {
  if (v == null || !isFinite(v)) return '—'
  return v.toFixed(decimals)
}

/** Format as percentage */
export function fmtPct(v: number | null | undefined, decimals = 2): string {
  if (v == null || !isFinite(v)) return '—'
  return `${v.toFixed(decimals)}%`
}

/** Format large numbers with commas */
export function fmtInt(v: number | null | undefined): string {
  if (v == null || !isFinite(v)) return '—'
  return Math.round(v).toLocaleString('en-IN')
}

/** Clamp a number to [min, max] */
export function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v))
}

/** Join class names, filtering falsy values */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

/** Color class based on severity */
export function severityColor(s: string): string {
  switch (s) {
    case 'error': return 'text-red-400'
    case 'warning': return 'text-amber-400'
    case 'info': return 'text-blue-400'
    default: return 'text-slate-400'
  }
}

/** R² classification */
export function r2Label(r2: number | null): { label: string; color: string } {
  if (r2 == null || !isFinite(r2)) return { label: 'Undefined', color: 'text-slate-400' }
  if (r2 >= 0.9) return { label: 'Excellent', color: 'text-emerald-400' }
  if (r2 >= 0.7) return { label: 'Good', color: 'text-emerald-300' }
  if (r2 >= 0.5) return { label: 'Moderate', color: 'text-amber-400' }
  return { label: 'Weak', color: 'text-red-400' }
}

/** Source label for optimization candidate */
export function sourceLabel(s: string): string {
  const map: Record<string, string> = {
    newton: 'Newton–Raphson',
    polynomial_root: 'Analytical Root',
    boundary_lower: 'Lower Boundary',
    boundary_upper: 'Upper Boundary',
    demand_zero_boundary: 'Demand Zero',
    capacity_transition: 'Capacity Transition',
    discrete: 'Discrete Price',
  }
  return map[s] ?? s
}
