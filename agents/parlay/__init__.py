"""
HAKARI: NBA PrizePicks Decision Engine
=======================================
Modular architecture for projection, market analysis, and decision-making.

Core Components:
- schemas: Data models (PropState, ProjectionResult, PickDecision, etc.)
- market_layer: Line tracking and implied baselines
- policy_engine: SKIP-first decision logic
- motif_engine: Pattern recognition with shrinkage
- parlay_builder: Correlation-aware slip construction
- backtest_engine: Walk-forward evaluation

Note: Imports are done lazily to avoid circular import issues.
Import specific modules directly, e.g.:
    from agents.parlay.schemas import ProjectionResult
    from agents.parlay.policy_engine import get_policy_engine
"""

# Only export the lightweight schemas at package level
# Other modules should be imported directly to avoid circular imports

__all__ = [
    # Direct import paths
    'schemas',
    'market_layer', 
    'policy_engine',
    'motif_engine',
    'parlay_builder',
    'backtest_engine',
    'nba_logic',
    'suggestion_engine',
    'data_service',
    'ref_factor',
    'veteran_fade',
    'nba_context',
]

# Explicit import to avoid recursion in lazy loader
from . import nba_logic

def __getattr__(name):
    """Lazy loading to avoid circular imports."""
    if name == 'schemas':
        from . import schemas
        return schemas
    elif name == 'market_layer':
        from . import market_layer
        return market_layer
    elif name == 'policy_engine':
        from . import policy_engine
        return policy_engine
    elif name == 'motif_engine':
        from . import motif_engine
        return motif_engine
    elif name == 'parlay_builder':
        from . import parlay_builder
        return parlay_builder
    elif name == 'backtest_engine':
        from . import backtest_engine
        return backtest_engine
    # elif name == 'nba_logic':
    #     from . import nba_logic
    #     return nba_logic
    elif name == 'suggestion_engine':
        from . import suggestion_engine
        return suggestion_engine
    elif name == 'data_service':
        from . import data_service
        return data_service
    elif name == 'ref_factor':
        from . import ref_factor
        return ref_factor
    elif name == 'veteran_fade':
        from . import veteran_fade
        return veteran_fade
    elif name == 'nba_context':
        from . import nba_context
        return nba_context
    
    raise AttributeError(f"module 'agents.parlay' has no attribute '{name}'")
