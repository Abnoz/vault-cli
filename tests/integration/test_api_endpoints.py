"""Integration tests for API endpoints."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vault_api.app import app
from vault_core.config import APISettings
from vault_core.vault import VaultClient


@pytest.fixture
def api_settings() -> APISettings:
    """Fixture providing API settings for tests."""
    return APISettings(api_key="test-api-key", port=8000, cors_origins=["*"])


@pytest.fixture
def mock_vault_client() -> MagicMock:
    """Fixture providing a mock Vault client."""
    return MagicMock(spec=VaultClient)


@pytest.fixture
def client(api_settings: APISettings, mock_vault_client: MagicMock) -> TestClient:
    """Fixture providing a test client with mocked dependencies."""
    app_module = sys.modules["vault_api.app"]
    from vault_api.rate_limit import limiter

    # Set module-level variables and patch dependency functions
    original_api_settings = getattr(app_module, "_api_settings", None)
    original_vault_client = getattr(app_module, "_vault_client", None)
    original_get_api_settings = app_module.get_api_settings
    original_get_vault_client = app_module.get_vault_client

    app_module._api_settings = api_settings
    app_module._vault_client = mock_vault_client

    def mock_get_api_settings():
        return api_settings

    def mock_get_vault_client():
        return mock_vault_client

    app_module.get_api_settings = mock_get_api_settings
    app_module.get_vault_client = mock_get_vault_client

    # Ensure limiter is set on app state for rate limiting to work
    app_module.app.state.limiter = limiter

    try:
        yield TestClient(app_module.app)
    finally:
        # Restore original values
        app_module._api_settings = original_api_settings
        app_module._vault_client = original_vault_client
        app_module.get_api_settings = original_get_api_settings
        app_module.get_vault_client = original_get_vault_client


def test_list_projects_endpoint(client: TestClient):
    """Test listing projects via API."""
    from vault_core.projects import list_projects
    import sys

    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "list_projects") as mock_list:
        mock_list.return_value = ["project1", "project2"]

        response = client.get(
            "/api/v1/projects",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert len(data["projects"]) == 2


def test_get_project_endpoint(client: TestClient):
    """Test getting project info via API."""
    from vault_core.projects import ProjectInfo
    import sys

    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "get_project") as mock_get:
        mock_get.return_value = ProjectInfo(
            project_name="test-project",
            environments=["dev", "staging"],
            paths=["secret/data/test-project/dev", "secret/data/test-project/staging"],
        )

        response = client.get(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "test-project"
        assert len(data["environments"]) == 2


def test_create_project_endpoint(client: TestClient):
    """Test creating project via API."""
    from vault_core.projects import ProjectCreationResult
    import sys

    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=["secret/data/test-project/dev"],
            skipped_paths=[],
        )

        response = client.post(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_name"] == "test-project"


def test_update_project_endpoint(client: TestClient):
    """Test updating project via API."""
    from vault_core.projects import ProjectUpdateResult
    import sys
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "update_project") as mock_update:
        mock_update.return_value = ProjectUpdateResult(
            project_name="test-project",
            added_environments=["staging"],
            removed_environments=[],
            created_paths=["secret/data/test-project/staging"],
            deleted_paths=[],
        )

        response = client.put(
            "/api/v1/projects/test-project",
            json={"add_environments": ["staging"]},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "test-project"
        assert len(data["added_environments"]) == 1
        assert "staging" in data["added_environments"]


def test_delete_project_endpoint(client: TestClient):
    """Test deleting project via API."""
    import sys

    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "delete_project") as mock_delete:
        mock_delete.return_value = ["secret/data/test-project/dev"]

        response = client.delete(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "test-project"
        assert len(data["deleted_paths"]) == 1

