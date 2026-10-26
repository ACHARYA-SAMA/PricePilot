# PricePilot - Event Revenue Optimizer

Academic project report draft. Prepared 26 October 2026. Replace institution, author, supervisor, and submission details only with actual information. This draft does not invent those details.

## Abstract

PricePilot explores ticket-price decisions through least-squares demand fitting and explicit Newton-Raphson iterations. Historical price/sales observations are validated before linear and quadratic demand models are compared. Revenue is formed as price multiplied by modeled demand. A candidate comparison handles stationary points, price endpoints, nonnegative-demand boundaries, capacity transitions, and optional price grids. The React interface is connected to a Python/FastAPI numerical engine so displayed results and exported analyses can share one computational source. Included demonstrations are synthetic. An executed exact linear reference reproduced the theoretical price 125, demand 250, and revenue 31,250 to floating-point precision. The project illustrates numerical methods; it does not establish causal price effects or validate predictions against independent real event sales.

## 1. Introduction and motivation

Event organizers face a tradeoff: higher ticket prices earn more per ticket but can reduce demand. A fixed observed price does not reveal how revenue would change at another price. Mathematics supplies an explicit model of this tradeoff and a way to inspect the calculations rather than accepting an unexplained recommendation.

The project connects **Unit V: Least-Squares Curve Fitting and Regression** with **Unit II: Newton-Raphson**. It emphasizes numerical correctness, transparent intermediate steps, feasible choices, and honest limitations. A polished interface supports explanation but does not replace mathematical evidence.

## 2. Problem statement

Given finite observations `(p_i,y_i)` from comparable events or price offers, fit a price-demand relationship and estimate the price maximizing predicted ticket revenue inside a user-specified interval, optionally limited by venue capacity and a ticket-price increment. Show how the estimate was obtained, how the competing models behave, and when a confident recommendation is unsupported.

## 3. Objectives

1. Validate CSV records without silently converting invalid numeric cells to zero.
2. Estimate linear and quadratic demand coefficients using stable least squares.
3. Calculate residuals, SSE, MAE, RMSE, R², and adjusted R² where defined.
4. Compare models using held-out errors when sufficient data is available.
5. Explicitly iterate Newton-Raphson on the revenue derivative and preserve failure states.
6. Compare all relevant feasible candidates rather than assuming every stationary point is a maximum.
7. Explain calculations through equations, traces, plots, scenarios, and exports.

The final implementation audit, rather than this list of objectives, determines which acceptance requirements have been verified.

## 4. Mathematical background

Least squares minimizes the sum of squared discrepancies between observed and modeled demand. For a linear model, `D(p)=a+bp`; for a quadratic, `D(p)=a+bp+cp²`. The normal equations follow by differentiating the objective with respect to every coefficient and setting the derivatives to zero.

Writing `Xβ≈y`, the normal equations are `XᵀXβ=Xᵀy`. For a quadratic, the matrix contains the sums of price powers through the fourth power. The application exposes these sums for academic explanation but solves the scaled design system using `numpy.linalg.lstsq`; direct inversion of `XᵀX` is avoided because it magnifies numerical conditioning problems.

For quadratic demand, revenue is `R(p)=ap+bp²+cp³`, so `R'(p)=a+2bp+3cp²` and `R''(p)=2b+6cp`. Newton-Raphson applies the tangent-line root approximation to `f=R'`, giving

\[
p_{n+1}=p_n-\frac{a+2bp_n+3cp_n^2}{2b+6cp_n}.
\]

The derivative residual must be small at a claimed root. A negative second derivative indicates a local maximum, a positive one indicates a local minimum, and a zero second derivative is inconclusive. Endpoints and piecewise capacity transitions must still be checked. Full derivations appear in `mathematical_foundation.md`.

## 5. Methodology

### Data preparation

Only event ID, ticket price, and tickets sold are mandatory. Additional descriptors support inspection and grouping but do not become fitted predictors automatically. Validation reports missing required fields, invalid numeric values, inappropriate signs, fractional counts, duplicates, capacity inconsistencies, and insufficient price variation. The analysis should use a deliberately selected comparable group.

### Model estimation and evaluation

Prices are centered and scaled before fitting. Final coefficients are transformed to original currency units and used without rounding during prediction. Rank and conditioning checks separate a numerical output from a credible model estimate.

When at least fifteen observations exist and event IDs are unique, an 80/20 random row split with seed 42 supplies a reproducible holdout. Repeated event IDs instead trigger whole-event splitting, requiring at least five independent groups and targeting an 80/20 ratio of groups rather than rows. Either strategy is disabled with an explicit warning if a partition lacks sufficient independent price variation, rank, or conditioning. Both candidate models use the same evaluation split. The final active models are refitted on all selected records, while holdout metrics retain their evaluation-stage coefficients. Responses export `split_strategy` and zero-based training/validation indices. Accurate IDs are necessary for correct event isolation; chronological forecasting validation remains outside the implementation.

### Feasible optimization

The algorithm retains the actual Newton trace separately from independent stationary-root recovery. It adds interval boundaries, demand-zero roots, and capacity-transition roots. For capacity `C`, realized expected sales are `min(max(D(p),0),C)`. Negative polynomial-demand regions are flagged rather than treated as reliable predictions. The best feasible revenue is selected from the relevant candidates. If a grid is required, adjacent grid prices around region boundaries/stationary points are compared. A bounded scan supplies an approximate independent numerical check.

## 6. System architecture

The frontend manages interaction and visualization; the backend owns CSV processing, numerical fitting, diagnostics, optimization, scenarios, and report calculations. No separate JavaScript implementation of regression or optimization is required. API contracts use Pydantic; frontend calls use typed TypeScript structures. State changes must invalidate dependent results to avoid showing an old optimization beside new diagnostics.

There is no paid service, user account requirement, AI API, or database dependency for local use. The stack is React/TypeScript/Vite on the client and FastAPI/NumPy/Pandas on the server, with Recharts/KaTeX for presentation and Matplotlib/ReportLab for reports. Backend diagnostics supply actual-versus-predicted points, a reference diagonal, residual histogram data, and fit-curve overlays. `/regression/compare` aliases the comparison endpoint; `/diagnostics/evaluate` supplies diagnostic results. Residual/scenario CSVs and SVG/PNG charts extend the export routes. The PDF scenario section records the active scenario prices and hypothetical demand multiplier separately from the unchanged base optimization. Repository structure and run commands appear in the README. The audit records which interface and export paths were actually exercised.

## 7. Results obtained from executed synthetic/reference calculations

### Exact linear reference

Eight noiseless points were generated at prices `[25,50,75,100,125,150,175,200]` from `D(p)=500-2p`. A direct Python engine invocation on 26 October 2026 recovered:

| Quantity | Actual output | Exact theoretical value |
|---|---:|---:|
| Intercept `a` | 499.9999999999999 | 500 |
| Slope `b` | -1.9999999999999993 | -2 |
| Feasible maximizing price | 125.00000000000001 | 125 |
| Predicted demand | 249.99999999999994 | 250 |
| Revenue | 31249.999999999996 | 31,250 |

The interval was `[25,200]`, start was `100`, and no capacity bound was supplied. Newton reported convergence. Independent algebra gives `R'=500-4p`, `R''=-4`; both endpoint revenues are lower. This checks the reference algorithm case and floating-point behavior, not event-market accuracy.

### Exact quadratic coefficient recovery

Using the same prices and noiseless `D(p)=600-2p-0.001p²`, the executed recovered coefficients were `(599.9999999999993,-1.9999999999999902,-0.0010000000000000378)`. The agreement with `(600,-2,-0.001)` is within floating-point precision. No noisy sample is expected to reproduce latent coefficients exactly.

### Standard synthetic demonstration

The final standard generator was adjusted to sample prices from 50–170 with capacities 800–1000. Its fixed seed 42 produces 80 rows, 13 distinct prices, no zero-sales rows, and no sold-out rows. The underlying mechanism is `800-3.5p-0.005p²+ε`, with Gaussian noise standard deviation 15 tickets and whole-ticket rounding. All category labels share this one simulated mechanism.

The following direct-engine outputs were observed after that correction:

| Metric | Final linear fit | Final quadratic fit |
|---|---:|---:|
| Full-data observations | 80 | 80 |
| Intercept | 846.4819874274663 | 767.9111636686947 |
| Linear coefficient | -4.536774661508704 | -2.9578133146008936 |
| Quadratic coefficient | Not applicable | -0.007240275982627887 |
| Full-data RMSE | 15.38153579770667 | 13.641308769342585 |
| Full-data R² | 0.9890053080076514 | 0.9913523969744223 |
| Held-out RMSE, 16 observations | 14.972699920452937 | 14.102831552982643 |

The comparison selected the quadratic. Optimizing its final full-data coefficients on `[50,170]` without capacity or price-grid restriction gave price `95.98332850384918`, modeled demand `417.3071867688157`, and revenue `40054.53279464838`. Newton converged in three recorded iterations; the second derivative was `-10.0853013577964`, and the result was classified as an interior maximum. The scan reported agreement, with scan price `95.99319863972795`.

These are **simulated results** from an executed engine invocation. They are not observed business improvement, an independent field trial, or proof that real events obey the model. The held-out coefficients differ from final-refit coefficients, as expected.

## 8. Testing and quality assurance

Mathematical tests should cover known coefficient recovery, residual identities, undefined metrics, independent-price requirements, Newton failure modes, boundary winners, capacity transitions, negative-demand infeasibility, and discrete grids. API checks should exercise actual request validation and current-state export alignment. Browser testing must exercise complete flows and representative viewport sizes. Report content and rendered layout need direct inspection.

No final total test count, coverage percentage, browser-success assertion, performance benchmark, or completion claim is inferred here. Consult `implementation_audit.md` for the actual final commands, exit codes, artifacts, failures, and remaining requirements.

## 9. Discussion

The reference results demonstrate agreement between the implemented numerical engine and independently derived algebra. The standard sample illustrates how a quadratic can improve held-out prediction modestly while retaining a decreasing demand shape. The recommended price arises from a fitted model and configured interval, not from a hardcoded demonstration value.

Capacity changes the problem from a smooth polynomial to a piecewise objective. This makes the candidate comparison academically significant: Newton alone cannot establish the constrained global maximum. Similarly, algorithmic convergence and economic plausibility answer different questions and must be reported separately.

## 10. Limitations

Price alone cannot explain every difference between events. Capacity-censored sales underestimate latent demand, and ordinary least squares does not correct them. Grouped holdouts isolate repeated event IDs, but their validity depends on accurate event identification; random group/row splits do not test future-time forecasting. No prediction intervals or real-world validation are established. Polynomial extrapolation can become implausible. Revenue omits costs. A finite scan is an approximation, and floating-point arithmetic is inexact. The local application is not a production multi-user ticketing system. Hypothetical scenario multipliers are assumptions, not fitted causal effects.

## 11. Conclusion

PricePilot provides an inspectable connection between least-squares fitting and numerical revenue analysis. The directly executed reference cases agree with exact mathematical expectations within floating-point precision. The simulated demonstration supports explanation of the methods, while the final audit determines the verified application status. Practical pricing decisions require additional evidence about comparability, censoring, confounding, and uncertainty.

## 12. Future scope

Possible extensions include chronological validation, repeated cross-validation, uncertainty intervals, censored-demand estimation, cost/profit models, and multiple explanatory variables. None should be presented as implemented merely because it appears in this section.

## References and source transparency

The algebraic derivations in this report are written explicitly and can be checked directly. No unverified paper title, author list, publication year, DOI, or textbook edition is supplied. Implementation sources are the repository modules `regression.py`, `optimization.py`, `validation.py`, `diagnostics.py`, `simulation.py`, `reporting.py`, and the synthetic generator. Library usage is documented by the installed packages and their source/API documentation. Add institutional bibliography requirements only after verifying the actual bibliographic details of the sources used.
