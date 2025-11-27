"""Output formatting helpers for the Vault CLI."""

from __future__ import annotations

from typing import Any, Dict

from rich.console import Console
from rich.table import Table

console = Console()


def _truncate(value: str, limit: int = 50) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def render_secrets_table(data: Dict[str, Any]) -> None:
    """Render a formatted table of secrets."""

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Key", style="bold", overflow="fold")
    table.add_column("Value", overflow="fold")

    for key, value in sorted(data.items()):
        display_value = _truncate(str(value))
        table.add_row(key, display_value)

    console.print(table)
