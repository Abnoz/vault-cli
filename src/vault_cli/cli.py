"""Typer-powered command implementation for the Python Vault CLI."""

from __future__ import annotations

from typing import Any, Dict, Optional

import typer

from vault_core.config import ConfigError, VaultSettings, load_vault_settings
from vault_core.vault import VaultClient, VaultClientError

from .formatting import render_secrets_table
from .io import InputNotInteractiveError, confirm, prompt_value
from .types import coerce_value

app = typer.Typer(help="Python Vault CLI with feature parity to the Go version")


def _die(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def _ensure_ctx(ctx: typer.Context) -> Dict[str, Any]:
    if ctx.obj is None:
        ctx.obj = {}
    return ctx.obj


def _get_client(ctx: typer.Context) -> VaultClient:
    obj = _ensure_ctx(ctx)
    client = obj.get("client")
    if client is not None:
        return client

    settings: VaultSettings = obj["settings"]
    client = VaultClient(addr=settings.addr, token=settings.token)
    obj["client"] = client
    return client


def _read_secrets(ctx: typer.Context) -> Dict[str, Any]:
    settings: VaultSettings = _ensure_ctx(ctx)["settings"]
    client = _get_client(ctx)
    try:
        return client.read_data(settings.path)
    except VaultClientError as exc:
        _die(str(exc))


def _write_secrets(ctx: typer.Context, data: Dict[str, Any]) -> None:
    settings: VaultSettings = _ensure_ctx(ctx)["settings"]
    client = _get_client(ctx)
    try:
        client.write_data(settings.path, data)
    except VaultClientError as exc:
        _die(str(exc))


@app.callback()
def main(
    ctx: typer.Context,
    addr: Optional[str] = typer.Option(None, "--addr", help="Vault server address"),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Vault token (or set VAULT_TOKEN)",
    ),
    path: Optional[str] = typer.Option(
        None,
        "--path",
        help="Secrets path (KV v2 data endpoint, e.g. secret/data/dev)",
    ),
) -> None:
    """Top-level callback that resolves configuration and stores it in context."""

    try:
        settings = load_vault_settings(
            addr_option=addr,
            token_option=token,
            path_option=path,
        )
    except ConfigError as exc:
        _die(str(exc))

    _ensure_ctx(ctx)["settings"] = settings


@app.command()
def list(ctx: typer.Context) -> None:  # noqa: A001 - command name parity
    """List all secrets under the configured path."""

    data = _read_secrets(ctx)
    if not data:
        typer.echo("No secrets found.")
        return

    typer.echo(f"\nFound {len(data)} secret(s):\n")
    render_secrets_table(data)


@app.command()
def get(ctx: typer.Context, key: str) -> None:
    """Get the value for a specific key."""

    data = _read_secrets(ctx)
    if key not in data:
        _die(f"Secret '{key}' not found")

    typer.echo(data[key])


@app.command()
def add(ctx: typer.Context, key: str, value: str) -> None:
    """Add a new secret (errors if the key already exists)."""

    data = _read_secrets(ctx)
    if key in data:
        _die(
            f"Secret '{key}' already exists. Use 'edit' or 'set' to update it.",
        )

    data[key] = value
    _write_secrets(ctx, data)
    typer.echo(f"Successfully added secret '{key}'")


@app.command()
def edit(
    ctx: typer.Context,
    key: str,
    value: Optional[str] = typer.Argument(
        None,
        show_default=False,
        help="Optional new value. If omitted, you will be prompted.",
    ),
) -> None:
    """Edit an existing secret, prompting if no value is provided."""

    data = _read_secrets(ctx)
    if key not in data:
        _die(f"Secret '{key}' not found. Use 'add' to create it.")

    current_value = data[key]
    if value is None:
        typer.echo(f"Current value: {current_value}")
        try:
            value = prompt_value("Enter new value")
        except InputNotInteractiveError as exc:
            _die(
                f"{exc} Provide the value as an argument: vault-cli edit {key} 'new-value'",
            )

    value = value.strip()
    if value == "":
        _die("No value provided. Aborting.")

    data[key] = coerce_value(value)
    _write_secrets(ctx, data)
    typer.echo(f"Successfully updated secret '{key}'")


@app.command()
def delete(
    ctx: typer.Context,
    key: str,
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt.",
    ),
) -> None:
    """Delete a secret, prompting for confirmation unless --force is set."""

    data = _read_secrets(ctx)
    if key not in data:
        _die(f"Secret '{key}' not found")

    if not force:
        try:
            confirmed = confirm(f"Are you sure you want to delete '{key}'?")
        except InputNotInteractiveError as exc:
            _die(f"{exc} Use --force to skip confirmation.")
        if not confirmed:
            typer.echo("Deletion cancelled.")
            return

    data.pop(key, None)
    _write_secrets(ctx, data)
    typer.echo(f"Successfully deleted secret '{key}'")


@app.command()
def set(
    ctx: typer.Context,
    key: str,
    value: str,
) -> None:
    """Add or overwrite a secret (preserving numeric/boolean types)."""

    data = _read_secrets(ctx)
    existed = key in data

    data[key] = coerce_value(value)
    _write_secrets(ctx, data)

    action = "updated" if existed else "added"
    typer.echo(f"Successfully {action} secret '{key}'")
