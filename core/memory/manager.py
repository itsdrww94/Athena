import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger("athena.memory.manager")

# --- Contracts ---

class SemanticMemory(BaseModel):
    """Stable facts, preferences, and constraints."""
    fact_id: str
    category: str # preference, goal, constraint, relationship
    content: str
    confidence: float = 1.0
    source_ref: Optional[str] = None
    last_accessed: datetime = Field(default_factory=datetime.now)

class EpisodicMemory(BaseModel):
    """Daily Capsules and key episodes."""
    episode_id: str
    date: str
    summary: str
    highlights: Dict[str, Any]
    embeddings: Optional[List[float]] = None # For vector search

# --- Manager ---

class MemoryManager:
    """
    Manages the 'Brain' (Supabase implementation wrapper).
    Separates Semantic (Facts) from Episodic (History).
    """
    
    def __init__(self):
        import os
        from supabase import create_client, Client
        
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if url and key:
            self.client: Client = create_client(url, key)
            self.enabled = True
        else:
            logger.warning("Supabase credentials not found. Memory will be ephemeral.")
            self.enabled = False

    def add_semantic(self, content: str, category: str = "general") -> str:
        """Store a new fact."""
        if not self.enabled:
            return "ephemeral_id"
            
        data = {
            "content": content, 
            "category": category,
            "confidence": 1.0
        }
        try:
            res = self.client.table("memories_semantic").insert(data).execute()
            return res.data[0]['fact_id']
        except Exception as e:
            logger.error(f"Failed to add semantic memory: {e}")
            return "error"

    def get_semantic(self, query: str = None, context_tags: List[str] = None) -> List[SemanticMemory]:
        """
        Retrieve relevant facts. 
        """
        if not self.enabled:
            return []
            
        try:
            # Simple retrieval for now (TODO: Vector Search)
            query_builder = self.client.table("memories_semantic").select("*")
            if context_tags:
                # Placeholder for tag filtering
                pass
            
            res = query_builder.limit(10).execute()
            
            return [SemanticMemory(**item) for item in res.data]
        except Exception as e:
            logger.error(f"Failed to retrieve semantic memory: {e}")
            return []

    def add_episodic(self, capsule: Dict[str, Any]) -> str:
        """Store a Daily Capsule."""
        if not self.enabled:
            return "ephemeral_id"
            
        data = {
            "date": capsule.get("date"),
            "summary": capsule.get("summary"),
            "highlights": capsule.get("highlights", {})
        }
        try:
            res = self.client.table("memories_episodic").insert(data).execute()
            return res.data[0]['episode_id']
        except Exception as e:
            logger.error(f"Failed to add episodic memory: {e}")
            return "error"

    def get_recent_episodes(self, limit: int = 7) -> List[EpisodicMemory]:
        """Get the last N days (Working Memory)."""
        if not self.enabled:
            return []
            
        try:
            res = self.client.table("memories_episodic").select("*").order("date", desc=True).limit(limit).execute()
            return [EpisodicMemory(**item) for item in res.data]
        except Exception as e:
            logger.error(f"Failed to retrieve episodes: {e}")
            return [] # Return empty on error to prevent crash

    def search_episodes(self, query: str) -> List[EpisodicMemory]:
        """Find similar past days (Vector Search)."""
        # TODO: Implement pgvector match
        return []
