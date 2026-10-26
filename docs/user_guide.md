# PricePilot user guide

## Starting and recovering the application

Follow the two-terminal commands in the repository README. Keep the local FastAPI backend running while using the Vite frontend. A connection error usually means the backend is stopped or its port does not match the frontend proxy. Check `http://127.0.0.1:8000/api/v1/health`, then retry the requested operation.

PricePilot keeps the current analysis in application memory. Save required exports before closing or refreshing the page. An export is a record of the input/configuration at export time; it is not a promise of permanent cloud storage.

## 1. Load and inspect data

Start with **Standard College Events** for a clean demonstration. The 80 records are generated, not collected. They follow one shared synthetic demand mechanism across illustrative category labels. Prices span 50–170; capacities are deliberately above generated sales so this standard sample is not censored.

Use **Sold-Out Events** to understand capacity warnings. Its fixed capacity is 200 and many recorded sales are capped; an ordinary regression of those sales is not an estimate of unrestricted customer demand.

Use **Problematic Data** to inspect missing values, duplicate rows, nonpositive prices, negative/fractional sales, and sales above capacity. It is deliberately unsuitable as an unreviewed pricing dataset.

For a personal CSV, provide `event_id,ticket_price,tickets_sold`. Optional descriptive columns do not make other required columns optional. Use plain numeric prices without currency symbols or thousands separators unless the parser explicitly supports them. Sales count whole tickets. If automatic header normalization does not match required fields, supply an explicit mapping instead of accepting an ambiguous guess.

Review the validation summary and individual issues. Invalid records must be corrected or excluded before analysis. Missing numeric values must never become zeros silently. Download rejected rows to preserve the explanation of what failed. Download cleaned data after edits are accepted.

## 2. Prepare comparable observations

Search/filter the data to inspect it. Editing a cell, deleting a row, adding a record, or changing the selected group changes the input to the analysis. Revalidate the edited selection before fitting. Reset restores the original dataset according to the UI's reset action; export a cleaned copy if you want to preserve your changes.

Select one event history, one meaningful category, or a deliberately chosen comparable group when available. Pooling all events assumes that their price/sales relationship is comparable. A music festival and a small workshop may require separate models. Selecting one event with only one historical price does not supply enough information to estimate a price response.

## 3. Fit and compare demand

Open **Demand Modeling** and fit the eligible models. Inspect equations, sample sizes, error measures, and warnings. A line needs at least two distinct prices mathematically; a quadratic needs at least three. The validation policy imposes additional practical row-count thresholds and stronger conditions for automatic quadratic recommendations.

Read the recommendation reason. A quadratic is not preferred merely because its training R² is higher. If a holdout is available, its metrics come from predictions on records not used by the evaluation-stage fit. The final displayed coefficients are refitted on all selected records and are the coefficients used for optimization and scenarios.

For at least fifteen observations, unique event IDs use an 80/20 random row split with seed 42. Repeated IDs instead use entire event groups, requiring at least five independent groups and targeting an 80/20 ratio of groups. If either partition lacks enough independent prices or rank, the application disables the holdout with a warning. Keep IDs accurate: every record from the same underlying event should share its identifier. Exported `split_strategy` and zero-based `train_indices`/`val_indices` identify the partition. This is not chronological future-event validation.

You may choose another eligible model to explore its implications. Treat an unstable, implausible, weakly supported, or extrapolating model cautiously. Model selection changes invalidate prior optimization results.

## 4. Optimize revenue

Open **Revenue Optimization**. Start with a price interval near the historical prices. Set an initial guess within that interval, an iteration budget, and appropriate numerical tolerances. Optional capacity caps realizable expected sales; an optional price increment restricts permitted ticket prices.

Run the optimizer. Read these separate outputs:

- **Newton status:** whether the iterative equation solver converged, failed, or produced an unsuitable stationary point.
- **Stationary classification:** the second derivative test for the Newton root, when valid.
- **Candidate comparison:** actual revenues at stationary points, endpoints, demand-zero boundaries, and capacity transitions.
- **Final classification:** why the winning feasible price was chosen.
- **Scan check:** an independent bounded numerical comparison.

A valid upper-boundary recommendation can coexist with Newton failure. That does not mean Newton converged. A converged local minimum is also not a revenue maximum. A capacity-constrained maximum may occur where modeled demand meets capacity, at a nondifferentiable kink of realized revenue.

Distinguish raw predicted demand from realizable sales. Demand can exceed capacity. Negative raw polynomial demand is an invalid region; clipping a chart at zero does not make the prediction economically valid. Prices outside observed support are extrapolations.

## 5. Explore scenarios

Open **Scenario Simulator** and submit a proposed price and baseline. Predicted demand, realizable sales, revenue, and the baseline comparison should come from the backend. Adjust the price and observe the returned values. Comparing a current, proposed, and recommended price can show the model's tradeoff between price and sales.

When baseline revenue is zero, percentage change is undefined; an unavailable value is the correct result. The hypothetical demand multiplier accepts a finite factor greater than zero and at most ten. It scales modeled demand before capacity is applied, using the same factor for baseline comparisons. This is an assumption rather than a fitted causal effect and does not change the base optimization. Do not interpret slider changes as evidence of actual future ticket sales.

## 6. Explain diagnostics and calculations

Use **Model Diagnostics** to inspect residuals and error metrics. Backend-calculated plot data include actual versus predicted sales with a diagonal reference, a residual histogram, and fitted-curve overlays. A residual is actual sales minus predicted sales. RMSE measures typical squared-error scale in tickets. R² measures explained variation on the evaluated sample; it is undefined for zero-variance sales and can be negative out of sample. The optimization workspace also exposes convergence data; the final audit records its browser verification status.

Use **Mathematical Walkthrough** to explain the normal equations, stable solution approach, coefficients, revenue derivatives, Newton substitution, and maximum verification. The complete derivations are also in `mathematical_foundation.md`.

## 7. Export and check

Open **Reports and Exports**. Available backend outputs include prediction, residual, and scenario CSVs, analysis JSON, SVG/PNG charts, and an academic PDF. Keep the active dataset, selected model, bounds, capacity, and any grid configuration consistent. The report's scenario section records active scenario prices and the hypothetical multiplier separately from the unchanged base optimization. Recompute after edits before treating a report as the final result. Check the final audit for the actual browser/download paths exercised.

Open downloaded files. Confirm the observation count, coefficients, model, constraints, and result match the current analysis. CSV text fields beginning with spreadsheet formula characters need safe export handling. JSON contains reproducible numerical information but may not serve as a UI import unless an import action is explicitly provided.

## Common messages

| Message or condition | Meaning and useful action |
|---|---|
| Too few distinct prices | More rows at the same price cannot identify the curve; provide independent price levels. |
| Quadratic not eligible | Use a line or add sufficient valid observations and price variation. |
| Sold-out/censored data | Recorded sales may understate demand; explain this limitation or use more suitable data. |
| Newton failed | Inspect the denominator, residual, bounds, and start. Candidate recovery is separate from iteration convergence. |
| Negative predicted demand | The polynomial is invalid there; narrow the range or select a better-supported model. |
| Extrapolation | The recommendation lies outside historical support; treat it as exploratory. |
| Undefined R² | Actual sales have no variation; do not interpret an unavailable value as zero or perfect fit. |
| No feasible price | Correct the bounds, demand region, capacity, or increment; do not invent a recommendation. |

This guide describes the workflow and interpretation. The final implementation audit records which actions were actually exercised in the browser and any remaining incomplete requirements.
