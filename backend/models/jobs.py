"""Job models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


class JobCreate(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}


class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command: str
    parameters: Dict[str, Any] = {}
    status: str = "pending"  # pending, running, completed, failed, cancelled
    logs: List[str] = []
    output: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
