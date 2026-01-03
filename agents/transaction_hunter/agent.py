#!/usr/bin/env python3
"""
Transaction Hunter
==================
"The Receipt Scanner"
Level 3: Execute (Restricted Sensor).

Roles:
- Always-on Sensor (simulated via cron/schedule).
- Scans for new receipt emails.
- Output: "purchase" Events for Athena.
- Action: Append-Only log to Notion "Receipts Inbox" (if confidence high).

Ref: Autonomy Policy (Sensor)
"""

import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from services.athena_schemas import AgentOutput, AthenaEvent
except ImportError:
    class AgentOutput:
        def __init__(self): 
            self.observations = []
            self.recommendations = []
            self.events_to_log = []

def main():
    parser = argparse.ArgumentParser(description="Athena Transaction Hunter")
    parser.add_argument("--context", required=False, help="JSON Context Capsule")
    parser.add_argument("--days", type=int, default=1, help="Lookback days")
    
    args = parser.parse_args()
    
    output = AgentOutput()
    
    # 1. SCAN LOGIC (Mock)
    # In real impl, this calls GmailService
    found_emails = [
        {"subject": "Receipt from Uber", "amount": 15.00, "vendor": "Uber"},
        {"subject": "Amazon Order #123", "amount": 5.00, "vendor": "Amazon"}
    ]
    
    output.observations.append(f"Scanned last {args.days} days. Found {len(found_emails)} receipts.")
    
    for email in found_emails:
        # 2. CREATE EVENTS
        # Normalized event for Pattern Engine
        # event = AthenaEvent(type="purchase", domain="finance", value=email['amount'], source="gmail")
        # output.events_to_log.append(event)
        
        output.observations.append(f"Found: {email['vendor']} - ${email['amount']}")
        
        # 3. APPEND-ONLY ACTION (Stub)
        output.recommendations.append(f"Action: Append '${email['amount']}' to Notion Receipts Inbox.")
        
    # 4. SAFETY CHECK
    output.recommendations.append("Note: Not updating Budget Totals directly (Hub/Finance Job).")

    print_envelope(output)

def print_envelope(output):
    print("START_ENVELOPE")
    result = {
        "observations": output.observations,
        "recommendations": output.recommendations,
        "events_to_log": [] # Mocked
    }
    print(json.dumps(result, indent=2))
    print("END_ENVELOPE")

if __name__ == "__main__":
    main()
