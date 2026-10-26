# PricePilot interaction contract

Visual identity is in DESIGN.md; src/index.css owns runtime tokens.

| Capability | Canonical owner | Contract |
|---|---|---|
| Navigation | App.tsx native hash links | Nine named sections; active link exposes aria-current. Narrow navigation opens from a labelled button and closes on route change. |
| Table selection | DatasetPage selected Set and pageRows | Checkboxes select individual source rows; header checkbox affects only the visible 25-row page. Bulk removal is draft-only and Reset restores import. |
| Select/listbox | Native select | Platform-owned keyboard, popup, and multiple-selection behavior. |
| Data-entry fields | Native labelled controls and backend validation | Numeric draft text is preserved; explicit Apply validates observations before active analysis changes. |
| Dates | Backend CSV validation | Optional dates are preserved; no custom date picker. |
| Scrollbars | src/index.css | Globally visible themed scrollbars; tables and formulas own controlled overflow. |
| Feedback | App.tsx + UI.Notice | Indeterminate live status during requests; persistent actionable errors; no speculative success messages. |
| CRUD | DatasetPage + services/api.ts | Reversible in-memory drafts, add/remove/edit/reset, explicit revalidation. No server persistence is implied. |

State: changing dataset clears regression and optimization. Changing demand model or pricing configuration clears optimization. Every derived response carries a revision and is ignored when stale. Scenario/curve requests abort on replacement and only matching request keys render. Global mutation locking prevents overlapping dataset/analysis mutations.

Original imported rows and edited source rows are distinct. Active observation groups are revalidated by the backend. Rejected source rows remain editable. Analysis/export uses only accepted observations. Leaving Dataset Studio discards unapplied local edits; that behavior is stated above the editor.

CSV exports escape textual formula prefixes; all prices, predictions, diagnostics, revenue and validation summaries come from the Python backend. Browser serialization contains no demand model or optimizer.

Locale: English labels, INR formatting using en-IN, decimal prices and continuous ticket forecasts explicitly labeled. Undefined metrics show an em dash or Undefined. Synthetic data is always identified.

Accessibility: native links/buttons/fields, visible focus, label association, skip link, live request status, status text beyond color, chart explanations, controlled horizontal scrolling, reduced motion and forced-color fallbacks.

Verification must include production build plus actual browser sample, upload/recovery, model choice, optimization, scenario, export, and narrow viewport flows. Build success alone is not behavioral verification.

Expanded evidence views use backend-returned demand predictions, diagnostic plot coordinates and histogram bins, recorded Newton steps, and evaluated scenario points. Scenario demand multipliers are hypothetical and persisted separately from the fitted model and base optimum; changing dataset, model or constraints clears them. Reports receive the last successfully evaluated scenario controls.
