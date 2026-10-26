"""
PricePilot — Validation Module

Validates uploaded CSV datasets and individual observations.
Each validation function returns structured issues with row-level detail.
"""

from __future__ import annotations

import io
import math
import csv
import os
from datetime import date
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants (configurable via settings in production)
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = int(os.getenv("PRICEPILOT_MAX_FILE_BYTES", 5 * 1024 * 1024))
MAX_ROWS = int(os.getenv("PRICEPILOT_MAX_ROWS", 10_000))
MIN_ROWS_FOR_LINEAR = 3       # absolute minimum for linear regression
MIN_ROWS_FOR_QUADRATIC = 6    # practical minimum for quadratic
MIN_DISTINCT_PRICES_LINEAR = 2
MIN_DISTINCT_PRICES_QUADRATIC = 3
RECOMMENDED_MIN_ROWS_QUADRATIC = 12
RECOMMENDED_MIN_DISTINCT_QUADRATIC = 6


class IssueSeverity(str, Enum):
    ERROR = "error"      # Row must be rejected
    WARNING = "warning"  # Row is usable but flagged
    INFO = "info"        # Informational


@dataclass
class RowIssue:
    row_index: int        # 1-based (matching CSV row number)
    column: str | None
    severity: IssueSeverity
    code: str
    message: str


@dataclass
class ValidationResult:
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    warning_count: int = 0
    duplicate_count: int = 0
    unique_prices: int = 0
    unique_event_ids: int = 0
    price_min: float | None = None
    price_max: float | None = None
    price_mean: float | None = None
    capacity_available: bool = False
    sellout_count: int = 0
    issues: list[RowIssue] = field(default_factory=list)
    valid_dataframe: pd.DataFrame | None = None
    rejected_dataframe: pd.DataFrame | None = None
    column_mapping: dict[str, str] = field(default_factory=dict)

    # Regression eligibility flags
    linear_eligible: bool = False
    quadratic_eligible: bool = False
    quadratic_recommended: bool = False
    eligibility_notes: list[str] = field(default_factory=list)
    has_sellout_warning: bool = False
    sellout_warning_message: str | None = None


# ---------------------------------------------------------------------------
# Column normalisation
# ---------------------------------------------------------------------------

# Maps common alternative column names → canonical names
COLUMN_ALIASES: dict[str, str] = {
    # ticket_price
    "price": "ticket_price",
    "ticket price": "ticket_price",
    "ticketprice": "ticket_price",
    "cost": "ticket_price",
    "fare": "ticket_price",
    "amount": "ticket_price",
    # tickets_sold
    "sales": "tickets_sold",
    "tickets sold": "tickets_sold",
    "ticketssold": "tickets_sold",
    "sold": "tickets_sold",
    "quantity": "tickets_sold",
    "qty": "tickets_sold",
    "attendees": "tickets_sold",
    "attendance": "tickets_sold",
    # event_id
    "event": "event_id",
    "id": "event_id",
    "eventid": "event_id",
    "event id": "event_id",
    # optional fields
    "name": "event_name",
    "event name": "event_name",
    "category": "event_category",
    "type": "event_category",
    "date": "event_date",
    "capacity": "venue_capacity",
    "venue capacity": "venue_capacity",
    "venuecapacity": "venue_capacity",
    "period": "sales_period",
    "city": "location",
    "promo": "promotion_type",
    "promotion": "promotion_type",
}

REQUIRED_COLUMNS = {"event_id", "ticket_price", "tickets_sold"}
OPTIONAL_COLUMNS = {
    "event_name", "event_category", "event_date",
    "venue_capacity", "sales_period", "location", "promotion_type",
}


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Attempt to map uploaded column names to canonical names.
    Returns (renamed_df, mapping_applied).
    Only applies unambiguous, safe mappings.
    """
    rename_map: dict[str, str] = {}
    targets: dict[str, list[str]] = {}
    explicit_columns = {c.lower().strip() for c in df.columns}
    for original in df.columns:
        normalized = original.lower().strip()
        canonical = COLUMN_ALIASES.get(normalized, normalized)
        # An exact canonical header is authoritative (including one chosen by
        # explicit mapping in the upload endpoint). Other alias-like columns
        # remain ordinary metadata; do not re-map an unused "cost" onto price.
        if canonical != normalized and canonical in explicit_columns:
            canonical = normalized
        targets.setdefault(canonical, []).append(original)
    ambiguous = {k: v for k, v in targets.items() if len(v) > 1}
    if ambiguous:
        raise ValueError(f"Ambiguous column mappings {ambiguous}. Choose one source per canonical column.")
    for canonical, sources in targets.items():
        if sources[0] != canonical:
            rename_map[sources[0]] = canonical
    df = df.rename(columns=rename_map)
    return df, rename_map


# ---------------------------------------------------------------------------
# CSV Parsing
# ---------------------------------------------------------------------------

def parse_csv(content: bytes, filename: str = "upload.csv") -> tuple[pd.DataFrame | None, str | None]:
    """
    Parse raw CSV bytes into a DataFrame.
    Returns (dataframe, error_message). On failure returns (None, message).
    """
    if not filename.lower().endswith(".csv"):
        return None, "File must have a .csv extension."

    if len(content) > MAX_FILE_SIZE_BYTES:
        mb = len(content) / (1024 * 1024)
        return None, f"File size ({mb:.1f} MB) exceeds the 5 MB limit."

    if len(content) == 0:
        return None, "Uploaded file is empty."

    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            return None, "File encoding is not supported. Please save the CSV as UTF-8."

    try:
        parsed_rows = list(csv.reader(io.StringIO(text), strict=True))
        nonempty_rows = [r for r in parsed_rows if r]
        if not nonempty_rows:
            return None, "CSV contains no data rows or columns."
        header = nonempty_rows[0]
        if len(set(header)) != len(header):
            return None, "CSV contains duplicate column names; rename them before uploading."
        if any(len(r) != len(header) for r in nonempty_rows[1:]):
            return None, "CSV row field counts must match the header; check delimiters and quoting."
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except Exception as exc:
        return None, f"CSV parsing failed: {exc}"

    if df.empty or len(df.columns) == 0:
        return None, "CSV contains no data rows or columns."

    if len(df) > MAX_ROWS:
        return None, (
            f"Dataset has {len(df):,} rows, which exceeds the {MAX_ROWS:,}-row limit. "
            "Please filter or split the data before uploading."
        )

    return df, None


# ---------------------------------------------------------------------------
# Row-level validation
# ---------------------------------------------------------------------------

def _try_float(value: str) -> float | None:
    """Parse a string to float, returning None on failure."""
    if value is None or str(value).strip() in ("", "nan", "NaN", "None", "null"):
        return None
    try:
        v = float(str(value).strip().replace(",", ""))
        if not math.isfinite(v):
            return None
        return v
    except ValueError:
        return None


def validate_rows(df: pd.DataFrame) -> ValidationResult:
    """
    Validate each row in the DataFrame.
    Returns a ValidationResult with row-level issues and valid/rejected DataFrames.
    """
    result = ValidationResult()
    result.total_rows = len(df)
    issues: list[RowIssue] = []

    valid_indices: list[int] = []
    rejected_indices: list[int] = []

    # --- Detect duplicates (all columns) before row-level processing
    dup_mask = df.duplicated(keep="first")
    dup_rows = set(df.index[dup_mask].tolist())
    result.duplicate_count = int(dup_mask.sum())

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-based + 1 for header
        row_issues: list[RowIssue] = []
        is_rejected = False

        # --- Check for duplicate
        if idx in dup_rows:
            row_issues.append(RowIssue(
                row_index=row_num, column=None,
                severity=IssueSeverity.WARNING, code="DUPLICATE_ROW",
                message="This row appears to be a duplicate of an earlier row.",
            ))
            is_rejected = True

        # --- ticket_price
        raw_price = str(row.get("ticket_price", "")).strip()
        if raw_price in ("", "nan", "None", "null"):
            row_issues.append(RowIssue(
                row_index=row_num, column="ticket_price",
                severity=IssueSeverity.ERROR, code="MISSING_PRICE",
                message="ticket_price is missing.",
            ))
            is_rejected = True
            price_val = None
        else:
            price_val = _try_float(raw_price)
            if price_val is None:
                row_issues.append(RowIssue(
                    row_index=row_num, column="ticket_price",
                    severity=IssueSeverity.ERROR, code="INVALID_PRICE",
                    message=f"ticket_price '{raw_price}' is not a valid number.",
                ))
                is_rejected = True
            elif price_val <= 0:
                row_issues.append(RowIssue(
                    row_index=row_num, column="ticket_price",
                    severity=IssueSeverity.ERROR, code="NONPOSITIVE_PRICE",
                    message=f"ticket_price must be greater than zero (got {price_val}).",
                ))
                is_rejected = True
            elif price_val > 1_000_000:
                row_issues.append(RowIssue(
                    row_index=row_num, column="ticket_price",
                    severity=IssueSeverity.WARNING, code="UNUSUALLY_LARGE_PRICE",
                    message=f"ticket_price {price_val:,.0f} is unusually large.",
                ))

        # --- tickets_sold
        raw_sold = str(row.get("tickets_sold", "")).strip()
        if raw_sold in ("", "nan", "None", "null"):
            row_issues.append(RowIssue(
                row_index=row_num, column="tickets_sold",
                severity=IssueSeverity.ERROR, code="MISSING_SOLD",
                message="tickets_sold is missing.",
            ))
            is_rejected = True
            sold_val = None
        else:
            sold_val = _try_float(raw_sold)
            if sold_val is None:
                row_issues.append(RowIssue(
                    row_index=row_num, column="tickets_sold",
                    severity=IssueSeverity.ERROR, code="INVALID_SOLD",
                    message=f"tickets_sold '{raw_sold}' is not a valid number.",
                ))
                is_rejected = True
            elif sold_val < 0:
                row_issues.append(RowIssue(
                    row_index=row_num, column="tickets_sold",
                    severity=IssueSeverity.ERROR, code="NEGATIVE_SOLD",
                    message=f"tickets_sold cannot be negative (got {sold_val}).",
                ))
                is_rejected = True
            else:
                if sold_val != int(sold_val):
                    row_issues.append(RowIssue(
                        row_index=row_num, column="tickets_sold",
                        severity=IssueSeverity.ERROR, code="NONINTEGER_SOLD",
                        message=(
                            f"tickets_sold {sold_val} is not a whole number; "
                            "ticket counts must be nonnegative integers."
                        ),
                    ))
                    is_rejected = True

        # --- event_id
        raw_id = str(row.get("event_id", "")).strip()
        if raw_id in ("", "nan", "None", "null"):
            row_issues.append(RowIssue(
                row_index=row_num, column="event_id",
                severity=IssueSeverity.ERROR, code="MISSING_EVENT_ID",
                message="event_id is missing.",
            ))
            is_rejected = True

        # --- venue_capacity (optional)
        if "venue_capacity" in df.columns:
            raw_cap = str(row.get("venue_capacity", "")).strip()
            if raw_cap not in ("", "nan", "None", "null"):
                cap_val = _try_float(raw_cap)
                if cap_val is None or cap_val <= 0 or cap_val != int(cap_val):
                    row_issues.append(RowIssue(
                        row_index=row_num, column="venue_capacity",
                        severity=IssueSeverity.ERROR, code="INVALID_CAPACITY",
                        message=f"venue_capacity '{raw_cap}' must be a positive integer or blank.",
                    ))
                    is_rejected = True
                elif sold_val is not None and sold_val > cap_val:
                    row_issues.append(RowIssue(
                        row_index=row_num, column="tickets_sold",
                        severity=IssueSeverity.ERROR, code="EXCEEDS_CAPACITY",
                        message=(
                            f"tickets_sold ({int(sold_val)}) exceeds "
                            f"venue_capacity ({int(cap_val)})."
                        ),
                    ))
                    is_rejected = True

        raw_date = str(row.get("event_date", "")).strip()
        if raw_date:
            try:
                date.fromisoformat(raw_date)
            except ValueError:
                row_issues.append(RowIssue(
                    row_index=row_num, column="event_date", severity=IssueSeverity.WARNING,
                    code="INVALID_DATE", message="event_date must use an ISO calendar date (YYYY-MM-DD)."
                ))

        if (price_val is not None and abs(price_val) > 1e12) or (sold_val is not None and abs(sold_val) > 1e12):
            row_issues.append(RowIssue(
                row_index=row_num, column=None, severity=IssueSeverity.ERROR,
                code="NUMERICAL_LIMIT", message="Numeric values exceed the supported maximum of 1e12."
            ))
            is_rejected = True

        issues.extend(row_issues)
        if is_rejected:
            rejected_indices.append(int(idx))
        else:
            valid_indices.append(int(idx))

    result.issues = issues
    result.warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
    result.rejected_rows = len(rejected_indices)
    result.valid_rows = len(valid_indices)

    # Build valid and rejected DataFrames
    valid_df = df.iloc[valid_indices].copy().reset_index(drop=True)
    valid_df['_source_row'] = [index + 2 for index in valid_indices]
    rejected_df = df.iloc[rejected_indices].copy().reset_index(drop=True)
    rejected_df["_source_row"] = [idx + 2 for idx in rejected_indices]
    issues_by_source: dict[int, list[str]] = {}
    for issue in issues:
        issues_by_source.setdefault(issue.row_index, []).append(issue.message)
    rejected_df["_errors"] = ["; ".join(issues_by_source.get(idx + 2, []))
                              for idx in rejected_indices]

    # Type-cast valid rows
    if not valid_df.empty:
        valid_df["ticket_price"] = valid_df["ticket_price"].map(_try_float)
        valid_df["tickets_sold"] = valid_df["tickets_sold"].map(_try_float).astype("Int64")
        valid_df["observed_revenue"] = valid_df["ticket_price"] * valid_df["tickets_sold"]

        if "venue_capacity" in valid_df.columns:
            valid_df["venue_capacity"] = valid_df["venue_capacity"].map(_try_float)

        # Compute price statistics
        prices = valid_df["ticket_price"].dropna()
        result.price_min = float(prices.min()) if len(prices) > 0 else None
        result.price_max = float(prices.max()) if len(prices) > 0 else None
        result.price_mean = float(prices.mean()) if len(prices) > 0 else None
        result.unique_prices = int(prices.nunique())
        result.unique_event_ids = int(valid_df["event_id"].nunique())
        result.capacity_available = "venue_capacity" in valid_df.columns and valid_df["venue_capacity"].notna().any()

        # Sellout check
        if result.capacity_available:
            cap_col = valid_df["venue_capacity"]
            sold_col = valid_df["tickets_sold"]
            result.sellout_count = int((sold_col >= cap_col).sum())
            if result.sellout_count > 0:
                pct = result.sellout_count / len(valid_df) * 100
                result.has_sellout_warning = True
                result.sellout_warning_message = (
                    f"{result.sellout_count} of {len(valid_df)} observations ({pct:.0f}%) "
                    "appear to be sold-out events. Observed sales at capacity may underestimate "
                    "true unconstrained demand. Regression estimates should be interpreted cautiously."
                )

    result.valid_dataframe = valid_df
    result.rejected_dataframe = rejected_df

    # --- Regression eligibility
    _assess_eligibility(result)

    return result


def _assess_eligibility(result: ValidationResult) -> None:
    """Determine whether regression is mathematically feasible given the valid data."""
    n = result.valid_rows
    k_prices = result.unique_prices
    notes: list[str] = []

    if n < MIN_ROWS_FOR_LINEAR or k_prices < MIN_DISTINCT_PRICES_LINEAR:
        result.linear_eligible = False
        result.quadratic_eligible = False
        notes.append(
            f"Linear regression requires at least {MIN_ROWS_FOR_LINEAR} observations "
            f"with at least {MIN_DISTINCT_PRICES_LINEAR} distinct prices. "
            f"Found {n} valid rows with {k_prices} distinct price(s)."
        )
    else:
        result.linear_eligible = True
        notes.append(f"Linear regression is eligible ({n} rows, {k_prices} distinct prices).")

    if n < MIN_ROWS_FOR_QUADRATIC or k_prices < MIN_DISTINCT_PRICES_QUADRATIC:
        result.quadratic_eligible = False
        notes.append(
            f"Quadratic regression requires at least {MIN_ROWS_FOR_QUADRATIC} observations "
            f"with at least {MIN_DISTINCT_PRICES_QUADRATIC} distinct prices. "
            f"Found {n} valid rows with {k_prices} distinct price(s)."
        )
    else:
        result.quadratic_eligible = True

        if n >= RECOMMENDED_MIN_ROWS_QUADRATIC and k_prices >= RECOMMENDED_MIN_DISTINCT_QUADRATIC:
            result.quadratic_recommended = True
            notes.append(
                f"Quadratic regression is well-supported ({n} rows, {k_prices} distinct prices)."
            )
        else:
            result.quadratic_recommended = False
            notes.append(
                f"Quadratic regression is mathematically feasible but may be unreliable. "
                f"At least {RECOMMENDED_MIN_ROWS_QUADRATIC} rows and "
                f"{RECOMMENDED_MIN_DISTINCT_QUADRATIC} distinct prices are recommended "
                f"(found {n} rows, {k_prices} distinct prices)."
            )

    result.eligibility_notes = notes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_csv_bytes(content: bytes, filename: str = "upload.csv") -> ValidationResult:
    """
    Full validation pipeline:
    1. Parse CSV bytes
    2. Normalise column names
    3. Check required columns
    4. Validate rows
    Returns a ValidationResult.
    """
    result = ValidationResult()

    df, parse_error = parse_csv(content, filename)
    if parse_error:
        result.issues.append(RowIssue(
            row_index=0, column=None,
            severity=IssueSeverity.ERROR, code="PARSE_ERROR",
            message=parse_error,
        ))
        return result

    # Normalise
    try:
        df, mapping = normalize_columns(df)
    except ValueError as exc:
        result.issues.append(RowIssue(0, None, IssueSeverity.ERROR, "AMBIGUOUS_COLUMN", str(exc)))
        return result
    result.column_mapping = mapping

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        for col in sorted(missing):
            result.issues.append(RowIssue(
                row_index=0, column=col,
                severity=IssueSeverity.ERROR, code="MISSING_COLUMN",
                message=(
                    f"Required column '{col}' is missing. "
                    f"Found columns: {list(df.columns)}."
                ),
            ))
        return result

    # Row-level validation
    row_result = validate_rows(df)
    row_result.column_mapping = mapping
    return row_result
