"""Tests for authentication module."""
import pytest
from fastapi import HTTPException

from auth import create_token, verify_token, hash_password, verify_password


class TestJWTHandler:
    """Test JWT token handling."""

    def test_create_token(self):
        """Test token creation."""
        email = "test@example.com"
        token = create_token(email)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid(self):
        """Test verification of valid token."""
        email = "test@example.com"
        token = create_token(email)
        verified_email = verify_token(token)
        assert verified_email == email

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        verified_email = verify_token(invalid_token)
        assert verified_email is None

    def test_verify_token_expired(self):
        """Test verification of expired token."""
        # Create a token with expired timestamp
        import jwt
        from datetime import datetime, timezone, timedelta
        from config import config

        payload = {
            'email': 'test@example.com',
            'exp': datetime.now(timezone.utc) - timedelta(hours=1),
            'iat': datetime.now(timezone.utc) - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
        verified_email = verify_token(expired_token)
        assert verified_email is None


class TestPasswordHandling:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith('$2b$')  # bcrypt hash format

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "testpassword123"
        invalid_hash = "not-a-valid-hash"
        assert verify_password(password, invalid_hash) is False


@pytest.mark.asyncio
class TestAuthAPI:
    """Test authentication API endpoints."""

    async def test_hash_password_endpoint(self, test_client):
        """Test password hashing endpoint."""
        response = test_client.post(
            "/api/auth/hash-password",
            json={"password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "hash" in data
        assert data["hash"].startswith('$2b$')

    async def test_login_success(self, test_client, admin_credentials):
        """Test successful login."""
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": admin_credentials["email"],
                "password": admin_credentials["password"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "email" in data
        assert data["email"] == admin_credentials["email"]

    async def test_login_wrong_email(self, test_client, admin_credentials):
        """Test login with wrong email."""
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "wrong@example.com",
                "password": admin_credentials["password"]
            }
        )
        assert response.status_code == 401

    async def test_login_wrong_password(self, test_client, admin_credentials):
        """Test login with wrong password."""
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": admin_credentials["email"],
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    async def test_check_auth_valid(self, test_client, auth_headers):
        """Test auth check with valid token."""
        response = test_client.get("/api/auth/check", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert "email" in data

    async def test_check_auth_invalid(self, test_client):
        """Test auth check with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = test_client.get("/api/auth/check", headers=headers)
        assert response.status_code == 401

    async def test_check_auth_missing(self, test_client):
        """Test auth check without token."""
        response = test_client.get("/api/auth/check")
        assert response.status_code == 403  # Missing credentials
