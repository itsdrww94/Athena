"""
HAKARI DECISION ENGINE: Policy Engine
======================================
Phase 3 Implementation - SKIP-first decision logic with edge thresholds.

The policy layer transforms projections + market data into actionable decisions.
SKIP is a first-class citizen - the default action when edge is unclear.
"""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

try:
    from .schemas import (
        ProjectionResult, MarketSnapshot, PickDecision, PropState,
        DEFAULT_POLICY_CONFIG
    )
    from .market_layer import get_market_service
except ImportError:
    from schemas import (
        ProjectionResult, MarketSnapshot, PickDecision, PropState,
        DEFAULT_POLICY_CONFIG
    )
    from market_layer import get_market_service

logger = logging.getLogger("Hakari.Policy")


class PolicyEngine:
    """
    The decision layer: converts ProjectionResult + MarketSnapshot → PickDecision.
    
    Design Philosophy:
    - SKIP is the default. You need POSITIVE edge to bet.
    - Edge must exceed thresholds AND no hard-stop flags.
    - Confidence is adjusted for line movement.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_POLICY_CONFIG
        self._market = get_market_service()
    
    # =========================================================================
    # CORE DECISION LOGIC
    # =========================================================================
    
    def evaluate(self, projection: ProjectionResult, 
                  market: MarketSnapshot,
                  prop_state: Optional[PropState] = None) -> PickDecision:
        """
        Main entry point: evaluate a prop and return OVER/UNDER/SKIP decision.
        
        Decision Flow:
        1. Calculate edge metrics
        2. Check hard-stop flags → SKIP if any triggered
        3. Check dead zone → SKIP if probability too close to 50%
        4. Check edge threshold → SKIP if edge too small
        5. Check confidence threshold → SKIP if confidence too low
        6. Determine OVER vs UNDER based on probabilities
        7. Apply line movement penalty
        8. Assign tier and Kelly fraction
        
        Returns:
            PickDecision with full reasoning trace
        """
        # Step 1: Calculate edge metrics
        edge_raw = projection.mean - market.line
        edge_pct = (edge_raw / market.line * 100) if market.line != 0 else 0.0
        
        # Determine primary direction
        if projection.p_over > projection.p_under:
            direction = 'OVER'
            prob_win = projection.p_over
            prob_residual = projection.p_over - market.implied_baseline
        else:
            direction = 'UNDER'
            prob_win = projection.p_under
            prob_residual = projection.p_under - (1 - market.implied_baseline)
        
        # Initialize decision object
        decision = PickDecision(
            action='SKIP',  # Default - will override if passes checks
            edge_raw=edge_raw,
            edge_pct=edge_pct,
            prob_residual=prob_residual,
            confidence=projection.confidence,
            adjusted_confidence=projection.confidence,
            risk_flags=list(projection.risk_tags),
            risk_score=projection.risk_score,
            reasons=[],
            skip_reason=None,
            ev_estimate=0.0,
            kelly_fraction=0.0,
            tier='SKIP'
        )
        
        # Step 2: Check hard-stop flags
        hard_stops = self.config['hard_stop_flags']
        triggered_stops = [f for f in projection.risk_tags if f in hard_stops]
        if triggered_stops:
            decision.skip_reason = f"Hard stop: {', '.join(triggered_stops)}"
            decision.reasons.append(f"🛑 {decision.skip_reason}")
            logger.info(f"SKIP: {decision.skip_reason}")
            return decision
        
        # Step 3: Check dead zone
        dead_lower = self.config['dead_zone_lower']
        dead_upper = self.config['dead_zone_upper']
        if dead_lower <= projection.p_over <= dead_upper:
            decision.skip_reason = f"Dead zone: P(over)={projection.p_over:.2%} in [{dead_lower:.0%}, {dead_upper:.0%}]"
            decision.reasons.append(f"⚖️ {decision.skip_reason}")
            logger.info(f"SKIP: {decision.skip_reason}")
            return decision
        
        # Step 4: Check edge threshold
        min_edge = self.config['min_edge_pct']
        if abs(edge_pct) < min_edge:
            decision.skip_reason = f"Edge too small: {edge_pct:.1f}% < {min_edge}%"
            decision.reasons.append(f"📉 {decision.skip_reason}")
            logger.info(f"SKIP: {decision.skip_reason}")
            return decision
        
        # Step 5: Check confidence threshold
        min_conf = self.config['min_confidence']
        if projection.confidence < min_conf:
            decision.skip_reason = f"Low confidence: {projection.confidence:.1%} < {min_conf:.0%}"
            decision.reasons.append(f"🤔 {decision.skip_reason}")
            logger.info(f"SKIP: {decision.skip_reason}")
            return decision
        
        # Step 6: Apply line movement penalty
        movement_penalty = 1.0
        if market.line_movement and market.movement_direction:
            # Line UP = market expects higher → hurts OVER
            # Line DOWN = market expects lower → hurts UNDER
            if market.movement_direction == 'UP' and direction == 'OVER':
                movement_penalty = 0.95 if abs(market.line_movement) < 2 else 0.85
                decision.reasons.append(f"📊 Line moved UP against OVER: penalty {movement_penalty:.0%}")
            elif market.movement_direction == 'DOWN' and direction == 'UNDER':
                movement_penalty = 0.95 if abs(market.line_movement) < 2 else 0.85
                decision.reasons.append(f"📊 Line moved DOWN against UNDER: penalty {movement_penalty:.0%}")
            elif market.movement_direction in ['UP', 'DOWN']:
                movement_penalty = 1.02  # Slight boost when agreeing with movement
                decision.reasons.append(f"✅ Line moved WITH our direction")
        
        adjusted_confidence = projection.confidence * movement_penalty
        decision.adjusted_confidence = adjusted_confidence
        
        # Re-check confidence after adjustment
        if adjusted_confidence < min_conf:
            decision.skip_reason = f"Adjusted confidence too low: {adjusted_confidence:.1%} < {min_conf:.0%}"
            decision.reasons.append(f"⬇️ {decision.skip_reason}")
            logger.info(f"SKIP: {decision.skip_reason}")
            return decision
        
        # ============================
        # PASSED ALL CHECKS - MAKE BET
        # ============================
        
        decision.action = direction
        
        # Step 7: Calculate EV and Kelly
        ev = prob_win * market.payout_multiplier - 1.0
        decision.ev_estimate = ev
        
        # Kelly: f* = (bp - q) / b where b = payout - 1
        b = market.payout_multiplier - 1.0
        if b > 0:
            kelly = ((b * prob_win) - (1 - prob_win)) / b
            decision.kelly_fraction = max(0.0, min(0.25, kelly))  # Cap at 25%
        
        # Step 8: Assign tier
        decision.tier = self._assign_tier(edge_pct, adjusted_confidence, ev)
        
        # Build reasoning
        decision.reasons.extend([
            f"📈 Edge: {edge_pct:+.1f}% ({direction})",
            f"🎯 P(win): {prob_win:.1%} vs baseline {market.implied_baseline:.1%}",
            f"💰 EV: {ev:+.2f} | Kelly: {decision.kelly_fraction:.1%}",
            f"🏆 Tier: {decision.tier}"
        ])
        
        logger.info(f"BET {direction}: Edge={edge_pct:.1f}%, Tier={decision.tier}")
        
        return decision
    
    # =========================================================================
    # TIER ASSIGNMENT
    # =========================================================================
    
    def _assign_tier(self, edge_pct: float, confidence: float, ev: float) -> str:
        """
        Assign tier based on edge + confidence.
        
        S-Tier: Edge > 10%, Confidence > 75%, EV > 0.15
        A-Tier: Edge > 7%, Confidence > 65%
        B-Tier: Edge > 5%, Confidence > 55%
        C-Tier: Edge > 3%, Confidence > 55%
        """
        edge = abs(edge_pct)
        
        if edge > 10 and confidence > 0.75 and ev > 0.15:
            return 'S'
        elif edge > 7 and confidence > 0.65:
            return 'A'
        elif edge > 5 and confidence > 0.55:
            return 'B'
        elif edge > 3 and confidence > 0.55:
            return 'C'
        else:
            return 'SKIP'
    
    # =========================================================================
    # BATCH EVALUATION
    # =========================================================================
    
    def evaluate_batch(self, props: List[Dict]) -> List[PickDecision]:
        """
        Evaluate multiple props at once.
        
        Args:
            props: List of {'projection': ProjectionResult, 'market': MarketSnapshot, 'state': PropState}
        
        Returns:
            List of PickDecision
        """
        results = []
        for p in props:
            decision = self.evaluate(
                projection=p['projection'],
                market=p['market'],
                prop_state=p.get('state')
            )
            results.append(decision)
        
        # Log summary
        bets = [d for d in results if d.action != 'SKIP']
        skips = len(results) - len(bets)
        logger.info(f"Batch: {len(bets)} bets, {skips} skips out of {len(results)} props")
        
        return results
    
    # =========================================================================
    # EDGE CALCULATIONS (Utility Methods)
    # =========================================================================
    
    @staticmethod
    def calculate_edge_metrics(projection: ProjectionResult, 
                                market: MarketSnapshot) -> Dict:
        """
        Calculate multiple edge formulations for analysis.
        """
        return {
            'edge_raw': projection.mean - market.line,
            'edge_pct': (projection.mean - market.line) / market.line * 100 if market.line else 0,
            'z_score': projection.z_score,
            'prob_residual_over': projection.p_over - market.implied_baseline,
            'prob_residual_under': projection.p_under - (1 - market.implied_baseline),
        }
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    def update_config(self, updates: Dict) -> None:
        """Update policy configuration."""
        self.config.update(updates)
        logger.info(f"Policy config updated: {updates}")
    
    def get_skip_rules_summary(self) -> List[str]:
        """Return human-readable skip rules."""
        c = self.config
        return [
            f"1. Hard stop flags: {c['hard_stop_flags']}",
            f"2. Dead zone: P(over) in [{c['dead_zone_lower']:.0%}, {c['dead_zone_upper']:.0%}]",
            f"3. Min edge: {c['min_edge_pct']}%",
            f"4. Min confidence: {c['min_confidence']:.0%}",
            f"5. Line movement penalty threshold: {c['line_movement_penalty_threshold']} pts"
        ]


# =============================================================================
# Convenience singleton
# =============================================================================

_policy_engine = None

def get_policy_engine(config: Optional[Dict] = None) -> PolicyEngine:
    """Get or create the global PolicyEngine instance."""
    global _policy_engine
    if _policy_engine is None or config is not None:
        _policy_engine = PolicyEngine(config)
    return _policy_engine
