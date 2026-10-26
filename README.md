# PricePilot - Event Revenue Optimizer

Find the right ticket price. Maximize modeled event revenue. Understand the mathematics.

PricePilot is a local academic application connecting **Unit V: Least-Squares Curve Fitting and Regression** with **Unit II: Newton-Raphson**. It fits ticket demand from a selected historical dataset, constructs revenue functions, and compares feasible prices. Python is the authoritative calculation engine; the React interface displays API results.

This is a numerical-methods project. It does not use an AI service, require API keys, or establish that changing a price causes the predicted sales response. Included datasets are **Synthetic Demonstration Data - Not Real Historical Sales**.

## Run locally on Windows

Open two PowerShell terminals in the repository root. Use Python 3.13 or newer and a Node.js version compatible with the installed Vite release.

Backend:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend, in the second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open the URL printed by Vite (normally <http://localhost:5173>). API documentation is at <http://127.0.0.1:8000/docs>; the health endpoint is <http://127.0.0.1:8000/api/v1/health>. The development frontend proxies `/api` requests to the local backend. If a port is occupied, use a free port and update the proxy destination consistently. No database or cloud account is needed.

## Intended analysis workflow

1. Open Dataset Studio and choose a synthetic sample or upload a CSV.
2. Inspect rejected rows, duplicates, eligibility notes, and sellout warnings. Correct or exclude unsuitable rows and revalidate.
3. Select comparable event observations. Different events can have different demand relationships.
4. Fit the eligible models in Demand Modeling and inspect the model-selection explanation.
5. Set a feasible price interval and optional capacity in Revenue Optimization. Run the optimizer and inspect its actual Newton trace, stationary classification, and candidate comparison.
6. Explore alternatives in Scenario Simulator and inspect errors in Model Diagnostics.
7. Use Mathematical Walkthrough to explain the equations. Export the active analysis and report from Reports and Exports.

See the [user guide](docs/user_guide.md) for detailed instructions and the [implementation audit](docs/implementation_audit.md) for the actual checks performed and remaining gaps. An instruction in this guide is not evidence that a feature passed browser testing; the audit is the source for verification status.

## Data format

Only these columns are required:

```csv
event_id,ticket_price,tickets_sold
DEMO-01,50,400
DEMO-02,100,300
DEMO-03,150,200
DEMO-04,200,100
```

Prices must be finite and positive. Sales must be finite, nonnegative whole tickets. Optional fields include `event_name`, `event_category`, `event_date`, `venue_capacity`, `sales_period`, `location`, and `promotion_type`. A supplied venue capacity must be meaningful; recorded sales cannot exceed it. Invalid values must be corrected rather than silently converted to zero. Consult [the data dictionary](data/data_dictionary.md).

Regenerate deterministic local sample CSVs from the backend generator:

```powershell
python scripts\generate_sample_data.py
```

This writes the three `data/sample_*.csv` files. Their internal `_synthetic` and `_note` columns preserve provenance; the application may omit internal columns from its display.

## Architecture and calculation pipeline

```text
CSV/sample -> validation -> selected comparable observations
           -> linear/quadratic least squares -> diagnostics + holdout comparison
           -> selected final model -> explicit Newton-Raphson trace
           -> stationary/boundary/capacity/grid candidate comparison
           -> bounded scan verification -> scenarios and exports
```

The backend uses FastAPI, Pydantic, NumPy, Pandas, Matplotlib, and ReportLab. Tests use pytest and HTTPX. The frontend uses React, TypeScript, Vite, Tailwind CSS, Recharts, KaTeX, and Lucide. Dependencies are defined by `backend/requirements.txt` and `frontend/package.json` with its lockfile.

```text
backend/app/core/       numerical engine, validation, generation, reporting
backend/app/api/routes/ local API endpoints
backend/app/schemas/    request and response contracts
backend/tests/          mathematical and API regression tests
frontend/src/          application, pages, state, typed API client
data/                  deterministic CSV demonstrations and dictionary
docs/                  derivations, algorithms, report, viva and demo support
scripts/               reproducible local utility scripts
```

The normal equations are exposed for teaching. The solver uses `numpy.linalg.lstsq` on centered/scaled price columns; it does not explicitly invert `X.T @ X`. Full-data fit metrics and held-out evaluation metrics have different purposes and must be read separately. Newton-Raphson solves `R'(p)=0`; it is not by itself a global maximizer. The optimizer also compares feasible boundaries and capacity transitions.

Holdout evaluation uses seeded random rows for unique event IDs, or entire event groups when IDs repeat and at least five independent groups exist. At least fifteen observations and sufficient independent price support are required. Exported split metadata makes this choice inspectable; chronological splitting is not implemented. Scenario demand multipliers are explicitly hypothetical, applied before capacity, and do not change the base optimization.

The backend also provides diagnostics, a `/regression/compare` alias, residual/scenario CSVs, SVG/PNG charts, and reports containing active scenario assumptions. The [final audit](docs/implementation_audit.md) records which interface and export actions were actually exercised.

## Verification commands

From the repository root:

```powershell
python -m pytest backend\tests -q
Set-Location frontend
npm run build
npm run lint
```

From the repository root, use `.\backend\.venv\Scripts\python.exe` instead of `python` to run checks with the project environment. The exact verified dependency snapshot is in `backend/requirements-lock.txt`. Browser scripts and their setup are documented in the final audit. Do not infer passing tests from the presence of a test file.

The exact mathematical reference is `D(p)=500-2p`. On a compatible interval with no binding capacity, the theoretical answer is `p=125`, `D=250`, and `R=31,250`. An executed direct-engine check recovered these values to floating-point precision; the [testing notes](docs/testing_and_validation.md) distinguish that observation from the theoretical derivation.

## Academic material

- [Mathematical foundation](docs/mathematical_foundation.md): derivations, scaling, diagnostics, capacity, candidate comparison.
- [Algorithm explanations](docs/algorithm_explanations.md): inputs, outputs, pseudocode, stopping criteria, failures.
- [Project report draft](docs/project_report.md): academically framed methodology and explicitly synthetic/reference results.
- [Viva questions](docs/viva_questions.md): project-specific questions with precise answers.
- [Presentation outline](docs/presentation_outline.md) and [five-minute demonstration](docs/demo_script.md).
- [Limitations](docs/limitations.md): interpretation and unsupported claims.

Screenshots and exported verification artifacts should only be treated as evidence when linked by the final implementation audit. No coverage percentage, benchmark, or real-world sales validation is claimed here.
