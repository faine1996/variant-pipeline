"""Regression tests against the real sample data in data/input/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline.aggregate.aggregator import aggregate
from pipeline.convert.converter import convert_all, convert_file

PROJECT_ROOT = Path(__file__).parent.parent
REAL_INPUT_DIR = PROJECT_ROOT / "data" / "input"

NUMBERED_FILES = [f"variants_{i}.csv" for i in range(1, 6)]

EXPECTED_CHROMOSOME_TALLY = {
    "chr1": 12,
    "chr2": 14,
    "chr3": 8,
    "chr4": 7,
    "chr5": 9,
    "chr6": 7,
    "chr7": 8,
    "chr8": 6,
    "chr9": 6,
    "chr10": 6,
    "chr11": 7,
    "chr12": 7,
    "chr13": 5,
    "chr14": 5,
    "chr15": 5,
    "chr16": 6,
    "chr17": 5,
    "chr18": 6,
    "chr19": 5,
    "chr20": 5,
    "chr21": 6,
    "chr22": 5,
    "chrX": 6,
    "chrY": 5,
}


def test_five_numbered_files_match_verification_target(tmp_path: Path) -> None:
    """The five numbered sample CSVs, isolated, produce exactly the documented totals."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    for filename in NUMBERED_FILES:
        shutil.copy(REAL_INPUT_DIR / filename, input_dir / filename)

    from pipeline.process.processor import process_all

    convert_dir = tmp_path / "convert"
    process_dir = tmp_path / "process"
    summary_path = tmp_path / "summary.json"

    convert_all(input_dir, convert_dir)
    process_all(convert_dir, process_dir, sleep_seconds=0)
    aggregate(convert_dir, process_dir, summary_path)

    with open(summary_path, encoding="utf-8") as handle:
        summary = json.load(handle)

    assert summary["total_variants"] == 161
    assert summary["total_skipped_rows"] == 0
    assert len(summary["variants_per_chromosome"]) == 24
    assert summary["variants_per_chromosome"] == EXPECTED_CHROMOSOME_TALLY


def test_variants_clean_is_all_valid(tmp_path: Path) -> None:
    """variants_clean.csv: 6 valid, 0 skipped."""
    output_dir = tmp_path / "convert"
    convert_file(REAL_INPUT_DIR / "variants_clean.csv", output_dir)

    with open(output_dir / "variants_clean.json", encoding="utf-8") as handle:
        result = json.load(handle)

    assert result["counts"] == {"valid": 6, "skipped": 0}


def test_variants_messy_matches_corrected_target(tmp_path: Path) -> None:
    """variants_messy.csv: 4 valid, 8 skipped (see DECISIONS.md D16)."""
    output_dir = tmp_path / "convert"
    convert_file(REAL_INPUT_DIR / "variants_messy.csv", output_dir)

    with open(output_dir / "variants_messy.json", encoding="utf-8") as handle:
        result = json.load(handle)

    assert result["counts"] == {"valid": 4, "skipped": 8}