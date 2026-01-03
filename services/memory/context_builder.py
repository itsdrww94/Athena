"""
Athena Context Builder
======================
Builds rich context packets for the orchestrator before processing each message.
Combines recent conversation history, relevant facts, and semantic matches.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Lazy imports
_logger = None

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.context")
    return _logger


@dataclass
class ContextPacket:
    """
    Complete context packet for the orchestrator.
    
    Contains everything needed to understand the user's request in context.
    """
    # User profile facts
    user_name: str = "User"
    user_facts: Dict[str, Any] = field(default_factory=dict)
    
    # Recent conversation
    recent_messages: List[Dict[str, str]] = field(default_factory=list)
    conversation_summary: str = ""
    
    # Semantic matches (RAG)
    semantic_matches: List[Dict[str, Any]] = field(default_factory=list)
    
    # Active context
    current_session_id: str = ""
    current_interface: str = "cli"
    
    # Timing
    built_at: str = ""
    
    def to_prompt_string(self) -> str:
        """
        Format context packet as a string for LLM prompt injection.
        """
        lines = []
        
        # User info
        lines.append(f"**User Profile:**")
        lines.append(f"- Name: {self.user_name}")
        for key, value in list(self.user_facts.items())[:10]:  # Limit facts
            lines.append(f"- {key}: {value}")
        
        # Recent conversation
        if self.recent_messages:
            lines.append(f"\n**Recent Conversation ({len(self.recent_messages)} turns):**")
            for msg in self.recent_messages[-5:]:  # Last 5 turns
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")[:200]  # Truncate
                lines.append(f"{role}: {content}")
        
        # Semantic matches
        if self.semantic_matches:
            lines.append(f"\n**Relevant Memory ({len(self.semantic_matches)} matches):**")
            for match in self.semantic_matches[:3]:  # Top 3
                text = match.get("text", "")[:150]
                similarity = match.get("similarity", 0)
                lines.append(f"- [{similarity:.2f}] {text}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_name": self.user_name,
            "user_facts": self.user_facts,
            "recent_messages": self.recent_messages,
            "conversation_summary": self.conversation_summary,
            "semantic_matches": self.semantic_matches,
            "current_session_id": self.current_session_id,
            "current_interface": self.current_interface,
            "built_at": self.built_at
        }


def build_context(user_id: str, session_id: str, query: str,
                  include_semantic: bool = True,
                  max_recent: int = 10,
                  max_facts: int = 20,
                  max_semantic: int = 5) -> ContextPacket:
    """
    Build a complete context packet for the orchestrator.
    
    This function MUST be called before routing/answering every user message.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        query: The user's current message (used for semantic search)
        include_semantic: Whether to perform semantic search
        max_recent: Maximum recent messages to include
        max_facts: Maximum facts to include
        max_semantic: Maximum semantic matches to include
        
    Returns:
        ContextPacket with all relevant context
    """
    logger = _get_logger()
    
    packet = ContextPacket(
        current_session_id=session_id,
        built_at=datetime.utcnow().isoformat()
    )
    
    try:
        from services.memory.client import get_memory
        memory = get_memory()
        
        if not memory.is_configured:
            logger.warning("Memory not configured, returning empty context")
            return packet
        
        # 1. Get user facts
        facts = memory.retrieve_facts(user_id, limit=max_facts)
        for fact in facts:
            packet.user_facts[fact.key] = fact.value
            if fact.key == "name":
                packet.user_name = str(fact.value).strip('"')
        
        # 2. Get recent conversation
        events = memory.get_recent_events(user_id, session_id, limit=max_recent)
        for event in reversed(events):  # Chronological order
            packet.recent_messages.append({
                "role": event.role,
                "content": event.content,
                "timestamp": str(event.created_at) if event.created_at else ""
            })
        
        # 3. Semantic search for relevant memories
        if include_semantic and query:
            chunks = memory.semantic_search(user_id, query, k=max_semantic)
            for chunk in chunks:
                packet.semantic_matches.append({
                    "text": chunk.chunk_text,
                    "source": chunk.source,
                    "similarity": chunk.similarity
                })
        
        # 4. Generate conversation summary if there are many messages
        if len(packet.recent_messages) > 5:
            # Simple summary: use first and last messages
            first = packet.recent_messages[0].get("content", "")[:50]
            last = packet.recent_messages[-1].get("content", "")[:50]
            packet.conversation_summary = f"Started with: '{first}...' → Currently: '{last}...'"
        
        logger.info(
            f"Context built: {len(packet.user_facts)} facts, "
            f"{len(packet.recent_messages)} messages, "
            f"{len(packet.semantic_matches)} semantic matches"
        )
        
    except Exception as e:
        logger.error(f"Context builder failed: {e}")
    
    return packet


def get_quick_context(user_id: str = "default", session_id: str = "default") -> str:
    """
    Get a quick context string for simple use cases.
    
    Returns formatted string suitable for prompt injection.
    """
    packet = build_context(user_id, session_id, "", include_semantic=False)
    return packet.to_prompt_string()
