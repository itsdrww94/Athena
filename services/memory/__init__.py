"""
Athena Memory Service
=====================
Unified memory API for all Athena components.

Usage:
    from services.memory import get_memory
    
    memory = get_memory()
    memory.write_event(user_id, session_id, "user", "Hello!")
    context = memory.build_context(user_id, session_id, "What's my name?")
"""

from services.memory.client import MemoryStore, get_memory, Event, Fact, Chunk
from services.memory.context_builder import build_context, ContextPacket

__all__ = [
    "MemoryStore",
    "get_memory",
    "Event",
    "Fact", 
    "Chunk",
    "build_context",
    "ContextPacket",
]
