import os
import sys
import logging
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from services.notion_service import get_notion_service

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_notion")

def create_database(client, parent_page_id: str, title: str, properties: Dict[str, Any]) -> str:
    """Helper to create a database and return its ID."""
    try:
        response = client.databases.create(
            parent={"page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=properties
        )
        db_id = response["id"]
        logger.info(f"[+] Created Database: '{title}' (ID: {db_id})")
        return db_id
    except Exception as e:
        logger.error(f"[-] Failed to create database '{title}': {e}")
        return None

def main():
    logger.info("Initializing Notion Setup for JARVIS Case Management...")
    
    svc = get_notion_service()
    if not svc.initialize():
        logger.error("Failed to initialize Notion Service. Check credentials.")
        return

    client = svc.client

    # 1. Create Root Page
    # We need a parent page. If NOTION_ROOT_PAGE_ID is not set, we might need to search or ask user.
    # For this script, we'll try to create a new top-level page?? No, Notion API cannot create top-level pages easily without a parent.
    # We will search for a page named "Dashboard" or "Athena" to use as parent, or just use the first page found if none.
    # OR better: User instructions say "Create a top-level Notion page... Inside it, create these databases".
    # So we should look for "JARVIS — Case Management" page first, if not found, maybe create it under a known parent.
    # Let's search for "JARVIS — Case Management"
    
    root_page_id = None
    existing = svc.search_page("JARVIS — Case Management")
    
    if existing:
        root_page_id = existing[0]["id"]
        logger.info(f"[*] Found existing root page: {existing[0]['title']} ({root_page_id})")
    else:
        logger.warning("[!] Root page 'JARVIS — Case Management' not found.")
        logger.warning("[!] Please create this page manually in Notion, share it with the integration, and run this script again.")
        # Try to find *any* page shared to create it under? No, safer to ask user.
        # However, for this task, I will try to find a page named "Athena" or "Workspace" to create it under if possible.
        # But per instructions "Part A — Create the Databases (once)... Create a top-level Notion page..."
        # I'll Assume the user reads output or I can try to create it under the first available page if I can't find it.
        # Actually, let's just abort if we can't find it, or maybe create it under the page defined in .env if any.
        
        # Fallback: List all pages and pick one? No.
        logger.error("Aborting. Please create 'JARVIS — Case Management' page and share with bot.")
        return

    # 2. Define Properties for Databases
    
    # --- DB 1: Casefiles (Runs) ---
    props_runs = {
        "Run ID": {"title": {}},
        "Target Label": {"rich_text": {}},
        "Scope Mode": {"select": {"options": [{"name": "SELF_AUDIT", "color": "blue"}, {"name": "CTF_LAB", "color": "orange"}, {"name": "AUTHORIZED", "color": "green"}]}},
        "Redaction": {"select": {"options": [{"name": "ON", "color": "green"}, {"name": "OFF", "color": "red"}]}},
        "Run Mode": {"select": {"options": [{"name": "LIVE", "color": "red"}, {"name": "REPLAY", "color": "gray"}]}},
        "Started At": {"date": {}},
        "Ended At": {"date": {}},
        "Duration (min)": {"number": {"format": "number"}},
        "Run Summary (1–2 lines)": {"rich_text": {}},
        "Top 3 Findings (Brief)": {"rich_text": {}},
        "Top 3 Risks (Brief)": {"rich_text": {}},
        # Rollups will be added later or manually as API creation of rollups requires relations first
    }
    
    db_runs_id = create_database(client, root_page_id, "Casefiles (Runs)", props_runs)
    if not db_runs_id: return

    # --- DB 2: Findings ---
    props_findings = {
        "Finding ID": {"title": {}},
        "Run": {"relation": {"database_id": db_runs_id, "type": "dual_property", "dual_property": {}}}, # Dual for reciprocal
        "Status": {"select": {"options": [{"name": "Confirmed", "color": "red"}, {"name": "Lead", "color": "yellow"}, {"name": "Conflict", "color": "orange"}, {"name": "Rejected", "color": "gray"}]}},
        "Severity": {"select": {"options": [{"name": "Critical", "color": "purple"}, {"name": "High", "color": "red"}, {"name": "Medium", "color": "orange"}, {"name": "Low", "color": "yellow"}, {"name": "Info", "color": "blue"}]}},
        "Confidence": {"number": {"format": "number"}},
        "Entity Type": {"select": {"options": [{"name": "Username"}, {"name": "Email"}, {"name": "Phone"}, {"name": "Image"}, {"name": "URL"}, {"name": "Domain"}, {"name": "IPAddress"}, {"name": "LocationReference"}, {"name": "VehicleIdentifier"}]}},
        "Entity Value (Display)": {"rich_text": {}},
        "Collector": {"select": {"options": [{"name": "Identity"}, {"name": "Breach"}, {"name": "Image"}, {"name": "Archive"}, {"name": "Infra"}, {"name": "Geo"}, {"name": "Vehicle"}, {"name": "Other"}]}},
        "Source Type": {"select": {"options": [{"name": "API"}, {"name": "Archive"}, {"name": "Local"}, {"name": "Web"}]}},
        "Source Ref": {"url": {}},
        "Retrieved At": {"date": {}},
        "Risk Tag": {"multi_select": {"options": [{"name": "Credential"}, {"name": "Exposure"}, {"name": "Linkability"}, {"name": "Impersonation"}, {"name": "Infrastructure"}, {"name": "Location"}, {"name": "Vehicle"}, {"name": "Other"}]}},
        "Notes (Brief)": {"rich_text": {}},
        "Verification Steps": {"rich_text": {}},
        # Formulas cannot be created via API easily (read-only in some contexts, or requires rigorous strict schema). 
        # We will skip creating Formulas via API for now, User can add them.
    }
    
    db_findings_id = create_database(client, root_page_id, "Findings", props_findings)

    # --- DB 3: Entities ---
    props_entities = {
        "Entity ID": {"title": {}},
        "Run": {"relation": {"database_id": db_runs_id, "type": "dual_property", "dual_property": {}}},
        "Entity Type": {"select": {}}, # Options will auto-add
        "Entity Value (Display)": {"rich_text": {}},
        "Sensitivity": {"select": {"options": [{"name": "Public", "color": "green"}, {"name": "Sensitive", "color": "yellow"}, {"name": "Highly Sensitive", "color": "red"}]}},
        "Confidence (Entity)": {"number": {}},
        "First Observed": {"date": {}},
        "Last Observed": {"date": {}},
        "Notes": {"rich_text": {}},
        "Connected Findings": {"relation": {"database_id": db_findings_id, "type": "dual_property", "dual_property": {}}}
    }
    
    db_entities_id = create_database(client, root_page_id, "Entities", props_entities)

    # --- DB 4: Timeline Events ---
    props_timeline = {
        "Event ID": {"title": {}},
        "Run": {"relation": {"database_id": db_runs_id, "type": "dual_property", "dual_property": {}}},
        "Date/Time": {"date": {}},
        "Event Type": {"select": {"options": [{"name": "Archive Snapshot"}, {"name": "Discovery"}, {"name": "Account Change"}, {"name": "Breach Disclosure"}, {"name": "Verification"}, {"name": "Other"}]}},
        "Related URL": {"url": {}},
        "Snapshot URL": {"url": {}},
        "Change Summary": {"rich_text": {}},
        "Confidence": {"number": {}},
        "Linked Findings": {"relation": {"database_id": db_findings_id, "type": "dual_property", "dual_property": {}}}
    }
    
    db_timeline_id = create_database(client, root_page_id, "Timeline Events", props_timeline)

    # --- DB 5: Next Best Actions ---
    props_actions = {
        "Action ID": {"title": {}},
        "Run": {"relation": {"database_id": db_runs_id, "type": "dual_property", "dual_property": {}}},
        "Priority": {"select": {"options": [{"name": "P0", "color": "red"}, {"name": "P1", "color": "orange"}, {"name": "P2", "color": "yellow"}, {"name": "P3", "color": "blue"}]}},
        "Category": {"select": {"options": [{"name": "Verify Lead"}, {"name": "Reduce Risk"}, {"name": "Collect More Evidence"}, {"name": "Cleanup Footprint"}]}},
        "Status": {"select": {"options": [{"name": "Not Started"}, {"name": "In Progress"}, {"name": "Complete"}, {"name": "Blocked"}]}},
        "Effort": {"select": {"options": [{"name": "5m"}, {"name": "15m"}, {"name": "30m"}, {"name": "1h"}, {"name": "2h+"}]}},
        "Linked Finding": {"relation": {"database_id": db_findings_id, "type": "dual_property", "dual_property": {}}},
        "Why This Matters": {"rich_text": {}},
        "Success Criteria": {"rich_text": {}}
    }
    
    db_actions_id = create_database(client, root_page_id, "Next Best Actions", props_actions)

    # --- DB 6: Decision Journal ---
    props_journal = {
        "Step": {"title": {}},
        "Run": {"relation": {"database_id": db_runs_id, "type": "dual_property", "dual_property": {}}},
        "Step #": {"number": {}},
        "Phase": {"select": {"options": [{"name": "Classify"}, {"name": "Plan"}, {"name": "Collect"}, {"name": "Normalize"}, {"name": "Resolve"}, {"name": "Triage"}, {"name": "Score"}, {"name": "Report"}, {"name": "Export"}]}},
        "Reasoning (Brief)": {"rich_text": {}},
        "Output": {"rich_text": {}},
        "Constraints Hit": {"multi_select": {"options": [{"name": "Scope Block"}, {"name": "Cache Hit"}, {"name": "Rate Limit"}, {"name": "Max Depth"}, {"name": "Conflict Detected"}]}}
    }
    
    db_journal_id = create_database(client, root_page_id, "Decision Journal", props_journal)

    # --- Summary ---
    print("\n" + "="*60)
    print("SETUP COMPLETE. ADD THESE TO YOUR .env FILE:")
    print("="*60)
    print(f"NOTION_JARVIS_RUNS_DB_ID={db_runs_id}")
    
    # Save to file
    import json
    ids = {
        "NOTION_JARVIS_RUNS_DB_ID": db_runs_id,
        "NOTION_JARVIS_FINDINGS_DB_ID": db_findings_id,
        "NOTION_JARVIS_ENTITIES_DB_ID": db_entities_id,
        "NOTION_JARVIS_TIMELINE_DB_ID": db_timeline_id,
        "NOTION_JARVIS_ACTIONS_DB_ID": db_actions_id,
        "NOTION_JARVIS_JOURNAL_DB_ID": db_journal_id
    }
    with open("notion_db_ids.json", "w") as f:
        json.dump(ids, f, indent=2)
        
    print("IDs saved to notion_db_ids.json")

if __name__ == "__main__":
    main()
