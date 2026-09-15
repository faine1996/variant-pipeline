"""Shared UTC timestamp formatting for pipeline stage outputs."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Args:
        None.

    Returns:
        A timestamp like "2026-09-14T12:00:00Z".

    Raises:
        Nothing.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")