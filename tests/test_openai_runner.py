"""
OpenAI Runner Tests
===================
Test OpenAI integration and fallback behavior.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOpenAIRunner:
    """Tests for the OpenAI runner module."""
    
    def test_openai_runner_import(self):
        """Test that openai_runner can be imported."""
        from core.openai_runner import run_openai_chat, is_openai_available
        
        assert callable(run_openai_chat)
        assert callable(is_openai_available)
    
    def test_openai_not_configured_returns_none(self):
        """Test that run_openai_chat returns None when not configured."""
        from core.openai_runner import run_openai_chat
        
        # Create mock agent spec
        mock_spec = MagicMock()
        mock_spec.name = "test"
        mock_spec.description = "Test agent"
        
        # Mock settings to have no OpenAI key
        with patch('core.openai_runner._get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = None
            
            result = run_openai_chat(
                agent_spec=mock_spec,
                message="Hello",
                context=None,
                interface="test"
            )
            
            assert result is None
    
    def test_is_openai_available_no_key(self):
        """Test is_openai_available returns False when no key."""
        from core.openai_runner import is_openai_available
        
        with patch('core.openai_runner._get_settings') as mock_settings:
            mock_settings.return_value.openai_api_key = None
            
            assert is_openai_available() == False


class TestFallbackBehavior:
    """Tests for the OpenAI-Gemini fallback chain."""
    
    def test_fallback_function_exists(self):
        """Test that the fallback function exists in runner."""
        from agents.runner import _run_ai_chat_with_fallback
        
        assert callable(_run_ai_chat_with_fallback)
    
    def test_fallback_to_gemini_when_openai_fails(self):
        """Test that Gemini is used when OpenAI returns None."""
        from agents.runner import _run_ai_chat_with_fallback
        
        mock_spec = MagicMock()
        mock_spec.name = "test"
        mock_spec.description = "Test agent"
        
        with patch('agents.runner._run_gemini_chat') as mock_gemini:
            mock_gemini.return_value = "Gemini response"
            
            with patch('core.openai_runner.run_openai_chat') as mock_openai:
                mock_openai.return_value = None  # OpenAI fails
                
                result = _run_ai_chat_with_fallback(
                    agent_spec=mock_spec,
                    message="Hello",
                    context=None,
                    interface="test"
                )
                
                # Should have called Gemini as fallback
                mock_gemini.assert_called_once()
                assert result == "Gemini response"


class TestSettingsOpenAI:
    """Test OpenAI settings."""
    
    def test_is_openai_configured_property(self):
        """Test is_openai_configured property exists."""
        from core.settings import get_settings
        
        settings = get_settings()
        
        # Should return bool without crashing
        assert isinstance(settings.is_openai_configured, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
