"""Command-line entry point for the Aggregate stage."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.aggregate.aggregator import aggregate
from pipeline.common.log_setup import configure_logging


def main() -> None:
    """Parse command-line arguments and run the Aggregate stage.

    Args:
        None.

    Returns:
        None.

    Raises:
        Nothing beyond what aggregate raises for I/O failures.
    """
    configure_logging()
    parser = argparse.ArgumentParser(description="Aggregate stage outputs into a summary.")
    parser.add_argument(
        "--convert-dir",
        type=Path,
        default=Path("data/work/convert"),
        help="Directory containing Stage 1's *.json output files.",
    )
    parser.add_argument(
        "--process-dir",
        type=Path,
        default=Path("data/work/process"),
        help="Directory containing Stage 2's *.meta.json output files.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("data/output/summary.json"),
        help="Path to write the summary JSON file to.",
    )
    args = parser.parse_args()
    aggregate(args.convert_dir, args.process_dir, args.output_path)


if __name__ == "__main__":
    main()