"""
HAKARI DECISION ENGINE: Parlay Builder
========================================
Phase 5 Implementation - Correlation-aware slip construction.

Builds optimal parlays by:
- Scoring correlations with heuristic penalties
- Enforcing constraints (max same-team, diversity)
- Ranking combinations by adjusted EV
"""

import logging
from typing import List, Dict, Optional, Tuple
from itertools import combinations
from dataclasses import dataclass

try:
    from .schemas import (
        PickDecision, ParlaySlip, 
        CORRELATION_PENALTIES, CORRELATION_BONUSES,
        POWER_PAYOUTS, FLEX_PAYOUTS
    )
except ImportError:
    from schemas import (
        PickDecision, ParlaySlip,
        CORRELATION_PENALTIES, CORRELATION_BONUSES,
        POWER_PAYOUTS, FLEX_PAYOUTS
    )

logger = logging.getLogger("Hakari.ParlayBuilder")


@dataclass
class LegContext:
    """Context for a single leg (used for correlation scoring)."""
    decision: PickDecision
    player_id: str
    player_name: str
    team_id: str
    game_id: str
    stat_type: str
    action: str  # OVER/UNDER


class ParlayBuilder:
    """
    Constructs correlation-aware parlays from a pool of PickDecisions.
    
    Workflow:
    1. Filter candidates (only OVER/UNDER, min edge)
    2. Generate all valid combinations (2-6 legs)
    3. Score each for correlation
    4. Apply constraints
    5. Rank by adjusted EV
    6. Return top N slips
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'min_edge_for_parlay': 5.0,     # Min edge % to include in parlay
            'min_confidence': 0.55,
            'max_legs': 6,
            'max_same_team': 2,              # Max legs from same team
            'max_same_stat': 3,              # Max legs of same stat type
            'top_n_slips': 3,                # Return top N
            'default_slip_type': 'POWER',
        }
    
    # =========================================================================
    # MAIN ENTRY: BUILD OPTIMAL SLIPS
    # =========================================================================
    
    def build_slips(self, candidates: List[Tuple[PickDecision, Dict]], 
                     leg_count: int = 3,
                     slip_type: str = 'POWER') -> List[ParlaySlip]:
        """
        Build optimal parlay slips from candidate picks.
        
        Args:
            candidates: List of (PickDecision, context_dict) tuples
                context_dict: {'player_id', 'team_id', 'game_id', 'stat_type', 'player_name'}
            leg_count: Target number of legs (2-6)
            slip_type: 'POWER' or 'FLEX'
        
        Returns:
            Top N ParlaySlip objects, ranked by adjusted EV
        """
        # Step 1: Filter to actionable picks
        filtered = []
        for decision, ctx in candidates:
            if decision.action == 'SKIP':
                continue
            if abs(decision.edge_pct) < self.config['min_edge_for_parlay']:
                continue
            if decision.confidence < self.config['min_confidence']:
                continue
            
            leg = LegContext(
                decision=decision,
                player_id=ctx.get('player_id', ''),
                player_name=ctx.get('player_name', 'Unknown'),
                team_id=ctx.get('team_id', ''),
                game_id=ctx.get('game_id', ''),
                stat_type=decision.edge_raw > 0 and ctx.get('stat_type', 'points') or ctx.get('stat_type', 'points'),
                action=decision.action
            )
            filtered.append(leg)
        
        if len(filtered) < leg_count:
            logger.warning(f"Not enough candidates ({len(filtered)}) for {leg_count}-leg parlay")
            return []
        
        # Step 2: Generate all combinations
        all_combos = list(combinations(filtered, leg_count))
        logger.info(f"Evaluating {len(all_combos)} potential {leg_count}-leg combinations")
        
        # Step 3: Score and validate each
        valid_slips = []
        for combo in all_combos:
            legs = list(combo)
            
            # Check constraints
            violations = self._check_constraints(legs)
            if violations:
                continue  # Skip invalid combos
            
            # Score correlation
            corr_score, corr_breakdown = self._calculate_correlation(legs)
            
            # Calculate EV
            payout = POWER_PAYOUTS.get(leg_count, 1.0) if slip_type == 'POWER' else FLEX_PAYOUTS.get((leg_count, leg_count), 1.0)
            combined_prob = 1.0
            for leg in legs:
                p_win = leg.decision.confidence  # Approximation
                combined_prob *= p_win
            
            # Apply correlation penalty to probability
            adjusted_prob = combined_prob * (1 - corr_score * 0.5)  # Partial penalty
            ev_estimate = adjusted_prob * payout - 1.0
            
            # Build slip
            slip = ParlaySlip(
                legs=[leg.decision for leg in legs],
                leg_count=leg_count,
                correlation_score=corr_score,
                correlation_breakdown=corr_breakdown,
                combined_probability=combined_prob,
                adjusted_probability=adjusted_prob,
                payout_multiplier=payout,
                ev_estimate=ev_estimate,
                constraints_satisfied=self._get_satisfied_constraints(legs),
                constraints_violated=[],
                slip_reasoning=self._build_reasoning(legs, corr_score, ev_estimate),
                slip_type=f"{slip_type}_{leg_count}",
                recommended_stake=self._calculate_recommended_stake(ev_estimate, adjusted_prob)
            )
            valid_slips.append(slip)
        
        # Step 4: Rank by EV
        valid_slips.sort(key=lambda s: s.ev_estimate, reverse=True)
        
        top_n = self.config['top_n_slips']
        logger.info(f"Returning top {min(top_n, len(valid_slips))} slips from {len(valid_slips)} valid")
        
        return valid_slips[:top_n]
    
    # =========================================================================
    # CORRELATION SCORING
    # =========================================================================
    
    def _calculate_correlation(self, legs: List[LegContext]) -> Tuple[float, Dict]:
        """
        Calculate correlation score using heuristic penalties.
        
        Returns:
            (score 0-1, breakdown dict)
        """
        score = 0.0
        breakdown = {}
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                pair_key = f"{leg1.player_name} vs {leg2.player_name}"
                pair_penalties = []
                
                # Same team + same stat (worst)
                if leg1.team_id == leg2.team_id and leg1.stat_type == leg2.stat_type:
                    penalty = CORRELATION_PENALTIES['same_team_same_stat']
                    score += penalty
                    pair_penalties.append(('same_team_same_stat', penalty))
                
                # Same team + different stat
                elif leg1.team_id == leg2.team_id:
                    penalty = CORRELATION_PENALTIES['same_team_diff_stat']
                    score += penalty
                    pair_penalties.append(('same_team_diff_stat', penalty))
                
                # Same game (potential pace stacking)
                if leg1.game_id == leg2.game_id and leg1.team_id != leg2.team_id:
                    penalty = CORRELATION_PENALTIES['pace_stacking']
                    score += penalty
                    pair_penalties.append(('pace_stacking', penalty))
                
                # Inverse correlation bonus (opposing teams)
                if leg1.game_id == leg2.game_id and leg1.team_id != leg2.team_id:
                    if (leg1.action == 'OVER' and leg2.action == 'UNDER') or \
                       (leg1.action == 'UNDER' and leg2.action == 'OVER'):
                        bonus = CORRELATION_BONUSES['inverse_correlation']
                        score += bonus  # bonus is negative
                        pair_penalties.append(('inverse_correlation', bonus))
                
                # Different games bonus
                if leg1.game_id != leg2.game_id:
                    bonus = CORRELATION_BONUSES['game_diversity']
                    score += bonus
                    pair_penalties.append(('game_diversity', bonus))
                
                if pair_penalties:
                    breakdown[pair_key] = pair_penalties
        
        # Clamp to 0-1
        score = max(0.0, min(1.0, score))
        
        return score, breakdown
    
    # =========================================================================
    # CONSTRAINT VALIDATION
    # =========================================================================
    
    def _check_constraints(self, legs: List[LegContext]) -> List[str]:
        """Check if combination violates any constraints."""
        violations = []
        
        # Max same team
        team_counts = {}
        for leg in legs:
            team_counts[leg.team_id] = team_counts.get(leg.team_id, 0) + 1
        
        max_team = max(team_counts.values()) if team_counts else 0
        if max_team > self.config['max_same_team']:
            violations.append(f"Too many from same team: {max_team}")
        
        # Max same stat
        stat_counts = {}
        for leg in legs:
            stat_counts[leg.stat_type] = stat_counts.get(leg.stat_type, 0) + 1
        
        max_stat = max(stat_counts.values()) if stat_counts else 0
        if max_stat > self.config['max_same_stat']:
            violations.append(f"Too many same stat: {max_stat}")
        
        return violations
    
    def _get_satisfied_constraints(self, legs: List[LegContext]) -> List[str]:
        """List constraints that are satisfied."""
        satisfied = []
        
        team_counts = {}
        for leg in legs:
            team_counts[leg.team_id] = team_counts.get(leg.team_id, 0) + 1
        
        if max(team_counts.values(), default=0) <= self.config['max_same_team']:
            satisfied.append('team_diversity')
        
        # Count unique games
        games = set(leg.game_id for leg in legs)
        if len(games) >= 2:
            satisfied.append('game_diversity')
        
        return satisfied
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _build_reasoning(self, legs: List[LegContext], 
                          corr_score: float, ev: float) -> str:
        """Build human-readable slip reasoning."""
        names = [f"{leg.player_name} {leg.action}" for leg in legs]
        return (
            f"{len(legs)}-Leg: {' / '.join(names)} | "
            f"Corr: {corr_score:.2f} | EV: {ev:+.2f}"
        )
    
    def _calculate_recommended_stake(self, ev: float, prob: float) -> float:
        """Calculate Kelly-based stake recommendation."""
        if ev <= 0:
            return 0.0
        
        # Simplified: fraction of kelly based on EV
        base_stake = min(0.05, ev * 0.1)  # 1 unit = 1% bankroll
        return base_stake


# =============================================================================
# Convenience function
# =============================================================================

_parlay_builder = None

def get_parlay_builder(config: Optional[Dict] = None) -> ParlayBuilder:
    global _parlay_builder
    if _parlay_builder is None or config is not None:
        _parlay_builder = ParlayBuilder(config)
    return _parlay_builder
