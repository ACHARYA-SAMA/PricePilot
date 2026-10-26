# Viva preparation: questions and precise answers

## Regression and diagnostics

1. **What does PricePilot predict?** A modeled relationship between ticket price and expected recorded sales for a selected comparable group. It does not guarantee future sales.
2. **What is regression?** Estimating a function linking an outcome to predictors from observations. Here the outcome is ticket demand/sales and the predictor is price.
3. **Why least squares?** It chooses coefficients minimizing the sum of squared residuals. The objective has a transparent mathematical derivation and a stable linear-algebra solution for these models.
4. **Why square errors?** Squaring prevents positive/negative errors canceling and penalizes large errors strongly. It also makes this objective differentiable. It can increase sensitivity to outliers.
5. **What is the linear demand model?** `D(p)=a+bp`; `a` is the intercept and `b` is the change in modeled ticket demand per unit of price.
6. **What is the quadratic model?** `D(p)=a+bp+cp²`. Its slope `b+2cp` changes with price; the parameters are still linear in the coefficients.
7. **Why compare both?** A quadratic captures curvature but uses another parameter and may overfit. Comparison assesses whether the added flexibility improves prediction credibly.
8. **What are the normal equations?** `XᵀXβ=Xᵀy`, obtained by setting the gradient of `||Xβ-y||²` to zero. For a quadratic, the matrix uses price-power sums through degree four.
9. **Why not directly invert `XᵀX`?** Forming it worsens conditioning, and an explicit inverse is unnecessary. The implementation uses `numpy.linalg.lstsq` on a centered/scaled design.
10. **Why center and scale prices?** It reduces disparity among design columns and improves numerical conditioning. Coefficients are transformed back so displayed equations use actual prices.
11. **Does scaling change predictions?** A correct change of basis preserves the polynomial function to numerical precision. It changes coefficient representation, not the modeled relationship.
12. **How many distinct prices are needed?** At least two for a uniquely identifiable line and three for a quadratic. Practical validation/recommendation thresholds are more conservative.
13. **Why do repeated prices not solve rank deficiency?** Repeating a design row adds observations but does not add an independent column direction. One price cannot identify a price slope.
14. **What is a residual?** Actual sales minus predicted sales at the same observation: `e_i=y_i-ŷ_i`.
15. **What are SSE, MAE and RMSE?** `SSE=sum e²`, `MAE=mean |e|`, `RMSE=sqrt(mean e²)`. MAE/RMSE are in tickets; SSE is in squared tickets.
16. **What does R² mean?** `1-SSE/SST`, a relative error measure against the evaluated sample's mean-demand benchmark. It does not prove causality or forecast reliability.
17. **Can R² be negative?** Yes, especially on held-out observations when predictions are worse than the mean benchmark.
18. **What if sales have zero variance?** `SST=0`, making the usual R² ratio undefined. Display unavailable, not a fabricated zero or one.
19. **What is adjusted R²?** `1-(1-R²)(n-1)/(n-k-1)`, where `k` excludes the intercept. It is undefined when the denominator is nonpositive.
20. **Why not select the quadratic by training R² alone?** A nested model with more parameters can fit training data at least as well without improving predictions on new data.
21. **What is overfitting?** Capturing sample-specific noise rather than a relationship that generalizes. Flexible models and small samples increase the risk.
22. **Why a holdout?** It evaluates predictions on records the evaluation-stage model did not train on. It provides a limited generalization check.
23. **What split does the implementation use?** With at least fifteen observations and unique event IDs, a seeded 80/20 random row split. Repeated IDs use whole-event groups with seed 42 and at least five independent groups; the target ratio is 80/20 of groups. Inadequate independent price variation/rank disables holdout evaluation with a warning. Chronological splitting is not implemented.
24. **Why do holdout and final coefficients differ?** Evaluation-stage coefficients use only training rows. Final active models are refitted on all selected records after evaluation.
25. **How does the implementation address event leakage?** It keeps all records with the same event ID in one holdout partition when repeated IDs exist. Accurate IDs are essential: related records mislabeled as different events may still leak information. Exported `split_strategy` and zero-based `train_indices`/`val_indices` make the partition inspectable.

## Revenue and numerical optimization

26. **What is the revenue function?** `R(p)=pD(p)`. It models ticket income, excluding costs and other revenue streams.
27. **Is maximizing revenue maximizing profit?** No. Profit subtracts costs, which are not modeled here.
28. **Why differentiate revenue?** An interior differentiable optimum must have zero first derivative. This identifies stationary candidates, which must still be classified and compared.
29. **Derive revenue derivatives for quadratic demand.** `R=ap+bp²+cp³`, `R'=a+2bp+3cp²`, and `R''=2b+6cp`.
30. **What is Newton-Raphson?** An iterative root solver using a tangent approximation: `p_next=p-f(p)/f'(p)`. Here `f=R'`.
31. **How is the Newton update derived?** From `f(p+h)≈f(p)+hf'(p)=0`, solve `h≈-f/f'` and add the correction to `p`.
32. **Why is an initial guess required?** Newton constructs a local approximation at the current point. Different starts can converge to different roots or fail.
33. **What if the denominator vanishes?** Division is undefined or unstable. The algorithm records failure rather than inventing the next iterate.
34. **Does Newton always converge?** No. It can diverge, leave the permitted interval, stagnate, encounter a small denominator, or exhaust the iteration limit.
35. **Does a small step prove convergence?** No. It can indicate stagnation. The derivative residual at the returned price must also satisfy the configured criterion.
36. **What is checked at a stationary point?** Finite price, interval membership, nonnegative demand, derivative residual, and second derivative. Classification and feasibility are separate checks.
37. **How is a local maximum verified?** At a valid stationary point, a negative second derivative establishes a strict local maximum. Positive gives a minimum; zero is inconclusive.
38. **Can Newton find a minimum?** Yes. Solving `R'=0` does not distinguish maxima from minima; the second derivative and candidate comparison do that.
39. **Why evaluate endpoints?** A constrained interval maximum can occur at a boundary even with no interior stationary maximum.
40. **Why compare analytical stationary roots?** For these low-degree polynomials, roots of the revenue derivative can be recovered independently, checking that Newton did not miss a relevant candidate.
41. **Does analytical recovery mean Newton converged?** No. The Newton status must remain its actual status. A separately recovered winner has a different provenance.
42. **Why is negative demand invalid?** Ticket sales cannot be negative. A polynomial predicting negative values is outside a physically meaningful region and must be flagged.
43. **How is capacity handled?** Expected realizable sales are `min(max(D,0),C)`, and realized modeled revenue is price times that quantity.
44. **Why can capacity change the optimum?** On a saturated segment revenue is `Cp`, increasing with price. A maximum may occur where demand drops to capacity, a kink missed by unconstrained derivative roots alone.
45. **What are capacity-censored observations?** Sold-out sales record available capacity, while actual willing customer demand may be higher. Ordinary regression cannot infer that unseen excess from the sales count alone.
46. **What is a discrete-price optimum?** The highest feasible modeled revenue among allowed grid prices. Rounding a continuous optimum alone can select an invalid or suboptimal point.
47. **Why a bounded numerical scan?** It provides an independent approximate cross-check of the candidate maximum. Finite grid resolution is a limitation, so agreement is not an exact proof.
48. **What if the chosen range is beyond observed prices?** That is extrapolation. Warn that polynomial behavior there may be unsupported or implausible.

## Implementation, evidence, and academic defense

49. **Which component computes the results?** The Python backend. The frontend requests results and visualizes them, avoiding inconsistent duplicate numerical engines.
50. **What happens when data or configuration changes?** Dependent results must be invalidated and recomputed so stale optimization and diagnostics are not mixed.
51. **Why are invalid values not replaced by zero?** That would fabricate observations, bias regression, and hide data-quality problems. Reject or explicitly correct the record.
52. **What independent exact reference was checked?** `D=500-2p` gives `R'=500-4p`, so `p=125`, `D=250`, and `R=31,250` when bounds/capacity permit. An executed engine check agreed to floating-point precision.
53. **How was quadratic fitting checked?** Noiseless data from `D=600-2p-0.001p²` recovered those coefficients to floating-point precision. This is an algorithm check, not field validation.
54. **Why are noisy standard coefficients different from generating coefficients?** Random noise and ticket-count rounding perturb the observations. Least squares estimates the finite sample, not an exact latent formula.
55. **Are the sample categories evidence that unlike events can be pooled?** No. Their labels share one synthetic mechanism by construction; real categories require a comparability assessment.
56. **What must a report preserve?** Active observations, selected model, numerical configuration, results, warnings, and provenance. Its scenario section records active scenario prices and the hypothetical demand multiplier separately from base optimization. It must not silently use another model or stale constraints.
57. **What does a successful build prove?** That configured compilation/bundling succeeded. It does not prove runtime interactions, responsive layout, mathematical correctness, or export contents.
58. **Where are actual test claims recorded?** In the implementation audit with commands, exit codes, observed outputs, and available artifacts. No tests or coverage percentages are invented.
59. **What are the main limitations?** Price-only association, confounding, censoring, extrapolation, small samples, dependence on accurate event IDs for grouped validation, no chronological forecasting test, no uncertainty intervals, and no independent real-world validation.
60. **What would improve the project?** Chronological validation, repeated evaluation, uncertainty intervals, censored-demand models, and cost/profit analysis, each implemented and tested before being advertised.

61. **How does the hypothetical demand multiplier work?** A finite user factor in `(0,10]` scales fitted demand before the capacity cap. Proposed and baseline scenarios use the same factor. It does not estimate causality or change base optimization.
62. **Which diagnostic data come from the backend?** Residuals, actual-versus-predicted points with a reference diagonal, histogram bins/counts, and fitted curve overlays. The client plots returned values instead of implementing a second numerical engine.
