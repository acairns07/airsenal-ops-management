"""Tests for encryption utilities."""
import pytest
from utils.encryption import encrypt_secret, decrypt_secret


class TestEncryption:
    """Test secret encryption and decryption."""

    def test_encrypt_secret(self):
        """Test encrypting a secret."""
        secret = "my-secret-value"
        encrypted = encrypt_secret(secret)
        assert encrypted is not None
        assert encrypted != secret
        assert len(encrypted) > len(secret)

    def test_decrypt_secret(self):
        """Test decrypting a secret."""
        secret = "my-secret-value"
        encrypted = encrypt_secret(secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == secret

    def test_encrypt_decrypt_round_trip(self):
        """Test full encryption/decryption round trip."""
        original = "test-password-123!@#"
        encrypted = encrypt_secret(original)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        secret = ""
        encrypted = encrypt_secret(secret)
        assert encrypted == ""

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        decrypted = decrypt_secret("")
        assert decrypted == ""

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data."""
        with pytest.raises(ValueError):
            decrypt_secret("invalid-encrypted-data")

    def test_encrypt_special_characters(self):
        """Test encrypting strings with special characters."""
        secret = "p@ssw0rd!#$%^&*()"
        encrypted = encrypt_secret(secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == secret

    def test_encrypt_unicode(self):
        """Test encrypting unicode strings."""
        secret = "密码🔐"
        encrypted = encrypt_secret(secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == secret
