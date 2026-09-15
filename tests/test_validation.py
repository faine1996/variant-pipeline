"""Tests for the six validation rules in pipeline.common.validation."""

from __future__ import annotations

import pytest

from pipeline.common.validation import (
    ValidationError,
    check_bases,
    check_chrom,
    check_field_count,
    check_index,
    check_pos,
)
from tests.conftest import FIXTURES_DIR, read_csv_rows


def test_valid_minimal_rows_pass_every_check() -> None:
    """Every row in valid_minimal.csv should pass all six checks."""
    rows = read_csv_rows(FIXTURES_DIR / "valid_minimal.csv")
    assert rows, "fixture must contain at least one row"
    for row in rows:
        check_field_count(row)
        index, chrom, pos, ref, alt = row
        check_index(index)
        check_chrom(chrom)
        check_pos(pos)
        check_bases("REF", ref)
        check_bases("ALT", alt)


def test_multibase_alleles_accepted() -> None:
    """Multi-base REF and ALT values must be accepted, not just single bases."""
    rows = read_csv_rows(FIXTURES_DIR / "multibase_alleles.csv")
    assert rows, "fixture must contain at least one row"
    multi_base_seen = False
    for row in rows:
        _, _, _, ref, alt = row
        if len(ref) > 1 or len(alt) > 1:
            multi_base_seen = True
        check_bases("REF", ref)
        check_bases("ALT", alt)
    assert multi_base_seen, "fixture should actually contain a multi-base value"


def test_field_count_rejects_six_fields() -> None:
    """A row with an extra comma (6 fields) must fail check_field_count."""
    rows = read_csv_rows(FIXTURES_DIR / "malformed_rows.csv")
    six_field_rows = [row for row in rows if len(row) == 6]
    assert six_field_rows, "fixture should contain a 6-field row"
    with pytest.raises(ValidationError):
        check_field_count(six_field_rows[0])


def test_check_index_rejects_empty_index() -> None:
    """A row with an empty index field must fail check_index."""
    rows = read_csv_rows(FIXTURES_DIR / "malformed_rows.csv")
    empty_index_rows = [row for row in rows if len(row) == 5 and row[0] == ""]
    assert empty_index_rows, "fixture should contain a row with an empty index"
    with pytest.raises(ValidationError):
        check_index(empty_index_rows[0][0])


def test_check_chrom_rejects_empty_chrom() -> None:
    """A row with an empty CHROM field must fail check_chrom."""
    rows = read_csv_rows(FIXTURES_DIR / "malformed_rows.csv")
    empty_chrom_rows = [row for row in rows if len(row) == 5 and row[1] == ""]
    assert empty_chrom_rows, "fixture should contain a row with an empty CHROM"
    with pytest.raises(ValidationError):
        check_chrom(empty_chrom_rows[0][1])


def test_check_pos_rejects_non_numeric() -> None:
    """A non-numeric POS value must fail check_pos."""
    with pytest.raises(ValidationError):
        check_pos("not_a_number")


def test_check_pos_rejects_zero_and_negative() -> None:
    """POS must be strictly positive; zero and negative values are rejected."""
    with pytest.raises(ValidationError):
        check_pos("0")
    with pytest.raises(ValidationError):
        check_pos("-5")


def test_check_pos_accepts_positive_integer() -> None:
    """A valid positive integer string is accepted and parsed to an int."""
    assert check_pos("17282953") == 17282953


def test_check_bases_rejects_empty() -> None:
    """An empty REF or ALT value must be rejected."""
    with pytest.raises(ValidationError):
        check_bases("REF", "")
    with pytest.raises(ValidationError):
        check_bases("ALT", "")


def test_check_bases_rejects_non_acgt_letter() -> None:
    """A base outside A/C/G/T, such as N, must be rejected."""
    with pytest.raises(ValidationError):
        check_bases("REF", "N")


def test_check_bases_rejects_digit() -> None:
    """A digit inside ALT must be rejected."""
    with pytest.raises(ValidationError):
        check_bases("ALT", "1")


def test_check_bases_rejects_stray_carriage_return() -> None:
    """A trailing '\\r' that reached validation must still be rejected.

    Defence in depth: converter.py is responsible for stripping CRLF
    remnants before calling these functions, but if it ever failed to,
    validation must not silently accept the result.
    """
    with pytest.raises(ValidationError):
        check_bases("ALT", "T\r")


def test_double_defect_row_fails_at_first_broken_rule() -> None:
    """A row breaking two rules (empty index, negative POS) fails both checks."""
    rows = read_csv_rows(FIXTURES_DIR / "malformed_rows.csv")
    double_defect_rows = [
        row for row in rows if len(row) == 5 and row[0] == "" and row[2] == "-5"
    ]
    assert double_defect_rows, "fixture should contain the double-defect row"
    index, chrom, pos, ref, alt = double_defect_rows[0]
    with pytest.raises(ValidationError):
        check_index(index)
    with pytest.raises(ValidationError):
        check_pos(pos)


def test_crlf_input_yields_no_stray_carriage_return() -> None:
    """Reading a CRLF-terminated CSV must not leave '\\r' glued to ALT."""
    rows = read_csv_rows(FIXTURES_DIR / "crlf_endings.csv")
    assert rows, "fixture must contain at least one row"
    for row in rows:
        _, _, _, _, alt = row
        assert "\r" not in alt
        check_bases("ALT", alt)