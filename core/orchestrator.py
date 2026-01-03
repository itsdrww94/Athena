"""
Athena Orchestrator
===================
Central orchestration loop that coordinates all message handling.

This is the brain of Athena - every user message flows through here.

Workflow:
1. Log user message to memory
2. Build context (facts, history, semantic matches)
3. Route to appropriate agent
4. Execute agent
5. Log response to memory
6. Return response
"""

from typing import Optional, Dict, Any
import time

# Lazy imports to avoid circular dependencies
_logger = None
_settings = None

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger, set_agent_context
        _logger = get_logger("athena.orchestrator")
    return _logger

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings


def handle_message(
    user_id: str,
    session_id: str,
    message: str,
    interface: str = "cli"
) -> str:
    """
    Central orchestration loop for Athena.
    
    This function coordinates all message handling:
    1. Logs the user message to memory
    2. Builds context from memory (facts, history, semantic)
    3. Routes to the appropriate agent
    4. Executes the agent
    5. Logs the response to memory
    6. Returns the response
    
    All interfaces (CLI, Telegram, API) must funnel through this function
    via core/app.py to ensure consistent behavior.
    
    Args:
        user_id: User identifier
        session_id: Session identifier  
        message: The user's message
        interface: Source interface ('cli', 'telegram', 'api')
        
    Returns:
        Response string from the agent
    """
    logger = _get_logger()
    start_time = time.time()
    
    # Import here to avoid circular imports
    from core.router import route_message, extract_command_args, is_command
    from core.agent_registry import get_agent
    from services.memory.context_builder import build_context
    from agents.runner import run_agent
    
    logger.info(f"Handling message: {message[:100]}...")
    
    # =========================================================================
    # 1. LOG USER MESSAGE
    # =========================================================================
    try:
        from services.memory.client import get_memory
        memory = get_memory()
        
        if memory.is_configured:
            memory.write_event(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=message,
                metadata={"interface": interface}
            )
    except Exception as e:
        logger.warning(f"Failed to log user message: {e}")
        memory = None
    
    # =========================================================================
    # 2. BUILD CONTEXT
    # =========================================================================
    try:
        context = build_context(
            user_id=user_id,
            session_id=session_id,
            query=message,
            include_semantic=not is_command(message)  # Skip semantic for commands
        )
    except Exception as e:
        logger.warning(f"Context build failed: {e}")
        from services.memory.context_builder import ContextPacket
        context = ContextPacket()
    
    # =========================================================================
    # 3. ROUTE TO AGENT
    # =========================================================================
    agent_name = route_message(message, context)
    agent_spec = get_agent(agent_name)
    
    if not agent_spec:
        # Fallback to athena if agent not found
        logger.warning(f"Agent '{agent_name}' not found, using athena")
        agent_spec = get_agent("athena")
    
    from core.logging import set_agent_context
    set_agent_context(agent_name)
    
    # =========================================================================
    # 4. EXECUTE AGENT
    # =========================================================================
    try:
        # Extract command and args if applicable
        command, args = extract_command_args(message)
        
        response = run_agent(
            agent_spec=agent_spec,
            message=message,
            context=context,
            command=command,
            args=args,
            interface=interface
        )
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        response = f"I encountered an error: {str(e)}"
    
    # =========================================================================
    # 5. LOG RESPONSE
    # =========================================================================
    if memory and memory.is_configured:
        try:
            memory.write_event(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=response[:5000],  # Truncate very long responses
                metadata={
                    "interface": interface,
                    "agent": agent_name,
                    "latency_ms": int((time.time() - start_time) * 1000)
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log response: {e}")
    
    # =========================================================================
    # 6. RECORD TELEMETRY
    # =========================================================================
    latency_ms = int((time.time() - start_time) * 1000)
    try:
        from core.telemetry import record_agent_run
        from core.logging import get_run_id
        
        record_agent_run(
            run_id=get_run_id(),
            agent_name=agent_name,
            status="completed",
            latency_ms=latency_ms,
            user_id=user_id,
            session_id=session_id
        )
    except Exception as e:
        logger.debug(f"Telemetry recording failed: {e}")
    
    logger.info(f"Message handled in {latency_ms}ms by {agent_name}")
    
    return response
