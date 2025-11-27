"""Type coercion helpers mirroring the Go CLI behaviour."""

from __future__ import annotations

from typing import Any


def coerce_value(raw_value: str) -> Any:
    """Attempt to coerce a string into int or bool, otherwise return as-is."""

    raw_value = raw_value.strip()

    if raw_value == "":
        return ""

    # Integer preservation (base 10 only, matching strconv.Atoi).
    if raw_value.lstrip("+-").isdigit():
        try:
            return int(raw_value, 10)
        except ValueError:
            # Fallback to string if the int is out of range.
            pass

    lowered = raw_value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"

    return raw_value
