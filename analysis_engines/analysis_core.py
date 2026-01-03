#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     A N A L Y S I S   C O R E                                 ║
║                  "The Research Lab Protocol"                                   ║
║                                                                               ║
║  Evidence-based analysis with privacy tiers and audit logging                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Principles:
1. No conclusions without evidence (show receipts)
2. Pull only relevant data, not everything
3. Three privacy tiers: permanent, derived, ephemeral
4. All queries are audited

Architecture:
    Storage Layer → Modeling Layer → Intelligence Layer → Conclusions
         ↓              ↓                   ↓                  ↓
    Raw files      Clean tables      Features/RAG        Citations
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

ATHENA_DATA_DIR = Path.home() / "athena_data"
AUDIT_LOG_DIR = ATHENA_DATA_DIR / "audit_logs"
CACHE_DIR = ATHENA_DATA_DIR / ".analysis_cache"

AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# PRIVACY TIERS
# =============================================================================

class PrivacyTier(Enum):
    """Three-tier privacy model for memory and insights."""
    PERMANENT = "permanent"      # Explicit user preferences, never expires
    DERIVED = "derived"          # Inferred insights, expire after 30-90 days
    EPHEMERAL = "ephemeral"      # Session memory, discarded after conversation


class SensitivityLevel(Enum):
    """Sensitivity tagging for data buckets."""
    PUBLIC = "public"            # Safe to analyze freely
    PRIVATE = "private"          # Requires explicit request to access
    RESTRICTED = "restricted"    # Health, intimate, off-limits unless asked
    

# Analysis modes with different permissions
ANALYSIS_MODES = {
    "finance": {
        "allowed_buckets": ["transactions", "subscriptions", "income"],
        "restricted_buckets": ["health"],
        "description": "Spending patterns, budgets, financial goals"
    },
    "health": {
        "allowed_buckets": ["sleep", "fitness", "nutrition"],
        "restricted_buckets": ["finance", "relationships"],
        "description": "Wellness, habits, fitness tracking"
    },
    "schedule": {
        "allowed_buckets": ["calendar", "tasks", "routines"],
        "restricted_buckets": ["finance", "health"],
        "description": "Time management, productivity, planning"
    },
    "learning": {
        "allowed_buckets": ["knowledge", "conversations", "notes"],
        "restricted_buckets": ["finance", "health"],
        "description": "Education, research, skill development"
    },
    "social": {
        "allowed_buckets": ["messages", "contacts", "events"],
        "restricted_buckets": ["finance"],
        "description": "Relationships, communication patterns"
    }
}


# =============================================================================
# EVIDENCE & CITATIONS
# =============================================================================

@dataclass
class Evidence:
    """A piece of evidence supporting a conclusion."""
    source: str              # Where the data came from
    timestamp: datetime      # When the evidence is from
    data_point: Any          # The actual data
    relevance: float         # 0-1 how relevant to the question
    citation: str            # Human-readable citation


@dataclass
class Conclusion:
    """An analytical conclusion with supporting evidence."""
    statement: str           # The conclusion
    confidence: float        # 0-1 confidence level
    evidence: List[Evidence] # Supporting evidence
    methodology: str         # How we arrived at this
    limitations: List[str]   # Caveats and limitations
    generated_at: datetime   # When conclusion was generated
    
    def to_dict(self) -> Dict:
        return {
            "statement": self.statement,
            "confidence": self.confidence,
            "evidence": [asdict(e) for e in self.evidence],
            "methodology": self.methodology,
            "limitations": self.limitations,
            "generated_at": self.generated_at.isoformat()
        }
    
    def format_with_receipts(self) -> str:
        """Format conclusion with citations (show receipts)."""
        output = [
            f"📊 **Conclusion:** {self.statement}",
            f"   Confidence: {self.confidence*100:.0f}%",
            f"\n📝 **Evidence ({len(self.evidence)} sources):**"
        ]
        
        for i, ev in enumerate(self.evidence[:5], 1):
            output.append(f"   {i}. [{ev.source}] {ev.citation}")
        
        if self.limitations:
            output.append(f"\n⚠️ **Limitations:**")
            for lim in self.limitations[:3]:
                output.append(f"   - {lim}")
        
        return "\n".join(output)


# =============================================================================
# AUDIT LOGGING
# =============================================================================

class AuditLogger:
    """
    Log every data access for transparency.
    
    Every answer shows WHAT DATA IT USED and WHY.
    """
    
    def __init__(self):
        self.session_id = hashlib.md5(
            datetime.now().isoformat().encode()
        ).hexdigest()[:8]
        
        self.log_file = AUDIT_LOG_DIR / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def log_access(self, query: str, data_sources: List[str], 
                   records_accessed: int, purpose: str,
                   mode: str = "general") -> None:
        """Log a data access event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "query": query[:200],
            "data_sources": data_sources,
            "records_accessed": records_accessed,
            "purpose": purpose,
            "mode": mode
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    def log_conclusion(self, conclusion: Conclusion) -> None:
        """Log a generated conclusion."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "type": "conclusion",
            "statement": conclusion.statement[:200],
            "confidence": conclusion.confidence,
            "evidence_count": len(conclusion.evidence),
            "sources": [e.source for e in conclusion.evidence]
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_recent_accesses(self, hours: int = 24) -> List[Dict]:
        """Get recent data accesses for review."""
        cutoff = datetime.now() - timedelta(hours=hours)
        accesses = []
        
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if entry_time > cutoff:
                        accesses.append(entry)
        
        return accesses


# =============================================================================
# FEATURE STORE (Precomputed Analytics)
# =============================================================================

class FeatureStore:
    """
    Precomputed features for fast insights.
    
    Stores daily/weekly aggregates so we don't re-read everything.
    """
    
    def __init__(self):
        self.store_file = CACHE_DIR / "feature_store.json"
        self.features = self._load()
    
    def _load(self) -> Dict:
        if self.store_file.exists():
            return json.loads(self.store_file.read_text())
        return {"updated_at": None, "features": {}}
    
    def save(self) -> None:
        self.features["updated_at"] = datetime.now().isoformat()
        self.store_file.write_text(json.dumps(self.features, indent=2, default=str))
    
    def set_feature(self, category: str, name: str, value: Any, 
                    ttl_days: int = 7) -> None:
        """Set a precomputed feature with TTL."""
        if category not in self.features["features"]:
            self.features["features"][category] = {}
        
        self.features["features"][category][name] = {
            "value": value,
            "computed_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=ttl_days)).isoformat()
        }
        self.save()
    
    def get_feature(self, category: str, name: str) -> Optional[Any]:
        """Get a feature if not expired."""
        cat = self.features["features"].get(category, {})
        feat = cat.get(name)
        
        if not feat:
            return None
        
        expires = datetime.fromisoformat(feat["expires_at"])
        if datetime.now() > expires:
            return None  # Expired
        
        return feat["value"]
    
    def get_all_features(self, category: str) -> Dict[str, Any]:
        """Get all non-expired features for a category."""
        cat = self.features["features"].get(category, {})
        result = {}
        
        for name, feat in cat.items():
            expires = datetime.fromisoformat(feat["expires_at"])
            if datetime.now() <= expires:
                result[name] = feat["value"]
        
        return result


# =============================================================================
# INSIGHT MEMORY (Privacy-Tiered)
# =============================================================================

class InsightMemory:
    """
    Three-tier memory for insights.
    
    - Permanent: User preferences, explicit facts (never expire)
    - Derived: Inferred patterns (expire after 30-90 days)
    - Ephemeral: Current session only (discarded after)
    """
    
    def __init__(self):
        self.memory_file = CACHE_DIR / "insight_memory.json"
        self.memory = self._load()
        self.ephemeral = {}  # Session-only, not persisted
    
    def _load(self) -> Dict:
        if self.memory_file.exists():
            return json.loads(self.memory_file.read_text())
        return {
            "permanent": {},
            "derived": {}
        }
    
    def save(self) -> None:
        # Clean expired derived insights
        self._clean_expired()
        self.memory_file.write_text(json.dumps(self.memory, indent=2, default=str))
    
    def _clean_expired(self) -> None:
        """Remove expired derived insights."""
        now = datetime.now()
        to_remove = []
        
        for key, insight in self.memory["derived"].items():
            expires = datetime.fromisoformat(insight.get("expires_at", now.isoformat()))
            if now > expires:
                to_remove.append(key)
        
        for key in to_remove:
            del self.memory["derived"][key]
    
    def set_permanent(self, key: str, value: Any, source: str = "user") -> None:
        """Set a permanent insight (user preference, explicit fact)."""
        self.memory["permanent"][key] = {
            "value": value,
            "source": source,
            "set_at": datetime.now().isoformat()
        }
        self.save()
    
    def set_derived(self, key: str, value: Any, confidence: float,
                    ttl_days: int = 30) -> None:
        """Set a derived insight (inferred pattern, expires)."""
        self.memory["derived"][key] = {
            "value": value,
            "confidence": confidence,
            "inferred_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=ttl_days)).isoformat()
        }
        self.save()
    
    def set_ephemeral(self, key: str, value: Any) -> None:
        """Set session-only insight (not persisted)."""
        self.ephemeral[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get insight from any tier (permanent > derived > ephemeral)."""
        if key in self.memory["permanent"]:
            return self.memory["permanent"][key]["value"]
        
        if key in self.memory["derived"]:
            insight = self.memory["derived"][key]
            expires = datetime.fromisoformat(insight["expires_at"])
            if datetime.now() <= expires:
                return insight["value"]
        
        return self.ephemeral.get(key, default)
    
    def get_all_permanent(self) -> Dict[str, Any]:
        """Get all permanent insights."""
        return {k: v["value"] for k, v in self.memory["permanent"].items()}
    
    def get_profile(self) -> Dict[str, Any]:
        """Get complete user profile from all tiers."""
        profile = {
            "permanent": self.get_all_permanent(),
            "derived": {
                k: v["value"] for k, v in self.memory["derived"].items()
                if datetime.now() <= datetime.fromisoformat(v["expires_at"])
            },
            "session": self.ephemeral.copy()
        }
        return profile


# =============================================================================
# ANALYSIS ENGINE (Evidence-Based)
# =============================================================================

class AnalysisEngine:
    """
    Evidence-based analysis engine.
    
    Rule: No conclusions without evidence.
    """
    
    def __init__(self, mode: str = "general"):
        self.mode = mode
        self.permissions = ANALYSIS_MODES.get(mode, {
            "allowed_buckets": [],
            "restricted_buckets": []
        })
        
        self.audit = AuditLogger()
        self.features = FeatureStore()
        self.memory = InsightMemory()
        self.evidence_collected = []
    
    def can_access(self, bucket: str) -> bool:
        """Check if current mode can access a data bucket."""
        if bucket in self.permissions.get("restricted_buckets", []):
            return False
        return True
    
    def collect_evidence(self, source: str, data_point: Any,
                         timestamp: datetime = None, 
                         relevance: float = 1.0) -> Evidence:
        """Collect a piece of evidence with citation."""
        evidence = Evidence(
            source=source,
            timestamp=timestamp or datetime.now(),
            data_point=data_point,
            relevance=relevance,
            citation=f"From {source} at {(timestamp or datetime.now()).strftime('%Y-%m-%d')}"
        )
        self.evidence_collected.append(evidence)
        return evidence
    
    def conclude(self, statement: str, confidence: float,
                 methodology: str = "", 
                 limitations: List[str] = None) -> Conclusion:
        """Generate a conclusion with collected evidence."""
        
        if not self.evidence_collected:
            raise ValueError("Cannot conclude without evidence. Collect evidence first.")
        
        # Sort evidence by relevance
        sorted_evidence = sorted(
            self.evidence_collected,
            key=lambda e: e.relevance,
            reverse=True
        )
        
        conclusion = Conclusion(
            statement=statement,
            confidence=confidence,
            evidence=sorted_evidence[:10],  # Keep top 10
            methodology=methodology,
            limitations=limitations or ["Based on available data only"],
            generated_at=datetime.now()
        )
        
        # Audit the conclusion
        self.audit.log_conclusion(conclusion)
        
        # Clear evidence for next analysis
        self.evidence_collected = []
        
        return conclusion
    
    def analyze_with_evidence(self, question: str, 
                               data_fetcher, 
                               analyzer) -> Conclusion:
        """
        Run an analysis with full evidence chain.
        
        1. Fetch relevant data (via data_fetcher)
        2. Analyze it (via analyzer function)
        3. Generate conclusion with citations
        """
        # Log the query
        self.audit.log_access(
            query=question,
            data_sources=["pending"],
            records_accessed=0,
            purpose="analysis",
            mode=self.mode
        )
        
        # Fetch data
        data, sources = data_fetcher(question)
        
        # Collect as evidence
        for source, records in data.items():
            for record in records[:100]:  # Limit per source
                self.collect_evidence(
                    source=source,
                    data_point=record,
                    timestamp=record.get("timestamp"),
                    relevance=0.8
                )
        
        # Run analysis
        result = analyzer(data)
        
        # Update audit with actual sources
        self.audit.log_access(
            query=question,
            data_sources=sources,
            records_accessed=sum(len(v) for v in data.values()),
            purpose="analysis_complete",
            mode=self.mode
        )
        
        return result


# =============================================================================
# DAILY/WEEKLY REPORT GENERATORS
# =============================================================================

def generate_daily_report(engine: AnalysisEngine) -> Dict[str, Conclusion]:
    """Generate daily analysis report."""
    reports = {}
    
    # These would call the actual data analysis
    # For now, structure the output format
    
    reports["summary"] = {
        "type": "daily_summary",
        "generated_at": datetime.now().isoformat(),
        "sections": [
            "spending_today",
            "calendar_tomorrow",
            "habit_streaks",
            "anomalies_detected"
        ]
    }
    
    return reports


def generate_weekly_report(engine: AnalysisEngine) -> Dict[str, Conclusion]:
    """Generate weekly analysis report."""
    reports = {}
    
    reports["summary"] = {
        "type": "weekly_summary",
        "generated_at": datetime.now().isoformat(),
        "sections": [
            "spending_vs_last_week",
            "hidden_costs",
            "time_sinks",
            "habit_changes",
            "goal_progress"
        ]
    }
    
    return reports


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Demo the analysis system."""
    print("🔬 Analysis Core - Research Lab Protocol")
    print("=" * 50)
    
    # Initialize
    engine = AnalysisEngine(mode="finance")
    
    # Show current mode permissions
    print(f"\n📊 Current Mode: {engine.mode}")
    print(f"   Allowed: {engine.permissions.get('allowed_buckets', [])}")
    print(f"   Restricted: {engine.permissions.get('restricted_buckets', [])}")
    
    # Demo evidence collection
    engine.collect_evidence(
        source="transactions",
        data_point={"amount": 45.50, "merchant": "DoorDash"},
        timestamp=datetime.now() - timedelta(days=1),
        relevance=0.9
    )
    
    engine.collect_evidence(
        source="transactions",
        data_point={"amount": 12.99, "merchant": "Spotify"},
        timestamp=datetime.now() - timedelta(days=2),
        relevance=0.7
    )
    
    # Generate conclusion
    conclusion = engine.conclude(
        statement="Weekend spending is 30% higher than weekdays",
        confidence=0.85,
        methodology="Compared average daily spending across weekdays vs weekends",
        limitations=["Only analyzed last 30 days", "Excludes recurring bills"]
    )
    
    print("\n" + conclusion.format_with_receipts())
    
    # Show audit log
    print(f"\n📋 Audit log: {engine.audit.log_file}")


if __name__ == "__main__":
    main()
