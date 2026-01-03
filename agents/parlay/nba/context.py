import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =================================================================================================
# MODULE: RealTimeContextModule
# =================================================================================================
class RealTimeContextModule:
    """
    Manages real-time data inputs: Injury Status and Line Movement.
    """
    def __init__(self, players_status=None, props_data=None):
        self.players_status = players_status or {}
        self.props_data = props_data or {}

    def get_injury_adjustment(self, player_id):
        """
        Returns a dictionary of adjustment factors based on injury status.
        dict keys: 'minutes_factor', 'usage_factor', 'status', 'description'
        """
        status_info = self.players_status.get(player_id, {'status': 'active'})
        status = status_info.get('status', 'active').lower()
        
        adj = {
            'minutes_factor': 1.0,
            'usage_factor': 1.0,
            'status': status,
            'unavailable': False, 
            'description': status_info.get('injury_type', '')
        }

        if status == 'active':
            return adj
        elif status == 'questionable':
            # Risk of lower minutes or playing hurt
            adj['minutes_factor'] = 0.90
            adj['usage_factor'] = 0.95
        elif status == 'doubtful':
             # High risk if they play
            adj['minutes_factor'] = 0.80
            adj['usage_factor'] = 0.90
        elif status in ['out', 'rest']:
            adj['unavailable'] = True
            adj['minutes_factor'] = 0.0
            
        return adj

    def get_line_movement_confidence(self, player_id, stat_type):
        """
        Analyzes line movement to return a confidence multiplier (0.0 - 1.0).
        Big moves against our projection might lower confidence.
        """
        # structure: props[player_id][stat_type] -> {open, current, ...}
        p_props = self.props_data.get(player_id, {})
        prop = p_props.get(stat_type)
        
        if not prop:
            return 1.0 # No line data, neutral
            
        open_line = prop.get('open_line')
        curr_line = prop.get('current_line')
        
        if open_line is None or curr_line is None:
            return 1.0
            
        delta = curr_line - open_line
        abs_delta = abs(delta)
        
        # Thresholds
        SMALL_MOVE = 0.5
        BIG_MOVE = 1.5
        
        if abs_delta < SMALL_MOVE:
            return 1.0 # No meaningful move
            
        # If big move, we return a factor to be used downstream. 
        # The caller (Projection Engine) needs to verify if the move supports or contradicts the model.
        # Here we just return the MAGNITUDE of caution. 
        # Actually, spec says: "If sudden move... adjust trust... output confidence factor"
        
        if abs_delta >= BIG_MOVE:
            return 0.85 # High caution
        else:
            return 0.95 # Slight caution
            
        return 1.0


# =================================================================================================
# MODULE: MatchupContextModule
# =================================================================================================
class MatchupContextModule:
    """
    Calculates position-based opponent difficulty and replacement quality.
    """
    def __init__(self, league_averages=None):
        self.league_averages = league_averages or {} 
        # Expected league_averages format: {'C': 45.5, 'PG': 42.0 ... for Fantasy pts or Def Rating}

    def get_positional_defense_factor(self, player_pos, opponent_stats, stat_type='points'):
        """
        Returns a multiplier based on opponent's defense vs position.
        opponent_stats: dict of { 'PG': 105.0, 'SG': 108.2 ... } representing Def Rating or Points Allowed
        """
        # For simplicity, let's assume opponent_stats contains 'def_rating_vs_pos' dict
        def_ratings = opponent_stats.get('def_rating_vs_pos', {})
        
        opp_rating = def_ratings.get(player_pos)
        league_avg = self.league_averages.get(player_pos, 100.0) # Default 100 if unknown estimate
        
        if opp_rating is None:
            return 1.0
            
        # Higher Def Rating (allowed) = Weaker Defense? 
        # Usually Def Rating = Pts Allowed Per 100 Poss. So Higher = Bad Defense = Good for Offense.
        # BUT spec says: "def_rating_vs_pos... If > 1 (tough defender) -> multiply by factor < 1"
        # This implies the user might be supplying a Ratio or a "Strength" metric where High = Good Defense.
        # Let's stick to the spec's implication: 
        # "pos_def_ratio = opponent_def_vs_pos / league_avg"
        # If User provides "Points Allowed", Higher = Easier.
        # If User provides "Defensive Strength", Higher = Harder.
        
        # Let's assume standard "Points Allowed" inverse logic for now unless spec was explicit about "Rating" meaning "Strength".
        # Re-reading spec: "If pos_def_ratio > 1 (tough defender)" 
        # This explicitly says Ratio > 1 is TOUGH. So Opp Stat > League Avg = TOUGH.
        # This means the metric is likely "Defensive Efficiency" (Points Allowed per 100) is NOT it.
        # It's likely a "Defense Score" where 100 is avg, 110 is elite defense, 90 is bad.
        
        ratio = opp_rating / league_avg
        
        if ratio > 1.05: # Tough Matchup
            return 0.92 # Fade
        elif ratio < 0.95: # Easy Matchup
            return 1.08 # Boost
            
        return 1.0

    def check_defender_injury(self, opponent_roster, player_pos):
        """
        Checks if primary defender for position is out and returns boost.
        """
        # Placeholder logic: simplified
        # opponent_roster: list of dicts { 'position': 'C', 'status': 'out', 'role': 'starter' }
        
        primary_defender_out = False
        for p in opponent_roster:
            if p.get('position') == player_pos and p.get('role') == 'starter' and p.get('status') == 'out':
                primary_defender_out = True
                break
        
        if primary_defender_out:
            return 1.05 # 5% Boost if starter is out
            
        return 1.0


# =================================================================================================
# MODULE: GameScriptModule
# =================================================================================================
class GameScriptModule:
    """
    Predicts likely game flow (close, blowout risk) and translates to adjustments.
    """
    def __init__(self):
        # Config constants
        self.BLOWOUT_THRESHOLD = 12.5
        self.HEAVY_FAV_THRESHOLD = 8.5
        
    def predict_script(self, spread, total, team_implied_total):
        """
        Returns category: 'likely_close', 'favored_mild', 'blowout_risk'
        Spread is conventionally negative for favorites (e.g. -14.5). 
        """
        abs_spread = abs(spread)
        
        if abs_spread >= self.BLOWOUT_THRESHOLD:
            return 'blowout_risk'
        elif abs_spread >= self.HEAVY_FAV_THRESHOLD:
            return 'favored_mild'
        else:
            return 'likely_close'

    def get_script_adjustments(self, script, is_favorite):
        """
        Returns multipliers for minutes/usage.
        """
        adj = {'minutes_star': 1.0, 'minutes_role': 1.0, 'usage_star': 1.0}
        
        if script == 'blowout_risk':
            # Risk of sitting 4th quarter
            if is_favorite:
                adj['minutes_star'] = 0.88 # 12% cut (approx 4-5 mins less in 4th)
                adj['minutes_role'] = 1.10 # Garbage time heroes
            else:
                 # Underdogs in blowout might also sit stars if crushed
                adj['minutes_star'] = 0.90 
                adj['minutes_role'] = 1.05
                
        elif script == 'favored_mild':
            if is_favorite:
                adj['minutes_star'] = 0.97 # Slight shave
            
        # 'likely_close' -> Defaults 1.0
        
        return adj


# =================================================================================================
# MODULE: FatigueModule
# =================================================================================================
class FatigueModule:
    """
    Calculates fatigue index and adjustments.
    """
    def calculate_fatigue_index(self, days_rest, games_last_7, travel_km, age):
        """
        Returns 0-10 index.
        """
        index = 0.0
        
        # Base fatigue from rest
        if days_rest == 0: index += 4.0
        elif days_rest == 1: index += 1.0
        
        # Schedule density
        if games_last_7 >= 4: index += 2.0
        if games_last_7 >= 5: index += 2.0 # Extra penalty
        
        # Travel (simplified)
        if travel_km > 2000: index += 1.5
        elif travel_km > 1000: index += 0.5
        
        # Age multiplier
        if age >= 33: index *= 1.3
        elif age >= 29: index *= 1.1
        elif age <= 22: index *= 0.9 # Youth recovery
        
        return min(index, 10.0)

    def get_fatigue_penalty(self, fatigue_index, stat_type):
        """
        Returns multiplier. Shooting stats affected more.
        """
        # Shooting stats
        shooting = ['points', '3pm', '3pt', 'fgm']
        
        if fatigue_index < 3.0:
            return 1.0 # Fresh
            
        # Linear decay: 1.0 at index 3 -> 0.85 at index 10
        # Slope = (0.85 - 1.0) / (10 - 3) = -0.15 / 7 = -0.021
        
        penalty = 1.0 - ((fatigue_index - 3.0) * 0.02)
        
        if stat_type in shooting:
            return max(penalty, 0.80) # Cap at 20% fade
            
        # Other stats less affected (hustle stats might even stay flat or up if gritty game?)
        # Let's assume slight general fatigue
        return max(penalty + 0.01, 0.90) 
