"""FastAPI application for Vault secrets management API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
import time

from vault_core.config import APISettings, ConfigError, VaultSettings, load_api_settings, load_vault_settings
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

from .decorators import read_rate_limit, write_rate_limit
from .dependencies import verify_api_key
from .errors import create_error_response
from .helpers import (
    build_project_creation_message,
    build_project_deletion_message,
    build_project_update_message,
    handle_project_operation_error,
    parse_environments_from_request,
)
from .logging_config import get_logger, log_error, log_request
from .models import (
    ProjectCreationRequest,
    ProjectCreationResponse,
    ProjectDeleteResponse,
    ProjectInfoResponse,
    ProjectListResponse,
    ProjectUpdateRequest,
    ProjectUpdateResponse,
)
from .rate_limit import DEFAULT_READ_LIMIT, DEFAULT_WRITE_LIMIT, get_rate_limit_key, limiter


logger = get_logger()

# Global state for API settings and Vault client
_api_settings: APISettings | None = None
_vault_client: VaultClient | None = None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        log_request(request.method, str(request.url.path), response.status_code, duration_ms)
        return response


# Load settings early to configure CORS
try:
    _api_settings = load_api_settings(api_key_option=None, port_option=None)
    cors_origins = list(_api_settings.cors_origins)
except ConfigError:
    # Fallback if settings can't be loaded
    _api_settings = None
    cors_origins = ["*"]
    logger.warning("Failed to load API settings, using default CORS origins")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI app initialization."""
    global _api_settings, _vault_client

    # Settings already loaded above for CORS configuration
    if _api_settings is None:
        try:
            _api_settings = load_api_settings(api_key_option=None, port_option=None)
        except ConfigError as exc:
            log_error("initialization", exc)
            logger.warning("Failed to load API settings: %s", exc)

    try:
        vault_settings = load_vault_settings(
            addr_option=None,
            token_option=None,
            path_option=None,
        )
        _vault_client = VaultClient(addr=vault_settings.addr, token=vault_settings.token)
        logger.info("Vault client initialized successfully")
    except (ConfigError, VaultClientError) as exc:
        # Log error but allow app to start (will fail on first request)
        log_error("initialization", exc)
        logger.warning("Failed to initialize Vault client: %s", exc)

    yield

    _vault_client = None
    _api_settings = None


app = FastAPI(
    title="Vault Secrets API",
    description="API for managing Vault secrets with project organization",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS using loaded settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS configured with origins: %s", cors_origins)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)


def get_api_settings() -> APISettings:
    """Dependency to get API settings."""
    if _api_settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API not properly configured",
        )
    return _api_settings


def get_vault_client() -> VaultClient:
    """Dependency to get Vault client."""
    if _vault_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vault client not available",
        )
    return _vault_client


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Vault Secrets API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "list_projects": "GET /api/v1/projects",
            "get_project": "GET /api/v1/projects/{project_name}",
            "create_project": "POST /api/v1/projects/{project_name}",
            "update_project": "PUT /api/v1/projects/{project_name}",
            "delete_project": "DELETE /api/v1/projects/{project_name}",
        },
    }


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Returns the health status of the API service.",
    response_description="Service health status",
)
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with service status
    """
    return {"status": "healthy"}


@app.post(
    "/api/v1/projects/{project_name}",
    response_model=ProjectCreationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
    summary="Create a new project",
    description="Create a new project with default (dev, staging, production) or custom environments. "
    "Each environment is created as a KV v2 path in Vault.",
    response_description="Project creation result with created and skipped paths",
    responses={
        201: {"description": "Project created successfully"},
        400: {"description": "Invalid project name or environments"},
        401: {"description": "Invalid or missing API key"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Vault operation failed"},
    },
)
@limiter.limit(DEFAULT_WRITE_LIMIT, key_func=get_rate_limit_key)
async def create_project_endpoint(
    request: Request,
    project_name: str,
    request_body: ProjectCreationRequest | None = None,
    environments: str | None = Query(
        None,
        description="Comma-separated list of environments (overrides request body). Example: dev,staging,production",
        examples=["dev,staging,production"],
    ),
    api_settings: APISettings = Depends(get_api_settings),
    x_api_key: str = Header(..., alias="X-API-Key", description="API key for authentication"),
    vault_client: VaultClient = Depends(get_vault_client),
) -> ProjectCreationResponse:
    """Create a new project with default or custom environments.

    Args:
        request: FastAPI request object (for rate limiting)
        project_name: Name of the project to create (alphanumeric, hyphens, underscores only)
        request_body: Optional request body with environments list
        environments: Optional query parameter with comma-separated environments (overrides request body)
        api_settings: API settings (from dependency)
        x_api_key: API key from header (will be validated)
        vault_client: Vault client instance (from dependency)

    Returns:
        ProjectCreationResponse with created paths and status

    Raises:
        HTTPException: If project creation fails or API key is invalid
    """
    verify_api_key(x_api_key, api_settings)

    env_list = parse_environments_from_request(
        query_param=environments,
        request_body_environments=request_body.environments if request_body else None,
    )

    try:
        logger.info("Creating project: %s with environments: %s", project_name, env_list)
        result = create_project(
            client=vault_client,
            project_name=project_name,
            environments=env_list,
        )
        logger.info(
            "Project created: %s - Created: %d, Skipped: %d",
            project_name,
            len(result.created_paths),
            len(result.skipped_paths),
        )
    except (ProjectCreationError, VaultClientError) as exc:
        raise handle_project_operation_error("create_project", exc, project_name=project_name) from exc

    message = build_project_creation_message(
        project_name=result.project_name,
        created_count=len(result.created_paths),
        skipped_count=len(result.skipped_paths),
    )

    return ProjectCreationResponse(
        project_name=result.project_name,
        created_paths=result.created_paths,
        skipped_paths=result.skipped_paths,
        message=message,
    )


@app.get(
    "/api/v1/projects",
    response_model=ProjectListResponse,
    tags=["projects"],
    summary="List all projects",
    description="Retrieve a list of all projects under the configured base path.",
    response_description="List of project names",
    responses={
        200: {"description": "List of projects retrieved successfully"},
        401: {"description": "Invalid or missing API key"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Vault operation failed"},
    },
)
@limiter.limit(DEFAULT_READ_LIMIT, key_func=get_rate_limit_key)
async def list_projects_endpoint(
    request: Request,
    api_settings: APISettings = Depends(get_api_settings),
    x_api_key: str = Header(..., alias="X-API-Key", description="API key for authentication"),
    vault_client: VaultClient = Depends(get_vault_client),
) -> ProjectListResponse:
    """List all projects.

    Returns a list of all project names under the configured base path.

    Args:
        request: FastAPI request object (for rate limiting)
        api_settings: API settings (from dependency)
        x_api_key: API key from header (will be validated)
        vault_client: Vault client instance (from dependency)

    Returns:
        ProjectListResponse with list of project names

    Raises:
        HTTPException: If listing fails or API key is invalid
    """
    verify_api_key(x_api_key, api_settings)

    try:
        logger.info("Listing all projects")
        projects = list_projects(client=vault_client)
        logger.info("Found %d projects", len(projects))
        return ProjectListResponse(projects=projects, count=len(projects))
    except (ProjectOperationError, VaultClientError) as exc:
        raise handle_project_operation_error("list_projects", exc) from exc


@app.get(
    "/api/v1/projects/{project_name}",
    response_model=ProjectInfoResponse,
    tags=["projects"],
    summary="Get project information",
    description="Retrieve detailed information about a specific project, including all environments and their paths.",
    response_description="Project information with environments and paths",
    responses={
        200: {"description": "Project information retrieved successfully"},
        401: {"description": "Invalid or missing API key"},
        404: {"description": "Project not found"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Vault operation failed"},
    },
)
@limiter.limit(DEFAULT_READ_LIMIT, key_func=get_rate_limit_key)
async def get_project_endpoint(
    request: Request,
    project_name: str,
    api_settings: APISettings = Depends(get_api_settings),
    x_api_key: str = Header(..., alias="X-API-Key", description="API key for authentication"),
    vault_client: VaultClient = Depends(get_vault_client),
) -> ProjectInfoResponse:
    """Get information about a specific project.

    Returns project details including all environments and their paths.

    Args:
        request: FastAPI request object (for rate limiting)
        project_name: Name of the project to retrieve
        api_settings: API settings (from dependency)
        x_api_key: API key from header (will be validated)
        vault_client: Vault client instance (from dependency)

    Returns:
        ProjectInfoResponse with project details

    Raises:
        HTTPException: If project not found, operation fails, or API key is invalid
    """
    verify_api_key(x_api_key, api_settings)

    try:
        logger.info("Getting project: %s", project_name)
        project_info = get_project(client=vault_client, project_name=project_name)
        logger.info("Project found: %s with %d environments", project_name, len(project_info.environments))
        return ProjectInfoResponse(
            project_name=project_info.project_name,
            environments=project_info.environments,
            paths=project_info.paths,
        )
    except (ProjectOperationError, VaultClientError) as exc:
        raise handle_project_operation_error(
            "get_project",
            exc,
            project_name=project_name,
            not_found_status=status.HTTP_404_NOT_FOUND,
        ) from exc


@app.put(
    "/api/v1/projects/{project_name}",
    response_model=ProjectUpdateResponse,
    tags=["projects"],
    summary="Update a project",
    description="Add or remove environments from an existing project. "
    "You can add new environments, remove existing ones, or both in a single request.",
    response_description="Project update result with added/removed environments",
    responses={
        200: {"description": "Project updated successfully"},
        400: {"description": "Invalid request or environment names"},
        401: {"description": "Invalid or missing API key"},
        404: {"description": "Project not found"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Vault operation failed"},
    },
)
async def update_project_endpoint(
    request: Request,
    project_name: str,
    body: ProjectUpdateRequest = Body(...),
    api_settings: APISettings = Depends(get_api_settings),
    x_api_key: str = Header(..., alias="X-API-Key", description="API key for authentication"),
    vault_client: VaultClient = Depends(get_vault_client),
) -> ProjectUpdateResponse:
    """Update a project by adding or removing environments.

    Args:
        request: FastAPI request object (for rate limiting)
        project_name: Name of the project to update
        body: Update request with environments to add/remove
        api_settings: API settings (from dependency)
        x_api_key: API key from header (will be validated)
        vault_client: Vault client instance (from dependency)

    Returns:
        ProjectUpdateResponse with update details

    Raises:
        HTTPException: If project not found, update fails, or API key is invalid
    """
    verify_api_key(x_api_key, api_settings)

    try:
        logger.info(
            "Updating project: %s - Add: %s, Remove: %s",
            project_name,
            body.add_environments,
            body.remove_environments,
        )
        result = update_project(
            client=vault_client,
            project_name=project_name,
            add_environments=body.add_environments,
            remove_environments=body.remove_environments,
        )
        logger.info(
            "Project updated: %s - Added: %d, Removed: %d",
            project_name,
            len(result.added_environments),
            len(result.removed_environments),
        )
    except (ProjectOperationError, VaultClientError) as exc:
        raise handle_project_operation_error("update_project", exc, project_name=project_name) from exc

    message = build_project_update_message(
        project_name=result.project_name,
        added_count=len(result.added_environments),
        removed_count=len(result.removed_environments),
    )

    return ProjectUpdateResponse(
        project_name=result.project_name,
        added_environments=result.added_environments,
        removed_environments=result.removed_environments,
        created_paths=result.created_paths,
        deleted_paths=result.deleted_paths,
        message=message,
    )


# Apply rate limiting to the update endpoint (after function definition to avoid type issues)
update_project_endpoint = write_rate_limit(update_project_endpoint)


@app.delete(
    "/api/v1/projects/{project_name}",
    response_model=ProjectDeleteResponse,
    tags=["projects"],
    summary="Delete a project",
    description="Delete a project and all its environments. "
    "**WARNING**: This operation is irreversible. All secrets in all environments will be permanently deleted.",
    response_description="Project deletion result with deleted paths",
    responses={
        200: {"description": "Project deleted successfully"},
        401: {"description": "Invalid or missing API key"},
        404: {"description": "Project not found"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Vault operation failed"},
    },
)
@limiter.limit(DEFAULT_WRITE_LIMIT, key_func=get_rate_limit_key)
async def delete_project_endpoint(
    request: Request,
    project_name: str,
    api_settings: APISettings = Depends(get_api_settings),
    x_api_key: str = Header(..., alias="X-API-Key", description="API key for authentication"),
    vault_client: VaultClient = Depends(get_vault_client),
) -> ProjectDeleteResponse:
    """Delete a project and all its environments.

    This operation is irreversible. All secrets in all environments will be deleted.

    Args:
        request: FastAPI request object (for rate limiting)
        project_name: Name of the project to delete
        api_settings: API settings (from dependency)
        x_api_key: API key from header (will be validated)
        vault_client: Vault client instance (from dependency)

    Returns:
        ProjectDeleteResponse with deletion details

    Raises:
        HTTPException: If project not found, deletion fails, or API key is invalid
    """
    verify_api_key(x_api_key, api_settings)

    try:
        logger.warning("Deleting project: %s", project_name)
        deleted_paths = delete_project(client=vault_client, project_name=project_name)
        logger.warning("Project deleted: %s - Deleted %d paths", project_name, len(deleted_paths))
    except (ProjectOperationError, VaultClientError) as exc:
        raise handle_project_operation_error(
            "delete_project",
            exc,
            project_name=project_name,
            not_found_status=status.HTTP_404_NOT_FOUND,
        ) from exc

    message = build_project_deletion_message(
        project_name=project_name,
        deleted_paths_count=len(deleted_paths),
    )

    return ProjectDeleteResponse(
        project_name=project_name,
        deleted_paths=deleted_paths,
        message=message,
    )

