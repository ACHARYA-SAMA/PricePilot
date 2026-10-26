# Five-minute project demonstration script

Perform the actual workflow on a running local application. If a step fails, state the failure and use the recorded evidence only with its original context; do not pretend a prerecorded result is a live calculation. Feature-level verification status is in the final implementation audit.

## 0:00–0:35 - Introduce the problem

“PricePilot is an event ticket-pricing project built around numerical methods. A higher price earns more per ticket, but it may reduce sales. We model that tradeoff with least-squares demand fitting and use Newton-Raphson to find stationary revenue points. Then we compare feasible candidates so a stationary point is not automatically mistaken for the best price.”

## 0:35–1:15 - Inspect the input

Open Dataset Studio and load Standard College Events.

“These are 80 synthetic demonstration records, not actual college sales. Each record has an event identifier, ticket price, and tickets sold. This sample uses one common demand mechanism across illustrative event labels. We inspect validation, independent price variation, and capacity warnings before fitting. In real data, we would select comparable events rather than assume unrelated events share demand.”

Point to actual counts. Do not recite numbers that differ from the loaded sample.

## 1:15–2:05 - Explain least squares

Open Demand Modeling and fit the models.

“The linear model is `D(p)=a+bp`; the quadratic adds `cp²`. Least squares minimizes squared residuals, where a residual is actual sales minus predicted sales. Differentiating that objective gives the normal equations. The backend uses a centered and scaled design matrix with a stable least-squares solver. It displays coefficients in the original currency units.”

“We compare errors and warnings. A quadratic can improve training fit simply by being more flexible, so a held-out comparison is useful when there is sufficient data. The final coefficients are refitted on all selected records; held-out metrics remain separate.”

## 2:05–3:10 - Explain optimization

Open Revenue Optimization, use bounds near the observed prices, and run it.

“Revenue is `pD(p)`. For quadratic demand, its derivative is `a+2bp+3cp²`. Newton-Raphson solves this derivative equation using `p_next=p-R'/R''`. These are the actual iterations and residuals returned by Python.”

Point to the status and second derivative.

“A negative second derivative identifies a local maximum at a valid stationary point. But the global feasible winner can also be an endpoint or a capacity transition. The candidate table compares those alternatives. With capacity, realizable sales are capped, making revenue piecewise. Newton convergence and the final winning source are reported separately.”

## 3:10–3:45 - Explore a scenario

Open Scenario Simulator and change the proposed ticket price.

“The backend evaluates demand and realized revenue at this price and compares it with a baseline. The graph makes the modeled price-versus-sales tradeoff visible. This is an exploration of the fitted relationship, not a claim that future customers will behave exactly this way.”

Inspect the actual response before describing the direction of change.

## 3:45–4:15 - Explain errors and export

Open Model Diagnostics, then Reports and Exports.

“Residual plots help detect systematic errors. RMSE is measured in tickets; R² describes variation explained on the evaluated sample, not causality. We can export numerical results and generate an academic report that preserves the active model and configuration. We must open the export to verify that it matches the analysis.”

## 4:15–5:00 - Reference check and limitations

“For the exact reference `D=500-2p`, the derivative is `500-4p`, so the theoretical price is 125, predicted sales250, and revenue31,250, provided the bounds and capacity allow it. An executed Python check reproduces these results within floating-point precision. Noiseless quadratic data also checks coefficient recovery.”

“The project demonstrates Unit V regression and Unit II Newton-Raphson with visible calculations. Its limits include confounding, capacity censoring, extrapolation, and the absence of independent real-world validation. Correct optimization of a fitted model does not establish a guaranteed market outcome. The audit records the tests actually executed and any remaining gaps.”

## Optional recovery demonstration

If time permits, load Problematic Data and explain one actual row error. Alternatively, upload three rows at an identical price to show why a line cannot identify a slope. Correct/replace the input and rerun to demonstrate recovery. Do not use an intentionally invalid dataset to present a confident recommendation.
