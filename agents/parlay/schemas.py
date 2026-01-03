"""
HAKARI DECISION ENGINE: Core Data Schemas
==========================================
Phase 1 Implementation - Type-safe contracts for all layers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


# =============================================================================
# FEATURE VECTOR: Everything the policy layer sees
# =============================================================================

@dataclass
class PropState:
    """Complete feature vector for policy decision-making."""
    
    # Player Identity
    player_id: str
    player_name: str
    team_id: str
    position: str
    age: int
    
    # Stat Context
    stat_type: str              # points, rebounds, assists, 3pm, etc.
    line: float                 # PrizePicks line
    
    # Baseline Stats
    season_avg: float
    l10_avg: float
    l5_avg: float
    home_away_avg: float
    
    # Volatility
    season_stdev: float
    l10_stdev: float
    cv: float                   # Coefficient of variation
    
    # Game Context
    opponent_id: str
    opponent_def_rank: int      # 1-30 (1 = best defense)
    home_game: bool
    spread: float
    total: float
    team_implied_total: float
    
    # Fatigue Context
    days_rest: int
    is_b2b: bool
    games_last_7: int
    travel_km: float = 0.0
    
    # Injury Context
    player_status: str = "HEALTHY"  # HEALTHY, QUESTIONABLE, GTD, OUT
    minutes_restriction: Optional[float] = None
    teammate_injuries: List[str] = field(default_factory=list)
    
    # Referee Context
    crew_names: List[str] = field(default_factory=list)
    whistle_index: float = 5.0
    
    # Motif Features (blended with priors)
    motif_vs_team: float = 0.0
    motif_rest_context: float = 0.0
    motif_injury_return: Optional[int] = None  # Games since return
    motif_usage_shift: float = 0.0
    
    # Series Context (Playoffs)
    series_lead: Optional[str] = None
    playoff_round: Optional[int] = None
    
    # Incentive Context
    has_incentive: bool = False
    incentive_multiplier: float = 1.0
    
    # Timestamps
    snapshot_time_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# PROJECTION LAYER OUTPUT
# =============================================================================

@dataclass
class ProjectionResult:
    """Output of the projection layer with full uncertainty quantification."""
    
    # Core Projections
    mean: float                     # μ - central projection
    stdev: float                    # σ - projected volatility
    p_over: float                   # P(stat > line)
    p_under: float                  # P(stat < line)
    z_score: float                  # (mean - line) / stdev
    
    # Confidence
    confidence: float               # 0-1 meta-confidence
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Risk Assessment
    risk_tags: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    
    # Explanation Trace (adjustments applied)
    explanation: Dict = field(default_factory=dict)
    # Example structure:
    # {
    #   'rpm_base': 24.5,
    #   'def_adjust': {'mult': 0.92, 'reason': 'vs BOS (Rank 3)'},
    #   'fatigue_adjust': {'mult': 0.88, 'reason': 'Age 38 B2B'},
    #   ...
    # }


# =============================================================================
# MARKET LAYER: Line and baseline information
# =============================================================================

@dataclass
class MarketSnapshot:
    """Market state at decision time."""
    
    # Current Line
    line: float
    line_timestamp_utc: str
    
    # Line Movement (if tracking)
    opening_line: Optional[float] = None
    line_movement: Optional[float] = None   # current - opening
    movement_direction: Optional[str] = None  # 'UP', 'DOWN', 'STABLE'
    
    # Implied Baseline
    implied_baseline: float = 0.50
    baseline_method: str = "default_50"     # 'empirical_bucket', 'default_50'
    
    # Payout Structure
    payout_type: str = "POWER"              # 'FLEX' or 'POWER'
    leg_count: int = 1
    payout_multiplier: float = 1.0
    
    # Juice Estimate
    estimated_vig: float = 0.10             # ~10% for PrizePicks


# =============================================================================
# POLICY LAYER: Decision output
# =============================================================================

@dataclass
class PickDecision:
    """Output of the policy layer - the final decision."""
    
    # Decision
    action: str                     # 'OVER', 'UNDER', 'SKIP'
    
    # Edge Metrics
    edge_raw: float                 # μ - line
    edge_pct: float                 # (μ - line) / line * 100
    prob_residual: float            # P(over) - implied_baseline
    
    # Confidence
    confidence: float               # Inherited from ProjectionResult
    adjusted_confidence: float      # After line movement penalty
    
    # Risk
    risk_flags: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    skip_reason: Optional[str] = None
    
    # Ranking
    ev_estimate: float = 0.0        # prob_win * payout - 1
    kelly_fraction: float = 0.0     # Recommended bet size
    tier: str = "SKIP"              # 'S', 'A', 'B', 'C', 'SKIP'


# =============================================================================
# PARLAY LAYER: Constructed slip
# =============================================================================

@dataclass
class ParlaySlip:
    """A fully constructed correlation-aware parlay."""
    
    # Legs
    legs: List[PickDecision] = field(default_factory=list)
    leg_count: int = 0
    
    # Correlation
    correlation_score: float = 0.0          # 0-1 (lower = better)
    correlation_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # EV Proxy
    combined_probability: float = 0.0       # Product of p_win (naive)
    adjusted_probability: float = 0.0       # After correlation adjustment
    payout_multiplier: float = 1.0
    ev_estimate: float = 0.0                # adj_prob * payout - 1
    
    # Constraints
    constraints_satisfied: List[str] = field(default_factory=list)
    constraints_violated: List[str] = field(default_factory=list)
    
    # Explanation
    slip_reasoning: str = ""
    
    # Metadata
    slip_type: str = "POWER_3"              # 'FLEX_3', 'POWER_3', etc.
    recommended_stake: float = 0.0          # Kelly-based


# =============================================================================
# BACKTEST LAYER: Audit trail
# =============================================================================

@dataclass
class BacktestRecord:
    """Complete audit trail for reproducible backtesting."""
    
    # Identifiers
    record_id: str
    timestamp_utc: str
    game_date: str
    game_id: str
    
    # The Pick
    player_id: str
    player_name: str
    stat_type: str
    line: float
    decision: str                   # OVER/UNDER/SKIP
    
    # Snapshots (at decision time)
    prop_state: Optional[PropState] = None
    projection_result: Optional[ProjectionResult] = None
    market_snapshot: Optional[MarketSnapshot] = None
    pick_decision: Optional[PickDecision] = None
    
    # Results (filled post-game)
    actual_stat: Optional[float] = None
    actual_minutes: Optional[float] = None
    hit: Optional[bool] = None
    payout: Optional[float] = None  # +profit or -stake
    
    # Context
    game_result: Optional[Dict] = None
    line_at_close: Optional[float] = None
    beat_close: Optional[bool] = None
    
    # Audit
    model_version: str = "2.0.0"
    config_hash: str = ""


# =============================================================================
# MOTIF FEATURE (for Pattern Engine)
# =============================================================================

@dataclass
class MotifFeature:
    """Single motif feature with shrinkage metadata."""
    
    name: str                       # "vs_team_rebounds_l5"
    value: float                    # Observed average
    sample_size: int                # N games
    confidence: float               # min(1.0, n / 10)
    prior: float                    # Season average
    blended: float                  # Shrunk estimate
    
    @staticmethod
    def blend(motif_value: float, prior_value: float, n: int, shrinkage_k: int = 10) -> float:
        """Bayesian shrinkage: blend motif with prior based on sample size."""
        return (motif_value * n + prior_value * shrinkage_k) / (n + shrinkage_k)


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Skip rule thresholds (configurable via config/thresholds.yaml)
DEFAULT_POLICY_CONFIG = {
    'min_edge_pct': 3.0,                # Skip if |edge| < 3%
    'min_confidence': 0.55,             # Skip if confidence < 55%
    'dead_zone_lower': 0.45,            # Skip if P(over) in [0.45, 0.55]
    'dead_zone_upper': 0.55,
    'line_movement_penalty_threshold': 1.5,  # Reduce confidence if line moves > 1.5
    'hard_stop_flags': [
        'GTD_NO_STATUS',
        'BLOWOUT_RISK_HIGH',
        'INJURY_FIRST_GAME_BACK',
        'MINUTES_RESTRICTION_UNKNOWN',
    ],
}

# Motif configuration
DEFAULT_MOTIF_CONFIG = {
    'min_sample_size': 3,
    'shrinkage_k': 10,
    'max_motif_weight': 0.25,           # Cap adjustments at ±25%
}

# Correlation penalties (heuristic V1)
CORRELATION_PENALTIES = {
    'same_team_same_stat': 0.25,
    'same_team_diff_stat': 0.10,
    'pace_stacking': 0.08,
    'minutes_cannibalization': 0.15,
    'star_out_beneficiaries': 0.12,
}

CORRELATION_BONUSES = {
    'inverse_correlation': -0.05,
    'game_diversity': -0.03,
}

# PrizePicks payout tables
POWER_PAYOUTS = {
    2: 3.0,
    3: 5.0,
    4: 10.0,
    5: 20.0,
    6: 25.0,
}

FLEX_PAYOUTS = {
    # (legs, hits): multiplier
    (6, 6): 25.0, (6, 5): 2.0, (6, 4): 0.4,
    (5, 5): 10.0, (5, 4): 1.5, (5, 3): 0.25,
    (4, 4): 5.0,  (4, 3): 1.5,
    (3, 3): 2.25, (3, 2): 1.25,
    (2, 2): 3.0,
}

# Implied baseline buckets (empirical estimates)
PRIZEPICKS_IMPLIED_BASELINE = {
    'points': {
        (0, 15): 0.52,
        (15, 25): 0.50,
        (25, 40): 0.48,
    },
    'rebounds': {
        (0, 6): 0.51,
        (6, 10): 0.50,
        (10, 15): 0.49,
    },
    'assists': {
        (0, 5): 0.51,
        (5, 10): 0.50,
        (10, 15): 0.49,
    },
    '3pm': {
        (0, 2): 0.52,
        (2, 4): 0.50,
        (4, 6): 0.48,
    },
}
