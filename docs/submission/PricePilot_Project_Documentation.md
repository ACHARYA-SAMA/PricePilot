# PricePilot
## Event Revenue Optimizer
Numerical Methods Project Report

Submitted to MLRIT

Submitted by

| Team member | Roll number |
| --- | --- |
| Arman Acharya | 25r21a6704 |
| Manit Reddy | 25r21a6722 |
| K.Aravind | 25r21a6730 |

Under the guidance of
Mr. Praveen Kumar

Submission date
28 October 2026

<!-- page -->
# Abstract
PricePilot is a local web application that demonstrates how least-squares regression and Newton–Raphson iteration can support event ticket-pricing analysis. The application accepts price and sales observations, validates the data, fits linear and quadratic demand models, and estimates a revenue-maximizing price within specified constraints. It connects Unit V, Least-Squares Curve Fitting and Regression, with Unit II, Newton–Raphson, through a complete and inspectable computational workflow.

The frontend uses React and TypeScript, while a Python backend built with FastAPI performs the calculations. NumPy solves centered and scaled least-squares systems. The application displays fitted equations, residual diagnostics, model comparison, revenue curves, the actual Newton iteration trace, and alternative price scenarios. Optional venue capacity and ticket-price increments make the optimization feasible under practical restrictions. Candidate comparison includes stationary points, interval boundaries, demand-zero boundaries, and capacity transitions, because a stationary point alone does not establish the constrained maximum.

An exact reference case, D(p) = 500 − 2p, reproduces the theoretical optimum of 125 currency units per ticket, expected demand of 250 tickets, and revenue of 31,250 currency units. In the standard synthetic sample, the fitted quadratic gives a continuous recommended price of approximately 95.98 and modeled revenue of 40,054.53. These are numerical demonstrations rather than evidence of actual business improvement.

Verification performed on 27 October 2026 passed 126 backend tests and 11 frontend state and workflow tests. The production build and lint also passed. An independent numerical oracle checked 250 seeded quadratic, capacity, and discrete-price cases against dense continuous scans or exact discrete grids. Existing browser evidence provides additional coverage of data recovery, navigation, scenarios, exports, and responsive layouts.

PricePilot provides a transparent academic application of numerical methods. Its outputs depend on the quality and comparability of the input observations and on the chosen model. It does not establish causal price effects, maximize profit, or guarantee future ticket sales.

Keywords: least squares, regression, Newton–Raphson, demand modeling, constrained revenue optimization, numerical methods.

<!-- page -->
# Contents
{{TOC}}

<!-- page -->
# 1 Introduction
## 1 1 Background
An event organizer must choose a ticket price before knowing exactly how many people will attend. Increasing price raises the amount earned per ticket, but it may reduce sales. Choosing the lowest price can attract more attendees while leaving potential revenue unrealized. Choosing a very high price can reduce attendance enough to lower total revenue. A demand model expresses this tradeoff and allows candidate prices to be compared mathematically.

PricePilot presents this process as an educational application. The user supplies observations of price and recorded sales, inspects data-quality issues, estimates a demand curve, and examines the revenue implied by that curve. The recommendation is accompanied by equations, diagnostics, and numerical steps so that the result can be explained during a project demonstration.

## 1 2 Problem statement
Given finite price and sales observations from comparable events or offers, estimate a price-demand relationship and determine the feasible ticket price that maximizes modeled ticket revenue. The analysis must account for a chosen price interval, optional venue capacity, and an optional permitted price increment. It must also explain when the available data or fitted relationship cannot support a useful recommendation.

## 1 3 Objectives
- Validate records and expose rejected rows, duplicates, and capacity warnings.
- Fit linear and quadratic demand curves with numerically stable least squares.
- Compare models using diagnostics and held-out prediction errors when available.
- Apply Newton–Raphson to the derivative of the revenue function and show the real iteration trace.
- Compare feasible stationary points and boundaries before recommending a price.
- Support scenarios, charts, and exports that preserve the active analysis settings.

## 1 4 Academic relevance
Least-squares fitting supplies the estimated demand coefficients. Differentiation converts the revenue objective into a root-finding problem, and Newton–Raphson supplies the iterative solution. The final candidate comparison shows why numerical convergence, local classification, and constrained maximization are distinct questions. This links the two numerical-methods units through one understandable application.

<!-- page -->
# 2 Scope and Requirements
## 2 1 Functional requirements
The application must load an included demonstration dataset or an uploaded CSV, identify usable observations, fit eligible models, and display the selected demand equation. It must compute revenue over a permitted interval, expose convergence and failure information, and compare hypothetical prices. Users must be able to inspect diagnostics and export the current analysis.

| Requirement | Implemented behavior |
| --- | --- |
| Data preparation | CSV upload, column mapping, editing, validation, and accepted or rejected rows |
| Demand estimation | Linear and quadratic fits with residuals and numerical warnings |
| Model comparison | Shared holdout split when eligible and a stated selection reason |
| Revenue analysis | Bounds, starting guess, tolerances, capacity, and price increments |
| Interpretation | Candidate table, convergence trace, diagnostics, and scenarios |
| Reporting | PDF, JSON, CSV, SVG, and PNG exports |

## 2 2 Quality requirements
Python is the authoritative calculation engine. The interface should display backend results consistently, preserve full numerical precision during calculation, and round only for presentation. Invalid numeric inputs must produce explicit errors rather than invented zero values. Changes to the data, selected model, or optimization constraints must invalidate affected results so an earlier recommendation is not shown as current.

The interface supports desktop, tablet, and phone layouts. This responsiveness assists demonstrations on different screen sizes; it does not constitute accessibility certification or testing on every physical device.

## 2 3 Scope boundaries
PricePilot is a local academic analysis tool. It does not sell tickets, process payments, authenticate multiple users, or maintain a database of customer transactions. Price is the sole fitted predictor. Descriptive columns help users inspect and select data but do not automatically become explanatory variables. The objective is ticket revenue rather than profit because costs are not modeled.

## 2 4 Runtime requirements
The repository documents Python 3.13 or newer and a Node.js version compatible with the installed Vite release. Two local processes run the backend and frontend. A modern browser accesses the interface. Initial dependency installation requires package access; the application itself needs no paid API, cloud account, AI service, or database.

<!-- page -->
# 3 System Architecture
The system separates interaction from computation. React components collect input and present the returned analysis. FastAPI routes validate requests and invoke Python services. The numerical core performs data validation, regression, optimization, diagnostics, scenarios, and reporting. This keeps the displayed coefficients, recommendation, and exports tied to the same computational implementation.

![Architecture](architecture.png)
Figure 1. PricePilot architecture and analysis pipeline.

## 3 1 Technology stack
| Layer | Technologies | Responsibility |
| --- | --- | --- |
| Interface | React, TypeScript, Vite, Tailwind CSS | Pages, controls, layout, and state |
| Visual presentation | Recharts, KaTeX, Lucide | Charts, mathematical notation, and icons |
| HTTP API | FastAPI and Pydantic | Routes, request contracts, and structured errors |
| Numerical processing | NumPy and Pandas | Least squares, arrays, CSV processing, and summaries |
| File generation | Matplotlib and ReportLab | Export charts and application analysis PDFs |
| Verification | pytest, HTTPX, Node tests, browser scripts | Numerical, API, state, and interaction checks |

## 3 2 Analysis state
The frontend retains the current working analysis in memory. Dataset changes clear dependent fits and recommendations. A model change clears the previous optimum. Bounds or capacity changes invalidate optimization while retaining an applicable demand fit. Revision checks prevent delayed responses from replacing results for newer inputs. Exports should be saved before closing or refreshing the application.

<!-- page -->
# 4 Data Design and Validation
## 4 1 Input schema
| Column | Required | Meaning and rules |
| --- | --- | --- |
| event_id | Yes | Nonempty identifier for the underlying event |
| ticket_price | Yes | Finite positive price in one consistent currency |
| tickets_sold | Yes | Finite nonnegative whole-ticket sales count |
| venue_capacity | No | Positive whole-ticket capacity; sales must not exceed it |
| event_name and event_category | No | Descriptive labels used for inspection and grouping |
| event_date | No | Event date; supplied invalid dates receive a visible issue |
| sales_period, location, promotion_type | No | Descriptors; not fitted predictors |

Observed revenue is derived as ticket_price × tickets_sold. Currency is not inferred from the file, so all prices in an analysis must use the same unit. Internal _synthetic and _note fields preserve the provenance of included demonstrations.

## 4 2 Validation sequence
The validator checks the file type and size, parses CSV content, resolves unambiguous header aliases, and applies explicit mappings where required. It then checks each record for missing identifiers, invalid or nonfinite numbers, nonpositive prices, negative or fractional sales, invalid capacity, and sales above capacity. Accepted and rejected records retain their original source-row relationship. Duplicate and sellout warnings remain visible.

The default upload limit is 5 MiB and the default record limit is 10,000. Regression requests also allow at most 10,000 observations. The CSV policy requires at least three valid rows and two distinct prices for linear fitting. Quadratic eligibility requires at least six rows and three distinct prices; automatic quadratic recommendation uses the stronger policy of twelve rows and six distinct prices.

## 4 3 Demonstration datasets
| Dataset | Records | Purpose |
| --- | --- | --- |
| Standard College Events | 80 | Clean synthetic demand example with seed 42 and 13 prices |
| Sold-Out Events | 40 | Illustrates capacity censoring at 200 tickets using seed 43 |
| Problematic Data | 13 | Deliberate missing values, invalid counts, and a duplicate |

All three datasets are synthetic. A sellout reveals that latent demand may exceed recorded sales; ordinary least squares does not undo this censoring. Users must select observations whose audiences, offers, and event conditions are meaningfully comparable.

<!-- page -->
# 5 Least Squares Demand Estimation
## 5 1 Linear demand
Let pᵢ denote the price and yᵢ the recorded sales for observation i. A linear model estimates demand as D(p) = a + bp. The coefficients minimize the sum of squared residuals.

> S(a,b) = Σᵢ (yᵢ − a − bpᵢ)²

Setting the partial derivatives with respect to a and b to zero gives the normal equations:

> na + bΣpᵢ = Σyᵢ
> aΣpᵢ + bΣpᵢ² = Σpᵢyᵢ

For distinct prices, the slope is Σ(pᵢ − p̄)(yᵢ − ȳ) / Σ(pᵢ − p̄)², and the intercept is ȳ − bp̄. A decreasing demand curve normally has a negative slope. Identical prices cannot identify the slope, regardless of the number of repeated observations.

## 5 2 Quadratic demand
A quadratic allows the rate of demand change to vary with price. Its model is D(p) = a + bp + cp², and the design matrix has columns 1, p, and p². Differentiating the squared-error objective yields three equations:

> na + bΣpᵢ + cΣpᵢ² = Σyᵢ
> aΣpᵢ + bΣpᵢ² + cΣpᵢ³ = Σpᵢyᵢ
> aΣpᵢ² + bΣpᵢ³ + cΣpᵢ⁴ = Σpᵢ²yᵢ

At least three distinct prices are necessary for full column rank. Exactly interpolating three observations is possible without demonstrating useful prediction. PricePilot therefore separates mathematical estimability from practical eligibility and recommendation.

## 5 3 Stable implementation
In matrix notation, least squares minimizes ‖Xβ − y‖², with explanatory normal equations XᵀXβ = Xᵀy. PricePilot exposes the original sums for teaching, but it solves a centered and scaled design matrix with numpy.linalg.lstsq [1]. It does not explicitly invert XᵀX.

With t = (p − μ)/s, the fitted model is α + βₜt + γt². Coefficients return to price units using c = γ/s², b = βₜ/s − 2γμ/s², and a = α − βₜμ/s + γμ²/s². Rank, conditioning, finite results, and the precision of this transformation are checked. The unrounded coefficients drive every later calculation.

<!-- page -->
# 6 Diagnostics and Model Selection
## 6 1 Residual measures
For actual sales yᵢ and prediction ŷᵢ, the residual is eᵢ = yᵢ − ŷᵢ. Positive residuals indicate underprediction and negative residuals indicate overprediction. Residual patterns can reveal a systematic shape that a single summary score conceals.

| Measure | Definition | Interpretation |
| --- | --- | --- |
| SSE | Σeᵢ² | Total squared error in squared tickets |
| MAE | Σ abs(eᵢ) / n | Average absolute error in tickets |
| RMSE | √(SSE / n) | Error scale that penalizes large misses |
| R² | 1 − SSE / SST | Explained sample variation when SST > 0 |
| Adjusted R² | 1 − (1 − R²)(n − 1)/(n − k − 1) | R² adjusted for k nonconstant predictors |

Here SST = Σ(yᵢ − ȳ)². R² is undefined when actual sales have no variation. Adjusted R² also requires n − k − 1 > 0; k is one for linear demand and two for quadratic demand. Undefined values remain unavailable rather than becoming fabricated zeros. An out-of-sample R² can be negative.

## 6 2 Holdout evaluation
When at least fifteen observations have unique event IDs, a seeded 80/20 random row split is used. If event IDs repeat, the split instead isolates entire events and requires at least five independent groups. The 80/20 target then applies to groups, so the row counts need not follow the same ratio. Both models use the same partition. Inadequate price support, rank, or conditioning disables holdout evaluation with a warning.

The evaluation-stage model is fitted only on training observations and predicts untouched validation observations. After comparison, final models are refitted on all selected records for display, optimization, and scenarios. Consequently, held-out metrics and final coefficients refer to different fitting stages. Exported partition indices and split strategy make this distinction inspectable.

## 6 3 Selection policy
When holdout scores are available, the quadratic is preferred only if its validation RMSE is more than 5% lower than the linear score, its support policy permits recommendation, and its demand shape is plausible. Without holdout, the implementation uses a conservative adjusted-R² comparison and the same support and shape considerations. The 5% threshold is a decision heuristic, not a statistical significance test. Random holdout does not validate future-time forecasting.

<!-- page -->
# 7 Revenue Model and Newton Raphson Method
## 7 1 Revenue function
Ticket revenue is price multiplied by expected demand. For linear demand, the revenue curve is quadratic; for quadratic demand, it is cubic.

| Demand | Revenue R(p) | First derivative R′(p) | Second derivative R″(p) |
| --- | --- | --- | --- |
| a + bp | ap + bp² | a + 2bp | 2b |
| a + bp + cp² | ap + bp² + cp³ | a + 2bp + 3cp² | 2b + 6cp |

An interior stationary price satisfies R′(p) = 0. Newton–Raphson estimates a root by repeatedly intersecting the tangent to f(p) = R′(p) with the price axis.

> pₙ₊₁ = pₙ − R′(pₙ) / R″(pₙ)
> pₙ₊₁ = pₙ − (a + 2bpₙ + 3cpₙ²) / (2b + 6cpₙ)

The interface displays each actual price, derivative, second derivative, correction, next estimate, and absolute step. The API defaults are a price-step tolerance of 10⁻⁶, derivative tolerance of 10⁻⁸, and iteration limit of 100. The interface supplies the chosen configuration, which can differ from these API defaults. The request contract permits iteration limits from 1 to 500.

## 7 2 Convergence and failure
A small derivative residual is required before claiming convergence. A small step alone can occur because of numerical stagnation, so it is insufficient. Failure states include a near-zero denominator, nonfinite arithmetic, an iterate leaving the permitted interval, stagnation, and exhausting the iteration budget. The initial guess must lie within the positive price bounds.

## 7 3 Stationary point classification
At a verified stationary price, a negative R″ indicates a strict local maximum and a positive R″ indicates a strict local minimum. An effectively zero second derivative is inconclusive. The classification is local: even a local maximum must be compared with feasible interval boundaries and capacity transitions. Newton can fail while a separately evaluated boundary still gives a valid feasible recommendation. The application preserves these two outcomes separately.

<!-- page -->
# 8 Feasible Optimization Algorithm
## 8 1 Constraints and capacity
Let L and U be the positive lower and upper price limits, with L < U. When capacity C is supplied, the realizable sales calculation caps modeled demand at C.

> Q(p) = min(max(D(p), 0), C)
> Rᶜ(p) = pQ(p), subject to L ≤ p ≤ U

Without a capacity value, positive modeled demand is not capped. Negative raw demand remains flagged as an invalid economic region; clipping it for visualization does not make it a reliable prediction. A continuous expected sales value may be fractional even though observed ticket counts must be whole numbers.

## 8 2 Candidate construction
The optimizer first runs Newton–Raphson and preserves its trace and status. It then independently recovers real roots of the polynomial revenue derivative. It adds the interval endpoints and roots of D(p) = 0. If capacity is supplied, roots of D(p) = C are also included. Every candidate is checked for bounds, demand feasibility, realizable sales, and revenue.

Capacity creates a piecewise revenue function. In the sold-out region, revenue is pC; outside that region it follows pD(p). A maximum may occur where D(p) crosses C, even if the derivative of the uncapped revenue is not zero there. Including these transition points is therefore necessary.

## 8 3 Discrete ticket prices
An optional positive increment h permits prices at multiples of h inside the chosen bounds. The method considers neighboring grid values around stationary points and region boundaries. It rejects values outside the interval or an admissible demand region. If no permitted grid price is feasible, it reports that condition instead of inventing a recommendation. This candidate reduction uses the structure of the low-degree piecewise polynomial.

## 8 4 Pseudocode
```text
validate data, model, bounds, capacity, increment, and tolerances
fit the selected final demand model
run Newton on R_prime and keep its actual status
collect stationary roots, endpoints, and demand-zero roots
add capacity roots when capacity is configured
project candidates to adjacent allowed grid prices when required
evaluate demand, feasibility, realized sales, and realized revenue
select the feasible candidate with the largest realized revenue
compare with a bounded scan and return warnings and evidence
```

The scan is an independent numerical cross-check with finite resolution. Agreement supports the calculation for the tested configuration; it does not establish real-world demand accuracy.

<!-- page -->
# 9 Application Modules
## 9 1 User interface modules
| Section | Purpose |
| --- | --- |
| Overview | Introduces the workflow and summarizes the current analysis |
| Dataset Studio | Loads data and supports inspection, editing, grouping, and validation |
| Demand Modeling | Displays fitted curves, equations, metrics, and model comparison |
| Revenue Optimization | Collects constraints and displays the recommendation and trace |
| Scenario Simulator | Compares proposed prices and hypothetical demand assumptions |
| Model Diagnostics | Shows residuals, actual versus predicted sales, and error measures |
| Mathematical Walkthrough | Explains normal equations, derivatives, and numerical steps |
| Reports and Exports | Downloads analysis data, charts, and the application report |
| About | Explains the project and its academic context |

## 9 2 Backend responsibilities
validation.py parses and checks observations. regression.py fits the models and compares them. optimization.py implements Newton iteration, candidate construction, grid handling, and scan verification. diagnostics.py prepares numerical diagnostics and plot data. simulation.py evaluates prices and hypothetical scenarios. reporting.py produces the application charts and report, while services/analysis.py assembles a consistent analysis for exports.

## 9 3 Scenario assumptions
The scenario multiplier is a user-supplied factor m satisfying 0 < m ≤ 10. It scales demand before capacity is applied: Dₛ(p) = mD(p). Baseline comparisons use the same factor. Percentage change is unavailable when baseline revenue is zero. These controls explore assumptions; they do not estimate the causal effect of promotion or change the base optimization result.

## 9 4 Consistent exports
Analysis exports preserve the active observations, selected model, constraints, provenance, and scenario assumptions. JSON includes numerical values and split metadata. CSV exports support data inspection; SVG and PNG preserve the curves. The application's exported PDF is a compact analysis report, while this document describes the complete project.

<!-- page -->
# 10 API and Repository Structure
All application routes below use the /api/v1 prefix. FastAPI provides interactive documentation at /docs and alternative documentation at /redoc [2]. Pydantic request models enforce numeric and structural constraints [4]. Invalid request bodies receive structured validation errors.

| Method | Route suffix | Purpose |
| --- | --- | --- |
| GET | /health | Backend status and version |
| GET | /sample-datasets | List included synthetic datasets |
| GET | /sample-datasets/{dataset_id} | Load a selected sample |
| POST | /datasets/validate | Validate uploaded CSV and optional column mapping |
| POST | /regression/fit | Fit and compare eligible demand models |
| POST | /regression/compare | Alias for the comparison operation |
| POST | /optimization/run | Optimize using current observations and settings |
| POST | /diagnostics/evaluate | Produce selected-model diagnostic data |
| POST | /scenarios/evaluate | Evaluate proposed scenario prices |
| POST | /reports/pdf | Export the active analysis report |
| POST | /exports/cleaned-csv | Download accepted observations |
| POST | /exports/predictions-csv | Download fitted predictions and residuals |
| POST | /exports/residuals-csv | Download residual data |
| POST | /exports/scenarios-csv | Download scenario assumptions and results |
| POST | /exports/analysis-json | Download reproducible analysis information |
| POST | /exports/chart-svg or /exports/chart-png | Download analysis curves |

## 10 1 Source organization
```text
backend/app/core/        Numerical methods and data processing
backend/app/api/routes/  HTTP endpoint implementation
backend/app/schemas/     Request and response contracts
backend/app/services/    Analysis assembly
backend/tests/           Mathematical and API tests
frontend/src/pages/      Nine application sections
frontend/src/lib/        Application state and workflow logic
frontend/src/services/   Typed API client
data/                    Samples and data dictionary
docs/                    Theory, report, user guide, and viva material
scripts/                 Generators and verification utilities
```

<!-- page -->
# 11 Interface Evidence
The following screenshots come from the repository's recorded Chromium verification artifacts. They show the implemented interface with synthetic demonstration data. They illustrate application behavior rather than independently observed market outcomes.

![Dataset Studio](../../output/verification/browser/desktop-dataset.png)
Figure 2. Dataset Studio provides data inspection, validation summaries, and preparation controls.

![Demand Modeling](../../output/verification/browser/extended-model-overlay.png)
Figure 3. Demand Modeling compares the fitted demand curves and displays model evidence.

<!-- page -->
# 12 Optimization and Diagnostic Views
The optimization view presents the feasible recommendation with the actual numerical trace. Diagnostic plots help examine errors independently of the recommended price. Both views draw their numerical values from the backend analysis.

![Revenue Optimization](../../output/verification/browser/extended-convergence.png)
Figure 4. Revenue Optimization displays the recommended price, expected sales, and revenue curve.

![Model Diagnostics](../../output/verification/browser/extended-diagnostics.png)
Figure 5. Model Diagnostics displays residual and actual-versus-predicted evidence.

<!-- page -->
# 13 Results and Discussion
## 13 1 Standard synthetic sample
The standard dataset contains 80 observations generated with seed 42. Its 13 distinct prices span 50 to 170. The latent mechanism is 800 − 3.5p − 0.005p² plus normally distributed noise with standard deviation 15 tickets, followed by whole-ticket rounding. The fixed sample has no zero-sales or sold-out observations. Category labels share this simulated mechanism by construction.

| Quantity | Linear fit | Quadratic fit |
| --- | --- | --- |
| Intercept a | 846.481987 | 767.911164 |
| Linear coefficient b | −4.536775 | −2.957813 |
| Quadratic coefficient c | Not applicable | −0.007240276 |
| Full-data RMSE in tickets | 15.381536 | 13.641309 |
| Full-data R² | 0.989005 | 0.991352 |
| Held-out RMSE in tickets | 14.972700 | 14.102832 |

The quadratic reduces held-out RMSE by approximately 5.81% relative to the line and is selected under the implemented policy. The held-out comparison uses 16 validation observations. The displayed final coefficients come from fitting all 80 accepted observations, while validation errors come from the training-only fit.

## 13 2 Continuous optimum
For the selected final quadratic on [50,170], with no price grid and no binding capacity, the recommended price is 95.983329. Expected demand is 417.307187 tickets and modeled revenue is 40,054.532795 currency units. The recorded Newton result converges with three trace entries, and R″ at the stationary point is approximately −10.085301. The bounded scan agrees with the selected candidate.

## 13 3 Capacity and scenarios
The earlier browser audit also records a capacity-limited configuration with upper price bound 140 and capacity 200. Its recommendation is the upper boundary 140, with 200 realizable expected sales and revenue 28,000. This differs from the uncapped case because the constraints change the objective.

At price 100, the standard model gives demand 399.727072 and revenue 39,972.707238. A hypothetical multiplier of 1.2 gives demand 479.672487 and revenue 47,967.248686 when capacity does not bind. This is an assumed scenario, not measured growth. It leaves the base optimum unchanged. The reported numbers demonstrate internal numerical behavior; no actual ticket-sales improvement is claimed.

<!-- page -->
# 14 Worked Mathematical Reference
## 14 1 Exact linear demand
Consider eight noiseless observations at prices 25, 50, 75, 100, 125, 150, 175, and 200, generated by D(p) = 500 − 2p. Least squares recovers a = 500 and b = −2 within floating-point precision. On the interval [25,200], the revenue and its derivatives are:

> R(p) = 500p − 2p²
> R′(p) = 500 − 4p
> R″(p) = −4

Starting at p₀ = 100, Newton gives p₁ = 100 − (500 − 400)/(−4) = 125. At 125, the derivative residual is zero in exact arithmetic. Since the second derivative is negative, this stationary point is a strict local maximum.

| Candidate price | Demand in tickets | Revenue in currency units | Role |
| --- | --- | --- | --- |
| 25 | 450 | 11,250 | Lower endpoint |
| 125 | 250 | 31,250 | Interior stationary point |
| 200 | 100 | 20,000 | Upper endpoint |

The interior point exceeds both endpoints, establishing the maximum on this interval. Direct engine checks recorded in the project recover approximately 125.00000000000001, 249.99999999999994 tickets, and 31,249.999999999996 revenue. These tiny differences are normal floating-point effects.

## 14 2 Exact quadratic recovery
For the same prices, the noiseless demand D(p) = 600 − 2p − 0.001p² recovers coefficients approximately 599.9999999999993, −1.9999999999999902, and −0.0010000000000000378. This verifies recovery of a known polynomial. It does not imply that coefficients fitted to noisy, clipped, or censored observations equal the latent generating coefficients.

## 14 3 Why this check matters
A known answer distinguishes implementation correctness from a plausible-looking chart. Regression can be checked against the exact coefficients, Newton against the known derivative root, and optimization against endpoint comparison. The example establishes a reproducible reference case, while broader tests cover failure states, nonlinear coefficients, capacities, and price grids.

<!-- page -->
# 15 Testing and Verification
## 15 1 Checks rerun on 27 October 2026
| Check | Executed command | Observed result |
| --- | --- | --- |
| Backend tests | backend/.venv/Scripts/python.exe -m pytest backend/tests -q | 126 passed; one dependency deprecation warning |
| Independent numerical oracle | backend/.venv/Scripts/python.exe scripts/verify_numerical_oracle.py | 250 seeded cases passed; largest oracle revenue excess 1.16 × 10⁻¹⁰ |
| Production frontend build | npm run build in frontend | Passed; bundle-size advisory emitted |
| Frontend state and workflow | npm test in frontend | 11 passed and 0 failed |
| Frontend lint | npm run lint in frontend | Passed with no reported errors |

The backend tests cover coefficient recovery, metrics, invalid input, grouping, API behavior, Newton failure states, boundaries, capacities, and numerical edge cases. The independent oracle uses exhaustive 20,001-point continuous scans or exact discrete grids. Its numerical agreement applies to those generated cases and does not measure predictive accuracy on real events.

Frontend tests cover invalidation after changing the dataset, model, bounds, or capacity; delayed responses; source-row order; first-time sample settings; and scenario or export state. A successful production build verifies compilation and bundling, while lint checks configured code diagnostics. Neither proves that every interaction is usable.

## 15 2 Existing browser and export evidence
The implementation audit records Chromium checks of all nine routes at 1440 × 1000, 768 × 1024, and 390 × 844. It records sample and upload workflows, invalid-data recovery, model selection, scenarios, eight downloads, and representative screenshots. Additional checks cover mobile drawer keyboard behavior and preservation of scenario assumptions in exports. These are prior recorded checks, not browser runs repeated for this report.

The audit also records parsing and visual inspection of application-generated PDFs. Screenshot evidence used in Chapters 11 and 12 is drawn from those recorded artifacts.

## 15 3 Qualifications
One backend warning concerns deprecated HTTPX use in the dependency test-client path. Vite reports that the approximately 1,026 kB minified JavaScript bundle exceeds its advisory threshold. These warnings do not fail the executed checks. No test-coverage percentage, general performance benchmark, cross-browser certification, or independent field validation is asserted.

<!-- page -->
# 16 Installation and Execution
## 16 1 Backend setup
Open PowerShell at the PricePilot repository root. Create a virtual environment and install the backend requirements. The following commands assume Python is available on PATH.

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal open. The application API runs at http://127.0.0.1:8000. Confirm that http://127.0.0.1:8000/api/v1/health responds, and inspect interactive API documentation at http://127.0.0.1:8000/docs.

## 16 2 Frontend setup
Open a second PowerShell terminal at the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open the local URL printed by Vite, normally http://localhost:5173. The development proxy forwards /api requests to the backend. If a port changes, keep the proxy destination and backend port consistent. Both processes must remain running while using the application.

## 16 3 Reproducing checks and samples
From the root, run the backend suite and oracle with the project virtual-environment Python. In frontend, run npm test, npm run build, and npm run lint. The browser scripts additionally require Playwright and a compatible Chromium installation; the implementation audit explains their setup.

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
.\backend\.venv\Scripts\python.exe scripts\verify_numerical_oracle.py
.\backend\.venv\Scripts\python.exe scripts\generate_sample_data.py
```

The last command regenerates the three demonstration CSVs. Preserve the actual dataset and dependency lockfiles with a submitted project so the calculations can be reproduced. The backend dependency snapshot is backend/requirements-lock.txt; frontend installation uses its package lockfile.

<!-- page -->
# 17 User Guide and Demonstration
## 17 1 Recommended demonstration sequence
1. Open Dataset Studio and load Standard College Events. Explain that the 80 rows are synthetic and inspect prices, row counts, and validation status.
2. Open Demand Modeling and fit the eligible models. Compare the curves and held-out errors, then explain the selected final quadratic.
3. Open Revenue Optimization. Use price bounds 50 to 170 with a valid starting guess. Explain that a nonbinding capacity gives the same result as the uncapped reference configuration.
4. Run optimization and inspect the result near 95.98. Show the real Newton trace, negative second derivative, candidate comparison, and scan agreement.
5. Open Scenario Simulator. Compare price 100 with the recommendation, then demonstrate a clearly labeled hypothetical demand multiplier.
6. Open Model Diagnostics and Mathematical Walkthrough. Explain residuals, RMSE, the normal equations, and the revenue derivative.
7. Open Reports and Exports. Download the current JSON, CSV, chart, or PDF and confirm that its settings match the visible analysis.

## 17 2 Working with uploaded data
Provide event_id, ticket_price, and tickets_sold as the required CSV headers, or explicitly map equivalent headers. Use plain numeric prices and whole-ticket sales. Inspect all rejected rows, duplicate warnings, and capacity warnings. Correct or exclude problematic records visibly, select a comparable group, and revalidate before fitting. Many rows at one price do not replace independent price variation.

## 17 3 Common problems
| Condition | Interpretation and action |
| --- | --- |
| API connection fails | Confirm the backend is running and the proxy uses its port |
| Too few distinct prices | Add observations at independent price levels |
| Quadratic is unavailable | Use the line or provide enough valid rows and price levels |
| Sellout warning | Explain censored sales or use more suitable observations |
| Newton failure | Inspect start, bounds, denominator, and derivative residual |
| Negative demand or extrapolation | Narrow the interval or reconsider the fitted model |
| An earlier result disappears | Recompute after input or configuration changes |

Save necessary exports before refreshing or closing the page. The working analysis is held in application memory; downloaded JSON is an analysis record and is not automatically a supported restore mechanism.

<!-- page -->
# 18 Limitations Future Scope and Conclusion
## 18 1 Limitations
The fitted relationship uses price alone. Differences in performers, promotion, audience, timing, location, and competition may confound it. Pooling unrelated events can produce a misleading demand curve, and a category label does not prove comparability. Observational association does not establish the effect of changing a price.

Recorded sales at capacity are censored observations of latent demand. Ordinary least squares does not correct this censoring. Polynomial extrapolation may become increasing or negative outside observed support. A high training R² can coexist with weak generalization, and the current single random holdout does not establish future-time forecast accuracy. Grouped splitting relies on accurate event identifiers.

Newton–Raphson can fail or identify a local minimum. Candidate comparison addresses the specified low-degree constrained problem, while the finite scan remains an approximate cross-check. Floating-point arithmetic introduces small numerical differences. Revenue excludes operating costs, and deterministic capacity does not model cancellations, queues, changing inventory, or multiple ticket tiers.

Included data are synthetic. No independent real event dataset, causal experiment, uncertainty interval, or guarantee of business effectiveness is established. The local application is not a production ticketing platform. The scenario multiplier represents an assumption and does not change the base optimization.

## 18 2 Future scope
Useful extensions include chronological validation, repeated cross-validation, uncertainty intervals, multivariable demand models, and methods for censored sales. Cost information could support profit optimization. More complex ticketing studies could examine multiple tiers, time-varying demand, and inventory allocation. Persistent storage and deployment hardening would be needed for broader multi-user use. These items are proposed extensions rather than implemented features.

## 18 3 Conclusion
PricePilot implements an inspectable connection between least-squares demand fitting and numerical revenue analysis. It turns validated observations into fitted curves, derives a revenue objective, shows Newton–Raphson iterations, and compares feasible candidates under bounds and optional capacity or price increments. The exact linear reference agrees with its algebraic answer, and automated checks support the implemented numerical and application behavior.

The educational contribution is the complete explanation from input data to constrained recommendation. Practical use would require stronger evidence about comparable events, censoring, omitted variables, and uncertainty before treating the modeled price as an operational decision.

<!-- page -->
# References
## Official technical documentation
[1] NumPy. numpy.linalg.lstsq API reference. Explains the least-squares solver used by the numerical core. Accessed 27 October 2026.
https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html

[2] FastAPI. Official documentation. Reference for the backend framework and interactive API documentation. Accessed 27 October 2026.
https://fastapi.tiangolo.com/

[3] React. Official documentation. Reference for the component-based frontend framework. Accessed 27 October 2026.
https://react.dev/

[4] Pydantic. Official validation documentation. Reference for typed request contracts and validation. Accessed 27 October 2026.
https://docs.pydantic.dev/latest/

## Project implementation sources
The mathematical derivations in Chapters 5 to 8 are written explicitly and correspond to backend/app/core/regression.py and backend/app/core/optimization.py. Data rules and generation details are defined in validation.py, data_generation.py, and data/data_dictionary.md. API contracts are defined in backend/app/schemas/schemas.py and backend/app/api/routes/routes.py.

Numerical examples and recorded interface evidence are documented in docs/mathematical_foundation.md, docs/testing_and_validation.md, and docs/implementation_audit.md. The standard sample and its limitations are described in data/data_dictionary.md. Installation and usage are described in README.md and docs/user_guide.md.

Screenshots in this report are local verification artifacts from output/verification/browser: desktop-dataset.png, extended-model-overlay.png, extended-convergence.png, and extended-diagnostics.png. They are evidence of the implemented synthetic demonstration interface.

The automated verification results in Chapter 15 were rerun on 27 October 2026. Earlier browser results are identified separately as recorded audit evidence. No unverified textbook edition, survey, publication, or field study is cited.

<!-- page -->
# Appendix A Viva Preparation
## Why use least squares
The observations generally do not lie exactly on a simple curve. Least squares selects coefficients that minimize total squared prediction error and gives a reproducible fit rather than a manually chosen curve.

## Why center and scale prices
Price powers can have very different magnitudes. Centering and scaling improve the numerical representation of the design matrix. Coefficients are then transformed back so the equation remains interpretable in the original currency units.

## Why avoid explicitly inverting the normal equations
The normal equations explain the derivation, but forming and inverting XᵀX can amplify numerical conditioning problems. PricePilot instead solves the scaled least-squares problem using NumPy's solver.

## Why apply Newton to the revenue derivative
An interior differentiable optimum must satisfy R′(p) = 0. Newton–Raphson finds a root of this equation using R″(p) as the tangent slope. It is not applied directly to make revenue equal zero.

## Does Newton convergence prove the best price
No. A root can be a minimum, and an endpoint or capacity transition can earn more. The second derivative gives a local classification; feasible candidate comparison determines the recommendation for the configured problem.

## Why can the quadratic have higher training R² yet be rejected
Additional flexibility can reduce training error without improving new-observation predictions. PricePilot compares held-out RMSE when available and checks support and demand shape before recommending the quadratic.

## What does capacity change
Expected realizable sales cannot exceed the configured capacity. The revenue function becomes piecewise, and the point where demand reaches capacity becomes a candidate even when it is not an uncapped stationary point.

## Are the data and results real business evidence
The included datasets are synthetic. The exact reference and automated checks support numerical correctness for tested cases. They do not validate demand forecasts for actual events or establish causal revenue improvement.

## Why is the recommended sales count fractional
The fitted curve represents an expected value, which can be fractional. Actual observed ticket counts must be whole numbers. A fractional expectation does not mean a fractional ticket is sold.

## What should be emphasized in the demonstration
Explain the two numerical methods, the exact 125 reference, the actual Newton trace, the separate feasible candidate comparison, and the limitations of the synthetic demand model.
