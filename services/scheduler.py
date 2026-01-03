"""
Athena Agent Scheduler
======================
Manages the "Heartbeat" of Autonomous Agents.
Checks Access Control schedules and triggers agents.

Ref: Autonomy Policy
"""

import logging
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from .access_control import get_access_control, ACCESS_MATRIX, MODE_SENSOR, MODE_ANALYST

logger = logging.getLogger("athena.scheduler")

class Scheduler:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.state_file = Path(__file__).parent.parent / "brain" / "scheduler_state.json"
        self.last_run: Dict[str, str] = self._load_state()
        self._initialized = True

    def _load_state(self) -> Dict[str, str]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.last_run, f)

    def heartbeat(self, console=None):
        """
        Check schedules and run agents if needed.
        Called by Main Loop.
        """
        ac = get_access_control()
        now = datetime.now()
        
        for agent_name, policy in ACCESS_MATRIX.items():
            if not policy.schedule or policy.schedule == "on_demand":
                continue
                
            should_run = False
            last_run_str = self.last_run.get(agent_name)
            last_run_time = datetime.fromisoformat(last_run_str) if last_run_str else datetime.min
            
            # 1. Check Schedule Logic
            if policy.schedule == "always_on":
                # Run every 15 mins for sensors (mocked)
                if now - last_run_time > timedelta(minutes=15):
                    should_run = True
                    
            elif policy.schedule == "daily" or "daily" in policy.schedule:
                # Run once a day (if not run today)
                if last_run_time.date() < now.date() and now.hour >= 8: # 8 AM start
                    should_run = True
                    
            elif policy.schedule == "weekly":
                # Run once a week (e.g., Monday)
                if last_run_time.date() < now.date() and now.weekday() == 0:
                    should_run = True
                    
            elif policy.schedule == "throttled_daily":
                # Deal Sniper logic (mock: run if not run today)
                if last_run_time.date() < now.date():
                    should_run = True

            # 2. Execute
            if should_run:
                self._trigger_agent(agent_name, policy, console)
                self.last_run[agent_name] = now.isoformat()
                self._save_state()

    def _trigger_agent(self, agent_name: str, policy, console):
        if console:
            console.print(f"[dim]⏰ Scheduler: Triggering '{agent_name}' ({policy.autonomy_mode})...[/dim]")
        
        # Construct cmd args based on mode
        args = ""
        if agent_name == "financial_advisor":
            if policy.schedule == "event_driven_and_daily":
                args = "auto-planning --scope daily"
        elif agent_name == "scan":
            args = "--days 1"
        elif agent_name == "deals":
            args = "--mode scan"

        # Execute
        try:
             # Run in background/subprocess (blocking for now for simplicity in CLI loop)
             # In a real GUI app, this would be async.
             if agent_name == "financial_advisor":
                 cmd = f"python agents/financial_advisor/agent.py {args}"
             else:
                 cmd = f"python agents/{agent_name}.py {args}"
             
             # Context injection logic would happen here same as CLI
             # For now, we skip context or pass empty
             result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True
             )
             
             # Log Output (Short summary)
             if console:
                 if result.stdout:
                     console.print(f"[dim]✓ {agent_name}: Ran successfully.[/dim]")
                     # Ideally parse envelope and log to PatternEngine
                 if result.stderr:
                     console.print(f"[red]⚠ {agent_name} Error: {result.stderr}[/red]")
                     
        except Exception as e:
            if console:
                console.print(f"[red]Scheduler Error running {agent_name}: {e}[/red]")

def get_scheduler() -> Scheduler:
    return Scheduler()
