"""
Calendar Helper
================
Parses natural language dates/times for calendar integration.

Examples:
- "tomorrow at noon" → datetime
- "next Monday 3pm" → datetime
- "in 2 hours" → datetime
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Day name to weekday number
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

# Time shortcuts
TIME_SHORTCUTS = {
    "noon": (12, 0),
    "midnight": (0, 0),
    "morning": (9, 0),
    "afternoon": (14, 0),
    "evening": (18, 0),
    "night": (20, 0)
}


def parse_natural_datetime(text: str, reference: datetime = None) -> Tuple[Optional[datetime], int]:
    """
    Parse natural language into a datetime.
    
    Args:
        text: Natural language like "tomorrow at 3pm"
        reference: Reference point (defaults to now)
        
    Returns:
        Tuple of (datetime or None, duration_minutes)
    """
    ref = reference or datetime.now()
    text = text.lower().strip()
    duration = 60  # Default 1 hour
    
    result_date = None
    result_time = None
    
    # 1. Parse relative days
    if "today" in text:
        result_date = ref.date()
    elif "tomorrow" in text:
        result_date = (ref + timedelta(days=1)).date()
    elif "day after tomorrow" in text:
        result_date = (ref + timedelta(days=2)).date()
    elif "next week" in text:
        result_date = (ref + timedelta(weeks=1)).date()
    
    # 2. Parse weekday names
    for day_name, day_num in WEEKDAYS.items():
        if day_name in text:
            days_ahead = day_num - ref.weekday()
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            if "next" in text:
                days_ahead += 7
            result_date = (ref + timedelta(days=days_ahead)).date()
            break
    
    # 3. Parse time shortcuts
    for shortcut, (hour, minute) in TIME_SHORTCUTS.items():
        if shortcut in text:
            result_time = (hour, minute)
            break
    
    # 4. Parse explicit times (e.g., "3pm", "15:00", "3:30 pm")
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)
        
        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
            
        result_time = (hour, minute)
    
    # 5. Parse "in X hours/minutes"
    in_match = re.search(r'in\s+(\d+)\s+(hour|minute|min|hr)s?', text)
    if in_match:
        amount = int(in_match.group(1))
        unit = in_match.group(2)
        if unit in ["hour", "hr"]:
            result_date = ref.date()
            result_time = ((ref + timedelta(hours=amount)).hour, ref.minute)
        elif unit in ["minute", "min"]:
            result_date = ref.date()
            full_dt = ref + timedelta(minutes=amount)
            result_time = (full_dt.hour, full_dt.minute)
    
    # 6. Parse duration ("for 2 hours", "30 minutes")
    dur_match = re.search(r'(?:for\s+)?(\d+)\s*(hour|hr|minute|min)s?', text)
    if dur_match:
        amount = int(dur_match.group(1))
        unit = dur_match.group(2)
        if unit in ["hour", "hr"]:
            duration = amount * 60
        elif unit in ["minute", "min"]:
            duration = amount
    
    # Combine date and time
    if result_date is None:
        result_date = ref.date()
    if result_time is None:
        # Default to next hour
        result_time = (ref.hour + 1, 0)
    
    try:
        final_dt = datetime.combine(result_date, datetime.min.time().replace(
            hour=result_time[0], 
            minute=result_time[1]
        ))
        return final_dt, duration
    except Exception:
        return None, duration


def format_event_confirmation(title: str, start: datetime, duration: int) -> str:
    """Format a nice confirmation message."""
    end = start + timedelta(minutes=duration)
    date_str = start.strftime("%A, %B %d")
    time_str = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
    
    return f"📅 **{title}**\n{date_str}\n{time_str}"
