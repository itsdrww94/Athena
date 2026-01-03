"""
Athena Proactive Nudges
========================
Time-based and pattern-based nudges that Athena sends first.

Features:
- Morning briefing (8 AM weekdays)
- Payday reminders (1st/15th)
- End of month budget check
- Pattern anomaly alerts
"""

import logging
from datetime import datetime, time
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("athena.nudges")

@dataclass
class ScheduledNudge:
    """A nudge scheduled to fire at specific times/conditions."""
    id: str
    name: str
    message: str
    trigger_time: Optional[time] = None  # Specific time of day
    trigger_days: List[int] = field(default_factory=list)  # 0=Mon, 6=Sun
    trigger_dates: List[int] = field(default_factory=list)  # Day of month (1-31)
    cooldown_hours: int = 24  # Don't repeat for this long
    last_fired: Optional[datetime] = None
    enabled: bool = True
    
    def should_fire(self, now: datetime) -> bool:
        """Check if this nudge should fire right now."""
        if not self.enabled:
            return False
            
        # Check cooldown
        if self.last_fired:
            hours_since = (now - self.last_fired).total_seconds() / 3600
            if hours_since < self.cooldown_hours:
                return False
        
        # Check time window (within 5 minutes of trigger)
        if self.trigger_time:
            current_time = now.time()
            trigger_minutes = self.trigger_time.hour * 60 + self.trigger_time.minute
            current_minutes = current_time.hour * 60 + current_time.minute
            if abs(current_minutes - trigger_minutes) > 5:
                return False
        
        # Check day of week
        if self.trigger_days and now.weekday() not in self.trigger_days:
            return False
            
        # Check day of month
        if self.trigger_dates and now.day not in self.trigger_dates:
            return False
            
        return True


class ProactiveNudgeEngine:
    """
    Manages and dispatches proactive nudges.
    
    Usage:
        engine = ProactiveNudgeEngine()
        nudge = engine.check_pending()
        if nudge:
            telegram.send_text(nudge["message"])
    """
    
    # Default nudge catalog
    DEFAULT_NUDGES = [
        ScheduledNudge(
            id="morning_briefing",
            name="Morning Briefing",
            message="☀️ Good morning! Ready for your daily briefing?\n\nReply 'brief' for news, calendar, and patterns.",
            trigger_time=time(8, 0),
            trigger_days=[0, 1, 2, 3, 4],  # Mon-Fri
            cooldown_hours=20
        ),
        ScheduledNudge(
            id="payday_check",
            name="Payday Reminder",
            message="💰 It's payday! Want me to check your recent transactions and budget status?\n\nReply 'finance' for a full report.",
            trigger_time=time(10, 0),
            trigger_dates=[1, 15],
            cooldown_hours=24
        ),
        ScheduledNudge(
            id="end_of_month",
            name="End of Month Budget",
            message="📊 End of month approaching! Should I prepare your spending summary?\n\nReply 'budget' for the report.",
            trigger_time=time(18, 0),
            trigger_dates=[28, 29, 30],
            cooldown_hours=48
        ),
        ScheduledNudge(
            id="weekend_reflection",
            name="Weekend Reflection",
            message="🌅 Happy weekend! Anything you'd like to capture or plan for next week?\n\nReply with your thoughts.",
            trigger_time=time(10, 0),
            trigger_days=[5],  # Saturday
            cooldown_hours=48
        ),
    ]
    
    def __init__(self):
        self.nudges: List[ScheduledNudge] = list(self.DEFAULT_NUDGES)
        self._load_state()
    
    def _get_state_path(self):
        from pathlib import Path
        return Path(__file__).parent.parent.parent / "brain" / "nudge_state.json"
    
    def _load_state(self):
        """Load last_fired times from disk."""
        import json
        path = self._get_state_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    state = json.load(f)
                for nudge in self.nudges:
                    if nudge.id in state:
                        nudge.last_fired = datetime.fromisoformat(state[nudge.id])
            except Exception as e:
                logger.warning(f"Failed to load nudge state: {e}")
    
    def _save_state(self):
        """Save last_fired times to disk."""
        import json
        path = self._get_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            state = {n.id: n.last_fired.isoformat() for n in self.nudges if n.last_fired}
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save nudge state: {e}")
    
    def check_pending(self) -> Optional[Dict]:
        """
        Check if any nudge should fire right now.
        Returns the nudge payload or None.
        """
        now = datetime.now()
        
        for nudge in self.nudges:
            if nudge.should_fire(now):
                nudge.last_fired = now
                self._save_state()
                
                return {
                    "id": nudge.id,
                    "name": nudge.name,
                    "message": nudge.message,
                    "type": "PROACTIVE_NUDGE"
                }
        
        return None
    
    def add_custom_nudge(self, nudge: ScheduledNudge):
        """Add a custom nudge to the schedule."""
        self.nudges.append(nudge)
    
    def disable_nudge(self, nudge_id: str):
        """Disable a nudge by ID."""
        for nudge in self.nudges:
            if nudge.id == nudge_id:
                nudge.enabled = False
                break
    
    def get_all_nudges(self) -> List[Dict]:
        """Get status of all nudges."""
        return [
            {
                "id": n.id,
                "name": n.name,
                "enabled": n.enabled,
                "last_fired": n.last_fired.isoformat() if n.last_fired else None
            }
            for n in self.nudges
        ]


# Singleton accessor
_engine_instance: Optional[ProactiveNudgeEngine] = None

def get_proactive_engine() -> ProactiveNudgeEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ProactiveNudgeEngine()
    return _engine_instance
