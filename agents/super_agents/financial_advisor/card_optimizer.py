"""
Card Optimizer — Deal Registry
==============================
Stores 200+ card deals and advises on optimal payment method.

Commands:
- add_deal(): Register a new offer
- get_best_card(): Find optimal payment for a purchase
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class CardDeal:
    """A credit/debit card deal or reward."""
    card_name: str           # "Chase Freedom Flex"
    merchant_pattern: str    # "Starbucks", "Amazon", or "*" for all
    category: Optional[str]  # "Dining", "Grocery", etc.
    reward_rate: float       # 0.05 = 5%
    reward_type: str         # "cashback", "points", "discount"
    expires: Optional[str]   # "2024-03-31" or None for permanent
    notes: str = ""          # "Q1 2024 rotating category"
    
    def is_expired(self) -> bool:
        """Check if deal has expired."""
        if not self.expires:
            return False
        try:
            exp_date = datetime.strptime(self.expires, "%Y-%m-%d")
            return datetime.now() > exp_date
        except ValueError:
            return False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CardDeal":
        return cls(**data)


@dataclass
class CardRecommendation:
    """Result of get_best_card()."""
    card_name: str
    reward_rate: float
    reward_type: str
    estimated_savings: float
    message: str


class CardOptimizer:
    """
    Registry of card deals. Advises best payment method for purchases.
    
    Usage:
        optimizer = CardOptimizer()
        optimizer.add_deal("Chase", "Starbucks", 0.10, reward_type="cashback")
        rec = optimizer.get_best_card("Starbucks", "Dining", 5.50)
        print(rec.message)  # "Use Chase for 10% back (saves $0.55)"
    """
    
    DEFAULT_BASELINE = {
        "card_name": "Citi Double Cash",
        "reward_rate": 0.02,
        "reward_type": "cashback"
    }
    
    def __init__(self, deals_file: Optional[str] = None):
        self.deals: List[CardDeal] = []
        self.deals_file = deals_file or self._default_deals_path()
        self.load_deals()
    
    def _default_deals_path(self) -> str:
        """Get default path for deals JSON file."""
        base = Path(__file__).parent / "data"
        base.mkdir(exist_ok=True)
        return str(base / "card_deals.json")
    
    def load_deals(self):
        """Load deals from JSON file."""
        if os.path.exists(self.deals_file):
            try:
                with open(self.deals_file, "r") as f:
                    data = json.load(f)
                    self.deals = [CardDeal.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self.deals = []
        else:
            # Initialize with some common defaults
            self._init_default_deals()
    
    def save_deals(self):
        """Save deals to JSON file."""
        with open(self.deals_file, "w") as f:
            json.dump([d.to_dict() for d in self.deals], f, indent=2)
    
    def _init_default_deals(self):
        """Initialize with common card deals."""
        self.deals = [
            CardDeal("Amazon Prime Visa", "Amazon", None, 0.05, "cashback", None, "5% on Amazon"),
            CardDeal("Amazon Prime Visa", "Whole Foods", None, 0.05, "cashback", None, "5% at Whole Foods"),
            CardDeal("Amex Gold", "*", "Dining", 0.04, "points", None, "4x on Dining"),
            CardDeal("Amex Gold", "*", "Grocery", 0.04, "points", None, "4x on Groceries"),
            CardDeal("Target RedCard", "Target", None, 0.05, "discount", None, "5% off Target"),
            CardDeal("Chase Freedom Flex", "*", "Dining", 0.03, "cashback", None, "3% on Dining"),
            CardDeal("Chase Freedom Flex", "*", "Drugstore", 0.03, "cashback", None, "3% at Drugstores"),
            CardDeal("Citi Double Cash", "*", None, 0.02, "cashback", None, "2% on everything"),
        ]
        self.save_deals()
    
    def add_deal(
        self,
        card_name: str,
        merchant_pattern: str,
        reward_rate: float,
        category: Optional[str] = None,
        reward_type: str = "cashback",
        expires: Optional[str] = None,
        notes: str = ""
    ) -> CardDeal:
        """
        Add a new deal to the registry.
        
        Example:
            add_deal("Chase", "Starbucks", 0.10, reward_type="cashback")
        """
        deal = CardDeal(
            card_name=card_name,
            merchant_pattern=merchant_pattern,
            category=category,
            reward_rate=reward_rate,
            reward_type=reward_type,
            expires=expires,
            notes=notes
        )
        self.deals.append(deal)
        self.save_deals()
        return deal
    
    def remove_deal(self, card_name: str, merchant_pattern: str) -> bool:
        """Remove a deal by card and merchant."""
        original_len = len(self.deals)
        self.deals = [
            d for d in self.deals
            if not (d.card_name == card_name and d.merchant_pattern == merchant_pattern)
        ]
        if len(self.deals) < original_len:
            self.save_deals()
            return True
        return False
    
    def get_best_card(
        self,
        merchant: str,
        category: str,
        amount: float
    ) -> CardRecommendation:
        """
        Find optimal payment for a purchase.
        
        Args:
            merchant: Merchant name (e.g., "Starbucks")
            category: Purchase category (e.g., "Dining")
            amount: Purchase amount
        
        Returns:
            CardRecommendation with best card and estimated savings
        """
        matches: List[tuple] = []  # (CardDeal, score)
        
        for deal in self.deals:
            if deal.is_expired():
                continue
            
            score = self._calculate_match_score(deal, merchant, category)
            if score > 0:
                matches.append((deal, score, deal.reward_rate))
        
        if not matches:
            # Fall back to baseline
            savings = amount * self.DEFAULT_BASELINE["reward_rate"]
            return CardRecommendation(
                card_name=self.DEFAULT_BASELINE["card_name"],
                reward_rate=self.DEFAULT_BASELINE["reward_rate"],
                reward_type=self.DEFAULT_BASELINE["reward_type"],
                estimated_savings=savings,
                message=f"Use {self.DEFAULT_BASELINE['card_name']} for 2% flat (saves ${savings:.2f})"
            )
        
        # Sort by reward rate (highest first), then by match score
        matches.sort(key=lambda x: (x[2], x[1]), reverse=True)
        best_deal, _, _ = matches[0]
        
        savings = amount * best_deal.reward_rate
        rate_pct = best_deal.reward_rate * 100
        
        return CardRecommendation(
            card_name=best_deal.card_name,
            reward_rate=best_deal.reward_rate,
            reward_type=best_deal.reward_type,
            estimated_savings=savings,
            message=f"Use {best_deal.card_name} for {rate_pct:.0f}% {best_deal.reward_type} (saves ${savings:.2f})"
        )
    
    def _calculate_match_score(self, deal: CardDeal, merchant: str, category: str) -> int:
        """
        Calculate how well a deal matches a purchase.
        Higher score = better match.
        
        Returns:
            0 = no match
            1 = wildcard match (applies to all)
            2 = category match
            3 = merchant match (exact or partial)
        """
        merchant_lower = merchant.lower()
        pattern_lower = deal.merchant_pattern.lower()
        
        # Exact or partial merchant match (highest priority)
        if pattern_lower != "*" and pattern_lower in merchant_lower:
            return 3
        
        # Category match
        if deal.category and deal.category.lower() == category.lower():
            return 2
        
        # Wildcard (applies to everything)
        if deal.merchant_pattern == "*" and not deal.category:
            return 1
        
        return 0
    
    def list_deals(self, card_filter: Optional[str] = None) -> List[CardDeal]:
        """List all deals, optionally filtered by card name."""
        if card_filter:
            return [d for d in self.deals if card_filter.lower() in d.card_name.lower()]
        return self.deals


# =============================================================================
# SINGLETON
# =============================================================================

_optimizer_instance: Optional[CardOptimizer] = None


def get_card_optimizer() -> CardOptimizer:
    """Get or create the card optimizer singleton."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = CardOptimizer()
    return _optimizer_instance
