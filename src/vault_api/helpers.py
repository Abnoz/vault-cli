"""Helper functions for API endpoints to reduce code duplication."""

from __future__ import annotations

from typing import Callable, TypeVar

from fastapi import HTTPException, Request, status

from vault_core.projects import ProjectCreationError, ProjectOperationError
from vault_core.vault import VaultClientError

from .errors import create_error_response
from .logging_config import log_error

T = TypeVar("T")


def parse_environments_from_request(
    query_param: str | None = None,
    request_body_environments: list[str] | None = None,
) -> list[str] | None:
    """Parse environment list from query parameter or request body.

    Query parameter takes precedence over request body.

    Args:
        query_param: Comma-separated environments from query parameter
        request_body_environments: Environments from request body

    Returns:
        List of environment names, or None if neither is provided
    """
    if query_param:
        return [env.strip() for env in query_param.split(",") if env.strip()]
    return request_body_environments


def handle_project_operation_error(
    operation: str,
    error: Exception,
    project_name: str | None = None,
    not_found_status: int = status.HTTP_400_BAD_REQUEST,
) -> HTTPException:
    """Handle project operation errors consistently.

    Args:
        operation: Name of the operation that failed
        error: The exception that occurred
        project_name: Optional project name for context
        not_found_status: HTTP status code for not found errors

    Returns:
        HTTPException to raise
    """
    context = {"project_name": project_name} if project_name else {}
    log_error(operation, error, **context)

    if isinstance(error, ProjectOperationError):
        # Check if it's a "not found" error
        error_msg = str(error).lower()
        if "not found" in error_msg:
            status_code = not_found_status
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        return create_error_response(error, status_code)

    if isinstance(error, ProjectCreationError):
        return create_error_response(error, status.HTTP_400_BAD_REQUEST)

    if isinstance(error, VaultClientError):
        return create_error_response(error, status.HTTP_502_BAD_GATEWAY, "Vault operation failed")

    # Fallback for unknown errors
    return create_error_response(error, status.HTTP_500_INTERNAL_SERVER_ERROR)


def build_project_creation_message(
    project_name: str,
    created_count: int,
    skipped_count: int,
) -> str:
    """Build a user-friendly message for project creation.

    Args:
        project_name: Name of the project
        created_count: Number of paths created
        skipped_count: Number of paths skipped (already existed)

    Returns:
        Human-readable status message
    """
    if skipped_count > 0 and created_count > 0:
        return (
            f"Project '{project_name}' partially created. "
            f"{created_count} path(s) created, {skipped_count} already existed."
        )
    if skipped_count > 0:
        return f"Project '{project_name}' already exists with all specified environments."
    return f"Project '{project_name}' created successfully with {created_count} environment(s)."


def build_project_update_message(
    project_name: str,
    added_count: int,
    removed_count: int,
) -> str:
    """Build a user-friendly message for project update.

    Args:
        project_name: Name of the project
        added_count: Number of environments added
        removed_count: Number of environments removed

    Returns:
        Human-readable status message
    """
    message = f"Project '{project_name}' updated successfully."
    if added_count > 0:
        message += f" Added {added_count} environment(s)."
    if removed_count > 0:
        message += f" Removed {removed_count} environment(s)."
    return message


def build_project_deletion_message(
    project_name: str,
    deleted_paths_count: int,
) -> str:
    """Build a user-friendly message for project deletion.

    Args:
        project_name: Name of the project
        deleted_paths_count: Number of paths deleted

    Returns:
        Human-readable status message
    """
    return (
        f"Project '{project_name}' and all its environments deleted successfully. "
        f"{deleted_paths_count} path(s) removed."
    )

