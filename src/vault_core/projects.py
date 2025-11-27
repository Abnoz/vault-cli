"""Project creation utilities for organizing Vault secrets by project and environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .constants import DEFAULT_ENVIRONMENTS, DEFAULT_VAULT_BASE_PATH
from .sanitization import SanitizationError, sanitize_environment_name, sanitize_project_name
from .vault import VaultClient, VaultClientError


class ProjectCreationError(RuntimeError):
    """Raised when project creation fails."""


class ProjectOperationError(RuntimeError):
    """Raised when project operations fail."""


@dataclass(frozen=True, slots=True)
class ProjectCreationResult:
    """Result of project creation operation."""

    project_name: str
    created_paths: List[str]
    skipped_paths: List[str]


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    """Information about a project."""

    project_name: str
    environments: List[str]
    paths: List[str]


@dataclass(frozen=True, slots=True)
class ProjectUpdateResult:
    """Result of project update operation."""

    project_name: str
    added_environments: List[str]
    removed_environments: List[str]
    created_paths: List[str]
    deleted_paths: List[str]


def create_project(
    client: VaultClient,
    project_name: str,
    environments: List[str] | None = None,
    base_path: str = DEFAULT_VAULT_BASE_PATH,
) -> ProjectCreationResult:
    """Create a project with default or custom environments.

    Args:
        client: Vault client instance
        project_name: Name of the project to create
        environments: List of environment names (defaults to dev, staging, production)
        base_path: Base KV v2 path (defaults to "secret/data")

    Returns:
        ProjectCreationResult with created and skipped paths

    Raises:
        ProjectCreationError: If project name is invalid or creation fails
        VaultClientError: If Vault operations fail
    """
    # Sanitize project name (converts SanitizationError to ProjectCreationError)
    try:
        sanitized_project_name = sanitize_project_name(project_name)
    except SanitizationError as exc:
        raise ProjectCreationError(str(exc)) from exc

    if environments is None:
        envs = DEFAULT_ENVIRONMENTS
    else:
        envs = environments
        if not envs:
            raise ProjectCreationError("At least one environment must be specified.")

    # Sanitize all environment names
    sanitized_envs = []
    for env in envs:
        try:
            sanitized_envs.append(sanitize_environment_name(env))
        except SanitizationError as exc:
            raise ProjectCreationError(f"Invalid environment name '{env}': {exc}") from exc

    created_paths: List[str] = []
    skipped_paths: List[str] = []

    for env in sanitized_envs:
        path = f"{base_path}/{sanitized_project_name}/{env}"

        # Check if path already exists by trying to read it
        existing_data = client.read_data(path)
        if existing_data:
            skipped_paths.append(path)
            continue

        # Create empty secret to establish the path
        try:
            client.write_data(path, {})
            created_paths.append(path)
        except VaultClientError as exc:
            raise ProjectCreationError(
                f"Failed to create path '{path}': {exc}",
            ) from exc

    return ProjectCreationResult(
        project_name=sanitized_project_name,
        created_paths=created_paths,
        skipped_paths=skipped_paths,
    )


def list_projects(
    client: VaultClient,
    base_path: str = DEFAULT_VAULT_BASE_PATH,
) -> List[str]:
    """List all projects under the base path.

    Args:
        client: Vault client instance
        base_path: Base KV v2 path (defaults to "secret/data")

    Returns:
        List of project names

    Raises:
        VaultClientError: If Vault operations fail
    """
    try:
        # List paths under base_path
        projects = client.list_paths(base_path)
        return sorted(projects)
    except VaultClientError as exc:
        raise ProjectOperationError(f"Failed to list projects: {exc}") from exc


def get_project(
    client: VaultClient,
    project_name: str,
    base_path: str = DEFAULT_VAULT_BASE_PATH,
) -> ProjectInfo:
    """Get information about a project.

    Args:
        client: Vault client instance
        project_name: Name of the project
        base_path: Base KV v2 path (defaults to "secret/data")

    Returns:
        ProjectInfo with project details

    Raises:
        ProjectOperationError: If project doesn't exist or operation fails
        VaultClientError: If Vault operations fail
    """
    try:
        sanitized_project_name = sanitize_project_name(project_name)
    except SanitizationError as exc:
        raise ProjectOperationError(str(exc)) from exc

    project_path = f"{base_path}/{sanitized_project_name}"
    try:
        # List environments under the project
        environments = client.list_paths(project_path)
        if not environments:
            raise ProjectOperationError(f"Project '{sanitized_project_name}' not found or has no environments")

        # Build full paths
        paths = [f"{project_path}/{env}" for env in sorted(environments)]

        return ProjectInfo(
            project_name=sanitized_project_name,
            environments=sorted(environments),
            paths=paths,
        )
    except VaultClientError as exc:
        raise ProjectOperationError(f"Failed to get project '{sanitized_project_name}': {exc}") from exc


def update_project(
    client: VaultClient,
    project_name: str,
    add_environments: List[str] | None = None,
    remove_environments: List[str] | None = None,
    base_path: str = DEFAULT_VAULT_BASE_PATH,
) -> ProjectUpdateResult:
    """Update a project by adding or removing environments.

    Args:
        client: Vault client instance
        project_name: Name of the project
        add_environments: List of environments to add
        remove_environments: List of environments to remove
        base_path: Base KV v2 path (defaults to "secret/data")

    Returns:
        ProjectUpdateResult with update details

    Raises:
        ProjectOperationError: If project doesn't exist or operation fails
        VaultClientError: If Vault operations fail
    """
    try:
        sanitized_project_name = sanitize_project_name(project_name)
    except SanitizationError as exc:
        raise ProjectOperationError(str(exc)) from exc

    # Verify project exists
    try:
        project_info = get_project(client, sanitized_project_name, base_path)
    except ProjectOperationError:
        raise ProjectOperationError(f"Project '{sanitized_project_name}' not found")

    add_envs = add_environments or []
    remove_envs = remove_environments or []

    if not add_envs and not remove_envs:
        raise ProjectOperationError("At least one environment to add or remove must be specified")

    # Sanitize environment names
    sanitized_add = []
    for env in add_envs:
        try:
            sanitized_add.append(sanitize_environment_name(env))
        except SanitizationError as exc:
            raise ProjectOperationError(f"Invalid environment name '{env}': {exc}") from exc

    sanitized_remove = []
    for env in remove_envs:
        try:
            sanitized_remove.append(sanitize_environment_name(env))
        except SanitizationError as exc:
            raise ProjectOperationError(f"Invalid environment name '{env}': {exc}") from exc

    # Check that environments to remove exist
    existing_envs = set(project_info.environments)
    for env in sanitized_remove:
        if env not in existing_envs:
            raise ProjectOperationError(f"Environment '{env}' does not exist in project '{sanitized_project_name}'")

    # Check that environments to add don't already exist
    for env in sanitized_add:
        if env in existing_envs:
            raise ProjectOperationError(f"Environment '{env}' already exists in project '{sanitized_project_name}'")

    project_path = f"{base_path}/{sanitized_project_name}"
    created_paths: List[str] = []
    deleted_paths: List[str] = []

    # Add environments
    for env in sanitized_add:
        path = f"{project_path}/{env}"
        try:
            client.write_data(path, {})
            created_paths.append(path)
        except VaultClientError as exc:
            raise ProjectOperationError(f"Failed to add environment '{env}': {exc}") from exc

    # Remove environments (delete the paths)
    for env in sanitized_remove:
        path = f"{project_path}/{env}"
        try:
            client.delete_data(path)
            deleted_paths.append(path)
        except VaultClientError as exc:
            raise ProjectOperationError(f"Failed to remove environment '{env}': {exc}") from exc

    return ProjectUpdateResult(
        project_name=sanitized_project_name,
        added_environments=sanitized_add,
        removed_environments=sanitized_remove,
        created_paths=created_paths,
        deleted_paths=deleted_paths,
    )


def delete_project(
    client: VaultClient,
    project_name: str,
    base_path: str = DEFAULT_VAULT_BASE_PATH,
) -> List[str]:
    """Delete a project and all its environments.

    Args:
        client: Vault client instance
        project_name: Name of the project to delete
        base_path: Base KV v2 path (defaults to "secret/data")

    Returns:
        List of deleted paths

    Raises:
        ProjectOperationError: If project doesn't exist or operation fails
        VaultClientError: If Vault operations fail
    """
    try:
        sanitized_project_name = sanitize_project_name(project_name)
    except SanitizationError as exc:
        raise ProjectOperationError(str(exc)) from exc

    # Get project info to find all environments
    try:
        project_info = get_project(client, sanitized_project_name, base_path)
    except ProjectOperationError:
        raise ProjectOperationError(f"Project '{sanitized_project_name}' not found")

    deleted_paths: List[str] = []

    # Delete all environments
    for path in project_info.paths:
        try:
            client.delete_data(path)
            deleted_paths.append(path)
        except VaultClientError as exc:
            raise ProjectOperationError(f"Failed to delete path '{path}': {exc}") from exc

    return deleted_paths

