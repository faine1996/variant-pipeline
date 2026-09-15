"""Tests for Stage 1 (Convert): row validation, skip logging, and CRLF handling."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import pytest

from pipeline.convert.converter import convert_file
from tests.conftest import FIXTURES_DIR


def _run_convert(fixture_name: str, tmp_path: Path) -> dict[str, object]:
    """Copy a fixture CSV into a temp dir, convert it, and load the JSON result.

    Args:
        fixture_name: Filename of a CSV under tests/fixtures/.
        tmp_path: Pytest's per-test temporary directory.

    Returns:
        The parsed JSON output as a dict.

    Raises:
        OSError: If the fixture cannot be copied or the output read.
        json.JSONDecodeError: If the output is not valid JSON.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    csv_path = input_dir / fixture_name
    shutil.copy(FIXTURES_DIR / fixture_name, csv_path)

    convert_file(csv_path, output_dir)

    output_path = output_dir / f"{csv_path.stem}.json"
    with open(output_path, encoding="utf-8") as handle:
        return json.load(handle)


def test_valid_minimal_produces_one_object_per_row(tmp_path: Path) -> None:
    """Each valid row in the input becomes one object in "variants"."""
    result = _run_convert("valid_minimal.csv", tmp_path)
    assert result["counts"] == {"valid": 2, "skipped": 0}
    assert len(result["variants"]) == 2
    assert result["variants"][0] == {
        "index": "chr1:1000_A/T",
        "chrom": "chr1",
        "pos": 1000,
        "ref": "A",
        "alt": "T",
    }


def test_malformed_rows_are_skipped_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Every row in malformed_rows.csv is skipped, each with its own warning."""
    with caplog.at_level(logging.WARNING):
        result = _run_convert("malformed_rows.csv", tmp_path)

    assert result["counts"] == {"valid": 0, "skipped": 8}
    assert result["variants"] == []
    assert len(caplog.records) == 8
    assert all("malformed_rows.csv" in record.getMessage() for record in caplog.records)


def test_crlf_input_yields_no_stray_carriage_return(tmp_path: Path) -> None:
    """A CRLF-terminated input file must not leak '\\r' into ALT values."""
    result = _run_convert("crlf_endings.csv", tmp_path)
    assert result["counts"]["skipped"] == 0
    for variant in result["variants"]:
        assert "\r" not in variant["alt"]