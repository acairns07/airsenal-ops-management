"""Secret management models."""
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class SecretUpdate(BaseModel):
    key: str
    value: str


class Secret(BaseModel):
    key: str
    value: str
    is_set: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
