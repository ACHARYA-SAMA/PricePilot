# Dataset dictionary and provenance

All `sample_*.csv` files are **Synthetic Demonstration Data - Not Real Historical Sales**. Regenerate them with `python scripts/generate_sample_data.py`. The generator imports `backend/app/core/data_generation.py`; that source defines the reproducible sampling process.

## Fields

| Column | Required | Meaning and validation |
|---|---|---|
| `event_id` | Yes | Nonempty event identifier. Records from one underlying event must share an accurate ID. Repeated IDs trigger whole-event holdout isolation when data is sufficient. |
| `ticket_price` | Yes | Finite positive price per ticket, in a consistent currency. |
| `tickets_sold` | Yes | Finite nonnegative integer recorded sales. Missing or invalid cells must not silently become zero. |
| `event_name` | No | Descriptive event label. |
| `event_category` | No | User-supplied grouping label; does not itself prove comparability. |
| `event_date` | No | Optional event date, preferably ISO `YYYY-MM-DD`. Invalid supplied dates require a visible issue. |
| `venue_capacity` | No | Positive whole-ticket capacity when known. Recorded sales must not exceed it. |
| `sales_period` | No | Number of sales days in the generated samples. Not a fitted predictor. |
| `location` | No | Descriptive location. Not a fitted predictor. |
| `promotion_type` | No | Descriptive promotion label. Not a fitted predictor. |
| `_synthetic` | Internal | `True` for generated records; provenance metadata. |
| `_note` | Internal | Explicit synthetic-demonstration warning. |

Observed revenue is derived by the Python processing pipeline as `ticket_price * tickets_sold`. It need not be supplied in an uploaded CSV. Any unknown descriptive field should be preserved or explicitly handled rather than interpreted as another mathematical predictor.

## Standard College Events

- File: `sample_events.csv`; registry ID: `standard`.
- 80 rows; fixed seed 42.
- Prices are sampled uniformly from 50–170 and rounded to the nearest 10.
- Latent demand equation: `D(p)=800-3.5p-0.005p²+ε`, with `ε~Normal(0,15)` tickets.
- Generated demand is rounded to whole tickets, lower-bounded by zero, and capped by the generated venue capacity. For the fixed default sample, neither clipping limit binds.
- Capacities are 800, 900, or 1000. Actual generated default sample: 13 distinct prices, no zero-sales rows, no sold-out rows.
- Five illustrative category labels share the same synthetic demand-generating mechanism. This is a generation assumption, not evidence that actual Music, Comedy, Tech Talk, Cultural, and Sports events can be pooled.
- All remaining categorical labels are simulation metadata, not observed sources or calibrated causal influences.

The noiseless latent function has an interior revenue maximum in the sampled interval. A fitted curve based on noisy rounded observations need not recover the exact latent coefficients.

## Sold-Out Events

- File: `sample_sellout_events.csv`; registry ID: `sellout`.
- 40 rows; fixed seed 43.
- Prices sampled from 100–400 and rounded to the nearest 10.
- Latent demand: `1200-4p+ε`, with `ε~Normal(0,20)` tickets.
- Recorded sales: rounded demand clipped to `[0,200]`; venue capacity is 200.
- Actual default sample: 24 rows at capacity and 11 zero-sales rows.
- This sample deliberately demonstrates censoring and clipped observations. Fitting ordinary least squares to its recorded sales does not recover latent unrestricted demand in general.

## Problematic Data

- File: `sample_invalid_data.csv`; registry ID: `problematic`.
- 13 manually specified synthetic records, including one exact duplicate.
- Deliberate faults include missing numeric values, negative/zero prices, negative and fractional ticket counts, and sales above capacity.
- Valid surviving records have limited independent price variation; inspect the validator's actual eligibility result.
- No random noise model or fitted generating equation is claimed for this file. Registry seed zero is a marker, not a random simulation used to create these rows.

## Reproducibility and interpretation

The fixed generator seed gives reproducibility within the recorded code and numerical-library environment. Do not assume a future changed generator or library version produces byte-identical CSVs. Record dependencies and retain the actual CSV used in a submitted project.

These files support demonstrations and algorithm tests. They are not student survey findings, real ticketing records, published research datasets, or evidence of business effectiveness.
