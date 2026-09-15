"""Tests for Stage 3 (Aggregate): tallies, totals, and chromosome ordering."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline.aggregate.aggregator import aggregate
from pipeline.convert.converter import convert_file
from pipeline.process.processor import process_file
from tests.conftest import FIXTURES_DIR


def _write_convert_json(path: Path, source_file: str, chroms: list[str]) -> None:
    """Write a minimal Stage-1-shaped JSON file directly, for ordering tests.

    Args:
        path: Where to write the JSON file.
        source_file: Value for the "source_file" field.
        chroms: One chromosome name per variant to include; each becomes
            a minimal variant entry.

    Returns:
        None.

    Raises:
        OSError: If the file cannot be written.
    """
    variants = [
        {"index": f"{chrom}:1_A/T", "chrom": chrom, "pos": 1, "ref": "A", "alt": "T"}
        for chrom in chroms
    ]
    data = {
        "source_file": source_file,
        "converted_at": "2026-01-01T00:00:00Z",
        "variants": variants,
        "counts": {"valid": len(variants), "skipped": 0},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


def _run_full_pipeline(fixture_names: list[str], tmp_path: Path) -> dict[str, object]:
    """Run Convert, Process, and Aggregate on a set of fixture CSVs.

    Args:
        fixture_names: Filenames of CSVs under tests/fixtures/ to include.
        tmp_path: Pytest's per-test temporary directory.

    Returns:
        The parsed summary.json output as a dict.

    Raises:
        OSError: If any file cannot be read or written.
        json.JSONDecodeError: If an output file is not valid JSON.
    """
    input_dir = tmp_path / "input"
    convert_dir = tmp_path / "convert"
    process_dir = tmp_path / "process"
    input_dir.mkdir(exist_ok=True)

    for fixture_name in fixture_names:
        csv_path = input_dir / fixture_name
        shutil.copy(FIXTURES_DIR / fixture_name, csv_path)
        convert_file(csv_path, convert_dir)
        json_path = convert_dir / f"{csv_path.stem}.json"
        process_file(json_path, process_dir, sleep_seconds=0)

    summary_path = tmp_path / "summary.json"
    aggregate(convert_dir, process_dir, summary_path)

    with open(summary_path, encoding="utf-8") as handle:
        return json.load(handle)


def test_natural_chromosome_ordering(tmp_path: Path) -> None:
    """Chromosomes sort numerically (chr2 before chr10), not alphabetically."""
    convert_dir = tmp_path / "convert"
    process_dir = tmp_path / "process"
    process_dir.mkdir(parents=True)
    _write_convert_json(
        convert_dir / "sample.json",
        "sample.csv",
        ["chr10", "chr2", "chr1", "chrY", "chrX"],
    )

    summary_path = tmp_path / "summary.json"
    aggregate(convert_dir, process_dir, summary_path)

    with open(summary_path, encoding="utf-8") as handle:
        summary = json.load(handle)

    assert list(summary["variants_per_chromosome"].keys()) == [
        "chr1",
        "chr2",
        "chr10",
        "chrX",
        "chrY",
    ]


def test_totals_and_input_files_from_two_fixtures(tmp_path: Path) -> None:
    """Totals, skip count, and input_files_processed reflect both input files."""
    summary = _run_full_pipeline(["valid_minimal.csv", "multibase_alleles.csv"], tmp_path)
    assert summary["input_files_processed"] == [
        "multibase_alleles.csv",
        "valid_minimal.csv",
    ]
    assert summary["total_variants"] == 5
    assert summary["total_skipped_rows"] == 0
    assert summary["variants_per_chromosome"] == {
        "chr1": 2,
        "chr2": 1,
        "chr3": 1,
        "chr5": 1,
    }


def test_skipped_rows_total_across_files(tmp_path: Path) -> None:
    """total_skipped_rows sums skips from every input file."""
    summary = _run_full_pipeline(["valid_minimal.csv", "malformed_rows.csv"], tmp_path)
    assert summary["total_variants"] == 2
    assert summary["total_skipped_rows"] == 8
    assert summary["total_processing_seconds"] < 0.5