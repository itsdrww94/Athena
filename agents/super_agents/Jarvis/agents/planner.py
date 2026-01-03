from typing import List, Dict, Any, Set
from ..core.scope import ScopeManager

class PlannerAgent:
    """
    Agent 2: The Strategist.
    Decides 'What do we do with this evidence?'.
    Generates the 'Next Best Actions' queue.
    """
    
    def __init__(self, scope_manager: ScopeManager):
        self.scope = scope_manager
        # Define policies: EntityType -> [Allowed Actions]
        self.POLICY_MAP = {
            "email": ["breach_check", "domain_lookup", "social_lookup", "osint_scan", "knowledge_search"],
            "username": ["social_enum", "repo_search", "osint_scan", "knowledge_search"],
            "image": ["exif_scan", "reverse_image_search"],
            "vin": ["specs_lookup", "salvage_check", "knowledge_search"],
            "url": ["archive_lookup", "tech_stack_scan", "osint_scan", "knowledge_search"],
            "ip": ["osint_scan", "knowledge_search"],
            "domain": ["osint_scan", "knowledge_search"]
        }

    def generate_plan(self, entities: List[Dict[str, Any]], history: Set[str]) -> List[Dict[str, Any]]:
        """
        Consumes entities. Produces a prioritized queue of actions.
        Checks Scope and History (to avoid loops).
        """
        action_queue = []
        
        for entity in entities:
            e_type = entity.get("type")
            e_value = entity.get("value")
            
            if not e_type or not e_value:
                continue
                
            possible_actions = self.POLICY_MAP.get(e_type, [])
            
            for action in possible_actions:
                # 1. Deduplication check
                action_id = f"{action}:{e_value}"
                if action_id in history:
                    continue
                    
                # 2. Scope check (Is this action allowed on this target?)
                if not self.scope.validate_target(e_value):
                    # In strict mode, we might skip. In lab mode, maybe log and skip.
                    # For now, assume ScopeManager handles the heavy lifting of "Is this target allowlisted?"
                    # But also check if the *Action* is allowed.
                    continue

                if not self.scope.validate_action(action, {}):
                    continue

                # 3. Prioritize
                priority = self._get_priority(e_type, action)
                
                action_queue.append({
                    "id": action_id,
                    "action": action,
                    "target": e_value,
                    "priority": priority,
                    "entity_source": entity
                })
                
        # Sort by priority (Higher is better)
        return sorted(action_queue, key=lambda x: x["priority"], reverse=True)

    def _get_priority(self, e_type: str, action: str) -> int:
        """
        Simple heuristic for 'High Yield' actions.
        """
        high_yield = ["breach_check", "exif_scan"]
        if action in high_yield:
            return 10
        return 5
