from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
import json

class CanonicalEvent(BaseModel):
    """
    The Single Source of Truth for the Unified Timeline.
    Aligns with 'Unified Event Timeline' spec.
    """
    event_id: str = Field(..., description="Deterministic hash of source + id")
    event_type: str = Field(..., description="TRANSACTION, WATCH, LISTEN, RIDE, SOCIAL, NOTE, PREFERENCE, MOOD")
    source: str = Field(..., description="gmail, youtube_takeout, spotify, etc.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "drew"
    privacy_level: str = "MED" # LOW, MED, HIGH
    raw_ref: Optional[str] = None # Pointer to Vault object (e.g., gs://athena-vault/...)
    data: Dict[str, Any] = Field(default_factory=dict) # Event-specific payload
    derived: Dict[str, Any] = Field(default_factory=dict) # Computed features

    @classmethod
    def create_id(cls, source: str, source_item_id: str, timestamp: datetime) -> str:
        """
        Generate a deterministic event_id for deduplication.
        """
        # Ensure consistent string representation
        ts_str = timestamp.isoformat()
        payload = f"{source}:{source_item_id}:{ts_str}"
        return hashlib.sha256(payload.encode()).hexdigest()

    @field_validator('privacy_level')
    def validate_privacy(cls, v):
        allowed = {'LOW', 'MED', 'HIGH'}
        if v not in allowed:
            raise ValueError(f"Privacy must be one of {allowed}")
        return v
