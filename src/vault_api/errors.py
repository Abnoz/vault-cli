"""Error sanitization utilities for API responses."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from vault_core.projects import ProjectCreationError, ProjectOperationError
from vault_core.vault import VaultClientError

logger = logging.getLogger(__name__)


def sanitize_error_message(error: Exception, default_message: str = "An error occurred") -> str:
    """Sanitize error messages to prevent information leakage.

    Args:
        error: The exception that occurred
        default_message: Default message to return if error should be hidden

    Returns:
        Sanitized error message safe for client consumption
    """
    # Log the full error for debugging
    logger.exception("Error occurred: %s", error)

    # For known application errors, return the message (already user-friendly)
    if isinstance(error, (ProjectCreationError, ProjectOperationError)):
        return str(error)

    # For Vault errors, return generic message
    if isinstance(error, VaultClientError):
        return "Vault operation failed. Please try again later."

    # For unknown errors, return default message
    return default_message


def create_error_response(
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    default_message: str = "An error occurred",
) -> HTTPException:
    """Create a sanitized HTTP error response.

    Args:
        error: The exception that occurred
        status_code: HTTP status code
        default_message: Default message if error should be hidden

    Returns:
        HTTPException with sanitized message
    """
    message = sanitize_error_message(error, default_message)
    return HTTPException(status_code=status_code, detail=message)

