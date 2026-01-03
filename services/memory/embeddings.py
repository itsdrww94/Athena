"""
Athena Embeddings Providers
===========================
Abstraction layer for embedding models.
Supports Google, OpenAI, and local (sentence-transformers) providers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import os

# Lazy imports
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
        _logger = get_logger("athena.embeddings")
    return _logger


class EmbeddingsProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts.
        
        Args:
            texts: List of strings to embed
            
        Returns:
            List of embedding vectors
        """
        pass


class GoogleEmbeddingsProvider(EmbeddingsProvider):
    """Google/Gemini embeddings provider."""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-004"):
        self.api_key = api_key or _get_settings().effective_gemini_key
        self.model = model
        self._dimension = 768  # Default for text-embedding-004
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            _get_logger().error("Google API key not configured")
            return []
        
        try:
            from google import genai
            
            client = genai.Client(api_key=self.api_key)
            embeddings = []
            
            # Process in batches to avoid rate limits
            batch_size = 20
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                for text in batch:
                    response = client.models.embed_content(
                        model=self.model,
                        content=text
                    )
                    if hasattr(response, 'embedding') and response.embedding:
                        embeddings.append(list(response.embedding.values))
                    elif hasattr(response, 'embeddings') and response.embeddings:
                        embeddings.append(list(response.embeddings[0].values))
                    else:
                        _get_logger().warning(f"Unexpected embedding response: {response}")
                        embeddings.append([0.0] * self._dimension)
            
            return embeddings
            
        except Exception as e:
            _get_logger().error(f"Google embedding failed: {e}")
            return []


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    """OpenAI embeddings provider."""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or _get_settings().openai_api_key
        self.model = model
        # Dimension depends on model
        self._dimension = 1536 if "large" in model else 768
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            _get_logger().error("OpenAI API key not configured")
            return []
        
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            embeddings = []
            for item in response.data:
                embeddings.append(item.embedding)
            
            return embeddings
            
        except Exception as e:
            _get_logger().error(f"OpenAI embedding failed: {e}")
            return []


class LocalEmbeddingsProvider(EmbeddingsProvider):
    """
    Local embeddings using sentence-transformers.
    
    Falls back to a simple stub if sentence-transformers isn't installed.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # Default for all-MiniLM-L6-v2
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def _load_model(self):
        if self._model is not None:
            return True
            
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            return True
        except ImportError:
            _get_logger().warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            return False
        except Exception as e:
            _get_logger().error(f"Failed to load local model: {e}")
            return False
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self._load_model():
            # Return zero vectors as fallback
            _get_logger().warning("Using zero-vector fallback for embeddings")
            return [[0.0] * self._dimension for _ in texts]
        
        try:
            embeddings = self._model.encode(texts, show_progress_bar=False)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            _get_logger().error(f"Local embedding failed: {e}")
            return []


# =============================================================================
# PROVIDER FACTORY
# =============================================================================

_provider_instance: Optional[EmbeddingsProvider] = None

def get_embeddings_provider() -> EmbeddingsProvider:
    """
    Get the configured embeddings provider.
    
    Reads from settings.embeddings_provider to choose:
    - 'google': Google/Gemini embeddings
    - 'openai': OpenAI embeddings
    - 'local': Local sentence-transformers
    
    Returns:
        EmbeddingsProvider instance
    """
    global _provider_instance
    
    if _provider_instance is not None:
        return _provider_instance
    
    settings = _get_settings()
    provider_name = settings.embeddings_provider.lower()
    
    if provider_name == "google":
        if settings.effective_gemini_key:
            _provider_instance = GoogleEmbeddingsProvider()
        else:
            _get_logger().warning("Google API key not set, falling back to local")
            _provider_instance = LocalEmbeddingsProvider()
            
    elif provider_name == "openai":
        if settings.openai_api_key:
            _provider_instance = OpenAIEmbeddingsProvider()
        else:
            _get_logger().warning("OpenAI API key not set, falling back to local")
            _provider_instance = LocalEmbeddingsProvider()
            
    else:  # local or any other value
        _provider_instance = LocalEmbeddingsProvider()
    
    return _provider_instance


def reset_provider():
    """Reset the cached provider (useful for testing)."""
    global _provider_instance
    _provider_instance = None
