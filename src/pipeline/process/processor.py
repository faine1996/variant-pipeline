"""Stage 2: Process converted JSON files, recording timing metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pipeline.common.atomic_io import AtomicWriter, clear_directory
from pipeline.common.timestamps import utc_now_iso


def process_file(json_path: Path, output_dir: Path, sleep_seconds: float) -> None:
    """Process one converted JSON file, recording timing metrics.

    Loads the whole input file into memory rather than streaming it — an
    accepted limit at this data scale (see PLAN.md Stage 2).

    Args:
        json_path: Path to a converted JSON file from Stage 1.
        output_dir: Directory to write the metrics output file into.
        sleep_seconds: How many seconds to sleep, simulating elapsed
            processing time.

    Returns:
        None.

    Raises:
        OSError: If json_path cannot be read or the output cannot be
            written.
        json.JSONDecodeError: If json_path is not valid JSON.
    """
    with open(json_path, encoding="utf-8") as handle:
        converted = json.load(handle)

    started_at = utc_now_iso()
    start_time = time.monotonic()
    time.sleep(sleep_seconds)
    elapsed = time.monotonic() - start_time
    finished_at = utc_now_iso()

    metrics = {
        "source_file": converted["source_file"],
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": elapsed,
        "row_count": converted["counts"]["valid"],
        "skipped_count": converted["counts"]["skipped"],
    }

    output_path = output_dir / f"{json_path.stem}.meta.json"
    with AtomicWriter(output_path) as out_handle:
        json.dump(metrics, out_handle, indent=2)
        out_handle.write("\n")


def process_all(input_dir: Path, output_dir: Path, sleep_seconds: float) -> None:
    """Process every converted JSON file in input_dir.

    Args:
        input_dir: Directory containing Stage 1's *.json output files.
        output_dir: Directory to write *.meta.json output files into.
            Cleared before processing starts.
        sleep_seconds: How many seconds to sleep per file.

    Returns:
        None.

    Raises:
        OSError: If input_dir cannot be read or any output cannot be
            written.
    """
    clear_directory(output_dir)
    for json_path in sorted(input_dir.glob("*.json")):
        process_file(json_path, output_dir, sleep_seconds)