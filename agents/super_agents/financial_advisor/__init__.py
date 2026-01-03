"""
Financial Advisor Package
=========================
Athena Finance Division 2.0

Components:
- finance_logic: Safe-to-Spend calculations
- bank_ecosystem: Five-Bank Model
- card_optimizer: Deal Registry
- smart_transfer: Transfer Recommendations
- sentinel: Background Monitoring
- notion_sync: Notion Integration
"""

from .finance_logic import can_spend, get_daily_allowance, analyze_spending
from .bank_ecosystem import get_bank_ecosystem, BankEcosystem
from .card_optimizer import get_card_optimizer, CardOptimizer
from .smart_transfer import SmartTransfer, get_smart_transfer
from .sentinel import get_finance_sentinel, FinanceSentinel
from .risk_engine import get_risk_engine
from .plan_engine import get_plan_engine

__all__ = [
    # Finance Logic
    "can_spend",
    "get_daily_allowance",
    "analyze_spending",
    # Bank Ecosystem
    "get_bank_ecosystem",
    "BankEcosystem",
    # Card Optimizer
    "get_card_optimizer",
    "CardOptimizer",
    # Smart Transfer
    "SmartTransfer",
    "get_smart_transfer",
    # Sentinel
    "get_finance_sentinel",
    "FinanceSentinel",
    # Legacy Engines
    "get_risk_engine",
    "get_plan_engine",
]
