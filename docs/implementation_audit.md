# PricePilot — evidence-based implementation audit

This audit records work and checks actually executed in this workspace. Source-file existence alone is not treated as verification. Included data and reported sample results are synthetic demonstrations, not independent real-world validation.

## Delivered application

The local FastAPI/React application provides all nine principal sections: Overview, Dataset Studio, Demand Modeling, Revenue Optimization, Scenario Simulator, Model Diagnostics, Mathematical Walkthrough, Reports and Exports, and About. Python is the sole demand-fitting and numerical optimization engine. The browser maps returned data into charts and formats values.

| Approved phase | Implementation and executed evidence | Status / qualification |
|---|---|---|
| 1. Setup and infrastructure | Existing files preserved; starter App replaced; isolated backend virtual environment installed; Vite and Uvicorn started; health and proxied API requests exercised in Chromium. | Local runtime verified. No Git repository existed, so no commit or PR is claimed. |
| 2. Mathematical engine | Scaled least-squares fits, coefficient recovery, residual metrics, group-aware holdout, Newton iterations and residual checks, stationary classification, boundary/capacity/discrete candidates, validation, simulation and reporting. | Automated mathematical/API tests and independent grid oracle pass. |
| 3. API routes | Health; three sample datasets; CSV validation with explicit mapping; regression fit/compare; diagnostics; optimization; scenarios; PDF; cleaned/predictions/residuals/scenarios CSV; JSON; SVG and PNG figures. | Endpoints executed in tests; eight main export buttons exercised in a real browser. |
| 4. Backend tests | Original 53-test baseline expanded to 126 tests, including reproduced numerical and API regressions. | Final suite: 126 passed, exit 0; one dependency deprecation warning. |
| 5. Frontend | Nine sections, source-row editing/add/delete/reset, grouping/search/sort, visible validation issues, model selection, invalidating state, actual curves/diagnostics/convergence charts, scenario controls, KaTeX and active-configuration exports. | Production build, lint and 11 state tests pass. Browser flows and representative viewport checks pass. |
| 6. Integration and testing | Sample/upload/invalid-data/recovery/scenario/export flows; desktop/tablet/phone routes; mobile focus trapping; generated PDF rendered and inspected. | Chromium verified. Cross-browser, real-device and formal accessibility certification are not claimed. |
| 7. Documentation | README, derivations, algorithm pseudocode, synthetic project-report draft, user guide, limitations, testing notes, 62 viva answers, presentation outline, five-minute demo, data dictionary and reproducible sample generation. | Files inspected; numeric examples executed. No fabricated bibliography, coverage percentage or performance benchmark. |

## Final commands and observed results

Commands below were executed; all listed verification commands exited **0**. Backend commands are relative to the repository root unless a directory is specified.

| Command | Observed output |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` | **126 passed**, one Starlette/httpx deprecation warning. Final captured run: 2.37 s. |
| `backend/.venv/Scripts/python.exe scripts/verify_numerical_oracle.py` | **250 seeded quadratic/capacity/discrete cases** compared against exhaustive 20,001-point continuous or exact discrete grids. Largest oracle revenue excess: **1.16e-10**. |
| `backend/.venv/Scripts/python.exe scripts/verify_api.py` | Standard sample and exact linear API references asserted; JSON, CSV, SVG and PDF artifacts written. |
| `backend/.venv/Scripts/python.exe scripts/verify_limits.py` | 10,000 rows validated and fitted; 10,001-observation request rejected with 422; oversized CSV returned an explicit file-limit issue. |
| `npm run build` in `frontend` | TypeScript and Vite production build succeeded. JS bundle approximately **1,026.07 kB** minified / **304.76 kB** gzip; Vite emitted its >500 kB advisory. |
| `npm test` in `frontend` | **11 passed, 0 failed**: dataset/model/config invalidation, stale responses, sample defaults, preserved source order, and scenario/export state. |
| `npm run lint` in `frontend` | Exit 0, no warnings or errors. |
| `node scripts/verify_browser.cjs` | All 11 flow groups passed; **8 downloads**, **31 screenshots**; no recorded console errors, page exceptions or unexpected failed requests. |
| `node scripts/verify_browser_extra.cjs` | Five additional flow groups passed: displayed sample settings, selected event category, topbar column mapping/source order/rejected export, delete/reset, and mobile keyboard behavior. |
| `node scripts/verify_browser_features.cjs` | Diagnostic plot data, model overlay, convergence chart, multiplier sensitivity, JSON/CSV/PDF scenario persistence, and four new-chart phone layouts verified; no recorded errors. |

Logs are in `output/verification/backend-tests.log`, `numerical-oracle.log`, `frontend-build.log`, `frontend-tests.log` and `frontend-lint.log`. Browser evidence is in `output/verification/browser/browser-evidence.json`, `browser-extra-evidence.json` and `browser-features-evidence.json`. Output artifacts are intentionally ignored by Git.

The limits check observed 0.377 s for 10,000-row validation and 0.057 s for its regression request in one local TestClient run. These are specific observations, **not** a general benchmark or concurrent load test.

### Browser setup for reproducing checks

The three browser scripts require Playwright and Chromium, independently of the application dependencies. For example, install Playwright in a test-tools folder, make its node_modules available with `NODE_PATH`, install its Chromium browser, then run the scripts with both app servers active. If using an already installed browser, set `PLAYWRIGHT_EXECUTABLE_PATH` to its executable.

This session used the Codex bundled Playwright package and installed Chromium executable. Browser module discovery initially requested a missing bundled revision; specifying the available Chromium executable resolved that tooling issue. An early tablet menu check incorrectly assumed the mobile drawer was active at 768 px; the test was corrected to respect the actual 760 px breakpoint. These were not recorded as successful app checks until the corrected scripts passed.

## Numerical reference evidence

### Exact linear case

Input demand: `D(p)=500−2p`, feasible interval `[50,240]`, no capacity cap.

API output:

```text
optimal_price             125.00000000000003
optimal_realized_demand   250.00000000000006
optimal_realized_revenue  31250.000000000015
```

The browser-upload reference independently displayed **125, 250, 31,250**. Algebra gives `R′(p)=500−4p=0` and `R″(p)=−4`; the implementation agrees within floating-point precision.

### Known quadratic recovery

The noiseless polynomial `D(p)=600−2p−0.001p²` recovered:

```text
a = 599.9999999999993
b = -1.9999999999999902
c = -0.0010000000000000378
```

These are a direct engine check recorded in testing notes, separate from fitting noisy synthetic observations.

### Standard synthetic sample

The corrected standard generator returns 80 records, 13 distinct prices, prices 50–170, no sold-out records and no zero-sales records. Seed 42; latent demand `800−3.5p−0.005p²` plus Normal(0,15) noise, with integer observed counts. Its final fitted quadratic is:

```text
a = 767.9111636686947
b = -2.9578133146008936
c = -0.007240275982627887
full-data RMSE = 13.641308769342585 tickets
held-out RMSE = 14.102831552982643 tickets
best feasible price = 95.98332850384918
expected realized revenue = 40054.53279464838
```

The held-out score comes from a training-only fit. The displayed coefficients and subsequent optimization use all accepted rows. Noise means the latent generator's coefficients should not be expected to be recovered exactly.

With maximum price 140 and capacity 200, the browser verified a distinct **upper-boundary recommendation of 140**, expected sales **200**, and revenue **28,000**. For constant demand 30 on prices 100–130, Newton correctly reported `failed_zero_derivative` while separate boundary comparison selected price **130**.

### Hypothetical scenario evidence

At price 100 in the standard sample, uncapped modeled demand was 399.72707238232647 and revenue 39,972.707238232644. With the explicitly hypothetical multiplier 1.2, the API returned demand 479.6724868587918 and revenue 47,967.24868587918. JSON, scenario CSV and PDF preserved this assumption. The base optimization revenue stayed **40,054.53279464838**. A scenario assumption is not observed evidence or a causal estimate.

## Browser and PDF inspection

- All nine routes checked at **1440×1000**, **768×1024** and **390×844**. Page-wide overflow was asserted absent at tablet and phone widths. Tables and formulas use local horizontal scrolling where necessary.
- Opened and inspected screenshots of all nine phone pages and the major desktop pages, including the added model overlay, residual histogram, actual-versus-predicted plot, convergence and scenario comparison.
- Dataset Studio browser checks covered rejected-row editing, adding a record, source-order preservation, search, event-category selection, bulk deletion, reset, column mapping and rejected-row download.
- Identical-price input disabled fitting; replacing it with adequate input recovered without a page refresh.
- Selecting another model removed the previous optimum. The numerical iteration trace and final derivative residual were visible.
- Mobile drawer was inert while closed; 20 Tab presses stayed inside the open drawer; Escape closed it and restored focus to its trigger.
- Generated PDF files were parsed with pypdf, rendered using bundled Poppler, and visually inspected. The final multiplier report has **5 A4 pages**, embedded Unicode-capable fonts, readable tables/plots, a complete iteration trace, candidate comparison, scenario assumptions and limitations. Its text contains both the unchanged base revenue and hypothetical scenario revenue; no NaN text was found in the standard report.

Representative artifacts:

- `output/verification/sample-report.pdf`
- `output/verification/sample-analysis.json`
- `output/verification/browser/desktop-overview.png`
- `output/verification/browser/390-overview.png`
- `output/verification/browser/extended-diagnostics.png`
- `output/verification/browser/extended-scenario-multiplier.png`
- `output/verification/browser/multiplier-report.pdf`

## Significant corrections made

1. Replaced the unconnected starter UI and resolved existing TypeScript errors.
2. Aligned full-data fits used by model views, optimization, simulation and exports; preserved independent holdout scoring.
3. Eliminated the short-training-array prediction-export defect and settings/provenance loss in reports.
4. Rejected fractional/nonfinite/invalid sales and capacities instead of rounding or imputing them.
5. Added reliable Newton residual/range/stagnation checks; stopped classifying failed iterates or zero revenue as valid interior maxima.
6. Corrected capacity roots, small polynomial curvature, and decimal price-grid boundaries.
7. Replaced fabricated zero values for undefined Newton corrections with null; unexpected required nonfinite evidence returns an error.
8. Fixed ambiguous CSV mapping, source-row/error associations, original input ordering and formula-safe exports.
9. Made sample optimization use exactly the controls displayed by the UI.
10. Prevented event-group leakage and stale asynchronous/chart results.
11. Added the remaining diagnostic/scenario/convergence plots and residual/scenario/image exports.

## Remaining limitations and unverified work

- No independent real-world ticket-sales validation, causal experiment, confidence interval or guaranteed revenue uplift is claimed.
- Chronological holdout is not implemented. Grouped random holdout depends on accurate event IDs; incorrectly identified groups can still mislead evaluation.
- Application state is in memory and resets on refresh. JSON exports are reproducible records; one-click JSON session restoration is not implemented.
- A full concurrent load test, cross-browser/device matrix and screen-reader audit were not performed. Keyboard and representative Chromium layouts were checked; WCAG certification is not claimed.
- Vite's bundle-size advisory and the Starlette/httpx test deprecation warning remain. The application still builds and tests successfully.
- Nearby selected-price and base-optimum chart annotation labels can crowd. Both values are also given in text and tabular form; their numerical values remain distinct and correct.
- SVG/PNG exports are backend composite analytical figures, rather than a download of every individual browser chart.
- No editable PowerPoint file was generated. The requested presentation outline and demonstration narration are supplied.
- Profit, multiple ticket tiers, dynamic inventory, multivariable demand and censored-demand estimation are outside this implementation. Revenue is gross modeled ticket revenue.

## Local execution

Frontend: http://127.0.0.1:5173/ — backend/docs: http://127.0.0.1:8000/docs.

From the repository root, run these in separate PowerShell terminals:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Both servers were running when this audit was written. See README for installation and `backend/requirements-lock.txt` for the exact environment snapshot used for verification.
