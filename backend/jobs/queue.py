"""Job queue with retry logic and error handling."""
import asyncio
from typing import Set, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from config import config
from models import Job
from utils.logging import get_logger
from .executor import JobExecutor, JobExecutionError
from .websocket_manager import manager

logger = get_logger(__name__)


class JobQueue:
    """Job queue with retry logic and sequential processing."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.is_processing = False
        self.current_job_id: Optional[str] = None
        self.executor = JobExecutor(db)
        self.cancelled_jobs: Set[str] = set()

    async def add_job(self, job: Job) -> str:
        """
        Add a job to the queue.

        Args:
            job: Job to add

        Returns:
            Job ID
        """
        # Save job to database
        job_dict = job.model_dump()
        job_dict['created_at'] = job_dict['created_at'].isoformat()
        if job_dict.get('started_at'):
            job_dict['started_at'] = job_dict['started_at'].isoformat()
        if job_dict.get('completed_at'):
            job_dict['completed_at'] = job_dict['completed_at'].isoformat()

        await self.db.jobs.insert_one(job_dict)
        logger.info(
            f"Job added to queue",
            extra={'job_id': job.id, 'command': job.command}
        )

        # Start processing if not already processing
        if not self.is_processing:
            asyncio.create_task(self.process_queue())

        return job.id

    async def process_queue(self):
        """Process jobs in the queue sequentially."""
        if self.is_processing:
            return

        self.is_processing = True
        logger.info("Job queue processing started")

        try:
            while True:
                # Get next pending job
                job_doc = await self.db.jobs.find_one(
                    {"status": "pending"},
                    sort=[("created_at", 1)]
                )

                if not job_doc:
                    break

                job_id = job_doc['id']
                self.current_job_id = job_id

                # Update job status to running
                await self._update_job_status(
                    job_id,
                    "running",
                    started_at=datetime.now(timezone.utc)
                )

                # Execute job with retry logic
                await self._execute_with_retry(job_doc)

        except Exception as e:
            logger.error(f"Queue processing error: {e}", exc_info=True)
        finally:
            self.is_processing = False
            self.current_job_id = None
            self.cancelled_jobs.clear()
            logger.info("Job queue processing finished")

    async def _execute_with_retry(self, job_doc: Dict[str, Any]):
        """
        Execute a job with retry logic.

        Args:
            job_doc: Job document from database
        """
        job_id = job_doc['id']
        command = job_doc['command']
        parameters = job_doc['parameters']
        retry_count = job_doc.get('retry_count', 0)
        max_retries = job_doc.get('max_retries', config.MAX_JOB_RETRIES)

        logger.info(
            f"Executing job (attempt {retry_count + 1}/{max_retries + 1})",
            extra={'job_id': job_id, 'command': command}
        )

        try:
            # Create log callback
            async def log_callback(message: str):
                await self._log_to_job(job_id, message)

            # Execute job
            logs, returncode = await self.executor.execute(
                job_id,
                command,
                parameters,
                log_callback
            )

            # Check if cancelled
            if job_id in self.cancelled_jobs:
                await self._handle_cancellation(job_id)
                return

            # Handle result
            if returncode == 0:
                await self._handle_success(job_id, command, parameters, logs)
            else:
                await self._handle_failure(job_id, command, returncode, retry_count, max_retries)

        except asyncio.CancelledError:
            await self._handle_cancellation(job_id)
        except JobExecutionError as e:
            await self._handle_failure(job_id, command, str(e), retry_count, max_retries)
        except Exception as e:
            logger.error(
                f"Unexpected error during job execution: {e}",
                extra={'job_id': job_id},
                exc_info=True
            )
            await self._handle_failure(job_id, command, str(e), retry_count, max_retries)

    async def _handle_success(
        self,
        job_id: str,
        command: str,
        parameters: Dict[str, Any],
        logs: list
    ):
        """
        Handle successful job completion.

        Args:
            job_id: Job identifier
            command: Command type
            parameters: Command parameters
            logs: Job logs
        """
        logger.info(f"Job completed successfully", extra={'job_id': job_id})

        # Parse output
        output_payload = await self.executor.parse_output(command, parameters, logs)
        if output_payload:
            await self.db.jobs.update_one(
                {"id": job_id},
                {"$set": {"output": output_payload}}
            )
            await manager.broadcast(job_id, {"type": "output", "payload": output_payload})

        # Persist database
        try:
            await self.executor._persist_sqlite(job_id)
            await self._log_to_job(job_id, "Database persisted successfully")
        except JobExecutionError as e:
            logger.error(f"Failed to persist database: {e}", extra={'job_id': job_id})
            await self._update_job_status(
                job_id,
                "failed",
                error=f"Persist failed: {e}",
                completed_at=datetime.now(timezone.utc)
            )
            return

        # Mark as completed
        await self._update_job_status(
            job_id,
            "completed",
            completed_at=datetime.now(timezone.utc)
        )

    async def _handle_failure(
        self,
        job_id: str,
        command: str,
        error: Any,
        retry_count: int,
        max_retries: int
    ):
        """
        Handle job failure with retry logic.

        Args:
            job_id: Job identifier
            command: Command type
            error: Error message or return code
            retry_count: Current retry count
            max_retries: Maximum retries allowed
        """
        error_msg = str(error) if isinstance(error, str) else f"Command exited with code {error}"
        logger.warning(
            f"Job failed: {error_msg}",
            extra={'job_id': job_id, 'retry_count': retry_count, 'max_retries': max_retries}
        )

        # Check if we should retry
        if retry_count < max_retries:
            # Schedule retry
            await self._log_to_job(
                job_id,
                f"Job failed, will retry in {config.JOB_RETRY_DELAY_SECONDS} seconds (attempt {retry_count + 1}/{max_retries})"
            )
            await self.db.jobs.update_one(
                {"id": job_id},
                {
                    "$set": {
                        "status": "pending",
                        "retry_count": retry_count + 1,
                        "started_at": None
                    }
                }
            )
            await manager.broadcast(job_id, {
                "type": "status",
                "status": "pending",
                "retry_count": retry_count + 1
            })

            # Wait before retry
            await asyncio.sleep(config.JOB_RETRY_DELAY_SECONDS)
            logger.info(f"Retrying job", extra={'job_id': job_id})
        else:
            # Max retries exceeded
            await self._log_to_job(
                job_id,
                f"Job failed after {max_retries} retries: {error_msg}"
            )
            await self._update_job_status(
                job_id,
                "failed",
                error=error_msg,
                completed_at=datetime.now(timezone.utc)
            )

    async def _handle_cancellation(self, job_id: str):
        """
        Handle job cancellation.

        Args:
            job_id: Job identifier
        """
        self.cancelled_jobs.discard(job_id)
        await self._log_to_job(job_id, "Job cancelled by user")
        await self._update_job_status(
            job_id,
            "cancelled",
            error="Cancelled by user request",
            completed_at=datetime.now(timezone.utc)
        )
        logger.info(f"Job cancelled", extra={'job_id': job_id})

    async def cancel_job(self, job_id: str):
        """
        Cancel a running job.

        Args:
            job_id: Job identifier to cancel

        Raises:
            ValueError: If job is not currently running
        """
        if self.current_job_id != job_id:
            raise ValueError("Job is not currently running")

        if job_id in self.cancelled_jobs:
            logger.warning(f"Job already being cancelled", extra={'job_id': job_id})
            return

        self.cancelled_jobs.add(job_id)
        logger.info(f"Cancelling job", extra={'job_id': job_id})

        await self._log_to_job(
            job_id,
            "Cancellation requested by user. Attempting to terminate process..."
        )
        await self.db.jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "cancelling"}}
        )
        await manager.broadcast(job_id, {"type": "status", "status": "cancelling"})

        # Terminate process
        self.executor.terminate()

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        """
        Update job status in database.

        Args:
            job_id: Job identifier
            status: New status
            error: Optional error message
            started_at: Optional start timestamp
            completed_at: Optional completion timestamp
        """
        update_doc = {"status": status}
        if error is not None:
            update_doc["error"] = error
        if started_at is not None:
            update_doc["started_at"] = started_at.isoformat()
        if completed_at is not None:
            update_doc["completed_at"] = completed_at.isoformat()

        await self.db.jobs.update_one(
            {"id": job_id},
            {"$set": update_doc}
        )

        # Broadcast status update
        broadcast_msg = {"type": "status", "status": status}
        if error:
            broadcast_msg["error"] = error
        await manager.broadcast(job_id, broadcast_msg)

        logger.debug(
            f"Job status updated",
            extra={'job_id': job_id, 'status': status}
        )

    async def _log_to_job(self, job_id: str, message: str):
        """
        Add log message to job.

        Args:
            job_id: Job identifier
            message: Log message
        """
        await self.db.jobs.update_one(
            {"id": job_id},
            {"$push": {"logs": message}}
        )

        # Broadcast log to WebSocket clients
        await manager.broadcast(job_id, {"type": "log", "message": message})


# Global job queue instance (will be initialized with db in main app)
job_queue: Optional[JobQueue] = None


def init_job_queue(db: AsyncIOMotorDatabase):
    """Initialize the global job queue."""
    global job_queue
    job_queue = JobQueue(db)
    logger.info("Job queue initialized")
