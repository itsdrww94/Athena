#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                  M E M O R Y   C O R E   v 3 . 0                              ║
║                       "The Hippocampus"                                        ║
║                                                                               ║
║  Athena's Long-Term Memory System aligned with Engineering Design v3.0       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Core Philosophy: "Athena is the Strategist; Agents are the Soldiers."
- Agents are DETERMINISTIC tools (inputs -> outputs)
- Athena handles EVOLUTION and ADAPTATION via memory analysis

Tables (Supabase):
1. memory_logs     - Full conversation history
2. agent_states    - Agent key-value persistence 
3. user_facts      - Evolution table (learned preferences)
4. agent_registry  - Sub-agent orchestration
5. athena_monologue - Thought analysis

Key Functions:
- log_interaction()    - Save user/Athena exchange
- get_context()        - Get last N conversations for prompt
- get_user_profile()   - Get full user facts for routing decisions
- update_user_preference() - Update learned preference
- get_preference()     - Get single preference for agent argument

Usage:
    from services.memory_core import get_memory
    
    memory = get_memory()
    
    # Before executing ANY command, get user profile
    profile = memory.get_user_profile()
    
    # If profile says current_interest = "Anime", route to:
    # python cinema_companion.py --genre "Anime"
"""

import os
import sys
import json
import logging
import uuid
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

# Fix import path for standalone execution
sys.path.insert(0, str(__file__).rsplit("services", 1)[0])

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logger = logging.getLogger("athena.memory")


# =============================================================================
# MEMORY CORE CLASS
# =============================================================================

class MemoryCore:
    """
    Athena's Memory System v3.0 - The Hippocampus
    
    Core Principle: Athena is Smart, Agents are Dumb.
    This class provides the intelligence layer that analyzes history
    and provides preferences as ARGUMENTS to deterministic agents.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - only one memory instance."""
        if cls._instance is None:
            cls._instance = super(MemoryCore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {}
        self._profile_cache = {}
        self._cache_time = None
        self._initialized = True
        
        self._connect()
    
    def _connect(self) -> bool:
        """Initialize connection headers."""
        if not self.url or not self.key:
            logger.warning("Supabase credentials not configured")
            return False
        
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        return True
    
    @property
    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.url and self.key)
    
    def _request(self, method: str, table: str, data: Dict = None, params: Dict = None) -> Optional[Any]:
        """Make a REST API request to Supabase."""
        if not self.is_configured:
            return None
        
        try:
            import requests
            
            url = f"{self.url}/rest/v1/{table}"
            
            if params:
                query_parts = [f"{k}={v}" for k, v in params.items()]
                if query_parts:
                    url += "?" + "&".join(query_parts)
            
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=10)
            else:
                return None
            
            if response.status_code in [200, 201, 204]:
                return response.json() if response.text else {"success": True}
            else:
                logger.error(f"Supabase error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Memory request failed: {e}")
            return None
    
    # =========================================================================
    # CORE FUNCTIONS (v3.0 Spec)
    # =========================================================================
    
    def log_interaction(self, user_input: str, athena_response: str, 
                        summary: str = None, source: str = "telegram") -> bool:
        """
        Save user/Athena exchange to memory_logs and Archive to Cloud.
        
        Args:
            user_input: What the user said
            athena_response: What Athena replied
            summary: Brief summary for search (auto-generated if None)
            source: telegram, cli, api
        """
        # 1. Supabase Log
        data = {
            "user_input": user_input,
            "athena_response": athena_response[:5000],
            "source": source
        }
        
        if summary:
            data["summary"] = summary
        else:
            # Auto-generate brief summary
            data["summary"] = f"{user_input[:50]}..."
        
        result = self._request("POST", "memory_logs", data)
        
        # 2. Cloud Archival (Fire & Forget)
        try:
            from services.cloud_storage import get_cloud_storage
            cloud = get_cloud_storage()
            
            timestamp = datetime.now().strftime('%Y-%m-%d/%H-%M-%S')
            filename = f"conversations/{timestamp}_{source}.json"
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user_input,
                "athena": athena_response,
                "source": source
            }
            
            cloud.upload_json(log_entry, filename)
        except Exception as e:
            logger.warning(f"Cloud archival failed: {e}")

        return result is not None
    
    def get_context(self, limit: int = 5) -> str:
        """
        Get last N conversations formatted for prompt injection.
        
        Returns:
            Formatted string with recent exchanges
        """
        params = {
            "select": "user_input,athena_response,created_at",
            "order": "created_at.desc",
            "limit": str(limit)
        }
        
        result = self._request("GET", "memory_logs", params=params)
        
        if not result:
            return ""
        
        parts = ["**Recent Conversations:**"]
        for chat in reversed(result):
            user = chat.get("user_input", "")[:100]
            bot = chat.get("athena_response", "")[:200]
            parts.append(f"User: {user}")
            parts.append(f"Athena: {bot}...")
        
        return "\n".join(parts)
    
    def get_user_profile(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get full user facts for routing decisions.
        
        THIS IS THE KEY FUNCTION FOR THE STRATEGIST PATTERN.
        Call this BEFORE executing ANY command to get preferences.
        
        Returns:
            Dict with all user facts organized by category
        """
        # Use cache if fresh (5 minutes)
        if not force_refresh and self._profile_cache and self._cache_time:
            cache_age = (datetime.now() - self._cache_time).total_seconds()
            if cache_age < 300:
                return self._profile_cache
        
        # Fetch all user_facts
        result = self._request("GET", "user_facts", params={"select": "*"})
        
        if not result:
            return {}
        
        # Organize by category
        profile = {
            "personal": {},
            "preference": {},
            "technical": {},
            "goal": {}
        }
        
        for row in result:
            key = row.get("key", "")
            value = row.get("value")
            category = row.get("category", "preference")
            
            # Parse JSON values
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except:
                    pass
            
            if category in profile:
                profile[category][key] = value
            else:
                profile["preference"][key] = value
        
        self._profile_cache = profile
        self._cache_time = datetime.now()
        
        return profile
    
    def update_user_preference(self, key: str, value: Any, 
                               category: str = "preference",
                               source: str = "inference",
                               confidence: float = 1.0) -> bool:
        """
        Update or create a user preference in user_facts.
        
        This is how the "Trend Spotter" updates learned preferences.
        
        Args:
            key: Preference key (e.g., "current_movie_preference")
            value: Any JSON-serializable value
            category: preference, personal, technical, goal
            source: inference, explicit, system
            confidence: How confident (0.0-1.0)
        """
        data = {
            "key": key,
            "value": json.dumps(value) if not isinstance(value, str) else value,
            "category": category,
            "source": source,
            "confidence": confidence
        }
        
        # Use upsert
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        
        try:
            import requests
            url = f"{self.url}/rest/v1/user_facts"
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code in [200, 201]:
                self._profile_cache = {}  # Invalidate cache
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update preference: {e}")
            return False
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a single preference value.
        
        Agents call this to get a specific preference as an ARGUMENT.
        
        Args:
            key: Preference key (e.g., "current_movie_preference")
            default: Default value if not found
        """
        profile = self.get_user_profile()
        
        # Search all categories
        for category in profile.values():
            if key in category:
                return category[key]
        
        return default
    
    # =========================================================================
    # AGENT ROUTING HELPER
    # =========================================================================
    
    def get_agent_args(self, agent_name: str) -> Dict[str, str]:
        """
        Get command-line arguments for a specific agent based on user preferences.
        
        This is the BRIDGE between Athena (Strategist) and Agents (Soldiers).
        
        Args:
            agent_name: Name of the agent to get args for
            
        Returns:
            Dict of argument name -> value (e.g., {"genre": "Anime"})
        """
        profile = self.get_user_profile()
        prefs = profile.get("preference", {})
        args = {}
        
        if agent_name == "cinema_companion":
            if "current_movie_preference" in prefs:
                args["genre"] = prefs["current_movie_preference"]
            if prefs.get("detected_mood") == "stressed":
                args["type"] = "feel_good"
                
        elif agent_name == "news_brief":
            if "interests" in prefs:
                args["filter"] = ",".join(prefs["interests"][:3])
                
        elif agent_name == "msp_scout":
            if "interests" in prefs:
                args["interest"] = prefs["interests"][0] if prefs["interests"] else "tech"
                
        elif agent_name == "finance" or agent_name == "finance_manager":
            if "current_financial_mode" in prefs:
                args["mode"] = prefs["current_financial_mode"]
                
        elif agent_name == "health_sync":
            if prefs.get("detected_mood") in ["stressed", "tired"]:
                args["advice_mode"] = "true"
        
        return args
    
    def build_agent_command(self, agent_name: str, user_args: str = "") -> str:
        """
        Build the full command string for an agent with preferences as arguments.
        
        Example:
            user asks for movie -> 
            build_agent_command("cinema_companion", "--recommend") ->
            "python agents/cinema_companion.py --recommend --genre Anime"
        
        Args:
            agent_name: Name of the agent
            user_args: Arguments from user's request
            
        Returns:
            Full command string
        """
        base_cmd = f"python agents/{agent_name}.py"
        
        if user_args:
            base_cmd += f" {user_args}"
        
        # Add inferred preferences as arguments
        pref_args = self.get_agent_args(agent_name)
        for arg_name, arg_value in pref_args.items():
            # Don't override if user already specified
            if f"--{arg_name}" not in user_args:
                base_cmd += f" --{arg_name} \"{arg_value}\""
        
        return base_cmd
    
    # =========================================================================
    # AGENT STATE (Key-Value Store)
    # =========================================================================
    
    def save_state(self, agent_name: str, key: str, value: Any) -> bool:
        """Save agent state (e.g., 'last_video_checked')."""
        data = {
            "agent_name": agent_name,
            "key": key,
            "value": {"data": value} if not isinstance(value, dict) else value
        }
        
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        
        try:
            import requests
            url = f"{self.url}/rest/v1/agent_states"
            response = requests.post(url, headers=headers, json=data, timeout=10)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False
    
    def load_state(self, agent_name: str, key: str = None) -> Optional[Any]:
        """Load agent state."""
        params = {"agent_name": f"eq.{agent_name}"}
        if key:
            params["key"] = f"eq.{key}"
        
        result = self._request("GET", "agent_states", params=params)
        
        if not result:
            return None
        
        if key:
            if result and len(result) > 0:
                value = result[0].get("value", {})
                return value.get("data", value)
            return None
        else:
            return {e.get("key"): e.get("value", {}).get("data", e.get("value")) for e in result}
    
    # =========================================================================
    # AGENT REGISTRY
    # =========================================================================
    
    def register_agent(self, agent_name: str, task: str, metadata: Dict = None) -> Optional[str]:
        """Register an agent execution."""
        agent_id = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        data = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "task_description": task,
            "status": "pending",
            "metadata": metadata or {}
        }
        
        result = self._request("POST", "agent_registry", data)
        return agent_id if result else None
    
    def update_agent_status(self, agent_id: str, status: str, 
                            output: str = None, error: str = None) -> bool:
        """Update agent status."""
        data = {"status": status}
        
        if status == "running":
            data["started_at"] = datetime.now().isoformat()
        elif status in ["completed", "failed"]:
            data["completed_at"] = datetime.now().isoformat()
        
        if output:
            data["last_output"] = output[:5000]
        if error:
            data["error_message"] = error
        
        try:
            import requests
            url = f"{self.url}/rest/v1/agent_registry?agent_id=eq.{agent_id}"
            response = requests.patch(url, headers=self.headers, json=data, timeout=10)
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            return False
    
    # =========================================================================
    # THOUGHT LOGGING
    # =========================================================================
    
    def log_thought(self, thought: str, action: str = None, 
                    category: str = "analysis", success_score: int = None) -> bool:
        """Log Athena's internal thought process."""
        data = {
            "thought_process": thought,
            "category": category
        }
        
        if action:
            data["action_taken"] = action
        if success_score and 1 <= success_score <= 5:
            data["success_score"] = success_score
        
        result = self._request("POST", "athena_monologue", data)
        return result is not None
    
    # =========================================================================
    # TREND SPOTTER (Preference Evolution)
    # =========================================================================
    
    def analyze_trends(self, chat_limit: int = 50) -> Dict[str, Any]:
        """
        Analyze recent interactions to update user preferences.
        
        Run this periodically (every 50 interactions or weekly).
        """
        params = {
            "select": "user_input,summary",
            "order": "created_at.desc",
            "limit": str(chat_limit)
        }
        result = self._request("GET", "memory_logs", params=params)
        
        if not result or len(result) < 5:
            return {"status": "not_enough_data"}
        
        # Build activity summary
        activity = "\n".join([f"- {r.get('user_input', '')[:100]}" for r in result[:30]])
        
        try:
            from google import genai
            
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = f"""Analyze these user interactions and identify preferences.

{activity}

Return JSON with:
- current_movie_preference: string (Anime, Action, Comedy, Horror, none)
- current_music_mood: string (upbeat, chill, focused, none)
- current_financial_mode: string (aggressive_saving, normal, spending)
- detected_mood: string (positive, stressed, focused, tired)
- interests: list of top 3 topics

Return ONLY valid JSON."""

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            
            text = response.text.strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def update_from_trends(self) -> Dict[str, Any]:
        """Run trend analysis and update user_facts."""
        trends = self.analyze_trends()
        
        if trends.get("status") in ["error", "not_enough_data"]:
            return trends
        
        updates = {}
        
        for key in ["current_movie_preference", "current_music_mood", 
                    "current_financial_mode", "detected_mood"]:
            if trends.get(key) and trends[key] != "none":
                self.update_user_preference(key, trends[key])
                updates[key] = trends[key]
        
        if trends.get("interests"):
            self.update_user_preference("interests", trends["interests"])
            updates["interests"] = trends["interests"]
        
        self.log_thought(
            f"Trend analysis: Updated {list(updates.keys())}",
            action="update_preferences",
            category="learning",
            success_score=5 if updates else 3
        )
        
        return {"status": "success", "updates": updates}
    
    # =========================================================================
    # CONTEXT FOR PROMPTS
    # =========================================================================
    
    def get_full_context(self, chat_limit: int = 5) -> str:
        """Get user profile + recent chats for prompt injection."""
        parts = []
        
        # Profile summary
        profile = self.get_user_profile()
        if profile:
            personal = profile.get("personal", {})
            prefs = profile.get("preference", {})
            
            parts.append("**User Profile:**")
            if personal.get("name"):
                parts.append(f"• Name: {personal['name']}")
            if personal.get("location"):
                loc = personal["location"]
                parts.append(f"• Location: {loc.get('city', '')}, {loc.get('state', '')}")
            if prefs.get("current_movie_preference"):
                parts.append(f"• Current Movie Preference: {prefs['current_movie_preference']}")
            if prefs.get("detected_mood"):
                parts.append(f"• Detected Mood: {prefs['detected_mood']}")
            parts.append("")
        
        # Recent chats
        context = self.get_context(limit=chat_limit)
        if context:
            parts.append(context)
        
        return "\n".join(parts)


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_memory_instance: Optional[MemoryCore] = None

def get_memory() -> MemoryCore:
    """Get or create the memory singleton."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryCore()
    return _memory_instance


# =============================================================================
# CLI FOR TESTING
# =============================================================================

def main():
    """Test memory core v3.0."""
    print("=" * 60)
    print("🧠 ATHENA MEMORY CORE v3.0 - Test Suite")
    print("=" * 60)
    
    memory = get_memory()
    
    if not memory.is_configured:
        print("❌ Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
        return
    
    # Test get_user_profile
    print("\n1. Testing get_user_profile()...")
    profile = memory.get_user_profile()
    if profile:
        print(f"   ✅ Found {sum(len(v) for v in profile.values())} facts")
        for cat, facts in profile.items():
            if facts:
                print(f"   📁 {cat}: {list(facts.keys())[:3]}...")
    else:
        print("   ❌ No profile found. Run supabase_schema.sql first.")
    
    # Test get_agent_args
    print("\n2. Testing get_agent_args('cinema_companion')...")
    args = memory.get_agent_args("cinema_companion")
    print(f"   Inferred args: {args}")
    
    # Test build_agent_command
    print("\n3. Testing build_agent_command()...")
    cmd = memory.build_agent_command("cinema_companion", "--recommend")
    print(f"   Command: {cmd}")
    
    # Test log_interaction
    print("\n4. Testing log_interaction()...")
    success = memory.log_interaction(
        "Testing v3.0 memory",
        "Memory v3.0 is working!"
    )
    print(f"   Log: {'✅' if success else '❌'}")
    
    # Test get_context
    print("\n5. Testing get_context()...")
    context = memory.get_context(limit=3)
    print(f"   Context length: {len(context)} chars")
    
    print("\n" + "=" * 60)
    print("✅ Memory Core v3.0 test complete!")
    print("\nNext: Run 'python athena_remote.py' to test full routing.")


if __name__ == "__main__":
    main()
