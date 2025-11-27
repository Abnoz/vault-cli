"""Tests for project creation API endpoint."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vault_api.app import app
from vault_core.config import APISettings
from vault_core.projects import ProjectCreationError, ProjectCreationResult
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
    # Get the actual module object from sys.modules
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


def test_create_project_endpoint_success(client: TestClient):
    """Test successful project creation via API."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=[
                "secret/data/test-project/dev",
                "secret/data/test-project/staging",
                "secret/data/test-project/production",
            ],
            skipped_paths=[],
        )

        response = client.post(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["project_name"] == "test-project"
    assert len(data["created_paths"]) == 3
    assert len(data["skipped_paths"]) == 0
    assert "created successfully" in data["message"].lower()


def test_create_project_endpoint_with_custom_environments(client: TestClient):
    """Test project creation with custom environments via query param."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=["secret/data/test-project/test"],
            skipped_paths=[],
        )

        response = client.post(
            "/api/v1/projects/test-project?environments=test",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["created_paths"]) == 1


def test_create_project_endpoint_with_request_body(client: TestClient):
    """Test project creation with environments in request body."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=["secret/data/test-project/custom"],
            skipped_paths=[],
        )

        response = client.post(
            "/api/v1/projects/test-project",
            json={"environments": ["custom"]},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["created_paths"]) == 1


def test_create_project_endpoint_query_param_overrides_body(client: TestClient):
    """Test that query param environments override request body."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=["secret/data/test-project/query"],
            skipped_paths=[],
        )

        response = client.post(
            "/api/v1/projects/test-project?environments=query",
            json={"environments": ["body"]},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        # Verify query param was used (environments list should contain "query")
        call_args = mock_create.call_args
        assert call_args is not None
        assert call_args[1]["environments"] == ["query"]


def test_create_project_endpoint_missing_api_key(client: TestClient):
    """Test that missing API key returns 422 (FastAPI validation error)."""
    response = client.post("/api/v1/projects/test-project")

    assert response.status_code == 422  # FastAPI validation error for missing required header


def test_create_project_endpoint_invalid_api_key(client: TestClient):
    """Test that invalid API key returns 401."""
    response = client.post(
        "/api/v1/projects/test-project",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_create_project_endpoint_invalid_project_name(client: TestClient):
    """Test that invalid project name returns 400."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.side_effect = ProjectCreationError("Invalid project name")

        response = client.post(
            "/api/v1/projects/invalid@project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


def test_create_project_endpoint_vault_error(client: TestClient):
    """Test that Vault errors return 502."""
    from vault_core.vault import VaultClientError

    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.side_effect = VaultClientError("Vault connection failed")

        response = client.post(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 502
        assert "vault" in response.json()["detail"].lower()


def test_create_project_endpoint_partial_creation(client: TestClient):
    """Test response when some paths already exist."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=["secret/data/test-project/dev"],
            skipped_paths=["secret/data/test-project/staging"],
        )

        response = client.post(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["created_paths"]) == 1
        assert len(data["skipped_paths"]) == 1
        assert "partially created" in data["message"].lower()


def test_create_project_endpoint_all_existing(client: TestClient):
    """Test response when all paths already exist."""
    app_module = sys.modules["vault_api.app"]

    with patch.object(app_module, "create_project") as mock_create:
        mock_create.return_value = ProjectCreationResult(
            project_name="test-project",
            created_paths=[],
            skipped_paths=["secret/data/test-project/dev"],
        )

        response = client.post(
            "/api/v1/projects/test-project",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["created_paths"]) == 0
        assert len(data["skipped_paths"]) == 1
        assert "already exists" in data["message"].lower()

