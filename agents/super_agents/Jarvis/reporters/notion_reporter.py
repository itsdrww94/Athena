from typing import Dict, Any, List, Optional
import os
import logging
from datetime import datetime
from services.notion_service import get_notion_service

logger = logging.getLogger("jarvis.notion")

class JarvisNotionReporter:
    """
    Handles reporting JARVIS investigation results to the Notion Case Management System.
    Follows the blueprint: one Casefile (Run) -> Many Findings, Entities, Actions, etc.
    """
    
    def __init__(self):
        self.svc = get_notion_service()
        self.enabled = False
        
        # Database IDs from Environment
        self.db_runs = os.getenv("NOTION_JARVIS_RUNS_DB_ID")
        self.db_findings = os.getenv("NOTION_JARVIS_FINDINGS_DB_ID")
        self.db_entities = os.getenv("NOTION_JARVIS_ENTITIES_DB_ID")
        self.db_timeline = os.getenv("NOTION_JARVIS_TIMELINE_DB_ID")
        self.db_actions = os.getenv("NOTION_JARVIS_ACTIONS_DB_ID")
        self.db_journal = os.getenv("NOTION_JARVIS_JOURNAL_DB_ID")
        
        # Check if basic config is present
        if self.svc.is_configured and self.db_runs:
            self.enabled = True
            self.svc.initialize()
        else:
            logger.warning("[JarvisNotionReporter] Disabled. Missing API Key or NOTION_JARVIS_RUNS_DB_ID.")

    def publish_casefile(self, report: Dict[str, Any]) -> str:
        """
        Publishes the full report to Notion.
        Returns the URL of the created Casefile page.
        """
        if not self.enabled:
            print("[JarvisNotionReporter] Disabled. Skipping publish.")
            return None
            
        print("[*] Publishing to Notion Case Management System...")
        
        # 1. Create Casefile (Run) Page
        run_page_id, run_url = self._create_casefile_page(report)
        if not run_page_id:
            logger.error("Failed to create Casefile page.")
            return None
            
        print(f"[+] Casefile Created: {run_url}")
        
        # 2. Upload Entities & Findings
        findings_data = report.get("triage", {}).get("confirmed", []) + \
                        report.get("triage", {}).get("leads", []) + \
                        report.get("triage", {}).get("rejected", [])
                        
        self._upload_findings(run_page_id, findings_data)
        
        # 3. Upload Actions
        remediation = report.get("remediation", []) # List of strings or dicts
        self._upload_actions(run_page_id, remediation)
        
        # 4. Upload Decision Journal
        journal = report.get("journal", []) 
        if isinstance(journal, dict):
            journal = journal.get("history", [])
            
        self._upload_journal(run_page_id, journal)
        
        # 5. Upload Timeline (if available)
        timeline = report.get("timeline", [])
        self._upload_timeline(run_page_id, timeline)
        
        print(f"[+] Notion Publish Complete.")
        return run_url

    def _create_casefile_page(self, report: Dict[str, Any]):
        """Creates the main run page."""
        target = report.get("target", "Unknown Target")
        case_id = f"RUN-{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        
        # Stats
        triage = report.get("triage", {})
        count_findings = len(triage.get("confirmed", []))
        
        # Determine properties based on blueprint
        run_mode = "LIVE"
        scope = "AUTHORIZED" # Default
        
        props = {
            "Run ID": {"title": [{"text": {"content": case_id}}]},
            "Target Label": {"rich_text": [{"text": {"content": str(target)}}]},
            "Scope Mode": {"select": {"name": scope}},
            "Redaction": {"select": {"name": "ON"}},
            "Run Mode": {"select": {"name": run_mode}},
            "Started At": {"date": {"start": datetime.now().isoformat()}},
            "Run Summary (1–2 lines)": {"rich_text": [{"text": {"content": f"Automated run on {target}. Found {count_findings} confirmed items."}}]}
        }
        
        try:
            resp = self.svc.client.pages.create(
                parent={"database_id": self.db_runs},
                properties=props
            )
            return resp["id"], resp.get("url")
        except Exception as e:
            logger.error(f"Error creating Casefile: {e}")
            return None, None

    def _upload_findings(self, run_page_id: str, findings: List[Dict]):
        """Uploads findings to findings DB."""
        if not self.db_findings: return
        
        count = 0
        for item in findings:
            try:
                # Map properties
                status = item.get("status_tag", "Lead")
                # Map JARVIS confidence/severity if available
                conf = float(item.get("confidence", 0.0))
                
                severity = "Info"
                if conf > 0.9: severity = "Critical"
                elif conf > 0.8: severity = "High"
                elif conf > 0.6: severity = "Medium"
                
                # Basic fields
                val = str(item.get("value", "N/A"))
                typ = item.get("type", "Unknown")
                
                props = {
                    "Finding ID": {"title": [{"text": {"content": f"F-{count:04d}"}}]},
                    "Run": {"relation": [{"id": run_page_id}]}, # Critical relation
                    "Status": {"select": {"name": status}},
                    "Severity": {"select": {"name": severity}},
                    "Confidence": {"number": conf},
                    "Entity Type": {"select": {"name": typ}},
                    "Entity Value (Display)": {"rich_text": [{"text": {"content": val}}]},
                    "Source Type": {"select": {"name": "Web"}},
                    "Retrieved At": {"date": {"start": datetime.now().isoformat()}}
                }
                
                if "url" in item:
                    props["Source Ref"] = {"url": item["url"]}
                    
                if "notes" in item:
                    props["Notes (Brief)"] = {"rich_text": [{"text": {"content": str(item["notes"])}}]}

                self.svc.client.pages.create(
                    parent={"database_id": self.db_findings},
                    properties=props
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to upload finding: {e}")
                
        print(f"    [+] Uploaded {count} findings.")

    def _upload_actions(self, run_page_id: str, actions: List[Any]):
        """Uploads remediation actions."""
        if not self.db_actions: return
        
        count = 0
        for action in actions:
            try:
                # Handle string or dict
                if isinstance(action, str):
                    title = action
                    cat = "Reduce Risk"
                else:
                    title = action.get("action", "Unknown Action")
                    cat = action.get("category", "Reduce Risk")

                props = {
                    "Action ID": {"title": [{"text": {"content": f"ACT-{count:03d}"}}]},
                    "Run": {"relation": [{"id": run_page_id}]},
                    "Category": {"select": {"name": cat}},
                    "Status": {"select": {"name": "Not Started"}},
                    "Why This Matters": {"rich_text": [{"text": {"content": title}}]}
                }
                
                self.svc.client.pages.create(
                    parent={"database_id": self.db_actions},
                    properties=props
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to upload action: {e}")

    def _upload_journal(self, run_page_id: str, journal_entries: List[Dict]):
        """Uploads decision logs."""
        if not self.db_journal: return
        
        count = 0
        for entry in journal_entries:
            try:
                step_name = entry.get("action", "Step")
                reason = str(entry.get("reason", ""))
                out = str(entry)[:2000]
                
                props = {
                    "Step": {"title": [{"text": {"content": step_name}}]},
                    "Run": {"relation": [{"id": run_page_id}]},
                    "Step #": {"number": count + 1},
                    "Reasoning (Brief)": {"rich_text": [{"text": {"content": reason}}]},
                    "Output": {"rich_text": [{"text": {"content": out}}]}
                }
                
                self.svc.client.pages.create(
                    parent={"database_id": self.db_journal},
                    properties=props
                )
                count += 1
            except Exception as e:
                pass

    def _upload_timeline(self, run_page_id: str, events: List[Dict]):
        """Uploads timeline events."""
        if not self.db_timeline: return
        
        count = 0
        for evt in events:
            try:
                title = evt.get("event", "Event")
                date_str = evt.get("date", datetime.now().isoformat())
                
                props = {
                    "Event ID": {"title": [{"text": {"content": f"EVT-{count:03d}"}}]},
                    "Run": {"relation": [{"id": run_page_id}]},
                    "Date/Time": {"date": {"start": date_str}},
                    "Event Type": {"select": {"name": "Discovery"}},
                    "Change Summary": {"rich_text": [{"text": {"content": title}}]}
                }
                
                self.svc.client.pages.create(
                    parent={"database_id": self.db_timeline},
                    properties=props
                )
                count += 1
            except Exception:
                pass
