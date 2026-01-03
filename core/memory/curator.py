import logging
from typing import List, Dict, Any
from datetime import datetime
from collections import Counter

from core.contracts.event_schema import CanonicalEvent

logger = logging.getLogger("athena.memory.curator")

class MemoryCurator:
    """
    The Archivist.
    Job: Compresses raw days into clean Daily Capsules.
    """
    
    def generate_daily_capsule(self, date_str: str, events: List[CanonicalEvent]) -> Dict[str, Any]:
        """
        Synthesize a list of events into a summary capsule.
        """
        if not events:
            return {
                "date": date_str,
                "summary": "No activity recorded.",
                "stats": {}
            }
            
        # 1. Aggregations
        transaction_count = sum(1 for e in events if e.event_type == "TRANSACTION")
        watch_count = sum(1 for e in events if e.event_type == "WATCH")
        
        # 2. Highlights
        top_channels = Counter([e.data.get("channel_name") for e in events if e.event_type == "WATCH"]).most_common(3)
        
        # 3. Pattern Signals (Heuristics for now, LLM later)
        late_night_activity = sum(1 for e in events if e.timestamp.hour < 5)
        
        capsule = {
            "date": date_str,
            "created_at": datetime.now().isoformat(),
            "stats": {
                "transactions": transaction_count,
                "videos_watched": watch_count,
                "late_night_events": late_night_activity
            },
            "highlights": {
                "top_channels": [c[0] for c in top_channels],
                # "top_merchants": ...
            },
            "narrative": self._generate_narrative_template(watch_count, late_night_activity)
        }
        
        return capsule

    def _generate_narrative_template(self, watch_count: int, late_night: int) -> str:
        """Simple template generator (Placeholder for LLM)."""
        narrative = f"Active day with {watch_count} videos watched."
        if late_night > 0:
            narrative += " Notable late-night activity detected."
        return narrative
