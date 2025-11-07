"""API routes module."""
from fastapi import APIRouter
from .auth import router as auth_router
from .secrets import router as secrets_router
from .jobs import router as jobs_router
from .reports import router as reports_router
from .team import router as team_router
from .health import router as health_router
from .ai_recommendations import router as ai_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(secrets_router, prefix="/secrets", tags=["secrets"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(team_router, prefix="/team", tags=["team"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])

__all__ = ['api_router']
