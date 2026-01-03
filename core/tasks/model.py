import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Enums ---
class TaskStatus:
    DRAFT = "DRAFT"         # Collecting info
    READY = "READY"         # Ready to execute (waiting for confirm)
    RUNNING = "RUNNING"     # Agent executing
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"

class TaskMode:
    DRAFT = "DRAFT"         # Safety on
    EXECUTE = "EXECUTE"     # Safety off

# --- Intent Schema ---
class IntentSchema(BaseModel):
    name: str                   # e.g. "schedule_event"
    description: str
    required_slots: List[str]   # e.g. ["what", "when"]
    optional_slots: List[str]   # e.g. ["location", "duration"]
    actions: List[str]          # Actions this intent triggers (e.g. "calendar.create")

# --- Task Object ---
class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    intent: str                 # The detected intent name
    slots: Dict[str, Any] = {}  # Extracted values {"when": "tomorrow"}
    assumptions: Dict[str, Any] = {} # Inferred values {"when": "2025-12-26"}
    
    status: str = TaskStatus.DRAFT
    mode: str = TaskMode.DRAFT
    
    confidence: float = 0.0
    risk_level: str = "LOW"     # LOW, MED, HIGH
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_missing_slots(self, schema: IntentSchema) -> List[str]:
        """Return list of required slots that are empty."""
        return [slot for slot in schema.required_slots if slot not in self.slots]

    def is_ready(self, schema: IntentSchema) -> bool:
        return len(self.get_missing_slots(schema)) == 0
