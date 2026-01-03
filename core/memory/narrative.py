from typing import List, Dict, Any
from datetime import datetime, timedelta

from core.memory.manager import MemoryManager

class NarrativeGenerator:
    """
    Storyteller.
    Generates 'Weekly Narrative' reports from Episodic Memory.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        
    def generate_weekly_report(self) -> str:
        """
        Synthesize the last 7 days into a narrative.
        """
        # Get last 7 days
        episodes = self.memory.get_recent_episodes(limit=7)
        if not episodes:
            return "Not enough data for a weekly report yet."
            
        # Placeholder Logic (LLM would usually do this synthesis)
        # We will structure the prompt input here
        
        report = f"# 📅 Weekly Report ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        
        report += "## Key Logic\n"
        report += f"Analyzed {len(episodes)} days of activity.\n\n"
        
        report += "## Daily Recaps\n"
        for ep in episodes:
            report += f"- **{ep.date}**: {ep.summary}\n"
            
        report += "\n## Trends Detected\n"
        report += "- (Placeholder: Pattern Engine would insert trends here, e.g., 'Late Night Activity decreased by 10%')\n"
        
        return report
