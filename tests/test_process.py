"""Tests for Stage 2 (Process): metrics fields, sleep timing, and count carry-through."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline.convert.converter import convert_file
from pipeline.process.processor import process_file
from tests.conftest import FIXTURES_DIR


def _convert_then_process(
    fixture_name: str, tmp_path: Path, sleep_seconds: float
) -> dict[str, object]:
    """Run Convert then Process on a fixture CSV, returning the metrics dict.

    Args:
        fixture_name: Filename of a CSV under tests/fixtures/.
        tmp_path: Pytest's per-test temporary directory.
        sleep_seconds: Value to pass through to process_file.

    Returns:
        The parsed *.meta.json output as a dict.

    Raises:
        OSError: If any file cannot be read or written.
        json.JSONDecodeError: If an output file is not valid JSON.
    """
    input_dir = tmp_path / "input"
    convert_dir = tmp_path / "convert"
    process_dir = tmp_path / "process"
    input_dir.mkdir(exist_ok=True)


    csv_path = input_dir / fixture_name
    shutil.copy(FIXTURES_DIR / fixture_name, csv_path)
    convert_file(csv_path, convert_dir)

    json_path = convert_dir / f"{csv_path.stem}.json"
    process_file(json_path, process_dir, sleep_seconds)

    meta_path = process_dir / f"{csv_path.stem}.meta.json"
    with open(meta_path, encoding="utf-8") as handle:
        return json.load(handle)


def test_metrics_file_has_all_six_fields(tmp_path: Path) -> None:
    """The output metrics file has exactly the six fields PLAN.md specifies."""
    metrics = _convert_then_process("valid_minimal.csv", tmp_path, sleep_seconds=0)
    assert set(metrics.keys()) == {
        "source_file",
        "started_at",
        "finished_at",
        "duration_seconds",
        "row_count",
        "skipped_count",
    }


def test_sleep_seconds_is_honoured(tmp_path: Path) -> None:
    """duration_seconds reflects the actual sleep_seconds passed in."""
    metrics = _convert_then_process("valid_minimal.csv", tmp_path, sleep_seconds=0.3)
    # 10ms tolerance: time.sleep() precision varies by platform, and Windows'
    # coarser timer granularity can return a fraction early.
    assert metrics["duration_seconds"] >= 0.3 - 0.01


def test_zero_sleep_seconds_is_fast(tmp_path: Path) -> None:
    """A sleep_seconds of 0 must not introduce any real delay."""
    metrics = _convert_then_process("valid_minimal.csv", tmp_path, sleep_seconds=0)
    assert metrics["duration_seconds"] < 0.5


def test_counts_are_carried_through_from_convert(tmp_path: Path) -> None:
    """row_count and skipped_count match Stage 1's counts exactly."""
    valid_metrics = _convert_then_process("valid_minimal.csv", tmp_path, sleep_seconds=0)
    assert valid_metrics["row_count"] == 2
    assert valid_metrics["skipped_count"] == 0

    malformed_metrics = _convert_then_process(
        "malformed_rows.csv", tmp_path, sleep_seconds=0
    )
    assert malformed_metrics["row_count"] == 0
    assert malformed_metrics["skipped_count"] == 8