"""
Athena Router
=============
Routes user messages to the appropriate agent based on:
1. Explicit commands (/command)
2. Keyword matching
3. LLM-based intent classification (fallback)
"""

import re
from typing import Dict, Any, Optional, List

# Lazy imports
_settings = None
_logger = None

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.router")
    return _logger


# =============================================================================
# ROUTING RULES
# =============================================================================

# Command prefix patterns
COMMAND_PATTERN = re.compile(r"^/(\w+)(?:\s+(.*))?$")

# Keyword -> Agent mapping (loaded from registry)
_keyword_map: Optional[Dict[str, str]] = None

def _get_keyword_map() -> Dict[str, str]:
    """Get the keyword to agent mapping (cached)."""
    global _keyword_map
    if _keyword_map is None:
        from core.agent_registry import get_all_keywords
        _keyword_map = get_all_keywords()
    return _keyword_map


def _reset_keyword_map():
    """Reset the keyword map cache."""
    global _keyword_map
    _keyword_map = None


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_message(message: str, context: Any = None) -> str:
    """
    Route a user message to the appropriate agent.
    
    Routing priority:
    1. Explicit /command - maps directly to agent name
    2. Keyword matching - scans message for known keywords
    3. LLM classification - uses model to determine intent (if enabled)
    4. Default fallback - returns 'athena'
    
    Args:
        message: User message
        context: Optional ContextPacket from context_builder
        
    Returns:
        Agent name to handle this message
    """
    logger = _get_logger()
    message_lower = message.lower().strip()
    
    # 1. Check for explicit /command
    command_match = COMMAND_PATTERN.match(message)
    if command_match:
        command = command_match.group(1).lower()
        from core.agent_registry import get_agent
        
        # Direct agent name match
        if get_agent(command):
            logger.info(f"Route: command /{command} -> {command}")
            return command
        
        # Check command aliases
        command_aliases = {
            "status": "athena",
            "help": "athena",
            "start": "athena",
            "fever": "hakari",
            "domain": "hakari",
            "bag_watch": "hakari",
            "ref_report": "hakari",
            "vet_fade": "hakari",
            "audit": "hakari",
            "movies": "cinema",
            "browse": "web",
            "look": "web",
            "scan": "finance",
        }
        
        if command in command_aliases:
            agent = command_aliases[command]
            logger.info(f"Route: command alias /{command} -> {agent}")
            return agent
    
    # 2. Keyword matching
    keyword_map = _get_keyword_map()
    words = set(re.findall(r'\b\w+\b', message_lower))
    
    # Score each agent by keyword matches
    agent_scores: Dict[str, int] = {}
    for word in words:
        if word in keyword_map:
            agent = keyword_map[word]
            agent_scores[agent] = agent_scores.get(agent, 0) + 1
    
    if agent_scores:
        best_agent = max(agent_scores, key=agent_scores.get)
        best_score = agent_scores[best_agent]
        
        # Only route if we have a reasonable match (at least 1 keyword)
        if best_score >= 1:
            logger.info(f"Route: keyword match -> {best_agent} (score: {best_score})")
            return best_agent
    
    # 3. LLM-based classification (optional, for complex cases)
    settings = _get_settings()
    if settings.effective_gemini_key and _should_use_llm_routing(message):
        try:
            agent = _llm_route(message, context)
            if agent:
                logger.info(f"Route: LLM classification -> {agent}")
                return agent
        except Exception as e:
            logger.warning(f"LLM routing failed: {e}")
    
    # 4. Default fallback
    logger.info("Route: fallback -> athena")
    return "athena"


def _should_use_llm_routing(message: str) -> bool:
    """
    Determine if LLM routing should be used.
    
    Use LLM for longer, more complex messages where keyword matching
    might not be sufficient.
    """
    # Use LLM for messages > 50 chars with no clear keywords
    return len(message) > 50


def _llm_route(message: str, context: Any = None) -> Optional[str]:
    """
    Use LLM to classify the intent and route to an agent.
    
    Returns agent name or None if classification fails.
    """
    try:
        from google import genai
        from google.genai import types
        from core.agent_registry import list_agents
        
        settings = _get_settings()
        client = genai.Client(api_key=settings.effective_gemini_key)
        
        agent_list = list_agents()
        
        prompt = f"""Classify the user's intent and return the most appropriate agent.

Available agents: {', '.join(agent_list)}

Agent descriptions:
- athena: General chat, help, greetings
- jarvis: OSINT, security, background checks, investigations
- finance: Money, budget, expenses, spending
- hakari: NBA betting, parlays, sports picks
- cinema: Movies, TV shows, streaming recommendations
- dj: Music, Spotify, playlists
- news: Headlines, daily briefing
- notion: Notes, journal, tasks
- calendar: Events, meetings, scheduling
- web: Browsing websites, web scraping
- deals: Sales, discounts, price tracking

User message: "{message}"

Return ONLY the agent name (one word, lowercase). If unsure, return "athena".
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=20,
                temperature=0.1
            )
        )
        
        result = response.text.strip().lower()
        
        # Validate it's a known agent
        if result in agent_list:
            return result
        
        return None
        
    except Exception as e:
        _get_logger().error(f"LLM routing error: {e}")
        return None


def extract_command_args(message: str) -> tuple:
    """
    Extract command and arguments from a message.
    
    Args:
        message: User message
        
    Returns:
        Tuple of (command, args) or (None, None) if not a command
    """
    match = COMMAND_PATTERN.match(message.strip())
    if match:
        return match.group(1).lower(), match.group(2) or ""
    return None, None


def is_command(message: str) -> bool:
    """Check if message is a /command."""
    return message.strip().startswith("/")
