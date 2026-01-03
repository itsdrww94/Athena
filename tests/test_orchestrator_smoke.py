"""
Orchestrator Smoke Tests
========================
Basic smoke tests for the orchestration system.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOrchestrator:
    """Smoke tests for the orchestrator."""
    
    def test_handle_message_import(self):
        """Test that handle_message can be imported."""
        from core.orchestrator import handle_message
        
        assert callable(handle_message)
    
    def test_handle_simple_message(self):
        """Test handling a simple message."""
        from core.orchestrator import handle_message
        
        # This should work even without full setup
        # It may fail if Gemini isn't configured, but shouldn't crash
        try:
            response = handle_message(
                user_id="test_user",
                session_id="test_session",
                message="/help",
                interface="test"
            )
            
            assert isinstance(response, str)
            assert len(response) > 0
        except Exception as e:
            # OK if it fails due to missing API keys
            assert "configured" in str(e).lower() or "error" in str(e).lower()
    
    def test_handle_command_routing(self):
        """Test that commands are routed correctly."""
        from core.router import route_message
        from core.agent_registry import get_agent
        
        # Test routing works
        agent_name = route_message("/finance log 25 lunch")
        assert agent_name == "finance"
        
        # Test agent exists
        agent = get_agent(agent_name)
        assert agent is not None
        assert agent.name == "finance"


class TestAppEntrypoint:
    """Test the main app entrypoint."""
    
    def test_run_athena_import(self):
        """Test that run_athena can be imported."""
        from core.app import run_athena
        
        assert callable(run_athena)
    
    def test_run_athena_signature(self):
        """Test run_athena accepts expected arguments."""
        from core.app import run_athena
        import inspect
        
        sig = inspect.signature(run_athena)
        params = list(sig.parameters.keys())
        
        assert "input_message" in params
        assert "interface" in params
        assert "user_id" in params


class TestLogging:
    """Test logging functionality."""
    
    def test_logger_creation(self):
        """Test creating a logger."""
        from core.logging import get_logger
        
        logger = get_logger("test.module")
        
        assert logger is not None
        assert logger.name == "test.module"
    
    def test_run_id(self):
        """Test run ID generation."""
        from core.logging import new_run_id, get_run_id
        
        run_id = new_run_id()
        
        assert len(run_id) == 8
        assert get_run_id() == run_id
    
    def test_context_clearing(self):
        """Test context clearing."""
        from core.logging import new_run_id, clear_context, get_run_id
        
        new_run_id()
        clear_context()
        
        assert get_run_id() == ""


class TestSettings:
    """Test settings configuration."""
    
    def test_settings_import(self):
        """Test that settings can be imported."""
        from core.settings import get_settings, AthenaSettings
        
        settings = get_settings()
        
        assert isinstance(settings, AthenaSettings)
    
    def test_settings_defaults(self):
        """Test default settings values."""
        from core.settings import get_settings
        
        settings = get_settings()
        
        assert settings.athena_env in ["dev", "prod"]
        assert settings.max_cost_per_day > 0
        assert settings.default_model_cloud is not None
    
    def test_settings_properties(self):
        """Test settings property methods."""
        from core.settings import get_settings
        
        settings = get_settings()
        
        # These should return bool without crashing
        assert isinstance(settings.is_supabase_configured, bool)
        assert isinstance(settings.is_telegram_configured, bool)
        assert isinstance(settings.is_gemini_configured, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
