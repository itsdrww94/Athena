"""
Athena CLI Integration Layer
============================
This module bridges the legacy athena_cli.py with the new orchestrator.

Usage:
    from core.cli_integration import process_with_orchestrator
    
    # In the main loop:
    response = process_with_orchestrator(user_input, use_new_orchestrator=True)
"""

import os
from typing import Optional

# Feature flag to enable new orchestrator
USE_NEW_ORCHESTRATOR = os.getenv("ATHENA_USE_NEW_ORCHESTRATOR", "0") == "1"


def process_with_orchestrator(
    user_input: str,
    interface: str = "cli",
    user_id: str = "default",
    session_id: Optional[str] = None
) -> Optional[str]:
    """
    Process user input through the new orchestrator.
    
    Args:
        user_input: The user's message
        interface: Source interface
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Response string if handled, None if should fall back to legacy
    """
    if not USE_NEW_ORCHESTRATOR:
        return None
    
    try:
        from core.app import run_athena
        
        response = run_athena(
            input_message=user_input,
            interface=interface,
            user_id=user_id,
            session_id=session_id
        )
        
        return response
        
    except ImportError:
        # New orchestrator not available
        return None
    except Exception as e:
        # Log error but allow fallback
        print(f"[Orchestrator Error: {e}]")
        return None


def should_use_orchestrator() -> bool:
    """Check if new orchestrator should be used."""
    return USE_NEW_ORCHESTRATOR


def enable_orchestrator():
    """Enable the new orchestrator (runtime)."""
    global USE_NEW_ORCHESTRATOR
    USE_NEW_ORCHESTRATOR = True


def disable_orchestrator():
    """Disable the new orchestrator (runtime)."""
    global USE_NEW_ORCHESTRATOR
    USE_NEW_ORCHESTRATOR = False
