"""
Router Tests
============
Tests for the message routing system.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCommandExtraction:
    """Test command extraction from messages."""
    
    def test_extract_simple_command(self):
        """Test extracting a simple /command."""
        from core.router import extract_command_args
        
        command, args = extract_command_args("/finance")
        
        assert command == "finance"
        assert args == ""
    
    def test_extract_command_with_args(self):
        """Test extracting a command with arguments."""
        from core.router import extract_command_args
        
        command, args = extract_command_args("/finance log 25 food")
        
        assert command == "finance"
        assert args == "log 25 food"
    
    def test_extract_no_command(self):
        """Test that non-commands return None."""
        from core.router import extract_command_args
        
        command, args = extract_command_args("Hello there")
        
        assert command is None
        assert args is None
    
    def test_is_command(self):
        """Test is_command helper."""
        from core.router import is_command
        
        assert is_command("/help") is True
        assert is_command("/finance log") is True
        assert is_command("Hello") is False
        assert is_command("What is /help?") is False


class TestRouting:
    """Test message routing."""
    
    def test_route_explicit_command(self):
        """Test routing explicit /command."""
        from core.router import route_message
        
        agent = route_message("/finance")
        assert agent == "finance"
        
        agent = route_message("/jarvis investigate example.com")
        assert agent == "jarvis"
    
    def test_route_command_alias(self):
        """Test routing command aliases."""
        from core.router import route_message
        
        agent = route_message("/fever")
        assert agent == "hakari"
        
        agent = route_message("/help")
        assert agent == "athena"
    
    def test_route_keyword_matching(self):
        """Test keyword-based routing."""
        from core.router import route_message
        
        agent = route_message("What's my spending this month?")
        assert agent == "finance"
        
        agent = route_message("Can you look up a parlay for tonight?")
        assert agent == "hakari"
        
        agent = route_message("Play some music")
        assert agent == "dj"
    
    def test_route_multiple_keywords(self):
        """Test routing with multiple keyword matches."""
        from core.router import route_message
        
        # Should prefer agent with more matches
        agent = route_message("Check my budgetfg spending expenses")
        assert agent == "finance"
    
    def test_route_fallback(self):
        """Test that unknown messages route to athena."""
        from core.router import route_message
        
        agent = route_message("What is quantum computing?")
        assert agent == "athena"


class TestKeywordMap:
    """Test keyword to agent mapping."""
    
    def test_keyword_map_loaded(self):
        """Test that keyword map is populated."""
        from core.router import _get_keyword_map
        
        keyword_map = _get_keyword_map()
        
        assert len(keyword_map) > 0
        assert "money" in keyword_map
        assert keyword_map["money"] == "finance"
    
    def test_keyword_map_reset(self):
        """Test keyword map reset."""
        from core.router import _get_keyword_map, _reset_keyword_map
        
        # Get initial map
        map1 = _get_keyword_map()
        
        # Reset
        _reset_keyword_map()
        
        # Get again (should be rebuilt)
        map2 = _get_keyword_map()
        
        assert len(map2) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
