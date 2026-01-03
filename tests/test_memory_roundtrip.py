"""
Memory Roundtrip Tests
======================
Tests basic memory operations: write and read events/facts.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMemoryRoundtrip:
    """Test memory write and read operations."""
    
    @pytest.fixture
    def memory(self):
        """Get memory store instance."""
        from services.memory.client import get_memory
        return get_memory()
    
    def test_memory_config(self, memory):
        """Test that memory is configured (or gracefully handles missing config)."""
        # This test passes whether Supabase is configured or not
        assert hasattr(memory, 'is_configured')
        if memory.is_configured:
            assert memory.url is not None
            assert memory.key is not None
    
    def test_event_write_read(self, memory):
        """Test writing and reading an event."""
        if not memory.is_configured:
            pytest.skip("Supabase not configured")
        
        # Write an event
        event_id = memory.write_event(
            user_id="test_user",
            session_id="test_session",
            role="user",
            content="Test message from pytest",
            metadata={"test": True}
        )
        
        assert event_id is not None, "Event write should return an ID"
        
        # Read recent events
        events = memory.get_recent_events(
            user_id="test_user",
            session_id="test_session",
            limit=5
        )
        
        assert len(events) > 0, "Should find at least one event"
        
        # Find our event
        found = any(e.content == "Test message from pytest" for e in events)
        assert found, "Should find the test event"
    
    def test_fact_upsert_retrieve(self, memory):
        """Test upserting and retrieving a fact."""
        if not memory.is_configured:
            pytest.skip("Supabase not configured")
        
        # Upsert a fact
        fact_id = memory.upsert_fact(
            user_id="test_user",
            key="test_preference",
            value={"color": "blue", "number": 42},
            category="preference",
            confidence=0.9
        )
        
        assert fact_id is not None, "Fact upsert should return an ID"
        
        # Retrieve facts
        facts = memory.retrieve_facts(
            user_id="test_user",
            keys=["test_preference"],
            limit=5
        )
        
        assert len(facts) > 0, "Should find at least one fact"
        
        # Check the value
        fact = facts[0]
        assert fact.key == "test_preference"
        assert fact.value.get("color") == "blue"
    
    def test_get_single_fact(self, memory):
        """Test getting a single fact by key."""
        if not memory.is_configured:
            pytest.skip("Supabase not configured")
        
        # First upsert
        memory.upsert_fact(
            user_id="test_user",
            key="single_fact_test",
            value="test_value"
        )
        
        # Get it
        value = memory.get_fact("test_user", "single_fact_test")
        assert value is not None
    
    def test_legacy_log_interaction(self, memory):
        """Test legacy log_interaction method."""
        if not memory.is_configured:
            pytest.skip("Supabase not configured")
        
        success = memory.log_interaction(
            user_input="Hello, legacy test",
            athena_response="Hello back!",
            source="pytest"
        )
        
        assert success is True
    
    def test_legacy_get_context(self, memory):
        """Test legacy get_context method."""
        if not memory.is_configured:
            pytest.skip("Supabase not configured")
        
        context = memory.get_context(limit=3)
        
        # Should return a string (may be empty)
        assert isinstance(context, str)


class TestMemoryDataClasses:
    """Test memory data classes."""
    
    def test_event_creation(self):
        """Test Event dataclass."""
        from services.memory.client import Event
        
        event = Event(
            id=1,
            user_id="user1",
            session_id="session1",
            role="user",
            content="Hello"
        )
        
        assert event.id == 1
        assert event.user_id == "user1"
        assert event.role == "user"
    
    def test_fact_creation(self):
        """Test Fact dataclass."""
        from services.memory.client import Fact
        
        fact = Fact(
            id=1,
            user_id="user1",
            key="name",
            value="Drew"
        )
        
        assert fact.id == 1
        assert fact.key == "name"
        assert fact.value == "Drew"
    
    def test_chunk_creation(self):
        """Test Chunk dataclass."""
        from services.memory.client import Chunk
        
        chunk = Chunk(
            id=1,
            user_id="user1",
            source="conversation",
            chunk_text="Some text",
            similarity=0.95
        )
        
        assert chunk.id == 1
        assert chunk.similarity == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
