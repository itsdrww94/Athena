import os
import json
import logging
import math
from datetime import datetime
from typing import Dict, Any, List

# Try-except import for config to handle local vs module execution
try:
    from . import config
except ImportError:
    import config

logger = logging.getLogger("Hakari.Ledger")

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "data", "ledger.jsonl")
PARAMS_PATH = os.path.join(os.path.dirname(__file__), "data", "params.json")

# Ensure data dir exists
os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)

class Ledger:
    def __init__(self):
        self.ledger_path = LEDGER_PATH
        self.params_path = PARAMS_PATH

    # TOOL 11: Ledger Logger
    def log_decision(self, 
                     context: Dict[str, Any], 
                     decision: Dict[str, Any], 
                     result: Dict[str, Any] = None,
                     shadow_mode: bool = False) -> bool:
        """
        Log decision to Supabase (and optional local legacy file).
        """
        try:
            try:
                from .supabase_client import get_client
            except ImportError:
                from supabase_client import get_client
            
            client = get_client()

            # Construct Payload
            payload = {
                "slip": {
                    "legs": decision.get('picks', []), # assuming structure
                    "legs_count": len(decision.get('picks', [])),
                    "correlation_score": decision.get('coherence', {}).get('correlation_score'),
                    "value_score": decision.get('combined_value'),
                },
                "stake": {
                    "amount": result.get('stake') if result else 0,
                    "currency": "USD",
                    "cap_applied": False # Logic not passed here yet
                },
                "thresholds_used": decision.get('thresholds_used', {}),
                "explanation": {
                    "human_explain": decision.get('explain', []),
                    "machine_explain": decision.get('explain_machine', {})
                },
                "execution_intent": {
                    "shadow_mode": shadow_mode,
                    "automation_enabled": not shadow_mode, # Proxy
                    "submitted_planned": not shadow_mode
                }
            }
            
            # Fire and forget
            import asyncio
            asyncio.create_task(client.emit_event(
                event_type="decision_made",
                payload=payload,
                platform="prizepicks",
                mode="shadow" if shadow_mode else "autonomous",
                slip_id=result.get("slip_id") if result else None
            ))
            
            # Legacy local log for backup
            self._log_legacy(context, decision, result, shadow_mode)
            return True
            
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            return False

    def _log_legacy(self, context, decision, result, shadow_mode):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context, 
            "decision": decision, 
            "result": result,
            "meta": {"shadow_mode": shadow_mode}
        }
        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except: pass

    async def record_outcome(self, slip_id: str, outcome_data: Dict):
        """
        Emit result_recorded event.
        outcome_data: {results:[], slip_outcome, money_won_lost, post_mortem}
        """
        from .supabase_client import get_client
        client = get_client()
        
        await client.emit_event(
            event_type="result_recorded",
            payload={
                "slip_id": slip_id,
                **outcome_data
            },
            slip_id=slip_id
        )

    # TOOL 12: Boring Reinforcement Parameter Updater
    async def update_policy_parameters(self, current_thresholds: Dict) -> Dict:
        """
        Clamped Bandit-Style Updater.
        Reads from Supabase history (async).
        """
        from .supabase_client import get_client
        client = get_client()
        
        # 1. Load recent history
        min_samples = config.RL_SETTINGS.get('min_samples_for_update', 20)
        
        # Fetch Result Recorded events
        history = await client.query_recent_events(limit=100, event_type="result_recorded")
        
        if not history:
            # Fallback to local legacy if Supabase empty/offline
            history = self._load_history(limit=100)
            # Adapt legacy format to simpler dict for below
            # Legacy history is full ledger entries. Supabase history is Event dicts.
            # We need to unify logic or branch.
            # Legacy structure: entry['result']['money_won_lost']
            # Supabase structure: entry['payload']['money_won_lost']
            pass # Handling inside loop below
        
        valid_samples = []
        for h in history:
            # Parse Payload vs Legacy
            payload = h.get('payload', h.get('result', {})) 
            if payload and  payload.get('status') in ['WON', 'LOST'] or payload.get('slip_outcome') in ['WON', 'LOST']:
                valid_samples.append(payload)

        if len(valid_samples) < min_samples:
            logger.info(f"RL: Not enough samples ({len(valid_samples)}). Freezing.")
            return current_thresholds

        # 2. Calculate metrics
        wins = sum(1 for p in valid_samples if float(p.get('money_won_lost', 0)) > 0)
        win_rate = wins / len(valid_samples)
        
        target = config.RL_SETTINGS.get('target_win_rate', 0.56)
        max_delta = config.RL_SETTINGS.get('max_update_delta', 0.01)
        
        new_thresholds = current_thresholds.copy()
        reason = "Stable"
        
        # 3. Boring Update Detection
        if win_rate < (target - 0.04):
            # TIGHTEN
            new_thresholds['min_edge_prob'] = min(0.15, new_thresholds.get('min_edge_prob', 0.06) + max_delta)
            new_thresholds['min_confidence'] = min(0.65, new_thresholds.get('min_confidence', 0.45) + max_delta)
            reason = f"WinRate {win_rate:.2f} < {target}. Tightening."
        elif win_rate > (target + 0.04):
            # RELAX
            new_thresholds['min_edge_prob'] = max(0.02, new_thresholds.get('min_edge_prob', 0.06) - (max_delta / 2))
            reason = f"WinRate {win_rate:.2f} > {target}. Relaxing."
            
        if reason != "Stable":
             await client.emit_event(
                 event_type="policy_updated",
                 payload={
                     "reason_summary": reason,
                     "changes": {"min_edge_prob": new_thresholds['min_edge_prob']},
                     "performance_snapshot": {"win_rate": win_rate, "samples": len(valid_samples)}
                 }
             )
            
        return new_thresholds


    def _load_history(self, limit=50) -> List[Dict]:
        """Load resolved entries from ledger."""
        data = []
        try:
            if not os.path.exists(self.ledger_path):
                return []
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    try:
                        entry = json.loads(line)
                        if entry.get('type') == 'POST_MORTEM': continue
                        if entry.get('meta', {}).get('shadow_mode'): continue # Don't learn from shadow for now (or maybe we should?)
                        
                        if entry.get('result', {}).get('status') in ['WON', 'LOST']:
                            data.append(entry)
                    except:
                        continue
                    if len(data) >= limit:
                        break
        except Exception:
            pass
        return data

# Singleton
_ledger = Ledger()
def get_ledger():
    return _ledger
