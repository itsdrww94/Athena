"""
Financial Advisor: Ledger Engine
================================
Truth Layer for Money.
Handles: Transactions, Category Totals, Reconciliation.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import json
from datetime import datetime

@dataclass
class Transaction:
    id: str
    date: str
    vendor: str
    amount: float
    category: str
    source: str # e.g. "manual", "hunter", "bank"

class LedgerEngine:
    def __init__(self):
        self.transactions: List[Transaction] = []
        self.budgets = {
            "Food": 600,
            "Tech": 200,
            "Travel": 1000,
            "Bills": 1500,
            "General": 300
        }
        # In real app, load from disk/DB

    def add_transaction(self, t: Transaction):
        """Add transaction to ledger."""
        self.transactions.append(t)
        # In real app, persist to DB

    def get_remaining_budget(self, category: str) -> float:
        """Calculate remaining budget for category."""
        limit = self.budgets.get(category, 100)
        spent = sum(t.amount for t in self.transactions if t.category == category)
        return limit - spent

    def get_total_spend(self, period="month") -> float:
        return sum(t.amount for t in self.transactions)

def get_ledger_engine():
    return LedgerEngine()
