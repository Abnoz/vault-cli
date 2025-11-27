"""Input sanitization utilities for path and name validation."""

from __future__ import annotations

from .constants import ALLOWED_PATH_CHARS, MAX_ENVIRONMENT_NAME_LENGTH, MAX_PROJECT_NAME_LENGTH


class SanitizationError(ValueError):
    """Raised when input fails sanitization checks."""


def sanitize_path_component(component: str, max_length: int, component_type: str = "path") -> str:
    """Sanitize a path component to prevent injection attacks.

    Args:
        component: The path component to sanitize
        max_length: Maximum allowed length
        component_type: Type of component for error messages

    Returns:
        Sanitized component

    Raises:
        SanitizationError: If component is invalid
    """
    if not component:
        raise SanitizationError(f"{component_type} cannot be empty")

    # Check for path traversal attempts
    if ".." in component or "/" in component or "\\" in component:
        raise SanitizationError(f"{component_type} contains invalid characters (path traversal attempt)")

    # Check for only allowed characters
    if not all(c in ALLOWED_PATH_CHARS for c in component):
        raise SanitizationError(
            f"{component_type} must contain only alphanumeric characters, hyphens, and underscores",
        )

    # Check length
    if len(component) > max_length:
        raise SanitizationError(f"{component_type} cannot exceed {max_length} characters")

    return component.strip()


def sanitize_project_name(name: str) -> str:
    """Sanitize a project name."""
    return sanitize_path_component(name, MAX_PROJECT_NAME_LENGTH, "project name")


def sanitize_environment_name(name: str) -> str:
    """Sanitize an environment name."""
    return sanitize_path_component(name, MAX_ENVIRONMENT_NAME_LENGTH, "environment name")


def sanitize_path(path: str) -> str:
    """Sanitize a full Vault path to prevent injection.

    Args:
        path: Full Vault path (e.g., "secret/data/project/env")

    Returns:
        Sanitized path

    Raises:
        SanitizationError: If path contains invalid components
    """
    if not path:
        raise SanitizationError("Path cannot be empty")

    # Split path and validate each component
    parts = path.split("/")
    sanitized_parts = []

    for part in parts:
        if not part:
            continue  # Skip empty parts from leading/trailing slashes
        # Allow mount points and "data" marker
        if part in ("secret", "data"):
            sanitized_parts.append(part)
        else:
            # Sanitize other components
            sanitized_parts.append(sanitize_path_component(part, MAX_PROJECT_NAME_LENGTH, "path component"))

    return "/".join(sanitized_parts)

