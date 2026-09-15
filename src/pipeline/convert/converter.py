"""Stage 1: Convert CSV input files into JSON, validating each row."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pipeline.common.timestamps import utc_now_iso
from pathlib import Path

from pipeline.common.atomic_io import AtomicWriter, clear_directory
from pipeline.common.validation import (
    ValidationError,
    check_bases,
    check_chrom,
    check_field_count,
    check_index,
    check_pos,
)

logger = logging.getLogger(__name__)


def _validate_row(fields: list[str]) -> dict[str, object]:
    """Run all six validation rules on one row's fields.

    Args:
        fields: The row's fields, already stripped of surrounding
            whitespace.

    Returns:
        A dict with keys index, chrom, pos, ref, alt, ready to be
        serialised into the output JSON's "variants" list.

    Raises:
        ValidationError: If any of the six rules reject the row. The
            first rule to fail stops the remaining checks from running.
    """
    check_field_count(fields)
    index, chrom, pos, ref, alt = fields
    check_index(index)
    check_chrom(chrom)
    parsed_pos = check_pos(pos)
    check_bases("REF", ref)
    check_bases("ALT", alt)
    return {"index": index, "chrom": chrom, "pos": parsed_pos, "ref": ref, "alt": alt}


def convert_file(csv_path: Path, output_dir: Path) -> None:
    """Convert one input CSV into one JSON output file, streaming rows.

    Args:
        csv_path: Path to the input CSV file.
        output_dir: Directory to write the output JSON file into.

    Returns:
        None.

    Raises:
        OSError: If csv_path cannot be opened or the output cannot be
            written.
    """
    output_path = output_dir / f"{csv_path.stem}.json"
    valid_count = 0
    skipped_count = 0

    with open(csv_path, newline="", encoding="utf-8") as csv_handle:
        reader = csv.reader(csv_handle)
        next(reader)

        with AtomicWriter(output_path) as out_handle:
            out_handle.write("{\n")
            out_handle.write(f'  "source_file": {json.dumps(csv_path.name)},\n')
            out_handle.write(f'  "converted_at": {json.dumps(utc_now_iso())},\n')
            out_handle.write('  "variants": [')

            first_variant = True
            for fields in reader:
                stripped = [field.strip() for field in fields]
                try:
                    variant = _validate_row(stripped)
                except ValidationError as exc:
                    skipped_count += 1
                    logger.warning(
                        "%s line %d: skipped row: %s",
                        csv_path.name,
                        reader.line_num,
                        exc.reason,
                    )
                    continue
                separator = "" if first_variant else ","
                out_handle.write(f"{separator}\n    {json.dumps(variant)}")
                first_variant = False
                valid_count += 1

            if not first_variant:
                out_handle.write("\n  ")
            out_handle.write("],\n")
            counts = {"valid": valid_count, "skipped": skipped_count}
            out_handle.write(f'  "counts": {json.dumps(counts)}\n')
            out_handle.write("}\n")


def convert_all(input_dir: Path, output_dir: Path) -> None:
    """Convert every CSV in input_dir, one JSON output file per input.

    Args:
        input_dir: Directory containing input CSV files.
        output_dir: Directory to write output JSON files into. Cleared
            before conversion starts.

    Returns:
        None.

    Raises:
        OSError: If input_dir cannot be read or any output cannot be
            written.
    """
    clear_directory(output_dir)
    for csv_path in sorted(input_dir.glob("*.csv")):
        convert_file(csv_path, output_dir)