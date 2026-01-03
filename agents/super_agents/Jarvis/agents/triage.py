from typing import List, Dict, Any

class TriageAgent:
    """
    Agent 4: The Judge.
    Sorts findings into 'Fact', 'Lead', 'Junk'.
    """
    
    def triage(self, findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns bucketed findings.
        """
        buckets = {
            "confirmed": [],
            "leads": [],
            "rejected": []
        }
        
        for f in findings:
            conf = f.get("confidence", 0.0)
            
            if conf >= 0.8:
                buckets["confirmed"].append(f)
            elif conf >= 0.4:
                buckets["leads"].append(f)
            else:
                buckets["rejected"].append(f)
                
        return buckets
