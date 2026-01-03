"""
HAKARI MODULE: SUGGESTION ENGINE v2.0
---------------------------------------
Generates +EV suggestions using the full Decision Engine pipeline:
- ProjectionResult from nba_logic
- MarketSnapshot from market_layer
- PickDecision from policy_engine
- ParlaySlip from parlay_builder

Scans for 'Jackpots' (mispriced backups when stars are OUT).
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Import Decision Engine Components
try:
    from . import nba_logic
    from .schemas import PropState, ProjectionResult, MarketSnapshot, PickDecision, ParlaySlip
    from .market_layer import get_market_service
    from .policy_engine import get_policy_engine
    from .parlay_builder import get_parlay_builder
    from .data_service import NBADataService
except ImportError:
    import nba_logic
    from schemas import PropState, ProjectionResult, MarketSnapshot, PickDecision, ParlaySlip
    from market_layer import get_market_service
    from policy_engine import get_policy_engine
    from parlay_builder import get_parlay_builder
    from data_service import NBADataService

logger = logging.getLogger("Hakari.SuggestionEngine")


class SuggestionEngine:
    """
    v2.0: Integrated with Decision Engine for full projection → decision pipeline.
    """
    
    def __init__(self, nba_logic_module=None):
        self.logic = nba_logic_module or nba_logic
        self._market = get_market_service()
        self._policy = get_policy_engine()
        self._parlay = get_parlay_builder()
        self._data = NBADataService()

    # =========================================================================
    # JACKPOT DETECTION (Injury-based opportunities)
    # =========================================================================
    
    def _check_star_status(self, team_id):
        """
        Check if a Star (Usg > 30%) is OUT for a team.
        Returns context dict or None.
        """
        # TODO: Integrate with real injury data from data_service
        return None

    def _find_undervalued_backup(self, team_id, star_context):
        """
        Find backup player who benefits from star absence.
        """
        # TODO: Integrate with roster + projection logic
        return None

    async def detect_jackpots(self, games) -> List[Dict]:
        """
        Hakari's 'Fever' logic: Searches for backups starting due to injury.
        
        Returns:
            List of high-confidence 'Jackpot' pick contexts
        """
        jackpots = []
        logger.info("Scanning for Jackpots...")
        
        for g in games:
            home_id = g.get('home_team_id')
            away_id = g.get('away_team_id')
            
            # Check Home Team
            star_out = self._check_star_status(home_id)
            if star_out:
                hero = self._find_undervalued_backup(home_id, star_out)
                if hero:
                    jackpots.append(hero)
            
            # Check Away Team
            star_out = self._check_star_status(away_id)
            if star_out:
                hero = self._find_undervalued_backup(away_id, star_out)
                if hero:
                    jackpots.append(hero)
        
        if jackpots:
            logger.info(f"HAKARI: Found {len(jackpots)} Jackpot opportunities!")
        else:
            logger.info("No clear Jackpots found. Market is tight.")
            
        return jackpots

    # =========================================================================
    # V2.0: FULL DECISION ENGINE PIPELINE
    # =========================================================================
    
    async def evaluate_prop(self, player_name: str, stat_type: str, 
                             line: float, game_context: Dict = None,
                             team_status: Dict = None) -> Tuple[PickDecision, ProjectionResult]:
        """
        Full v2.0 pipeline: Evaluate a single prop through projection → policy.
        
        Args:
            player_name: Player name
            stat_type: 'points', 'rebounds', 'assists', etc.
            line: PrizePicks line
            game_context: Optional game context overrides
            team_status: Optional team injury context
        
        Returns:
            (PickDecision, ProjectionResult) tuple
        """
        # 1. Fetch player data
        logs = self._data.fetch_player_logs(player_name)
        if not logs:
            logger.warning(f"No data for {player_name}")
            # Return SKIP decision
            return PickDecision(
                action='SKIP',
                edge_raw=0, edge_pct=0, prob_residual=0,
                confidence=0, adjusted_confidence=0,
                skip_reason=f"No data for {player_name}"
            ), None
        
        # 2. Build player stats from logs
        stat_key = stat_type.lower()
        if stat_key == 'points':
            stat_key = 'pts'
        elif stat_key == 'rebounds':
            stat_key = 'reb'
        elif stat_key == 'assists':
            stat_key = 'ast'
        elif stat_key == '3pm':
            stat_key = '3pm'
        
        recent_vals = [g.get(stat_key, 0) for g in logs[:10]]
        avg_stat = sum(recent_vals) / len(recent_vals) if recent_vals else 0
        avg_minutes = sum(g.get('min', 30) for g in logs[:10]) / len(logs[:10]) if logs else 30
        
        player_stats = {
            'name': player_name,
            f'avg_{stat_type}': avg_stat,
            'avg_minutes': avg_minutes,
            'age': 27,  # Default, would come from roster API
        }
        
        # 3. Create projection
        game_ctx = game_context or {'is_home': True, 'days_rest': 2}
        team_ctx = team_status or {}
        
        projector = self.logic.UniversalPlayerProjection(
            player_stats=player_stats,
            game_context=game_ctx,
            team_status=team_ctx
        )
        
        # Get full projection result
        projection = projector.get_full_projection(stat_type=stat_type, line=line)
        
        # 4. Build market snapshot
        market = self._market.build_snapshot(
            player_id=player_name.replace(' ', '_'),
            stat_type=stat_type,
            line=line
        )
        
        # 5. Evaluate with policy engine
        decision = self._policy.evaluate(projection, market)
        
        logger.info(f"{player_name} {stat_type}@{line}: {decision.action} ({decision.tier})")
        
        return decision, projection
    
    async def generate_suggestions(self, props: List[Dict] = None, 
                                    leg_count: int = 3,
                                    slip_type: str = 'POWER') -> Dict:
        """
        v2.0: Generate optimal parlay slips from a list of props.
        
        Args:
            props: List of {'player': str, 'stat': str, 'line': float, 'game_context': dict}
            leg_count: Target parlay size (2-6)
            slip_type: 'POWER' or 'FLEX'
        
        Returns:
            {
                'evaluated_count': int,
                'bets': int,
                'skips': int,
                'decisions': List[PickDecision],
                'slips': List[ParlaySlip]
            }
        """
        if not props:
            return {"results": [], "parlay": {}}
        
        # Evaluate all props
        candidates = []
        decisions = []
        
        for prop in props:
            decision, projection = await self.evaluate_prop(
                player_name=prop['player'],
                stat_type=prop['stat'],
                line=prop['line'],
                game_context=prop.get('game_context'),
                team_status=prop.get('team_status')
            )
            
            decisions.append(decision)
            
            if decision.action != 'SKIP':
                candidates.append((decision, {
                    'player_id': prop['player'].replace(' ', '_'),
                    'player_name': prop['player'],
                    'team_id': prop.get('team_id', 'UNK'),
                    'game_id': prop.get('game_id', 'UNK'),
                    'stat_type': prop['stat']
                }))
        
        bets = len(candidates)
        skips = len(decisions) - bets
        
        # Build slips if enough candidates
        slips = []
        if len(candidates) >= leg_count:
            slips = self._parlay.build_slips(candidates, leg_count, slip_type)
        
        return {
            'evaluated_count': len(props),
            'bets': bets,
            'skips': skips,
            'decisions': decisions,
            'slips': slips
        }
    
    async def generate_suggestions_simple(self, constraints: Dict) -> Dict:
        """
        v3.0: Simple suggestion generation using get_player_data directly.
        
        Uses the upgraded nba_logic.get_player_data with SKIP filtering and value_score ranking.
        
        Args:
            constraints: {
                "candidates": [{"player": str, "stat": str, "line": float, "meta": dict}, ...],
                "legs": int (2-6),
                "payout_mode": "flex" | "power",
                "top_n": int (how many slips to return)
            }
        
        Returns:
            {
                'evaluated_count': int,
                'bets': int,
                'skips': int,
                'ranked_picks': List[Dict],  # Sorted by value_score
                'top_slips': List[Dict],     # Built slips with coherence
                'skip_reasons': Dict[str, str]
            }
        """
        candidates = constraints.get('candidates', [])
        legs = constraints.get('legs', 4)
        payout_mode = constraints.get('payout_mode', 'flex')
        top_n = constraints.get('top_n', 10)
        
        if not candidates:
            return {
                'evaluated_count': 0, 'bets': 0, 'skips': 0,
                'ranked_picks': [], 'top_slips': [], 'skip_reasons': {}
            }
        
        # Evaluate each candidate using get_player_data
        evaluated = []
        skip_reasons = {}
        
        for cand in candidates:
            player = cand.get('player', '')
            stat = cand.get('stat', 'points')
            line = cand.get('line', 0)
            meta = cand.get('meta', {})
            
            # Call the upgraded get_player_data
            result = self.logic.get_player_data(
                player_name=player,
                stat_type=stat,
                line=line,
                context_overrides=meta
            )
            
            # Attach original candidate info
            result['player'] = player
            result['stat'] = stat
            result['line'] = line
            result['team_id'] = meta.get('team_id', 'UNK')
            result['game_id'] = meta.get('game_id', 'UNK')
            
            if result.get('action') == 'SKIP':
                skip_reasons[player] = result.get('skip_reason', 'Unknown')
            else:
                evaluated.append(result)
        
        # Rank by value_score (descending)
        ranked = sorted(evaluated, key=lambda x: x.get('value_score', 0), reverse=True)
        
        # Build slips from top candidates
        top_slips = []
        if len(ranked) >= legs:
            # Take top N * 2 candidates to build multiple slip options
            top_candidates = ranked[:min(len(ranked), legs * 3)]
            
            # Build slips using coherence checking
            # Improved: Combinatorial generation to find diverse slips instead of just sliding window
            import itertools
            
            # Limit pool to top 12 to avoid combinatorial explosion (12C4 = 495)
            pool = ranked[:12]
            combos = list(itertools.combinations(pool, legs))
            
            valid_slips = []
            
            for slip_picks in combos:
                # 1. Check Constraints (Max 3 per team)
                team_counts = {}
                game_counts = {}
                for p in slip_picks:
                    tid = p.get('team_id', 'UNK')
                    gid = p.get('game_id', 'UNK')
                    team_counts[tid] = team_counts.get(tid, 0) + 1
                    game_counts[gid] = game_counts.get(gid, 0) + 1
                
                if any(c > 3 for c in team_counts.values()):
                    continue # Violation: Max 3 players per team

                # 2. Coherence Check
                picks_for_coherence = [
                    {
                        'stat': p['stat'],
                        'direction': 'more' if p['action'] == 'OVER' else 'less',
                        'team_id': p.get('team_id', 'UNK'),
                        'risk_tags': p.get('risk_tags', []),
                        'context_tags': []
                    }
                    for p in slip_picks
                ]
                
                coherence = self.logic.validate_parlay_coherence(picks_for_coherence, detailed=True)
                
                # 3. Calculate Scores
                combined_value = sum(p.get('value_score', 0) for p in slip_picks)
                combined_confidence = sum(p.get('confidence', 0) for p in slip_picks) / legs
                
                # Diversification Bonus/Penalty
                diversity_score = 1.0
                unique_games = len(game_counts)
                
                if legs >= 4 and unique_games < 2:
                    diversity_score *= 0.9 # Penalty for single-game 4+ leg
                elif unique_games >= 3:
                    diversity_score *= 1.05 # Bonus for wide spread
                
                final_score = combined_value * coherence.get('correlation_score', 1) * diversity_score
                
                valid_slips.append({
                    'legs': legs,
                    'picks': [
                        {
                            'player': p['player'],
                            'stat': p['stat'],
                            'line': p['line'],
                            'action': p['action'],
                            'value_score': p.get('value_score', 0),
                            'confidence': p.get('confidence', 0),
                            'explain': p.get('explain', [])
                        }
                        for p in slip_picks
                    ],
                    'combined_value': round(combined_value, 4),
                    'combined_confidence': round(combined_confidence, 3),
                    'coherence': coherence,
                    'diversity_info': f"{unique_games} Games",
                    'final_score': round(final_score, 4),
                    'payout_mode': payout_mode
                })
        
        # Sort slips by Final Score (Value * Correlation * Diversity)
        top_slips = sorted(
            valid_slips, 
            key=lambda s: s['final_score'], 
            reverse=True
        )[:top_n]
        
        return {
            'evaluated_count': len(candidates),
            'bets': len(evaluated),
            'skips': len(candidates) - len(evaluated),
            'ranked_picks': ranked[:20],  # Top 20 individual picks
            'top_slips': top_slips,
            'skip_reasons': skip_reasons
        }
    
    # =========================================================================
    # LEGACY COMPATIBILITY
    # =========================================================================
    
    async def get_quick_pick(self, player_name: str, stat_type: str, 
                              line: float) -> Dict:
        """
        Simplified single-pick analysis (backward compatible).
        """
        decision, projection = await self.evaluate_prop(player_name, stat_type, line)
        
        return {
            "verdict": decision.action,
            "score": projection.mean if projection else 0,
            "diff": decision.edge_raw,
            "win_prob": projection.p_over if decision.action == 'OVER' else projection.p_under if projection else 0.5,
            "tier": decision.tier,
            "confidence": decision.confidence,
            "edge_pct": decision.edge_pct,
            "reasons": decision.reasons
        }
    
    def get_quick_pick_sync(self, player_name: str, stat_type: str, line: float) -> Dict:
        """
        Synchronous single-pick using get_player_data directly.
        """
        return self.logic.get_player_data(player_name, stat_type, line)

