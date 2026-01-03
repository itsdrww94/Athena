"""
Athena Context Sync
====================
File-based state sharing for multi-surface context (CLI ↔ Telegram).

The ContextStack now persists to disk so CLI and Telegram share state.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("athena.sync")

STATE_FILE = Path(__file__).parent.parent.parent / "brain" / "context_sync.json"

class ContextSyncManager:
    """
    Manages shared state between CLI and Telegram.
    
    Both surfaces read/write to the same JSON file.
    """
    
    @staticmethod
    def save_state(chat_id: str, state_data: Dict[str, Any]):
        """Save a chat's state to the shared file."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing
            all_states = {}
            if STATE_FILE.exists():
                with open(STATE_FILE, "r") as f:
                    all_states = json.load(f)
            
            # Update this chat's state
            state_data["synced_at"] = datetime.now().isoformat()
            all_states[str(chat_id)] = state_data
            
            # Write back
            with open(STATE_FILE, "w") as f:
                json.dump(all_states, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save context sync: {e}")
    
    @staticmethod
    def load_state(chat_id: str) -> Optional[Dict[str, Any]]:
        """Load a chat's state from the shared file."""
        try:
            if not STATE_FILE.exists():
                return None
                
            with open(STATE_FILE, "r") as f:
                all_states = json.load(f)
            
            return all_states.get(str(chat_id))
            
        except Exception as e:
            logger.error(f"Failed to load context sync: {e}")
            return None
    
    @staticmethod
    def sync_result_set(chat_id: str, result_type: str, items: list, surface: str):
        """Sync a result set across surfaces."""
        state = ContextSyncManager.load_state(chat_id) or {}
        state["last_result_set"] = {
            "type": result_type,
            "items": items,
            "surface": surface,
            "timestamp": datetime.now().isoformat()
        }
        ContextSyncManager.save_state(chat_id, state)
    
    @staticmethod
    def get_synced_result_set(chat_id: str) -> Optional[Dict]:
        """Get the latest result set from any surface."""
        state = ContextSyncManager.load_state(chat_id)
        if state:
            return state.get("last_result_set")
        return None


def get_sync_manager() -> ContextSyncManager:
    return ContextSyncManager()
