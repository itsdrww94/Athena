"""
Athena Context Tags
====================
Automatic temporal and situational awareness for every interaction.

Tags help Athena understand:
- When you're talking to her (morning vs late night)
- What kind of day it is (weekday, weekend, payday)
- The interaction pattern (quick check vs deep convo)
"""

from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class ContextTags:
    """Container for all active context tags."""
    time_of_day: str  # morning, afternoon, evening, night, late_night
    day_type: str  # weekday, weekend
    day_name: str  # monday, tuesday, ...
    calendar_context: List[str]  # payday, first_of_month, end_of_month, holiday
    hour: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "time_of_day": self.time_of_day,
            "day_type": self.day_type,
            "day_name": self.day_name,
            "calendar_context": self.calendar_context,
            "hour": self.hour
        }
    
    def to_prompt_string(self) -> str:
        """Format for injection into LLM prompts."""
        cal_str = ", ".join(self.calendar_context) if self.calendar_context else "normal_day"
        return f"[Time: {self.time_of_day} ({self.hour}:00) | Day: {self.day_name} ({self.day_type}) | Context: {cal_str}]"


class ContextTagger:
    """
    Generates context tags based on current time and calendar.
    
    Usage:
        tagger = ContextTagger()
        tags = tagger.get_current_tags()
        print(tags.time_of_day)  # "evening"
    """
    
    # Configurable thresholds
    TIME_BLOCKS = {
        "late_night": (0, 5),    # 12 AM - 5 AM
        "morning": (5, 12),      # 5 AM - 12 PM
        "afternoon": (12, 17),   # 12 PM - 5 PM
        "evening": (17, 21),     # 5 PM - 9 PM
        "night": (21, 24),       # 9 PM - 12 AM
    }
    
    # User-specific paydays (can be configured)
    PAYDAY_DAYS = [1, 15]  # 1st and 15th of month (common bi-weekly)
    
    # US Federal Holidays (simplified - dates for 2024/2025)
    HOLIDAYS = {
        (1, 1): "new_years_day",
        (7, 4): "independence_day",
        (12, 25): "christmas_day",
        (12, 31): "new_years_eve",
        # Add more as needed
    }
    
    def __init__(self, payday_days: List[int] = None):
        if payday_days:
            self.PAYDAY_DAYS = payday_days
    
    def get_current_tags(self, at_time: datetime = None) -> ContextTags:
        """Generate context tags for the current (or specified) moment."""
        now = at_time or datetime.now()
        
        return ContextTags(
            time_of_day=self._get_time_of_day(now.hour),
            day_type=self._get_day_type(now),
            day_name=now.strftime("%A").lower(),
            calendar_context=self._get_calendar_context(now),
            hour=now.hour
        )
    
    def _get_time_of_day(self, hour: int) -> str:
        """Map hour to time-of-day label."""
        for label, (start, end) in self.TIME_BLOCKS.items():
            if start <= hour < end:
                return label
        return "night"  # Default fallback
    
    def _get_day_type(self, dt: datetime) -> str:
        """Weekday (0-4) vs Weekend (5-6)."""
        return "weekend" if dt.weekday() >= 5 else "weekday"
    
    def _get_calendar_context(self, dt: datetime) -> List[str]:
        """Generate calendar-based context tags."""
        tags = []
        day = dt.day
        month = dt.month
        
        # Payday check
        if day in self.PAYDAY_DAYS:
            tags.append("payday")
        
        # Position in month
        if day <= 3:
            tags.append("first_of_month")
        elif day >= 28:
            tags.append("end_of_month")
        
        # Holiday check
        holiday = self.HOLIDAYS.get((month, day))
        if holiday:
            tags.append(f"holiday_{holiday}")
        
        # Christmas week special handling
        if month == 12 and 24 <= day <= 26:
            tags.append("christmas_week")
        
        return tags
    
    def enrich_for_llm(self, user_input: str) -> Dict:
        """
        Prepare enriched context for the LLM/Router.
        
        Returns:
            {
                "original_input": str,
                "context_tags": ContextTags,
                "enriched_prompt": str  # Optional system hint
            }
        """
        tags = self.get_current_tags()
        
        # Generate a hint for the LLM based on context
        hint = self._generate_context_hint(tags)
        
        return {
            "original_input": user_input,
            "context_tags": tags,
            "context_hint": hint
        }
    
    def _generate_context_hint(self, tags: ContextTags) -> str:
        """Generate a natural language hint based on context."""
        hints = []
        
        # Time-based personality adjustments
        if tags.time_of_day == "late_night":
            hints.append("User is up late. Keep responses calming and concise.")
        elif tags.time_of_day == "morning":
            hints.append("Morning mode: Be energizing and action-oriented.")
        elif tags.time_of_day == "evening":
            hints.append("Evening wind-down: Be relaxed and reflective.")
        
        # Calendar-based
        if "payday" in tags.calendar_context:
            hints.append("It's payday! User might be thinking about finances.")
        if "end_of_month" in tags.calendar_context:
            hints.append("End of month approaching - budget awareness might be helpful.")
        if any("holiday" in t for t in tags.calendar_context):
            hints.append("Holiday context - be festive and understanding of relaxed mood.")
        
        # Weekend vs Weekday
        if tags.day_type == "weekend":
            hints.append("Weekend mode: User likely has more flexibility.")
        
        return " ".join(hints) if hints else ""


# Singleton accessor
_tagger_instance: Optional[ContextTagger] = None

def get_context_tagger() -> ContextTagger:
    global _tagger_instance
    if _tagger_instance is None:
        _tagger_instance = ContextTagger()
    return _tagger_instance
