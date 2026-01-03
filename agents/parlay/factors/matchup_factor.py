import logging

logger = logging.getLogger("Hakari.Factors.Matchup")

class MatchupFactor:
    """
    Stanford CS229 Matchup Logic
    ----------------------------
    Handles specific opponent-based adjustments:
    1. Chaos Factor (Turnover Rate)
    2. Glass Eater (Rebound Rate)
    """
    
    def __init__(self):
        pass

    def get_chaos_multiplier(self, stat_type, opponent_stats):
        """
        Chaos Factor: Boosts projections for players facing sloppy teams.
        Threshold: Opponent TOV% > 16.0
        """
        opp_tov_rate = opponent_stats.get('tov_rate', 0)
        
        if opp_tov_rate > 16.0:
            if stat_type == 'steals':
                logger.debug(f"Chaos Factor: Opp TOV% {opp_tov_rate:.1f} > 16.0 -> +15% steals")
                return 1.15
            elif stat_type == 'points':
                logger.debug(f"Chaos Factor: Opp TOV% {opp_tov_rate:.1f} > 16.0 -> +4% points")
                return 1.04
        
        return 1.0

    def get_glass_eater_multiplier(self, stat_type, opponent_stats):
        """
        Glass Eater: Adjusts rebounds based on opponent strength.
        """
        if stat_type != 'rebounds':
            return 1.0
            
        opp_reb_rate = opponent_stats.get('rebound_rate', 50.0)
        
        if opp_reb_rate < 48.0:
            logger.debug(f"Glass Eater: Opp REB% {opp_reb_rate:.1f} < 48 -> +8% boards")
            return 1.08
        elif opp_reb_rate > 52.0:
            logger.debug(f"Glass Eater: Opp REB% {opp_reb_rate:.1f} > 52 -> -6% boards")
            return 0.94
            
        return 1.0
