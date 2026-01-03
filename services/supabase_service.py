import os
import json
import logging
import requests
from typing import Optional, Dict, Any

from rich.console import Console

console = Console()
logger = logging.getLogger("athena")

class SupabaseService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
            cls._instance.initialized = False
            cls._instance.url = None
            cls._instance.key = None
            cls._instance.headers = {}
        return cls._instance

    def initialize(self):
        """Initialize Supabase REST details from env"""
        if self.initialized:
            return True
            
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            return False
            
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        self.initialized = True
        return True

    def log_thought(self, thought: str, category: str = "analysis", session_id: str = "custom_session") -> bool:
        """
        Log thought via REST API (No SDK needed)
        """
        if not self.initialized:
            if not self.initialize():
                return False

        try:
            endpoint = f"{self.url}/rest/v1/athena_monologue"
            data = {
                "thought_process": thought,
                "category": category,
                "session_id": session_id,
                "metadata": {"source": "cli_agent_rest"}
            }
            
            resp = requests.post(endpoint, headers=self.headers, json=data, timeout=5)
            if resp.status_code in [200, 201]:
                return True
            else:
                logger.error(f"Supabase REST Error: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to log thought: {e}")
            return False

# Global accessor
def get_supabase_service():
    return SupabaseService()
