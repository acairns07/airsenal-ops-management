"""Rate limiting middleware."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config import config
from utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        Check if a request is allowed.

        Args:
            key: Unique identifier for the client (e.g., IP address)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)

        # Remove old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > minute_ago
        ]

        # Check if limit exceeded
        if len(self.requests[key]) >= self.requests_per_minute:
            oldest_request = min(self.requests[key])
            retry_after = int((oldest_request + timedelta(minutes=1) - now).total_seconds())
            return False, max(retry_after, 1)

        # Add current request
        self.requests[key] = self.requests[key][-self.requests_per_minute + 1:] + [now]
        return True, 0

    def cleanup(self):
        """Clean up old entries to prevent memory growth."""
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)

        # Remove keys with no recent requests
        keys_to_remove = [
            key for key, requests in self.requests.items()
            if not requests or max(requests) < minute_ago
        ]
        for key in keys_to_remove:
            del self.requests[key]


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=config.RATE_LIMIT_PER_MINUTE)


def rate_limit_key(request: Request) -> str:
    """
    Generate a rate limit key from a request.

    Args:
        request: FastAPI request

    Returns:
        Rate limit key (IP address or user identifier)
    """
    # Try to get user from Authorization header first
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        # Use token as key (hashed for privacy)
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    # Fall back to IP address
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()

    client = request.client
    return client.host if client else 'unknown'


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.limiter = _rate_limiter

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health check
        if request.url.path == '/api/health':
            return await call_next(request)

        # Get rate limit key
        key = rate_limit_key(request)

        # Check rate limit
        allowed, retry_after = self.limiter.is_allowed(key)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {key}",
                extra={
                    'rate_limit_key': key,
                    'path': request.url.path,
                    'retry_after': retry_after
                }
            )
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Retry after {retry_after} seconds.",
                headers={'Retry-After': str(retry_after)}
            )

        # Process request
        response = await call_next(request)

        # Periodic cleanup (every ~100 requests)
        import random
        if random.random() < 0.01:
            self.limiter.cleanup()

        return response
