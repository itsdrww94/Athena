import re
from typing import Dict, List, Any

class ClassifierAgent:
    """
    Agent 1: The Detective's Eyes.
    Detects what kind of evidence has been provided.
    Does NOT act, just labels.
    """
    
    PATTERNS = {
        "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "phone": r"\+?1?\d{9,15}", # Basic catch-all, verify specific regions later
        "url": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
        "ip": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "username": r"^@?[a-zA-Z0-9._]{3,20}$", # Broad username match
        "vin": r"\b[A-HJ-NPR-Z0-9]{17}\b", # Modern VIN
    }

    def classify(self, input_data: str) -> List[Dict[str, Any]]:
        """
        Returns a list of potential classifications with confidence.
        """
        findings = []
        
        for p_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, input_data)
            if matches:
                for m in matches:
                    findings.append({
                        "type": p_type,
                        "value": m,
                        "confidence": 0.9 if len(m) > 5 else 0.5
                    })
        
        # Heuristics for things regex misses
        if "instagram.com" in input_data:
            findings.append({"type": "platform_url", "value": input_data, "platform": "instagram", "confidence": 1.0})
            
        return findings

    def extract_identifiers(self, url: str) -> List[str]:
        """
        Specialized logic: Pull usernames from URLs.
        e.g. twitter.com/username -> username
        """
        # Placeholder for specific platform logic
        if "twitter.com" in url or "x.com" in url:
            parts = url.strip("/").split("/")
            return [parts[-1]]
            
        return []
