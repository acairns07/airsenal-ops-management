"""JWT token handling."""
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from config import config
from utils.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


def create_token(email: str) -> str:
    """
    Create a JWT token for a user.

    Args:
        email: User's email address

    Returns:
        JWT token string
    """
    payload = {
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    logger.info(f"Token created for user", extra={'user_email': email})
    return token


def verify_token(token: str) -> Optional[str]:
    """
    Verify a JWT token and extract the email.

    Args:
        token: JWT token string

    Returns:
        Email if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload.get('email')
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: expired token")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = None
) -> str:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: MongoDB database instance

    Returns:
        User's email address

    Raises:
        HTTPException: If token is invalid or user is not authorized
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")

    email = verify_token(credentials.credentials)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if db:
        # Check if user email matches admin email
        admin_email = await db.secrets.find_one({"key": "APP_ADMIN_EMAIL"})
        if not admin_email or email != admin_email.get('value'):
            logger.warning(f"Unauthorized access attempt", extra={'user_email': email})
            raise HTTPException(status_code=403, detail="Unauthorized")

    logger.debug(f"User authenticated", extra={'user_email': email})
    return email


def verify_websocket_token(token: str, db: AsyncIOMotorDatabase = None) -> Optional[str]:
    """
    Verify a WebSocket connection token.

    Args:
        token: JWT token string
        db: MongoDB database instance (optional)

    Returns:
        Email if valid, None otherwise
    """
    return verify_token(token)
