import logging
import random
from typing import List, Optional, Dict
from datetime import datetime
from core.pattern_engine.modes import ModeScore

logger = logging.getLogger("athena.interventions")

class InterventionEngine:
    """
    Routine Coach.
    Decides IF and WHAT to nudge based on Modes.
    """
    
    CATALOG = {
        "AUTOPILOT": [
            "Intentional Watch Timer: Set a 20m timer?",
            "Pattern Check: You've jumped topics 3 times. Seeking something specific?",
            "Hydration Check: Drink water before next video."
        ],
        "SPIRAL_RISK": [
            "Circuit Breaker: Stop spending for 24h?",
            "Reflection Prompt: What triggered this session?",
            "Walk Suggestion: 5 min fresh air."
        ],
        "FOCUS": [
            "Momentum Keeper: Great streak. Keep going.",
            "Deep Work Timer: 45m sprint?"
        ]
    }
    
    def __init__(self):
        self.last_intervention_time = None
        self.cooldown_minutes = 60 # Don't annoy the user
        
    def generate_nudge(self, modes: List[ModeScore]) -> Optional[Dict[str, str]]:
        """
        Returns a Nudge payload or None.
        """
        # 1. Check Cooldown
        if self._is_cooling_down():
            return None
            
        # 2. Select Highest Priority Mode
        if not modes:
            return None
            
        primary_mode = modes[0]
        
        # Only nudge if score is high enough
        if primary_mode.score < 0.6:
            return None
            
        # 3. Select Nudge
        possible_nudges = self.CATALOG.get(primary_mode.mode, [])
        if not possible_nudges:
            return None
            
        selected_nudge = random.choice(possible_nudges)
        
        self.last_intervention_time = datetime.now()
        
        return {
            "type": "NUDGE",
            "mode": primary_mode.mode,
            "message": selected_nudge,
            "reason": f"Detected {primary_mode.mode} ({primary_mode.score:.2f})"
        }

    def _is_cooling_down(self) -> bool:
        if not self.last_intervention_time:
            return False
        delta = (datetime.now() - self.last_intervention_time).total_seconds() / 60
        return delta < self.cooldown_minutes
