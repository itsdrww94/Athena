"""
Athena Pattern Engine
=====================
"The Lab Notebook"
Handles Event Ingestion, Deduplication, and Trend Tracking.

Build Order Ref: 2, 3, 4
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from .athena_schemas import AthenaEvent, AgentOutput

logger = logging.getLogger("athena.pattern_engine")

@dataclass
class Pattern:
    id: str
    domain: str
    name: str # e.g. "Friday Night Impulse"
    description: str
    confidence: float # 0.0 to 1.0 (Machine Confidence)
    support: int # Number of events supporting this
    status: str # "hypothesis", "confirmed", "rejected"
    meta: Dict[str, Any] = field(default_factory=dict) # e.g. {"weekday": 4, "hour_block": "late_night"}
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

class PatternEngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PatternEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # Storage
        self.events: List[AthenaEvent] = []
        self.dedupe_index: Dict[str, str] = {} 
        self.patterns: Dict[str, Pattern] = {} # pattern_id -> Pattern
        
        # Legacy support (map domain trends to patterns view if needed)
        self.trends: Dict[str, Dict] = defaultdict(dict) 
        
        self._initialized = True

    # =========================================================================
    # 2. EVENT LOGGER & 3. DEDUPE
    # =========================================================================

    def ingest_agent_output(self, output: AgentOutput) -> int:
        accepted_count = 0
        for event in output.events_to_log:
            if self._ingest_event(event):
                accepted_count += 1
                
        touched_domains = {e.domain for e in output.events_to_log}
        for domain in touched_domains:
            self._analyze_patterns(domain)
            
        return accepted_count

    def _ingest_event(self, event: AthenaEvent) -> bool:
        fingerprint = event.generate_dedupe_key()
        if fingerprint in self.dedupe_index:
            logger.info(f"Dedupe: Skipping duplicate event {fingerprint}")
            return False
            
        self.events.append(event)
        self.dedupe_index[fingerprint] = event.event_id
        return True

    # =========================================================================
    # 4. PATTERN REGISTRY & ADVANCED BASELINES
    # =========================================================================
    
    def _analyze_patterns(self, domain: str):
        """
        Run advanced pattern detection for a domain.
        Ref: Phase 5 (Cognitive Upgrade)
        """
        domain_events = [e for e in self.events if e.domain == domain]
        if not domain_events:
            return

        now = datetime.now()
        
        # A. Baselines
        stats = self._calculate_advanced_stats(domain_events, now)
        
        # B. Detect/Update Patterns
        self._detect_volume_anomaly(domain, stats)
        # self._detect_sequence(domain, domain_events) # Future implementation
        
        # C. Update Legacy Trends View (for compatibility)
        self.trends[domain] = {
            "metric": "activity_volume",
            "direction": stats["direction"],
            "count_last_30d": stats["count_30d"],
            "baseline_30d": stats["baseline_30d"]
        }

    def _calculate_advanced_stats(self, events: List[AthenaEvent], now: datetime) -> Dict:
        """
        Calculate 30d, Weekend vs Weekday, etc.
        """
        last_30d = now - timedelta(days=30)
        
        # 1. Volume 30d
        count_30d = sum(1 for e in events if e.timestamp >= last_30d)
        total_count = len(events)
        
        # 2. Baseline (Simple)
        months_active = max(1, (now - events[0].timestamp).days / 30)
        baseline_30d = (total_count - count_30d) / months_active if total_count > count_30d else count_30d
        
        # 3. Direction
        direction = "flat"
        if baseline_30d > 0:
            delta = (count_30d - baseline_30d) / baseline_30d
            if delta > 0.2: direction = "up"
            elif delta < -0.2: direction = "down"
            
        return {
            "count_30d": count_30d,
            "baseline_30d": baseline_30d,
            "direction": direction
        }

    def _detect_volume_anomaly(self, domain: str, stats: Dict):
        """
        If direction is UP/DOWN, create/update a Pattern.
        """
        if stats["direction"] == "flat":
            return

        pid = f"pattern_{domain}_volume"
        confidence = 0.6 if abs(stats["count_30d"] - stats["baseline_30d"]) < 5 else 0.85
        
        if pid in self.patterns:
            # Update existing
            p = self.patterns[pid]
            if p.status != "rejected":
                p.confidence = confidence
                p.support = stats["count_30d"]
                p.last_updated = datetime.now().isoformat()
        else:
            # Create new Hypothesis
            self.patterns[pid] = Pattern(
                id=pid,
                domain=domain,
                name=f"{domain.capitalize()} Activity {stats['direction'].upper()}",
                description=f"Activity is {stats['direction']} ({stats['count_30d']} vs {stats['baseline_30d']:.1f})",
                confidence=confidence,
                support=stats["count_30d"],
                status="hypothesis"
            )

    # =========================================================================
    # 5. USER FEEDBACK
    # =========================================================================

    def rate_pattern(self, pattern_id: str, correct: bool):
        """
        User Feedback Loop.
        """
        if pattern_id in self.patterns:
            p = self.patterns[pattern_id]
            if correct:
                p.status = "confirmed"
                p.confidence = min(0.99, p.confidence + 0.1)
            else:
                p.status = "rejected"
                p.confidence = max(0.01, p.confidence - 0.3)
            p.last_updated = datetime.now().isoformat()
            self.save_state()
            return True
        return False

    def get_active_patterns(self, domain: str = None) -> List[Pattern]:
        """Return confirmed or high-confidence hypothesis patterns."""
        res = []
        for p in self.patterns.values():
            if domain and p.domain != domain:
                continue
            if p.status == "rejected":
                continue
            if p.confidence > 0.4:
                res.append(p)
        return res

    # =========================================================================
    # 6. PERSISTENCE
    # =========================================================================
    
    def _get_paths(self):
        from pathlib import Path
        base = Path(__file__).parent.parent / "brain"
        base.mkdir(exist_ok=True)
        return base / "events_log.json", base / "patterns_db.json" # Renamed trends -> patterns

    def save_state(self):
        import json
        e_path, p_path = self._get_paths()
        
        # Events
        serializable_events = []
        for e in self.events:
            d = e.__dict__.copy()
            if isinstance(d["timestamp"], datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            serializable_events.append(d)
        
        with open(e_path, "w") as f:
            json.dump(serializable_events, f, indent=2)
            
        # Patterns
        serializable_patterns = {k: asdict(v) for k, v in self.patterns.items()}
        with open(p_path, "w") as f:
            json.dump(serializable_patterns, f, indent=2)

    def load_state(self):
        import json
        e_path, p_path = self._get_paths()
        
        if e_path.exists():
            try:
                with open(e_path, "r") as f:
                    raw_events = json.load(f)
                self.events = []
                self.dedupe_index = {}
                for d in raw_events:
                    d["timestamp"] = datetime.fromisoformat(d["timestamp"])
                    evt = AthenaEvent(**d)
                    self.events.append(evt)
                    self.dedupe_index[evt.generate_dedupe_key()] = evt.event_id
            except Exception: pass

        if p_path.exists():
            try:
                with open(p_path, "r") as f:
                    raw_patterns = json.load(f)
                self.patterns = {k: Pattern(**v) for k, v in raw_patterns.items()}
                
                # Rehydrate Trends view for backward compatibility
                for p in self.patterns.values():
                    if p.status != "rejected":
                         self.trends[p.domain]["direction"] = "up" if "UP" in p.name else ("down" if "DOWN" in p.name else "flat")
            except Exception: pass

_pattern_engine = None
def get_pattern_engine() -> PatternEngine:
    global _pattern_engine
    if _pattern_engine is None:
        _pattern_engine = PatternEngine()
        _pattern_engine.load_state()
    return _pattern_engine
