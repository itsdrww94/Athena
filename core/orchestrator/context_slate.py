from typing import Dict, Any, List
from core.memory.manager import MemoryManager

class ContextSlateBuilder:
    """
    Constructs the 'State of Mind' for Athena before generating a response.
    Borrows 'Context Slate' concept from the spec.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        
    def build_slate(self, user_query: str, active_modes: List[str] = []) -> str:
        """
        Assemble the Context Slate.
        Returns a formatted string or JSON to inject into System Prompt.
        """
        
        # 1. Retrieve Relevant Facts (Semantic)
        facts = self.memory.get_semantic(query=user_query)
        facts_str = "\n".join([f"- {f.content}" for f in facts]) if facts else "None relevant."
        
        # 2. Retrieve Recent History (Episodic)
        # Limit to last 3 days for conciseness
        episodes = self.memory.get_recent_episodes(limit=3)
        history_str = ""
        for ep in episodes:
            history_str += f"Date: {ep.date} | Summary: {ep.summary}\n"
        if not history_str:
            history_str = "No recent history available."
            
        # 3. Format Slate
        slate = f"""
[SEMANTIC MEMORY - Known Facts]
{facts_str}

[EPISODIC MEMORY - Recent Context]
{history_str}

[CURRENT MODES]
Active: {', '.join(active_modes) if active_modes else 'Standard'}
"""
        return slate
