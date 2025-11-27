"""Decorators for API endpoints."""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from fastapi import Request

from .rate_limit import DEFAULT_READ_LIMIT, DEFAULT_WRITE_LIMIT, get_rate_limit_key, limiter

F = TypeVar("F", bound=Callable)


def apply_rate_limit(
    limit: str = DEFAULT_WRITE_LIMIT,
    key_func: Callable[[Request], str] = get_rate_limit_key,
) -> Callable[[F], F]:
    """Apply rate limiting to an endpoint function.

    This decorator should be applied AFTER the function is defined to avoid
    Pydantic forward reference issues with type annotations.

    Args:
        limit: Rate limit string (e.g., "10/minute")
        key_func: Function to generate rate limit key from request

    Returns:
        Decorator function

    Example:
        @app.put("/endpoint")
        async def my_endpoint(...):
            ...

        my_endpoint = apply_rate_limit()(my_endpoint)
    """
    def decorator(func: F) -> F:
        return limiter.limit(limit, key_func=key_func)(func)
    return decorator


def read_rate_limit(func: F) -> F:
    """Apply read rate limit to an endpoint.

    Convenience decorator for read operations (GET endpoints).

    Args:
        func: Endpoint function to decorate

    Returns:
        Decorated function
    """
    return apply_rate_limit(DEFAULT_READ_LIMIT)(func)


def write_rate_limit(func: F) -> F:
    """Apply write rate limit to an endpoint.

    Convenience decorator for write operations (POST, PUT, DELETE endpoints).

    Args:
        func: Endpoint function to decorate

    Returns:
        Decorated function
    """
    return apply_rate_limit(DEFAULT_WRITE_LIMIT)(func)

