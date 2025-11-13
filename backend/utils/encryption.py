"""Secret encryption utilities."""
from cryptography.fernet import Fernet
from config import config


class SecretEncryption:
    """Handle encryption and decryption of secrets."""

    def __init__(self):
        self.cipher = Fernet(config.ENCRYPTION_KEY.encode() if isinstance(config.ENCRYPTION_KEY, str) else config.ENCRYPTION_KEY)

    def encrypt(self, value: str) -> str:
        """Encrypt a secret value."""
        if not value:
            return value
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt a secret value."""
        if not encrypted_value:
            return encrypted_value
        try:
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt secret: {e}")


_encryption = SecretEncryption()


def encrypt_secret(value: str) -> str:
    """Encrypt a secret value."""
    return _encryption.encrypt(value)


def decrypt_secret(encrypted_value: str) -> str:
    """Decrypt a secret value."""
    return _encryption.decrypt(encrypted_value)
