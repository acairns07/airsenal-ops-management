"""Secrets management API routes."""
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone

from models import SecretUpdate
from auth import get_current_user
from utils.logging import get_logger
from utils.encryption import encrypt_secret, decrypt_secret

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database instance."""
    from database import db
    return db


@router.get("")
async def get_secrets(
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get all secrets (masked values).

    Args:
        current_user: Current authenticated user
        db: Database instance

    Returns:
        List of secrets with masked values
    """
    secrets = await db.secrets.find({}).to_list(None)

    # Don't return actual values, just whether they're set
    secret_status = []
    for secret in secrets:
        secret_status.append({
            "key": secret['key'],
            "is_set": bool(secret.get('value')),
            "masked_value": "***" if secret.get('value') else ""
        })

    logger.info(f"Retrieved {len(secret_status)} secrets", extra={'user_email': current_user})
    return secret_status


@router.post("")
async def update_secret(
    secret: SecretUpdate,
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Update or create a secret.

    Args:
        secret: Secret to update
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Success status
    """
    try:
        # Encrypt the secret value
        encrypted_value = encrypt_secret(secret.value)

        # Update or insert secret
        await db.secrets.update_one(
            {"key": secret.key},
            {
                "$set": {
                    "value": encrypted_value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )

        logger.info(
            f"Secret updated",
            extra={'user_email': current_user, 'secret_key': secret.key}
        )

        return {"success": True, "key": secret.key}
    except Exception as e:
        logger.error(
            f"Failed to update secret: {e}",
            extra={'user_email': current_user, 'secret_key': secret.key},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to update secret: {str(e)}")
