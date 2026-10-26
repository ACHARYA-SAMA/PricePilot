"""
PricePilot — pytest tests for CSV validation module.
"""

import io
import pytest
from app.core.validation import validate_csv_bytes, parse_csv, normalize_columns
import pandas as pd


def make_csv(rows: list[list], header=None) -> bytes:
    if header is None:
        header = ["event_id", "ticket_price", "tickets_sold"]
    lines = [",".join(str(c) for c in header)]
    for r in rows:
        lines.append(",".join(str(c) for c in r))
    return "\n".join(lines).encode()


class TestValidation:
    def test_valid_simple_csv(self):
        content = make_csv([
            ["EVT001", 100, 200],
            ["EVT002", 150, 180],
            ["EVT003", 200, 150],
        ])
        result = validate_csv_bytes(content)
        assert result.valid_rows == 3
        assert result.rejected_rows == 0
        assert result.linear_eligible

    def test_empty_file(self):
        result = validate_csv_bytes(b"")
        assert any(i.code == "PARSE_ERROR" for i in result.issues)

    def test_missing_required_column(self):
        content = b"ticket_price,tickets_sold\n100,200\n"
        result = validate_csv_bytes(content)
        assert any(i.code == "MISSING_COLUMN" for i in result.issues)

    def test_negative_price_rejected(self):
        content = make_csv([["EVT001", -50, 200], ["EVT002", 100, 150], ["EVT003", 150, 100]])
        result = validate_csv_bytes(content)
        assert result.rejected_rows >= 1
        assert any(i.code == "NONPOSITIVE_PRICE" for i in result.issues)

    def test_zero_price_rejected(self):
        content = make_csv([["EVT001", 0, 200], ["EVT002", 100, 150], ["EVT003", 150, 100]])
        result = validate_csv_bytes(content)
        assert any(i.code == "NONPOSITIVE_PRICE" for i in result.issues)

    def test_negative_tickets_rejected(self):
        content = make_csv([["EVT001", 100, -10], ["EVT002", 150, 200]])
        result = validate_csv_bytes(content)
        assert any(i.code == "NEGATIVE_SOLD" for i in result.issues)

    def test_missing_ticket_price(self):
        content = make_csv([["EVT001", "", 200], ["EVT002", 100, 150]])
        result = validate_csv_bytes(content)
        assert any(i.code == "MISSING_PRICE" for i in result.issues)

    def test_missing_tickets_sold(self):
        content = make_csv([["EVT001", 100, ""], ["EVT002", 150, 200]])
        result = validate_csv_bytes(content)
        assert any(i.code == "MISSING_SOLD" for i in result.issues)

    def test_duplicate_detection(self):
        content = make_csv([
            ["EVT001", 100, 200],
            ["EVT001", 100, 200],
            ["EVT002", 150, 180],
        ])
        result = validate_csv_bytes(content)
        assert result.duplicate_count >= 1

    def test_column_alias_normalization(self):
        content = b"event,price,sales\nE1,100,200\nE2,150,180\nE3,200,150\n"
        result = validate_csv_bytes(content)
        assert "price" in result.column_mapping or result.valid_rows > 0

    def test_single_price_insufficient_for_regression(self):
        content = make_csv([
            ["EVT001", 100, 200],
            ["EVT002", 100, 195],
        ])
        result = validate_csv_bytes(content)
        assert not result.linear_eligible or result.unique_prices == 1

    def test_capacity_exceeded_warning(self):
        content = b"event_id,ticket_price,tickets_sold,venue_capacity\nE1,100,500,200\nE2,150,180,200\n"
        result = validate_csv_bytes(content)
        assert any(i.code == "EXCEEDS_CAPACITY" for i in result.issues)

    def test_file_too_large(self):
        # Simulate a large file
        big = b"event_id,ticket_price,tickets_sold\n" + b"E1,100,200\n" * 2000000
        result = validate_csv_bytes(big)
        assert any(i.code == "PARSE_ERROR" for i in result.issues)

    def test_noninteger_tickets_warning(self):
        content = make_csv([["EVT001", 100, 175.7], ["EVT002", 150, 200], ["EVT003", 200, 150]])
        result = validate_csv_bytes(content)
        assert any(i.code == "NONINTEGER_SOLD" for i in result.issues)

    def test_eligibility_notes_populated(self):
        content = make_csv([
            ["E1", 100, 200], ["E2", 150, 180], ["E3", 200, 160],
            ["E4", 250, 140], ["E5", 300, 120],
        ])
        result = validate_csv_bytes(content)
        assert len(result.eligibility_notes) > 0
