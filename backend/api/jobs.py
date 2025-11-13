"""Job management API routes."""
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from datetime import datetime

from models import JobCreate, Job
from auth import get_current_user
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database instance."""
    from database import db
    return db


def get_job_queue():
    """Dependency to get job queue instance."""
    from jobs.queue import job_queue
    if not job_queue:
        raise HTTPException(status_code=500, detail="Job queue not initialized")
    return job_queue


@router.post("", response_model=Job)
async def create_job(
    job_create: JobCreate,
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    queue = Depends(get_job_queue)
):
    """
    Create a new job.

    Args:
        job_create: Job to create
        current_user: Current authenticated user
        db: Database instance
        queue: Job queue instance

    Returns:
        Created job
    """
    job = Job(command=job_create.command, parameters=job_create.parameters)
    job_id = await queue.add_job(job)

    logger.info(
        f"Job created",
        extra={'user_email': current_user, 'job_id': job_id, 'command': job.command}
    )

    return job


@router.get("", response_model=List[Job])
async def get_jobs(
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get recent jobs (last 50).

    Args:
        current_user: Current authenticated user
        db: Database instance

    Returns:
        List of jobs
    """
    jobs = await db.jobs.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)

    # Convert ISO strings back to datetime
    for job in jobs:
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('started_at'), str):
            job['started_at'] = datetime.fromisoformat(job['started_at'])
        if isinstance(job.get('completed_at'), str):
            job['completed_at'] = datetime.fromisoformat(job['completed_at'])

    return jobs


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a specific job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Job details

    Raises:
        HTTPException: If job not found
    """
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Convert ISO strings back to datetime
    if isinstance(job.get('created_at'), str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    if isinstance(job.get('started_at'), str):
        job['started_at'] = datetime.fromisoformat(job['started_at'])
    if isinstance(job.get('completed_at'), str):
        job['completed_at'] = datetime.fromisoformat(job['completed_at'])

    return job


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: str = Depends(get_current_user),
    queue = Depends(get_job_queue)
):
    """
    Cancel a running job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        queue: Job queue instance

    Returns:
        Success status

    Raises:
        HTTPException: If job cannot be cancelled
    """
    try:
        await queue.cancel_job(job_id)
        logger.info(f"Job cancelled", extra={'user_email': current_user, 'job_id': job_id})
        return {"success": True, "job_id": job_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{job_id}/logs")
async def clear_job_logs(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Clear logs for a specific job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Success status

    Raises:
        HTTPException: If job not found
    """
    result = await db.jobs.update_one({"id": job_id}, {"$set": {"logs": []}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info(f"Job logs cleared", extra={'user_email': current_user, 'job_id': job_id})
    return {"success": True, "job_id": job_id}


@router.delete("/logs")
async def clear_all_job_logs(
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Clear logs for all jobs.

    Args:
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Success status with count of cleared jobs
    """
    result = await db.jobs.update_many({}, {"$set": {"logs": []}})
    logger.info(
        f"All job logs cleared",
        extra={'user_email': current_user, 'count': result.modified_count}
    )
    return {"success": True, "cleared": result.modified_count}


@router.get("/{job_id}/output")
async def get_job_output(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get parsed output for a job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Job output

    Raises:
        HTTPException: If job not found
    """
    job = await db.jobs.find_one(
        {"id": job_id},
        {"_id": 0, "id": 1, "command": 1, "status": 1, "parameters": 1, "completed_at": 1, "output": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
