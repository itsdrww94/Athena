"""
Bank Ecosystem — Five-Bank Model
================================
Models the user's multi-bank financial structure with strict "job descriptions."

Banks:
1. Chase (Hub) — Paycheck ingress, routing
2. Bank of America (Bill Vault) — Fixed bills only
3. Capital One Checking (Fun) — Daily discretionary
4. Capital One Credit (Subs) — Recurring subscriptions
5. Chime (HYSA) — Savings & surplus
6. Robinhood (Assets) — Investments (excluded from liquidity)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum


class BankRole(Enum):
    HUB = "hub"              # Paycheck ingress
    BILLS = "bills"          # Fixed expenses
    FUN = "fun"              # Discretionary
    SUBS = "subs"            # Subscriptions
    SAVINGS = "savings"      # Reserve
    ASSETS = "assets"        # Investments


@dataclass
class RecurringBill:
    """A recurring bill or subscription."""
    name: str
    amount: float
    due_day: int  # Day of month (1-31)
    category: str
    bank_id: str  # Which bank pays this


@dataclass
class Deposit:
    """A detected deposit/income."""
    amount: float
    source: str
    timestamp: datetime
    bank_id: str


@dataclass
class BankAccount:
    """Represents a single bank account."""
    id: str
    name: str
    role: BankRole
    balance: float = 0.0
    pending: float = 0.0
    last_updated: Optional[datetime] = None
    excluded_from_liquidity: bool = False
    
    @property
    def available(self) -> float:
        """Available balance (balance minus pending)."""
        return self.balance - self.pending


# =============================================================================
# DEFAULT BANK CONFIGURATION
# =============================================================================

DEFAULT_BANKS: Dict[str, BankAccount] = {
    "chase": BankAccount(
        id="chase",
        name="Chase Checking",
        role=BankRole.HUB,
    ),
    "boa": BankAccount(
        id="boa",
        name="Bank of America",
        role=BankRole.BILLS,
    ),
    "cap1_checking": BankAccount(
        id="cap1_checking",
        name="Capital One 360 Checking",
        role=BankRole.FUN,
    ),
    "cap1_credit": BankAccount(
        id="cap1_credit",
        name="Capital One Savor",
        role=BankRole.SUBS,
    ),
    "chime": BankAccount(
        id="chime",
        name="Chime HYSA",
        role=BankRole.SAVINGS,
    ),
    "robinhood": BankAccount(
        id="robinhood",
        name="Robinhood",
        role=BankRole.ASSETS,
        excluded_from_liquidity=True,
    ),
}


@dataclass
class SafeToSpendResult:
    """Result of ecosystem-wide safe-to-spend check."""
    approved: bool
    available: float
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    message: str


class BankEcosystem:
    """
    Manages the Five-Bank Ecosystem.
    Tracks balances, calculates liquidity, and coordinates transfers.
    """
    
    SAFETY_BUFFER = 2000.0  # Minimum reserve
    
    def __init__(self):
        # Deep copy default banks
        self.accounts: Dict[str, BankAccount] = {
            k: BankAccount(
                id=v.id,
                name=v.name,
                role=v.role,
                balance=v.balance,
                excluded_from_liquidity=v.excluded_from_liquidity
            )
            for k, v in DEFAULT_BANKS.items()
        }
        self.bills: List[RecurringBill] = []
        self.recent_deposits: List[Deposit] = []
    
    def get_account(self, account_id: str) -> Optional[BankAccount]:
        """Get account by ID."""
        return self.accounts.get(account_id)
    
    def update_balance(self, account_id: str, balance: float, pending: float = 0.0):
        """Update an account's balance."""
        if account_id in self.accounts:
            self.accounts[account_id].balance = balance
            self.accounts[account_id].pending = pending
            self.accounts[account_id].last_updated = datetime.now()
    
    def get_total_liquid(self) -> float:
        """Sum of all non-excluded account balances."""
        return sum(
            acc.available
            for acc in self.accounts.values()
            if not acc.excluded_from_liquidity
        )
    
    def get_upcoming_bills(self, days: int = 7) -> float:
        """Sum of bills due within the next N days."""
        today = datetime.now()
        total = 0.0
        
        for bill in self.bills:
            # Calculate next due date
            due_date = datetime(today.year, today.month, min(bill.due_day, 28))
            if due_date < today:
                # Bill already passed this month, check next month
                if today.month == 12:
                    due_date = datetime(today.year + 1, 1, min(bill.due_day, 28))
                else:
                    due_date = datetime(today.year, today.month + 1, min(bill.due_day, 28))
            
            if (due_date - today).days <= days:
                total += bill.amount
        
        return total
    
    def safe_to_spend(self, amount: float) -> SafeToSpendResult:
        """
        Ecosystem-wide safe-to-spend check.
        Considers total liquidity, upcoming bills, and safety buffer.
        """
        liquid = self.get_total_liquid()
        upcoming = self.get_upcoming_bills(7)
        available = liquid - self.SAFETY_BUFFER - upcoming
        
        approved = available >= amount
        
        # Risk level
        if available < 500:
            risk = "HIGH"
        elif available < 1000:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        
        if approved:
            remaining = available - amount
            msg = f"✅ Approved. ${remaining:.2f} remains after purchase."
        else:
            shortfall = amount - available
            msg = f"❌ Not recommended. Need ${shortfall:.2f} more."
        
        return SafeToSpendResult(
            approved=approved,
            available=max(0, available),
            risk_level=risk,
            message=msg
        )
    
    def add_bill(self, name: str, amount: float, due_day: int, category: str, bank_id: str = "boa"):
        """Register a recurring bill."""
        self.bills.append(RecurringBill(
            name=name,
            amount=amount,
            due_day=due_day,
            category=category,
            bank_id=bank_id
        ))
    
    def record_deposit(self, account_id: str, amount: float, source: str = "Unknown"):
        """Record a deposit for payday routing logic."""
        self.recent_deposits.append(Deposit(
            amount=amount,
            source=source,
            timestamp=datetime.now(),
            bank_id=account_id
        ))
    
    def get_recent_deposits(self, account_id: str, hours: int = 24) -> List[Deposit]:
        """Get deposits to an account within the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            d for d in self.recent_deposits
            if d.bank_id == account_id and d.timestamp >= cutoff
        ]
    
    def calculate_payday_split(self, paycheck_amount: float) -> Dict[str, float]:
        """
        Calculate recommended split for a paycheck.
        Default: 60% Bills, 30% Fun, 10% Savings
        """
        return {
            "bills": paycheck_amount * 0.60,
            "fun": paycheck_amount * 0.30,
            "savings": paycheck_amount * 0.10,
        }
    
    def get_velocity(self, account_id: str = "cap1_checking", days_until_payday: int = 14) -> float:
        """
        Calculate daily burn rate for an account.
        Returns how much can be spent per day until payday.
        """
        account = self.get_account(account_id)
        if not account:
            return 0.0
        return account.available / max(1, days_until_payday)


# =============================================================================
# SINGLETON
# =============================================================================

_ecosystem_instance: Optional[BankEcosystem] = None


def get_bank_ecosystem() -> BankEcosystem:
    """Get or create the bank ecosystem singleton."""
    global _ecosystem_instance
    if _ecosystem_instance is None:
        _ecosystem_instance = BankEcosystem()
    return _ecosystem_instance
