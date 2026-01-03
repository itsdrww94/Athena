"""
HAKARI MODULE: INCENTIVES (Bag Watch)
--------------------------------------
Scrapes or simulates performance-based contract escalators.
Targets players near the 65-game mark or PPG/APG milestones.
"""

import logging

class IncentiveModule:
    """
    Manages the 'Greed Multiplier' for contract incentives.
    """
    def __init__(self, incentive_data=None):
        """
        Args:
            incentive_data (dict): Manual injection of incentive data.
            Format: { 'player_id': { 'target_stat': 'AST', 'target_val': 8.0, 'current_val': 7.8, 'games_left': 5 } }
        """
        self.incentive_data = incentive_data or {} 
        self.logger = logging.getLogger("Hakari.Incentives")

    def calculate_greed_multiplier(self, player_id, stat_type):
        """
        Returns the multiplier if a player is chasing a bag.
        """
        # Ensure ID is string for lookup stability
        pid = str(player_id)
        player_incentives = self.incentive_data.get(pid)
        
        if not player_incentives:
            return 1.0

        target_stat = player_incentives.get('target_stat', '').lower()
        if stat_type.lower() != target_stat:
            return 1.0

        # Logic: If they are within 5% of the goal with < 10 games left
        current = player_incentives.get('current_val', 0)
        goal = player_incentives.get('target_val', 0)
        games_left = player_incentives.get('games_left', 82)

        # Div by zero guard
        if goal == 0: 
            return 1.0

        if current >= (goal * 0.95) and games_left <= 10:
            # The "Greed Multiplier"
            self.logger.info(f"Incentive Alert: Player {pid} chasing {target_stat} ({current}/{goal}) -> x1.15")
            return 1.15 
            
        return 1.0

class SeriesContextModule:
    """
    Manages series-based context adjustments (Playoffs, 3-0 Traps).
    """
    def __init__(self):
        self.logger = logging.getLogger("Hakari.SeriesContext")
        
    def get_minutes_adjustment(self, series_lead, location, archetype):
        """
        Adjusts projected minutes based on series context.
        
        Logic:
        - If team is up 3-0 and playing AWAY, they often let off the gas.
        - Starters sit early (x0.90), Bench plays more (x1.15).
        """
        min_mult = 1.0
        
        if series_lead == "3-0" and location == "AWAY":
            if archetype in ["ALPHA", "BETA", "BIG"]:
                 min_mult = 0.90 # Starters sit early
                 self.logger.info(f"Series Context: 3-0 Trap (Away) -> Fading Star Minutes x0.90")
            elif archetype == "ROLE_PLAYER":
                 min_mult = 1.15 # Bench plays more "Garbage Time"
                 self.logger.info(f"Series Context: 3-0 Trap (Away) -> Boosting Bench Minutes x1.15")
                 
        return min_mult

# =============================================================================
# TOOL 1: SLIP INGESTION (Image/Text -> Legs)
# =============================================================================

class SlipIngester:
    """
    Parses raw inputs (images/text) into structured leg data.
    """
    @staticmethod
    def parse_input(platform: str, raw_content: str, is_image: bool = False) -> list:
        """
        Parses input into a list of leg dictionaries.
        
        Args:
            platform: 'prizepicks', 'underdog'
            raw_content: OCR text or raw user text
            is_image: If True, assumes raw_content is image path (stubbed)
            
        Returns:
            [ { 'player': str, 'stat': str, 'line': float, 'side': 'OVER/UNDER' } ]
        """
        if is_image:
            # TODO: Integrate Google Gemini Vision here
            return [{"error": "Vision not yet connected", "raw": raw_content}]
        
        # Simple text parsing (Mock regex for prototype)
        # Format assumed: "LeBron James Points 25.5 OVER"
        legs = []
        lines = raw_content.split('\n')
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 4:
                # Naive parse
                side = parts[-1].upper()
                line_val = float(parts[-2])
                stat = parts[-3]
                player = " ".join(parts[:-3])
                
                legs.append({
                    "platform": platform,
                    "player": player,
                    "stat": PropNormalizer.normalize(stat),
                    "line": line_val,
                    "side": side,
                    "raw_text": line
                })
        return legs

# =============================================================================
# TOOL 2: PROP NORMALIZER
# =============================================================================

class PropNormalizer:
    """
    Canonicalizes stat names across platforms.
    """
    MAPPING = {
        'pts': 'points', 'points': 'points',
        'reb': 'rebounds', 'rebs': 'rebounds', 'rebounds': 'rebounds',
        'ast': 'assists', 'asts': 'assists', 'assists': 'assists',
        'pra': 'pra', 'pts+reb+ast': 'pra',
        '3pm': '3pm', 'threes': '3pm', '3pt': '3pm',
        'stl': 'steals', 'steals': 'steals',
        'blk': 'blocks', 'blocks': 'blocks',
        'turnovers': 'turnovers', 'to': 'turnovers'
    }

    @staticmethod
    def normalize(raw_stat: str) -> str:
        return PropNormalizer.MAPPING.get(raw_stat.lower().strip(), raw_stat.lower())

