"""
HAKARI DECISION ENGINE: Motif/Pattern Engine
==============================================
Phase 4 Implementation - Pattern recognition with Bayesian shrinkage.

Motifs are measurable historical patterns that adjust projections:
- vs specific team
- rest context (B2B, 3-in-4, etc.)
- injury return games
- usage shifts when teammate out
"""

import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

try:
    from .schemas import MotifFeature, DEFAULT_MOTIF_CONFIG
except ImportError:
    from schemas import MotifFeature, DEFAULT_MOTIF_CONFIG

logger = logging.getLogger("Hakari.Motif")


class MotifEngine:
    """
    Extracts and blends pattern-based features for projection adjustments.
    
    Key principles:
    - Shrinkage: blend motif with season prior to avoid overfitting
    - Minimum samples: require N games before using motif
    - Capped adjustments: max ±25% impact
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_MOTIF_CONFIG
        
        # Cache for computed motifs
        self._motif_cache: Dict[str, MotifFeature] = {}
    
    # =========================================================================
    # VS TEAM MOTIF
    # =========================================================================
    
    def get_vs_team_motif(self, player_logs: List[Dict], opponent_id: str,
                           stat_type: str, prior: float) -> MotifFeature:
        """
        Calculate player's average vs specific team (last N games).
        
        Args:
            player_logs: Historical game logs with opponent info
            opponent_id: Team ID to filter
            stat_type: 'points', 'rebounds', etc.
            prior: Season average (for shrinkage)
        
        Returns:
            MotifFeature with blended value
        """
        # Filter logs vs this opponent
        vs_games = [g for g in player_logs if str(g.get('opponent_id')) == str(opponent_id)]
        
        if len(vs_games) < self.config['min_sample_size']:
            # Not enough data - return prior
            return MotifFeature(
                name=f"vs_team_{stat_type}",
                value=prior,
                sample_size=len(vs_games),
                confidence=0.0,
                prior=prior,
                blended=prior
            )
        
        # Calculate motif value
        stat_key = stat_type.lower()
        values = [g.get(stat_key, 0) for g in vs_games]
        motif_value = sum(values) / len(values) if values else prior
        
        # Blend with prior
        blended = MotifFeature.blend(
            motif_value, prior, len(vs_games), self.config['shrinkage_k']
        )
        
        confidence = min(1.0, len(vs_games) / 10.0)
        
        return MotifFeature(
            name=f"vs_team_{stat_type}",
            value=motif_value,
            sample_size=len(vs_games),
            confidence=confidence,
            prior=prior,
            blended=blended
        )
    
    # =========================================================================
    # REST CONTEXT MOTIF
    # =========================================================================
    
    def get_rest_context_motif(self, player_logs: List[Dict], 
                                rest_days: int, stat_type: str, 
                                prior: float) -> MotifFeature:
        """
        Calculate player's average in similar rest situations.
        
        Categories:
        - B2B (rest_days=0)
        - Short rest (1 day)
        - Normal (2-3 days)
        - Extended (4+ days)
        """
        # Determine rest category
        if rest_days == 0:
            rest_category = 'b2b'
        elif rest_days == 1:
            rest_category = 'short'
        elif rest_days <= 3:
            rest_category = 'normal'
        else:
            rest_category = 'extended'
        
        # Filter logs by rest category (requires rest_days in logs)
        matching_games = []
        for g in player_logs:
            g_rest = g.get('rest_days', 2)  # Default to normal
            if rest_days == 0 and g_rest == 0:
                matching_games.append(g)
            elif rest_days == 1 and g_rest == 1:
                matching_games.append(g)
            elif 2 <= rest_days <= 3 and 2 <= g_rest <= 3:
                matching_games.append(g)
            elif rest_days >= 4 and g_rest >= 4:
                matching_games.append(g)
        
        if len(matching_games) < self.config['min_sample_size']:
            return MotifFeature(
                name=f"rest_{rest_category}_{stat_type}",
                value=prior,
                sample_size=len(matching_games),
                confidence=0.0,
                prior=prior,
                blended=prior
            )
        
        stat_key = stat_type.lower()
        values = [g.get(stat_key, 0) for g in matching_games]
        motif_value = sum(values) / len(values) if values else prior
        
        blended = MotifFeature.blend(
            motif_value, prior, len(matching_games), self.config['shrinkage_k']
        )
        
        return MotifFeature(
            name=f"rest_{rest_category}_{stat_type}",
            value=motif_value,
            sample_size=len(matching_games),
            confidence=min(1.0, len(matching_games) / 10.0),
            prior=prior,
            blended=blended
        )
    
    # =========================================================================
    # INJURY RETURN MOTIF
    # =========================================================================
    
    def get_injury_return_motif(self, games_since_return: int, 
                                 stat_type: str, prior: float) -> MotifFeature:
        """
        Apply adjustment for games 1-3 after returning from injury.
        
        Uses preset multipliers (not historical data - low sample issue):
        - Game 1 back: 0.85 (15% reduction)
        - Game 2 back: 0.92
        - Game 3 back: 0.96
        - Game 4+: 1.00
        """
        if games_since_return is None or games_since_return > 3:
            return MotifFeature(
                name=f"injury_return_{stat_type}",
                value=prior,
                sample_size=0,
                confidence=0.0,
                prior=prior,
                blended=prior
            )
        
        # Preset multipliers
        multipliers = {1: 0.85, 2: 0.92, 3: 0.96}
        mult = multipliers.get(games_since_return, 1.0)
        
        adjusted = prior * mult
        
        return MotifFeature(
            name=f"injury_return_g{games_since_return}_{stat_type}",
            value=adjusted,
            sample_size=1,  # Preset, not empirical
            confidence=0.80,  # High confidence in known pattern
            prior=prior,
            blended=adjusted
        )
    
    # =========================================================================
    # USAGE SHIFT MOTIF (Teammate Out)
    # =========================================================================
    
    def get_usage_shift_motif(self, player_logs: List[Dict],
                               missing_teammate_id: str, stat_type: str,
                               prior: float) -> MotifFeature:
        """
        Calculate player's performance when specific teammate is OUT.
        
        Key for injury vacuum detection.
        """
        # Filter games where teammate was out
        games_without = [g for g in player_logs 
                         if missing_teammate_id in g.get('teammates_out', [])]
        
        if len(games_without) < self.config['min_sample_size']:
            return MotifFeature(
                name=f"without_{missing_teammate_id}_{stat_type}",
                value=prior,
                sample_size=len(games_without),
                confidence=0.0,
                prior=prior,
                blended=prior
            )
        
        stat_key = stat_type.lower()
        values = [g.get(stat_key, 0) for g in games_without]
        motif_value = sum(values) / len(values) if values else prior
        
        blended = MotifFeature.blend(
            motif_value, prior, len(games_without), self.config['shrinkage_k']
        )
        
        return MotifFeature(
            name=f"without_{missing_teammate_id}_{stat_type}",
            value=motif_value,
            sample_size=len(games_without),
            confidence=min(1.0, len(games_without) / 10.0),
            prior=prior,
            blended=blended
        )
    
    # =========================================================================
    # HOME/AWAY SPLIT MOTIF
    # =========================================================================
    
    def get_home_away_motif(self, player_logs: List[Dict], 
                             is_home: bool, stat_type: str,
                             prior: float) -> MotifFeature:
        """Calculate home vs away performance split."""
        
        matching = [g for g in player_logs if g.get('is_home') == is_home]
        
        if len(matching) < self.config['min_sample_size']:
            return MotifFeature(
                name=f"{'home' if is_home else 'away'}_{stat_type}",
                value=prior,
                sample_size=len(matching),
                confidence=0.0,
                prior=prior,
                blended=prior
            )
        
        stat_key = stat_type.lower()
        values = [g.get(stat_key, 0) for g in matching]
        motif_value = sum(values) / len(values) if values else prior
        
        blended = MotifFeature.blend(
            motif_value, prior, len(matching), self.config['shrinkage_k']
        )
        
        return MotifFeature(
            name=f"{'home' if is_home else 'away'}_{stat_type}",
            value=motif_value,
            sample_size=len(matching),
            confidence=min(1.0, len(matching) / 10.0),
            prior=prior,
            blended=blended
        )
    
    # =========================================================================
    # AGGREGATE MOTIF ADJUSTMENT
    # =========================================================================
    
    def calculate_aggregate_adjustment(self, motifs: List[MotifFeature], 
                                        prior: float) -> Tuple[float, Dict]:
        """
        Combine multiple motifs into a single adjustment multiplier.
        
        Uses confidence-weighted average of deviations from prior.
        Capped at max_motif_weight.
        
        Returns:
            (final_adjusted_value, breakdown_dict)
        """
        if not motifs:
            return prior, {}
        
        total_weight = 0.0
        weighted_deviation = 0.0
        breakdown = {}
        
        for m in motifs:
            if m.confidence > 0 and m.sample_size >= self.config['min_sample_size']:
                deviation = (m.blended - prior) / prior if prior != 0 else 0
                weight = m.confidence
                
                weighted_deviation += deviation * weight
                total_weight += weight
                breakdown[m.name] = {
                    'raw': m.value,
                    'blended': m.blended,
                    'deviation_pct': deviation * 100,
                    'confidence': m.confidence
                }
        
        if total_weight == 0:
            return prior, breakdown
        
        # Average deviation
        avg_deviation = weighted_deviation / total_weight
        
        # Cap at max weight
        max_adj = self.config['max_motif_weight']
        capped_deviation = max(-max_adj, min(max_adj, avg_deviation))
        
        final_value = prior * (1 + capped_deviation)
        
        logger.debug(f"Aggregate motif: prior={prior:.1f}, adj={capped_deviation:+.1%}, final={final_value:.1f}")
        
        return final_value, breakdown


# =============================================================================
# Convenience singleton
# =============================================================================

_motif_engine = None

def get_motif_engine(config: Optional[Dict] = None) -> MotifEngine:
    global _motif_engine
    if _motif_engine is None or config is not None:
        _motif_engine = MotifEngine(config)
    return _motif_engine
