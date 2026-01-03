#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     T H E   C H R O N O B I O L O G I S T                     ║
║                       Engine A: Time & Energy                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Determines the user's biological rhythm for optimal task scheduling.

Analysis:
1. Activity Heatmap - Peak focus hours, digital downtime
2. Sleep Consistency Index - Wake time variance
3. Weekend vs Weekday patterns
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics

from .utils import normalize_timestamp, get_hour_of_day, get_day_of_week


class Chronobiologist:
    """
    Analyzes time-based patterns to determine chronotype and optimal scheduling.
    """
    
    def __init__(self):
        self.activities = []  # List of (timestamp, activity_type) tuples
        self.daily_first_activity = {}  # date -> first timestamp
        self.daily_last_activity = {}   # date -> last timestamp
    
    def add_activity(self, timestamp: datetime, activity_type: str = "general") -> None:
        """Add an activity timestamp for analysis."""
        if timestamp:
            self.activities.append((timestamp, activity_type))
            
            date_key = timestamp.date()
            
            # Track first and last activity per day
            if date_key not in self.daily_first_activity:
                self.daily_first_activity[date_key] = timestamp
            else:
                if timestamp < self.daily_first_activity[date_key]:
                    self.daily_first_activity[date_key] = timestamp
            
            if date_key not in self.daily_last_activity:
                self.daily_last_activity[date_key] = timestamp
            else:
                if timestamp > self.daily_last_activity[date_key]:
                    self.daily_last_activity[date_key] = timestamp
    
    def load_from_dataframe(self, df, timestamp_col: str = "timestamp", 
                            activity_col: str = None) -> int:
        """Load activities from a pandas DataFrame."""
        count = 0
        for _, row in df.iterrows():
            ts = normalize_timestamp(row[timestamp_col])
            activity = row[activity_col] if activity_col else "general"
            if ts:
                self.add_activity(ts, activity)
                count += 1
        return count
    
    def get_activity_heatmap(self) -> Dict[int, int]:
        """
        Generate hourly activity heatmap.
        
        Returns:
            Dict mapping hour (0-23) to activity count
        """
        heatmap = defaultdict(int)
        
        for ts, _ in self.activities:
            hour = get_hour_of_day(ts)
            if hour is not None:
                heatmap[hour] += 1
        
        return dict(heatmap)
    
    def get_peak_focus_window(self) -> Dict[str, Any]:
        """
        Identify the user's peak focus hours.
        
        Returns:
            Dict with peak_start, peak_end, peak_hours, downtime_hours
        """
        heatmap = self.get_activity_heatmap()
        
        if not heatmap:
            return {"error": "No activity data"}
        
        # Find top 25% of hours by activity
        sorted_hours = sorted(heatmap.items(), key=lambda x: x[1], reverse=True)
        total_hours = len(sorted_hours)
        top_count = max(3, total_hours // 4)
        
        peak_hours = sorted([h[0] for h in sorted_hours[:top_count]])
        
        # Find continuous peak window
        if peak_hours:
            peak_start = peak_hours[0]
            peak_end = peak_hours[-1]
        else:
            peak_start = 9
            peak_end = 17
        
        # Find downtime (bottom 25%)
        bottom_hours = sorted([h[0] for h in sorted_hours[-top_count:]])
        
        return {
            "peak_start": peak_start,
            "peak_end": peak_end,
            "peak_hours": peak_hours,
            "downtime_hours": bottom_hours,
            "total_activities": len(self.activities),
            "insight": f"Peak focus: {peak_start}:00-{peak_end}:00"
        }
    
    def get_sleep_consistency_index(self) -> Dict[str, Any]:
        """
        Calculate sleep pattern consistency.
        
        Uses first/last activity times as proxy for wake/sleep times.
        
        Returns:
            Dict with wake_std_minutes, sleep_std_minutes, consistency_score
        """
        if len(self.daily_first_activity) < 7:
            return {"error": "Need at least 7 days of data"}
        
        # Extract wake times (hour + minute as decimal)
        wake_minutes = []
        sleep_minutes = []
        
        for date, wake_ts in self.daily_first_activity.items():
            wake_minutes.append(wake_ts.hour * 60 + wake_ts.minute)
            
            if date in self.daily_last_activity:
                sleep_ts = self.daily_last_activity[date]
                sleep_minutes.append(sleep_ts.hour * 60 + sleep_ts.minute)
        
        wake_std = statistics.stdev(wake_minutes) if len(wake_minutes) >= 2 else 0
        sleep_std = statistics.stdev(sleep_minutes) if len(sleep_minutes) >= 2 else 0
        
        # Calculate average wake/sleep times
        avg_wake_mins = statistics.mean(wake_minutes) if wake_minutes else 0
        avg_sleep_mins = statistics.mean(sleep_minutes) if sleep_minutes else 0
        
        avg_wake_hour = int(avg_wake_mins // 60)
        avg_wake_min = int(avg_wake_mins % 60)
        avg_sleep_hour = int(avg_sleep_mins // 60)
        avg_sleep_min = int(avg_sleep_mins % 60)
        
        # Consistency score (lower std = more consistent)
        # 100 = very consistent (<15min std), 0 = very inconsistent (>120min std)
        consistency = max(0, 100 - (wake_std / 1.2))
        
        # Flag irregular patterns
        insights = []
        if wake_std > 60:
            insights.append("⚠️ Irregular wake times (>1hr variance)")
        if sleep_std > 90:
            insights.append("⚠️ Irregular sleep times (>1.5hr variance)")
        if consistency > 80:
            insights.append("✅ Consistent sleep schedule")
        
        return {
            "avg_wake_time": f"{avg_wake_hour:02d}:{avg_wake_min:02d}",
            "avg_sleep_time": f"{avg_sleep_hour:02d}:{avg_sleep_min:02d}",
            "wake_std_minutes": round(wake_std, 1),
            "sleep_std_minutes": round(sleep_std, 1),
            "consistency_score": round(consistency, 1),
            "days_analyzed": len(self.daily_first_activity),
            "insights": insights
        }
    
    def get_weekday_vs_weekend(self) -> Dict[str, Any]:
        """Compare activity patterns weekdays vs weekends."""
        weekday_hours = defaultdict(int)
        weekend_hours = defaultdict(int)
        
        for ts, _ in self.activities:
            hour = get_hour_of_day(ts)
            day = get_day_of_week(ts)
            
            if hour is not None and day is not None:
                if day < 5:  # Mon-Fri
                    weekday_hours[hour] += 1
                else:  # Sat-Sun
                    weekend_hours[hour] += 1
        
        # Find peak hours for each
        weekday_peak = max(weekday_hours.items(), key=lambda x: x[1])[0] if weekday_hours else None
        weekend_peak = max(weekend_hours.items(), key=lambda x: x[1])[0] if weekend_hours else None
        
        return {
            "weekday_peak_hour": weekday_peak,
            "weekend_peak_hour": weekend_peak,
            "weekday_activities": sum(weekday_hours.values()),
            "weekend_activities": sum(weekend_hours.values()),
            "shift": (weekend_peak - weekday_peak) if weekday_peak and weekend_peak else 0
        }
    
    def get_chronotype(self) -> Dict[str, Any]:
        """
        Determine user's chronotype (morning person vs night owl).
        
        Returns:
            Dict with chronotype label and supporting data
        """
        heatmap = self.get_activity_heatmap()
        
        if not heatmap:
            return {"chronotype": "unknown"}
        
        # Calculate morning (6-12) vs evening (18-24) activity
        morning_activity = sum(heatmap.get(h, 0) for h in range(6, 12))
        evening_activity = sum(heatmap.get(h, 0) for h in range(18, 24))
        afternoon_activity = sum(heatmap.get(h, 0) for h in range(12, 18))
        
        total = morning_activity + afternoon_activity + evening_activity
        
        if total == 0:
            return {"chronotype": "unknown"}
        
        morning_pct = (morning_activity / total) * 100
        evening_pct = (evening_activity / total) * 100
        
        if morning_pct > evening_pct + 10:
            chronotype = "early_bird"
            description = "Morning person - most productive before noon"
        elif evening_pct > morning_pct + 10:
            chronotype = "night_owl"
            description = "Night owl - peak energy in the evening"
        else:
            chronotype = "balanced"
            description = "Balanced schedule - consistent throughout day"
        
        return {
            "chronotype": chronotype,
            "description": description,
            "morning_pct": round(morning_pct, 1),
            "afternoon_pct": round((afternoon_activity / total) * 100, 1),
            "evening_pct": round(evening_pct, 1)
        }
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run full chronobiological analysis.
        
        Returns:
            Complete chronotype profile
        """
        return {
            "engine": "chronobiologist",
            "activities_analyzed": len(self.activities),
            "days_covered": len(self.daily_first_activity),
            "chronotype": self.get_chronotype(),
            "peak_focus": self.get_peak_focus_window(),
            "sleep_consistency": self.get_sleep_consistency_index(),
            "weekday_vs_weekend": self.get_weekday_vs_weekend(),
            "heatmap": self.get_activity_heatmap()
        }
