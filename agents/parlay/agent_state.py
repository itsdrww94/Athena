"""
HAKARI AGENT STATE MANAGER
--------------------------
Handles persistent state: modes, rolling stats, safety flags.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("Hakari.State")

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "agent_state.json")

DEFAULT_STATE = {
    "shadow_mode": True,  # Default to SAFETY
    "automation_enabled": False,
    "mode": "assisted", # or 'autonomous'
    "rolling_stats": {
        "wins": 0, "losses": 0, "roi_sum": 0.0, "drawdown_current": 0.0, "max_drawdown": 0.0
    },
    "failsafe_triggered": False,
    "learned_deltas": {},
    "last_update": None
}

def load_state():
    try:
        if not os.path.exists(STATE_FILE):
            return dict(DEFAULT_STATE)
        with open(STATE_FILE, "r") as f:
            return {**DEFAULT_STATE, **json.load(f)}
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return dict(DEFAULT_STATE)

def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        state["last_update"] = datetime.utcnow().isoformat()
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

def update_rolling_stats(result_pnl):
    state = load_state()
    stats = state["rolling_stats"]
    
    if result_pnl > 0:
        stats["wins"] += 1
        stats["drawdown_current"] = max(0.0, stats["drawdown_current"] - result_pnl) # Naive recovery
    else:
        stats["losses"] += 1
        stats["drawdown_current"] += abs(result_pnl)
    
    stats["roi_sum"] += result_pnl
    stats["max_drawdown"] = max(stats["max_drawdown"], stats["drawdown_current"])
    
    # Check failsafe
    if stats["drawdown_current"] > 50.0: # Hardcoded $50 drawdown pause for now, or use config
        state["failsafe_triggered"] = True
        state["automation_enabled"] = False # PAUSE
        logger.warning("FAILSAFE TRIGGERED: Drawdown exceeded limit. Automation PAUSED.")
        
    save_state(state)
    return stats

def get_flag(key):
    return load_state().get(key)

def set_flag(key, value):
    state = load_state()
    state[key] = value
    save_state(state)
