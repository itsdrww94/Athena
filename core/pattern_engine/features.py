from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from core.contracts.event_schema import CanonicalEvent

class FeatureFactory:
    """
    Enriches raw events with computed intelligence.
    """
    
    def __init__(self, history: List[CanonicalEvent]):
        self.history = history
        self._index_history()
        
    def _index_history(self):
        """Build indexes for fast lookup."""
        self.merchant_dates = defaultdict(list)
        self.daily_spend = defaultdict(float)
        
        for evt in self.history:
            if evt.event_type == "TRANSACTION":
                dt = evt.timestamp.date()
                amt = evt.data.get("amount", 0)
                merchant = evt.data.get("merchant_raw", "unknown")
                
                self.daily_spend[dt] += amt
                self.merchant_dates[merchant].append(evt.timestamp)

    def compute_transaction_features(self, event: CanonicalEvent) -> Dict[str, Any]:
        """
        Compute features for a new transaction.
        """
        data = event.data
        merchant = data.get("merchant_raw", "unknown")
        amount = data.get("amount", 0)
        ts = event.timestamp
        
        # 1. Novelty Score
        # How many times have we seen this merchant before *this* timestamp?
        past_visits = [t for t in self.merchant_dates[merchant] if t < ts]
        is_new_merchant = len(past_visits) == 0
        novelty_score = 1.0 if is_new_merchant else 0.0
        
        # 2. Recurrence (Subscription) Score
        # Simple heuristic: exact amount matches in previous months?
        # (Placeholder for complex logic)
        recurrence_score = 0.5 if amount < 50 else 0.1 # Base prior
        
        # 3. Spend Velocity (Last 7d)
        start_7d = ts.date() - timedelta(days=7)
        spend_7d = sum(
            self.daily_spend[date] 
            for date in self.daily_spend 
            if start_7d <= date < ts.date()
        )
        
        return {
            "merchant_norm": merchant, # Normalized name (TODO)
            "is_new_merchant": is_new_merchant,
            "novelty_score": novelty_score,
            "recurrence_score": recurrence_score,
            "spend_velocity_7d": round(spend_7d, 2),
            "amount_bucket": "high" if amount > 100 else ("med" if amount > 20 else "low")
        }
