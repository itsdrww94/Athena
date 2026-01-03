"""
Athena Agent Runner
===================
Unified agent execution layer.

Supports two execution modes:
1. Direct Python callable (for built-in agents)
2. Subprocess execution (for script-based agents)
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional, Dict

# Lazy imports
_logger = None
_settings = None

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.runner")
    return _logger

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings


# Base directory for resolving script paths
BASE_DIR = Path(__file__).parent.parent


def run_agent(
    agent_spec: Any,  # AgentSpec
    message: str,
    context: Any = None,  # ContextPacket
    command: Optional[str] = None,
    args: Optional[str] = None,
    interface: str = "cli"
) -> str:
    """
    Execute an agent and return its response.
    
    Execution priority:
    1. If agent_spec.handler is set, call it directly
    2. If agent_spec.script_path is set, run via subprocess
    3. Fall back to Gemini for general chat
    
    Args:
        agent_spec: AgentSpec from agent_registry
        message: User message
        context: ContextPacket from context builder
        command: Extracted command (e.g., "finance")
        args: Extracted arguments (e.g., "log 25 food")
        interface: Source interface
        
    Returns:
        Response string
    """
    logger = _get_logger()
    start_time = time.time()
    
    agent_name = agent_spec.name
    logger.info(f"Running agent: {agent_name}")
    
    # 1. Direct handler execution
    if agent_spec.handler is not None:
        try:
            result = agent_spec.handler(
                message=message,
                context=context,
                command=command,
                args=args,
                interface=interface
            )
            return str(result)
        except Exception as e:
            logger.error(f"Handler execution failed: {e}")
            return f"Agent error: {e}"
    
    # 2. Subprocess execution
    if agent_spec.script_path:
        return _run_subprocess(
            agent_spec=agent_spec,
            message=message,
            command=command,
            args=args,
            interface=interface
        )
    
    # 3. AI chat with fallback: OpenAI → Gemini
    return _run_ai_chat_with_fallback(
        agent_spec=agent_spec,
        message=message,
        context=context,
        interface=interface
    )


def _run_subprocess(
    agent_spec: Any,
    message: str,
    command: Optional[str],
    args: Optional[str],
    interface: str
) -> str:
    """Run an agent script via subprocess."""
    logger = _get_logger()
    
    script_path = BASE_DIR / agent_spec.script_path
    
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return f"Agent script not found: {agent_spec.script_path}"
    
    # Build command
    cmd = [sys.executable, str(script_path)]
    
    # Add arguments based on command
    if args:
        cmd.extend(args.split())
    
    logger.info(f"Subprocess: {' '.join(cmd[:5])}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(BASE_DIR),
            encoding='utf-8',
            errors='replace'
        )
        
        output = result.stdout.strip() or result.stderr.strip()
        
        if not output:
            output = "✅ Command completed (no output)"
        
        # Truncate if too long
        if len(output) > 4000:
            output = output[:4000] + "\n\n... (truncated)"
        
        return output
        
    except subprocess.TimeoutExpired:
        return "⏰ Agent timed out (30s limit)"
    except Exception as e:
        logger.error(f"Subprocess error: {e}")
        return f"Agent execution error: {e}"


def _run_ai_chat_with_fallback(
    agent_spec: Any,
    message: str,
    context: Any,
    interface: str
) -> str:
    """
    AI chat with fallback chain: OpenAI → Gemini.
    
    Tries OpenAI first (if configured), falls back to Gemini on failure.
    """
    logger = _get_logger()
    
    # 1. Try OpenAI first
    try:
        from core.openai_runner import run_openai_chat
        
        result = run_openai_chat(
            agent_spec=agent_spec,
            message=message,
            context=context,
            interface=interface
        )
        
        if result:
            logger.info("Response generated via OpenAI")
            return result
        
        logger.debug("OpenAI returned None, falling back to Gemini")
    except Exception as e:
        logger.debug(f"OpenAI attempt failed: {e}, falling back to Gemini")
    
    # 2. Fallback to Gemini
    return _run_gemini_chat(
        agent_spec=agent_spec,
        message=message,
        context=context,
        interface=interface
    )


def _run_gemini_chat(
    agent_spec: Any,
    message: str,
    context: Any,
    interface: str
) -> str:
    """Use Gemini for conversational response."""
    logger = _get_logger()
    settings = _get_settings()
    
    if not settings.effective_gemini_key:
        return "AI backend not configured. Please set GEMINI_API_KEY in .env"
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=settings.effective_gemini_key)
        
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
        
        # Generate response
        response = client.models.generate_content(
            model=settings.default_model_cloud,
            contents=f"{system_prompt}\n\nUser: {message}",
            config=types.GenerateContentConfig(
                max_output_tokens=2000,
                temperature=0.7
            )
        )
        
        return response.text if response.text else "I couldn't generate a response."
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"AI error: {e}"


# =============================================================================
# SPECIALIZED RUNNERS
# =============================================================================

def run_finance_agent(message: str, command: str = None, args: str = None) -> str:
    """Run the finance agent with structured input."""
    from core.agent_registry import get_agent
    spec = get_agent("finance")
    if not spec:
        return "Finance agent not found"
    
    return _run_subprocess(spec, message, command, args, "cli")


def run_hakari_agent(message: str, command: str = None, args: str = None) -> str:
    """Run the Hakari/parlay agent."""
    from core.agent_registry import get_agent
    spec = get_agent("hakari")
    if not spec:
        return "Hakari agent not found"
    
    # Map commands to Hakari subcommands
    hakari_cmd = command or "domain"
    cmd_args = f"--{hakari_cmd}"
    if args:
        cmd_args += f" {args}"
    
    return _run_subprocess(spec, message, command, cmd_args, "cli")


def run_jarvis_agent(target: str, redact: bool = False) -> str:
    """Run Jarvis OSINT agent."""
    from core.agent_registry import get_agent
    spec = get_agent("jarvis")
    if not spec:
        return "Jarvis agent not found"
    
    args = target
    if redact:
        args += " --redact"
    
    return _run_subprocess(spec, f"Investigate {target}", "jarvis", args, "cli")
