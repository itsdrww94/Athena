#!/usr/bin/env python3
"""
Life Ops Agent
==============
"The Quarterback"
Daily/Weekly execution planning.

Scientist Job: Goals + Constraints -> Action Plan.
Ref: 6. Life Ops Agent
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Fallback output class if schema not ready
try:
    from services.athena_schemas import AgentOutput
except ImportError:
    class AgentOutput:
        def __init__(self): 
            self.observations = []
            self.recommendations = []
            
def determine_mode(context):
    """
    Ref: 6. Logic requirements (Modes)
    Focus / Chill / Planner
    """
    trends = context.get("recent_trends", [])
    # Prototype logic
    if "sleep_low" in trends:
        return "chill"
    
    day = datetime.now().weekday()
    if day == 0: # Monday
        return "planner"
    elif day in [4, 5]: # Fri/Sat
        return "chill"
    else:
        return "focus"

def main():
    parser = argparse.ArgumentParser(description="Athena Life Ops")
    parser.add_argument("--context", required=False, help="JSON Context Capsule")
    
    args = parser.parse_args()
    
    try:
        capsule = json.loads(args.context) if args.context else {}
    except:
        capsule = {}
        
    output = AgentOutput()
    
    # 1. Determine Mode
    mode = determine_mode(capsule)
    output.add_observation(f"Current OPS Mode: {mode.upper()}")
    
    # 2. Generate Plan (Ref: 6. Outputs)
    plan = []
    
    if mode == "focus":
        plan = [
            "1. [Deep Work] 2 hours - Core Project",
            "2. [Admin] 30 mins - Email clearing",
            "3. [Health] Workout"
        ]
        output.add_recommendation("Strategy: 3 Big Tasks Max.")
        
    elif mode == "chill":
        plan = [
            "1. [Recovery] Light reading / Walk",
            "2. [Social] Check events",
            "3. [Hobby] Movie or Gaming"
        ]
        output.add_recommendation("Strategy: Recover social battery.")
        
    elif mode == "planner":
        plan = [
            "1. [Finance] Budget Review",
            "2. [Food] Meal Prep Planning",
            "3. [Schedule] Week Ahead"
        ]
        output.add_recommendation("Strategy: Set the week up.")
        
    # Add Plan
    output.add_recommendation("DAILY PLAN:")
    for task in plan:
        output.add_recommendation(task)

    # Print Result Envelope
    print("START_ENVELOPE")
    result = {
        "observations": output.observations,
        "recommendations": output.recommendations,
        "mode": mode
    }
    print(json.dumps(result, indent=2))
    print("END_ENVELOPE")

if __name__ == "__main__":
    main()
