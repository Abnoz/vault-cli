"""Logging configuration for the API."""

from __future__ import annotations

import logging
import sys
from typing import Any

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("vault_api")


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (defaults to 'vault_api')

    Returns:
        Configured logger instance
    """
    if name:
        return logging.getLogger(f"vault_api.{name}")
    return logger


def log_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Log an API request.

    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
    """
    level = logging.INFO if status_code < 400 else logging.WARNING
    logger.log(
        level,
        "Request: %s %s - Status: %d - Duration: %.2fms",
        method,
        path,
        status_code,
        duration_ms,
    )


def log_error(operation: str, error: Exception, **context: Any) -> None:
    """Log an error with context.

    Args:
        operation: Operation that failed
        error: Exception that occurred
        **context: Additional context to log
    """
    context_str = " ".join(f"{k}={v}" for k, v in context.items())
    logger.error(
        "Error in %s: %s - %s",
        operation,
        type(error).__name__,
        str(error),
        extra={"context": context_str} if context_str else None,
    )

