from typing import List, Dict, Any

class RiskAgent:
    """
    Agent 5: The Security Consultant.
    Calculates risk score and writes the 'Defender Mode' remediation pack.
    """
    
    def analyze_risk(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates risk summary.
        """
        risk_score = 0
        critical_issues = []
        
        for f in findings:
            severity = f.get("severity", "low")
            if severity == "critical":
                risk_score += 10
                critical_issues.append(f)
            elif severity == "high":
                risk_score += 5
            elif severity == "medium":
                risk_score += 2
                
        return {
            "total_risk_score": risk_score,
            "critical_count": len(critical_issues),
            "summary": "High risk detected" if risk_score > 20 else "Moderate risk"
        }

    def generate_remediation_pack(self, risks: Dict[str, Any]) -> List[str]:
        """
        Returns a list of actionable steps for the user.
        """
        steps = []
        
        if risks["total_risk_score"] > 0:
            steps.append("ACTION: Review critical findings immediately.")
            
        # Generic advice (upgrade with specific findings context later)
        steps.append("1. Rotate passwords for all accounts in 'Confirmed' breaches.")
        steps.append("2. Enable 2FA on identified social handles.")
        steps.append("3. Review privacy settings for exposed images.")
        
        return steps
