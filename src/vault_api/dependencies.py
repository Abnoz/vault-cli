"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from vault_core.config import APISettings


def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    api_settings: APISettings | None = None,
) -> str:
    """Verify API key from X-API-Key header using timing-safe comparison.

    Args:
        x_api_key: API key from request header
        api_settings: API settings containing expected API key

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if api_settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API configuration not available",
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use timing-safe comparison to prevent timing attacks
    if not secrets.compare_digest(x_api_key, api_settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key

