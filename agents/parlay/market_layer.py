"""
HAKARI DECISION ENGINE: Market Layer
=====================================
Phase 2 Implementation - Line tracking, implied baselines, and payout mapping.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

try:
    from .schemas import MarketSnapshot, PRIZEPICKS_IMPLIED_BASELINE, POWER_PAYOUTS, FLEX_PAYOUTS
except ImportError:
    from schemas import MarketSnapshot, PRIZEPICKS_IMPLIED_BASELINE, POWER_PAYOUTS, FLEX_PAYOUTS

logger = logging.getLogger("Hakari.Market")


class MarketService:
    """
    Manages market data: lines, movement tracking, implied baselines, and payouts.
    """
    
    def __init__(self):
        # Line cache: {(player_id, stat_type): {'line': float, 'timestamp': str, 'history': [...]}}
        self._line_cache: Dict[Tuple[str, str], Dict] = {}
        
        # Historical lines for movement tracking
        self._line_history: Dict[Tuple[str, str], list] = {}
    
    # =========================================================================
    # LINE MANAGEMENT
    # =========================================================================
    
    def update_line(self, player_id: str, stat_type: str, line: float, 
                    timestamp: Optional[str] = None) -> None:
        """
        Update the current line for a player/stat combo.
        Tracks history for line movement analysis.
        """
        key = (player_id, stat_type)
        ts = timestamp or datetime.utcnow().isoformat()
        
        # Store history
        if key not in self._line_history:
            self._line_history[key] = []
        self._line_history[key].append({'line': line, 'timestamp': ts})
        
        # Update current
        self._line_cache[key] = {
            'line': line,
            'timestamp': ts,
            'opening_line': self._line_history[key][0]['line'] if self._line_history[key] else line
        }
        
        logger.debug(f"Line updated: {player_id}/{stat_type} -> {line}")
    
    def get_current_line(self, player_id: str, stat_type: str) -> Optional[float]:
        """Get the current line for a player/stat."""
        key = (player_id, stat_type)
        if key in self._line_cache:
            return self._line_cache[key]['line']
        return None
    
    def get_line_movement(self, player_id: str, stat_type: str) -> Dict:
        """
        Analyze line movement from opening to current.
        
        Returns:
            dict with 'movement' (float), 'direction' (str), 'magnitude' (str)
        """
        key = (player_id, stat_type)
        
        if key not in self._line_cache or key not in self._line_history:
            return {'movement': 0.0, 'direction': 'STABLE', 'magnitude': 'NONE'}
        
        current = self._line_cache[key]['line']
        opening = self._line_cache[key]['opening_line']
        movement = current - opening
        
        # Classify direction
        if abs(movement) < 0.5:
            direction = 'STABLE'
            magnitude = 'NONE'
        elif movement > 0:
            direction = 'UP'
            magnitude = 'LARGE' if movement > 2.0 else 'SMALL'
        else:
            direction = 'DOWN'
            magnitude = 'LARGE' if abs(movement) > 2.0 else 'SMALL'
        
        return {
            'movement': movement,
            'direction': direction,
            'magnitude': magnitude,
            'opening': opening,
            'current': current
        }
    
    # =========================================================================
    # IMPLIED BASELINE
    # =========================================================================
    
    def get_implied_baseline(self, stat_type: str, line: float, 
                              sport: str = 'nba') -> Tuple[float, str]:
        """
        Get the implied probability baseline for a given stat/line.
        
        This represents the market's expectation of OVER hit rate.
        Values derived from historical PrizePicks empirical data.
        
        Returns:
            (baseline_probability, method_used)
        """
        stat_lower = stat_type.lower()
        
        # Lookup in empirical tables
        if stat_lower in PRIZEPICKS_IMPLIED_BASELINE:
            buckets = PRIZEPICKS_IMPLIED_BASELINE[stat_lower]
            for (low, high), baseline in buckets.items():
                if low <= line < high:
                    logger.debug(f"Baseline for {stat_type}@{line}: {baseline} (empirical)")
                    return baseline, 'empirical_bucket'
            
            # Line outside known buckets - use closest
            all_ranges = list(buckets.keys())
            if line < all_ranges[0][0]:
                return buckets[all_ranges[0]], 'empirical_edge_low'
            else:
                return buckets[all_ranges[-1]], 'empirical_edge_high'
        
        # Default fallback
        logger.debug(f"Baseline for {stat_type}@{line}: 0.50 (default)")
        return 0.50, 'default_50'
    
    # =========================================================================
    # PAYOUT MAPPING
    # =========================================================================
    
    def get_payout_multiplier(self, leg_count: int, 
                               slip_type: str = 'POWER') -> float:
        """
        Get the payout multiplier for a parlay.
        
        Args:
            leg_count: Number of legs (2-6)
            slip_type: 'POWER' (all must hit) or 'FLEX' (partial wins)
        
        Returns:
            Multiplier (e.g., 3.0 for 2-leg Power)
        """
        if slip_type.upper() == 'POWER':
            return POWER_PAYOUTS.get(leg_count, 1.0)
        else:
            # For FLEX, return max payout (all hit scenario)
            key = (leg_count, leg_count)
            return FLEX_PAYOUTS.get(key, 1.0)
    
    def calculate_flex_payout(self, leg_count: int, hits: int) -> float:
        """
        Calculate FLEX payout for partial wins.
        
        Args:
            leg_count: Total legs
            hits: Number of hits
        
        Returns:
            Multiplier (can be < 1 for partial refund)
        """
        key = (leg_count, hits)
        return FLEX_PAYOUTS.get(key, 0.0)
    
    def get_breakeven_probability(self, leg_count: int, 
                                   slip_type: str = 'POWER') -> float:
        """
        Calculate the per-leg win probability needed to break even.
        
        For n-leg POWER at payout P: P = 1/p^n → p = P^(-1/n)
        """
        payout = self.get_payout_multiplier(leg_count, slip_type)
        if payout <= 0:
            return 1.0
        
        # Break-even: p^n = 1/payout
        breakeven_combined = 1.0 / payout
        per_leg = breakeven_combined ** (1.0 / leg_count)
        return per_leg
    
    # =========================================================================
    # MARKET SNAPSHOT BUILDER
    # =========================================================================
    
    def build_snapshot(self, player_id: str, stat_type: str, 
                        line: float, slip_type: str = 'POWER',
                        leg_count: int = 1) -> MarketSnapshot:
        """
        Build a complete MarketSnapshot for policy layer.
        """
        # Update line tracking if not already present
        key = (player_id, stat_type)
        if key not in self._line_cache:
            self.update_line(player_id, stat_type, line)
        
        # Get movement data
        movement_data = self.get_line_movement(player_id, stat_type)
        
        # Get implied baseline
        baseline, method = self.get_implied_baseline(stat_type, line)
        
        # Get payout
        payout = self.get_payout_multiplier(leg_count, slip_type)
        
        return MarketSnapshot(
            line=line,
            line_timestamp_utc=self._line_cache[key]['timestamp'],
            opening_line=movement_data.get('opening'),
            line_movement=movement_data.get('movement'),
            movement_direction=movement_data.get('direction'),
            implied_baseline=baseline,
            baseline_method=method,
            payout_type=slip_type,
            leg_count=leg_count,
            payout_multiplier=payout,
            estimated_vig=0.10  # PrizePicks ~10%
        )
    
    # =========================================================================
    # LINE MOVEMENT CONFIDENCE ADJUSTMENT
    # =========================================================================
    
    def get_movement_confidence_penalty(self, player_id: str, stat_type: str,
                                         our_direction: str) -> float:
        """
        Returns a confidence multiplier based on line movement.
        
        If the line moves AGAINST our pick direction, reduce confidence.
        If it moves WITH us, slight boost.
        
        Args:
            our_direction: 'OVER' or 'UNDER' - our intended pick
        
        Returns:
            Multiplier (e.g., 0.9 for penalty, 1.05 for boost)
        """
        movement = self.get_line_movement(player_id, stat_type)
        line_dir = movement['direction']
        magnitude = movement['magnitude']
        
        if line_dir == 'STABLE':
            return 1.0
        
        # Line going UP: favors UNDER (market thinks higher)
        # Line going DOWN: favors OVER (market thinks lower)
        market_favors = 'UNDER' if line_dir == 'UP' else 'OVER'
        
        if our_direction == market_favors:
            # We agree with sharp money
            return 1.02 if magnitude == 'SMALL' else 1.05
        else:
            # We're against sharp money - reduce confidence
            penalty = 0.95 if magnitude == 'SMALL' else 0.85
            logger.warning(f"Line movement against our pick: {our_direction} vs market {market_favors}")
            return penalty


# =============================================================================
# Convenience singleton
# =============================================================================

_market_service = None

def get_market_service() -> MarketService:
    """Get or create the global MarketService instance."""
    global _market_service
    if _market_service is None:
        _market_service = MarketService()
    return _market_service
