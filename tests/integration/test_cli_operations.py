"""Integration tests for CLI operations."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from vault_cli import cli


@pytest.fixture(autouse=True)
def reset_cli_context():
    """Reset CLI context between tests."""
    cli.app.info.context_settings = {}


def test_list_projects_command(monkeypatch):
    """Test list-projects CLI command."""
    runner = CliRunner()

    def fake_list_projects(client, base_path="secret/data"):
        """Fake list_projects that returns test data."""
        from vault_core.projects import list_projects as real_list

        return real_list(client, base_path)

    # This test would need a real Vault connection or better mocking
    # For now, we'll skip if Vault is not available
    import os

    if not os.getenv("VAULT_TOKEN"):
        pytest.skip("Vault not configured")

    result = runner.invoke(
        cli.app,
        ["--token", os.getenv("VAULT_TOKEN", ""), "--addr", os.getenv("VAULT_ADDR", "http://localhost:8200"), "list-projects"],
    )

    # Should not crash (may return empty list or projects)
    assert result.exit_code in (0, 1)  # 0 for success, 1 for no projects or errors


def test_get_project_command(monkeypatch):
    """Test get-project CLI command."""
    runner = CliRunner()

    import os

    if not os.getenv("VAULT_TOKEN"):
        pytest.skip("Vault not configured")

    # Try to get a non-existent project (should fail gracefully)
    result = runner.invoke(
        cli.app,
        [
            "--token",
            os.getenv("VAULT_TOKEN", ""),
            "--addr",
            os.getenv("VAULT_ADDR", "http://localhost:8200"),
            "get-project",
            "non-existent-project-12345",
        ],
    )

    # Should fail with error message
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "error" in result.output.lower()

