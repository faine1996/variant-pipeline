"""Stage 3: Aggregate converted and processed outputs into a summary."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.common.atomic_io import AtomicWriter
from pipeline.common.timestamps import utc_now_iso


def _chrom_sort_key(chrom: str) -> tuple[int, object]:
    """Build a sort key giving natural chromosome ordering (chr1..chr22, chrX, chrY).

    Args:
        chrom: A chromosome label, e.g. "chr1" or "chrX".

    Returns:
        A tuple usable as a sort key: numbered chromosomes sort first, by
        their numeric value; anything else (chrX, chrY, or any
        non-standard contig) sorts after, alphabetically.

    Raises:
        Nothing.
    """
    suffix = chrom.removeprefix("chr")
    if suffix.isdigit():
        return (0, int(suffix))
    return (1, suffix)


def aggregate(convert_dir: Path, process_dir: Path, output_path: Path) -> None:
    """Combine Convert and Process outputs into one summary file.

    Args:
        convert_dir: Directory containing Stage 1's *.json output files.
        process_dir: Directory containing Stage 2's *.meta.json output
            files.
        output_path: Path to write the summary JSON file to.

    Returns:
        None.

    Raises:
        OSError: If either input directory cannot be read or the output
            cannot be written.
        json.JSONDecodeError: If an input file is not valid JSON.
    """
    input_files_processed: list[str] = []
    total_variants = 0
    total_skipped_rows = 0
    chrom_tally: dict[str, int] = {}

    for json_path in sorted(convert_dir.glob("*.json")):
        with open(json_path, encoding="utf-8") as handle:
            converted = json.load(handle)
        input_files_processed.append(converted["source_file"])
        total_variants += converted["counts"]["valid"]
        total_skipped_rows += converted["counts"]["skipped"]
        for variant in converted["variants"]:
            chrom = variant["chrom"]
            chrom_tally[chrom] = chrom_tally.get(chrom, 0) + 1

    total_processing_seconds = 0.0
    for meta_path in sorted(process_dir.glob("*.meta.json")):
        with open(meta_path, encoding="utf-8") as handle:
            metrics = json.load(handle)
        total_processing_seconds += metrics["duration_seconds"]

    variants_per_chromosome = {
        chrom: chrom_tally[chrom] for chrom in sorted(chrom_tally, key=_chrom_sort_key)
    }

    summary = {
        "generated_at": utc_now_iso(),
        "input_files_processed": input_files_processed,
        "total_variants": total_variants,
        "total_skipped_rows": total_skipped_rows,
        "total_processing_seconds": total_processing_seconds,
        "variants_per_chromosome": variants_per_chromosome,
    }

    with AtomicWriter(output_path) as out_handle:
        json.dump(summary, out_handle, indent=2)
        out_handle.write("\n")