"""
Tool Registry Tests
===================
Tests for the tool specification and registry system.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestToolSpec:
    """Test ToolSpec dataclass."""
    
    def test_create_tool_spec(self):
        """Test creating a ToolSpec."""
        from core.tools.base import ToolSpec, PermissionLevel
        
        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            permission_level=PermissionLevel.SAFE,
            category="testing"
        )
        
        assert spec.name == "test_tool"
        assert spec.permission_level == PermissionLevel.SAFE
    
    def test_tool_spec_defaults(self):
        """Test ToolSpec default values."""
        from core.tools.base import ToolSpec, PermissionLevel
        
        spec = ToolSpec(
            name="minimal_tool",
            description="Minimal"
        )
        
        assert spec.permission_level == PermissionLevel.SAFE
        assert spec.category == "utility"
        assert spec.input_schema == {}
        assert spec.requires_env == []


class TestPermissionLevel:
    """Test PermissionLevel enum."""
    
    def test_permission_levels(self):
        """Test all permission levels exist."""
        from core.tools.base import PermissionLevel
        
        assert PermissionLevel.SAFE.value == "SAFE"
        assert PermissionLevel.CONFIRM.value == "CONFIRM"
        assert PermissionLevel.BLOCKED.value == "BLOCKED"


class TestToolRegistry:
    """Test ToolRegistry singleton."""
    
    def test_registry_singleton(self):
        """Test registry is a singleton."""
        from core.tools.base import get_tool_registry
        
        reg1 = get_tool_registry()
        reg2 = get_tool_registry()
        
        assert reg1 is reg2
    
    def test_registry_has_default_tools(self):
        """Test registry has default tools registered."""
        from core.tools.base import get_tool_registry
        
        registry = get_tool_registry()
        
        assert "read_file" in registry.list()
        assert "write_file" in registry.list()
        assert "search_web" in registry.list()
    
    def test_get_tool(self):
        """Test getting a tool by name."""
        from core.tools.base import get_tool_registry
        
        registry = get_tool_registry()
        tool = registry.get("read_file")
        
        assert tool is not None
        assert tool.name == "read_file"
    
    def test_get_unknown_tool(self):
        """Test getting an unknown tool returns None."""
        from core.tools.base import get_tool_registry
        
        registry = get_tool_registry()
        tool = registry.get("nonexistent_tool")
        
        assert tool is None
    
    def test_list_by_category(self):
        """Test listing tools by category."""
        from core.tools.base import get_tool_registry
        
        registry = get_tool_registry()
        filesystem_tools = registry.list_by_category("filesystem")
        
        assert len(filesystem_tools) > 0
        assert all(t.category == "filesystem" for t in filesystem_tools)
    
    def test_list_by_permission(self):
        """Test listing tools by permission level."""
        from core.tools.base import get_tool_registry, PermissionLevel
        
        registry = get_tool_registry()
        
        safe_tools = registry.list_by_permission(PermissionLevel.SAFE)
        blocked_tools = registry.list_by_permission(PermissionLevel.BLOCKED)
        
        assert len(safe_tools) > 0
        assert len(blocked_tools) > 0
    
    def test_register_custom_tool(self):
        """Test registering a custom tool."""
        from core.tools.base import get_tool_registry, ToolSpec
        
        registry = get_tool_registry()
        
        custom = ToolSpec(
            name="custom_test_tool",
            description="A custom tool for testing"
        )
        
        registry.register(custom)
        
        retrieved = registry.get("custom_test_tool")
        assert retrieved is not None
        assert retrieved.description == "A custom tool for testing"


class TestPermissionChecking:
    """Test tool permission checking."""
    
    def test_check_safe_tool(self):
        """Test checking a SAFE tool."""
        from core.tools.base import check_tool_permission
        
        result = check_tool_permission("read_file")
        
        assert result["allowed"] is True
        assert result["requires_confirm"] is False
    
    def test_check_confirm_tool(self):
        """Test checking a CONFIRM tool."""
        from core.tools.base import check_tool_permission
        
        result = check_tool_permission("write_file")
        
        assert result["allowed"] is True
        assert result["requires_confirm"] is True
    
    def test_check_blocked_tool(self):
        """Test checking a BLOCKED tool."""
        from core.tools.base import check_tool_permission
        import os
        
        # Make sure social posting is disabled
        os.environ.pop("ATHENA_ENABLE_SOCIAL_POSTING", None)
        
        result = check_tool_permission("post_instagram")
        
        assert result["allowed"] is False
        assert "disabled" in result["reason"].lower()
    
    def test_check_unknown_tool(self):
        """Test checking an unknown tool."""
        from core.tools.base import check_tool_permission
        
        result = check_tool_permission("unknown_tool_xyz")
        
        assert result["allowed"] is False
        assert "not found" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
