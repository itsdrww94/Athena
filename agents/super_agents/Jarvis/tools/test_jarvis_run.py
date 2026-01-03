import os
import sys
import json
import logging
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

try:
    from agents.super_agents.Jarvis.reporters.notion_reporter import JarvisNotionReporter
except ImportError:
    print("Could not import JarvisNotionReporter. Check path.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    print("STARTING JARVIS NOTION TEST RUN...")

    # Load IDs from json if available
    try:
        with open("notion_db_ids.json", "r") as f:
            ids = json.load(f)
            for k, v in ids.items():
                if v:
                    os.environ[k] = v
                    print(f"Loaded {k}: {v}")
    except FileNotFoundError:
        print("notion_db_ids.json not found. Assuming IDs are in valid .env or this will fail.")

    # Create dummy report data
    target = "itsdrww"
    
    report = {
        "target": target,
        "triage": {
            "confirmed": [
                {
                    "type": "Username",
                    "value": "itsdrww",
                    "confidence": 1.0,
                    "status_tag": "Confirmed",
                    "source": "Initial Input",
                    "notes": "User provided handle."
                },
                {
                    "type": "Email",
                    "value": "itsdrww@gmail.com",
                    "confidence": 1.0,
                    "status_tag": "Confirmed",
                    "source": "Initial Input"
                },
                {
                    "type": "Phone",
                    "value": "6122052977",
                    "confidence": 1.0,
                    "status_tag": "Confirmed"
                }
            ],
            "leads": [
                {
                    "type": "Domain",
                    "value": "example-leak.com",
                    "confidence": 0.75,
                    "status_tag": "Lead",
                    "url": "http://example-leak.com/data",
                    "notes": "Potential breach source linked to email."
                }
            ],
            "rejected": []
        },
        "remediation": [
            {"action": "Review email security settings", "category": "Reduce Risk"},
            {"action": "Enable 2FA on Google Account", "category": "Reduce Risk"}
        ],
        "journal": [
            {"action": "Initial Classification", "reason": "Input matches known username format.", "timestamp": "2025-12-28 10:00:00"},
            {"action": "Identity Search", "reason": "Executed Sherlock scan.", "timestamp": "2025-12-28 10:01:00"}
        ],
        "timeline": [
            {"event": "Discovery of Phone Number", "date": "2025-12-28T10:05:00", "type": "Discovery"}
        ]
    }

    # Initialize Reporter
    reporter = JarvisNotionReporter()
    
    if not reporter.enabled:
        print("Reporter is DISABLED. Aborting test.")
        return

    # Publish
    url = reporter.publish_casefile(report)
    
    if url:
        print(f"SUCCESS! Check run here: {url}")
    else:
        print("FAILURE. No URL returned.")

if __name__ == "__main__":
    main()
