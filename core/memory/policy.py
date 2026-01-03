from typing import Any, Dict
from collections import defaultdict
from datetime import datetime, timedelta

class MemoryWritePolicy:
    """
    Decides when to promote a piece of information to Semantic Memory.
    
    Triggers "Save This?" when:
    1. User explicitly marks a preference tag
    2. User repeats the same preference 2+ times in a session
    3. User uses strong language ("always", "love", "hate", "prefer")
    """
    
    # Track repeated preferences per session (in-memory)
    _preference_counts: Dict[str, int] = defaultdict(int)
    _last_reset: datetime = datetime.now()
    
    # Keywords that indicate a stable preference
    STRONG_WORDS = ["always", "never", "hate", "love", "prefer", "favorite", "dislike"]
    
    @classmethod
    def _maybe_reset(cls):
        """Reset counts after 24h."""
        if datetime.now() - cls._last_reset > timedelta(hours=24):
            cls._preference_counts.clear()
            cls._last_reset = datetime.now()
    
    @classmethod 
    def track_preference(cls, key: str, value: str):
        """Call after each task completion to track recurring preferences."""
        cls._maybe_reset()
        pref_key = f"{key}:{value}"
        cls._preference_counts[pref_key] += 1
        
    @classmethod
    def get_count(cls, key: str, value: str) -> int:
        cls._maybe_reset()
        return cls._preference_counts.get(f"{key}:{value}", 0)
    
    @staticmethod
    def should_propose_save(intent: str, slots: Dict[str, Any], raw_text: str = "") -> bool:
        """
        Determine if we should ask the user "Save this as a preference?".
        """
        # 1. Skip purely episodic intents
        if intent in ["capture_note", "log_watch", "general_chat"]:
            return False
            
        # 2. Check for explicit tag
        if slots.get("tag") == "preference":
            return True
            
        # 3. Check for strong preference language
        lower_text = raw_text.lower() if raw_text else ""
        if any(word in lower_text for word in MemoryWritePolicy.STRONG_WORDS):
            return True
            
        # 4. Check repetition count (requires prior tracking)
        for key, value in slots.items():
            if MemoryWritePolicy.get_count(key, str(value)) >= 2:
                return True
            
        return False

    @staticmethod
    def format_proposal(slots: Dict[str, Any]) -> str:
        """Draft the text for the memory."""
        items = ", ".join([f"{k}={v}" for k, v in slots.items()])
        return f"💾 Save preference: {items}?"

