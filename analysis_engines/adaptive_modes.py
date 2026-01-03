#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    A D A P T I V E   M O D E S                                ║
║                  "The Chameleon Core"                                         ║
║                                                                               ║
║  Makes Athena adapt her response style based on detected context              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Modes:
- FOCUS: Short, structured, minimal fluff (detected: work hours, focus music)
- COACH: Encouraging + accountability (detected: fitness/goal discussions)
- CHILL: Lighter tone, reflection prompts (detected: evening, wind-down music)
- PLANNER: Next actions, deadlines, budget-aware (detected: planning keywords)
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# =============================================================================
# MODE DEFINITIONS
# =============================================================================

MODES = {
    "focus": {
        "name": "Focus Mode",
        "icon": "🎯",
        "style": "Short, structured, minimal fluff. Get to the point.",
        "traits": ["concise", "bulleted", "action-oriented", "no small talk"],
        "example": "Here's what you need:\n1. X\n2. Y\nDone.",
        "triggers": ["work hours", "focus playlist", "coding", "writing", "studying"]
    },
    "coach": {
        "name": "Coach Mode",
        "icon": "💪",
        "style": "Encouraging, accountability-focused, motivational.",
        "traits": ["supportive", "progress-tracking", "celebrates wins", "gentle pushes"],
        "example": "You've got this! Let's break it down:\n- Step 1: X\n- You already did Y, that's huge 🔥",
        "triggers": ["fitness", "gym", "goals", "habits", "progress", "accountability"]
    },
    "chill": {
        "name": "Chill Mode",
        "icon": "🌙",
        "style": "Relaxed, reflective, lighter tone. Good for winding down.",
        "traits": ["conversational", "reflective", "unhurried", "gentle suggestions"],
        "example": "Nice work today. Anything on your mind, or just vibing?",
        "triggers": ["evening", "wind-down music", "reflection", "journaling", "casual"]
    },
    "planner": {
        "name": "Planner Mode", 
        "icon": "📋",
        "style": "Next actions, deadlines, budget-aware. Structured planning.",
        "traits": ["deadline-focused", "budget-conscious", "prioritized", "calendar-aware"],
        "example": "This week:\n- [ ] Task A (due Mon)\n- [ ] Task B ($50 budget)\nTotal: 3 items, ~2h work",
        "triggers": ["planning", "schedule", "budget", "week", "organize", "priorities"]
    }
}

# =============================================================================
# MODE DETECTOR
# =============================================================================

class ModeDetector:
    """Detects which mode Athena should use based on context."""
    
    def __init__(self):
        self.current_mode = "default"
        self.mode_history = []
        
    def detect_from_time(self) -> Optional[str]:
        """Detect mode based on time of day."""
        hour = datetime.now().hour
        
        if 6 <= hour < 9:
            return "focus"  # Morning = get stuff done
        elif 9 <= hour < 17:
            return None  # Work hours = context-dependent
        elif 17 <= hour < 21:
            return "planner"  # Evening = plan tomorrow
        elif hour >= 21 or hour < 6:
            return "chill"  # Night = wind down
        
        return None
    
    def detect_from_message(self, message: str) -> Optional[str]:
        """Detect mode based on user's message content."""
        message_lower = message.lower()
        
        # Check each mode's triggers
        for mode_key, mode_def in MODES.items():
            for trigger in mode_def["triggers"]:
                if trigger in message_lower:
                    return mode_key
        
        return None
    
    def detect_from_patterns(self, user_data: Dict) -> Optional[str]:
        """Detect mode based on stored user patterns."""
        # Check if we have patterns data
        patterns = user_data.get("patterns_detected", [])
        current_activity = user_data.get("current_activity", "")
        
        # If user is typically in focus mode at this time, suggest it
        # This would be enhanced with actual pattern data
        
        return None
    
    def get_mode(self, message: str = "", user_data: Dict = None) -> Dict:
        """
        Get the recommended mode based on all signals.
        
        Priority:
        1. Explicit mode request ("be more coach-like")
        2. Message content triggers
        3. Time of day
        4. Default
        """
        user_data = user_data or {}
        
        # 1. Check for explicit mode request
        message_lower = message.lower()
        for mode_key in MODES.keys():
            if f"{mode_key} mode" in message_lower:
                self.current_mode = mode_key
                return MODES[mode_key]
        
        # 2. Detect from message
        detected = self.detect_from_message(message)
        if detected:
            self.current_mode = detected
            return MODES[detected]
        
        # 3. Detect from patterns
        detected = self.detect_from_patterns(user_data)
        if detected:
            self.current_mode = detected
            return MODES[detected]
        
        # 4. Detect from time
        detected = self.detect_from_time()
        if detected:
            self.current_mode = detected
            return MODES[detected]
        
        # 5. Default: no specific mode
        return {
            "name": "Default",
            "icon": "✨",
            "style": "Balanced, conversational, helpful.",
            "traits": ["adaptable", "friendly", "precise"]
        }
    
    def get_system_prompt_modifier(self, mode: Dict) -> str:
        """Generate a system prompt modifier for the current mode."""
        return f"""
## Current Adaptation Mode: {mode['icon']} {mode['name']}

Style: {mode['style']}

Traits to embody: {', '.join(mode.get('traits', []))}

Adjust your responses accordingly. If the user seems to want a different mode, switch.
"""


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

def get_mode_for_context(message: str = "", user_profile: Dict = None) -> Dict:
    """
    Main entry point for mode detection.
    
    Usage in athena_cli.py:
        from analysis_engines.adaptive_modes import get_mode_for_context
        mode = get_mode_for_context(user_input, user_profile)
        # Add mode['system_modifier'] to the prompt
    """
    detector = ModeDetector()
    mode = detector.get_mode(message, user_profile or {})
    mode["system_modifier"] = detector.get_system_prompt_modifier(mode)
    return mode


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    detector = ModeDetector()
    
    test_messages = [
        "I need to focus on this code",
        "How's my progress on my fitness goals?",
        "Just want to chill and reflect",
        "Help me plan my week",
        "What's up?"
    ]
    
    print("🎭 ADAPTIVE MODES TEST")
    print("=" * 50)
    
    for msg in test_messages:
        mode = detector.get_mode(msg)
        print(f"\n📝 '{msg}'")
        print(f"   → {mode['icon']} {mode['name']}")
        print(f"   Style: {mode['style']}")
