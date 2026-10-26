# Limitations and interpretation

## What a result means

PricePilot estimates a revenue-maximizing price **within a specified model and feasible interval**. It does not establish the true best event price or guarantee sales. A correct optimization can still rely on a poor demand model.

- Price is the sole fitted predictor. Marketing, performers, audience, timing, venue, and competition are not controlled for.
- Observational association is not proof that a price change causes the predicted sales change.
- Revenue excludes costs. The recommended price does not necessarily maximize profit.
- Demand is a continuous fitted expectation; a fractional expected ticket count is not a promise that a fractional ticket can be sold.
- The standard and sellout files are synthetic demonstrations. No independent real-world sales validation has been established.

## Data and evaluation

- Observations must represent comparable offers and audiences. Pooling unrelated event types can create a misleading curve.
- A sold-out observation only shows that demand was at least the recorded capacity. Ordinary least squares does not estimate latent demand under censoring.
- Few distinct price levels provide weak information about price response even if many rows are present.
- A quadratic can fit training data better while predicting future data worse.
- The implemented holdout isolates entire events when IDs repeat and sufficient independent groups exist; unique event IDs use a seeded random row split. Correct isolation depends on accurate IDs for all records from the same underlying event. Incorrect or inconsistent IDs can still allow related observations to cross partitions.
- Holdout assignment is randomized rather than chronological. It does not validate forecasting future events under time drift. Insufficient group counts or independent price variation disable holdout evaluation with an explicit warning.
- A single holdout split is not cross-validation, and its error estimates vary with the sample. Confidence intervals and uncertainty bands are not claimed.
- Full-data fit metrics describe the final refit. Held-out metrics come from evaluation-stage models trained without held-out records; the coefficients can differ.

## Numerical and economic limits

- Polynomial demand can become negative or increase implausibly outside observed prices. Invalid-demand regions must be flagged; extrapolation is exploratory.
- Newton-Raphson can fail, leave bounds, stagnate, or find a local minimum. Its failure status remains visible even if independent candidate comparison finds a feasible winner.
- A second derivative test is local. Interval endpoints and capacity transitions may win globally.
- A finite numerical scan is an approximate cross-check with limited resolution.
- Very large price grids require bounded verification rather than unlimited point enumeration.
- Floating-point values differ slightly from exact algebra. Calculations retain full precision; displayed currency is rounded.
- Capacity is a deterministic cap. The model does not simulate queues, inventory uncertainty, cancellations, dynamic release schedules, or multi-tier ticket allocation.
- A scenario demand multiplier is a user-supplied hypothetical assumption, bounded to `(0,10]`. It scales demand before applying capacity and uses the same factor for baseline comparisons. It is not a fitted causal effect and does not change the base optimization result.

## Scope and verification

This project is intended for local demonstration with a bounded CSV upload, not multi-user production hosting. Uploaded student data should remain within the local processing flow. Browser responsiveness, export correctness, PDF layout, and API recovery need executed checks; they must not be inferred from source files.

The [implementation audit](implementation_audit.md) is the authoritative record of which requirements were verified, which remain incomplete, and which could not be tested in the environment. This document does not claim test coverage percentages, performance benchmarks, certification, or validation against actual event outcomes.

Possible future work includes chronological validation, repeated cross-validation, censored-demand estimation, uncertainty intervals, cost/profit modeling, and multivariable analysis. These are future directions, not completed features.
