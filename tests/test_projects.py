"""Tests for project creation functionality."""

from __future__ import annotations

import pytest

from vault_core.projects import (
    ProjectCreationError,
    ProjectCreationResult,
    create_project,
)
from vault_core.vault import VaultClient, VaultClientError


class MockVaultClient:
    """Mock Vault client for testing."""

    def __init__(self, existing_paths: set[str] | None = None) -> None:
        self.existing_paths = existing_paths or set()
        self.write_calls: list[tuple[str, dict]] = []

    def read_data(self, path: str) -> dict:
        """Return empty dict if path doesn't exist, non-empty if it does."""
        if path in self.existing_paths:
            return {"some": "data"}
        return {}

    def write_data(self, path: str, data: dict) -> None:
        """Record write calls."""
        self.write_calls.append((path, data))


def test_create_project_with_default_environments():
    """Test creating a project with default environments."""
    client = MockVaultClient()
    result = create_project(client, "my-project")

    assert isinstance(result, ProjectCreationResult)
    assert result.project_name == "my-project"
    assert len(result.created_paths) == 3
    assert "secret/data/my-project/dev" in result.created_paths
    assert "secret/data/my-project/staging" in result.created_paths
    assert "secret/data/my-project/production" in result.created_paths
    assert len(result.skipped_paths) == 0
    assert len(client.write_calls) == 3


def test_create_project_with_custom_environments():
    """Test creating a project with custom environments."""
    client = MockVaultClient()
    result = create_project(client, "my-project", environments=["test", "prod"])

    assert result.project_name == "my-project"
    assert len(result.created_paths) == 2
    assert "secret/data/my-project/test" in result.created_paths
    assert "secret/data/my-project/prod" in result.created_paths
    assert len(result.skipped_paths) == 0


def test_create_project_skips_existing_paths():
    """Test that existing paths are skipped."""
    client = MockVaultClient(existing_paths={"secret/data/my-project/dev"})
    result = create_project(client, "my-project")

    assert len(result.created_paths) == 2
    assert "secret/data/my-project/dev" not in result.created_paths
    assert "secret/data/my-project/dev" in result.skipped_paths
    assert len(result.skipped_paths) == 1


def test_create_project_partially_existing():
    """Test project creation when some paths already exist."""
    client = MockVaultClient(existing_paths={"secret/data/my-project/staging"})
    result = create_project(client, "my-project", environments=["dev", "staging", "prod"])

    assert len(result.created_paths) == 2
    assert "secret/data/my-project/dev" in result.created_paths
    assert "secret/data/my-project/prod" in result.created_paths
    assert len(result.skipped_paths) == 1
    assert "secret/data/my-project/staging" in result.skipped_paths


def test_create_project_invalid_name_empty():
    """Test that empty project name is rejected."""
    client = MockVaultClient()
    with pytest.raises(ProjectCreationError, match="cannot be empty"):
        create_project(client, "")


def test_create_project_invalid_name_special_chars():
    """Test that project names with invalid characters are rejected."""
    client = MockVaultClient()
    with pytest.raises(ProjectCreationError, match="alphanumeric"):
        create_project(client, "my@project")


def test_create_project_invalid_name_too_long():
    """Test that project names exceeding 100 characters are rejected."""
    client = MockVaultClient()
    long_name = "a" * 101
    with pytest.raises(ProjectCreationError, match="exceed 100"):
        create_project(client, long_name)


def test_create_project_invalid_environment_name():
    """Test that invalid environment names are rejected."""
    client = MockVaultClient()
    with pytest.raises(ProjectCreationError, match="Invalid environment name"):
        create_project(client, "my-project", environments=["valid", "invalid@env"])


def test_create_project_empty_environments_list():
    """Test that empty environments list is rejected."""
    client = MockVaultClient()
    with pytest.raises(ProjectCreationError, match="At least one environment"):
        create_project(client, "my-project", environments=[])


def test_create_project_custom_base_path():
    """Test project creation with custom base path."""
    client = MockVaultClient()
    result = create_project(client, "my-project", base_path="custom/data")

    assert "custom/data/my-project/dev" in result.created_paths
    assert "custom/data/my-project/staging" in result.created_paths
    assert "custom/data/my-project/production" in result.created_paths


def test_create_project_validates_all_environments():
    """Test that all environment names are validated before creating any."""
    client = MockVaultClient()
    with pytest.raises(ProjectCreationError, match="Invalid environment name"):
        create_project(client, "my-project", environments=["valid", "invalid@env", "another"])

    # Verify no paths were created
    assert len(client.write_calls) == 0

