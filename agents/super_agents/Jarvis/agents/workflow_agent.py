import requests
from typing import Dict, Any

class WorkflowAgent:
    """
    Agent: The Nervous System.
    Wraps: n8n (via Webhooks)
    Capabilities: Trigger complex workflows, get results.
    """
    
    def __init__(self, n8n_url: str = "http://localhost:5678"):
        self.base_url = n8n_url

    def trigger_workflow(self, webhook_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Triggers an n8n workflow webhook.
        """
        url = f"{self.base_url}/webhook/{webhook_path}"
        try:
            print(f"[*] Triggering n8n workflow: {url}")
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    return {"status": "success", "raw_body": response.text}
            else:
                return {"error": "n8n returned error", "code": response.status_code}
                
        except Exception as e:
            return {"error": f"Connection failed: {str(e)}"}
