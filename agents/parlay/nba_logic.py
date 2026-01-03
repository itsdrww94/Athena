"""
HAKARI CORE: NBA LOGIC ENGINE (v2.0)
-------------------------------------
The central brain of the Hakari agent. 
Calculates +EV projections using:
- Rate Per Minute (RPM) Base
- Context Multipliers (Ref, Fatigue, Narrative, Incentives)
- Risk Management (Inverse Correlation)

v2.0: Integrated with Decision Engine schemas (ProjectionResult)
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
import logging

# Pure Python normal CDF approximation (avoid scipy import issues)
def _norm_cdf(x, mean=0, std=1):
    """Approximate normal CDF using error function approximation."""
    z = (x - mean) / std
    # Abramowitz and Stegun approximation
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if z >= 0 else -1
    z = abs(z) / math.sqrt(2)
    t = 1.0 / (1.0 + p * z)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-z * z)
    return 0.5 * (1.0 + sign * y)


# IMPORT HAKARI MODULES
try:
    from factors.ref_factor import RefereeModule
    from factors.fatigue_factor import FatigueModule
    from factors.matchup_factor import MatchupFactor
    from nba_context import IncentiveModule, SeriesContextModule
    from schemas import ProjectionResult, PropState
except ImportError:
    # Fallback for relative imports if run as script
    from .factors.ref_factor import RefereeModule
    from .factors.fatigue_factor import FatigueModule
    from .factors.matchup_factor import MatchupFactor
    from .nba_context import IncentiveModule, SeriesContextModule
    from .schemas import ProjectionResult, PropState

# Initialize Modules
ref_engine = RefereeModule()
fatigue_engine = FatigueModule()
incentive_engine = IncentiveModule()
series_engine = SeriesContextModule()
matchup_engine = MatchupFactor()

logger = logging.getLogger("Hakari.Core")

# --- PLACEHOLDER DATA STRUCTURES ---
# In production, these map to NBA_API calls or static files
RANKING_CACHE = {}

# Stanford CS229: Dampen "Hot Hand" bias - season stability > recent noise
BASE_PROJECTION_WEIGHTS = {
    'season': 0.60,  # Increased from 0.40 - research shows streaks are noise
    'l10': 0.15,     # Decreased from 0.35 - recent form overweighted
    'usage_adj': 0.25
}

# --- DECISION ENGINE THRESHOLDS (Tunable) ---
DECISION_THRESHOLDS = {
    'min_edge_prob': 0.06,       # Need P(best_side) > 0.50 + this value
    'min_confidence': 0.45,      # Minimum confidence to bet
    'sigma_floor': 0.75,         # Minimum sigma to prevent over-confidence
    'sample_n_min': 5,           # Minimum sample size for reliable estimates
    'risk_penalty_per_tag': 0.05 # Penalty to value_score per risk tag
}

# --- STAT-SPECIFIC SIGMA RANGES (Clamps) ---
SIGMA_CLAMPS = {
    'points': (2.0, 12.0),
    'rebounds': (1.0, 5.0),
    'assists': (1.0, 5.0),
    '3pm': (0.5, 3.0),
    'steals': (0.3, 1.5),
    'blocks': (0.3, 1.5),
    'default': (1.0, 8.0)
}

class UniversalPlayerProjection:
    """
    Calculates NBA player props based on context, not just averages.
    Integrates RPM, Referees, Fatigue, and Narratives.
    """
    def __init__(self, player_stats, game_context, team_status):
        self.player_stats = player_stats
        self.game_context = game_context # Includes crew_names, is_home, etc.
        self.team_status = team_status
        self.archetype = self._determine_archetype()
        
        # Base Data for RPM
        self.avg_minutes = player_stats.get('avg_minutes', 0)
        self.proj_minutes = self.avg_minutes # Mutable projection
        
        # Modules
        self.game_script_mods = {}

    def _determine_archetype(self):
        usage = self.player_stats.get('usage_rate', 0)
        pts = self.player_stats.get('avg_points', 0)
        reb = self.player_stats.get('avg_rebounds', 0)
        pos = self.player_stats.get('position', '')

        if usage > 0.30 or pts > 24: return "ALPHA"
        elif 0.24 <= usage <= 0.30: return "BETA"
        elif 'C' in pos or reb > 9: return "BIG"
        else: return "ROLE_PLAYER"

    def _apply_minute_adjustments(self):
        """
        Module Z: Minute Adjustments (Pre-RPM)
        Applies changes to projected minutes based on Series Context (3-0 Trap).
        """
        series_lead = self.game_context.get('series_status', '')
        # Determine location (Home/Away)
        is_home = self.game_context.get('is_home', True)
        location = "HOME" if is_home else "AWAY"
        
        # Apply Series Context (3-0 Road Trap)
        mult = series_engine.get_minutes_adjustment(series_lead, location, self.archetype)
        if mult != 1.0:
            self.proj_minutes *= mult
            reason = "3-0 Trap" if mult < 1.0 else "Garbage Time"
            logger.info(f"Minute Adjust: {reason} -> {self.proj_minutes:.1f} min ({mult}x)")

    def _calculate_rpm_base(self, stat_type):
        """
        Module A: Rate Per Minute (RPM) Calculation.
        Formula: (AvgStat / AvgMin) * ProjMinutes
        """
        avg_stat = self.player_stats.get(f'avg_{stat_type}', 0)
        if self.avg_minutes <= 0: return 0
        
        rpm = avg_stat / self.avg_minutes
        
        # Hard Cap for Role Players (Anti-Hallucination)
        if self.archetype == "ROLE_PLAYER" and self.proj_minutes > 28:
            self.proj_minutes = 28.0
            
        return rpm * self.proj_minutes

    def _apply_vacuum_adjustment(self, projection, stat_type):
        """Module B: Injury Redistribution (Vacuum)"""
        # Logic: If Alpha is OUT, Beta/Role players get Usage Bump
        if self.team_status.get('is_alpha_out'):
            if self.archetype == "BETA" and stat_type == 'points':
                projection *= 1.22
            elif self.archetype == "ROLE_PLAYER" and stat_type == 'points':
                projection *= 1.12
            elif self.archetype == "BIG":
                if stat_type == 'points': projection *= 0.95
                elif stat_type == 'rebounds': projection *= 1.08
        return projection

    def _apply_fatigue_adjustment(self, projection):
        """
        Module C: Veteran Fatigue (Imported Logic)
        """
        age = self.player_stats.get('age', 28)
        rest = self.game_context.get('days_rest', 1)
        is_road = not self.game_context.get('is_home', True)
        
        mult = fatigue_engine.get_fatigue_multiplier(age, rest, is_road)
        return projection * mult

    def _apply_ref_adjustment(self, projection, stat_type):
        """
        Module E: Referee Impact (Imported Logic)
        """
        crew = self.game_context.get('crew_names', [])
        # Simple style classifier
        style = "NEUTRAL"
        if self.archetype == "ALPHA" and stat_type == 'points': style = "FT_DEPENDENT"
        
        mult = ref_engine.get_ref_multiplier(crew, stat_type, style)
        return projection * mult

    def _apply_narrative_adjustments(self, projection, stat_type):
        """
        Module F: The Narrative Engine (D-Lo Effect & Playoff Trap)
        """
        # 1. The D-Lo Effect (Trade Rumor Spike)
        sentiment_score = self.game_context.get('trade_rumor_intensity', 0) 
        if sentiment_score > 7.0 and stat_type in ['points', '3pm']:
             projection *= 1.10 # +10% Pride Multiplier

        # 2. The 3-0 Road Trap (Narrative Multiplier - Redundant with Minutes but kept for sentiment effect if needed)
        # Note: We handled minutes in _apply_minute_adjustments. 
        # Here we can add a slight psychological fade if desired, but for now we rely on minutes.
        pass # Minute adjustment handles the heavy lifting
        
        return projection

    def _apply_incentive_adjustment(self, projection, stat_type):
        """
        Module G: Incentive Engine (Bag Watch)
        """
        pid = self.player_stats.get('id')
        mult = incentive_engine.calculate_greed_multiplier(pid, stat_type)
        return projection * mult

    def _apply_chaos_adjustment(self, projection, stat_type):
        """
        Stanford CS229 Module: Chaos Factor (Orchestrated by MatchupFactor)
        """
        opp_stats = self.game_context.get('opponent_stats', {})
        return projection * matchup_engine.get_chaos_multiplier(stat_type, opp_stats)

    def _apply_glass_eater_logic(self, projection, stat_type):
        """
        Stanford CS229 Module: Glass Eater Logic (Orchestrated by MatchupFactor)
        """
        opp_stats = self.game_context.get('opponent_stats', {})
        return projection * matchup_engine.get_glass_eater_multiplier(stat_type, opp_stats)

    def get_final_projection(self, stat_type='points'):
        """
        Master Pipeline (Legacy - returns raw value)
        """
        # 0. Adjust Minutes First
        self._apply_minute_adjustments()

        # 1. Base RPM
        base_proj = self._calculate_rpm_base(stat_type)
        
        # 2. Vacuum (Injury)
        proj = self._apply_vacuum_adjustment(base_proj, stat_type)
        
        # 3. Fatigue (Vet Fade)
        proj = self._apply_fatigue_adjustment(proj)
        
        # 4. Referees
        proj = self._apply_ref_adjustment(proj, stat_type)
        
        # 5. Narrative (D-Lo / Playoffs)
        proj = self._apply_narrative_adjustments(proj, stat_type)
        
        # 6. Incentives (Bag Watch)
        proj = self._apply_incentive_adjustment(proj, stat_type)
        
        # --- STANFORD CS229 UPGRADES ---
        proj = self._apply_chaos_adjustment(proj, stat_type)
        proj = self._apply_glass_eater_logic(proj, stat_type)
        
        return round(max(0, proj), 2)

    def get_full_projection(self, stat_type='points', line=None) -> ProjectionResult:
        """
        Full Decision Engine Pipeline - Returns ProjectionResult with uncertainty.
        
        This is the v2.0 entry point that integrates with the policy layer.
        
        Args:
            stat_type: 'points', 'rebounds', 'assists', '3pm', etc.
            line: PrizePicks line (for probability calculation)
        
        Returns:
            ProjectionResult with mean, stdev, P(over), P(under), confidence, etc.
        """
        # Build explanation trace
        explanation = {}
        
        # 0. Adjust Minutes First
        self._apply_minute_adjustments()
        explanation['proj_minutes'] = self.proj_minutes

        # 1. Base RPM
        base_proj = self._calculate_rpm_base(stat_type)
        explanation['rpm_base'] = round(base_proj, 2)
        
        # 2. Vacuum (Injury)
        proj = self._apply_vacuum_adjustment(base_proj, stat_type)
        if proj != base_proj:
            explanation['vacuum_adjust'] = {
                'mult': round(proj / base_proj, 3) if base_proj else 1.0,
                'reason': 'Alpha OUT' if self.team_status.get('is_alpha_out') else 'N/A'
            }
        
        # 3. Fatigue (Vet Fade)
        pre_fatigue = proj
        proj = self._apply_fatigue_adjustment(proj)
        if proj != pre_fatigue:
            age = self.player_stats.get('age', 28)
            rest = self.game_context.get('days_rest', 1)
            explanation['fatigue_adjust'] = {
                'mult': round(proj / pre_fatigue, 3),
                'reason': f'Age {age}, {rest} days rest'
            }
        
        # 4. Referees
        pre_ref = proj
        proj = self._apply_ref_adjustment(proj, stat_type)
        if proj != pre_ref:
            crew = self.game_context.get('crew_names', [])
            explanation['ref_adjust'] = {
                'mult': round(proj / pre_ref, 3),
                'reason': f'Crew: {", ".join(crew[:2])}...' if crew else 'N/A'
            }
        
        # 5. Narrative (D-Lo / Playoffs)
        pre_narr = proj
        proj = self._apply_narrative_adjustments(proj, stat_type)
        if proj != pre_narr:
            explanation['narrative_adjust'] = {
                'mult': round(proj / pre_narr, 3),
                'reason': 'Trade rumor / narrative'
            }
        
        # 6. Incentives (Bag Watch)
        pre_inc = proj
        proj = self._apply_incentive_adjustment(proj, stat_type)
        if proj != pre_inc:
            explanation['incentive_adjust'] = {
                'mult': round(proj / pre_inc, 3),
                'reason': 'Contract incentive chase'
            }
        
        # Final projection
        mean = round(max(0, proj), 2)
        explanation['final_projection'] = mean
        
        # Calculate standard deviation (from player stats or estimate)
        stdev = self.player_stats.get(f'{stat_type}_stdev', mean * 0.25)  # Default 25% CV
        stdev = max(0.5, stdev)  # Floor at 0.5
        
        # Calculate probabilities if line provided
        if line is not None and stdev > 0:
            z_score = (mean - line) / stdev
            p_under = _norm_cdf(line, mean=mean, std=stdev)
            p_over = 1 - p_under
        else:
            z_score = 0.0
            p_over = 0.50
            p_under = 0.50
        
        # Confidence calculation (based on data quality and context)
        base_confidence = 0.65
        # Reduce confidence for B2B
        if self.game_context.get('days_rest', 1) == 0:
            base_confidence -= 0.05
        # Reduce confidence for role players
        if self.archetype == 'ROLE_PLAYER':
            base_confidence -= 0.05
        # Boost confidence for Alphas
        if self.archetype == 'ALPHA':
            base_confidence += 0.05
        
        confidence = max(0.40, min(0.85, base_confidence))
        
        # Risk tags
        risk_tags = []
        if self.game_context.get('days_rest', 1) == 0:
            age = self.player_stats.get('age', 28)
            if age >= 33:
                risk_tags.append('VET_B2B')
        if self.team_status.get('is_alpha_out'):
            risk_tags.append('TEAM_INJURY_CONTEXT')
        if self.game_context.get('blowout_risk'):
            risk_tags.append('BLOWOUT_RISK')
        
        risk_score = len(risk_tags) * 0.15
        
        return ProjectionResult(
            mean=mean,
            stdev=round(stdev, 2),
            p_over=round(p_over, 4),
            p_under=round(p_under, 4),
            z_score=round(z_score, 3),
            confidence=round(confidence, 3),
            confidence_breakdown={'base': base_confidence, 'archetype': self.archetype},
            risk_tags=risk_tags,
            risk_score=round(risk_score, 3),
            explanation=explanation
        )


# --- HELPERS ---

def validate_parlay_coherence(picks, detailed=False):
    """
    Prevents cannibalization and scores correlation.
    
    Enhanced with correlation penalties/bonuses:
    - same-team points OVER + another primary scorer points OVER = penalty
    - multiple legs with "MINUTES_VOLATILE" tag = penalty
    - "PACE_UP" / "CLOSE_GAME" tags = small bonus
    
    Returns:
        (coherent: bool, message: str) - legacy format
        OR if detailed=True:
        {coherent: bool, message: str, correlation_score: float, violations: list}
    """
    violations = []
    correlation_score = 1.0  # Start neutral
    
    rebound_overs = [p for p in picks if p.get('stat') in ['rebounds', 'REB'] and p.get('direction') == 'more']
    points_overs = [p for p in picks if p.get('stat') in ['points', 'PTS'] and p.get('direction') == 'more']
    
    # Check if > 2 rebound overs from SAME TEAM
    reb_teams = [p.get('team_id') for p in rebound_overs]
    if len(rebound_overs) > 2 and len(set(reb_teams)) == 1:
        violations.append("TOO_MANY_TEAMMATE_REB_OVERS")
        correlation_score -= 0.15
    
    # Check same-team points OVERs (cannibalization)
    pts_teams = [p.get('team_id') for p in points_overs]
    for team in set(pts_teams):
        team_pts_count = pts_teams.count(team)
        if team_pts_count >= 2:
            violations.append(f"SAME_TEAM_PTS_OVERS_{team}")
            correlation_score -= 0.10 * (team_pts_count - 1)
    
    # Check for multiple MINUTES_VOLATILE legs
    volatile_count = sum(1 for p in picks if 'MINUTES_VOLATILE' in p.get('risk_tags', []))
    if volatile_count >= 2:
        violations.append("MULTIPLE_VOLATILE_MINUTES")
        correlation_score -= 0.08 * volatile_count
    
    # Bonuses (if context tags present)
    pace_up_count = sum(1 for p in picks if 'PACE_UP' in p.get('context_tags', []))
    if pace_up_count >= 2:
        correlation_score += 0.05
    
    coherent = len(violations) == 0 or correlation_score > 0.7
    message = "✅ Coherent Parlay" if coherent else f"⚠️ Correlation Issues: {', '.join(violations)}"
    
    if detailed:
        return {
            'coherent': coherent,
            'message': message,
            'correlation_score': round(max(0, correlation_score), 3),
            'violations': violations
        }
    return coherent, message


# =============================================================================
# PHASE 1 HELPER FUNCTIONS
# =============================================================================

def estimate_distribution_from_logs(logs, stat_type):
    """
    Estimate distribution parameters from player game logs.
    
    Uses per-minute rate decomposition for better variance estimation:
    - rate_i = stat_i / minutes_i
    - Approximate variance: var ≈ (μ_min² * σ_rate²) + (μ_rate² * σ_min²) + (σ_rate² * σ_min²)
    
    Returns:
        {
            'mu_rate': float, 'sigma_rate': float,
            'mu_min': float, 'sigma_min': float,
            'mu_stat': float, 'sigma_stat': float,
            'sample_n': int,
            'quality_flags': list[str]
        }
    """
    quality_flags = []
    
    # Stat key mapping
    stat_key_map = {
        'points': 'pts', 'rebounds': 'reb', 'assists': 'ast',
        '3pm': '3pm', 'steals': 'stl', 'blocks': 'blk'
    }
    stat_key = stat_key_map.get(stat_type.lower(), stat_type.lower())
    
    if not logs:
        quality_flags.append('NO_DATA')
        return {
            'mu_rate': 0, 'sigma_rate': 1, 'mu_min': 30, 'sigma_min': 5,
            'mu_stat': 0, 'sigma_stat': 5, 'sample_n': 0, 'quality_flags': quality_flags
        }
    
    sample_n = len(logs)
    if sample_n < DECISION_THRESHOLDS['sample_n_min']:
        quality_flags.append('LOW_SAMPLE')
    
    # Extract stat values and minutes
    stat_vals = []
    min_vals = []
    rates = []
    
    for g in logs:
        stat_val = g.get(stat_key, g.get('pts', 0))  # Fallback to pts
        minutes = g.get('min', 0)
        
        # Handle string minutes (e.g., "32:15")
        if isinstance(minutes, str):
            try:
                parts = minutes.split(':')
                minutes = float(parts[0]) + float(parts[1]) / 60 if len(parts) == 2 else float(parts[0])
            except:
                minutes = 0
        
        stat_vals.append(float(stat_val) if stat_val else 0)
        min_vals.append(float(minutes) if minutes else 0)
        
        # Calculate per-minute rate (guard against low minutes)
        if minutes and float(minutes) > 5:
            rates.append(float(stat_val) / float(minutes))
    
    # Calculate statistics
    mu_stat = np.mean(stat_vals) if stat_vals else 0
    sigma_stat = np.std(stat_vals, ddof=1) if len(stat_vals) > 1 else mu_stat * 0.25
    
    mu_min = np.mean(min_vals) if min_vals else 30
    sigma_min = np.std(min_vals, ddof=1) if len(min_vals) > 1 else 5
    
    mu_rate = np.mean(rates) if rates else (mu_stat / mu_min if mu_min > 0 else 0)
    sigma_rate = np.std(rates, ddof=1) if len(rates) > 1 else mu_rate * 0.25
    
    # Check for minutes volatility
    if sigma_min > 8 or (mu_min > 0 and sigma_min / mu_min > 0.25):
        quality_flags.append('MINUTES_VOLATILE')
    
    # Approximate combined variance using delta method
    combined_var = (mu_min**2 * sigma_rate**2) + (mu_rate**2 * sigma_min**2) + (sigma_rate**2 * sigma_min**2)
    sigma_combined = math.sqrt(combined_var) if combined_var > 0 else sigma_stat
    
    # Apply sigma floor and clamps
    clamp_range = SIGMA_CLAMPS.get(stat_type.lower(), SIGMA_CLAMPS['default'])
    sigma_combined = max(DECISION_THRESHOLDS['sigma_floor'], sigma_combined)
    sigma_combined = max(clamp_range[0], min(clamp_range[1], sigma_combined))
    
    return {
        'mu_rate': round(mu_rate, 4),
        'sigma_rate': round(sigma_rate, 4),
        'mu_min': round(mu_min, 2),
        'sigma_min': round(sigma_min, 2),
        'mu_stat': round(mu_stat, 2),
        'sigma_stat': round(sigma_combined, 2),
        'sample_n': sample_n,
        'quality_flags': quality_flags
    }


def prob_over_normal(mu, sigma, line):
    """Calculate probability of hitting OVER using normal CDF."""
    if sigma <= 0:
        return 1.0 if mu > line else 0.0
    return 1.0 - _norm_cdf(line, mean=mu, std=sigma)


def compute_confidence(sample_n, sigma, mu, quality_flags=None):
    """
    Compute confidence score (0..1) based on sample size and uncertainty.
    Higher sample_n and lower sigma relative to mu -> higher confidence.
    """
    quality_flags = quality_flags or []
    
    # Base confidence from sample size (diminishing returns)
    sample_conf = min(1.0, sample_n / 15)
    
    # Confidence from variance (lower CV = higher confidence)
    cv = sigma / mu if mu > 0 else 1.0
    variance_conf = max(0.3, 1.0 - cv)
    
    confidence = 0.5 * sample_conf + 0.5 * variance_conf
    
    # Penalties for quality flags
    if 'LOW_SAMPLE' in quality_flags:
        confidence -= 0.10
    if 'MINUTES_VOLATILE' in quality_flags:
        confidence -= 0.08
    if 'MOTIF_LOW_SAMPLE' in quality_flags:
        confidence -= 0.05
    if 'NO_DATA' in quality_flags:
        confidence = 0.0
    
    return round(max(0.0, min(1.0, confidence)), 3)


def risk_tags_from_context(player_stats, game_context, team_status, minutes_sigma, sample_n, quality_flags=None):
    """Generate risk tags based on context and data quality."""
    quality_flags = quality_flags or []
    tags = list(quality_flags)
    
    days_rest = game_context.get('days_rest', 1)
    if days_rest == 0:
        age = player_stats.get('age', 28)
        if age >= 33:
            tags.append('VET_B2B')
        else:
            tags.append('B2B')
    
    if team_status.get('is_alpha_out'):
        tags.append('TEAM_INJURY_VACUUM')
    if game_context.get('injury_return'):
        tags.append('INJURY_RETURN')
    if game_context.get('blowout_risk'):
        tags.append('BLOWOUT_RISK')
    
    if minutes_sigma > 8 and 'MINUTES_VOLATILE' not in tags:
        tags.append('MINUTES_VOLATILE')
    if sample_n < DECISION_THRESHOLDS['sample_n_min'] and 'LOW_SAMPLE' not in tags:
        tags.append('LOW_SAMPLE')
    
    return list(set(tags))


def decide_action(p_over, p_under, confidence, risk_tags, thresholds=None):
    """
    Decide action: OVER, UNDER, or SKIP.
    
    SKIP if:
    - max(p_over, p_under) < 0.50 + min_edge_prob
    - confidence < min_confidence
    - severe risk tags present
    """
    thresholds = thresholds or DECISION_THRESHOLDS
    
    best_side = 'OVER' if p_over >= p_under else 'UNDER'
    best_prob = max(p_over, p_under)
    edge_prob = best_prob - 0.50
    
    risk_penalty = len(risk_tags) * thresholds.get('risk_penalty_per_tag', 0.05)
    value_score = edge_prob * confidence - risk_penalty
    
    severe_tags = {'NO_DATA', 'INJURY_RETURN'}
    has_severe = bool(set(risk_tags) & severe_tags)
    
    skip_reason = None
    action = best_side
    
    if has_severe:
        action = 'SKIP'
        skip_reason = f"Severe risk: {set(risk_tags) & severe_tags}"
    elif best_prob < (0.50 + thresholds['min_edge_prob']):
        action = 'SKIP'
        skip_reason = f"Edge too low: {edge_prob:.1%} < {thresholds['min_edge_prob']:.1%}"
    elif confidence < thresholds['min_confidence']:
        action = 'SKIP'
        skip_reason = f"Confidence too low: {confidence:.1%} < {thresholds['min_confidence']:.1%}"
    elif value_score < 0:
        action = 'SKIP'
        skip_reason = f"Negative value score: {value_score:.3f}"
    
    return {
        'action': action,
        'best_side': best_side,
        'best_prob': round(best_prob, 4),
        'edge_prob': round(edge_prob, 4),
        'skip_reason': skip_reason,
        'value_score': round(value_score, 4),
        'risk_penalty': round(risk_penalty, 4)
    }


def compute_ev_proxy(p_hit, payout_mode="flex", legs=2):
    """
    Compute EV proxy for ranking purposes.
    For single leg: EV_proxy = (2 * p_hit - 1)
    TODO: Plug real PrizePicks payout tables for flex/power modes.
    """
    if legs == 1:
        return round(2 * p_hit - 1, 4)
    else:
        return round(p_hit - 0.50, 4)


def build_backtest_record(player_name, stat_type, line, mu, sigma, p_over, p_under, 
                          action, confidence, value_score, risk_tags, context_overrides=None):
    """Build a backtest record for logging/persistence."""
    return {
        'timestamp': datetime.now().isoformat(),
        'player': player_name,
        'stat_type': stat_type,
        'line': line,
        'mu': mu,
        'sigma': sigma,
        'p_over': p_over,
        'p_under': p_under,
        'action': action,
        'confidence': confidence,
        'value_score': value_score,
        'risk_tags': risk_tags,
        'context_overrides': context_overrides or {},
        'thresholds_used': DECISION_THRESHOLDS.copy()
    }


# =============================================================================
# DATA SERVICE & MAIN ENTRY POINT
# =============================================================================

# Initialize Data Service
try:
    from data_service import NBADataService
except ImportError:
    from .data_service import NBADataService

data_hub = NBADataService()


def get_player_data(player_name, stat_type, line, context_overrides=None):
    """
    UPGRADED Main Entry Point: Uses UniversalPlayerProjection pipeline
    with uncertainty quantification and SKIP-first decision logic.
    
    Args:
        player_name: Player name string
        stat_type: 'points', 'rebounds', 'assists', '3pm', etc.
        line: PrizePicks line (float)
        context_overrides: Optional dict with game context overrides:
            - days_rest, is_home, crew_names, trade_rumor_intensity
            - series_status, team_status.is_alpha_out, injury_return, etc.
    
    Returns:
        dict with LEGACY keys (backward compatible):
            - verdict: "MORE" or "LESS"
            - score: μ (projection mean)
            - diff: μ - line
            - win_prob: max(p_over, p_under)
        AND NEW keys:
            - action: "OVER" | "UNDER" | "SKIP"
            - mu, sigma, p_over, p_under
            - confidence, edge_prob, value_score
            - risk_tags, explain
    """
    context_overrides = context_overrides or {}
    
    # 1. Fetch Logs via NBADataService
    logs = data_hub.fetch_player_logs(player_name)
    if not logs:
        return {
            "error": f"Player {player_name} not found or no logs.",
            "verdict": "LESS", "score": 0, "diff": -float(line), "win_prob": 0.50,
            "action": "SKIP", "skip_reason": "No data available",
            "mu": 0, "sigma": 1, "p_over": 0.5, "p_under": 0.5,
            "confidence": 0, "edge_prob": 0, "value_score": 0,
            "risk_tags": ["NO_DATA"], "explain": ["No player data found"]
        }
    
    # 2. Estimate distribution from logs
    dist = estimate_distribution_from_logs(logs, stat_type)
    quality_flags = dist['quality_flags']
    
    # 3. Build player_stats for UniversalPlayerProjection
    stat_key_map = {'points': 'pts', 'rebounds': 'reb', 'assists': 'ast', '3pm': '3pm'}
    stat_key = stat_key_map.get(stat_type.lower(), stat_type.lower())
    
    # Infer avg_minutes from logs (or context override)
    avg_minutes = dist['mu_min']
    if avg_minutes < 15:  # Likely incomplete data
        # Heuristic: star-ish if high points, else role player
        if dist['mu_stat'] > 15 and stat_type.lower() == 'points':
            avg_minutes = 34
        else:
            avg_minutes = 28
    
    # Infer usage_rate if not available
    usage_rate = context_overrides.get('usage_rate', 0.22)
    if stat_type.lower() == 'points' and dist['mu_stat'] > 20:
        usage_rate = max(usage_rate, 0.28)
    
    player_stats = {
        'name': player_name,
        f'avg_{stat_type}': dist['mu_stat'],
        'avg_minutes': avg_minutes,
        'avg_points': dist['mu_stat'] if stat_type.lower() == 'points' else 0,
        'usage_rate': usage_rate,
        'age': context_overrides.get('age', 27),
        'position': context_overrides.get('position', ''),
    }
    
    # 4. Build game_context with NEUTRAL defaults
    game_context = {
        'days_rest': context_overrides.get('days_rest', 1),
        'is_home': context_overrides.get('is_home', True),
        'crew_names': context_overrides.get('crew_names', []),
        'trade_rumor_intensity': context_overrides.get('trade_rumor_intensity', 0),
        'series_status': context_overrides.get('series_status', ''),
        'blowout_risk': context_overrides.get('blowout_risk', False),
        'injury_return': context_overrides.get('injury_return', False),
        'opponent': context_overrides.get('opponent', None),
    }
    
    # 5. Build team_status
    team_status = {
        'is_alpha_out': context_overrides.get('is_alpha_out', False),
    }
    
    # 6. Create projection using UniversalPlayerProjection
    proj = UniversalPlayerProjection(player_stats, game_context, team_status)
    mu = proj.get_final_projection(stat_type)
    
    # 7. Use distribution sigma for probability calculation
    sigma = dist['sigma_stat']
    
    # 8. Calculate probabilities (Projection Opinion)
    p_over = prob_over_normal(mu, sigma, float(line))
    p_under = 1.0 - p_over

    # =========================================================================
    # DISAGREEMENT DETECTOR (Projection vs Motif)
    # =========================================================================
    disagreement_score = 0.0
    motif_opinion = None
    
    try:
        from motif_engine import get_motif_engine
        motif_eng = get_motif_engine()
        # Check vs Team Motif
        opp_id = game_context.get('opponent_id') or context_overrides.get('opponent_id')
        if opp_id:
            motif = motif_eng.get_vs_team_motif(logs, opp_id, stat_type, dist['mu_stat'])
            if motif.confidence > 0.5:
                # Naive probability from motif value (assuming same sigma)
                p_over_motif = prob_over_normal(motif.blended, sigma, float(line))
                diff = abs(p_over - p_over_motif)
                
                if diff > DECISION_THRESHOLDS.get('probability_diff_trigger', 0.12):
                    disagreement_score = diff
                    motif_opinion = f"Motif {motif.blended:.1f} ({p_over_motif:.1%})"
    except ImportError:
        pass

    # 9. Compute confidence
    confidence = compute_confidence(dist['sample_n'], sigma, mu, quality_flags)
    
    # Apply disagreement penalty
    if disagreement_score > 0:
        penalty = DECISION_THRESHOLDS.get('confidence_penalty', 0.15)
        confidence = max(0.0, confidence - penalty)
        quality_flags.append('MOTIF_DISAGREEMENT')

    # 10. Generate risk tags
    risk_tags = risk_tags_from_context(
        player_stats, game_context, team_status, 
        dist['sigma_min'], dist['sample_n'], quality_flags
    )
    
    # 11. Decide action (SKIP-first policy)
    decision = decide_action(p_over, p_under, confidence, risk_tags)
    
    # 12. Build Dual Explanations
    explain_human = []
    explain_machine = {
        "reason_codes": [],
        "feature_snapshot": {
            "mu": mu, "sigma": sigma, "line": line, 
            "disagreement": disagreement_score
        },
        "thresholds_used": DECISION_THRESHOLDS.copy()
    }
    
    if decision['action'] == 'SKIP':
        explain_human.append(f"SKIP due to {decision['skip_reason']}")
        explain_machine['reason_codes'].append("SKIP_TRIGGERED")
    else:
        explain_human.append(f"{decision['action']} {stat_type} vs line {line}")
        explain_human.append(f"Proj: {mu:.1f} (Limit: {line}) | Conf: {confidence:.0%}")
        explain_machine['reason_codes'].append("VALUE_FOUND")
    
    if risk_tags:
        explain_human.append(f"Risks: {', '.join(risk_tags)}")
        explain_machine['reason_codes'].extend(risk_tags)
        
    if motif_opinion:
        explain_human.append(f"Disagreement Warning: {motif_opinion}")
        explain_machine['reason_codes'].append("MOTIF_DISAGREEMENT")

    # 13. Compute EV proxy
    ev_proxy = compute_ev_proxy(decision['best_prob'], legs=1)
    
    # LEGACY keys (backward compatible)
    verdict = "MORE" if p_over >= p_under else "LESS"
    
    return {
        # Legacy keys
        "verdict": verdict,
        "score": round(mu, 1),
        "diff": round(mu - float(line), 1),
        "win_prob": round(decision['best_prob'], 4),
        
        # New keys
        "action": decision['action'],
        "mu": round(mu, 2),
        "sigma": round(sigma, 2),
        "p_over": round(p_over, 4),
        "p_under": round(p_under, 4),
        "confidence": round(confidence, 3),
        "edge_prob": round(decision['edge_prob'], 4),
        "value_score": round(decision['value_score'], 4),
        "risk_tags": risk_tags,
        "explain": explain_human,
        "explain_human": explain_human,
        "explain_machine": explain_machine,
        "skip_reason": decision.get('skip_reason'),
        "ev_proxy": ev_proxy,
        "sample_n": dist['sample_n'],
        "disagreement_score": round(disagreement_score, 4)
    }

