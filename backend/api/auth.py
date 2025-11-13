"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import LoginRequest, LoginResponse, HashPasswordRequest, HashPasswordResponse
from auth import create_token, get_current_user, hash_password, verify_password
from utils.logging import get_logger
from utils.encryption import decrypt_secret

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database instance."""
    from database import db
    return db


@router.post("/hash-password", response_model=HashPasswordResponse)
async def hash_password_endpoint(request: HashPasswordRequest):
    """
    Generate bcrypt hash for password (utility endpoint).

    Args:
        request: Password to hash

    Returns:
        Hashed password
    """
    hashed = hash_password(request.password)
    logger.info("Password hash generated")
    return HashPasswordResponse(hash=hashed)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Login with email and password.

    Args:
        request: Login credentials
        db: Database instance

    Returns:
        JWT token and email

    Raises:
        HTTPException: If credentials are invalid
    """
    logger.info(f"Login attempt", extra={'user_email': request.email})

    # Get admin email and password hash from secrets
    admin_email_doc = await db.secrets.find_one({"key": "APP_ADMIN_EMAIL"})
    admin_password_doc = await db.secrets.find_one({"key": "APP_ADMIN_PASSWORD_HASH"})

    if not admin_email_doc or not admin_password_doc:
        logger.warning("Admin credentials not configured")
        raise HTTPException(status_code=401, detail="Admin credentials not configured")

    admin_email = admin_email_doc['value']

    # Try to decrypt password hash (for new encrypted secrets)
    try:
        admin_password_hash = decrypt_secret(admin_password_doc['value'])
    except Exception:
        # Fall back to unencrypted (for backwards compatibility)
        admin_password_hash = admin_password_doc['value']

    # Verify email
    if request.email != admin_email:
        logger.warning(f"Invalid email", extra={'user_email': request.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not verify_password(request.password, admin_password_hash):
        logger.warning(f"Invalid password", extra={'user_email': request.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate token
    token = create_token(request.email)
    logger.info(f"Login successful", extra={'user_email': request.email})

    return LoginResponse(token=token, email=request.email)


@router.get("/check")
async def check_auth(
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Check if authentication token is valid.

    Args:
        current_user: Current authenticated user (from JWT)
        db: Database instance

    Returns:
        User authentication status
    """
    # Additional check against database
    admin_email = await db.secrets.find_one({"key": "APP_ADMIN_EMAIL"})
    if not admin_email or current_user != admin_email.get('value'):
        logger.warning(f"Auth check failed: user mismatch", extra={'user_email': current_user})
        raise HTTPException(status_code=403, detail="Unauthorized")

    return {"email": current_user, "authenticated": True}
