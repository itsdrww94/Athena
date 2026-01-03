"""
Athena Telemetry
================
Records agent runs for observability and cost tracking.
"""

from typing import Optional
from datetime import datetime

# Lazy imports
_logger = None
_settings = None

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.telemetry")
    return _logger

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings


def record_agent_run(
    run_id: str,
    agent_name: str,
    status: str = "completed",
    model_used: Optional[str] = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_estimate: float = 0.0,
    latency_ms: int = 0,
    user_id: str = "default",
    session_id: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[int]:
    """
    Record an agent run to the agent_runs table.
    
    Args:
        run_id: Unique run identifier
        agent_name: Name of the agent
        status: 'started', 'completed', or 'failed'
        model_used: AI model used (if any)
        tokens_in: Input tokens consumed
        tokens_out: Output tokens generated
        cost_estimate: Estimated cost in USD
        latency_ms: Request latency in milliseconds
        user_id: User identifier
        session_id: Session identifier
        error_message: Error message if failed
        
    Returns:
        Record ID if successful, None otherwise
    """
    logger = _get_logger()
    settings = _get_settings()
    
    if not settings.is_supabase_configured:
        logger.debug("Supabase not configured, skipping telemetry")
        return None
    
    try:
        import requests
        
        data = {
            "run_id": run_id,
            "user_id": user_id,
            "session_id": session_id or user_id,
            "agent_name": agent_name,
            "model_used": model_used,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_estimate": cost_estimate,
            "latency_ms": latency_ms,
            "status": status,
            "error_message": error_message,
            "metadata_json": {},
        }
        
        if status == "completed" or status == "failed":
            data["ended_at"] = datetime.utcnow().isoformat()
        
        headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        resp = requests.post(
            f"{settings.supabase_url}/rest/v1/agent_runs",
            headers=headers,
            json=data,
            timeout=5
        )
        
        if resp.status_code in [200, 201]:
            result = resp.json()
            return result[0].get("id") if result else None
        else:
            logger.warning(f"Telemetry write failed: {resp.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Telemetry error: {e}")
        return None


def get_daily_cost(user_id: str = "default") -> float:
    """
    Get total estimated cost for today.
    
    Returns:
        Total cost in USD
    """
    settings = _get_settings()
    
    if not settings.is_supabase_configured:
        return 0.0
    
    try:
        import requests
        from datetime import date
        
        today = date.today().isoformat()
        
        headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
        }
        
        resp = requests.get(
            f"{settings.supabase_url}/rest/v1/agent_runs"
            f"?user_id=eq.{user_id}"
            f"&started_at=gte.{today}"
            f"&select=cost_estimate",
            headers=headers,
            timeout=5
        )
        
        if resp.status_code == 200:
            records = resp.json()
            total = sum(r.get("cost_estimate", 0) or 0 for r in records)
            return total
            
    except Exception:
        pass
    
    return 0.0


def check_budget() -> dict:
    """
    Check if daily budget is exceeded.
    
    Returns:
        Dict with 'ok', 'spent', 'limit', and 'remaining' keys
    """
    settings = _get_settings()
    spent = get_daily_cost()
    limit = settings.max_cost_per_day
    
    return {
        "ok": spent < limit,
        "spent": spent,
        "limit": limit,
        "remaining": max(0, limit - spent)
    }
