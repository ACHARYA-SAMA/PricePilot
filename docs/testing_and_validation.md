# Testing and validation notes

The final test commands, exit codes, browser evidence, and unresolved gaps belong in [the implementation audit](implementation_audit.md). This document explains what the checks establish and records one directly executed reference check. A test-file name alone is not evidence of a pass.

## Executed mathematical reference on 26 October 2026

A direct Python invocation imported `fit_linear`, `fit_quadratic`, and `run_optimization` from `backend/app/core`. Input prices were `[25,50,75,100,125,150,175,200]`.

For noiseless `y=500-2p`, the actual output was:

```text
linear coefficients: a = 499.9999999999999, b = -1.9999999999999993
optimum:             125.00000000000001
predicted demand:    249.99999999999994
realizable revenue:  31249.999999999996
Newton converged:    True
```

Bounds were `[25,200]`, initial guess was `100`, and no capacity was supplied. The Python command exited `0`. Independent algebra gives `R'(p)=500-4p`, so the exact stationary price is `125`; `R''=-4` establishes a strict local maximum. Endpoint revenues `11,250` and `20,000` are smaller than `31,250`. Agreement to floating-point precision verifies this reference case; it does not validate arbitrary inputs or real-world outcomes.

For noiseless `y=600-2p-0.001p²`, the same invocation recovered:

```text
a = 599.9999999999993
b = -1.9999999999999902
c = -0.0010000000000000378
```

This verifies coefficient recovery for this known polynomial. It is distinct from fitting noisy, clipped, or capacity-censored samples, where exact recovery of latent generating coefficients is not expected.

## Reproducible reference command

Run from the repository root in PowerShell:

```powershell
@'
import sys
import numpy as np
sys.path.insert(0, "backend")
from app.core.regression import fit_linear, fit_quadratic
from app.core.optimization import run_optimization
p = np.array([25., 50., 75., 100., 125., 150., 175., 200.])
linear = fit_linear(p, 500 - 2*p)
result = run_optimization(linear.coefficients, p_min=25, p_max=200, p0=100)
quadratic = fit_quadratic(p, 600 - 2*p - .001*p*p)
assert np.allclose([linear.coefficients.a, linear.coefficients.b], [500, -2])
assert np.allclose([result.optimal_price, result.optimal_demand,
                    result.optimal_realized_revenue], [125, 250, 31250])
assert np.allclose([quadratic.coefficients.a, quadratic.coefficients.b,
                    quadratic.coefficients.c], [600, -2, -.001])
print(result.optimal_price, result.optimal_demand, result.optimal_realized_revenue)
print(quadratic.coefficients)
'@ | python -
```

## Verification layers

1. **Unit mathematics:** known coefficient recovery, residual identities, undefined metrics, rank failure, Newton convergence/failure, minima, bounds, capacity kinks, and discrete-price feasibility.
2. **API integration:** actual request/response validation, sample data, upload failure recovery, finite JSON, whole-event holdout isolation and partition metadata, current-configuration reporting, diagnostic plot data, hypothetical scenario scaling, and export alignment.
3. **Independent numerical checks:** analytical stationary roots and bounded scans against the candidate winner.
4. **Frontend build and lint:** type errors and configured static diagnostics. These do not prove usability.
5. **Browser interaction:** sample flow, invalid upload, model selection, optimization, scenario changes, download contents, stale-result invalidation, and representative viewport sizes.
6. **PDF review:** text/content checks and rendered page inspection. Text extraction alone cannot prove that layout is readable.

Use numerical tolerances appropriate to scale rather than exact binary equality. Undefined values must not be hidden as fabricated zeros. Report both failures and successful checks. No test coverage percentage or benchmark is claimed without a separately executed measurement.
