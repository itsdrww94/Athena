#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        H E A L T H   S Y N C                                  ║
║                          "The Coach"                                           ║
║                                                                               ║
║  Division III: LifeOS (Health & Leisure)                                      ║
║  Sync Samsung Watch data and analyze health trends                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
  - Google Fit API integration (Samsung Health → Google Fit → Athena)
  - Sleep analysis with Deep Sleep tracking
  - Step count monitoring
  - Trend analysis with Gemini insights

Usage:
  python health_sync.py --action summary
  python health_sync.py --action sleep
  python health_sync.py --action steps --days 7
"""

import os
import sys
import json
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Health targets
DAILY_STEP_GOAL = 10000
SLEEP_GOAL_HOURS = 7.5
DEEP_SLEEP_MIN_PERCENT = 15


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SleepData:
    """Sleep session data."""
    date: str
    total_hours: float
    deep_sleep_minutes: int
    light_sleep_minutes: int
    rem_minutes: int
    awake_minutes: int
    
    @property
    def deep_sleep_percent(self) -> float:
        total_minutes = self.total_hours * 60
        if total_minutes <= 0:
            return 0
        return (self.deep_sleep_minutes / total_minutes) * 100
    
    @property
    def quality_score(self) -> int:
        """Calculate sleep quality 0-100."""
        score = 50
        
        # Duration score
        if self.total_hours >= 7 and self.total_hours <= 9:
            score += 25
        elif self.total_hours >= 6:
            score += 15
        
        # Deep sleep score
        if self.deep_sleep_percent >= 20:
            score += 25
        elif self.deep_sleep_percent >= 15:
            score += 15
        elif self.deep_sleep_percent >= 10:
            score += 5
        
        return min(100, score)


@dataclass
class StepData:
    """Daily step count."""
    date: str
    steps: int
    distance_km: float
    calories: int
    
    @property
    def goal_percent(self) -> float:
        return (self.steps / DAILY_STEP_GOAL) * 100


# =============================================================================
# GOOGLE FIT API
# =============================================================================

def get_google_fit_service():
    """Get authenticated Google Fit service."""
    try:
        from services.google_service import get_google_service
        
        google = get_google_service()
        if google.is_authenticated():
            return google
        return None
        
    except ImportError:
        return None


def fetch_steps_from_fit(days: int = 7) -> List[StepData]:
    """
    Fetch step data from Google Fit.
    
    Note: Requires Google Fit API scope to be added to Google Service.
    For now, returns sample data for demo.
    """
    # In production, this would use Google Fit REST API
    # See: https://developers.google.com/fit/rest/v1/get-started
    
    # Sample data for demo
    sample_data = []
    for i in range(days):
        d = date.today() - timedelta(days=i)
        sample_data.append(StepData(
            date=d.isoformat(),
            steps=int(7500 + (i * 500) + (hash(str(d)) % 3000)),
            distance_km=round(5.2 + (hash(str(d)) % 20) / 10, 1),
            calories=int(250 + (hash(str(d)) % 150))
        ))
    
    return sample_data


def fetch_sleep_from_fit(days: int = 7) -> List[SleepData]:
    """
    Fetch sleep data from Google Fit.
    
    Note: Samsung Health → Google Fit sync required.
    Returns sample data for demo.
    """
    sample_data = []
    for i in range(days):
        d = date.today() - timedelta(days=i)
        total = 6.5 + (hash(str(d)) % 30) / 10
        
        sample_data.append(SleepData(
            date=d.isoformat(),
            total_hours=round(total, 1),
            deep_sleep_minutes=int(60 + (hash(str(d)) % 40)),
            light_sleep_minutes=int(180 + (hash(str(d)) % 60)),
            rem_minutes=int(80 + (hash(str(d)) % 30)),
            awake_minutes=int(10 + (hash(str(d)) % 20))
        ))
    
    return sample_data


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_with_gemini(health_data: Dict[str, Any]) -> Optional[str]:
    """Use Gemini to provide health insights."""
    if not GEMINI_API_KEY:
        return None
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""Analyze this health data and provide 3 actionable insights:

{json.dumps(health_data, indent=2)}

Focus on:
1. Sleep quality improvements
2. Activity level recommendations
3. Specific habit changes

Be concise and encouraging. This is for a Minneapolis-based tech worker.
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return None


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_sleep_report(sleep_data: List[SleepData]) -> str:
    """Format sleep data for display."""
    output = []
    output.append("=" * 60)
    output.append("😴 HEALTH SYNC - Sleep Analysis")
    output.append("=" * 60)
    output.append("")
    
    if not sleep_data:
        output.append("📭 No sleep data available.")
        return "\n".join(output)
    
    # Latest night
    latest = sleep_data[0]
    output.append(f"🌙 Last Night ({latest.date}):")
    output.append(f"   Total Sleep: {latest.total_hours:.1f} hours")
    output.append(f"   Deep Sleep:  {latest.deep_sleep_minutes} min ({latest.deep_sleep_percent:.0f}%)")
    output.append(f"   REM Sleep:   {latest.rem_minutes} min")
    output.append(f"   Quality:     {latest.quality_score}/100")
    output.append("")
    
    # Warning if deep sleep is low
    if latest.deep_sleep_percent < DEEP_SLEEP_MIN_PERCENT:
        output.append(f"⚠️  Deep sleep below {DEEP_SLEEP_MIN_PERCENT}% - consider:")
        output.append("   • Avoid caffeine after 2pm")
        output.append("   • Keep bedroom cooler (65-68°F)")
        output.append("   • Limit screen time before bed")
        output.append("")
    
    # Weekly average
    avg_hours = sum(s.total_hours for s in sleep_data) / len(sleep_data)
    avg_deep = sum(s.deep_sleep_percent for s in sleep_data) / len(sleep_data)
    avg_quality = sum(s.quality_score for s in sleep_data) / len(sleep_data)
    
    output.append(f"📊 7-Day Averages:")
    output.append(f"   Avg Sleep:   {avg_hours:.1f} hours")
    output.append(f"   Avg Deep:    {avg_deep:.0f}%")
    output.append(f"   Avg Quality: {avg_quality:.0f}/100")
    
    output.append("")
    output.append("=" * 60)
    
    return "\n".join(output)


def format_steps_report(steps_data: List[StepData]) -> str:
    """Format step data for display."""
    output = []
    output.append("=" * 60)
    output.append("👟 HEALTH SYNC - Activity Report")
    output.append("=" * 60)
    output.append("")
    
    if not steps_data:
        output.append("📭 No step data available.")
        return "\n".join(output)
    
    # Today
    today = steps_data[0]
    bar_len = int(today.goal_percent / 5)  # 20 chars = 100%
    bar = "█" * min(bar_len, 20) + "░" * max(0, 20 - bar_len)
    
    output.append(f"📍 Today ({today.date}):")
    output.append(f"   Steps:    {today.steps:,} / {DAILY_STEP_GOAL:,}")
    output.append(f"   Progress: [{bar}] {today.goal_percent:.0f}%")
    output.append(f"   Distance: {today.distance_km} km")
    output.append(f"   Calories: {today.calories}")
    output.append("")
    
    # Check goal
    if today.steps >= DAILY_STEP_GOAL:
        output.append("🎉 Great job! You hit your step goal!")
    else:
        remaining = DAILY_STEP_GOAL - today.steps
        output.append(f"💪 {remaining:,} steps to go!")
    
    output.append("")
    
    # Weekly summary
    total_steps = sum(s.steps for s in steps_data)
    avg_steps = total_steps / len(steps_data)
    goal_days = sum(1 for s in steps_data if s.steps >= DAILY_STEP_GOAL)
    
    output.append(f"📊 7-Day Summary:")
    output.append(f"   Total Steps:  {total_steps:,}")
    output.append(f"   Daily Avg:    {avg_steps:,.0f}")
    output.append(f"   Goals Hit:    {goal_days}/{len(steps_data)} days")
    
    output.append("")
    output.append("=" * 60)
    
    return "\n".join(output)


def format_summary(sleep_data: List[SleepData], steps_data: List[StepData]) -> str:
    """Format combined health summary."""
    output = []
    output.append("=" * 60)
    output.append("🏥 HEALTH SYNC - Daily Summary")
    output.append(f"📅 {date.today().strftime('%B %d, %Y')}")
    output.append("=" * 60)
    output.append("")
    
    # Sleep
    if sleep_data:
        latest_sleep = sleep_data[0]
        sleep_emoji = "✅" if latest_sleep.quality_score >= 70 else "⚠️"
        output.append(f"😴 Sleep: {latest_sleep.total_hours:.1f}h (Quality: {latest_sleep.quality_score}/100) {sleep_emoji}")
    
    # Steps
    if steps_data:
        today_steps = steps_data[0]
        steps_emoji = "✅" if today_steps.steps >= DAILY_STEP_GOAL else "🔄"
        output.append(f"👟 Steps: {today_steps.steps:,} / {DAILY_STEP_GOAL:,} {steps_emoji}")
    
    output.append("")
    output.append("=" * 60)
    
    return "\n".join(output)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Health Sync - Track sleep and activity"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["summary", "sleep", "steps", "analyze"],
        default="summary",
        help="Report type"
    )
    
    parser.add_argument("--days", "-d", type=int, default=7, help="Days to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    # Fetch data
    sleep_data = fetch_sleep_from_fit(args.days)
    steps_data = fetch_steps_from_fit(args.days)
    
    if args.action == "summary":
        result = format_summary(sleep_data, steps_data)
        
    elif args.action == "sleep":
        result = format_sleep_report(sleep_data)
        
    elif args.action == "steps":
        result = format_steps_report(steps_data)
        
    elif args.action == "analyze":
        print("🤖 Analyzing health data with Gemini...")
        health_summary = {
            "sleep": [{"date": s.date, "hours": s.total_hours, "quality": s.quality_score} for s in sleep_data],
            "steps": [{"date": s.date, "steps": s.steps, "goal_percent": s.goal_percent} for s in steps_data]
        }
        analysis = analyze_with_gemini(health_summary)
        result = analysis or "⚠️ Could not generate analysis. Check GEMINI_API_KEY."
    
    else:
        result = "Unknown action"
    
    if args.json:
        data = {
            "sleep": [vars(s) for s in sleep_data],
            "steps": [vars(s) for s in steps_data]
        }
        print(json.dumps(data, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
