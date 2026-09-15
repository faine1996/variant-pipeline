"""Logging configuration shared by all pipeline stages.

Ensures warnings and errors go to stderr, never to a file or stdout,
per project convention (DECISIONS.md D4).
"""

from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Configure the root logger to write to stderr.

    Every pipeline stage calls this once, at startup, before doing any
    other work.

    Args:
        None.

    Returns:
        None.

    Raises:
        Nothing.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )