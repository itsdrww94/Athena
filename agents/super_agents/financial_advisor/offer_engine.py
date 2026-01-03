"""
Financial Advisor: Offer Engine
===============================
Optimization Layer.
Stores 200-300+ offers/cards.
Optimizes payment path.
"""

from typing import Dict, List, Optional

class OfferEngine:
    def __init__(self):
        # Mock Catalog (Stub for huge database)
        self.cards = {
            "prime": {"name": "Amazon Prime Visa", "cashback": {"Amazon": 0.05, "Whole Foods": 0.05, "default": 0.01}},
            "gold": {"name": "Amex Gold", "cashback": {"Dining": 0.04, "Groceries": 0.04, "Travel": 0.03, "default": 0.01}},
            "double": {"name": "Citi Double Cash", "cashback": {"default": 0.02}},
            "target": {"name": "Target RedCard", "cashback": {"Target": 0.05, "default": 0.0}}
        }
        
    def get_best_card(self, merchant: str, category: str) -> str:
        """Find the maximal cashback card."""
        best_card = "double" # Baseline
        best_rate = 0.02
        
        # Check specific merchants
        if "Amazon" in merchant:
            return f"Use {self.cards['prime']['name']} (5% Back)"
        if "Target" in merchant:
             return f"Use {self.cards['target']['name']} (5% Off)"
             
        # Check Categories
        if category == "Food" or category == "Groceries":
             return f"Use {self.cards['gold']['name']} (4x Points)"
             
        return f"Use {self.cards['double']['name']} (2% Flat)"

def get_offer_engine():
    return OfferEngine()
