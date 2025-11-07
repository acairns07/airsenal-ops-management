"""Tests for secrets API endpoints."""
import pytest


@pytest.mark.asyncio
class TestSecretsAPI:
    """Test secrets management API."""

    async def test_get_secrets_empty(self, test_client, auth_headers, clean_db):
        """Test getting secrets when none exist."""
        response = test_client.get("/api/secrets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have at least admin credentials
        assert isinstance(data, list)

    async def test_update_secret(self, test_client, auth_headers, clean_db):
        """Test updating a secret."""
        response = test_client.post(
            "/api/secrets",
            json={"key": "TEST_SECRET", "value": "test-value"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["key"] == "TEST_SECRET"

    async def test_get_secrets_after_update(self, test_client, auth_headers, clean_db):
        """Test getting secrets after updating one."""
        # Create a secret
        test_client.post(
            "/api/secrets",
            json={"key": "TEST_SECRET", "value": "test-value"},
            headers=auth_headers
        )

        # Get all secrets
        response = test_client.get("/api/secrets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Find our secret
        test_secret = next((s for s in data if s["key"] == "TEST_SECRET"), None)
        assert test_secret is not None
        assert test_secret["is_set"] is True
        assert test_secret["masked_value"] == "***"

    async def test_update_secret_unauthorized(self, test_client, clean_db):
        """Test updating secret without authentication."""
        response = test_client.post(
            "/api/secrets",
            json={"key": "TEST_SECRET", "value": "test-value"}
        )
        assert response.status_code == 403

    async def test_get_secrets_unauthorized(self, test_client, clean_db):
        """Test getting secrets without authentication."""
        response = test_client.get("/api/secrets")
        assert response.status_code == 403

    async def test_update_fpl_secret(self, test_client, auth_headers, clean_db):
        """Test updating FPL secret."""
        response = test_client.post(
            "/api/secrets",
            json={"key": "FPL_TEAM_ID", "value": "123456"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify it's stored encrypted
        from database import db
        secret_doc = await db.secrets.find_one({"key": "FPL_TEAM_ID"})
        assert secret_doc is not None
        # Encrypted value should be different from original
        assert secret_doc["value"] != "123456"

    async def test_secret_encryption_in_storage(self, test_client, auth_headers, clean_db):
        """Test that secrets are encrypted in database."""
        from utils.encryption import decrypt_secret

        # Store a secret
        test_value = "my-secret-value-123"
        test_client.post(
            "/api/secrets",
            json={"key": "TEST_KEY", "value": test_value},
            headers=auth_headers
        )

        # Retrieve from database directly
        from database import db
        secret_doc = await db.secrets.find_one({"key": "TEST_KEY"})
        assert secret_doc is not None

        # Value should be encrypted
        stored_value = secret_doc["value"]
        assert stored_value != test_value

        # Should be able to decrypt
        decrypted = decrypt_secret(stored_value)
        assert decrypted == test_value
