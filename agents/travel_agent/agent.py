#!/usr/bin/env python3
"""
Travel Agent
============
"The Trip Planner"
Level 1: Propose Only.

Roles:
- Draft itineraries based on LTM prefs.
- Check affordability via Financial Advisor (Hub routing).
- Output: Trip Drafts to Notion (Gated).

Ref: Athena 2.0 Spec (Section 6.7)
"""

import sys
import argparse
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from services.athena_schemas import AgentOutput
except ImportError:
    class AgentOutput:
        def __init__(self): 
            self.observations = []
            self.recommendations = []

def main():
    parser = argparse.ArgumentParser(description="Athena Travel Agent")
    parser.add_argument("--context", required=False, help="JSON Context Capsule")
    parser.add_argument("--dest", help="Destination")
    parser.add_argument("--dates", help="Travel Dates")
    
    args = parser.parse_args()
    
    # 1. READ CONTEXT
    try:
        capsule = json.loads(args.context) if args.context else {}
    except:
        capsule = {} # Stub
        
    output = AgentOutput()
    
    # 2. GENERATE DRAFT (STUB)
    if args.dest:
        output.observations.append(f"Trip Request: {args.dest} ({args.dates or 'Flexible'})")
        
        # Check constraints from capsule
        constraints = capsule.get("relevant_constraints", {})
        if constraints.get("no_car"):
             output.recommendations.append("Filter: Transit-friendly / Walkable areas only.")
             
        output.recommendations.append(f"Draft Idea: Weekend in {args.dest}")
        output.recommendations.append("Action: Request Financial Advisor check for ~$800 budget.")
        
    else:
        output.observations.append("No destination specified.")
        output.recommendations.append("Where do you want to go?")

    # 3. PRINT ENVELOPE
    print("START_ENVELOPE")
    result = {
        "observations": output.observations,
        "recommendations": output.recommendations,
        "proposed_memory_updates": [] 
    }
    print(json.dumps(result, indent=2))
    print("END_ENVELOPE")

if __name__ == "__main__":
    main()
