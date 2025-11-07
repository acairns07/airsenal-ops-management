"""Reports API routes."""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any

from auth import get_current_user
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database instance."""
    from database import db
    return db


@router.get("/latest")
async def get_latest_reports(
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get latest prediction and optimization reports.

    Args:
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Latest prediction and optimization reports
    """
    prediction_job = await db.jobs.find_one(
        {"command": "predict", "status": "completed", "output": {"$exists": True}},
        sort=[("completed_at", -1)],
        projection={"_id": 0, "id": 1, "completed_at": 1, "output": 1}
    )
    optimisation_job = await db.jobs.find_one(
        {"command": "optimize", "status": "completed", "output": {"$exists": True}},
        sort=[("completed_at", -1)],
        projection={"_id": 0, "id": 1, "completed_at": 1, "output": 1}
    )

    def _format(job_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not job_doc:
            return None
        payload = job_doc.get("output") or {}
        payload["job_id"] = job_doc.get("id")
        payload["completed_at"] = job_doc.get("completed_at")
        return payload

    result = {
        "prediction": _format(prediction_job),
        "optimisation": _format(optimisation_job)
    }

    logger.info(f"Latest reports retrieved", extra={'user_email': current_user})
    return result
