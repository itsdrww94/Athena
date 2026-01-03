"""
Finance Logic — Ported from finance_algo.js
============================================
Core Safe-to-Spend algorithm and spending analysis functions.

The algorithm determines if a purchase is financially safe based on:
1. Current balance
2. Proposed purchase price
3. Safety buffer (default $2000)
4. Upcoming bills consideration
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SafeToSpendResult:
    """Result of a safe-to-spend check."""
    approved: bool
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    current_balance: float
    purchase_price: float
    safety_buffer: float
    upcoming_bills: float
    available_to_spend: float
    remaining_after_purchase: Optional[float]
    message: str


@dataclass
class SpendingAnalysis:
    """Result of spending pattern analysis."""
    total_spent: float
    category_breakdown: List[Dict]
    top_category: str
    transaction_count: int


@dataclass
class DailyAllowance:
    """Daily spending allowance calculation."""
    remaining: float
    days_remaining: int
    daily_allowance: float
    on_track: bool
    message: str


# =============================================================================
# MAIN SAFE-TO-SPEND FUNCTION
# =============================================================================

def can_spend(
    current_balance: float,
    purchase_price: float,
    safety_buffer: float = 2000.0,
    upcoming_bills: float = 0.0
) -> SafeToSpendResult:
    """
    Determines if a purchase is safe to make.
    
    Args:
        current_balance: Current account balance
        purchase_price: Price of the item to buy
        safety_buffer: Minimum amount to keep in account (default: 2000)
        upcoming_bills: Sum of bills due in next 7 days (default: 0)
    
    Returns:
        SafeToSpendResult with approval status and details
    """
    available_balance = current_balance - safety_buffer - upcoming_bills
    can_afford = available_balance >= purchase_price
    remaining_after = available_balance - purchase_price if can_afford else None
    
    # Calculate risk level
    if remaining_after is None:
        risk_level = "HIGH"
    elif remaining_after < 500:
        risk_level = "HIGH"
    elif remaining_after < 1000:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    if can_afford:
        message = f"✅ Purchase approved. You'll have ${remaining_after:.2f} available after this purchase."
    else:
        shortfall = purchase_price - available_balance
        message = f"❌ Purchase not recommended. You need ${shortfall:.2f} more to safely afford this."
    
    return SafeToSpendResult(
        approved=can_afford,
        risk_level=risk_level,
        current_balance=current_balance,
        purchase_price=purchase_price,
        safety_buffer=safety_buffer,
        upcoming_bills=upcoming_bills,
        available_to_spend=max(0, available_balance),
        remaining_after_purchase=remaining_after,
        message=message
    )


# =============================================================================
# SPENDING ANALYSIS FUNCTIONS
# =============================================================================

def analyze_spending(transactions: List[Dict]) -> SpendingAnalysis:
    """
    Analyzes spending patterns from transaction history.
    
    Args:
        transactions: Array of transaction dicts with 'transaction_type', 
                      'category', and 'amount' keys
    
    Returns:
        SpendingAnalysis with category breakdown
    """
    category_totals: Dict[str, float] = {}
    total_spent = 0.0
    
    for t in transactions:
        if t.get("transaction_type") == "expense":
            category = t.get("category", "Uncategorized")
            amount = float(t.get("amount", 0))
            category_totals[category] = category_totals.get(category, 0) + amount
            total_spent += amount
    
    # Sort categories by spending (descending)
    sorted_categories = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    category_breakdown = [
        {
            "category": cat,
            "amount": amt,
            "percentage": f"{(amt / total_spent * 100):.1f}" if total_spent > 0 else "0.0"
        }
        for cat, amt in sorted_categories
    ]
    
    return SpendingAnalysis(
        total_spent=total_spent,
        category_breakdown=category_breakdown,
        top_category=sorted_categories[0][0] if sorted_categories else "None",
        transaction_count=len(transactions)
    )


def get_daily_allowance(
    monthly_budget: float,
    spent_so_far: float,
    days_remaining: int
) -> DailyAllowance:
    """
    Calculates daily spending allowance based on remaining budget.
    
    Args:
        monthly_budget: Total monthly budget
        spent_so_far: Amount spent this month
        days_remaining: Days left in the month
    
    Returns:
        DailyAllowance with daily budget info
    """
    remaining = monthly_budget - spent_so_far
    daily = remaining / max(1, days_remaining)
    
    # Check if on track (linear pacing)
    days_elapsed = 30 - days_remaining
    expected_spend = monthly_budget * (days_elapsed / 30)
    on_track = spent_so_far <= expected_spend
    
    if daily > 0:
        message = f"💰 You can spend ${daily:.2f} per day for the rest of the month."
    else:
        message = f"⚠️ You've exceeded your budget by ${abs(remaining):.2f}."
    
    return DailyAllowance(
        remaining=remaining,
        days_remaining=days_remaining,
        daily_allowance=max(0, daily),
        on_track=on_track,
        message=message
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def days_until_end_of_month() -> int:
    """Calculate days remaining in current month."""
    today = datetime.now()
    if today.month == 12:
        next_month = datetime(today.year + 1, 1, 1)
    else:
        next_month = datetime(today.year, today.month + 1, 1)
    return (next_month - today).days
