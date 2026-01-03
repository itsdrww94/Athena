import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
import time

# NBA API
from nba_api.stats.endpoints import scoreboardv2, commonteamroster
from nba_api.stats.static import teams

# Local Imports
import nba_logic
from nba_logic import UniversalPlayerProjection, calculate_win_probability

class SuggestionEngine:
    def __init__(self):
        self.cache = {}

    async def generate_suggestions(self, constraints):
        """
        Main entry point for 'suggestion' command.
        constraints: dict with keys 'count', 'teams', 'players', 'category'
        """
        start_time = time.time()
        print(f"[SuggestionEngine] Starting generation with constraints: {constraints}")
        
        target_count = constraints.get('count', 2)
        target_teams = constraints.get('teams', []) # List of team abbr or names
        target_players = constraints.get('players', [])
        target_category = constraints.get('category', None)
        
        # 1. Get Today's Games
        games = self._get_todays_games()
        if not games:
            return {"error": "No games found for today."}
            
        print(f"[SuggestionEngine] Found {len(games)} games.")
        
        # 2. Identify Target Players
        candidates = [] # list of (player_name, team_id, opponent_id)
        
        if target_players:
            for p in target_players:
                 candidates.append({"name": p, "team_id": None})
        else:
            # Filter games by team if needed
            relevant_games = []
            for g in games:
                if target_teams:
                    hit = False
                    for t in target_teams:
                        if t.lower() in g['home_team_name'].lower() or t.lower() in g['visitor_team_name'].lower():
                            hit = True
                            break
                    if not hit: continue
                    
                relevant_games.append(g)
            
            # Get Rosters for relevant games
            # For the immediate implementation, I will use a placeholder list of current stars 
            if not candidates:
                candidates = self._get_star_candidates(relevant_games)
        
        # 3. Analyze Candidates
        results = []
        
        # Categories to check
        categories = ['points', 'rebounds', 'assists', 'threes']
        if target_category:
            categories = [target_category]
            
        # Limit concurrency
        sema = asyncio.Semaphore(5) 
        
        async def process_candidate(player_info):
            async with sema:
                name = player_info['name']
                
                for cat in categories:
                    # 1. Get Data
                    # Using executor because get_player_data is synchronous
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, nba_logic.get_player_data, name, cat, "0.0" # Pass 0.0 line initially
                    )
                    
                    if "error" in data: continue
                    
                    # 2. Extract Data for Projection Engine
                    # Note: calculate_win_probability is called in get_player_data
                    # For suggestions, we want to find good edges.
                    
                    # NOTE: get_player_data returned a projection. 
                    # If we trust that, we can just use it.
                    projection = data.get('score', 0)
                    
                    # Mock Line (Set line = projection * 0.9 to create an "Over" edge if user didn't specify)
                    # In reality we would fetch lines.
                    line = projection * 0.9 
                    
                    diff = projection - line
                    
                    if diff > 1.5: # Interesting pick
                        pick = {
                            'player': name,
                            'stat': cat,
                            'line': round(line, 1),
                            'projection': projection,
                            'diff': diff,
                            'direction': 'more',
                            'reasoning': f"Proj {projection} > Line {line}",
                            'win_prob': data.get('win_prob', 50)
                        }
                        results.append(pick)
            return

        tasks = [process_candidate(c) for c in candidates]
        await asyncio.gather(*tasks)
        
        # 4. Sort and Filter
        results.sort(key=lambda x: x['diff'], reverse=True)
        
        top_picks = results[:target_count]
        
        return {
            'count': len(top_picks),
            'picks': top_picks,
            'note': f"Analyzed {len(candidates)} players across {len(games)} games."
        }

    def _get_todays_games(self):
        # Mocking for speed/safety
        return [
            {'home_team_abbr': 'LAL', 'visitor_team_abbr': 'BOS', 'home_team_name': 'Lakers', 'visitor_team_name': 'Celtics'},
            {'home_team_abbr': 'DAL', 'visitor_team_abbr': 'PHX', 'home_team_name': 'Mavericks', 'visitor_team_name': 'Suns'},
            {'home_team_abbr': 'MIA', 'visitor_team_abbr': 'NYK', 'home_team_name': 'Heat', 'visitor_team_name': 'Knicks'},
             {'home_team_abbr': 'GSW', 'visitor_team_abbr': 'DEN', 'home_team_name': 'Warriors', 'visitor_team_name': 'Nuggets'}
        ]

    def _get_star_candidates(self, games):
        cands = []
        for g in games:
            if g['home_team_abbr'] == 'LAL': cands.extend([{'name': 'LeBron James'}, {'name': 'Anthony Davis'}])
            if g['visitor_team_abbr'] == 'BOS': cands.extend([{'name': 'Jayson Tatum'}, {'name': 'Jaylen Brown'}])
            if g['home_team_abbr'] == 'DAL': cands.extend([{'name': 'Luka Doncic'}, {'name': 'Kyrie Irving'}])
            if g['visitor_team_abbr'] == 'PHX': cands.extend([{'name': 'Kevin Durant'}, {'name': 'Devin Booker'}])
            if g['home_team_abbr'] == 'MIA': cands.extend([{'name': 'Jimmy Butler'}, {'name': 'Bam Adebayo'}])
            if g['visitor_team_abbr'] == 'NYK': cands.extend([{'name': 'Jalen Brunson'}, {'name': 'Julius Randle'}])
            if g['home_team_abbr'] == 'GSW': cands.extend([{'name': 'Stephen Curry'}, {'name': 'Draymond Green'}])
            if g['visitor_team_abbr'] == 'DEN': cands.extend([{'name': 'Nikola Jokic'}, {'name': 'Jamal Murray'}])

        return cands

# Expose instance
se = SuggestionEngine()
generate_suggestions = se.generate_suggestions
