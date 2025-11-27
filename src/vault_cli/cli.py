"""Typer-powered command implementation for the Python Vault CLI."""

from __future__ import annotations

from typing import Any, Dict, Optional

import typer

from vault_core.config import ConfigError, VaultSettings, load_vault_settings
from vault_core.projects import (
    ProjectCreationError,
    ProjectOperationError,
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
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


@app.command(name="create-project")
def create_project_cmd(
    ctx: typer.Context,
    project_name: str,
    environments: Optional[str] = typer.Option(
        None,
        "--environments",
        "-e",
        help="Comma-separated list of environments (defaults to dev,staging,production)",
    ),
) -> None:
    """Create a new project with default or custom environments.

    Creates KV v2 paths for each environment: secret/data/{project}/{env}
    """
    settings: VaultSettings = _ensure_ctx(ctx)["settings"]
    client = _get_client(ctx)

    # Parse environments
    env_list: list[str] | None = None
    if environments:
        env_list = [e.strip() for e in environments.split(",") if e.strip()]

    try:
        result = create_project(
            client=client,
            project_name=project_name,
            environments=env_list,
        )
    except ProjectCreationError as exc:
        _die(str(exc))
    except VaultClientError as exc:
        _die(f"Vault operation failed: {exc}")

    # Report results
    if result.skipped_paths and result.created_paths:
        typer.echo(
            f"Project '{project_name}' partially created:\n"
            f"  ✓ Created {len(result.created_paths)} path(s): {', '.join(result.created_paths)}\n"
            f"  ⊘ Skipped {len(result.skipped_paths)} existing path(s): {', '.join(result.skipped_paths)}",
        )
    elif result.skipped_paths:
        typer.echo(
            f"Project '{project_name}' already exists with all specified environments:\n"
            f"  ⊘ {', '.join(result.skipped_paths)}",
        )
    else:
        typer.echo(
            f"✓ Successfully created project '{project_name}' with {len(result.created_paths)} environment(s):\n"
            f"  {', '.join(result.created_paths)}",
        )


@app.command(name="list-projects")
def list_projects_cmd(ctx: typer.Context) -> None:
    """List all projects."""
    client = _get_client(ctx)

    try:
        projects = list_projects(client=client)
    except ProjectOperationError as exc:
        _die(str(exc))
    except VaultClientError as exc:
        _die(f"Vault operation failed: {exc}")

    if not projects:
        typer.echo("No projects found.")
        return

    typer.echo(f"\nFound {len(projects)} project(s):\n")
    for project in projects:
        typer.echo(f"  • {project}")


@app.command(name="get-project")
def get_project_cmd(
    ctx: typer.Context,
    project_name: str,
) -> None:
    """Get information about a specific project."""
    client = _get_client(ctx)

    try:
        project_info = get_project(client=client, project_name=project_name)
    except ProjectOperationError as exc:
        _die(str(exc))
    except VaultClientError as exc:
        _die(f"Vault operation failed: {exc}")

    typer.echo(f"\nProject: {project_info.project_name}")
    typer.echo(f"Environments ({len(project_info.environments)}):")
    for env in project_info.environments:
        typer.echo(f"  • {env}")
    typer.echo(f"\nPaths:")
    for path in project_info.paths:
        typer.echo(f"  • {path}")


@app.command(name="update-project")
def update_project_cmd(
    ctx: typer.Context,
    project_name: str,
    add_environments: Optional[str] = typer.Option(
        None,
        "--add-env",
        help="Comma-separated list of environments to add",
    ),
    remove_environments: Optional[str] = typer.Option(
        None,
        "--remove-env",
        help="Comma-separated list of environments to remove",
    ),
) -> None:
    """Update a project by adding or removing environments."""
    client = _get_client(ctx)

    # Parse environments
    add_env_list: list[str] | None = None
    if add_environments:
        add_env_list = [e.strip() for e in add_environments.split(",") if e.strip()]

    remove_env_list: list[str] | None = None
    if remove_environments:
        remove_env_list = [e.strip() for e in remove_environments.split(",") if e.strip()]

    if not add_env_list and not remove_env_list:
        _die("At least one of --add-env or --remove-env must be specified")

    try:
        result = update_project(
            client=client,
            project_name=project_name,
            add_environments=add_env_list,
            remove_environments=remove_env_list,
        )
    except ProjectOperationError as exc:
        _die(str(exc))
    except VaultClientError as exc:
        _die(f"Vault operation failed: {exc}")

    typer.echo(f"✓ Successfully updated project '{project_name}'")
    if result.added_environments:
        typer.echo(f"  Added environments: {', '.join(result.added_environments)}")
    if result.removed_environments:
        typer.echo(f"  Removed environments: {', '.join(result.removed_environments)}")


@app.command(name="delete-project")
def delete_project_cmd(
    ctx: typer.Context,
    project_name: str,
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Delete a project and all its environments.

    This operation is irreversible. All secrets in all environments will be deleted.
    """
    client = _get_client(ctx)

    # Get project info first to show what will be deleted
    try:
        project_info = get_project(client=client, project_name=project_name)
    except ProjectOperationError as exc:
        _die(str(exc))
    except VaultClientError as exc:
        _die(f"Vault operation failed: {exc}")

    # Confirm deletion
    if not force:
        typer.echo(f"\nWarning: This will delete project '{project_name}' and all its environments:")
        for env in project_info.environments:
            typer.echo(f"  • {env}")
        if not confirm("Are you sure you want to delete this project?"):
            typer.echo("Deletion cancelled.")
            raise typer.Exit(0)

    try:
        deleted_paths = delete_project(client=client, project_name=project_name)
    except ProjectOperationError as exc:
        _die(str(exc))
    except VaultClientError as exc:
        _die(f"Vault operation failed: {exc}")

    typer.echo(f"✓ Successfully deleted project '{project_name}'")
    typer.echo(f"  Deleted {len(deleted_paths)} path(s)")
