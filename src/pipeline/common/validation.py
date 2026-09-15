"""Row-level validation rules for input CSV variant records."""

from __future__ import annotations


class ValidationError(Exception):
    """Raised when a CSV row fails one or more validation rules."""

    def __init__(self, reason: str) -> None:
        """Store the human-readable reason this row was rejected.

        Args:
            reason: Short description of which rule failed, suitable for
                inclusion in a warning log line.

        Returns:
            None.

        Raises:
            Nothing.
        """
        super().__init__(reason)
        self.reason = reason


_ALLOWED_BASES = frozenset("ACGT")


def check_field_count(fields: list[str]) -> None:
    """Check that a CSV row has exactly 5 fields.

    Args:
        fields: The row's fields, already split by the csv module.

    Returns:
        None if the row has exactly 5 fields.

    Raises:
        ValidationError: If the row does not have exactly 5 fields.
    """
    if len(fields) != 5:
        raise ValidationError(f"expected 5 fields, got {len(fields)}")


def check_index(index: str) -> None:
    """Check that the index field is non-empty after stripping.

    Args:
        index: The index field, already stripped of surrounding whitespace.

    Returns:
        None if index is non-empty.

    Raises:
        ValidationError: If index is empty.
    """
    if not index:
        raise ValidationError("index is empty")


def check_chrom(chrom: str) -> None:
    """Check that the CHROM field is non-empty after stripping.

    Args:
        chrom: The CHROM field, already stripped of surrounding whitespace.

    Returns:
        None if chrom is non-empty.

    Raises:
        ValidationError: If chrom is empty.
    """
    if not chrom:
        raise ValidationError("CHROM is empty")


def check_pos(pos: str) -> int:
    """Check that the POS field parses as a positive integer.

    Args:
        pos: The POS field, already stripped of surrounding whitespace.

    Returns:
        The parsed positive integer value of pos.

    Raises:
        ValidationError: If pos does not parse as an integer, or parses
            to zero or a negative number.
    """
    try:
        value = int(pos)
    except ValueError as exc:
        raise ValidationError(f"POS is not an integer: {pos!r}") from exc
    if value <= 0:
        raise ValidationError(f"POS is not positive: {value}")
    return value


def check_bases(field_name: str, value: str) -> None:
    """Check that a field is one or more characters, all from A/C/G/T.

    Used for both REF and ALT, which share this exact rule.

    Args:
        field_name: Name of the field being checked ("REF" or "ALT"),
            used only to build a clear error message.
        value: The field value, already stripped of surrounding whitespace.

    Returns:
        None if value is 1+ characters, all from {A, C, G, T}.

    Raises:
        ValidationError: If value is empty or contains any character
            outside {A, C, G, T}.
    """
    if not value:
        raise ValidationError(f"{field_name} is empty")
    if not set(value) <= _ALLOWED_BASES:
        raise ValidationError(f"{field_name} contains invalid bases: {value!r}")