from typing import Dict, Any, List
from pydantic import BaseModel

class ModeScore(BaseModel):
    mode: str
    score: float # 0.0 to 1.0
    contributors: List[str] # Why this score?

class ModeCalculator:
    """
    The 'State of Mind' Quantifier.
    Computes daily modes based on behavioral signals.
    """
    
    @staticmethod
    def compute_modes(signals: Dict[str, Any]) -> List[ModeScore]:
        """
        Input: Dictionary of derived features (e.g., late_night_minutes, spend_velocity).
        Output: List of active ModeScores.
        """
        modes = []
        
        # 1. Autopilot Mode (Passive consumption)
        # Signals: High late night watch time, high topic jumping (volatility)
        late_night = signals.get("late_night_minutes", 0)
        volatility = signals.get("topic_volatility", 0)
        
        autopilot_score = 0.0
        reasons = []
        
        if late_night > 60:
            autopilot_score += 0.5
            reasons.append("High late-night watch time")
        if volatility > 5: # Arbitrary threshold for topic jumping
            autopilot_score += 0.3
            reasons.append("High topic volatility")
            
        if autopilot_score > 0:
            modes.append(ModeScore(mode="AUTOPILOT", score=min(autopilot_score, 1.0), contributors=reasons))

        # 2. Spiral Mode (Risk)
        # Signals: High Spend Velocity + Autopilot
        spend_vel = signals.get("spend_velocity_7d", 0)
        baseline_spend = signals.get("baseline_spend", 100) # Default
        
        spiral_score = 0.0
        spiral_reasons = []
        
        if autopilot_score > 0.4:
            spiral_score += 0.3
            spiral_reasons.append("Autopilot detected")
            
        if baseline_spend > 0 and (spend_vel / baseline_spend) > 1.5:
            spiral_score += 0.5
            spiral_reasons.append("Spend spike detected")
            
        if spiral_score > 0:
            modes.append(ModeScore(mode="SPIRAL_RISK", score=min(spiral_score, 1.0), contributors=spiral_reasons))
            
        # 3. Focus Mode (The Goal)
        # Signals: Low phone usage (missing here), intentional sessions
        # For now, inverse of Autopilot
        focus_score = 1.0 - autopilot_score
        if focus_score > 0.6:
            modes.append(ModeScore(mode="FOCUS", score=focus_score, contributors=["Low distraction signals"]))
            
        # Sort by score desc
        modes.sort(key=lambda x: x.score, reverse=True)
        return modes
