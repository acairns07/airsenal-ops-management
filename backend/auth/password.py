"""Password hashing and verification."""
from passlib.hash import bcrypt
from utils.logging import get_logger

logger = get_logger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    hashed = bcrypt.hash(password)
    logger.debug("Password hashed successfully")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    try:
        result = bcrypt.verify(plain_password, hashed_password)
        logger.debug(f"Password verification: {'success' if result else 'failed'}")
        return result
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False
