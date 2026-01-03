"""
HAKARI MODULE: VETERAN FATIGUE (The B2B Fade)
----------------------------------------------
Applies penalties to older players on back-to-back sets.

Logic:
- Age >= 33 AND Days Rest == 0.
- Base Fade: 0.90x (10% drop).
- Road Penalty: If 'Away' for both legs (approximated), additional 0.95x.
"""

import logging

class FatigueModule:
    """
    Manages the 'Veteran Fade' logic.
    """
    def __init__(self):
        self.logger = logging.getLogger("Hakari.Fatigue")

    def get_fatigue_multiplier(self, player_age, days_rest, is_road_game, prev_game_road=False):
        """
        Calculates the fatigue multiplier.

        Args:
            player_age (int): Player's age.
            days_rest (int): Days of rest (0 = B2B).
            is_road_game (bool): True if current game is Away.
            prev_game_road (bool): True if previous game was Away (optional context).
        
        Returns:
            float: Multiplier (e.g., 0.88).
        """
        if days_rest > 0:
            return 1.0

        # Logic only applies to B2B (Rest == 0)
        
        # 1. Age Filter (Senior Developer Adjustment: Strict 33+)
        if player_age < 33:
            return 1.0

        # 2. Base Fade
        multiplier = 0.88 # 12% reduction for the "old man" fade
        reason = "Veteran B2B"

        # 3. Road Penalty (Simulating the 'Double Road' fatigue)
        # If we know the previous game was on the road, or just assuming 'is_road_game' implies travel stress
        if is_road_game:
            multiplier *= 0.95 # Composite further reduction
            reason += " + Road Travel"

        self.logger.info(f"Fatigue Factor: {reason} (Age {player_age}) -> x{multiplier:.2f}")
        return multiplier
