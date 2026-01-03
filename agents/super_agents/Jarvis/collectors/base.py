from typing import Dict, Any, List
from abc import ABC, abstractmethod
from ..core.scope import ScopeManager

class BaseCollector(ABC):
    """
    Abstract Base Class for all Intelligence Collectors.
    Enforces Scope checks before running.
    """
    
    def __init__(self, scope_manager: ScopeManager):
        self.scope = scope_manager

    def run(self, target: str, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Public entry point. Checks scope, then calls _collect().
        """
        if not self.scope.validate_target(target):
            return [{"error": "Scope Violation", "target": target}]
            
        print(f"[{self.__class__.__name__}] Running on {target}...")
        return self._collect(target, options or {})

    @abstractmethod
    def _collect(self, target: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Actual implementation logic.
        """
        pass
