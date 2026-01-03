"""
Athena Core Logging - Structured JSON Logging with Run Context
==============================================================
Provides structured logging with run_id and trace_id for observability.
All logs are output as JSON for easy parsing and aggregation.
"""

import logging
import json
import uuid
import sys
from datetime import datetime
from typing import Optional, Any, Dict
from contextvars import ContextVar

# =============================================================================
# CONTEXT VARIABLES FOR RUN TRACKING
# =============================================================================

run_id_var: ContextVar[str] = ContextVar("run_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
agent_name_var: ContextVar[str] = ContextVar("agent_name", default="")


# =============================================================================
# JSON FORMATTER
# =============================================================================

class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for structured logging.
    
    Includes run_id, trace_id, and optional agent/tool context.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context variables if set
        run_id = run_id_var.get()
        if run_id:
            log_obj["run_id"] = run_id
            
        trace_id = trace_id_var.get()
        if trace_id:
            log_obj["trace_id"] = trace_id
            
        agent_name = agent_name_var.get()
        if agent_name:
            log_obj["agent_name"] = agent_name
        
        # Add extra fields from record
        if hasattr(record, "agent_name") and record.agent_name:
            log_obj["agent_name"] = record.agent_name
        if hasattr(record, "tool_name") and record.tool_name:
            log_obj["tool_name"] = record.tool_name
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms
        if hasattr(record, "tokens_in"):
            log_obj["tokens_in"] = record.tokens_in
        if hasattr(record, "tokens_out"):
            log_obj["tokens_out"] = record.tokens_out
        if hasattr(record, "model"):
            log_obj["model"] = record.model
        if hasattr(record, "interface"):
            log_obj["interface"] = record.interface
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
            
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for console output with colors.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        run_id = run_id_var.get()
        prefix = f"[{run_id}] " if run_id else ""
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"{color}[{timestamp}] {prefix}{record.levelname}: {record.getMessage()}{self.RESET}"


# =============================================================================
# LOGGER FACTORY
# =============================================================================

_loggers: Dict[str, logging.Logger] = {}

def get_logger(name: str, json_output: bool = False) -> logging.Logger:
    """
    Get a configured logger by name.
    
    Args:
        name: Logger name (e.g., "athena.memory", "athena.orchestrator")
        json_output: If True, use JSON formatter; otherwise use console formatter
        
    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Use JSON for production, console for dev
        try:
            from core.settings import is_production
            use_json = is_production() or json_output
        except ImportError:
            use_json = json_output
            
        if use_json:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(ConsoleFormatter())
            
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    
    _loggers[name] = logger
    return logger


# =============================================================================
# RUN CONTEXT MANAGEMENT
# =============================================================================

def new_run_id() -> str:
    """
    Generate a new run_id and set it in context.
    
    Returns:
        The new run_id (8 character hex string)
    """
    rid = uuid.uuid4().hex[:8]
    run_id_var.set(rid)
    return rid


def set_run_id(run_id: str) -> None:
    """Set the current run_id in context."""
    run_id_var.set(run_id)


def get_run_id() -> str:
    """Get the current run_id from context."""
    return run_id_var.get()


def new_trace_id() -> str:
    """Generate a new trace_id and set it in context."""
    tid = uuid.uuid4().hex[:8]
    trace_id_var.set(tid)
    return tid


def set_agent_context(agent_name: str) -> None:
    """Set the current agent name in context for logging."""
    agent_name_var.set(agent_name)


def clear_context() -> None:
    """Clear all context variables."""
    run_id_var.set("")
    trace_id_var.set("")
    agent_name_var.set("")
