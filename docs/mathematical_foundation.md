# Mathematical foundation

## 1. The modeled relationship

Let observation `i` contain ticket price `p_i` and recorded sales `y_i`. The fitted demand `D(p)` estimates sales conditional on price under a comparable-event assumption. Units are currency per ticket for price, tickets for demand, and currency for revenue. Sales at capacity are censored: observed sales equal the smaller of latent demand and capacity. Ordinary least squares does not undo this censoring.

Price is only one possible explanatory variable. Marketing, audience, performers, timing, and venue differences can confound the association. A fitted curve is not a causal experiment or a guaranteed forecast.

## 2. Linear least squares

For `D(p)=a+bp`, minimize

\[
S(a,b)=\sum_{i=1}^n [y_i-a-bp_i]^2.
\]

Write residual `e_i=y_i-a-bp_i`. Setting the partial derivatives to zero gives

\[
\frac{\partial S}{\partial a}=-2\sum e_i=0,
\qquad
\frac{\partial S}{\partial b}=-2\sum p_i e_i=0.
\]

Thus

\[
na+b\sum p_i=\sum y_i,
\qquad
a\sum p_i+b\sum p_i^2=\sum p_i y_i.
\]

With distinct prices, an equivalent analytical form is

\[
b=\frac{\sum(p_i-\bar p)(y_i-\bar y)}{\sum(p_i-\bar p)^2},
\qquad a=\bar y-b\bar p.
\]

At least two distinct prices are required for a uniquely identifiable line. Additional rows are needed for useful uncertainty assessment. The application's data-validation policy may impose a more conservative practical minimum than this mathematical minimum.

## 3. Quadratic least squares

For `D(p)=a+bp+cp²`, minimize

\[
S(a,b,c)=\sum_{i=1}^n[y_i-a-bp_i-cp_i^2]^2.
\]

The derivative equations are `sum e_i=0`, `sum p_i e_i=0`, and `sum p_i² e_i=0`, leading to

\[
\begin{bmatrix}
n & \sum p_i & \sum p_i^2\\
\sum p_i & \sum p_i^2 & \sum p_i^3\\
\sum p_i^2 & \sum p_i^3 & \sum p_i^4
\end{bmatrix}
\begin{bmatrix}a\\b\\c\end{bmatrix}
=
\begin{bmatrix}\sum y_i\\\sum p_i y_i\\\sum p_i^2 y_i\end{bmatrix}.
\]

Three distinct prices are the mathematical minimum for full column rank. A quadratic through only three observations can interpolate them exactly without providing credible predictive evidence. Repeated rows at one price increase observation count but do not add a new independent price level.

## 4. Matrix formulation and numerical stability

The design matrix has rows `[1,p_i]` for a line or `[1,p_i,p_i²]` for a quadratic. In both cases,

\[
X\beta\approx y,
\qquad \min_\beta\|X\beta-y\|_2^2,
\qquad X^TX\beta=X^Ty.
\]

The last relation is a derivation, not an instruction to invert `XᵀX`. Forming the normal-equation matrix squares the 2-norm condition number for a full-rank matrix, worsening numerical sensitivity. Price powers can also differ greatly in magnitude. PricePilot solves the centered/scaled least-squares system with NumPy's `lstsq`, checks rank and conditioning, and exposes original-basis sums for explanation.

Define `t=(p-μ)/s`, where `μ` is the price mean and `s` is a nonzero price scale. Fit

\[
D=\alpha+\beta_t t+\gamma t^2.
\]

Expansion gives original-price coefficients

\[
a=\alpha-\frac{\beta_t\mu}{s}+\frac{\gamma\mu^2}{s^2},
\qquad
b=\frac{\beta_t}{s}-\frac{2\gamma\mu}{s^2},
\qquad
c=\frac{\gamma}{s^2}.
\]

For a line, set `γ=0`. Predictions should be invariant under this change of basis to numerical precision. Calculations use unrounded coefficients; rounding is only for display. A rank-deficient design does not become identifiable just because a solver returns one least-squares vector.

## 5. Residual diagnostics

For `e_i=y_i-ŷ_i`,

\[
SSE=\sum e_i^2,
\quad MAE=\frac1n\sum|e_i|,
\quad RMSE=\sqrt{\frac{SSE}{n}},
\quad SST=\sum(y_i-\bar y)^2.
\]

MAE and RMSE are measured in tickets; SSE is measured in squared tickets. RMSE penalizes large errors more strongly than MAE.

\[
R^2=1-\frac{SSE}{SST},
\qquad
\bar R^2=1-(1-R^2)\frac{n-1}{n-k-1}.
\]

Here `k` counts predictors excluding the intercept: one for a line and two for a quadratic. When `SST=0`, R² is undefined. When `n-k-1<=0`, adjusted R² is undefined. Undefined values must be labeled unavailable and serialized as JSON `null`, never disguised as zero or perfect fit. Held-out R² can be negative: the model can perform worse than the held-out mean benchmark.

Inspect residuals versus price for systematic shape, actual versus predicted sales for calibration, and the error distribution for asymmetry or unusually large errors. These plots suggest limitations; they do not prove that the model assumptions hold.

## 6. Model comparison and final estimation

A more flexible quadratic cannot have a higher minimum training SSE than a nested linear model fitted to the same data. Consequently, higher training R² alone is insufficient evidence to select it.

A reproducible holdout comparison fits both models on the same training subset and evaluates both on untouched validation observations. With at least fifteen observations and unique event IDs, the implementation uses an 80/20 random row split with seed 42. With repeated event IDs, it instead assigns entire event groups to the two partitions, requiring at least five independent groups; the target ratio is 80/20 of groups, so row counts need not be exactly 80/20. If either partition lacks sufficient independent price variation or rank, holdout evaluation is disabled with an explicit warning. Selection weighs prediction error, simplicity, stability, and demand shape. When predictions are similar, prefer the simpler line.

After evaluation, full-data refits provide the displayed final coefficients and the model used for optimization and scenarios. Holdout metrics remain evaluation-stage metrics from models that did not train on the held-out rows. They are not the out-of-sample performance of the full-data refit. The response exposes `split_strategy` (`random_rows`, `random_groups`, or `none`) and zero-based `train_indices`/`val_indices` into the submitted observation list. Whole-group isolation depends on accurate event IDs: records from one event assigned different IDs are not recognized as related. The implementation does not provide chronological validation for future-time forecasting.

## 7. Revenue construction

Modeled ticket revenue is `R(p)=pD(p)`. It excludes fixed costs, variable costs, refunds, sponsorship, taxes, and non-ticket income; revenue maximization is not profit maximization.

For linear demand,

\[
R(p)=ap+bp^2,
\quad R'(p)=a+2bp,
\quad R''(p)=2b.
\]

For quadratic demand,

\[
R(p)=ap+bp^2+cp^3,
\quad R'(p)=a+2bp+3cp^2,
\quad R''(p)=2b+6cp.
\]

An interior differentiable optimum with positive feasible demand must satisfy `R'(p)=0`. This condition is necessary, not sufficient for a global maximum.

## 8. Newton-Raphson derivation

For a scalar root equation `f(p)=0`, approximate around `p_n`:

\[
f(p_n+h)\approx f(p_n)+hf'(p_n).
\]

Set the approximation to zero to obtain

\[
p_{n+1}=p_n-\frac{f(p_n)}{f'(p_n)}.
\]

Use `f=R'` and `f'=R''`. For quadratic demand,

\[
p_{n+1}=p_n-
\frac{a+2bp_n+3cp_n^2}{2b+6cp_n}.
\]

Each recorded iteration should expose the actual current price, derivative residual, second derivative, signed correction, next price, and absolute step change. A small step alone may indicate stagnation rather than a root; check the residual too. Failure conditions include a zero or very small denominator, a nonfinite iterate, divergence, leaving a permitted region, and exhausting the iteration budget. The status must describe what happened. Analytical recovery of a candidate is separate from Newton convergence.

For a converged stationary price `p_s`, negative `R''(p_s)` indicates a local maximum; positive indicates a local minimum; zero is inconclusive. Newton can converge to a minimum. That point must not be labeled a revenue recommendation solely because its residual is small.

## 9. Feasibility, capacity, and a global candidate comparison

Choose a positive bounded interval `[L,U]`. Restrict polynomial recommendations to regions with `D(p)>=0`. Negative polynomial demand is an invalid model region, even if a plotted realized-sales curve is clipped to zero.

With capacity `C>0`,

\[
S(p)=\min(\max(D(p),0),C),
\qquad R_C(p)=pS(p).
\]

On a capacity-saturated positive-price region, `R_C(p)=Cp` increases with price. The optimum can occur at the kink `D(p)=C`, even when the unconstrained stationary price is elsewhere. The candidate set therefore includes:

1. Real stationary roots of `R'(p)=0`, including an explicitly identified Newton result.
2. The interval endpoints.
3. Roots of `D(p)=0` that bound valid-demand regions.
4. Roots of `D(p)=C` that separate capped and uncapped sales.

Filter by finite prices, interval membership, and feasible demand. Evaluate realized revenue at all feasible candidates and select its largest value. Classify the winning source accurately: interior, lower/upper boundary, capacity transition, or discrete price. A bounded fine-grid scan supplies an independent numerical cross-check; its finite spacing makes it approximate, not a proof of an exact optimizer.

If price increments `h` are required, eligible prices are positive multiples `jh` in `[L,U]` under the implementation's grid convention. Optimize over that discrete set, not over a rounded continuous winner. A rounded price can be outside the range or can change the best choice near a capacity boundary. Report an empty grid rather than inventing a price.

For an explicitly hypothetical scenario factor `m` with `0<m<=10`, scenario demand is `D_m(p)=mD(p)` and realizable sales are `min(max(mD(p),0),C)` when capacity exists. Scaling precedes the cap. Proposed and baseline scenarios share the same factor; baseline percentage change remains undefined when its revenue is zero. The factor is a user assumption, not a fitted causal estimate, and does not modify the application's base optimization result.

## 10. Independently checkable reference

For exact `D(p)=500-2p`,

\[
R(p)=500p-2p^2,
\quad R'(p)=500-4p,
\quad R''(p)=-4.
\]

Thus `p=125` is a strict local maximum, with `D=250` and `R=31,250`. On `[25,200]` the endpoint revenues are `11,250` and `20,000`, so the stationary point wins. With capacity `C=200`, the capacity transition is `500-2p=200`, giving `p=150` and realized revenue `30,000`; that constrained optimum differs from the unconstrained one.

The exact quadratic reference `D(p)=600-2p-0.001p²` is useful for coefficient recovery. Noiseless values generated from it should recover `(600,-2,-0.001)` within numerical tolerance. This is an algorithm check, not validation against event sales.
