#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     C L O U D   A N A L Y S T                                 ║
║                    "The Dream Loop"                                            ║
║                                                                               ║
║  Athena learns while you sleep - runs on Google Cloud Functions              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Deployment: Google Cloud Functions
Trigger: Cloud Scheduler (weekly or daily)
Cost: $0 (Free Tier)

What it does:
1. Fetches last 7 days of memory_logs from Supabase
2. Analyzes patterns with Gemini 1.5 Pro
3. Updates user_facts with insights
4. Athena on your PC reads these next time she starts

Requirements (requirements.txt for Cloud Functions):
    functions-framework
    google-genai
    requests

Environment Variables (set in Cloud Functions console):
    SUPABASE_URL
    SUPABASE_KEY
    GEMINI_API_KEY
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# For Cloud Functions
try:
    import functions_framework
except ImportError:
    functions_framework = None


# =============================================================================
# CONFIGURATION (from environment variables)
# =============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

def supabase_request(method: str, table: str, data: Dict = None, params: Dict = None) -> Any:
    """Make a request to Supabase REST API."""
    import requests
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    
    if params:
        query_parts = [f"{k}={v}" for k, v in params.items()]
        url += "?" + "&".join(query_parts)
    
    if method == "GET":
        response = requests.get(url, headers=headers, timeout=30)
    elif method == "POST":
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        response = requests.post(url, headers=headers, json=data, timeout=30)
    elif method == "PATCH":
        response = requests.patch(url, headers=headers, json=data, timeout=30)
    else:
        return None
    
    if response.status_code in [200, 201, 204]:
        return response.json() if response.text else {"success": True}
    else:
        print(f"Supabase error: {response.status_code} - {response.text}")
        return None


# =============================================================================
# DATA FETCHING
# =============================================================================

def fetch_recent_logs(days: int = 7, limit: int = 100) -> List[Dict]:
    """Fetch recent memory_logs from Supabase."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    params = {
        "select": "user_input,athena_response,summary,source,created_at",
        "created_at": f"gte.{cutoff}",
        "order": "created_at.desc",
        "limit": str(limit)
    }
    
    return supabase_request("GET", "memory_logs", params=params) or []


def fetch_agent_registry(days: int = 7) -> List[Dict]:
    """Fetch recent agent executions."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    params = {
        "select": "agent_name,task_description,status,error_message,created_at",
        "created_at": f"gte.{cutoff}",
        "order": "created_at.desc"
    }
    
    return supabase_request("GET", "agent_registry", params=params) or []


def fetch_current_user_facts() -> Dict[str, Any]:
    """Get current user_facts."""
    result = supabase_request("GET", "user_facts", params={"select": "key,value,category"})
    
    if not result:
        return {}
    
    return {row["key"]: row["value"] for row in result}


# =============================================================================
# PATTERN ANALYSIS (Gemini)
# =============================================================================

def analyze_patterns(logs: List[Dict], agent_data: List[Dict], current_facts: Dict) -> Dict[str, Any]:
    """
    Use Gemini to analyze user behavior patterns.
    
    Returns insights to be stored in user_facts.
    """
    from google import genai
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Build context
    log_summary = []
    for log in logs[:50]:  # Last 50 conversations
        user_input = log.get("user_input", "")[:100]
        summary = log.get("summary", "")[:50]
        log_summary.append(f"- {user_input} ({summary})")
    
    agent_summary = []
    for agent in agent_data[:20]:
        name = agent.get("agent_name", "")
        status = agent.get("status", "")
        task = agent.get("task_description", "")[:50]
        agent_summary.append(f"- {name}: {status} - {task}")
    
    prompt = f"""You are analyzing a user's AI assistant logs from the past week.

## Recent Conversations:
{chr(10).join(log_summary)}

## Agent Executions:
{chr(10).join(agent_summary)}

## Current Known Facts:
{json.dumps(current_facts, indent=2)[:1000]}

## Analyze and return JSON with these insights:

{{
    "weekly_focus": "What is the user currently obsessed/focused on?",
    "current_mood": "positive|stressed|focused|tired|excited",
    "top_interests": ["list", "of", "3 interests"],
    "agent_performance": {{
        "most_used": "agent_name",
        "failures": ["list of failed agents if any"]
    }},
    "recommendations": [
        "Actionable recommendation 1",
        "Actionable recommendation 2"
    ],
    "priority_adjustments": {{
        "high_priority": ["agents to prioritize"],
        "low_priority": ["agents that can wait"]
    }},
    "detected_patterns": "Brief description of any behavioral patterns",
    "health_alert": "Any concerning patterns? Or 'none'"
}}

Return ONLY valid JSON, no markdown."""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-pro",  # Use Pro for large context
            contents=prompt
        )
        
        import re
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
        
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return {"error": str(e)}


# =============================================================================
# UPDATE USER_FACTS
# =============================================================================

def update_user_facts(insights: Dict[str, Any]) -> bool:
    """
    Write insights back to Supabase user_facts.
    """
    timestamp = datetime.now().isoformat()
    
    updates = [
        {
            "key": "weekly_insight",
            "value": json.dumps({
                "focus": insights.get("weekly_focus", "unknown"),
                "mood": insights.get("current_mood", "neutral"),
                "analyzed_at": timestamp
            }),
            "category": "analysis",
            "source": "cloud_analyst"
        },
        {
            "key": "current_interests",
            "value": json.dumps(insights.get("top_interests", [])),
            "category": "preference",
            "source": "inference"
        },
        {
            "key": "detected_mood",
            "value": json.dumps(insights.get("current_mood", "neutral")),
            "category": "preference",
            "source": "inference"
        },
        {
            "key": "weekly_recommendations",
            "value": json.dumps(insights.get("recommendations", [])),
            "category": "analysis",
            "source": "cloud_analyst"
        },
        {
            "key": "agent_priorities",
            "value": json.dumps(insights.get("priority_adjustments", {})),
            "category": "analysis",
            "source": "cloud_analyst"
        }
    ]
    
    success_count = 0
    for update in updates:
        result = supabase_request("POST", "user_facts", update)
        if result:
            success_count += 1
    
    print(f"Updated {success_count}/{len(updates)} user_facts")
    return success_count > 0


def log_analysis_run(insights: Dict[str, Any]) -> None:
    """Log this analysis run to athena_monologue."""
    supabase_request("POST", "athena_monologue", {
        "thought_process": f"Weekly analysis complete. Focus: {insights.get('weekly_focus', 'unknown')}. Mood: {insights.get('current_mood', 'neutral')}.",
        "action_taken": "update_user_facts",
        "category": "learning",
        "success_score": 5 if "error" not in insights else 2
    })


# =============================================================================
# MAIN FUNCTION (Cloud Functions Entry Point)
# =============================================================================

def run_weekly_analysis() -> Dict[str, Any]:
    """
    Main analysis function.
    
    This is what runs on the schedule.
    """
    print("=" * 60)
    print("☁️ ATHENA CLOUD ANALYST - Weekly Review")
    print(f"🕐 {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Validate config
    if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY]):
        return {"error": "Missing environment variables"}
    
    # Step 1: Fetch data
    print("\n📥 Fetching recent data...")
    logs = fetch_recent_logs(days=7, limit=100)
    agents = fetch_agent_registry(days=7)
    current_facts = fetch_current_user_facts()
    
    print(f"   Found {len(logs)} logs, {len(agents)} agent runs")
    
    if len(logs) < 5:
        return {"status": "skipped", "reason": "Not enough data to analyze"}
    
    # Step 2: Analyze patterns
    print("\n🧠 Analyzing patterns with Gemini...")
    insights = analyze_patterns(logs, agents, current_facts)
    
    if "error" in insights:
        return {"status": "error", "error": insights["error"]}
    
    print(f"   Focus: {insights.get('weekly_focus', 'unknown')}")
    print(f"   Mood: {insights.get('current_mood', 'neutral')}")
    print(f"   Interests: {insights.get('top_interests', [])}")
    
    # Step 3: Update user_facts
    print("\n📤 Updating user_facts...")
    update_user_facts(insights)
    
    # Step 4: Log the run
    log_analysis_run(insights)
    
    print("\n" + "=" * 60)
    print("✅ Weekly analysis complete!")
    
    return {
        "status": "success",
        "analyzed_at": datetime.now().isoformat(),
        "logs_analyzed": len(logs),
        "focus": insights.get("weekly_focus"),
        "mood": insights.get("current_mood")
    }


# =============================================================================
# CLOUD FUNCTIONS ENTRY POINT
# =============================================================================

if functions_framework:
    @functions_framework.http
    def athena_weekly_review(request):
        """
        HTTP Cloud Function entry point.
        
        Deploy this to Google Cloud Functions.
        Trigger via Cloud Scheduler with cron: 0 8 * * 1 (Monday 8AM)
        """
        try:
            result = run_weekly_analysis()
            return json.dumps(result), 200, {"Content-Type": "application/json"}
        except Exception as e:
            return json.dumps({"error": str(e)}), 500, {"Content-Type": "application/json"}


# =============================================================================
# LOCAL TESTING
# =============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Re-read env vars after loading
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    result = run_weekly_analysis()
    print("\nResult:", json.dumps(result, indent=2))
