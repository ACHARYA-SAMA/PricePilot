"""Cross-check 250 seeded models against an independent exhaustive grid.

Run from the repository root with backend/.venv/Scripts/python.exe
scripts/verify_numerical_oracle.py. The grid is verification, not the optimizer.
"""
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.optimization import run_optimization
from app.core.regression import RegressionCoefficients


def main() -> None:
    rng = np.random.default_rng(712)
    worst = 0.0
    for i in range(250):
        a = float(rng.uniform(-100, 1000))
        b = float(rng.uniform(-20, 20))
        c = float(rng.uniform(-0.2, 0.2))
        capacity = None if i % 2 else float(rng.uniform(20, 700))
        opt = run_optimization(
            RegressionCoefficients(a, b, c, "quadratic"),
            p_min=1, p_max=150, capacity=capacity,
            price_increment=5 if i % 3 == 0 else None,
        )
        p = np.arange(5, 151, 5, dtype=float) if i % 3 == 0 else np.linspace(1, 150, 20_001)
        # Deliberately evaluate the polynomial directly, outside engine helpers.
        d = a + b*p + c*p*p
        realized = np.maximum(0, d)
        if capacity is not None:
            realized = np.minimum(realized, capacity)
        feasible = d >= 0
        if not np.any(feasible):
            assert opt.optimal_price is None, (i, opt.optimal_price)
            continue
        oracle = float(np.max((p*realized)[feasible]))
        assert opt.optimal_realized_revenue is not None, (i, a, b, c)
        excess = max(0, oracle-opt.optimal_realized_revenue)
        worst = max(worst, excess)
        assert excess <= max(1e-6, abs(oracle)*1e-7), (i, oracle, opt.optimal_realized_revenue)
    print("250 seeded quadratic/capacity/discrete cases checked against exhaustive "
          "20,001-point or exact discrete grids; largest oracle excess = "
          f"{worst:.3g}.")


if __name__ == "__main__":
    main()
