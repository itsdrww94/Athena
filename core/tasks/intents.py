from typing import Dict
from core.tasks.model import IntentSchema

class IntentRegistry:
    """
    Registry of all known skills/intents and their slot requirements.
    """
    
    _REGISTRY: Dict[str, IntentSchema] = {
        
        # 1. Capture / Memory
        "capture_note": IntentSchema(
            name="capture_note",
            description="Save a thought, idea, or link.",
            required_slots=["content"],
            optional_slots=["tag", "priority"],
            actions=["notion.create_page"]
        ),
        
        # 2. Research
        "search_web": IntentSchema(
            name="search_web",
            description="Research a topic.",
            required_slots=["query"],
            optional_slots=["depth"],
            actions=["browser.search"]
        ),
        
        # 3. Calendar
        "schedule_event": IntentSchema(
            name="schedule_event",
            description="Add event to calendar.",
            required_slots=["title", "when"],
            optional_slots=["location", "duration"],
            actions=["calendar.create"]
        ),
        
        # 4. Finance
        "analyze_finance": IntentSchema(
            name="analyze_finance",
            description="Check spending or analyze budget.",
            required_slots=[], # Open ended
            optional_slots=["category", "period"],
            actions=["finance.report"]
        ),
        
        # 5. Media
        "log_watch": IntentSchema(
            name="log_watch",
            description="Log a movie or show watched.",
            required_slots=["title"],
            optional_slots=["rating", "review"],
            actions=["media.log"]
        )
    }
    
    @classmethod
    def get(cls, name: str) -> IntentSchema:
        return cls._REGISTRY.get(name)
    
    @classmethod
    def list_intents(cls):
        return list(cls._REGISTRY.values())
