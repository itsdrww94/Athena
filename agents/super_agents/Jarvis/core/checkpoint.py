"""
CheckPoint Manager
Handles fail-safe state saving and loading for JARVIS investigations.
"""
import json
import os
import time
from typing import Dict, Any, List

class CheckpointManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def get_checkpoint_path(self, target: str) -> str:
        safe_target = target.replace("@", "_").replace(".", "_").replace(":", "_")
        return os.path.join(self.output_dir, f"checkpoint_{safe_target}.json")

    def save_checkpoint(self, target: str, state: Dict[str, Any]):
        """
        Save current investigation state to disk.
        """
        filepath = self.get_checkpoint_path(target)
        try:
            # Metadata
            state["timestamp"] = time.time()
            state["target"] = target
            
            # Atomic write (write temp then rename)
            temp_path = filepath + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(state, f, indent=2, default=str)
            os.replace(temp_path, filepath)
            # print(f"[DEBUG] Checkpoint saved: {filepath}")
        except Exception as e:
            print(f"[!] Warning: Failed to save checkpoint: {e}")

    def load_checkpoint(self, target: str) -> Dict[str, Any]:
        """
        Load partial investigation state if exists.
        """
        filepath = self.get_checkpoint_path(target)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[!] Warning: Failed to load checkpoint: {e}")
        return None

    def clear_checkpoint(self, target: str):
        """
        Remove checkpoint after successful completion.
        """
        filepath = self.get_checkpoint_path(target)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
