"""
Athena Core Settings - Centralized Configuration
================================================
Uses Pydantic BaseSettings for validated, type-safe configuration.
All environment variables are loaded from .env and validated.
"""

import os
from typing import Optional
from functools import lru_cache

# First, try pydantic-settings (Pydantic v2), fallback to pydantic (v1)
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class AthenaSettings(BaseSettings):
    """
    Central configuration for Athena.
    
    All settings are loaded from environment variables.
    Use get_settings() to access the singleton instance.
    """
    
    # =========================================================================
    # DATABASE & CLOUD SERVICES
    # =========================================================================
    supabase_url: str = ""
    supabase_key: str = ""  # Service role key for full access
    n8n_webhook_url: Optional[str] = None
    google_application_credentials: Optional[str] = None
    google_cloud_storage_bucket: Optional[str] = None
    google_cloud_project: Optional[str] = None
    
    # =========================================================================
    # AI API KEYS
    # =========================================================================
    gemini_api_key: Optional[str] = None
    google_api_key: Optional[str] = None  # Fallback for Gemini
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # =========================================================================
    # MODEL PREFERENCES
    # =========================================================================
    default_model_local: str = "llama3.2"
    default_model_cloud: str = "gemini-2.0-flash-exp"
    embeddings_provider: str = "google"  # google|openai|local
    memory_embed_dim: int = 768  # Dimension for embedding vectors
    
    # =========================================================================
    # TELEGRAM
    # =========================================================================
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # =========================================================================
    # NOTION
    # =========================================================================
    notion_api_key: Optional[str] = None
    notion_journal_db_id: Optional[str] = None
    
    # =========================================================================
    # SOCIAL MEDIA
    # =========================================================================
    ig_username: Optional[str] = None
    ig_password: Optional[str] = None
    twitter_username: Optional[str] = None
    twitter_password: Optional[str] = None
    # ENVIRONMENT & BEHAVIOR
    # =========================================================================
    athena_env: str = "dev"  # dev|prod
    athena_skip_sync: bool = False  # Skip startup sync for faster loading
    athena_enable_social_posting: bool = False  # Gate for social media posting
    athena_debug: bool = False  # Enable verbose debug logging
    
    # =========================================================================
    # COST CONTROLS
    # =========================================================================
    max_cost_per_day: float = 5.00  # USD
    max_tokens_per_request: int = 8000
    
    # =========================================================================
    # SERVER CONFIGURATION
    # =========================================================================
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields for forward compatibility
        extra = "ignore"
    
    @property
    def is_supabase_configured(self) -> bool:
        """Check if Supabase credentials are present."""
        return bool(self.supabase_url and self.supabase_key)
    
    @property
    def is_telegram_configured(self) -> bool:
        """Check if Telegram bot is configured."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)
    
    @property
    def is_gemini_configured(self) -> bool:
        """Check if Gemini API is configured."""
        return bool(self.gemini_api_key or self.google_api_key)
    
    @property
    def effective_gemini_key(self) -> Optional[str]:
        """Get the Gemini API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
        return self.gemini_api_key or self.google_api_key
    
    @property
    def is_openai_configured(self) -> bool:
        """Check if OpenAI API is configured."""
        return bool(self.openai_api_key)


# Singleton accessor with caching
@lru_cache()
def get_settings() -> AthenaSettings:
    """
    Get the singleton AthenaSettings instance.
    
    Uses lru_cache to ensure only one instance is created.
    """
    return AthenaSettings()


# Convenience function for quick checks
def is_production() -> bool:
    """Check if running in production mode."""
    return get_settings().athena_env == "prod"
