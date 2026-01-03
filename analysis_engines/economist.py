#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                 T H E   B E H A V I O R A L   E C O N O M I S T               ║
║                    Engine C: Spending Psychology                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Identifies emotional spending triggers and financial patterns.

Analysis:
1. Vampire Spend Index - Late night impulse purchases
2. Lifestyle Creep Detector - Discretionary vs essential trends
3. Category Analysis - Where money goes
4. Spending Velocity - Acceleration/deceleration over time
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics

from .utils import normalize_timestamp, get_hour_of_day, safe_divide, calculate_moving_average


class BehavioralEconomist:
    """
    Analyzes spending patterns and financial psychology.
    """
    
    # Category classifications
    DISCRETIONARY_CATEGORIES = {
        "dining", "restaurants", "food delivery", "doordash", "ubereats", "grubhub",
        "entertainment", "streaming", "gaming", "games", "apps", "subscriptions",
        "shopping", "amazon", "electronics", "clothing", "fashion",
        "travel", "hotels", "flights", "vacation"
    }
    
    ESSENTIAL_CATEGORIES = {
        "groceries", "grocery", "utilities", "rent", "mortgage", "insurance",
        "gas", "fuel", "transportation", "medical", "pharmacy", "healthcare",
        "phone", "internet", "bills"
    }
    
    def __init__(self):
        self.transactions = []  # List of (timestamp, amount, category, description)
        self.daily_totals = defaultdict(float)
        self.monthly_totals = defaultdict(float)
        self.category_totals = defaultdict(float)
    
    def add_transaction(self, timestamp: datetime, amount: float, 
                        category: str = "", description: str = "") -> None:
        """Add a transaction for analysis."""
        if timestamp and amount != 0:
            self.transactions.append({
                "timestamp": timestamp,
                "amount": abs(amount),  # Normalize to positive
                "category": category.lower() if category else "uncategorized",
                "description": description.lower() if description else ""
            })
            
            date_key = timestamp.date()
            month_key = timestamp.strftime("%Y-%m")
            
            self.daily_totals[date_key] += abs(amount)
            self.monthly_totals[month_key] += abs(amount)
            self.category_totals[category.lower()] += abs(amount)
    
    def load_from_csv(self, filepath: str, date_col: str = "Date", 
                      amount_col: str = "Amount", category_col: str = "Category",
                      desc_col: str = "Description") -> int:
        """Load transactions from a CSV file."""
        try:
            import pandas as pd
            df = pd.read_csv(filepath)
            
            count = 0
            for _, row in df.iterrows():
                ts = normalize_timestamp(row.get(date_col))
                amount = float(row.get(amount_col, 0))
                category = str(row.get(category_col, ""))
                desc = str(row.get(desc_col, ""))
                
                if ts:
                    self.add_transaction(ts, amount, category, desc)
                    count += 1
            
            return count
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return 0
    
    def get_vampire_spend_index(self) -> Dict[str, Any]:
        """
        Calculate the "Vampire Spend" - late night impulse purchases.
        
        Purchases between 11 PM and 4 AM are flagged as potential impulse buys.
        """
        vampire_hours = set(range(23, 24)) | set(range(0, 5))  # 23:00 - 04:59
        
        vampire_spend = 0
        normal_spend = 0
        vampire_transactions = []
        
        for txn in self.transactions:
            hour = get_hour_of_day(txn["timestamp"])
            
            if hour in vampire_hours:
                vampire_spend += txn["amount"]
                vampire_transactions.append({
                    "time": txn["timestamp"].strftime("%Y-%m-%d %H:%M"),
                    "amount": txn["amount"],
                    "category": txn["category"]
                })
            else:
                normal_spend += txn["amount"]
        
        total_spend = vampire_spend + normal_spend
        
        if total_spend == 0:
            return {"error": "No spending data"}
        
        vampire_pct = (vampire_spend / total_spend) * 100
        
        # Flag concerning behavior
        if vampire_pct > 10:
            flag = "⚠️ High dopamine shopping risk - 10%+ late night spending"
        elif vampire_pct > 5:
            flag = "Moderate impulse risk"
        else:
            flag = "✅ Healthy spending patterns"
        
        return {
            "vampire_spend": round(vampire_spend, 2),
            "total_spend": round(total_spend, 2),
            "vampire_pct": round(vampire_pct, 2),
            "flag": flag,
            "vampire_transactions": vampire_transactions[:10],  # Top 10 examples
            "insight": f"{vampire_pct:.1f}% of spending happens between 11PM-4AM"
        }
    
    def get_lifestyle_creep_detector(self, months: int = 6) -> Dict[str, Any]:
        """
        Detect lifestyle creep by comparing discretionary vs essential spending trends.
        """
        monthly_discretionary = defaultdict(float)
        monthly_essential = defaultdict(float)
        
        for txn in self.transactions:
            month = txn["timestamp"].strftime("%Y-%m")
            category = txn["category"]
            amount = txn["amount"]
            
            # Classify
            is_discretionary = any(d in category or d in txn["description"] 
                                   for d in self.DISCRETIONARY_CATEGORIES)
            is_essential = any(e in category or e in txn["description"]
                              for e in self.ESSENTIAL_CATEGORIES)
            
            if is_discretionary:
                monthly_discretionary[month] += amount
            elif is_essential:
                monthly_essential[month] += amount
        
        if len(monthly_discretionary) < 2:
            return {"error": "Need at least 2 months of data"}
        
        # Get last N months
        sorted_months = sorted(monthly_discretionary.keys())[-months:]
        
        disc_values = [monthly_discretionary[m] for m in sorted_months]
        ess_values = [monthly_essential[m] for m in sorted_months]
        
        # Calculate growth rates
        if len(disc_values) >= 2 and disc_values[0] > 0:
            disc_growth = ((disc_values[-1] - disc_values[0]) / disc_values[0]) * 100
        else:
            disc_growth = 0
        
        if len(ess_values) >= 2 and ess_values[0] > 0:
            ess_growth = ((ess_values[-1] - ess_values[0]) / ess_values[0]) * 100
        else:
            ess_growth = 0
        
        # Detect creep
        if disc_growth > ess_growth * 2 and disc_growth > 20:
            flag = "⚠️ Lifestyle creep detected - discretionary spending growing 2x faster"
        elif disc_growth > ess_growth and disc_growth > 10:
            flag = "Moderate lifestyle expansion"
        else:
            flag = "✅ Spending growth balanced"
        
        return {
            "discretionary_growth_pct": round(disc_growth, 2),
            "essential_growth_pct": round(ess_growth, 2),
            "discretionary_trend": disc_values,
            "essential_trend": ess_values,
            "months_analyzed": sorted_months,
            "flag": flag,
            "insight": f"Discretionary: {disc_growth:+.1f}%, Essential: {ess_growth:+.1f}%"
        }
    
    def get_category_breakdown(self) -> Dict[str, Any]:
        """Get spending breakdown by category."""
        total = sum(self.category_totals.values())
        
        breakdown = []
        for cat, amount in sorted(self.category_totals.items(), 
                                   key=lambda x: x[1], reverse=True):
            pct = (amount / total * 100) if total > 0 else 0
            breakdown.append({
                "category": cat,
                "amount": round(amount, 2),
                "pct": round(pct, 2)
            })
        
        return {
            "total_spent": round(total, 2),
            "categories": breakdown[:15],  # Top 15
            "top_category": breakdown[0]["category"] if breakdown else "unknown"
        }
    
    def get_spending_velocity(self) -> Dict[str, Any]:
        """
        Analyze spending acceleration/deceleration over time.
        """
        if len(self.monthly_totals) < 3:
            return {"error": "Need at least 3 months of data"}
        
        sorted_months = sorted(self.monthly_totals.items())
        values = [v for _, v in sorted_months]
        
        # Calculate month-over-month changes
        changes = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                change = ((values[i] - values[i-1]) / values[i-1]) * 100
            else:
                change = 0
            changes.append(change)
        
        avg_change = statistics.mean(changes) if changes else 0
        
        # Moving average
        ma = calculate_moving_average(values, 3)
        
        if avg_change > 10:
            trend = "📈 Spending accelerating"
        elif avg_change < -10:
            trend = "📉 Spending decelerating"
        else:
            trend = "➡️ Spending stable"
        
        return {
            "avg_monthly_change_pct": round(avg_change, 2),
            "trend": trend,
            "monthly_values": values[-6:],  # Last 6 months
            "moving_average": ma[-6:] if len(ma) >= 6 else ma
        }
    
    def get_spending_triggers(self) -> List[str]:
        """Identify potential spending triggers based on patterns."""
        triggers = []
        
        # Check vampire spending
        vampire = self.get_vampire_spend_index()
        if vampire.get("vampire_pct", 0) > 10:
            triggers.append("Late Night / Sleep Deprivation")
        
        # Check lifestyle creep
        creep = self.get_lifestyle_creep_detector()
        if "creep detected" in creep.get("flag", "").lower():
            triggers.append("Lifestyle Creep")
        
        # Check for category spikes
        categories = self.get_category_breakdown()
        top_cats = [c["category"] for c in categories.get("categories", [])[:3]]
        
        for cat in top_cats:
            if any(d in cat for d in ["doordash", "ubereats", "delivery"]):
                triggers.append("Food Delivery / Convenience")
            elif any(d in cat for d in ["amazon", "shopping"]):
                triggers.append("Online Shopping")
        
        return triggers
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run full behavioral economics analysis.
        """
        return {
            "engine": "behavioral_economist",
            "transactions_analyzed": len(self.transactions),
            "vampire_spending": self.get_vampire_spend_index(),
            "lifestyle_creep": self.get_lifestyle_creep_detector(),
            "category_breakdown": self.get_category_breakdown(),
            "spending_velocity": self.get_spending_velocity(),
            "triggers": self.get_spending_triggers()
        }
