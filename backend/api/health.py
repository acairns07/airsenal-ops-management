"""Health check API routes."""
import sys
from fastapi import APIRouter

router = APIRouter()

# Python version check
PYTHON_VERSION = sys.version_info
PYTHON_VERSION_VALID = PYTHON_VERSION < (3, 13)


@router.get("/health")
async def health():
    """
    Health check endpoint.

    Returns:
        Health status and Python version information
    """
    return {
        "status": "ok",
        "python_version": f"{PYTHON_VERSION.major}.{PYTHON_VERSION.minor}.{PYTHON_VERSION.micro}",
        "python_version_valid": PYTHON_VERSION_VALID
    }


@router.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        API welcome message
    """
    return {"message": "AIrsenal Control Room API"}
