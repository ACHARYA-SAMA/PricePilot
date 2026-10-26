"""
PricePilot — Data Generation Module

Generates synthetic demonstration datasets for the PricePilot application.
All datasets are clearly labeled as synthetic and not real historical sales.

Random seed: 42 (fixed for reproducibility)
Generating equation for Dataset A: D(p) = 800 - 3.5p - 0.005p² + noise
  where noise ~ Normal(0, 15)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd


RANDOM_SEED = 42
RNG = np.random.default_rng(RANDOM_SEED)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clip_nonneg_int(v: float) -> int:
    return max(0, int(round(v)))


# ---------------------------------------------------------------------------
# Dataset A — Standard College Events
# ---------------------------------------------------------------------------

def generate_standard_events(n: int = 80) -> pd.DataFrame:
    """
    Generate ~80 observations of comparable student events.

    True underlying demand:
        D(p) = 800 - 3.5p - 0.005p²  (quadratic, decreasing over [50, 170])

    Interior revenue maximum for this model:
        R(p) = p·D(p) = 800p - 3.5p² - 0.005p³
        R'(p) = 800 - 7p - 0.015p² = 0
        Its positive stationary root lies within the sampled interval.

    Noise distribution: Normal(0, 15) tickets, clipped to ≥ 0.
    Price range: ₹50 to ₹170 with intentional spread.
    Capacity: 800–1000 tickets, above generated demand for this fixed seed.
    Category labels share one synthetic generating mechanism. Pooling actual
    event categories would require a separate comparability assessment.
    """
    rng = np.random.default_rng(RANDOM_SEED)

    # Prices spread across range to give adequate regression coverage
    prices = rng.uniform(50, 170, size=n)
    prices = np.round(prices, -1)  # round to nearest 10
    prices = np.clip(prices, 50, 170)

    noise = rng.normal(0, 15, size=n)

    def true_demand(p: np.ndarray) -> np.ndarray:
        return 800 - 3.5 * p - 0.005 * p ** 2

    raw_demand = true_demand(prices) + noise

    categories = rng.choice(
        ["Music", "Comedy", "Tech Talk", "Cultural", "Sports"],
        size=n,
        p=[0.3, 0.2, 0.2, 0.2, 0.1],
    )

    venues = rng.choice(["Main Auditorium", "Open Air", "College Hall", "Sports Ground"], size=n)
    capacity = np.where(venues == "Main Auditorium", 900, np.where(venues == "Open Air", 1000, 800))

    tickets_sold = np.array([
        min(_clip_nonneg_int(d), int(cap))
        for d, cap in zip(raw_demand, capacity)
    ])

    # Build event IDs
    event_ids = [f"EVT-A-{i+1:03d}" for i in range(n)]
    event_names = [f"{cat} Night #{i+1}" for i, cat in enumerate(categories)]

    # Sales period in days (random 7-30 days before event)
    sales_periods = rng.integers(7, 31, size=n)

    df = pd.DataFrame({
        "event_id": event_ids,
        "event_name": event_names,
        "event_category": categories,
        "ticket_price": prices.astype(int),
        "tickets_sold": tickets_sold,
        "venue_capacity": capacity,
        "sales_period": sales_periods,
        "location": rng.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Pune"], size=n),
        "promotion_type": rng.choice(["Flyer", "Social Media", "Email", "None"], size=n),
        "_synthetic": True,
        "_note": "Synthetic Demonstration Data — Not Real Historical Sales",
    })

    return df


# ---------------------------------------------------------------------------
# Dataset B — Sold-Out Events
# ---------------------------------------------------------------------------

def generate_sellout_events(n: int = 40) -> pd.DataFrame:
    """
    Generate events where ticket sales frequently hit venue capacity.

    True underlying demand is high, so many observations are capacity-censored.
    Capacity: 200 tickets (intentionally low).
    Warning: sold-out records may underestimate true unconstrained demand.
    """
    rng = np.random.default_rng(RANDOM_SEED + 1)

    prices = rng.uniform(100, 400, size=n)
    prices = np.round(prices, -1).astype(int)
    prices = np.clip(prices, 100, 400)

    # High baseline demand — many will hit capacity
    raw_demand = 1200 - 4.0 * prices + rng.normal(0, 20, size=n)

    capacity = 200  # fixed small venue
    tickets_sold = np.array([min(_clip_nonneg_int(d), capacity) for d in raw_demand])

    event_ids = [f"EVT-B-{i+1:03d}" for i in range(n)]

    df = pd.DataFrame({
        "event_id": event_ids,
        "event_name": [f"Premium Show #{i+1}" for i in range(n)],
        "event_category": "Music",
        "ticket_price": prices,
        "tickets_sold": tickets_sold,
        "venue_capacity": capacity,
        "sales_period": rng.integers(14, 60, size=n),
        "location": "Mumbai",
        "promotion_type": "Social Media",
        "_synthetic": True,
        "_note": "Synthetic Demonstration Data — Not Real Historical Sales",
    })

    return df


# ---------------------------------------------------------------------------
# Dataset C — Problematic Data
# ---------------------------------------------------------------------------

def generate_problematic_events() -> pd.DataFrame:
    """
    Dataset with deliberate issues for testing validation:
    - Missing values
    - Duplicate rows
    - Negative ticket prices
    - Zero ticket prices
    - Negative ticket counts
    - Insufficient price variation (most at ₹100)
    - Tickets exceeding capacity
    """
    rows = [
        # Valid rows
        {"event_id": "EVT-C-001", "ticket_price": 100, "tickets_sold": 200, "venue_capacity": 300, "event_category": "Music"},
        {"event_id": "EVT-C-002", "ticket_price": 100, "tickets_sold": 195, "venue_capacity": 300, "event_category": "Music"},
        {"event_id": "EVT-C-003", "ticket_price": 100, "tickets_sold": 210, "venue_capacity": 300, "event_category": "Music"},
        {"event_id": "EVT-C-004", "ticket_price": 100, "tickets_sold": 188, "venue_capacity": 300, "event_category": "Music"},
        {"event_id": "EVT-C-005", "ticket_price": 120, "tickets_sold": 175, "venue_capacity": 300, "event_category": "Music"},
        # Duplicate
        {"event_id": "EVT-C-001", "ticket_price": 100, "tickets_sold": 200, "venue_capacity": 300, "event_category": "Music"},
        # Negative price
        {"event_id": "EVT-C-006", "ticket_price": -50, "tickets_sold": 150, "venue_capacity": 300, "event_category": "Music"},
        # Zero price
        {"event_id": "EVT-C-007", "ticket_price": 0, "tickets_sold": 300, "venue_capacity": 300, "event_category": "Music"},
        # Negative tickets sold
        {"event_id": "EVT-C-008", "ticket_price": 150, "tickets_sold": -10, "venue_capacity": 300, "event_category": "Music"},
        # Missing ticket price
        {"event_id": "EVT-C-009", "ticket_price": None, "tickets_sold": 120, "venue_capacity": 300, "event_category": "Music"},
        # Missing tickets sold
        {"event_id": "EVT-C-010", "ticket_price": 200, "tickets_sold": None, "venue_capacity": 300, "event_category": "Music"},
        # Tickets exceeding capacity
        {"event_id": "EVT-C-011", "ticket_price": 80, "tickets_sold": 500, "venue_capacity": 300, "event_category": "Music"},
        # Non-integer tickets
        {"event_id": "EVT-C-012", "ticket_price": 90, "tickets_sold": 175.7, "venue_capacity": 300, "event_category": "Music"},
    ]
    df = pd.DataFrame(rows)
    df["_synthetic"] = True
    df["_note"] = "Synthetic Demonstration Data — Not Real Historical Sales"
    return df


# ---------------------------------------------------------------------------
# Exported dataset registry
# ---------------------------------------------------------------------------

@dataclass
class SampleDatasetInfo:
    id: str
    name: str
    description: str
    warning: str | None
    n_rows: int
    generating_equation: str
    random_seed: int
    noise_distribution: str
    capacity_note: str


SAMPLE_DATASETS: list[SampleDatasetInfo] = [
    SampleDatasetInfo(
        id="standard",
        name="Standard College Events",
        description=(
            "80 synthetic observations across five illustrative category labels, all sharing "
            "one demand-generating mechanism. Prices range from ₹50 to ₹170. A decreasing "
            "quadratic demand model with Gaussian noise gives an interior revenue maximum. "
            "This standard sample has no sold-out or zero-sales records."
        ),
        warning=None,
        n_rows=80,
        generating_equation="D(p) = 800 - 3.5p - 0.005p² + ε, ε ~ N(0,15)",
        random_seed=RANDOM_SEED,
        noise_distribution="Normal(0, 15) tickets",
        capacity_note="Venue capacities: 800–1000. Standard sample is uncensored; no events sold out.",
    ),
    SampleDatasetInfo(
        id="sellout",
        name="Sold-Out Events",
        description=(
            "40 synthetic events where ticket demand frequently exceeds venue capacity (200 seats). "
            "Demonstrates capacity-censored observations and the sellout warning."
        ),
        warning=(
            "Many observations in this dataset are capacity-constrained (sold out). "
            "Observed sales may underestimate true unconstrained demand. "
            "Regression estimates should be interpreted with caution."
        ),
        n_rows=40,
        generating_equation="D(p) = 1200 - 4.0p + ε, ε ~ N(0,20)",
        random_seed=RANDOM_SEED + 1,
        noise_distribution="Normal(0, 20) tickets",
        capacity_note="Fixed capacity: 200. Many events are sold out.",
    ),
    SampleDatasetInfo(
        id="problematic",
        name="Problematic Data (Validation Demo)",
        description=(
            "13 records with deliberate issues: missing values, duplicates, negative prices, "
            "zero prices, negative ticket counts, tickets exceeding capacity, and insufficient "
            "price variation. Use this to explore validation and error handling."
        ),
        warning=(
            "This dataset is intentionally broken. It is provided to demonstrate "
            "the validation system, not for revenue optimization."
        ),
        n_rows=13,
        generating_equation="N/A — deliberately invalid data",
        random_seed=0,
        noise_distribution="N/A",
        capacity_note="Mixed.",
    ),
]


def get_sample_dataframe(dataset_id: str) -> pd.DataFrame:
    if dataset_id == "standard":
        return generate_standard_events()
    elif dataset_id == "sellout":
        return generate_sellout_events()
    elif dataset_id == "problematic":
        return generate_problematic_events()
    else:
        raise ValueError(f"Unknown sample dataset id: {dataset_id!r}")
