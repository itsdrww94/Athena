#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       T H E   C O R R E L A T O R                              ║
║                   Engine D: Cross-Dataset Intelligence                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Finds hidden links between unrelated datasets.

Analysis:
1. Sleep → Spending correlation
2. Activity → Mood correlation  
3. Screen Time → Productivity correlation
4. Association Rule Mining
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import statistics

from .utils import normalize_timestamp


class Correlator:
    """
    Cross-dataset correlation engine.
    
    Finds hidden patterns like:
    - "When sleep < 6h, DoorDash orders increase 40%"
    - "Screen time spikes correlate with 'news' searches"
    """
    
    def __init__(self):
        # Daily data storage
        self.sleep_data = {}      # date -> hours slept
        self.spending_data = {}   # date -> total spent
        self.activity_data = {}   # date -> [(hour, type)]
        self.mood_data = {}       # date -> score (-1 to 1)
        self.screen_time = {}     # date -> dict of app -> minutes
        self.categories = {}      # date -> list of spending categories
    
    def add_sleep_data(self, date: date, hours: float) -> None:
        """Add sleep data for a date."""
        self.sleep_data[date] = hours
    
    def add_spending_data(self, date: date, amount: float, category: str = None) -> None:
        """Add spending data for a date."""
        if date not in self.spending_data:
            self.spending_data[date] = 0
            self.categories[date] = []
        
        self.spending_data[date] += amount
        if category:
            self.categories[date].append(category.lower())
    
    def add_activity_data(self, dt: datetime, activity_type: str = "general") -> None:
        """Add activity timestamp."""
        d = dt.date()
        if d not in self.activity_data:
            self.activity_data[d] = []
        self.activity_data[d].append((dt.hour, activity_type))
    
    def add_mood_data(self, date: date, score: float) -> None:
        """Add mood score for a date (-1 to 1)."""
        self.mood_data[date] = score
    
    def add_screen_time(self, date: date, app: str, minutes: int) -> None:
        """Add screen time data."""
        if date not in self.screen_time:
            self.screen_time[date] = {}
        self.screen_time[date][app] = minutes
    
    def correlate_sleep_spending(self) -> Dict[str, Any]:
        """
        Analyze if low sleep predicts higher spending.
        
        Hypothesis: Sleep deprivation leads to impulse purchases.
        """
        # Get dates with both sleep and spending data
        common_dates = set(self.sleep_data.keys()) & set(self.spending_data.keys())
        
        if len(common_dates) < 7:
            return {"error": "Need at least 7 days with both sleep and spending data"}
        
        # Split into low sleep (<6h) and normal sleep (>=6h)
        low_sleep_spending = []
        normal_sleep_spending = []
        
        for d in common_dates:
            sleep = self.sleep_data[d]
            spend = self.spending_data[d]
            
            if sleep < 6:
                low_sleep_spending.append(spend)
            else:
                normal_sleep_spending.append(spend)
        
        if not low_sleep_spending or not normal_sleep_spending:
            return {"error": "Not enough variance in sleep data"}
        
        avg_low = statistics.mean(low_sleep_spending)
        avg_normal = statistics.mean(normal_sleep_spending)
        
        if avg_normal > 0:
            increase_pct = ((avg_low - avg_normal) / avg_normal) * 100
        else:
            increase_pct = 0
        
        # Check for specific categories on low sleep days
        low_sleep_categories = []
        for d in common_dates:
            if self.sleep_data[d] < 6 and d in self.categories:
                low_sleep_categories.extend(self.categories[d])
        
        from collections import Counter
        common_low_sleep_purchases = Counter(low_sleep_categories).most_common(5)
        
        insight = None
        if increase_pct > 20:
            insight = f"⚠️ When sleep < 6h, spending increases by {increase_pct:.0f}%"
        elif increase_pct > 0:
            insight = f"Slight correlation: low sleep = {increase_pct:.0f}% more spending"
        else:
            insight = "✅ Sleep doesn't significantly affect spending"
        
        return {
            "correlation": "sleep_spending",
            "low_sleep_days": len(low_sleep_spending),
            "normal_sleep_days": len(normal_sleep_spending),
            "avg_spending_low_sleep": round(avg_low, 2),
            "avg_spending_normal_sleep": round(avg_normal, 2),
            "increase_pct": round(increase_pct, 2),
            "common_low_sleep_purchases": common_low_sleep_purchases,
            "insight": insight
        }
    
    def correlate_activity_mood(self) -> Dict[str, Any]:
        """
        Analyze if activity levels correlate with mood.
        """
        common_dates = set(self.activity_data.keys()) & set(self.mood_data.keys())
        
        if len(common_dates) < 7:
            return {"error": "Need at least 7 days of mood + activity data"}
        
        data_points = []
        for d in common_dates:
            activity_count = len(self.activity_data[d])
            mood = self.mood_data[d]
            data_points.append((activity_count, mood))
        
        # Simple correlation
        activity_scores = [x[0] for x in data_points]
        mood_scores = [x[1] for x in data_points]
        
        # High activity days
        median_activity = statistics.median(activity_scores)
        high_activity_moods = [m for a, m in data_points if a > median_activity]
        low_activity_moods = [m for a, m in data_points if a <= median_activity]
        
        if high_activity_moods and low_activity_moods:
            avg_high = statistics.mean(high_activity_moods)
            avg_low = statistics.mean(low_activity_moods)
            diff = avg_high - avg_low
            
            if diff > 0.2:
                insight = f"More activity → Better mood (+{diff:.2f} avg)"
            elif diff < -0.2:
                insight = f"Less activity → Better mood ({diff:.2f} avg)"
            else:
                insight = "Activity level doesn't strongly affect mood"
        else:
            insight = "Insufficient data for correlation"
            diff = 0
        
        return {
            "correlation": "activity_mood",
            "days_analyzed": len(common_dates),
            "mood_diff": round(diff, 3) if isinstance(diff, float) else diff,
            "insight": insight
        }
    
    def find_distraction_drivers(self) -> Dict[str, Any]:
        """
        Identify what triggers distraction/procrastination.
        
        Looks for screen time spikes and what precedes them.
        """
        if not self.screen_time:
            return {"error": "No screen time data"}
        
        # Find high screen time days
        total_daily = {d: sum(apps.values()) for d, apps in self.screen_time.items()}
        
        if not total_daily:
            return {"error": "No screen time data"}
        
        avg_time = statistics.mean(total_daily.values())
        high_days = [d for d, t in total_daily.items() if t > avg_time * 1.3]
        
        # What apps are used on high days
        high_day_apps = defaultdict(int)
        for d in high_days:
            for app, mins in self.screen_time.get(d, {}).items():
                high_day_apps[app] += mins
        
        top_distractions = sorted(high_day_apps.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "correlation": "distraction_drivers",
            "avg_screen_time_mins": round(avg_time, 0),
            "high_screen_time_days": len(high_days),
            "top_apps_on_high_days": top_distractions,
            "insight": f"Top distraction: {top_distractions[0][0]}" if top_distractions else "Unknown"
        }
    
    def find_associations(self) -> Dict[str, Any]:
        """
        Mine for association rules across datasets.
        
        Returns conditions and their outcomes.
        """
        rules = []
        
        # Rule 1: Sleep -> Spending
        sleep_spend = self.correlate_sleep_spending()
        if sleep_spend.get("increase_pct", 0) > 20:
            rules.append({
                "condition": "Sleep < 6 hours",
                "outcome": f"Spending +{sleep_spend['increase_pct']:.0f}%",
                "confidence": "high"
            })
        
        # Rule 2: Screen time -> specific apps
        distractions = self.find_distraction_drivers()
        if distractions.get("top_apps_on_high_days"):
            top_app = distractions["top_apps_on_high_days"][0][0]
            rules.append({
                "condition": "High screen time day",
                "outcome": f"Heavy usage of {top_app}",
                "confidence": "medium"
            })
        
        return {
            "association_rules": rules,
            "rules_found": len(rules)
        }
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run full correlation analysis.
        """
        return {
            "engine": "correlator",
            "data_points": {
                "sleep_days": len(self.sleep_data),
                "spending_days": len(self.spending_data),
                "activity_days": len(self.activity_data),
                "mood_days": len(self.mood_data),
                "screen_time_days": len(self.screen_time)
            },
            "sleep_spending": self.correlate_sleep_spending(),
            "activity_mood": self.correlate_activity_mood(),
            "distraction_drivers": self.find_distraction_drivers(),
            "association_rules": self.find_associations()
        }
