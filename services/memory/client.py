"""
Athena Memory Client - Unified Memory API
==========================================
Single interface for all memory operations:
- Event logging (conversations, tool calls)
- Fact storage (user preferences, profile)
- Semantic search (embeddings-based retrieval)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import requests

# Lazy imports to avoid circular dependencies
_settings = None
_logger = None

def _get_settings():
    global _settings
    if _settings is None:
        from core.settings import get_settings
        _settings = get_settings()
    return _settings

def _get_logger():
    global _logger
    if _logger is None:
        from core.logging import get_logger
        _logger = get_logger("athena.memory")
    return _logger


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Event:
    """A single memory event (conversation turn, tool call, etc.)"""
    id: int
    user_id: str
    session_id: str
    role: str  # user, assistant, system, tool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class Fact:
    """A durable fact about the user."""
    id: int
    user_id: str
    key: str
    value: Any
    category: str = "preference"
    confidence: float = 1.0
    source: str = "inference"
    updated_at: Optional[datetime] = None


@dataclass 
class Chunk:
    """A text chunk with embedding for semantic search."""
    id: int
    user_id: str
    source: str
    chunk_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    similarity: float = 0.0


# =============================================================================
# MEMORY STORE
# =============================================================================

class MemoryStore:
    """
    Unified memory API for Athena.
    
    Singleton pattern - use get_memory() to access.
    All methods use Supabase REST API directly (no SDK dependency).
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        settings = _get_settings()
        self.url = settings.supabase_url
        self.key = settings.supabase_key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        self._initialized = True
    
    @property
    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.url and self.key)
    
    def _request(self, method: str, endpoint: str, 
                 data: Dict = None, params: Dict = None) -> Optional[Any]:
        """Make a REST request to Supabase."""
        logger = _get_logger()
        
        url = f"{self.url}/rest/v1/{endpoint}"
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{param_str}"
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=self.headers, timeout=10)
            elif method == "POST":
                headers = {**self.headers, "Prefer": "return=representation"}
                resp = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PATCH":
                headers = {**self.headers, "Prefer": "return=representation"}
                resp = requests.patch(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, headers=self.headers, timeout=10)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            if resp.status_code in [200, 201]:
                return resp.json() if resp.text else None
            else:
                logger.error(f"Supabase error: {resp.status_code} - {resp.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    # =========================================================================
    # EVENT METHODS
    # =========================================================================
    
    def write_event(self, user_id: str, session_id: str, role: str,
                    content: str, metadata: Dict = None) -> Optional[int]:
        """
        Append an event to memory_events.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            role: One of 'user', 'assistant', 'system', 'tool'
            content: The message/action content
            metadata: Optional extra data
            
        Returns:
            The event ID if successful, None otherwise
        """
        if not self.is_configured:
            return None
            
        data = {
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata_json": metadata or {}
        }
        
        result = self._request("POST", "memory_events", data=data)
        if result and len(result) > 0:
            return result[0].get("id")
        return None
    
    def get_recent_events(self, user_id: str, session_id: str = None,
                          limit: int = 20) -> List[Event]:
        """
        Get recent events for a user/session.
        
        Args:
            user_id: User identifier
            session_id: Optional session filter
            limit: Max events to return
            
        Returns:
            List of Event objects, newest first
        """
        if not self.is_configured:
            return []
        
        params = {
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(limit)
        }
        if session_id:
            params["session_id"] = f"eq.{session_id}"
        
        result = self._request("GET", "memory_events", params=params)
        if not result:
            return []
        
        events = []
        for row in result:
            events.append(Event(
                id=row.get("id"),
                user_id=row.get("user_id"),
                session_id=row.get("session_id"),
                role=row.get("role"),
                content=row.get("content"),
                metadata=row.get("metadata_json", {}),
                created_at=row.get("created_at")
            ))
        return events
    
    # =========================================================================
    # FACT METHODS
    # =========================================================================
    
    def upsert_fact(self, user_id: str, key: str, value: Any,
                    category: str = "preference", 
                    confidence: float = 1.0,
                    source: str = "inference") -> Optional[int]:
        """
        Upsert a fact into memory_facts.
        
        Args:
            user_id: User identifier
            key: Unique key for this fact
            value: The fact value (will be JSON-serialized)
            category: One of 'preference', 'personal', 'goal', 'system'
            confidence: Confidence score 0-1
            source: Source of the fact
            
        Returns:
            The fact ID if successful, None otherwise
        """
        if not self.is_configured:
            return None
        
        # Use upsert via Prefer header
        data = {
            "user_id": user_id,
            "key": key,
            "value_json": value if isinstance(value, (dict, list)) else json.dumps(value),
            "category": category,
            "confidence": confidence,
            "source": source
        }
        
        headers = {
            **self.headers,
            "Prefer": "return=representation,resolution=merge-duplicates"
        }
        
        try:
            resp = requests.post(
                f"{self.url}/rest/v1/memory_facts",
                headers=headers,
                json=data,
                timeout=10
            )
            if resp.status_code in [200, 201]:
                result = resp.json()
                return result[0].get("id") if result else None
        except Exception as e:
            _get_logger().error(f"upsert_fact failed: {e}")
        return None
    
    def retrieve_facts(self, user_id: str, keys: List[str] = None,
                       category: str = None, limit: int = 50) -> List[Fact]:
        """
        Retrieve facts for a user.
        
        Args:
            user_id: User identifier
            keys: Optional list of specific keys to retrieve
            category: Optional category filter
            limit: Max facts to return
            
        Returns:
            List of Fact objects
        """
        if not self.is_configured:
            return []
        
        params = {
            "user_id": f"eq.{user_id}",
            "limit": str(limit),
            "order": "updated_at.desc"
        }
        if keys:
            params["key"] = f"in.({','.join(keys)})"
        if category:
            params["category"] = f"eq.{category}"
        
        result = self._request("GET", "memory_facts", params=params)
        if not result:
            return []
        
        facts = []
        for row in result:
            facts.append(Fact(
                id=row.get("id"),
                user_id=row.get("user_id"),
                key=row.get("key"),
                value=row.get("value_json"),
                category=row.get("category", "preference"),
                confidence=row.get("confidence", 1.0),
                source=row.get("source", "inference"),
                updated_at=row.get("updated_at")
            ))
        return facts
    
    def get_fact(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get a single fact value by key."""
        facts = self.retrieve_facts(user_id, keys=[key], limit=1)
        if facts:
            return facts[0].value
        return default
    
    # =========================================================================
    # EMBEDDING METHODS
    # =========================================================================
    
    def embed_and_store(self, user_id: str, source: str, text: str,
                        metadata: Dict = None) -> Optional[int]:
        """
        Embed text and store as a memory chunk.
        
        Args:
            user_id: User identifier
            source: Source type ('conversation', 'document', 'note')
            text: Text to embed
            metadata: Optional extra data
            
        Returns:
            The chunk ID if successful, None otherwise
        """
        if not self.is_configured:
            return None
        
        # Get embedding
        try:
            from services.memory.embeddings import get_embeddings_provider
            provider = get_embeddings_provider()
            embeddings = provider.embed([text])
            if not embeddings:
                return None
            embedding = embeddings[0]
        except Exception as e:
            _get_logger().error(f"Embedding failed: {e}")
            return None
        
        data = {
            "user_id": user_id,
            "source": source,
            "chunk_text": text,
            "embedding": embedding,
            "metadata_json": metadata or {}
        }
        
        result = self._request("POST", "memory_chunks", data=data)
        if result and len(result) > 0:
            return result[0].get("id")
        return None
    
    def semantic_search(self, user_id: str, query: str, k: int = 8,
                        threshold: float = 0.7) -> List[Chunk]:
        """
        Search memory chunks by semantic similarity.
        
        Args:
            user_id: User identifier
            query: Search query
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of Chunk objects with similarity scores
        """
        if not self.is_configured:
            return []
        
        # Get query embedding
        try:
            from services.memory.embeddings import get_embeddings_provider
            provider = get_embeddings_provider()
            embeddings = provider.embed([query])
            if not embeddings:
                return []
            query_embedding = embeddings[0]
        except Exception as e:
            _get_logger().error(f"Query embedding failed: {e}")
            return []
        
        # Call RPC function
        try:
            resp = requests.post(
                f"{self.url}/rest/v1/rpc/match_memory_chunks",
                headers=self.headers,
                json={
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": k,
                    "filter_user_id": user_id
                },
                timeout=15
            )
            if resp.status_code != 200:
                _get_logger().error(f"Semantic search failed: {resp.text}")
                return []
            
            result = resp.json()
            chunks = []
            for row in result:
                chunks.append(Chunk(
                    id=row.get("id"),
                    user_id=row.get("user_id"),
                    source=row.get("source"),
                    chunk_text=row.get("chunk_text"),
                    metadata=row.get("metadata_json", {}),
                    similarity=row.get("similarity", 0.0)
                ))
            return chunks
            
        except Exception as e:
            _get_logger().error(f"Semantic search error: {e}")
            return []
    
    # =========================================================================
    # LEGACY COMPATIBILITY
    # =========================================================================
    
    def log_interaction(self, user_input: str, athena_response: str,
                        summary: str = None, source: str = "telegram") -> bool:
        """
        Legacy method for logging interactions.
        
        Wraps write_event for backward compatibility with existing code.
        """
        user_event = self.write_event(
            user_id="default",
            session_id="default",
            role="user",
            content=user_input,
            metadata={"source": source}
        )
        
        assistant_event = self.write_event(
            user_id="default",
            session_id="default",
            role="assistant",
            content=athena_response,
            metadata={"source": source, "summary": summary}
        )
        
        return user_event is not None and assistant_event is not None
    
    def get_context(self, limit: int = 5) -> str:
        """
        Legacy method for getting conversation context.
        
        Returns formatted string of recent conversations.
        """
        events = self.get_recent_events("default", limit=limit * 2)
        
        if not events:
            return ""
        
        # Reverse to get chronological order
        events = list(reversed(events))
        
        lines = []
        for event in events:
            role = "User" if event.role == "user" else "Athena"
            lines.append(f"{role}: {event.content[:200]}")
        
        return "\n".join(lines)
    
    def get_user_profile(self) -> Dict[str, Any]:
        """
        Legacy method for getting user profile facts.
        """
        facts = self.retrieve_facts("default", limit=50)
        
        profile = {}
        for fact in facts:
            profile[fact.key] = fact.value
        
        return profile


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

def get_memory() -> MemoryStore:
    """Get the singleton MemoryStore instance."""
    return MemoryStore()
