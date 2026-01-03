import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class JournalEntry:
    timestamp: float
    entry_type: str  # CLASSIFICATION, ACTION, PIVOT, REJECTION
    content: Dict[str, Any]
    rationale: str
    confidence: float

class DecisionJournal:
    """
    Traces 'How JARVIS Thinks'.
    This is not just debug logs; it's the investgation narrative.
    """
    
    def __init__(self):
        self._entries: List[JournalEntry] = []
        self._start_time = time.time()

    def log_classification(self, input_data: str, entity_type: str, confidence: float, reason: str):
        self._log("CLASSIFICATION", {
            "input": input_data,
            "entity": entity_type
        }, reason, confidence)

    def log_action(self, tool_name: str, args: Dict[str, Any], reason: str):
        self._log("ACTION", {
            "tool": tool_name,
            "args": args
        }, reason, 1.0)

    def log_pivot(self, from_entity: str, to_action: str, reason: str):
        self._log("PIVOT", {
            "from": from_entity,
            "next": to_action
        }, reason, 0.8)

    def log_rejection(self, item: str, reason: str):
        """
        Explicitly log why something was ignored (Scope, Low Confidence, etc).
        """
        self._log("REJECTION", {
            "item": item
        }, reason, 1.0)

    def _log(self, type_str: str, content: Dict, rationale: str, confidence: float):
        entry = JournalEntry(
            timestamp=time.time(),
            entry_type=type_str,
            content=content,
            rationale=rationale,
            confidence=confidence
        )
        self._entries.append(entry)

    def export_json(self) -> str:
        return json.dumps([asdict(e) for e in self._entries], indent=2)

    def get_summary(self) -> List[str]:
        return [f"[{e.entry_type}] {e.rationale}" for e in self._entries]
