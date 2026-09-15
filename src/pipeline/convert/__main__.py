"""Command-line entry point for the Convert stage."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.common.log_setup import configure_logging
from pipeline.convert.converter import convert_all


def main() -> None:
    """Parse command-line arguments and run the Convert stage.

    Args:
        None.

    Returns:
        None.

    Raises:
        Nothing beyond what convert_all raises for I/O failures.
    """
    configure_logging()
    parser = argparse.ArgumentParser(description="Convert input CSVs to JSON.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/input"),
        help="Directory containing input CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/work/convert"),
        help="Directory to write converted JSON files into.",
    )
    args = parser.parse_args()
    convert_all(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()