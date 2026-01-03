"""
Tool Registry for Athena
========================
Central registry for tracking tool availability and routing triggers.
Enables capability-aware routing to prevent wrong tool selection.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum

logger = logging.getLogger("athena.tools")


class ToolStatus(Enum):
    OK = "OK"
    OFFLINE = "OFFLINE"
    MISSING_CONFIG = "MISSING_CONFIG"
    ERROR = "ERROR"


@dataclass
class ToolConfig:
    """Configuration for a registered tool."""
    name: str
    description: str
    status: ToolStatus = ToolStatus.OK
    
    # Routing
    routing_triggers: List[str] = field(default_factory=list)  # Regex patterns
    priority: int = 0  # Higher = checked first
    
    # Availability
    required_env_vars: List[str] = field(default_factory=list)
    required_modules: List[str] = field(default_factory=list)
    
    # Surface restrictions
    allowed_surfaces: List[str] = field(default_factory=lambda: ["terminal", "telegram"])
    
    # Action classification
    action_type: str = "read"  # read, propose, execute
    risk_level: str = "LOW"    # LOW, MED, HIGH
    
    # Error info
    error_message: Optional[str] = None


class ToolRegistry:
    """
    Central registry of all available tools and their status.
    
    Usage:
        registry = get_tool_registry()
        if registry.is_available("local_data_analyzer"):
            # Use the tool
        
        # Check what triggered
        tool = registry.match_routing_trigger("analyze the data folder")
        if tool:
            print(f"Route to: {tool.name}")
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._tools: Dict[str, ToolConfig] = {}
        self._register_default_tools()
        self._initialized = True
    
    def _register_default_tools(self):
        """Register all known tools with their configurations."""
        
        # Local Data Analyzer - HIGH PRIORITY for file operations
        self.register(ToolConfig(
            name="local_data_analyzer",
            description="Scan, classify, and analyze local files in data folder",
            routing_triggers=[
                r"data folder", r"local files?", r"logs?", r"directory",
                r"\./data", r"data/", r"analyze.*(folder|files|logs)",
                r"\.json$", r"\.zip$", r"\.csv$",
                r"chatgpt.*(logs?|export)", r"spotify.*(logs?|export)", 
                r"uber.*(logs?|export)", r"scan.*(folder|directory)",
            ],
            priority=100,  # High priority - check before web search
            allowed_surfaces=["terminal", "telegram"],
            action_type="read",
            risk_level="LOW"
        ))
        
        # Telegram Notifier - For distinct "reminder via telegram" requests
        self.register(ToolConfig(
            name="telegram_notifier",
            description="Schedule and send Telegram reminders/notifications",
            routing_triggers=[
                r"telegram reminder", r"dm me", r"message me on telegram",
                r"send me a (telegram )?reminder", r"telegram.*at \d",
                r"remind me (via|on) telegram", r"notify me (via|on) telegram",
            ],
            priority=90,
            required_env_vars=["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
            allowed_surfaces=["terminal", "telegram"],
            action_type="execute",
            risk_level="LOW"
        ))
        
        # Calendar Scheduler - For calendar-specific requests
        self.register(ToolConfig(
            name="calendar_scheduler",
            description="Create calendar events and meetings",
            routing_triggers=[
                r"add to (my )?calendar", r"schedule.*(meeting|appointment|event)",
                r"calendar entry", r"put.*(on|in) (my )?calendar",
            ],
            priority=85,
            allowed_surfaces=["terminal", "telegram"],
            action_type="execute",
            risk_level="MED"
        ))
        
        # Web Researcher - LOWER priority than local tools
        self.register(ToolConfig(
            name="web_researcher",
            description="Search the web for information",
            routing_triggers=[
                r"search (the )?(web|internet|online)",
                r"look up online", r"google", r"find info about",
            ],
            priority=50,  # Lower priority
            allowed_surfaces=["terminal", "telegram"],
            action_type="read",
            risk_level="LOW"
        ))
        
        # Gmail Scanner
        self.register(ToolConfig(
            name="gmail_scanner",
            description="Search and analyze Gmail messages",
            routing_triggers=[
                r"email", r"gmail", r"inbox", r"mail",
                r"check.*(my )?(emails?|inbox)",
            ],
            priority=80,
            required_env_vars=["GOOGLE_CREDENTIALS_FILE"],
            allowed_surfaces=["terminal", "telegram"],
            action_type="read",
            risk_level="LOW"
        ))
        
        # Check availability for all registered tools
        self._check_all_availability()
    
    def register(self, config: ToolConfig):
        """Register a tool configuration."""
        self._tools[config.name] = config
        logger.debug(f"Registered tool: {config.name}")
    
    def get_tool(self, name: str) -> Optional[ToolConfig]:
        """Get a tool configuration by name."""
        return self._tools.get(name)
    
    def is_available(self, name: str) -> bool:
        """Check if a tool is available and properly configured."""
        tool = self.get_tool(name)
        return tool is not None and tool.status == ToolStatus.OK
    
    def match_routing_trigger(self, user_input: str, surface: str = "terminal") -> Optional[ToolConfig]:
        """
        Find the highest-priority tool whose routing trigger matches the input.
        Returns None if no tool matches.
        """
        import re
        
        matches = []
        for tool in self._tools.values():
            # Skip unavailable tools
            if tool.status != ToolStatus.OK:
                continue
            
            # Skip tools not allowed on this surface
            if surface not in tool.allowed_surfaces:
                continue
            
            # Check routing triggers
            for pattern in tool.routing_triggers:
                if re.search(pattern, user_input, re.IGNORECASE):
                    matches.append(tool)
                    break
        
        if not matches:
            return None
        
        # Return highest priority
        return max(matches, key=lambda t: t.priority)
    
    def check_health(self) -> Dict[str, str]:
        """Return health status of all tools."""
        self._check_all_availability()
        return {name: tool.status.value for name, tool in self._tools.items()}
    
    def _check_all_availability(self):
        """Check availability of all registered tools."""
        for tool in self._tools.values():
            self._check_tool_availability(tool)
    
    def _check_tool_availability(self, tool: ToolConfig):
        """Check if a single tool is available."""
        # Check required env vars
        for var in tool.required_env_vars:
            if not os.getenv(var):
                tool.status = ToolStatus.MISSING_CONFIG
                tool.error_message = f"Missing env var: {var}"
                return
        
        # Check required modules
        for module in tool.required_modules:
            try:
                __import__(module)
            except ImportError:
                tool.status = ToolStatus.OFFLINE
                tool.error_message = f"Missing module: {module}"
                return
        
        tool.status = ToolStatus.OK
        tool.error_message = None
    
    def get_unavailable_message(self, tool_name: str) -> str:
        """Get a user-friendly message for why a tool is unavailable."""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Tool '{tool_name}' is not registered."
        
        if tool.status == ToolStatus.OK:
            return f"Tool '{tool_name}' is available."
        
        return f"I can't use {tool_name} right now: {tool.error_message}"


# Global accessor
def get_tool_registry() -> ToolRegistry:
    """Get the singleton ToolRegistry instance."""
    return ToolRegistry()
