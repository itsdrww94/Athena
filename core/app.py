"""
Athena Core App - Canonical Entrypoint
======================================
This is THE single entrypoint that all interfaces (CLI, Telegram, API) must call.
It ensures consistent logging, memory handling, and orchestration for every request.
"""

from typing import Optional, Dict, Any
import time

from core.logging import get_logger, new_run_id, set_agent_context, clear_context
from core.settings import get_settings

logger = get_logger("athena.app")


def run_athena(
    input_message: str,
    interface: str = "cli",
    user_id: str = "default",
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Canonical entrypoint for Athena.
    
    All interfaces (CLI, Telegram, API) MUST call this function to ensure:
    - Consistent run_id tracking
    - Memory logging for all interactions
    - Unified orchestration flow
    - Proper error handling
    
    Args:
        input_message: The user's message/command
        interface: Source interface ("cli", "telegram", "api")
        user_id: User identifier
        session_id: Optional session identifier (defaults to user_id if not provided)
        metadata: Optional extra metadata to include in logs
        
    Returns:
        The response string from Athena
    """
    # Generate run_id for this request
    run_id = new_run_id()
    start_time = time.time()
    
    # Default session_id to user_id if not provided
    if session_id is None:
        session_id = user_id
    
    logger.info(
        "Run started",
        extra={
            "interface": interface,
            "user_id": user_id,
            "session_id": session_id,
            "message_len": len(input_message),
            **(metadata or {})
        }
    )
    
    try:
        # Import orchestrator here to avoid circular imports
        from core.orchestrator import handle_message
        
        response = handle_message(
            user_id=user_id,
            session_id=session_id,
            message=input_message,
            interface=interface
        )
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            "Run completed",
            extra={
                "response_len": len(response),
                "latency_ms": round(latency_ms, 2)
            }
        )
        
        return response
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Run failed: {e}",
            extra={
                "error_type": type(e).__name__,
                "latency_ms": round(latency_ms, 2)
            },
            exc_info=True
        )
        
        # Return user-friendly error message
        settings = get_settings()
        if settings.athena_debug:
            return f"Error [{run_id}]: {e}"
        else:
            return f"I encountered an error processing your request. (ref: {run_id})"
    
    finally:
        clear_context()


def run_athena_async(
    input_message: str,
    interface: str = "cli",
    user_id: str = "default",
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Async wrapper for run_athena (for Telegram and other async interfaces).
    
    Currently just calls the sync version, but can be made truly async later.
    """
    # For now, just call sync version
    # TODO: Make orchestrator async-native
    return run_athena(input_message, interface, user_id, session_id, metadata)
