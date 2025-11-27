"""Integration tests for project CRUD operations."""

from __future__ import annotations

import pytest

from vault_core.projects import (
    ProjectOperationError,
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from vault_core.vault import VaultClient


@pytest.fixture
def test_project_name() -> str:
    """Generate a unique test project name."""
    import time

    return f"test-project-{int(time.time())}"


def test_create_and_list_projects(vault_client: VaultClient, test_project_name: str):
    """Test creating a project and listing projects."""
    # Create project
    result = create_project(vault_client, test_project_name, environments=["test"])
    assert result.project_name == test_project_name
    assert len(result.created_paths) == 1

    # List projects
    projects = list_projects(vault_client)
    assert test_project_name in projects

    # Cleanup
    delete_project(vault_client, test_project_name)


def test_get_project(vault_client: VaultClient, test_project_name: str):
    """Test getting project information."""
    # Create project
    create_project(vault_client, test_project_name, environments=["dev", "staging"])

    # Get project info
    project_info = get_project(vault_client, test_project_name)
    assert project_info.project_name == test_project_name
    assert len(project_info.environments) == 2
    assert "dev" in project_info.environments
    assert "staging" in project_info.environments

    # Cleanup
    delete_project(vault_client, test_project_name)


def test_update_project(vault_client: VaultClient, test_project_name: str):
    """Test updating a project."""
    # Create project
    create_project(vault_client, test_project_name, environments=["dev"])

    # Add environment
    result = update_project(
        vault_client,
        test_project_name,
        add_environments=["staging"],
    )
    assert "staging" in result.added_environments
    assert len(result.created_paths) == 1

    # Verify it was added
    project_info = get_project(vault_client, test_project_name)
    assert "staging" in project_info.environments

    # Remove environment
    result = update_project(
        vault_client,
        test_project_name,
        remove_environments=["dev"],
    )
    assert "dev" in result.removed_environments

    # Verify it was removed
    project_info = get_project(vault_client, test_project_name)
    assert "dev" not in project_info.environments
    assert "staging" in project_info.environments

    # Cleanup
    delete_project(vault_client, test_project_name)


def test_delete_project(vault_client: VaultClient, test_project_name: str):
    """Test deleting a project."""
    # Create project
    create_project(vault_client, test_project_name, environments=["dev", "staging"])

    # Delete project
    deleted_paths = delete_project(vault_client, test_project_name)
    assert len(deleted_paths) == 2

    # Verify it's gone
    projects = list_projects(vault_client)
    assert test_project_name not in projects

    # Verify get_project fails
    with pytest.raises(ProjectOperationError, match="not found"):
        get_project(vault_client, test_project_name)


def test_project_not_found(vault_client: VaultClient):
    """Test operations on non-existent project."""
    with pytest.raises(ProjectOperationError, match="not found"):
        get_project(vault_client, "non-existent-project-12345")

    with pytest.raises(ProjectOperationError, match="not found"):
        update_project(vault_client, "non-existent-project-12345", add_environments=["test"])

    with pytest.raises(ProjectOperationError, match="not found"):
        delete_project(vault_client, "non-existent-project-12345")

