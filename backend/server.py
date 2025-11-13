"""Main FastAPI application with modular architecture."""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from starlette.middleware.cors import CORSMiddleware

from config import config
from database import db, close_db_connection
from api import api_router
from jobs.queue import init_job_queue, job_queue
from jobs.websocket_manager import manager
from middleware import RateLimitMiddleware
from auth import verify_websocket_token
from utils.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create the main app
app = FastAPI(
    title="AIrsenal Control Room API",
    description="Backend API for managing AIrsenal FPL analytics",
    version="2.0.0"
)

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.add_middleware(
    RateLimitMiddleware,
    enabled=config.RATE_LIMIT_ENABLED
)

# Include API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Application starting up...")
    logger.info(f"CORS origins: {config.CORS_ORIGINS}")
    logger.info(f"Rate limiting: {'enabled' if config.RATE_LIMIT_ENABLED else 'disabled'}")
    logger.info(f"Max job retries: {config.MAX_JOB_RETRIES}")

    # Initialize job queue
    init_job_queue(db)
    logger.info("Job queue initialized")

    # Initialize AI and intelligence services
    from ai.recommendation_engine import init_recommendation_engine
    from intelligence.intelligence_service import init_intelligence_service

    init_recommendation_engine(db)
    init_intelligence_service(db)
    logger.info("AI and intelligence services initialized")

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down...")
    await close_db_connection()
    logger.info("Application shutdown complete")


@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str, token: str = Query(None)):
    """
    WebSocket endpoint for real-time job logs and status updates.

    Args:
        websocket: WebSocket connection
        job_id: Job identifier
        token: Optional JWT token for authentication

    Note:
        Token can be provided as query parameter (?token=xxx) for WebSocket connections
        since WebSocket API doesn't support custom headers in browser environments.
    """
    # Authenticate WebSocket connection
    if token:
        email = verify_websocket_token(token)
        if not email:
            logger.warning(
                f"WebSocket authentication failed",
                extra={'job_id': job_id}
            )
            await websocket.close(code=1008, reason="Authentication failed")
            return
        logger.info(
            f"WebSocket authenticated",
            extra={'job_id': job_id, 'user_email': email}
        )
    else:
        logger.warning(
            f"WebSocket connection without token",
            extra={'job_id': job_id}
        )
        # For backwards compatibility, allow connections without token
        # In production, you may want to enforce authentication by uncommenting:
        # await websocket.close(code=1008, reason="Authentication required")
        # return

    await manager.connect(job_id, websocket)

    try:
        # Send existing logs
        job = await db.jobs.find_one({"id": job_id})
        if job and job.get('logs'):
            for log in job['logs']:
                await websocket.send_json({"type": "log", "message": log})

        # Send current status
        if job:
            await websocket.send_json({"type": "status", "status": job.get('status', 'pending')})

        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages (ping/pong for keepalive)
            data = await websocket.receive_text()
            # Echo back for keepalive
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
        logger.info(f"WebSocket disconnected normally", extra={'job_id': job_id})
    except Exception as e:
        manager.disconnect(job_id, websocket)
        logger.error(
            f"WebSocket error: {e}",
            extra={'job_id': job_id},
            exc_info=True
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server_new:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
