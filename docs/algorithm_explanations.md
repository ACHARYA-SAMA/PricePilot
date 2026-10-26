# Algorithm explanations

The following pseudocode explains the implemented numerical approach. Configuration limits and request contracts live in the source; the final implementation audit records executed checks. All numerical outputs originate in Python.

## CSV validation

**Input:** CSV bytes, filename, and optional explicit header mapping. **Output:** cleaned eligible records, rejected records, row-level issues, warnings, summary counts, and model-eligibility flags.

```text
reject a disallowed filename/type or oversized input
decode and parse the CSV; report parse failure without inventing rows
check row-count limit and normalize unambiguous header aliases
apply only explicit mappings for ambiguous/unrecognized required headers
require event_id, ticket_price, tickets_sold
for each original record:
    check a nonempty event ID
    parse price and sales without substituting zero on failure
    require finite price > 0
    require finite whole-number sales >= 0
    validate any supplied capacity; reject sales above that capacity
    report duplicate records and optional-field inconsistencies
    retain original row location with any errors
separate accepted and rejected rows
compute accepted-record summaries and capacity-censoring warnings
assess independent price variation and conservative fitting thresholds
return structured results
```

**Failures:** unreadable content, malformed records, missing required headers, nonfinite numbers, invalid signs, fractional ticket counts, invalid capacity, and too few distinct prices. The recovery action is to correct/match the headers or records, or select more suitable data. Excluding invalid rows must be visible to the user. A valid parse does not imply that regression is eligible.

## Linear regression

**Input:** finite price and sales arrays. **Output:** coefficients in original currency units, predictions, residuals, diagnostics, normal-equation sums, stability status, and warnings.

```text
check compatible array lengths and >= 2 independent price levels
mu = mean(prices); s = nonzero sample price standard deviation
t = (prices - mu) / s
X = columns(ones, t)
solve min ||X * theta - sales|| using numpy.linalg.lstsq
check rank == 2, conditioning, and finite results
convert alpha,beta_t to a = alpha - beta_t*mu/s; b = beta_t/s
predict at original prices using unrounded a,b
compute residuals and diagnostics
compute original-basis sums for the explanatory normal equations
return the fit, labeling any instability
```

The mathematical minimum is two independent observations. CSV eligibility additionally uses a practical row-count policy. Identical prices cannot identify a price slope.

## Quadratic regression

**Input/output:** the same structure as a linear fit, with coefficient `c`.

```text
require >= 3 independent price levels
center and scale prices as for a line
X = columns(ones, t, t*t)
solve least squares; require full rank 3
recover a,b,c using the change-of-basis formulas
predict using a + b*p + c*p*p without rounding coefficients
compute residuals, diagnostics, rank/condition warnings, normal-equation sums
return the fit
```

Mathematical estimability and practical recommendation are separate. The CSV validator requires at least six records and three distinct prices for quadratic eligibility. Automated recommendation uses a stronger threshold: at least twelve records and six distinct prices. These policy thresholds do not eliminate overfitting or guarantee statistical reliability.

## Model comparison

**Input:** one selected comparable dataset, eligibility flags, seed. **Output:** final full-data fits, holdout metric objects when available, recommendation and reason.

```text
if n >= 15 and event IDs are unique:
    permute record indices with fixed seed 42
    assign floor(0.8*n) records to training, the remainder to validation
else if n >= 15 and repeated event IDs have >= 5 independent groups:
    permute independent groups with seed 42
    assign floor(0.8*group_count) entire groups to training
    assign all remaining entire groups to validation
else:
    report that a reliable holdout is unavailable
if a proposed holdout exists:
    check independent price levels, rank, and conditioning in both partitions
    disable the holdout with an explicit warning if either is inadequate
if holdout remains eligible:
    fit each eligible model only on training records
    predict untouched validation records and compute validation errors
fit each eligible final model on all selected records
check stability and plausible demand shape
select the quadratic only when justified by the configured evidence policy
prefer a stable simpler model when errors are similar
return separate full-data fits and holdout evaluation results
return split_strategy and zero-based train_indices/val_indices
```

The 5% validation-RMSE improvement rule is a decision heuristic, not a hypothesis test. Holdout objects retain their evaluation-stage coefficients; final full-data coefficients may differ. Repeated IDs trigger whole-event grouping, preventing an identified event from appearing in both partitions. The 80/20 ratio applies to groups rather than rows in that case. Correct isolation depends on accurate event IDs. The split is randomized, not chronological; future-time forecasting remains unvalidated.

## Diagnostics

```text
residual = actual - predicted
SSE = sum(residual**2)
MAE = mean(abs(residual))
RMSE = sqrt(SSE / n)
SST = sum((actual - mean(actual))**2)
R2 = undefined if SST == 0 else 1 - SSE/SST
adjusted_R2 = undefined if R2 undefined or n-k-1 <= 0
              else 1 - (1-R2)*(n-1)/(n-k-1)
```

For a quadratic, demand monotonicity follows from `D'(p)=b+2cp`; its extrema on an interval are at the derivative's endpoints. Demand positivity must also consider an interior quadratic vertex. A finite chart grid alone can miss a narrow invalid interval.

## Newton-Raphson

**Input:** fitted coefficients, initial guess `p0`, bounds, iteration limit, step tolerance and derivative-residual tolerance. **Output:** actual trace, convergence/failure status, candidate stationary price only when justified, and second-derivative classification.

```text
p = p0
reject a nonfinite or out-of-bounds start
for k = 0 .. max_iterations-1:
    f = R_prime(p); fp = R_second(p)
    if abs(f) <= derivative_tolerance:
        return converged at p, with current residual verified
    if fp is too small:
        return failed_zero_derivative
    correction = -f / fp
    next_p = p + correction
    record the actual p,f,fp,correction,next_p,absolute step
    if next_p is nonfinite: return failed_nonfinite
    if next_p leaves the allowed interval: return failed_out_of_bounds
    next_residual = R_prime(next_p)
    if abs(next_residual) <= derivative_tolerance:
        return converged at next_p
    if abs(next_p-p) <= price_tolerance:
        return failed_stagnation
    p = next_p
return failed_max_iterations
```

The exact trace and status depend on the input and floating-point arithmetic. No iterations are manufactured for teaching. Step tolerance alone cannot establish convergence. A failure does not erase the possibility that a valid boundary or independently recovered stationary point is the global feasible winner; that recovery must be labeled separately.

At a converged root, evaluate `R''`: negative means local maximum, positive means local minimum, and effectively zero is inconclusive. Check feasibility independently of classification.

## Feasible revenue maximization

**Input:** demand coefficients, positive bounds `L<U`, Newton controls, optional capacity `C`, optional increment `h`. **Output:** candidate table, winning feasible price and revenues, source/classification, scan comparison, warnings.

```text
validate finite bounds, tolerances, capacity and optional increment
run explicit Newton-Raphson and keep its status independently
recover all real polynomial roots of R_prime(p)=0
collect stationary candidates, L, U, and roots of D(p)=0
if capacity supplied: also collect roots of D(p)=C
for each candidate:
    compute raw demand and mark negative-demand regions infeasible
    compute realizable sales = min(max(demand,0),C) when C exists
    compute polynomial and realizable revenues
if a price increment is required:
    project each region's stationary point and boundary to adjacent grid prices
    retain valid multiples of h inside [L,U]
    compare these discrete candidates, or report an empty feasible grid
else:
    compare all feasible continuous candidates
choose the largest feasible realizable revenue and classify its source
independently compare with a bounded numerical scan
return actual candidates, trace, result and warnings
```

Why adjacent grid prices suffice here: within each smooth region, a polynomial maximum over a regular grid occurs next to a continuous stationary point or at a region boundary. Capacity transitions and demand-zero boundaries partition the regions; including floor/ceiling neighbors of every relevant boundary avoids rounding across an invalid region. This is specific to the low-degree piecewise polynomial modeled here, not a generic discrete-optimization theorem for arbitrary functions.

The scan evaluates discrete prices for a manageable grid; very large grids use a bounded approximate cross-check rather than allocating unbounded memory. A scan disagreement must be visible. Scan agreement is numerical evidence with finite resolution, not proof of real-world accuracy.

## Scenarios and reporting

Scenarios evaluate the selected final demand model at submitted prices. The optional `demand_multiplier` must be finite and satisfy `0 < factor <= 10`. It is explicitly hypothetical: multiply the fitted demand by the factor before applying capacity. The baseline uses the same factor, so the comparison holds that assumption constant. This does not modify the base optimization or estimate a causal effect. Scenarios report raw demand and capacity-limited realized sales. Negative raw demand is flagged; it must not become an apparently reliable zero-sales estimate. Baseline percentage revenue change is undefined when baseline revenue is zero.

Reports and exports should be generated from the active dataset, selected model, and current constraints. Rendering a file is not enough: verify its contents match those inputs. Report-generation, export alignment, stale-state handling, and browser checks are documented in the final implementation audit.

The backend exposes `/regression/compare` as an alias for the comparison performed by `/regression/fit`, and `/diagnostics/evaluate` supplies backend-calculated diagnostic plot data. Export routes include predictions/residuals/scenarios CSVs and SVG/PNG charts. The report's scenario section records active scenario prices and their hypothetical multiplier separately from the unchanged base optimization. Exported analysis includes split strategy and zero-based partition indices for reproducibility.
