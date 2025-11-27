"""Rate limiting configuration and middleware."""

from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

# Use in-memory storage for rate limiting (works in tests and production)
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key from request (uses API key if available, otherwise IP)."""
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use first 8 chars of API key as identifier (don't use full key for privacy)
        return f"api_key:{api_key[:8]}"
    # Fall back to IP address
    return get_remote_address(request)


# Default rate limits
DEFAULT_READ_LIMIT = "100/minute"
DEFAULT_WRITE_LIMIT = "10/minute"

