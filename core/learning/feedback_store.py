"""
Athena Feedback Store
======================
Stores routing decisions and user feedback for learning.

Logs:
- Intent classifications
- User corrections (fb_win, fb_spiral, fb_bad)
- "Why?" explanations

This data can be used to improve routing accuracy over time.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger("athena.feedback")

FEEDBACK_FILE = Path(__file__).parent.parent.parent / "brain" / "feedback_log.jsonl"

@dataclass
class FeedbackEntry:
    """A logged routing decision with optional feedback."""
    timestamp: str
    surface: str  # "terminal" or "telegram"
    user_input: str
    detected_intent: str
    confidence: float
    slots: Dict[str, Any]
    reasoning: str
    # Feedback (added later)
    feedback: Optional[str] = None  # "win", "spiral", "bad", None
    correction: Optional[str] = None  # User's correction if provided
    

class FeedbackStore:
    """
    Persistent log of routing decisions and feedback.
    
    Usage:
        store = FeedbackStore()
        entry_id = store.log_decision(...)
        store.add_feedback(entry_id, "win")
    """
    
    def __init__(self):
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def log_decision(
        self,
        surface: str,
        user_input: str,
        intent: str,
        confidence: float,
        slots: Dict[str, Any],
        reasoning: str = ""
    ) -> str:
        """Log a routing decision. Returns entry ID."""
        entry = FeedbackEntry(
            timestamp=datetime.now().isoformat(),
            surface=surface,
            user_input=user_input,
            detected_intent=intent,
            confidence=confidence,
            slots=slots,
            reasoning=reasoning
        )
        
        try:
            with open(FEEDBACK_FILE, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
        
        # ID is timestamp for simplicity
        return entry.timestamp
    
    def add_feedback(self, entry_timestamp: str, feedback: str, correction: str = None):
        """Add feedback to an existing entry."""
        # Read all entries
        entries = self._read_all()
        
        # Find and update
        for entry in entries:
            if entry.get("timestamp") == entry_timestamp:
                entry["feedback"] = feedback
                if correction:
                    entry["correction"] = correction
                break
        
        # Rewrite (not efficient but simple for this use case)
        try:
            with open(FEEDBACK_FILE, "w") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to update feedback: {e}")
    
    def _read_all(self) -> List[Dict]:
        """Read all entries from the log."""
        if not FEEDBACK_FILE.exists():
            return []
        
        entries = []
        try:
            with open(FEEDBACK_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read feedback log: {e}")
        
        return entries
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Get recent entries."""
        entries = self._read_all()
        return entries[-limit:]
    
    def get_feedback_summary(self) -> Dict[str, int]:
        """Get counts of feedback types."""
        entries = self._read_all()
        summary = {"win": 0, "spiral": 0, "bad": 0, "none": 0}
        for entry in entries:
            fb = entry.get("feedback")
            if fb in summary:
                summary[fb] += 1
            else:
                summary["none"] += 1
        return summary
    
    def get_low_confidence_intents(self) -> List[Dict]:
        """Get entries with low confidence for review."""
        entries = self._read_all()
        return [e for e in entries if e.get("confidence", 1.0) < 0.6]
    
    def get_corrections(self) -> List[Dict]:
        """Get entries with user corrections."""
        entries = self._read_all()
        return [e for e in entries if e.get("correction")]


# Singleton accessor
_store_instance: Optional[FeedbackStore] = None

def get_feedback_store() -> FeedbackStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = FeedbackStore()
    return _store_instance
