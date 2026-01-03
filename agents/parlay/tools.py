"""
HAKARI TOOL REGISTRY
--------------------
Central dictionary of the 12 agentic tools.
"""

from typing import Dict, Any, Callable

# Import Modules
try:
    from . import nba_logic
    from . import nba_context
    from . import parlay_builder
    from . import submission_engine
    from . import ledger
    from .data_service import NBADataService
except ImportError:
    import nba_logic
    import nba_context
    import parlay_builder
    import submission_engine
    import ledger
    from data_service import NBADataService

# Initialize Singletons
_ledger = ledger.get_ledger()
_data = NBADataService()
_builder = parlay_builder.get_parlay_builder()
_submitter = submission_engine.PrizePicksAutomator() if hasattr(submission_engine, 'PrizePicksAutomator') else None

# =============================================================================
# WRAPPER FUNCTIONS (To normalize signatures)
# =============================================================================

def tool_ingest_slip(platform: str, content: str) -> list:
    """Tool 1: Ingest slip image/text."""
    return nba_context.SlipIngester.parse_input(platform, content)

def tool_normalize_stat(stat: str) -> str:
    """Tool 2: Normalize stat name."""
    return nba_context.PropNormalizer.normalize(stat)

def tool_fetch_context(player: str) -> dict:
    """Tool 3: Fetch player logs and context."""
    # This was implicitly part of get_player_data, exposing raw fetch here
    logs = _data.fetch_player_logs(player)
    return {"logs": logs, "count": len(logs) if logs else 0}

def tool_get_projection(player_stats, game_context, team_status) -> dict:
    """Tool 4: Compute Mu and Sigma."""
    # Helper to access UniversalPlayerProjection components
    proj = nba_logic.UniversalPlayerProjection(player_stats, game_context, team_status)
    # This is slightly abstract as get_player_data usually orchestrates this.
    # For the tool registry, we might point to the orchestrator or this granular step.
    # We'll use get_player_data as the main "Analysis" tool that bundles 4-8 usually,
    # but providing granular access here as requested.
    return {"projection_object": proj} 

def tool_calc_probability(mu, sigma, line) -> dict:
    """Tool 5: Calculate Over/Under Probabilities."""
    p_over = nba_logic.prob_over_normal(mu, sigma, line)
    return {"p_over": p_over, "p_under": 1.0 - p_over}

def tool_assess_risk(sample_n, sigma, mu, context) -> dict:
    """Tool 6: Confidence & Risk Tags."""
    # Re-using logic implementation
    flags = nba_logic.risk_tags_from_context({}, context.get('game', {}), context.get('team', {}),  sigma, sample_n)
    conf = nba_logic.compute_confidence(sample_n, sigma, mu, flags)
    return {"confidence": conf, "risk_tags": flags}

# ... Tools 7 (EV) and 8 (Policy) are integrated in get_player_data return values
# We will register them as logical components 

def tool_build_parlay(candidates, legs=3) -> list:
    """Tool 9: Build optimal slips."""
    # candidates must be formatted as required by builder
    return _builder.build_slips(candidates, leg_count=legs)

async def tool_execute_slip(picks, amount, mode="autonomous") -> dict:
    """Tool 10: Execute/Submit slip."""
    if _submitter:
        return await _submitter.submit_slip(picks, amount, mode)
    return {"status": "ERROR", "message": "No submitter engine available"}

def tool_log_ledger(context, decision, result) -> bool:
    """Tool 11: Log to ledger."""
    return _ledger.log_decision(context, decision, result)

def tool_update_rl(current_thresholds) -> dict:
    """Tool 12: Update RL parameters."""
    return _ledger.update_policy_parameters(current_thresholds)


# =============================================================================
# THE REGISTRY
# =============================================================================

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ingest_slip": {
        "call": tool_ingest_slip,
        "desc": "Parse image/text into structured legs."
    },
    "normalize_prop": {
        "call": tool_normalize_stat,
        "desc": "Canonicalize stat names."
    },
    "fetch_context": {
        "call": tool_fetch_context,
        "desc": "Fetch logs and context for a player."
    },
    "compute_projection": {
        "call": tool_get_projection,
        "desc": "Get mu/sigma from stats (Tool 4)."
    },
    "calc_probability": {
        "call": tool_calc_probability,
        "desc": "Get P(over) from mu/sigma (Tool 5)."
    },
    "assess_risk": {
        "call": tool_assess_risk,
        "desc": "Get confidence and risk tags (Tool 6)."
    },
    "score_value": {
        "call": nba_logic.compute_ev_proxy, # Direct map
        "desc": "Get EV proxy (Tool 7)."
    },
    "decide_policy": {
        "call": nba_logic.decide_action, # Direct map
        "desc": "Get OVER/UNDER/SKIP decision (Tool 8)."
    },
    "build_parlay": {
        "call": tool_build_parlay,
        "desc": "Construct optimal slips (Tool 9)."
    },
    "execute_slip": {
        "call": tool_execute_slip,
        "desc": "Submit to prize picks (Tool 10)."
    },
    "log_ledger": {
        "call": tool_log_ledger,
        "desc": "Append to history (Tool 11)."
    },
    "update_rl": {
        "call": tool_update_rl,
        "desc": "Tune parameters based on history (Tool 12)."
    }
}
