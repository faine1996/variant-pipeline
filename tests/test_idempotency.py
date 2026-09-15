"""End-to-end tests for pipeline idempotency: rerun stability and input removal."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline.aggregate.aggregator import aggregate
from pipeline.convert.converter import convert_all
from pipeline.process.processor import process_all
from tests.conftest import FIXTURES_DIR


def _run_pipeline(input_dir: Path, work_dir: Path) -> dict[str, object]:
    """Run all three stages against input_dir, returning the summary dict.

    Args:
        input_dir: Directory containing input CSV files.
        work_dir: Directory to hold Convert/Process work output and the
            final summary.

    Returns:
        The parsed summary.json output as a dict.

    Raises:
        OSError: If any file cannot be read or written.
        json.JSONDecodeError: If an output file is not valid JSON.
    """
    convert_dir = work_dir / "convert"
    process_dir = work_dir / "process"
    summary_path = work_dir / "summary.json"

    convert_all(input_dir, convert_dir)
    process_all(convert_dir, process_dir, sleep_seconds=0)
    aggregate(convert_dir, process_dir, summary_path)

    with open(summary_path, encoding="utf-8") as handle:
        return json.load(handle)


def _stable_fields(summary: dict[str, object]) -> dict[str, object]:
    """Return a copy of a summary dict without fields expected to vary between runs.

    "generated_at" and "total_processing_seconds" are both timing-derived
    and are not required to be identical for the pipeline to be
    considered idempotent — only the actual data (counts, tallies, which
    files were processed) needs to match exactly between runs.

    Args:
        summary: A parsed summary.json dict.

    Returns:
        A shallow copy of summary, without those two keys.

    Raises:
        Nothing.
    """
    excluded = {"generated_at", "total_processing_seconds"}
    return {key: value for key, value in summary.items() if key not in excluded}


def test_rerun_produces_identical_summary(tmp_path: Path) -> None:
    """Running the pipeline twice on unchanged input gives the same result."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "valid_minimal.csv", input_dir / "valid_minimal.csv")
    shutil.copy(
        FIXTURES_DIR / "multibase_alleles.csv", input_dir / "multibase_alleles.csv"
    )

    first_summary = _run_pipeline(input_dir, tmp_path / "work")
    second_summary = _run_pipeline(input_dir, tmp_path / "work")
    assert _stable_fields(first_summary) == _stable_fields(second_summary)


def test_removing_input_excludes_it_from_next_run(tmp_path: Path) -> None:
    """Deleting an input file and rerunning removes it from the summary."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "valid_minimal.csv", input_dir / "valid_minimal.csv")
    shutil.copy(
        FIXTURES_DIR / "multibase_alleles.csv", input_dir / "multibase_alleles.csv"
    )

    first_summary = _run_pipeline(input_dir, tmp_path / "work")
    assert "multibase_alleles.csv" in first_summary["input_files_processed"]
    assert first_summary["total_variants"] == 5

    (input_dir / "multibase_alleles.csv").unlink()
    second_summary = _run_pipeline(input_dir, tmp_path / "work")

    assert second_summary["input_files_processed"] == ["valid_minimal.csv"]
    assert second_summary["total_variants"] == 2