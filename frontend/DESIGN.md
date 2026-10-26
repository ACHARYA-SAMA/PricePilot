# PricePilot frontend design

Product register: local analytics workspace for event organizers and mathematics students. The brief's navy/indigo/emerald identity is retained. The distinctive element is the mathematical decision card: the tradeoff between ticket volume and price is stated before any calculated KPI is shown.

Runtime ownership: src/index.css is canonical. This document mirrors its roles rather than generating tokens. Shared Panel, Notice, Metric, Formula, PageTitle and Empty primitives are in src/components/UI.tsx; all screens reuse them.

| Role | Runtime token | Value |
|---|---|---|
| Canvas | --navy | #101828 |
| Sidebar | --navy-deep | #0d1422 |
| Panel | --surface | #172233 |
| Primary action | --primary | #4f46e5 |
| Foreground | --text | #f8fafc |
| Supporting text | --muted | #a4b1c4 |
| Positive outcome | --emerald | #10b981 |
| Caution | --amber | #f59e0b |
| Failure | --red | #ef4444 |

Typography uses locally available Segoe UI/Inter/system sans without external requests, Cambria for compact equation summaries, and bundled KaTeX fonts for typeset mathematics. Numeric displays use tabular figures. The signature thesis is typographic, not decorative; no photography or generated imagery is required.

Layout: 248px desktop navigation, max 1600px workspace, 22px panel rhythm, 12px panel radius. At 760px the navigation becomes a keyboard-operable drawer. Tables and equations scroll within their panel. Charts reserve height and take measured container width.

Chart colors are separate accessible presentation roles: pale indigo demand, emerald revenue, amber historical observations. Data comes from backend calculations. Red/amber/green statuses always include explanatory text.

Reconciliation: original CSS used external Google fonts, low-contrast slate text, and inconsistent literal colors; shared runtime tokens now own all application styling. The brief's brand identity is preserved. Browser verification is recorded by the primary agent, not inferred from this stylesheet.
