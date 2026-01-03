#!/usr/bin/env python3
"""
Impulse Shield Agent
====================
"The Brake"
Reduce impulsive spending and decision fatigue.

Scientist Job: Detect risk state -> Intervene if needed.
Ref: 5. Impulse Shield Agent
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Schema (Mocking for standalone script if needed, but assuming avail)
try:
    from services.athena_schemas import AgentOutput, AthenaEvent
except ImportError:
    # Fallback for standalone dev
    class AgentOutput:
        def __init__(self): 
            self.observations = []
            self.recommendations = []
            self.events_to_log = []
            self.proposed_memory_updates = []
        def add_observation(self, t): self.observations.append(t)
        def add_recommendation(self, t): self.recommendations.append(t)
    class AthenaEvent:
        pass

def assess_risk(context, request_type):
    """
    Logic Ref:
    - high risk -> enforce cooldown
    - med risk -> nudge + cap
    - low risk -> normal flow
    """
    # Simple prototype logic
    risk_state = "low"
    
    # Check if late night (fake time for now, real implementation uses system time)
    hour = datetime.now().hour
    if hour > 22 or hour < 5:
        risk_state = "high"
    
    # Check finance context (stubbed)
    if context.get("over_budget", False):
        risk_state = "high"
        
    return risk_state

def main():
    parser = argparse.ArgumentParser(description="Athena Impulse Shield")
    parser.add_argument("--context", required=False, help="JSON Context Capsule")
    parser.add_argument("--request", required=True, help="User request or item to buy")
    parser.add_argument("--price", type=float, default=0.0, help="Price of item")
    
    args = parser.parse_args()
    
    # Parse capsule
    try:
        capsule = json.loads(args.context) if args.context else {}
    except:
        capsule = {}
        
    output = AgentOutput()
    
    # 1. Assess Risk
    risk = assess_risk(capsule, "purchase")
    output.add_observation(f"Current Impulse Risk State: {risk.upper()}")
    
    # 2. Apply Rules (Ref: 5.Logic requirements)
    if risk == "high":
        if args.price > 20: # Example threshold
            output.add_recommendation("🛑 BLOCKED: High impulse risk detected.")
            output.add_recommendation(f"Action: 24-hour cooldown initiated for '{args.request}'.")
            output.add_recommendation("Suggestion: Add to Wishlist instead.")
        else:
             output.add_recommendation("⚠️ CAUTION: Proceed with care. Late night spend.")
             
    elif risk == "medium":
        if args.price > 50:
            output.add_recommendation("Thinking Break: Do you really need this today?")
        else:
            output.add_recommendation("Approved: Within limits.")
            
    else: # Low
        output.add_recommendation("Approved: Standard flow.")

    # Print Result Envelope (for Hub to parse)
    print("START_ENVELOPE")
    result = {
        "observations": output.observations,
        "recommendations": output.recommendations,
        "risk_state": risk
    }
    print(json.dumps(result, indent=2))
    print("END_ENVELOPE")

if __name__ == "__main__":
    main()
