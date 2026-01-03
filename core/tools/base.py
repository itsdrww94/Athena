"""
Athena Tool Contracts
=====================
Standard tool specification with schemas, permissions, and execution.

Every tool in Athena must conform to ToolSpec to ensure:
- Consistent input/output validation
- Permission gating (SAFE/CONFIRM/BLOCKED)
- Structured logging
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List, Type
from enum import Enum
from abc import ABC, abstractmethod


# =============================================================================
# PERMISSION LEVELS
# =============================================================================

class PermissionLevel(Enum):
    """Tool permission levels."""
    SAFE = "SAFE"           # Execute immediately without confirmation
    CONFIRM = "CONFIRM"     # Require user confirmation before executing
    BLOCKED = "BLOCKED"     # Blocked unless explicitly enabled in settings


# =============================================================================
# TOOL SPECIFICATION
# =============================================================================

@dataclass
class ToolSpec:
    """
    Specification for an Athena tool.
    
    All tools must be registered with a ToolSpec to be usable by agents.
    """
    name: str
    description: str
    permission_level: PermissionLevel = PermissionLevel.SAFE
    
    # Input/Output schemas (using dicts for simplicity, can be Pydantic models)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Execution
    handler: Optional[Callable] = None
    
    # Metadata
    category: str = "utility"
    requires_env: List[str] = field(default_factory=list)  # Required env vars
    allowed_interfaces: List[str] = field(default_factory=lambda: ["cli", "telegram", "api"])
    
    # Risk assessment
    risk_level: str = "low"  # low, medium, high
    side_effects: List[str] = field(default_factory=list)  # e.g., ["writes_file", "sends_message"]


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """
    Central registry for all available tools.
    
    Usage:
        registry = get_tool_registry()
        registry.register(my_tool_spec)
        tool = registry.get("my_tool")
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolSpec] = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._register_default_tools()
        self._initialized = True
    
    def _register_default_tools(self):
        """Register built-in tools."""
        
        # File operations
        self.register(ToolSpec(
            name="read_file",
            description="Read contents of a file from the local filesystem",
            permission_level=PermissionLevel.SAFE,
            category="filesystem",
            input_schema={"path": "string"},
            output_schema={"content": "string", "size": "integer"}
        ))
        
        self.register(ToolSpec(
            name="write_file",
            description="Write content to a file on the local filesystem",
            permission_level=PermissionLevel.CONFIRM,
            category="filesystem",
            side_effects=["writes_file"],
            input_schema={"path": "string", "content": "string"},
            output_schema={"success": "boolean", "path": "string"}
        ))
        
        self.register(ToolSpec(
            name="list_directory",
            description="List files and directories in a path",
            permission_level=PermissionLevel.SAFE,
            category="filesystem",
            input_schema={"path": "string"},
            output_schema={"files": "array", "directories": "array"}
        ))
        
        # Web/Search
        self.register(ToolSpec(
            name="search_web",
            description="Search the web for information",
            permission_level=PermissionLevel.SAFE,
            category="web",
            input_schema={"query": "string", "num_results": "integer"},
            output_schema={"results": "array"}
        ))
        
        # Communication
        self.register(ToolSpec(
            name="send_telegram",
            description="Send a message via Telegram",
            permission_level=PermissionLevel.SAFE,
            category="communication",
            requires_env=["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
            side_effects=["sends_message"],
            input_schema={"text": "string", "parse_mode": "string"},
            output_schema={"success": "boolean", "message_id": "integer"}
        ))
        
        # Social Media (BLOCKED by default)
        self.register(ToolSpec(
            name="post_instagram",
            description="Post content to Instagram",
            permission_level=PermissionLevel.BLOCKED,
            category="social",
            requires_env=["IG_USERNAME", "IG_PASSWORD"],
            side_effects=["posts_social"],
            risk_level="high"
        ))
        
        self.register(ToolSpec(
            name="post_twitter",
            description="Post content to Twitter/X",
            permission_level=PermissionLevel.BLOCKED,
            category="social",
            requires_env=["TWITTER_USERNAME", "TWITTER_PASSWORD"],
            side_effects=["posts_social"],
            risk_level="high"
        ))
        
        # Memory
        self.register(ToolSpec(
            name="search_memory",
            description="Search Athena's memory for relevant information",
            permission_level=PermissionLevel.SAFE,
            category="memory",
            input_schema={"query": "string", "limit": "integer"},
            output_schema={"results": "array"}
        ))
        
        # System
        self.register(ToolSpec(
            name="run_command",
            description="Execute a shell command",
            permission_level=PermissionLevel.CONFIRM,
            category="system",
            side_effects=["executes_command"],
            risk_level="high",
            input_schema={"command": "string", "cwd": "string"},
            output_schema={"stdout": "string", "stderr": "string", "exit_code": "integer"}
        ))
    
    def register(self, tool: ToolSpec) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[ToolSpec]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def list_by_category(self, category: str) -> List[ToolSpec]:
        """List tools in a specific category."""
        return [t for t in self._tools.values() if t.category == category]
    
    def list_by_permission(self, level: PermissionLevel) -> List[ToolSpec]:
        """List tools with a specific permission level."""
        return [t for t in self._tools.values() if t.permission_level == level]
    
    def is_available(self, name: str) -> bool:
        """Check if a tool is registered and has required env vars."""
        tool = self.get(name)
        if not tool:
            return False
        
        import os
        for env_var in tool.requires_env:
            if not os.getenv(env_var):
                return False
        
        return True


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

def get_tool_registry() -> ToolRegistry:
    """Get the singleton ToolRegistry instance."""
    return ToolRegistry()


# =============================================================================
# PERMISSION CHECKING
# =============================================================================

def check_tool_permission(tool_name: str, interface: str = "cli") -> Dict[str, Any]:
    """
    Check if a tool can be executed.
    
    Returns:
        Dict with 'allowed', 'reason', and 'requires_confirm' keys
    """
    registry = get_tool_registry()
    tool = registry.get(tool_name)
    
    if not tool:
        return {
            "allowed": False,
            "reason": f"Tool '{tool_name}' not found",
            "requires_confirm": False
        }
    
    # Check interface
    if interface not in tool.allowed_interfaces:
        return {
            "allowed": False,
            "reason": f"Tool not allowed on {interface} interface",
            "requires_confirm": False
        }
    
    # Check permission level
    if tool.permission_level == PermissionLevel.BLOCKED:
        # Check if explicitly enabled
        import os
        if tool.category == "social":
            enabled = os.getenv("ATHENA_ENABLE_SOCIAL_POSTING", "").lower() == "true"
            if not enabled:
                return {
                    "allowed": False,
                    "reason": "Social posting is disabled. Set ATHENA_ENABLE_SOCIAL_POSTING=true to enable.",
                    "requires_confirm": False
                }
    
    if tool.permission_level == PermissionLevel.CONFIRM:
        return {
            "allowed": True,
            "reason": "Requires user confirmation",
            "requires_confirm": True
        }
    
    return {
        "allowed": True,
        "reason": "OK",
        "requires_confirm": False
    }
