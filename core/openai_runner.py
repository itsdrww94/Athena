"""
OpenAI Agent Runner
====================
Primary AI execution using OpenAI Agents SDK.
Falls back to None on failure to trigger Gemini fallback.
"""

from typing import Any, Optional

# Lazy imports
_logger = None
_settings = None

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.openai_runner")
    return _logger

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings


def run_openai_chat(
    agent_spec: Any,
    message: str,
    context: Any = None,
    interface: str = "cli"
) -> Optional[str]:
    """
    Use OpenAI Agents SDK for conversational response.
    
    Returns:
        Response string on success, None on failure (triggers fallback)
    """
    logger = _get_logger()
    settings = _get_settings()
    
    if not settings.openai_api_key:
        logger.debug("OpenAI not configured, skipping")
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Build system prompt
        system_prompt = f"""You are Athena, a Personal Super Agentic AI System.
You are currently operating as the '{agent_spec.name}' agent: {agent_spec.description}

Be concise, direct, and helpful. You communicate via {interface}.
If asked about your capabilities, mention available commands: /help
"""
        
        # Add context if available
        if context:
            try:
                context_str = context.to_prompt_string()
                if context_str:
                    system_prompt += f"\n**CONTEXT:**\n{context_str}\n"
            except Exception:
                pass
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        # Generate response using GPT-4
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective choice
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        logger.info(f"OpenAI response generated ({len(result)} chars)")
        return result if result else None
        
    except ImportError as e:
        logger.warning(f"OpenAI SDK not installed: {e}")
        return None
    except Exception as e:
        logger.warning(f"OpenAI error, falling back to Gemini: {e}")
        return None


def is_openai_available() -> bool:
    """Check if OpenAI is available and configured."""
    settings = _get_settings()
    if not settings.openai_api_key:
        return False
    
    try:
        from openai import OpenAI
        return True
    except ImportError:
        return False
