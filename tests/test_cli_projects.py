"""Tests for project creation CLI command."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from typer.testing import CliRunner

from vault_cli import cli
from vault_core.projects import ProjectCreationError, ProjectCreationResult


class StubVaultClient:
    """Stub Vault client for CLI tests."""

    def __init__(self, initial: Dict[str, Any] | None = None) -> None:
        self.data = dict(initial or {})
        self.existing_paths: set[str] = set()

    def read_data(self, path: str) -> Dict[str, Any]:  # noqa: ARG002
        """Return empty dict if path doesn't exist."""
        if path in self.existing_paths:
            return {"exists": True}
        return {}

    def write_data(self, path: str, data: Dict[str, Any]) -> None:  # noqa: ARG002
        """Record write operations."""
        self.existing_paths.add(path)


@pytest.fixture(autouse=True)
def reset_cli_context():
    """Reset CLI context between tests."""
    cli.app.info.context_settings = {}


def test_create_project_command_default_environments(monkeypatch):
    """Test create-project command with default environments."""
    runner = CliRunner()
    stub = StubVaultClient()

    def fake_create_project(client, project_name, environments=None, base_path="secret/data"):
        """Fake create_project that uses stub client."""
        from vault_core.projects import create_project as real_create

        return real_create(client, project_name, environments, base_path)

    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)
    monkeypatch.setattr(cli, "create_project", fake_create_project)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "create-project", "my-project"],
    )

    assert result.exit_code == 0
    assert "Successfully created project 'my-project'" in result.output
    assert "dev" in result.output
    assert "staging" in result.output
    assert "production" in result.output


def test_create_project_command_custom_environments(monkeypatch):
    """Test create-project command with custom environments."""
    runner = CliRunner()
    stub = StubVaultClient()

    def fake_create_project(client, project_name, environments=None, base_path="secret/data"):
        """Fake create_project that uses stub client."""
        from vault_core.projects import create_project as real_create

        return real_create(client, project_name, environments, base_path)

    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)
    monkeypatch.setattr(cli, "create_project", fake_create_project)

    result = runner.invoke(
        cli.app,
        [
            "--token",
            "t",
            "--addr",
            "http://vault:8200",
            "create-project",
            "my-project",
            "--environments",
            "test,prod",
        ],
    )

    assert result.exit_code == 0
    assert "Successfully created project 'my-project'" in result.output
    assert "test" in result.output
    assert "prod" in result.output
    assert "dev" not in result.output


def test_create_project_command_partial_creation(monkeypatch):
    """Test create-project when some paths already exist."""
    runner = CliRunner()
    stub = StubVaultClient()
    stub.existing_paths.add("secret/data/my-project/staging")

    def fake_create_project(client, project_name, environments=None, base_path="secret/data"):
        """Fake create_project that uses stub client."""
        from vault_core.projects import create_project as real_create

        return real_create(client, project_name, environments, base_path)

    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)
    monkeypatch.setattr(cli, "create_project", fake_create_project)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "create-project", "my-project"],
    )

    assert result.exit_code == 0
    assert "partially created" in result.output
    assert "Created" in result.output
    assert "Skipped" in result.output


def test_create_project_command_all_existing(monkeypatch):
    """Test create-project when all paths already exist."""
    runner = CliRunner()
    stub = StubVaultClient()
    stub.existing_paths.add("secret/data/my-project/dev")
    stub.existing_paths.add("secret/data/my-project/staging")
    stub.existing_paths.add("secret/data/my-project/production")

    def fake_create_project(client, project_name, environments=None, base_path="secret/data"):
        """Fake create_project that uses stub client."""
        from vault_core.projects import create_project as real_create

        return real_create(client, project_name, environments, base_path)

    monkeypatch.setattr(cli, "VaultClient", lambda **_: stub)
    monkeypatch.setattr(cli, "create_project", fake_create_project)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "create-project", "my-project"],
    )

    assert result.exit_code == 0
    assert "already exists" in result.output


def test_create_project_command_invalid_name(monkeypatch):
    """Test create-project with invalid project name."""
    runner = CliRunner()

    def fake_create_project(*args, **kwargs):
        """Fake that raises ProjectCreationError."""
        raise ProjectCreationError("Invalid project name")

    monkeypatch.setattr(cli, "create_project", fake_create_project)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "create-project", "invalid@project"],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Invalid project name" in result.output


def test_create_project_command_vault_error(monkeypatch):
    """Test create-project when Vault operation fails."""
    runner = CliRunner()
    from vault_core.vault import VaultClientError

    def fake_create_project(*args, **kwargs):
        """Fake that raises VaultClientError."""
        raise VaultClientError("Vault connection failed")

    monkeypatch.setattr(cli, "create_project", fake_create_project)

    result = runner.invoke(
        cli.app,
        ["--token", "t", "--addr", "http://vault:8200", "create-project", "my-project"],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Vault operation failed" in result.output


def test_create_project_command_missing_token():
    """Test create-project fails without token."""
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["--addr", "http://vault:8200", "create-project", "my-project"],
    )

    assert result.exit_code == 1
    assert "token" in result.output.lower()

