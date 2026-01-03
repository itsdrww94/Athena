"""
Context Builder Tests
=====================
Tests context building functionality.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestContextPacket:
    """Test ContextPacket dataclass."""
    
    def test_empty_packet(self):
        """Test creating an empty context packet."""
        from services.memory.context_builder import ContextPacket
        
        packet = ContextPacket()
        
        assert packet.user_name == "User"
        assert packet.user_facts == {}
        assert packet.recent_messages == []
        assert packet.semantic_matches == []
    
    def test_packet_with_data(self):
        """Test creating a populated context packet."""
        from services.memory.context_builder import ContextPacket
        
        packet = ContextPacket(
            user_name="Drew",
            user_facts={"location": "Minneapolis", "interests": ["AI"]},
            recent_messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            current_session_id="session_123"
        )
        
        assert packet.user_name == "Drew"
        assert packet.user_facts["location"] == "Minneapolis"
        assert len(packet.recent_messages) == 2
    
    def test_to_prompt_string(self):
        """Test converting packet to prompt string."""
        from services.memory.context_builder import ContextPacket
        
        packet = ContextPacket(
            user_name="Drew",
            user_facts={"location": "Minneapolis"},
            recent_messages=[
                {"role": "user", "content": "What's the weather?"}
            ]
        )
        
        prompt = packet.to_prompt_string()
        
        assert "Drew" in prompt
        assert "Minneapolis" in prompt
        assert "USER" in prompt or "user" in prompt.lower()
    
    def test_to_dict(self):
        """Test converting packet to dictionary."""
        from services.memory.context_builder import ContextPacket
        
        packet = ContextPacket(
            user_name="Drew",
            current_interface="telegram"
        )
        
        d = packet.to_dict()
        
        assert isinstance(d, dict)
        assert d["user_name"] == "Drew"
        assert d["current_interface"] == "telegram"


class TestBuildContext:
    """Test the build_context function."""
    
    def test_build_context_no_memory(self):
        """Test building context when memory is not configured."""
        from services.memory.context_builder import build_context, ContextPacket
        
        # This should work even without Supabase configured
        packet = build_context(
            user_id="test_user",
            session_id="test_session",
            query="Hello",
            include_semantic=False
        )
        
        assert isinstance(packet, ContextPacket)
        assert packet.current_session_id == "test_session"
    
    def test_build_context_with_memory(self):
        """Test building context with memory (if configured)."""
        from services.memory.context_builder import build_context
        from services.memory.client import get_memory
        
        memory = get_memory()
        if not memory.is_configured:
            pytest.skip("Supabase not configured")
        
        packet = build_context(
            user_id="default",
            session_id="test_session",
            query="What's my name?",
            include_semantic=False,
            max_facts=5,
            max_recent=5
        )
        
        # Should have some user facts from default user
        assert isinstance(packet, ContextPacket)


class TestQuickContext:
    """Test the get_quick_context function."""
    
    def test_quick_context(self):
        """Test getting quick context string."""
        from services.memory.context_builder import get_quick_context
        
        context = get_quick_context()
        
        assert isinstance(context, str)
        # Should contain something even if memory isn't configured
        assert "User" in context or len(context) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
