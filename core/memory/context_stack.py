import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Entity(BaseModel):
    type: str  # LOC, TIME, DATE, PERSON
    value: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatState(BaseModel):
    chat_id: str
    active_task_id: Optional[str] = None
    active_intent: Optional[str] = None
    entities: List[Entity] = []
    # Sticky Results (e.g. search list)
    last_result_set: Optional[Dict[str, Any]] = None # {type: 'email_list', items: [...], surface: 'terminal'}
    updated_at: datetime = Field(default_factory=datetime.now)

class ContextStack:
    """
    Manages the active context for a user/chat.
    Resolves pronouns ("there", "at 8") and references ("#5", "that email").
    
    IMPORTANT: References are surface-locked. Terminal references won't pull 
    from Telegram history and vice versa. This prevents cross-surface context bleed.
    """
    
    def __init__(self):
        # In-memory assumption for CLI. In prod, use Supabase `context_state`
        self._states: Dict[str, ChatState] = {}
        self._active_surface: str = "terminal"  # Current surface (terminal/telegram)
        
    @property
    def active_surface(self) -> str:
        return self._active_surface
    
    def set_active_surface(self, surface: str):
        """Set the current active surface (terminal/telegram)."""
        if surface in ["terminal", "telegram"]:
            self._active_surface = surface
        
    def get_state(self, chat_id: str) -> ChatState:
        if chat_id not in self._states:
            self._states[chat_id] = ChatState(chat_id=chat_id)
        return self._states[chat_id]
        
    def push_entity(self, chat_id: str, type: str, value: str):
        state = self.get_state(chat_id)
        # Add new entity to front
        state.entities.insert(0, Entity(type=type, value=value))
        # Keep only last 20
        state.entities = state.entities[:20]
        state.updated_at = datetime.now()
        
    def push_result_set(self, chat_id: str, result_type: str, items: List[Any], surface: str = "terminal"):
        """Store a numbered list result for future reference."""
        state = self.get_state(chat_id)
        state.last_result_set = {
            "type": result_type,
            "items": items,
            "surface": surface,
            "timestamp": datetime.now().isoformat()
        }
        
    def resolve_reference(self, chat_id: str, text: str) -> Optional[Any]:
        """
        Resolve '#5', 'that email', 'the second one'.
        Returns the actual item object or None.
        
        IMPORTANT: Surface-locked - only resolves references from current surface.
        Terminal won't pull from Telegram history and vice versa.
        """
        state = self.get_state(chat_id)
        if not state.last_result_set:
            return None
        
        # SURFACE LOCK: Only use result sets from the current active surface
        result_surface = state.last_result_set.get("surface", "terminal")
        if result_surface != self._active_surface:
            # Cross-surface retrieval blocked - don't pull Telegram history from terminal
            return None
            
        items = state.last_result_set.get("items", [])
        if not items:
            return None
            
        # 1. Numbered Reference ("#5", "number 5", "5")
        import re
        # Match #5, No. 5, Number 5
        match = re.search(r'(?:#|no\.?|number)\s*(\d+)', text, re.IGNORECASE)
        if match:
            idx = int(match.group(1)) - 1 # 1-based to 0-based
            if 0 <= idx < len(items):
                return items[idx]
        
        # 2. Ordinal Reference ("second one", "first email")
        ordinals = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
        for word, idx in ordinals.items():
            if word in text.lower():
                if 0 <= idx < len(items):
                    return items[idx]
                    
        # 3. "That [type]" -> Last item or Result Set itself
        type_singular = state.last_result_set.get("type", "").rstrip('s') # emails -> email
        if f"that {type_singular}" in text.lower() or "the email" in text.lower():
             # If just one item, return it. If list, maybe return the last accessed? 
             # For now, return the whole list context if needed, or None if ambiguous.
             pass
             
        return None

    def get_recent_entity(self, chat_id: str, type: str, max_age_minutes: int = 15) -> Optional[str]:
        """Find most recent entity of type within time window."""
        state = self.get_state(chat_id)
        now = datetime.now()
        
        for e in state.entities:
            if e.type == type:
                age = (now - e.timestamp).total_seconds() / 60
                if age <= max_age_minutes:
                    return e.value
        return None
        
    def resolve_slots(self, chat_id: str, slots: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Fill missing slots using Context Stack.
        e.g. if 'location' is missing, check if user said "there" or implies it.
        """
        assumptions = {}
        
        # Resolve References first
        ref_obj = self.resolve_reference(chat_id, text)
        if ref_obj:
            # Inject reference data into assumptions
            assumptions["reference_context"] = ref_obj
            # If the task needs a query or id, we might pull it from here
            if "snippet" in ref_obj:
                 assumptions["implied_content"] = ref_obj.get("snippet")
            if "id" in ref_obj:
                 assumptions["reference_id"] = ref_obj.get("id")

        # 1. Location Carry-Forward
        if "location" not in slots:
            # Explicit trigger phrases
            triggers = ["there", "that place", "same place"]
            if any(t in text.lower() for t in triggers):
                loc = self.get_recent_entity(chat_id, "LOC", max_age_minutes=120)
                if loc:
                    assumptions["location"] = loc
                    slots["location"] = loc # Auto-fill? Or just mark assumption?
                    
        # 2. Date Carry-Forward
        if "date" not in slots:
            if "tomorrow" in text.lower():
                # Simple heuristic
                pass 
            elif "same time" in text.lower():
                 # TODO: Time carry forward
                 pass
                 
        return assumptions
