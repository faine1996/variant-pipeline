"""Environment-variable-driven configuration shared by pipeline stages."""

from __future__ import annotations

import os

DEFAULT_SLEEP_SECONDS = 30.0


def get_sleep_seconds() -> float:
    """Read the SLEEP_SECONDS environment variable, defaulting to 30.

    Args:
        None.

    Returns:
        The number of seconds Stage 2 (Process) should sleep per file,
        as a float. Defaults to 30.0 if the environment variable is
        unset.

    Raises:
        ValueError: If SLEEP_SECONDS is set but is not a valid number.
    """
    raw_value = os.environ.get("SLEEP_SECONDS")
    if raw_value is None:
        return DEFAULT_SLEEP_SECONDS
    return float(raw_value)