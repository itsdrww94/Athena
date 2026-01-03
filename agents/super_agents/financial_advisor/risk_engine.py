"""
Financial Advisor: Risk Engine
==============================
Decision Layer.
Returns APPROVE / WARN / BLOCK based on constraints.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RiskDecision:
    verdict: str # APPROVE, WARN, BLOCK
    reason: str
    risk_level: str # low, med, high

class RiskEngine:
    def evaluate_purchase(self, amount: float, category: str, budget_remaining: float, hard_caps: Dict[str, float] = None) -> RiskDecision:
        """
        Evaluate a purchase against budgets and risk.
        """
        # 1. HARD BLOCK: Bill Risk (Simulated)
        if category == "Discretionary" and budget_remaining < amount:
             # Check if this cuts into bill money (Mock)
             pass
             
        # 2. HARD BLOCK: Hard Cap
        if hard_caps and category in hard_caps:
             if amount > hard_caps[category]:
                 return RiskDecision("BLOCK", f"Exceeds hard cap of ${hard_caps[category]}", "high")

        # 3. LOGIC
        if amount > budget_remaining * 1.5:
            return RiskDecision("BLOCK", f"Significantly exceeds budget (${budget_remaining}).", "high")
            
        elif amount > budget_remaining:
            return RiskDecision("WARN", f"Over budget by ${amount - budget_remaining:.2f}.", "med")
            
        else:
            return RiskDecision("APPROVE", "Safe to spend.", "low")

def get_risk_engine():
    return RiskEngine()
