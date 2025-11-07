"""Tests for rate limiting middleware."""
import pytest
from middleware.rate_limit import RateLimiter


class TestRateLimiter:
    """Test rate limiting logic."""

    def test_allows_requests_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(requests_per_minute=10)
        key = "test-client"

        for i in range(10):
            allowed, _ = limiter.is_allowed(key)
            assert allowed is True, f"Request {i+1} should be allowed"

    def test_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(requests_per_minute=5)
        key = "test-client"

        # Make requests up to limit
        for _ in range(5):
            allowed, _ = limiter.is_allowed(key)
            assert allowed is True

        # Next request should be blocked
        allowed, retry_after = limiter.is_allowed(key)
        assert allowed is False
        assert retry_after > 0

    def test_different_keys_tracked_separately(self):
        """Test that different keys are tracked separately."""
        limiter = RateLimiter(requests_per_minute=3)
        key1 = "client-1"
        key2 = "client-2"

        # Client 1 makes requests
        for _ in range(3):
            allowed, _ = limiter.is_allowed(key1)
            assert allowed is True

        # Client 1 is now blocked
        allowed, _ = limiter.is_allowed(key1)
        assert allowed is False

        # Client 2 should still be allowed
        allowed, _ = limiter.is_allowed(key2)
        assert allowed is True

    def test_cleanup_removes_old_entries(self):
        """Test that cleanup removes old entries."""
        limiter = RateLimiter(requests_per_minute=10)
        key = "test-client"

        # Make a request
        limiter.is_allowed(key)
        assert key in limiter.requests

        # Manually set old timestamp
        from datetime import datetime, timezone, timedelta
        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        limiter.requests[key] = [old_time]

        # Cleanup should remove the key
        limiter.cleanup()
        assert key not in limiter.requests

    def test_retry_after_value(self):
        """Test retry_after value is reasonable."""
        limiter = RateLimiter(requests_per_minute=2)
        key = "test-client"

        # Exhaust limit
        for _ in range(2):
            limiter.is_allowed(key)

        # Check retry_after
        allowed, retry_after = limiter.is_allowed(key)
        assert allowed is False
        assert 0 < retry_after <= 60  # Should be within a minute
