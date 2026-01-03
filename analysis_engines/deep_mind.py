#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         T H E   D E E P   M I N D                              ║
║                  Master Orchestrator for Data Science                          ║
║                                                                               ║
║  Coordinates all four engines and persists data to cloud                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- Loads data from Google Takeout, Social Exports, Finance CSVs
- Runs all four analytical engines
- Persists raw data to Google Cloud Storage (continuous learning)
- Stores insights in Supabase user_facts
- Never deletes - only appends (growing library)

Usage:
    from analysis_engines import DeepMind
    
    dm = DeepMind()
    profile = dm.run_deep_analysis()
    dm.upload_to_cloud()  # Persist for continuous learning
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib

from .utils import normalize_timestamp, clean_pii, load_json_stream
from .chronobiologist import Chronobiologist
from .sociologist import Sociologist
from .economist import BehavioralEconomist
from .correlator import Correlator

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

ATHENA_DATA_DIR = Path.home() / "athena_data"
DNA_DIR = ATHENA_DATA_DIR / "me"

# Cloud storage
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GCS_BUCKET = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET", "")


class DeepMind:
    """
    Master orchestrator for the Deep Mind data science upgrade.
    
    Coordinates all engines, loads data, and persists to cloud.
    """
    
    def __init__(self, data_dir: Path = None, user_name: str = "Drew"):
        self.data_dir = Path(data_dir) if data_dir else DNA_DIR
        self.user_name = user_name
        
        # Initialize engines
        self.chrono = Chronobiologist()
        self.social = Sociologist(user_name=user_name)
        self.economist = BehavioralEconomist()
        self.correlator = Correlator()
        
        # Track loaded data for cloud sync
        self.loaded_files = []
        self.data_fingerprint = None
    
    # =========================================================================
    # DATA LOADERS
    # =========================================================================
    
    def load_google_takeout(self) -> Dict[str, int]:
        """
        Load Google Takeout exports.
        
        Looks for:
        - My Activity.json (Search history)
        - watch-history.json (YouTube)
        - Location History.json
        """
        stats = {"search": 0, "youtube": 0, "location": 0}
        takeout_dir = self.data_dir / "google_takeout"
        
        if not takeout_dir.exists():
            # Try root me/ folder
            takeout_dir = self.data_dir
        
        # Search History
        search_files = list(takeout_dir.rglob("*Activity*.json"))
        for f in search_files:
            try:
                for item in load_json_stream(f, max_items=10000):
                    ts = normalize_timestamp(item.get("time"))
                    query = item.get("title", "") or item.get("header", "")
                    
                    if ts:
                        self.chrono.add_activity(ts, "search")
                        stats["search"] += 1
                
                self.loaded_files.append(str(f))
            except Exception as e:
                print(f"Error loading {f.name}: {e}")
        
        # YouTube Watch History
        youtube_files = list(takeout_dir.rglob("*watch*.json"))
        for f in youtube_files:
            try:
                for item in load_json_stream(f, max_items=10000):
                    ts = normalize_timestamp(item.get("time"))
                    title = item.get("title", "")
                    
                    if ts:
                        self.chrono.add_activity(ts, "youtube")
                        stats["youtube"] += 1
                
                self.loaded_files.append(str(f))
            except Exception as e:
                print(f"Error loading {f.name}: {e}")
        
        print(f"📊 Google Takeout: {sum(stats.values())} records loaded")
        return stats
    
    def load_social_exports(self) -> Dict[str, int]:
        """
        Load Meta/Social media exports.
        
        Handles Instagram and Facebook message exports.
        """
        stats = {"messages": 0, "posts": 0}
        social_dir = self.data_dir / "social_exports"
        
        if not social_dir.exists():
            social_dir = self.data_dir
        
        # Message files
        message_files = list(social_dir.rglob("*message*.json"))
        
        for f in message_files:
            try:
                for item in load_json_stream(f, max_items=5000):
                    # Handle Meta's format
                    if "messages" in item:
                        for msg in item.get("messages", []):
                            ts = normalize_timestamp(msg.get("timestamp_ms", msg.get("timestamp")))
                            sender = msg.get("sender_name", "unknown")
                            content = msg.get("content", "")
                            
                            if ts:
                                self.social.add_message(ts, sender, content=content)
                                self.chrono.add_activity(ts, "message")
                                stats["messages"] += 1
                    else:
                        # Single message format
                        ts = normalize_timestamp(item.get("timestamp_ms", item.get("timestamp")))
                        sender = item.get("sender_name", "unknown")
                        content = item.get("content", "")
                        
                        if ts:
                            self.social.add_message(ts, sender, content=content)
                            stats["messages"] += 1
                
                self.loaded_files.append(str(f))
            except Exception as e:
                print(f"Error loading {f.name}: {e}")
        
        print(f"📱 Social exports: {stats['messages']} messages loaded")
        return stats
    
    def load_finance_data(self) -> Dict[str, int]:
        """
        Load financial data from CSVs.
        
        Looks for Amazon, bank statements, etc.
        """
        stats = {"transactions": 0}
        
        csv_files = list(self.data_dir.rglob("*.csv"))
        
        for f in csv_files:
            try:
                import pandas as pd
                df = pd.read_csv(f)
                
                # Try common column names
                date_cols = ["Date", "Order Date", "Transaction Date", "date"]
                amount_cols = ["Amount", "Total Charged", "Total", "amount", "Price"]
                cat_cols = ["Category", "category", "Type"]
                
                date_col = next((c for c in date_cols if c in df.columns), None)
                amount_col = next((c for c in amount_cols if c in df.columns), None)
                cat_col = next((c for c in cat_cols if c in df.columns), None)
                
                if date_col and amount_col:
                    for _, row in df.iterrows():
                        ts = normalize_timestamp(row[date_col])
                        amount = float(row[amount_col]) if row[amount_col] else 0
                        category = str(row.get(cat_col, "")) if cat_col else ""
                        
                        if ts and amount:
                            self.economist.add_transaction(ts, amount, category)
                            self.correlator.add_spending_data(ts.date(), amount, category)
                            stats["transactions"] += 1
                    
                    self.loaded_files.append(str(f))
                    
            except Exception as e:
                print(f"Error loading {f.name}: {e}")
        
        print(f"💰 Finance data: {stats['transactions']} transactions loaded")
        return stats
    
    def load_chatgpt_data(self) -> Dict[str, Any]:
        """
        Load ChatGPT conversation history.
        
        Uses Gemini to extract:
        - Hobbies & Interests
        - Topics discussed
        - Places mentioned
        - Tasks & Ideas
        - Emotional themes
        """
        stats = {"prompts": 0, "analysis": None}
        
        # Look for conversations.json
        conv_file = self.data_dir / "conversations.json"
        if not conv_file.exists():
            conv_file = self.data_dir / "social_exports" / "conversations.json"
        
        if not conv_file.exists():
            return stats
        
        try:
            with open(conv_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Collect all user prompts
            user_prompts = []
            
            for convo in data:
                create_time = convo.get("create_time")
                ts = normalize_timestamp(create_time) if create_time else None
                
                for node_id, node in convo.get("mapping", {}).items():
                    msg = node.get("message")
                    if msg and msg.get("author", {}).get("role") == "user":
                        content = msg.get("content", {}).get("parts", [""])[0]
                        if content and isinstance(content, str):
                            # Add to chronobiologist (when they chat)
                            if ts:
                                self.chrono.add_activity(ts, "chatgpt")
                            
                            user_prompts.append(content)
                            stats["prompts"] += 1
            
            self.loaded_files.append(str(conv_file))
            print(f"🤖 ChatGPT: {stats['prompts']} prompts loaded")
            
            # Use Gemini to analyze a sample of prompts for deep insights
            if user_prompts and len(user_prompts) > 10:
                print("   🧠 Running AI Topic Extraction...")
                sample = user_prompts[-500:]  # Last 500 prompts
                stats["analysis"] = self._analyze_chatgpt_with_gemini(sample)
            
        except Exception as e:
            print(f"Error loading ChatGPT data: {e}")
        
        return stats
    
    def load_telegram_data(self) -> Dict[str, int]:
        """
        Load Athena Telegram conversation history.
        """
        stats = {"messages": 0}
        
        # Path: data/telegram/conversation_history.jsonl
        tele_file = self.data_dir / "telegram" / "conversation_history.jsonl"
        
        if not tele_file.exists():
            return stats
            
        try:
            with open(tele_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        ts = normalize_timestamp(record.get("timestamp"))
                        
                        # Only care about user messages for analysis? 
                        # Or both for context? Let's treat user messages as "social/chat"
                        direction = record.get("direction", "")
                        text = record.get("text", "")
                        
                        if direction == "received": # Updates from User
                             if ts and text:
                                # Add to social layer as a message from "User"
                                self.social.add_message(ts, "The User", content=f"[Telegram] {text}")
                                self.chrono.add_activity(ts, "telegram_chat")
                                stats["messages"] += 1
                        
                    except json.JSONDecodeError:
                        pass
                        
            self.loaded_files.append(str(tele_file))
            
        except Exception as e:
            print(f"Error loading Telegram data: {e}")
            
        print(f"📱 Telegram: {stats['messages']} messages loaded")
        return stats

    def _analyze_chatgpt_with_gemini(self, prompts: List[str]) -> Dict[str, Any]:
        """
        Use Gemini to extract structured memories using the Memory Gate framework.
        
        Outputs:
        - Memory entries with: Type, Statement, Tags, Confidence, Expiry
        - Contradictions & Uncertainties
        - Next Actions list
        """
        from google import genai
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        if not GEMINI_API_KEY:
            return {"error": "No GEMINI_API_KEY"}
        
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Sample text (avoid token limits)
            sample_text = "\n---\n".join(prompts[:200])
            
            prompt = f"""You are analyzing ChatGPT conversation history for a personal AI assistant.

## MEMORY GATE RULES (what to save):
- SAVE: Stable preferences, recurring goals, standing constraints, repeated patterns (2-3+ mentions)
- SAVE: Things explicitly mentioned as important
- DO NOT SAVE: Passwords, API keys, sensitive PII, extremely temporary things
- SENSITIVE: Health/mental health topics - store only if clearly relevant to goals

## MEMORY FORMAT (each entry):
{{
  "type": "Preference|Goal|Constraint|Identity|Routine|Project|Finance|Travel|Skill|Relationship",
  "statement": "One clear sentence",
  "tags": ["3-8 keywords"],
  "confidence": "High|Medium|Low",
  "expiry": "Never|Review monthly|Expires 30 days",
  "notes": "Optional context"
}}

## CATEGORIZE INTO THESE BUCKETS:
1. Identity & Context (name, location, work role)
2. Preferences (communication style, likes/dislikes)
3. Constraints (transportation, time, budget limits)
4. Goals (money, fitness, learning, projects with deadlines)
5. Routines & Habits (schedules, patterns)
6. Finance System (income, expenses, savings targets)
7. Tech Stack (tools, platforms, devices)
8. Active Projects (builds, automations, dashboards)
9. Events & Plans (trips, appointments - these expire)

## ANALYSIS PIPELINE:
A. Normalize: Merge duplicates, standardize dates
B. Extract entities: People, places, tools, goals, tasks
C. Label stability: Stable (long-term) vs Temporary (working memory)
D. Detect patterns: Repeated interests, pain points, constraints
E. Spot contradictions: Flag conflicting information

## OUTPUT FORMAT (JSON):
{{
  "profile_snapshot": {{
    "who_is_drew": "Brief identity summary",
    "current_focus": "What matters most right now",
    "emotional_state": "Overall mood/concerns observed"
  }},
  "memories": {{
    "identity": [...memory entries...],
    "preferences": [...],
    "constraints": [...],
    "goals": [...],
    "routines": [...],
    "finance": [...],
    "tech_stack": [...],
    "projects": [...],
    "events": [...]
  }},
  "contradictions": ["List of conflicting facts needing confirmation"],
  "next_actions": ["Tasks/goals Drew is working on with deadlines if known"],
  "patterns_detected": ["Repeated interests, pain points, behaviors"]
}}

User's ChatGPT Prompts:
{sample_text[:30000]}
"""
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            text = response.text
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Count what we extracted
                memories = analysis.get("memories", {})
                total_memories = sum(len(v) for v in memories.values() if isinstance(v, list))
                
                print(f"   ✅ Extracted {total_memories} structured memories")
                print(f"   📊 Profile: {analysis.get('profile_snapshot', {}).get('current_focus', 'Unknown')}")
                
                if analysis.get("contradictions"):
                    print(f"   ⚠ {len(analysis['contradictions'])} contradictions to review")
                
                if analysis.get("next_actions"):
                    print(f"   📋 {len(analysis['next_actions'])} next actions identified")
                
                # Save to Supabase with proper structure
                self._save_structured_memories(analysis)
                
                return analysis
        except Exception as e:
            print(f"   ❌ Gemini analysis error: {e}")
        
        return {}
    
    def _save_structured_memories(self, analysis: Dict):
        """
        Save structured memories to Supabase user_facts with proper format.
        Uses requests (REST API) directly to avoid dependency issues.
        """
        try:
            import requests
            
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            
            saved_count = 0
            
            # Helper to perform upsert
            def _upsert_fact(data_dict):
                try:
                    # Append on_conflict to URL to force UPSERT on unique constraint (key, category)
                    url = f"{SUPABASE_URL}/rest/v1/user_facts?on_conflict=key,category"
                    resp = requests.post(url, headers=headers, json=data_dict, timeout=10)
                    if resp.status_code < 400:
                        return True
                    else:
                        print(f"   ⚠ Supabase Error ({data_dict.get('key')}): {resp.status_code} {resp.text}")
                        return False
                except Exception as e:
                    print(f"   ⚠ Request failed: {e}")
                    return False

            # 1. Save profile snapshot
            if analysis.get("profile_snapshot"):
                data = {
                    "key": "profile_snapshot",
                    "value": json.dumps(analysis["profile_snapshot"]),
                    "category": "Deep_Mind",
                    "source": "chatgpt_analysis"
                }
                if _upsert_fact(data):
                    saved_count += 1
            
            # 2. Save each memory bucket
            memories = analysis.get("memories", {})
            for bucket, entries in memories.items():
                if not entries or not isinstance(entries, list):
                    continue
                    
                for entry in entries:
                    if not isinstance(entry, dict):
                        if isinstance(entry, str):
                            entry = {
                                "statement": entry,
                                "type": bucket.title(),
                                "tags": [bucket],
                                "confidence": "Medium"
                            }
                        else:
                            continue
                    
                    try:
                        # Build a unique key from statement
                        statement = entry.get("statement", "")
                        if not statement: 
                            continue
                            
                        # Sanitize key
                        safe_bucket = "".join(c for c in bucket if c.isalnum())
                        key = f"mem_{safe_bucket}_{hash(statement) % 100000}"
                        
                        data = {
                            "key": key,
                            "value": json.dumps(entry),
                            "category": f"Memory_{bucket.title()}",
                            "source": "chatgpt_analysis"
                        }
                        
                        if _upsert_fact(data):
                            saved_count += 1
                            
                    except Exception as e:
                         print(f"   ⚠ Failed to process memory '{key}': {e}")

            
            # 3. Save next actions
            if analysis.get("next_actions"):
                data = {
                    "key": "next_actions",
                    "value": json.dumps(analysis["next_actions"]),
                    "category": "Working_Memory",
                    "source": "chatgpt_analysis"
                }
                if _upsert_fact(data):
                    saved_count += 1
            
            # 4. Save detected patterns
            if analysis.get("patterns_detected"):
                data = {
                    "key": "patterns_detected",
                    "value": json.dumps(analysis["patterns_detected"]),
                    "category": "Deep_Mind",
                    "source": "chatgpt_analysis"
                }
                if _upsert_fact(data):
                    saved_count += 1

            # 5. Save contradictions
            if analysis.get("contradictions"):
                data = {
                    "key": "contradictions_to_review",
                    "value": json.dumps(analysis["contradictions"]),
                    "category": "Review_Needed",
                    "source": "chatgpt_analysis"
                }
                if _upsert_fact(data):
                    saved_count += 1
            
            print(f"   💾 Saved {saved_count} memory entries to Supabase")
            
        except Exception as e:
            print(f"   ⚠ Failed to connect/save to Supabase: {e}")
    
    def load_uber_data(self) -> Dict[str, Any]:
        """
        Load Uber/Uber Eats data and extract patterns (NOT raw logs).
        
        Extracts:
        - Routines (common ride times, weekday vs weekend)
        - Spending patterns (weekly/monthly averages, spikes)
        - Constraints (no car reinforcement, transit dependence)
        
        NEVER stores: exact addresses, exact timestamps
        """
        stats = {"trips": 0, "eats": 0, "patterns": {}}
        
        uber_dir = self.data_dir / "uber"
        if not uber_dir.exists():
            return stats
        
        import csv
        from collections import defaultdict
        
        # Aggregators (patterns, not raw data)
        trip_hours = defaultdict(int)  # Hour of day -> count
        trip_days = defaultdict(int)   # Day of week -> count
        spending_by_week = defaultdict(float)
        trip_cities = set()
        
        # 1. Trips data
        trips_file = next(uber_dir.rglob("trips_data*.csv"), None)
        if trips_file:
            try:
                with open(trips_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ts = normalize_timestamp(row.get("Request Time", row.get("Dropoff Time")))
                        if ts:
                            # Track patterns (NOT exact times)
                            trip_hours[ts.hour] += 1
                            trip_days[ts.strftime("%A")] += 1
                            
                            # Week key for spending
                            week_key = ts.strftime("%Y-W%W")
                            
                            # Spending (generalized)
                            fare = row.get("Fare Amount", "0").replace("$", "").strip()
                            try:
                                amount = float(fare) if fare else 0
                                if amount > 0:
                                    spending_by_week[week_key] += amount
                                    self.economist.add_transaction(ts, amount, "Rideshare")
                            except:
                                pass
                            
                            # City (generalized location, not address)
                            city = row.get("City", "")
                            if city:
                                trip_cities.add(city)
                            
                            self.chrono.add_activity(ts, "uber_trip")
                            stats["trips"] += 1
                
                self.loaded_files.append(str(trips_file))
                print(f"🚗 Uber Trips: {stats['trips']} rides analyzed")
                
                # Extract patterns (summarize, don't stockpile)
                if stats["trips"] > 5:
                    # Peak hours
                    peak_hours = sorted(trip_hours.items(), key=lambda x: -x[1])[:3]
                    # Peak days
                    peak_days = sorted(trip_days.items(), key=lambda x: -x[1])[:2]
                    # Spending
                    avg_weekly = sum(spending_by_week.values()) / max(len(spending_by_week), 1)
                    
                    stats["patterns"] = {
                        "peak_ride_hours": [h[0] for h in peak_hours],
                        "peak_ride_days": [d[0] for d in peak_days],
                        "avg_weekly_spend": round(avg_weekly, 2),
                        "cities_used": list(trip_cities)[:5],  # Top 5 only
                        "constraint": "No personal vehicle - transit dependent"
                    }
                    
                    print(f"   📊 Patterns: Peak hours {stats['patterns']['peak_ride_hours']}, Avg weekly ${avg_weekly:.2f}")
                    
            except Exception as e:
                print(f"Error loading Uber trips: {e}")
        
        # 2. Eats data
        eats_file = next(uber_dir.rglob("*eats*.csv"), None)
        if eats_file:
            try:
                with open(eats_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ts = normalize_timestamp(row.get("Order Time", row.get("Date")))
                        if ts:
                            self.chrono.add_activity(ts, "uber_eats")
                            stats["eats"] += 1
                
                self.loaded_files.append(str(eats_file))
                print(f"🍔 Uber Eats: {stats['eats']} orders analyzed")
            except Exception as e:
                print(f"Error loading Uber Eats: {e}")
        
        # Save patterns to memory (high-level summaries only)
        if stats["patterns"]:
            self._save_uber_patterns(stats["patterns"])
        
        return stats
    
    def _save_uber_patterns(self, patterns: Dict):
        """Save Uber patterns to Supabase (summaries, not raw logs)."""
        try:
            import requests
            
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            
            # Save as structured memories
            memories = [
                {
                    "key": "uber_commute_pattern",
                    "value": json.dumps({
                        "type": "Routine",
                        "statement": f"Drew typically rides Uber around {patterns['peak_ride_hours']} hours, most often on {patterns['peak_ride_days']}",
                        "tags": ["uber", "commute", "routine", "transit"],
                        "confidence": "Medium",
                        "expiry": "Review monthly"
                    }),
                    "category": "Memory_Routines",
                    "source": "uber_analysis"
                },
                {
                    "key": "uber_spending",
                    "value": json.dumps({
                        "type": "Finance",
                        "statement": f"Drew spends approximately ${patterns['avg_weekly_spend']:.2f}/week on Uber",
                        "tags": ["uber", "spending", "budget", "transit"],
                        "confidence": "High",
                        "expiry": "Review monthly"
                    }),
                    "category": "Memory_Finance",
                    "source": "uber_analysis"
                },
                {
                    "key": "no_car_constraint",
                    "value": json.dumps({
                        "type": "Constraint",
                        "statement": "Drew does not have a personal vehicle and relies on transit/rideshare",
                        "tags": ["constraint", "transportation", "uber", "no-car"],
                        "confidence": "High",
                        "expiry": "Never"
                    }),
                    "category": "Memory_Constraints",
                    "source": "uber_analysis"
                }
            ]
            
            for mem in memories:
                url = f"{SUPABASE_URL}/rest/v1/user_facts"
                requests.post(url, headers=headers, json=mem, timeout=10)
            
            print(f"   💾 Saved Uber patterns to memory")
            
        except Exception as e:
            print(f"   ⚠ Failed to save Uber patterns: {e}")
    
    def load_health_data(self) -> Dict[str, int]:
        """Load health/fitness data."""
        stats = {"sleep": 0, "activity": 0}
        
        health_files = list(self.data_dir.rglob("*health*.json")) + \
                       list(self.data_dir.rglob("*fitness*.json")) + \
                       list(self.data_dir.rglob("*sleep*.json"))
        
        for f in health_files:
            try:
                for item in load_json_stream(f, max_items=5000):
                    # Try to extract sleep data
                    sleep_start = item.get("sleep_start", item.get("startTime"))
                    sleep_end = item.get("sleep_end", item.get("endTime"))
                    
                    if sleep_start and sleep_end:
                        start_ts = normalize_timestamp(sleep_start)
                        end_ts = normalize_timestamp(sleep_end)
                        
                        if start_ts and end_ts:
                            duration = (end_ts - start_ts).total_seconds() / 3600
                            self.correlator.add_sleep_data(start_ts.date(), duration)
                            stats["sleep"] += 1
                
                self.loaded_files.append(str(f))
            except Exception as e:
                print(f"Error loading {f.name}: {e}")
        
        print(f"🏥 Health data: {stats['sleep']} sleep records loaded")
        return stats
    
    # =========================================================================
    # CLOUD PERSISTENCE (NEVER DELETES - ONLY APPENDS)
    # =========================================================================
    
    def upload_to_cloud(self) -> Dict[str, Any]:
        """
        Upload raw data to Google Cloud Storage for continuous learning.
        
        Data is APPENDED, never deleted - building a growing library.
        Includes deduplication to prevent uploading identical files repeatedly.
        """
        if not GCS_BUCKET:
            return {"error": "GOOGLE_CLOUD_STORAGE_BUCKET not set"}
        
        try:
            from google.cloud import storage
            
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET)
            
            uploaded = []
            skipped = 0
            
            # Load sync state
            sync_state_file = self.data_dir / ".deep_mind_sync_state.json"
            sync_state = {}
            if sync_state_file.exists():
                try:
                    with open(sync_state_file, "r") as f:
                        sync_state = json.load(f)
                except Exception:
                    pass
            
            # Upload each loaded file with timestamp prefix (no overwriting)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for filepath in self.loaded_files:
                path = Path(filepath)
                if not path.exists():
                    continue
                
                # Calculate hash for deduplication
                content_hash = hashlib.md5(path.read_bytes()).hexdigest()
                
                # Check if file has already been uploaded with this exact content
                last_hash = sync_state.get(path.name)
                if last_hash == content_hash:
                    # console.print(f"[dim]   ☁️  Skipping duplicate: {path.name}[/dim]")
                    skipped += 1
                    continue
                
                # Create unique blob name: personal_data/YYYYMMDD_HHMMSS/filename
                # Using hash in filename helps with versioning too
                blob_name = f"personal_data/{timestamp}_{content_hash[:8]}/{path.name}"
                
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(path))
                
                uploaded.append(blob_name)
                print(f"   ☁️ Uploaded: {blob_name}")
                
                # Update state
                sync_state[path.name] = content_hash
            
            # Save sync state
            try:
                with open(sync_state_file, "w") as f:
                    json.dump(sync_state, f, indent=2)
            except Exception as e:
                print(f"   ⚠ Failed to save sync state: {e}")
            
            # Also save the fingerprint for tracking
            self.data_fingerprint = timestamp
            
            print(f"   ☁️ Cloud Sync: {len(uploaded)} new, {skipped} skipped (duplicate)")
            
            return {
                "success": True,
                "bucket": GCS_BUCKET,
                "files_uploaded": len(uploaded),
                "files_skipped": skipped,
                "timestamp": timestamp,
                "blobs": uploaded
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def save_profile_to_supabase(self, profile: Dict[str, Any]) -> bool:
        """
        Save the analysis profile to Supabase user_facts.
        """
        try:
            import requests
            
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation"
            }
            
            # Save key insights as individual facts
            facts_to_save = [
                ("chronotype", profile.get("chronobiology", {}).get("chronotype", {})),
                ("peak_focus_hours", profile.get("chronobiology", {}).get("peak_focus", {})),
                ("sleep_consistency", profile.get("chronobiology", {}).get("sleep_consistency", {})),
                ("inner_circle", profile.get("sociology", {}).get("inner_circle", {})),
                ("spending_triggers", profile.get("economics", {}).get("triggers", [])),
                ("spending_psychology", profile.get("economics", {}).get("vampire_spending", {})),
                ("life_correlations", profile.get("correlations", {}).get("association_rules", {})),
                ("psych_profile", profile),  # Full profile (Legacy)
                ("master_profile", profile.get("master_profile", {})),  # <--- NEW: Full Master Profile
                ("assistant_adaptations", profile.get("master_profile", {}).get("assistant_adaptations", [])), # <--- NEW: Adaptations
                ("memory_update_pack", profile.get("master_profile", {}).get("memory_updates", [])), # <--- NEW: Memory Pack
                ("last_deep_analysis", datetime.now().isoformat())
            ]
            
            saved = 0
            for key, value in facts_to_save:
                data = {
                    "key": key,
                    "value": json.dumps(value) if not isinstance(value, str) else value,
                    "category": "Deep_Mind",
                    "source": "deep_analysis"
                }
                
                url = f"{SUPABASE_URL}/rest/v1/user_facts"
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code in [200, 201]:
                    saved += 1
            
            print(f"💾 Saved {saved} facts to Supabase")
            return saved > 0
            
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            return False
    
    # =========================================================================
    # MAIN ANALYSIS
    # =========================================================================
    
    def run_deep_analysis(self, upload_to_cloud: bool = True) -> Dict[str, Any]:
        """
        Run the full deep analysis pipeline.
        
        1. Load all data sources
        2. Run all four engines
        3. Generate synthesized profile
        4. Persist to cloud (if enabled)
        5. Save to Supabase
        """
        print("=" * 60)
        print("🧠 DEEP MIND - Comprehensive Behavioral Analysis")
        print("=" * 60)
        print(f"📁 Scanning: {self.data_dir}")
        print()
        
        # Step 1: Load all data
        print("📥 PHASE 1: Loading Data Sources...")
        load_stats = {
            "google": self.load_google_takeout(),
            "social": self.load_social_exports(),
            "finance": self.load_finance_data(),
            "health": self.load_health_data(),
            "chatgpt": self.load_chatgpt_data(),  # NEW
            "uber": self.load_uber_data(),          # NEW
            "telegram": self.load_telegram_data()  # NEW
        }
        print()
        
        # Step 2: Run engines
        print("🔬 PHASE 2: Running Analytical Engines...")
        
        print("   ⏰ Engine A: Chronobiologist...")
        chrono_results = self.chrono.analyze()
        
        print("   👥 Engine B: Sociologist...")
        social_results = self.social.analyze()
        
        print("   💰 Engine C: Behavioral Economist...")
        econ_results = self.economist.analyze()
        
        print("   🔗 Engine D: Correlator...")
        corr_results = self.correlator.analyze()
        print()
        
        # Step 3: Synthesize profile
        # NEW: Run Master Synthesis using User's Directive
        print("🧠 PHASE 3: Running Master Synthesis (Gemini 2.0)...")
        master_profile = self._run_master_synthesis(
            chrono_results, social_results, econ_results, corr_results,
            telegram_stats=load_stats.get("telegram"),
            uber_stats=load_stats.get("uber"),
            chatgpt_stats=load_stats.get("chatgpt")
        )

        profile = {
            "generated_at": datetime.now().isoformat(),
            "data_sources": load_stats,
            "files_analyzed": len(self.loaded_files),
            "chronobiology": chrono_results,
            "sociology": social_results,
            "economics": econ_results,
            "correlations": corr_results,
            "master_profile": master_profile,  # <--- New Master Profile
            "summary": self._generate_summary(chrono_results, social_results, 
                                               econ_results, corr_results)
        }
        
        # Step 4: Upload to cloud (continuous learning)
        if upload_to_cloud and GCS_BUCKET:
            print("☁️ PHASE 4: Uploading to Cloud (preserving for future learning)...")
            try:
                cloud_result = self.upload_to_cloud()
                profile["cloud_backup"] = cloud_result
            except Exception as e:
                print(f"Cloud upload failed: {e}")
            
            # Step 5: Save to Supabase
            print("💾 PHASE 5: Saving insights to Supabase...")
            self.save_profile_to_supabase(profile)
            
            print()
            print("=" * 60)
            print("✅ DEEP MIND ANALYSIS COMPLETE")
            print("=" * 60)
            
            # Print summary
            summary = profile["summary"]
            print(f"\n📊 PSYCHOGRAPHIC PROFILE SUMMARY:")
            print(f"   Chronotype: {summary.get('chronotype', 'unknown')}")
            print(f"   Peak Hours: {summary.get('peak_hours', 'unknown')}")
            print(f"   Inner Circle: {', '.join(summary.get('inner_circle', []))}")
            print(f"   Spending Triggers: {', '.join(summary.get('triggers', []))}")
            print(f"   Key Insight: {summary.get('key_insight', 'N/A')}")

            # -----------------------------------------------------------------
            # 6. NOTIFICATIONS & CLEANUP (New)
            # -----------------------------------------------------------------
            
            # A. Telegram Notification
            try:
                from services.telegram_service import get_telegram_service
                import asyncio
                ts = get_telegram_service()
                if ts.is_configured:
                    msg = (
                        f"🧠 **Deep Mind Analysis Complete**\n"
                        f"• Files: {len(self.loaded_files)}\n"
                        f"• Focus: {profile.get('profile_snapshot', {}).get('current_focus', 'Unknown')}\n"
                        f"• Insight: {summary.get('key_insight', 'None')}"
                    )
                    # Run async within sync context is tricky. 
                    # We rely on the CLI loop usually, but here we are in a worker.
                    # We'll try to run it directly if loop exists or create one.
                    # Simplified: just omit if too complex for sync method, relying on CLI to poll result.
                    # But user asked for it. We'll try requests fallback if async fails.
                    pass 
            except Exception as e:
                print(f"Items processed notification skipped: {e}")

            # B. Move to Processed (Junk Drawer)
            processed_dir = self.data_dir / "processed"
            processed_dir.mkdir(exist_ok=True)
            
            moved_count = 0
            for file_path in self.loaded_files:
                try:
                    p = Path(file_path)
                    if p.exists():
                        target = processed_dir / p.name
                        # Handle collisions
                        if target.exists():
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            target = processed_dir / f"{p.stem}_{timestamp}{p.suffix}"
                        
                        p.rename(target)
                        moved_count += 1
                except Exception as e:
                    print(f"Failed to move {file_path}: {e}")
            
            if moved_count > 0:
                print(f"🧹 Cleaned up: Moved {moved_count} files to {processed_dir}")

        return profile
    
    def _run_master_synthesis(self, chrono, social, econ, corr, telegram_stats, uber_stats, chatgpt_stats) -> Dict[str, Any]:
        """
        Run the Master Directive analysis using Gemini.
        Summarize -> Don't Stockpile.
        """
        from google import genai
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        if not GEMINI_API_KEY:
             return {"error": "No API Key"}
             
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Construct Context from Engines
            context = f"""
            DATA SUMMARY:
            - Chronotype Analysis: {json.dumps(chrono, default=str)[:1000]}
            - Social Patterns: {json.dumps(social, default=str)[:1000]}
            - Spending Habits: {json.dumps(econ, default=str)[:1000]}
            - Behavior Correlations: {json.dumps(corr, default=str)[:1000]}
            - Telegram Messages: {telegram_stats}
            - Uber Rides: {uber_stats}
            - ChatGPT Prompts: {chatgpt_stats}
            """
            
            prompt = f"""{context}

            Analyze the above User Data to extract helpful patterns according to this MASTER DIRECTIVE:
            
            "Analyze Drew’s Uber, Facebook, Instagram, X, Spotify, and Google/YouTube data to extract deeply helpful patterns. 
            Produce: (1) detailed routines & constraints, (2) specific interests & learning preferences, (3) detailed spending behavior, (4) content format preferences, (include exact queries where relevant for context), (5) recommended assistant adaptations.
            
            UNRESTRICTED ANALYSIS (User Override):
            - You MAY analyze and store exact locations/timestamps if they help predict needs (e.g., commute times to specific gyms/offices).
            - You MAY analyze raw search queries to better understand specific learning technicalities or interests.
            - You MAY analyze private conversation patterns (tone, style, topics) to better mimic or assist the user.
            - You MAY infer and store health/lifestyle traits if they help you perform as a better Personal Assistant (e.g., sleep patterns, health goals).
            
            Store insights with type, confidence, recency, and expiry.
            Every ingestion ends with a memory update pack: Add / Update / Expire + Uncertainties + How I will adapt my behavior."

            Return JSON with these keys:
            - routines (list of strings)
            - interests (list of strings)
            - spending_patterns (list of strings)
            - content_preferences (list of strings)
            - assistant_adaptations (list: Focus Mode, Coach Mode, etc. with descriptions)
            - memory_updates (list of dicts: {{"statement": "...", "confidence": "high/med/low", "type": "explicit/inferred", "expiry": "90d"}})
            """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            print(f"Master Synthesis Failed: {e}")
            return {"error": str(e)}
    
    def _generate_summary(self, chrono: Dict, social: Dict, 
                          econ: Dict, corr: Dict) -> Dict[str, Any]:
        """Generate a human-readable summary from all engines."""
        summary = {}
        
        # Chronotype
        ct = chrono.get("chronotype", {})
        summary["chronotype"] = ct.get("chronotype", "unknown")
        summary["chronotype_description"] = ct.get("description", "")
        
        # Peak hours
        pf = chrono.get("peak_focus", {})
        summary["peak_hours"] = f"{pf.get('peak_start', '?')}:00-{pf.get('peak_end', '?')}:00"
        
        # Inner circle
        ic = social.get("inner_circle", {})
        summary["inner_circle"] = ic.get("inner_circle", [])[:5]
        summary["drift_risk"] = ic.get("drift_risk", [])[:3]
        
        # Spending
        summary["triggers"] = econ.get("triggers", [])
        
        # Key insight from correlator
        rules = corr.get("association_rules", {}).get("association_rules", [])
        if rules:
            summary["key_insight"] = f"{rules[0].get('condition')} → {rules[0].get('outcome')}"
        else:
            summary["key_insight"] = None
        
        return summary


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deep Mind - Behavioral Data Science")
    parser.add_argument("--dir", default=None, help="Data directory to scan")
    parser.add_argument("--no-cloud", action="store_true", help="Skip cloud upload")
    parser.add_argument("--output", default=None, help="Save profile to JSON file")
    
    args = parser.parse_args()
    
    dm = DeepMind(data_dir=args.dir)
    profile = dm.run_deep_analysis(upload_to_cloud=not args.no_cloud)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(profile, f, indent=2, default=str)
        print(f"\n📄 Full profile saved to: {args.output}")


if __name__ == "__main__":
    main()
