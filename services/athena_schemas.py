"""
Athena Schemas (v2.0)
=====================
Strict definitions for the Hub-and-Spoke architecture.
"Contract-driven I/O"

Build Order Ref: 0.C (Contract-driven I/O)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

# =============================================================================
# 1. CONTEXT CAPSULE
# =============================================================================

@dataclass
class ContextCapsule:
    """
    Minimal personalized context sent to agents.
    Ref: 1.A (Capsule contents)
    """
    task_goal: str
    relevant_preferences: Dict[str, Any]
    relevant_constraints: Dict[str, Any]
    recent_trends: List[str]
    do_not_use: List[str] = field(default_factory=lambda: ["exact_address", "raw_messages", "health_data"])
    tone_profile: str = "direct"
    domain: str = "general"
    
    def to_json(self) -> str:
        import json
        return json.dumps(self.__dict__, default=str)

# =============================================================================
# 2. EVENTS
# =============================================================================

@dataclass
class AthenaEvent:
    """
    Normalized event for the Pattern Engine.
    Ref: 2.A (Event schema)
    """
    type: str  # watch, purchase, ride, search, sleep, recommendation, task_result
    domain: str  # movies, finance, health, events, deals, pets, system, news
    value: Any  # number or structured value
    source: str  # agent_name or platform
    
    # Optional / Auto-filled
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    time_bucket: str = field(default_factory=lambda: datetime.now().strftime("%Y-%W")) # Weekly bucket default
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    sensitivity: str = "low" # low, med, high
    evidence_ref: Optional[str] = None # Pointer to Vault
    user_ref: str = "Drew"
    timestamp: datetime = field(default_factory=datetime.now)

    def generate_dedupe_key(self) -> str:
        """Generate stable fingerprint. Ref: 3.A"""
        # Simple fingerprint: type + domain + value_str + day_bucket
        val_str = str(self.value)[:50]
        day = self.timestamp.strftime("%Y-%m-%d")
        return f"{self.type}|{self.domain}|{val_str}|{day}"

# =============================================================================
# 3. AGENT OUTPUT ENVELOPE
# =============================================================================

@dataclass
class AgentOutput:
    """
    Standard envelope for all agent results.
    Ref: 0.C (Contract-driven I/O)
    """
    observations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    events_to_log: List[AthenaEvent] = field(default_factory=list)
    proposed_memory_updates: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 1.0
    sensitivity_flag: str = "low"
    
    def add_observation(self, text: str):
        self.observations.append(text)
        
    def add_recommendation(self, text: str):
        self.recommendations.append(text)
        
    def log_event(self, event: AthenaEvent):
        self.events_to_log.append(event)
        
    def suggest_memory(self, type_: str, statement: str, category: str = "preference"):
        self.proposed_memory_updates.append({
            "type": type_, # add, update, expire
            "statement": statement,
            "category": category
        })
