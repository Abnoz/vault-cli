"""Input/output helpers for interactive CLI behaviour."""

from __future__ import annotations

import sys
from typing import TextIO

import typer


class InputNotInteractiveError(RuntimeError):
    """Raised when a command requires interactive input but stdin is not a TTY."""


def is_tty(stream: TextIO) -> bool:
    """Return True if the given stream is attached to a TTY."""

    try:
        return stream.isatty()
    except Exception:  # pragma: no cover - platform specific edge cases
        return False


def prompt_value(prompt: str) -> str:
    """Prompt the user for a new value (supports piped stdin)."""

    if is_tty(sys.stdin):
        return typer.prompt(prompt)

    # Non-interactive input: read everything from stdin.
    data = sys.stdin.read().strip()
    if not data:
        raise InputNotInteractiveError(
            "Cannot prompt for a value when stdin is not interactive.",
        )
    return data


def confirm(prompt: str) -> bool:
    """Prompt the user for a yes/no confirmation."""

    if not is_tty(sys.stdin):
        raise InputNotInteractiveError(
            "Confirmation requires interactive stdin; use --force to bypass.",
        )

    return typer.confirm(prompt, default=False)
