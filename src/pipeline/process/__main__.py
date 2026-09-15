"""Command-line entry point for the Process stage."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.common.config import get_sleep_seconds
from pipeline.common.log_setup import configure_logging
from pipeline.process.processor import process_all


def main() -> None:
    """Parse command-line arguments and run the Process stage.

    Args:
        None.

    Returns:
        None.

    Raises:
        Nothing beyond what process_all raises for I/O failures.
    """
    configure_logging()
    parser = argparse.ArgumentParser(description="Process converted JSON files.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/work/convert"),
        help="Directory containing Stage 1's *.json output files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/work/process"),
        help="Directory to write *.meta.json output files into.",
    )
    args = parser.parse_args()
    process_all(args.input_dir, args.output_dir, get_sleep_seconds())


if __name__ == "__main__":
    main()
