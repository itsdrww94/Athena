"""
Financial Advisor: Plan Engine
==============================
Planning Component.
Handles: Goals, Sinking Funds, Timelines.
"""

from typing import Dict, List, Any
import math

class PlanEngine:
    def evaluate_goal(self, goal_name: str, target_amount: float, monthly_surplus: float) -> List[str]:
        """
        Calculate timeline for a goal.
        """
        if monthly_surplus <= 0:
            return [f"Cannot plan for '{goal_name}' - No monthly surplus available."]
        
        months = math.ceil(target_amount / monthly_surplus)
        
        recommendations = [
            f"Goal: {goal_name} (${target_amount})",
            f"Timeline: ~{months} months at ${monthly_surplus}/mo",
            f"Suggestion: Set up a sinking fund transfer of ${monthly_surplus} on the 1st."
        ]
        return recommendations

def get_plan_engine():
    return PlanEngine()
