from typing import List, Dict, Any

class AnomalyDetector:
    """
    detects deviations from baselines.
    """
    
    @staticmethod
    def check_velocity_anomaly(current_velocity: float, baseline_avg: float) -> Dict[str, Any]:
        """
        Check if current spending is significantly higher than baseline.
        """
        if baseline_avg == 0:
            return {}
            
        ratio = current_velocity / baseline_avg
        
        if ratio > 2.0:
            return {
                "type": "HIGH_SPEND_VELOCITY",
                "severity": "HIGH",
                "message": f"Spending is {ratio:.1f}x higher than usual this week.",
                "data": {"current": current_velocity, "baseline": baseline_avg}
            }
        elif ratio > 1.5:
             return {
                "type": "ELEVATED_SPEND",
                "severity": "MED",
                "message": f"Spending is trending up ({ratio:.1f}x baseline).",
                "data": {"current": current_velocity, "baseline": baseline_avg}
            }
            
        return {}

    @staticmethod
    def check_transaction_anomalies(features: Dict[str, Any]) -> List[Dict]:
        """
        Check single-transaction flags.
        """
        alerts = []
        if features.get("is_new_merchant") and features.get("amount_bucket") == "high":
            alerts.append({
                "type": "NOVELTY_HIGH_SPEND",
                "severity": "MED",
                "message": "Large purchase at a new merchant."
            })
        return alerts
