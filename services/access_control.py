"""
Athena Access Control
=====================
Defines Access Levels, Data Stores, and the Policy Matrix.
"Guardrails for the AI"

Ref: Athena 2.0 Master Spec
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

# =============================================================================
# DEFINITIONS
# =============================================================================

LEVEL_0_OBSERVE = 0
LEVEL_1_PROPOSE = 1
LEVEL_2_GATEKEEPER = 2
LEVEL_3_EXECUTE = 3
LEVEL_4_ADMIN = 4

# Autonomy Modes
MODE_SENSOR = "sensor"     # Always-on/Frequent, Read/Append Only
MODE_ANALYST = "analyst"   # Scheduled, Read/Summarize
MODE_EXECUTOR = "executor" # On-demand, Gated, Full Capability

@dataclass
class AgentPolicy:
    level: int
    read_scopes: List[str]
    write_scopes: List[str]
    autonomy_mode: str = MODE_EXECUTOR # Default to safest/manual mode
    schedule: str = "on_demand" # "always_on", "daily", "weekly", "on_demand"
    execution_gates: List[str] = field(default_factory=list)
    description: str = ""

# =============================================================================
# ACCESS MATRIX
# =============================================================================

ACCESS_MATRIX = {
    # ✅ Athena Hub (Core Orchestrator)
    "athena_hub": AgentPolicy(
        level=LEVEL_4_ADMIN,
        read_scopes=["LTM", "WM", "EV", "Notion"],
        write_scopes=["events", "memory_commit", "notion_writes", "system_actions", "policy_enforcement"],
        autonomy_mode=MODE_EXECUTOR,
        description="Core Orchestrator - Final decision maker"
    ),

    # 💰 Financial Advisor (Upgraded)
    "financial_advisor": AgentPolicy(
        level=LEVEL_2_GATEKEEPER,
        read_scopes=["LTM", "WM", "EV", "Notion"],
        write_scopes=["events", "memory_proposals", "policy_decisions"],
        autonomy_mode=MODE_ANALYST,
        schedule="event_driven_and_daily",
        description="CFO Brain: Affordability, Planning, Risk"
    ),

    # 📧 Transaction Hunter
    "scan": AgentPolicy(
        level=LEVEL_3_EXECUTE,
        read_scopes=["EV", "LTM", "Notion"],
        write_scopes=["events", "notion_writes"],
        autonomy_mode=MODE_SENSOR,
        schedule="always_on",
        execution_gates=["confidence_threshold"],
        description="Receipt Scanner (Append-Only)"
    ),

    # 🎯 Deal Sniper
    "deals": AgentPolicy(
        level=LEVEL_1_PROPOSE,
        read_scopes=["LTM", "WM", "Notion"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_SENSOR,
        schedule="throttled_daily",
        execution_gates=["impulse_throttle"],
        description="Deal Finder (Throttled)"
    ),

    # 📰 News Brief
    "news": AgentPolicy(
        level=LEVEL_1_PROPOSE,
        read_scopes=["LTM", "WM"],
        write_scopes=["events", "memory_proposals"],
        autonomy_mode=MODE_ANALYST,
        schedule="daily",
        description="News Summarizer"
    ),
    
    # 🏙️ MSP Scout (Events)
    "events": AgentPolicy(
        level=LEVEL_1_PROPOSE,
        read_scopes=["LTM", "WM"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_ANALYST,
        schedule="weekly",
        description="Event Finder"
    ),

    # 🎬 Cinema Companion
    "movies": AgentPolicy(
        level=LEVEL_1_PROPOSE,
        read_scopes=["LTM", "WM", "Notion"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_ANALYST,
        schedule="weekly", # New releases
        description="Movies Planner"
    ),

    # ✈️ Travel Agent
    "travel": AgentPolicy(
        level=LEVEL_1_PROPOSE,
        read_scopes=["LTM", "WM"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_ANALYST, # or executor if booking enabled later
        schedule="on_demand",
        execution_gates=["finance_check"],
        description="Travel Planner"
    ),

    # 🏥 Health Sync
    "health": AgentPolicy(
        level=LEVEL_2_GATEKEEPER,
        read_scopes=["EV", "LTM", "WM", "Notion"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_ANALYST,
        schedule="daily_import_weekly_trend",
        description="Health Correlation Engine"
    ),

    # 🐱 Vet Manager
    "pets": AgentPolicy(
        level=LEVEL_2_GATEKEEPER,
        read_scopes=["LTM", "WM", "EV", "Notion"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_ANALYST,
        schedule="daily_reminders",
        description="Pet Care Manager"
    ),

    # 🏥 Medic
    "medic": AgentPolicy(
        level=LEVEL_2_GATEKEEPER,
        read_scopes=["system_metrics"], 
        write_scopes=["events", "memory_proposals"],
        autonomy_mode=MODE_SENSOR,
        schedule="always_on",
        execution_gates=["user_confirm", "hub_approval"],
        description="System Telemetry"
    ),

    # 🔴 Protocol Omega
    "omega": AgentPolicy(
        level=LEVEL_3_EXECUTE,
        read_scopes=["omega_vault"], 
        write_scopes=["omega_logs"],
        autonomy_mode=MODE_EXECUTOR,
        schedule="on_demand",
        execution_gates=["two_step_confirm"],
        description="Dead Man's Switch (Isolated)"
    ),

    # 🏭 Agent Factory
    "build": AgentPolicy(
        level=LEVEL_3_EXECUTE,
        read_scopes=["templates", "registry", "LTM"],
        write_scopes=["code_generation"],
        autonomy_mode=MODE_EXECUTOR,
        schedule="on_demand",
        execution_gates=["sandbox_mode", "hub_promotion"],
        description="Agent Generator"
    ),

    # 🗂️ Notion Agent
    "notion": AgentPolicy(
        level=LEVEL_3_EXECUTE,
        read_scopes=["Notion", "LTM", "WM"],
        write_scopes=["notion_writes"],
        autonomy_mode=MODE_SENSOR, # Filing is sensor-like
        schedule="always_on_inbox_filing", 
        execution_gates=["hub_approval"], # Edits require approval
        description="The Scribe"
    ),
    
    # 🛡️ Impulse Shield
    "shield": AgentPolicy(
        level=LEVEL_2_GATEKEEPER,
        read_scopes=["WM", "LTM"],
        write_scopes=["events", "memory_proposals", "policy_decisions"],
        autonomy_mode=MODE_ANALYST,
        schedule="event_driven",
        description="Impulse Brake"
    ),
    
    # 📅 Life Ops
    "ops": AgentPolicy(
        level=LEVEL_1_PROPOSE,
        read_scopes=["LTM", "WM", "Notion"],
        write_scopes=["events", "memory_proposals", "notion_writes"],
        autonomy_mode=MODE_ANALYST,
        schedule="daily_morning",
        description="Daily Planner"
    )
}

# =============================================================================
# LOGIC
# =============================================================================

class AccessControl:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AccessControl, cls).__new__(cls)
        return cls._instance

    def get_policy(self, agent_name: str) -> Optional[AgentPolicy]:
        """Get policy for an agent."""
        # Normalize name (remove _agent suffix if present)
        name = agent_name.replace("_agent", "")
        return ACCESS_MATRIX.get(name)

    def check_permission(self, agent_name: str, action_type: str) -> bool:
        """
        Check if agent is allowed to perform action.
        """
        policy = self.get_policy(agent_name)
        if not policy:
            return False 
            
        if action_type == "commit_memory":
            return "memory_commit" in policy.write_scopes
            
        if action_type == "propose_memory":
            return "memory_proposals" in policy.write_scopes
            
        if action_type == "write_notion":
            return "notion_writes" in policy.write_scopes
            
        if action_type == "spend_money":
            # Only Level 3+ can execute side effects, but usually gated
            return policy.level >= LEVEL_3_EXECUTE
            
        return False

    def get_gates(self, agent_name: str) -> List[str]:
        policy = self.get_policy(agent_name)
        return policy.execution_gates if policy else []

def get_access_control() -> AccessControl:
    return AccessControl()
