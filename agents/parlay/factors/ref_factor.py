"""
HAKARI MODULE: OFFICIATING IMPACT (Ref Factor)
-----------------------------------------------
Scrapes or assumes daily crew assignments to adjust projections based on
referee tendencies (Whistle Index).

Logic:
- Tight Whistle (Index > 7): +1.08x Boost to FT-dependent Overs.
- Loose Whistle (Index < 3): 0.95x Fade to Points/FT props.
- Specific Refs: Scott Foster, Tony Brothers, Mousa Dagher -> High Impact.
"""

import logging

# Named Refs with known tendencies (Simulated DB)
# In production, this would be updated via Selenium scrape.
HIGH_FPG_REFS = ["Scott Foster", "Tony Brothers", "Mousa Dagher", "Ben Taylor"]
LOW_FPG_REFS = ["Bill Kennedy", "Pat Fraher"]

class RefereeModule:
    """
    Manages the 'Ref Factor' adjustments.
    """
    def __init__(self, crew_data=None):
        """
        Args:
            crew_data (dict): Optional manual injection of crew data.
                              Format: {'game_id': ['Ref Name 1', 'Ref Name 2', ...]}
        """
        self.crew_data = crew_data or {}
        self.logger = logging.getLogger("Hakari.RefFactor")

    def get_whistle_index(self, crew_names):
        """
        Calculates a 'Whistle Index' (0-10) based on the crew.
        Base is 5.0.
        """
        index = 5.0
        
        if not crew_names:
            return index

        for ref in crew_names:
            if ref in HIGH_FPG_REFS:
                index += 2.5
            elif ref in LOW_FPG_REFS:
                index -= 1.5
        
        # Cap at 0-10
        return max(0.0, min(10.0, index))

    def get_ref_multiplier(self, crew_names, stat_type, player_style="NEUTRAL"):
        """
        Returns the projection multiplier based on the crew.

        Args:
            crew_names (list): List of referee names.
            stat_type (str): 'points', 'rebounds', etc.
            player_style (str): 'FT_DEPENDENT', 'DRIVER', or 'NEUTRAL'.
        
        Returns:
            float: Multiplier (e.g., 1.08).
        """
        # Only impacts Points and Free Throws (and maybe fouls if we tracked that)
        if stat_type not in ['points', 'ftm', 'fantasy']:
            return 1.0

        whistle_index = self.get_whistle_index(crew_names)
        
        # 1. Tight Whistle Trigger (> 7)
        if whistle_index > 7.0:
            if player_style in ['FT_DEPENDENT', 'DRIVER']:
                self.logger.info(f"Ref Factor: TIGHT WHISTLE ({whistle_index}) -> Boosting {stat_type}")
                return 1.08 # +8% Boost
            else:
                 return 1.02 # Small general boost for scoring environment

        # 2. Loose Whistle Trigger (< 3)
        if whistle_index < 3.0:
            self.logger.info(f"Ref Factor: LOOSE WHISTLE ({whistle_index}) -> Fading {stat_type}")
            return 0.95 # -5% Fade (Let them play = less FTs)

        return 1.0
