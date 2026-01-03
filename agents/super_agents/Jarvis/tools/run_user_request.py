import os
import sys
import logging
from datetime import datetime

# Setup Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from services.notion_service import get_notion_service
from agents.super_agents.Jarvis.reporters.notion_reporter import JarvisNotionReporter
from agents.super_agents.Jarvis.core.orchestrator import JarvisOrchestrator

# Config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_jarvis")

TARGET_INFO = {
    "username": "itsdrww",
    "email": "itsdrww@gmail.com",
    "phone": "6122052977"
}

def ensure_notion_setup():
    """Checks for IDs in env, if missing, tries to set up or warns."""
    runs_id = os.getenv("NOTION_JARVIS_RUNS_DB_ID")
    if not runs_id:
        print("[!] NOTION_JARVIS_RUNS_DB_ID not in env.")
        print("[*] Attempting to load from notion_db_ids.json")
        try:
            import json
            with open("notion_db_ids.json", "r") as f:
                ids = json.load(f)
                for k, v in ids.items():
                    if v:
                        os.environ[k] = v
                        print(f"    Loaded {k}")
        except FileNotFoundError:
            print("[!] JSON file not found. Running Setup Logic inline...")
            from agents.super_agents.Jarvis.tools.setup_notion import main as setup_main
            setup_main()
            # Reload json
            try:
                with open("notion_db_ids.json", "r") as f:
                    ids = json.load(f)
                    for k, v in ids.items():
                        if v:
                            os.environ[k] = v
            except:
                print("[!] Setup failed to produce JSON. Continuing without Notion...")
                return False
    return True

def run_jarvis():
    print(f"[*] Starting Jarvis Run for: {TARGET_INFO}")
    
    # 1. Notion Setup
    has_notion = ensure_notion_setup()
    
    # 2. Config
    config = {
        "output_dir": "./jarvis_output",
        "scope": "Authorized",
        "mode": "Live"
    }
    
    # 3. Orchestrator
    try:
        orchestrator = JarvisOrchestrator(config)
        
        # 4. Inject User Info as "Findings" to seed the run?
        # The orchestrator usually takes a single "target" string.
        # We'll use the username as the primary target, but maybe prompt logic handles the rest?
        # Actually, let's look at orchestrator.run_investigation(target)
        
        target = TARGET_INFO["username"]
        
        # Run Investigation
        report = orchestrator.run_investigation(target)
        
        # Manually Inject User Info if not present
        # This ensures the blueprint has the starter data
        known_intel = [
            {"type": "Email", "value": TARGET_INFO["email"], "confidence": 1.0, "status_tag": "Confirmed", "source": "User Input"},
            {"type": "Phone", "value": TARGET_INFO["phone"], "confidence": 1.0, "status_tag": "Confirmed", "source": "User Input"}
        ]
        
        confirmed = report.setdefault("triage", {}).setdefault("confirmed", [])
        
        # Deduplicate
        existing_vals = {str(x.get("value")) for x in confirmed}
        for item in known_intel:
            if item["value"] not in existing_vals:
                confirmed.append(item)
                print(f"[*] Injected known intel: {item['type']}")
        
        # Re-publish to Notion with complete data
        # Orchestrator runs publish internally, but we might want to update or re-publish if we modified report
        # The Orchestrator calls publish at the end. To patch this, we should really start the Orchestrator with this knowledge.
        # But for now, we will re-publish the updated report.
        if orchestrator.notion_reporter and orchestrator.notion_reporter.enabled:
             print("[*] Re-publishing report with injected intel...")
             orchestrator.notion_reporter.publish_casefile(report)
        
        print("\n[*] Run Complete.")
        
    except Exception as e:
        print(f"[!] Jarvis Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_jarvis()
