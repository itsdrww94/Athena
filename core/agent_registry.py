"""
Athena Agent Registry
=====================
Central registry of all available agents with their specifications.
Used by the router to select appropriate agents for user requests.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class AgentSpec:
    """
    Specification for an Athena agent.
    
    Attributes:
        name: Unique agent identifier
        description: Human-readable description
        allowed_tools: List of tool names this agent can use
        default_model_pref: Preferred model type ('local', 'cloud', 'auto')
        system_prompt_path: Optional path to system prompt file
        keywords: Keywords that trigger routing to this agent
        script_path: Path to agent script (for subprocess execution)
        handler: Optional Python callable for direct execution
    """
    name: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    default_model_pref: str = "auto"  # local, cloud, auto
    system_prompt_path: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    script_path: Optional[str] = None
    handler: Optional[Any] = None  # Callable


# =============================================================================
# AGENT REGISTRY
# =============================================================================

AGENT_REGISTRY: Dict[str, AgentSpec] = {
    # =========================================================================
    # CORE AGENTS
    # =========================================================================
    "athena": AgentSpec(
        name="athena",
        description="General-purpose orchestrator and conversational assistant",
        default_model_pref="cloud",
        keywords=["help", "hello", "hi", "hey", "general", "chat", "talk"],
        allowed_tools=["search_web", "read_file", "write_file", "send_telegram"]
    ),
    
    # =========================================================================
    # SECURITY & OSINT
    # =========================================================================
    "jarvis": AgentSpec(
        name="jarvis",
        description="OSINT and cybersecurity analysis suite",
        allowed_tools=["web_search", "osint_lookup", "report_generate", "notion_create"],
        default_model_pref="cloud",
        keywords=["investigate", "osint", "security", "lookup", "verify", "background", "check"],
        script_path="agents/jarvis_runner.py"
    ),
    
    # =========================================================================
    # FINANCE
    # =========================================================================
    "finance": AgentSpec(
        name="finance",
        description="Budget tracking, expense logging, and financial analysis",
        allowed_tools=["log_expense", "get_balance", "spending_chart", "notion_sync"],
        default_model_pref="local",
        keywords=["money", "budget", "expense", "expenses", "spending", "finance", "cost", "pay", 
                  "dollar", "purchase", "bought", "spent", "income", "save"],
        script_path="agents/super_agents/financial_advisor/agent.py"
    ),
    
    # =========================================================================
    # BETTING / HAKARI
    # =========================================================================
    "hakari": AgentSpec(
        name="hakari",
        description="NBA betting analysis and parlay generation",
        allowed_tools=["nba_stats", "generate_parlay", "check_fever", "ref_report"],
        default_model_pref="cloud",
        keywords=["parlay", "bet", "nba", "basketball", "picks", "odds", "fever",
                  "prizepicks", "underdog", "slip", "over", "under", "points"],
        script_path="agents/parlay/agent.py"
    ),
    
    # =========================================================================
    # MEDIA & ENTERTAINMENT
    # =========================================================================
    "cinema": AgentSpec(
        name="cinema",
        description="Movie and TV show recommendations and tracking",
        allowed_tools=["tmdb_search", "tmdb_trending"],
        default_model_pref="local",
        keywords=["movie", "movies", "film", "watch", "show", "series", "tv", 
                  "netflix", "streaming", "anime", "recommend"],
        script_path="agents/cinema_companion/agent.py"
    ),
    
    "dj": AgentSpec(
        name="dj",
        description="Spotify playback control and music recommendations",
        allowed_tools=["spotify_play", "spotify_search", "spotify_queue"],
        default_model_pref="local",
        keywords=["music", "song", "play", "spotify", "playlist", "dj", "listen"],
        script_path="agents/dj_booth/agent.py"
    ),
    
    # =========================================================================
    # NEWS & INFORMATION
    # =========================================================================
    "news": AgentSpec(
        name="news",
        description="Daily news briefing and topic summaries",
        allowed_tools=["news_fetch", "summarize"],
        default_model_pref="local",
        keywords=["news", "headlines", "briefing", "update", "latest", "today"],
        script_path="agents/news_brief/agent.py"
    ),
    
    # =========================================================================
    # PRODUCTIVITY
    # =========================================================================
    "notion": AgentSpec(
        name="notion",
        description="Notion workspace management - journal, tasks, expenses",
        allowed_tools=["notion_create", "notion_update", "notion_query"],
        default_model_pref="local",
        keywords=["notion", "journal", "task", "note", "page", "database"],
        script_path="agents/notion/agent.py"
    ),
    
    "calendar": AgentSpec(
        name="calendar",
        description="Google Calendar management - events, reminders",
        allowed_tools=["calendar_create", "calendar_list", "calendar_update"],
        default_model_pref="local",
        keywords=["calendar", "event", "meeting", "schedule", "remind", "appointment"],
        script_path="agents/calendar/agent.py"
    ),
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    "web": AgentSpec(
        name="web",
        description="Vision-powered web browsing and scraping",
        allowed_tools=["browser_navigate", "browser_click", "browser_screenshot"],
        default_model_pref="cloud",
        keywords=["browse", "website", "web", "open", "navigate", "scrape"],
        script_path="agents/web_surfer/agent.py"
    ),
    
    "deals": AgentSpec(
        name="deals",
        description="Deal hunting and price monitoring",
        allowed_tools=["deal_search", "price_check"],
        default_model_pref="local",
        keywords=["deal", "deals", "price", "sale", "discount", "cheap", "coupon"],
        script_path="agents/deal_sniper/agent.py"
    ),
}


# =============================================================================
# REGISTRY ACCESS FUNCTIONS
# =============================================================================

def list_agents() -> List[str]:
    """Return list of all registered agent names."""
    return list(AGENT_REGISTRY.keys())


def get_agent(name: str) -> Optional[AgentSpec]:
    """
    Get an agent specification by name.
    
    Args:
        name: Agent name (case-insensitive)
        
    Returns:
        AgentSpec if found, None otherwise
    """
    return AGENT_REGISTRY.get(name.lower())


def get_agent_for_keyword(keyword: str) -> Optional[AgentSpec]:
    """
    Find an agent whose keywords match the given term.
    
    Args:
        keyword: Keyword to search for
        
    Returns:
        First matching AgentSpec, or None
    """
    keyword_lower = keyword.lower()
    for agent in AGENT_REGISTRY.values():
        if keyword_lower in agent.keywords:
            return agent
    return None


def get_all_keywords() -> Dict[str, str]:
    """
    Get a mapping of all keywords to agent names.
    
    Returns:
        Dict mapping keyword -> agent_name
    """
    keywords = {}
    for agent in AGENT_REGISTRY.values():
        for kw in agent.keywords:
            keywords[kw] = agent.name
    return keywords


def register_agent(spec: AgentSpec) -> None:
    """
    Register a new agent or update existing.
    
    Args:
        spec: AgentSpec to register
    """
    AGENT_REGISTRY[spec.name.lower()] = spec
