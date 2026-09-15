"""Atomic file writing and directory-clearing helpers shared by all pipeline stages."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import TracebackType
from typing import TextIO


def clear_directory(directory: Path) -> None:
    """Delete every file directly inside a directory, creating it if absent.

    Args:
        directory: The directory to clear. Only files directly inside it
            are removed.

    Returns:
        None.

    Raises:
        OSError: If a file exists but cannot be deleted.
    """
    directory.mkdir(parents=True, exist_ok=True)
    for entry in directory.iterdir():
        if entry.is_file():
            entry.unlink()


class AtomicWriter:
    """Writes to a temp file, renaming it into place only if writing succeeds.

    Used as: `with AtomicWriter(path) as handle: handle.write(...)`.
    If the block raises, the temp file is deleted and `path` is left
    untouched. If the block finishes normally, the temp file is atomically
    renamed to `path`.
    """

    def __init__(self, final_path: Path) -> None:
        """Store the destination path; no file is created yet.

        Args:
            final_path: Where the file should end up once writing succeeds.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.final_path = final_path
        self._temp_path: Path | None = None
        self._handle: TextIO | None = None

    def __enter__(self) -> TextIO:
        """Create the temp file and return it open for writing.

        Args:
            None (other than self).

        Returns:
            An open, writable text file handle.

        Raises:
            OSError: If the temp file cannot be created.
        """
        self.final_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            dir=self.final_path.parent,
            prefix=f".{self.final_path.name}.",
            suffix=".tmp",
        )
        self._temp_path = Path(temp_name)
        self._handle = os.fdopen(fd, "w", encoding="utf-8")
        return self._handle

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Close the temp file, then rename it into place or delete it.

        Args:
            exc_type: The exception type raised inside the `with` block,
                or None if it finished without error.
            exc_value: The exception instance, or None.
            traceback: The exception's traceback, or None.

        Returns:
            False, always — this never suppresses an exception raised
            inside the `with` block.

        Raises:
            OSError: If closing, renaming, or deleting the temp file fails.
        """
        assert self._handle is not None
        assert self._temp_path is not None
        self._handle.close()
        if exc_type is None:
            os.replace(self._temp_path, self.final_path)
        else:
            self._temp_path.unlink(missing_ok=True)
        return False