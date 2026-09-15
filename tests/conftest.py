"""Shared helpers for the pipeline test suite."""

from __future__ import annotations

import csv
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_csv_rows(path: Path) -> list[list[str]]:
    """Read a CSV fixture file, returning each data row as a list of stripped fields.

    Skips the header row. Opens with newline='' so the csv module handles
    CRLF line endings correctly, matching how converter.py will read real
    input files.

    Args:
        path: Path to the CSV fixture file.

    Returns:
        A list of rows, each row itself a list of field strings with
        surrounding whitespace stripped.

    Raises:
        OSError: If the file cannot be opened.
    """
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)
        return [[field.strip() for field in row] for row in reader]