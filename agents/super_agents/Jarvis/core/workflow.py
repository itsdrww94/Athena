from typing import Dict, Any
import requests
import json

class WorkflowManager:
    """
    The Nervous System.
    Connects to n8n or other webhook-based automation platforms.
    """
    
    def __init__(self, webhook_base_url: str = None):
        # Allow base URL to be set via env or config
        self.webhook_base_url = webhook_base_url
        
    def trigger_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> bool:
        """
        Triggers a specific n8n workflow webhook.
        URL format: {base_url}/{workflow_id}
        """
        if not self.webhook_base_url:
            print("[WorkflowManager] No webhook_base_url configured.")
            return False
            
        url = f"{self.webhook_base_url}/{workflow_id}"
        
        try:
            print(f"[*] Triggering n8n workflow: {workflow_id}")
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"[WorkflowManager] Success: {response.text}")
                return True
            else:
                print(f"[WorkflowManager] Failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[WorkflowManager] Error: {e}")
            return False
