# Presentation outline: 12 slides

This outline is text for an editable presentation to be created later. It does not claim that a PowerPoint file or application screenshots have been generated. Use only screenshots linked in the final implementation audit.

| Slide | Content | Suggested visual / speaker point |
|---|---|---|
| 1. PricePilot | Event Revenue Optimizer; actual author/institution details | Tagline: find a price, inspect the mathematics. |
| 2. Motivation | Ticket revenue balances price and expected sales | A simple price-demand sketch, clearly marked conceptual. |
| 3. Problem statement | Estimate demand and maximize revenue inside feasible constraints | Show CSV inputs and the local calculation pipeline. |
| 4. Objectives | Validation, fitting, comparison, optimization, explanation | Emphasize mathematical correctness before appearance. |
| 5. Syllabus connection | Unit V least squares and Unit II Newton-Raphson | Connect fitted demand to revenue-derivative root finding. |
| 6. Least squares | Linear/quadratic design matrices and normal equations | Explain why a stable solver replaces direct inversion. |
| 7. Newton-Raphson | Tangent approximation and explicit update | Show an actual iteration trace from a verified run. |
| 8. Architecture | React/TypeScript client, FastAPI/Python numerical engine | All authoritative calculations occur in Python; no AI API. |
| 9. Application workflow | Dataset review to model comparison to optimization | Use actual screenshots only if captured and inspected. |
| 10. Verified results | Exact linear reference; labeled synthetic demonstration | Reference: price125, demand250, revenue31,250; show source/config. |
| 11. Limitations | Confounding, censoring, extrapolation, holdout limits | Distinguish correct arithmetic from real-market validation. |
| 12. Conclusion and scope | Transparent methods and defensible evidence | Future work is proposed, not already implemented. |

## Results to present carefully

The exact reference is a noiseless constructed example, checked by both engine execution and algebra. The standard generated sample is also synthetic, with seed 42 and 80 records; its fitted outputs are recorded in `project_report.md`. A screenshot is evidence of what was displayed at one moment, not proof that all workflows passed.

For a short viva, explain the derivative and why boundary/capacity comparisons are necessary. For a technical review, show the test command output and final audit. Do not claim business revenue improvement, statistical causality, unmeasured performance, or unsupported test coverage.
