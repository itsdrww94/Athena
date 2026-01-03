"""
HAKARI DECISION ENGINE: Backtest Engine
=========================================
Phase 6 Implementation - Walk-forward backtesting with leakage prevention.

Provides:
- Walk-forward split management
- BacktestRecord logging
- Leakage validation
- Metrics calculation
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import uuid

try:
    from .schemas import BacktestRecord, ProjectionResult, MarketSnapshot, PickDecision, PropState
except ImportError:
    from schemas import BacktestRecord, ProjectionResult, MarketSnapshot, PickDecision, PropState

logger = logging.getLogger("Hakari.Backtest")


class BacktestEngine:
    """
    Walk-forward backtesting with strict leakage prevention.
    
    Design:
    - Rolling train/test windows
    - Every pick logged with full state snapshot
    - Post-game result filling
    - Metrics calculation
    """
    
    def __init__(self, log_dir: Optional[str] = None, config: Optional[Dict] = None):
        self.config = config or {
            'train_days': 60,
            'test_days': 7,
            'roll_step': 7,
        }
        
        # Logging directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path(__file__).parent / 'logs' / 'backtest_records'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory record cache
        self._records: List[BacktestRecord] = []
    
    # =========================================================================
    # RECORD CREATION
    # =========================================================================
    
    def create_record(self, 
                       player_id: str,
                       player_name: str,
                       stat_type: str,
                       line: float,
                       decision: str,
                       game_id: str,
                       game_date: str,
                       prop_state: Optional[PropState] = None,
                       projection: Optional[ProjectionResult] = None,
                       market: Optional[MarketSnapshot] = None,
                       pick_decision: Optional[PickDecision] = None) -> BacktestRecord:
        """
        Create a BacktestRecord with full snapshot at decision time.
        """
        record = BacktestRecord(
            record_id=str(uuid.uuid4()),
            timestamp_utc=datetime.utcnow().isoformat(),
            game_date=game_date,
            game_id=game_id,
            player_id=player_id,
            player_name=player_name,
            stat_type=stat_type,
            line=line,
            decision=decision,
            prop_state=prop_state,
            projection_result=projection,
            market_snapshot=market,
            pick_decision=pick_decision,
        )
        
        self._records.append(record)
        return record
    
    # =========================================================================
    # RESULT FILLING
    # =========================================================================
    
    def fill_result(self, record_id: str, 
                     actual_stat: float,
                     actual_minutes: Optional[float] = None,
                     game_result: Optional[Dict] = None,
                     line_at_close: Optional[float] = None) -> bool:
        """
        Fill in actual results after game completion.
        """
        for record in self._records:
            if record.record_id == record_id:
                record.actual_stat = actual_stat
                record.actual_minutes = actual_minutes
                record.game_result = game_result
                record.line_at_close = line_at_close
                
                # Determine hit
                if record.decision == 'OVER':
                    record.hit = actual_stat > record.line
                elif record.decision == 'UNDER':
                    record.hit = actual_stat < record.line
                else:
                    record.hit = None  # SKIP
                
                # Calculate payout (assuming 1 unit stake)
                if record.hit is True:
                    record.payout = 1.0  # Won
                elif record.hit is False:
                    record.payout = -1.0  # Lost
                else:
                    record.payout = 0.0  # Skip
                
                # Beat the close?
                if line_at_close and record.decision != 'SKIP':
                    if record.decision == 'OVER':
                        record.beat_close = line_at_close > record.line
                    else:
                        record.beat_close = line_at_close < record.line
                
                logger.info(f"Result filled: {record_id} -> hit={record.hit}")
                return True
        
        logger.warning(f"Record not found: {record_id}")
        return False
    
    # =========================================================================
    # LEAKAGE VALIDATION
    # =========================================================================
    
    LEAKAGE_CHECKS = [
        'injury_status_at_bet_time',
        'line_at_bet_time',
        'minutes_at_bet_time',
        'game_result_excluded',
    ]
    
    def validate_no_leakage(self, record: BacktestRecord) -> List[str]:
        """
        Check for potential data leakage in a record.
        Returns list of warnings.
        """
        warnings = []
        
        # Check timestamps
        if record.actual_stat is not None:
            # Results filled - that's expected post-game
            pass
        
        # Ensure prop_state was captured at bet time
        if record.prop_state and record.prop_state.snapshot_time_utc:
            snapshot_time = datetime.fromisoformat(record.prop_state.snapshot_time_utc.replace('Z', '+00:00'))
            decision_time = datetime.fromisoformat(record.timestamp_utc.replace('Z', '+00:00'))
            
            if snapshot_time > decision_time:
                warnings.append("PropState snapshot after decision time")
        
        # Check for forbidden future data
        if record.actual_minutes is not None and record.hit is None:
            warnings.append("Actual minutes present before hit determination")
        
        return warnings
    
    # =========================================================================
    # WALK-FORWARD SPLITS
    # =========================================================================
    
    def generate_walk_forward_splits(self, start_date: str, 
                                      end_date: str) -> List[Tuple[str, str, str, str]]:
        """
        Generate walk-forward train/test splits.
        
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        splits = []
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        train_days = self.config['train_days']
        test_days = self.config['test_days']
        roll_step = self.config['roll_step']
        
        current = start
        while current + timedelta(days=train_days + test_days) <= end:
            train_start = current.strftime('%Y-%m-%d')
            train_end = (current + timedelta(days=train_days - 1)).strftime('%Y-%m-%d')
            test_start = (current + timedelta(days=train_days)).strftime('%Y-%m-%d')
            test_end = (current + timedelta(days=train_days + test_days - 1)).strftime('%Y-%m-%d')
            
            splits.append((train_start, train_end, test_start, test_end))
            current += timedelta(days=roll_step)
        
        return splits
    
    # =========================================================================
    # METRICS CALCULATION
    # =========================================================================
    
    def calculate_metrics(self, records: Optional[List[BacktestRecord]] = None) -> Dict:
        """
        Calculate backtest performance metrics.
        """
        records = records or self._records
        
        # Filter to completed records with results
        completed = [r for r in records if r.hit is not None]
        bets = [r for r in completed if r.decision != 'SKIP']
        skips = [r for r in records if r.decision == 'SKIP']
        
        if not bets:
            return {'error': 'No completed bets'}
        
        # Basic metrics
        hits = sum(1 for r in bets if r.hit)
        total = len(bets)
        hit_rate = hits / total
        
        # ROI
        total_wagered = total  # 1 unit per bet
        total_profit = sum(r.payout or 0 for r in bets)
        roi = (total_profit / total_wagered) * 100
        
        # By tier
        tier_stats = {}
        for r in bets:
            if r.pick_decision:
                tier = r.pick_decision.tier
                if tier not in tier_stats:
                    tier_stats[tier] = {'hits': 0, 'total': 0}
                tier_stats[tier]['total'] += 1
                if r.hit:
                    tier_stats[tier]['hits'] += 1
        
        # Beat the close
        beat_close_bets = [r for r in bets if r.beat_close is not None]
        beat_close_rate = sum(1 for r in beat_close_bets if r.beat_close) / len(beat_close_bets) if beat_close_bets else 0
        
        # Max drawdown (simplified)
        running_pnl = 0
        peak = 0
        max_dd = 0
        for r in sorted(bets, key=lambda x: x.game_date):
            running_pnl += r.payout or 0
            peak = max(peak, running_pnl)
            dd = peak - running_pnl
            max_dd = max(max_dd, dd)
        
        # Skip accuracy (should be ~50% if we're correctly identifying no-edge)
        skip_with_results = [r for r in skips if r.actual_stat is not None]
        if skip_with_results:
            # Check what would have happened
            skip_would_hit = sum(1 for r in skip_with_results 
                                  if (r.actual_stat > r.line))  # Assume OVER default
            skip_hit_rate = skip_would_hit / len(skip_with_results)
        else:
            skip_hit_rate = None
        
        return {
            'total_bets': total,
            'hits': hits,
            'hit_rate': hit_rate,
            'breakeven_required': 0.524,  # For -110
            'roi_pct': roi,
            'total_profit_units': total_profit,
            'max_drawdown_units': max_dd,
            'beat_close_rate': beat_close_rate,
            'skips': len(skips),
            'skip_hit_rate': skip_hit_rate,
            'tier_breakdown': tier_stats,
        }
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def save_records(self, filename: Optional[str] = None) -> str:
        """Save records to JSONL file."""
        if not filename:
            filename = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        filepath = self.log_dir / filename
        
        with open(filepath, 'w') as f:
            for record in self._records:
                # Convert to dict (skip nested objects for now - serialize separately)
                record_dict = {
                    'record_id': record.record_id,
                    'timestamp_utc': record.timestamp_utc,
                    'game_date': record.game_date,
                    'game_id': record.game_id,
                    'player_id': record.player_id,
                    'player_name': record.player_name,
                    'stat_type': record.stat_type,
                    'line': record.line,
                    'decision': record.decision,
                    'actual_stat': record.actual_stat,
                    'actual_minutes': record.actual_minutes,
                    'hit': record.hit,
                    'payout': record.payout,
                    'beat_close': record.beat_close,
                    'model_version': record.model_version,
                }
                f.write(json.dumps(record_dict) + '\n')
        
        logger.info(f"Saved {len(self._records)} records to {filepath}")
        return str(filepath)
    
    def load_records(self, filepath: str) -> int:
        """Load records from JSONL file."""
        count = 0
        with open(filepath, 'r') as f:
            for line in f:
                data = json.loads(line)
                record = BacktestRecord(
                    record_id=data['record_id'],
                    timestamp_utc=data['timestamp_utc'],
                    game_date=data['game_date'],
                    game_id=data['game_id'],
                    player_id=data['player_id'],
                    player_name=data['player_name'],
                    stat_type=data['stat_type'],
                    line=data['line'],
                    decision=data['decision'],
                    actual_stat=data.get('actual_stat'),
                    actual_minutes=data.get('actual_minutes'),
                    hit=data.get('hit'),
                    payout=data.get('payout'),
                    beat_close=data.get('beat_close'),
                    model_version=data.get('model_version', '2.0.0'),
                )
                self._records.append(record)
                count += 1
        
        logger.info(f"Loaded {count} records from {filepath}")
        return count


# =============================================================================
# Convenience singleton
# =============================================================================

_backtest_engine = None

def get_backtest_engine(log_dir: Optional[str] = None) -> BacktestEngine:
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine(log_dir)
    return _backtest_engine
