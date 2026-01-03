from typing import Dict, Any, List
from .scope import ScopeManager
from .logging import DecisionJournal
from ..agents.classifier import ClassifierAgent
from ..agents.planner import PlannerAgent
from ..agents.resolution import EntityResolutionAgent
from ..agents.triage import TriageAgent
from ..agents.risk import RiskAgent
from ..agents.report import ReportAgent
from ..reporters.notion_reporter import JarvisNotionReporter
from ..collectors.identity import IdentityCollector
from ..collectors.breach import BreachCollector
from ..collectors.geo import GeoCollector
from ..collectors.osint import SpiderFootCollector
from ..agents.knowledge import KnowledgeAgent
from .checkpoint import CheckpointManager

class JarvisOrchestrator:
    """
    JARVIS Core.
    Orchestrates the investigation pipeline.
    """
    
    def __init__(self, config: Dict[str, Any]):
        print("[DEBUG] JarvisOrchestrator initialized")
        self.config = config
        self.scope = ScopeManager(config)
        self.journal = DecisionJournal()
        
        # Initialize Agents
        self.classifier = ClassifierAgent()
        self.planner = PlannerAgent(self.scope)
        self.resolver = EntityResolutionAgent()
        self.triage_agent = TriageAgent()
        self.risk_agent = RiskAgent()
        self.report_agent = ReportAgent(config.get("output_dir", "./output"))
        self.notion_reporter = JarvisNotionReporter()
        self.knowledge_agent = KnowledgeAgent()
        
        # Initialize Collectors
        self.collectors = {
            "identity": IdentityCollector(self.scope),
            "breach": BreachCollector(self.scope),
            "geo": GeoCollector(self.scope),
            "osint": SpiderFootCollector(self.scope)
            # Add others as implemented
        }
        
        # Fail-Safe
        self.checkpoint_mgr = CheckpointManager(config.get("output_dir", "./output"))

    def run_investigation(self, target: str) -> Dict[str, Any]:
        """
        Main pipeline execution.
        """
        print(f"[*] Starting JARVIS run on: {target}")
        
        # 1. Scope Check
        if not self.scope.validate_target(target):
            reason = "Scope Violation: Target not authorized."
            self.journal.log_rejection(target, reason)
            return {"error": reason}
            
        # 2. Classification
        initial_findings = self.classifier.classify(target)
        for f in initial_findings:
            self.journal.log_classification(target, f["type"], f["confidence"], "Initial scan")
            
        # 3. Planning Loop (Simplified 1-pass)
        history = set()
        action_queue = self.planner.generate_plan(initial_findings, history)
        print(f"[DEBUG] Initial Findings: {len(initial_findings)}")
        print(f"[DEBUG] Action Queue: {len(action_queue)}")
        
        all_findings = initial_findings
        
        # --- FAIL-SAFE RESTORE ---
        # Check if we have a previous partial run
        saved_state = self.checkpoint_mgr.load_checkpoint(target)
        if saved_state:
            print(f"[*] FAIL-SAFE: Resuming investigation for {target}...")
            # Restore findings and history
            # Merge loaded findings with initial findings (deduplicate logic needed, but simple list extend for now)
            # In a real system, we'd be smarter. Here we just assume loaded findings include initials.
            if "findings" in saved_state:
                all_findings = saved_state["findings"]
            
            # Restore history of completed steps
            if "history" in saved_state:
                history = set(saved_state["history"])
                
            # Re-plan based on what we already have vs what we need?
            # For simplicity: We just skip steps in the queue that are already in 'history'
        
        # 4. Collection Execution
        # Update plan with potentially new findings from restore?
        # For now, we stick to the initial plan but skip actions already done.
        
        # Save Initial State
        self._save_state(target, all_findings, list(history))
        
        # 4. Collection Execution
        for step in action_queue:
            step_id = step["id"]
            if step_id in history:
                print(f"    [->] Skipping completed step: {step['action']}")
                continue
                
            action_name = step["action"]
            target_val = step["target"]
            
            # Map action to collector (simple map for now)
            # Map action to collector
            collector = None
            if "social" in action_name or "username" in action_name:
                collector = self.collectors["identity"]
            elif "breach" in action_name:
                collector = self.collectors["breach"]
            elif "exif" in action_name:
                collector = self.collectors["geo"]
            elif "osint" in action_name:
                collector = self.collectors["osint"]
            
            # Special handling for Agents that aren't 'collectors' dict based
            if "knowledge" in action_name:
                self.journal.log_action(action_name, {"target": target_val}, "Executing plan")
                new_data = self.knowledge_agent.search(target_val)
                all_findings.extend(new_data)
                history.add(step_id)
                self._save_state(target, all_findings, list(history))
                continue

            if collector:
                self.journal.log_action(action_name, {"target": target_val}, "Executing plan")
                new_data = collector.run(target_val)
                all_findings.extend(new_data)
                history.add(step_id)
                self._save_state(target, all_findings, list(history))
        
        # 5. Resolution & Triage
        resolved_entities = self.resolver.resolve_entities(all_findings)
        triaged_results = self.triage_agent.triage(resolved_entities)
        
        # 6. Risk Assessment
        risk_summary = self.risk_agent.analyze_risk(triaged_results["confirmed"])
        remediation = self.risk_agent.generate_remediation_pack(risk_summary)
        
        # 7. Reporting
        final_report = {
            "target": target,
            "triage": triaged_results,
            "risk": risk_summary,
            "remediation": remediation,
            "journal": self.journal.export_json()
        }
        
        # Save Report
        case_id = f"RUN_{target.replace('@','_')}"
        html_report = self.report_agent.generate_html_report(case_id, final_report)
        # In real world, write to file here
        
        # Publish to Notion
        self.notion_reporter.publish_casefile(final_report)
        
        # Clear Checkpoint on Success
        self.checkpoint_mgr.clear_checkpoint(target)
        
        return final_report

    def _save_state(self, target: str, findings: List[Any], history: List[str]):
        state = {
            "findings": findings,
            "history": history
        }
        self.checkpoint_mgr.save_checkpoint(target, state)
