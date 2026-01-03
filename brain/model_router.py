"""
Athena Model Router
===================
Chooses between local and cloud models based on task complexity,
privacy requirements, and cost constraints.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

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
        _logger = get_logger("athena.model_router")
    return _logger


class ModelPreference(Enum):
    """Model preference options."""
    LOCAL = "local"
    CLOUD = "cloud"
    AUTO = "auto"


@dataclass
class ModelChoice:
    """Result of model routing decision."""
    use_local: bool
    model_name: str
    reason: str


class ModelRouter:
    """
    Routes requests to appropriate AI models.
    
    Decision factors:
    - Task complexity (simple chat vs. complex reasoning)
    - Privacy level (sensitive data stays local)
    - Cost constraints (daily budget)
    - Explicit user preference
    """
    
    def __init__(self):
        self.settings = _get_settings()
    
    def choose_model(
        self,
        task_type: str = "chat",
        complexity: str = "medium",
        privacy_level: str = "normal",
        prefer: Optional[str] = None
    ) -> ModelChoice:
        """
        Choose the best model for a task.
        
        Args:
            task_type: Type of task ('chat', 'reasoning', 'coding', 'summarize')
            complexity: Task complexity ('low', 'medium', 'high')
            privacy_level: Privacy requirement ('normal', 'sensitive', 'private')
            prefer: Explicit preference ('local', 'cloud', 'auto' or None)
            
        Returns:
            ModelChoice with selected model
        """
        logger = _get_logger()
        
        # Handle explicit preference
        if prefer == "local":
            return ModelChoice(
                use_local=True,
                model_name=self.settings.default_model_local,
                reason="Explicit local preference"
            )
        
        if prefer == "cloud":
            if not self._is_cloud_available():
                return ModelChoice(
                    use_local=True,
                    model_name=self.settings.default_model_local,
                    reason="Cloud requested but not available, falling back to local"
                )
            return ModelChoice(
                use_local=False,
                model_name=self.settings.default_model_cloud,
                reason="Explicit cloud preference"
            )
        
        # Privacy gate - sensitive data must stay local
        if privacy_level in ("sensitive", "private"):
            return ModelChoice(
                use_local=True,
                model_name=self.settings.default_model_local,
                reason=f"Privacy level '{privacy_level}' requires local processing"
            )
        
        # Cost gate - check budget
        if self._is_budget_exceeded():
            return ModelChoice(
                use_local=True,
                model_name=self.settings.default_model_local,
                reason="Daily budget exceeded, using local model"
            )
        
        # Task-based routing
        if task_type in ("coding", "reasoning") or complexity == "high":
            if self._is_cloud_available():
                return ModelChoice(
                    use_local=False,
                    model_name=self.settings.default_model_cloud,
                    reason=f"Complex {task_type} task requires cloud model"
                )
        
        if task_type == "summarize" and complexity != "low":
            if self._is_cloud_available():
                return ModelChoice(
                    use_local=False,
                    model_name=self.settings.default_model_cloud,
                    reason="Summarization benefits from cloud model"
                )
        
        # Default: prefer local for simple tasks
        if complexity == "low":
            return ModelChoice(
                use_local=True,
                model_name=self.settings.default_model_local,
                reason="Simple task can be handled locally"
            )
        
        # Medium complexity: use cloud if available
        if self._is_cloud_available():
            return ModelChoice(
                use_local=False,
                model_name=self.settings.default_model_cloud,
                reason="Default to cloud for medium complexity"
            )
        
        # Fallback to local
        return ModelChoice(
            use_local=True,
            model_name=self.settings.default_model_local,
            reason="Cloud not available, using local"
        )
    
    def _is_cloud_available(self) -> bool:
        """Check if cloud models are configured."""
        return bool(self.settings.effective_gemini_key or self.settings.openai_api_key)
    
    def _is_budget_exceeded(self) -> bool:
        """Check if daily budget is exceeded."""
        try:
            from core.telemetry import check_budget
            budget = check_budget()
            return not budget["ok"]
        except Exception:
            return False
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimation."""
        # GPT-style: ~4 chars per token
        return len(text) // 4
    
    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """
        Estimate cost for a request.
        
        Rough pricing (as of 2024):
        - GPT-4o: $5/1M input, $15/1M output
        - Gemini Flash: ~$0.075/1M input, ~$0.30/1M output
        - Gemini Pro: ~$0.50/1M input, ~$1.50/1M output
        """
        model_lower = model.lower()
        
        if "flash" in model_lower:
            cost = (tokens_in * 0.075 + tokens_out * 0.30) / 1_000_000
        elif "pro" in model_lower:
            cost = (tokens_in * 0.50 + tokens_out * 1.50) / 1_000_000
        elif "gpt-4" in model_lower:
            cost = (tokens_in * 5.0 + tokens_out * 15.0) / 1_000_000
        else:
            cost = 0.0  # Local models are free
        
        return round(cost, 6)


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_router_instance: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    """Get the singleton ModelRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance


def choose_model(**kwargs) -> ModelChoice:
    """Convenience function to choose a model."""
    return get_model_router().choose_model(**kwargs)
