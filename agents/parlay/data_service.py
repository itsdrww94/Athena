"""
Hakari Data Service
Wrapper for Official NBA API to fetch live game data and player stats.
"""

from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import playergamelog, commonteamroster
from nba_api.stats.static import players, teams
from datetime import datetime
import pandas as pd
import time
import logging

logger = logging.getLogger("Hakari.Data")

class NBADataService:
    def __init__(self):
        self._team_cache = {}
        self._player_cache = {}

    def fetch_live_games(self):
        """Get today's games from NBA Live Scoreboard."""
        try:
            board = scoreboard.Scoreboard()
            games = board.games.get_dict()
            
            clean_games = []
            for g in games:
                clean_games.append({
                    "game_id": g['gameId'],
                    "home_team_id": g['homeTeam']['teamId'],
                    "away_team_id": g['awayTeam']['teamId'],
                    "home_score": g['homeTeam']['score'],
                    "away_score": g['awayTeam']['score'],
                    "status": g['gameStatusText']
                })
            return clean_games
        except Exception as e:
            logger.error(f"Scoreboard Error: {e}")
            return []

    def get_player_id(self, name):
        """Find player ID by name."""
        if name in self._player_cache:
            return self._player_cache[name]
        
        found = players.find_players_by_full_name(name)
        if found:
            pid = found[0]['id']
            self._player_cache[name] = pid
            return pid
        return None

    def fetch_player_logs(self, player_name, season="2024-25"):
        """Get last 10 game logs for a player."""
        pid = self.get_player_id(player_name)
        if not pid:
            return None
        
        try:
            # Add small delay to avoid rate limits
            time.sleep(0.6)
            log = playergamelog.PlayerGameLog(player_id=pid, season=season)
            df = log.get_data_frames()[0]
            
            # Standardize columns
            logs = []
            for _, row in df.head(10).iterrows():
                logs.append({
                    "date": row['GAME_DATE'],
                    "matchup": row['MATCHUP'],
                    "wl": row['WL'],
                    "min": row['MIN'],
                    "pts": row['PTS'],
                    "reb": row['REB'],
                    "ast": row['AST'],
                    "3pm": row['FG3M']
                })
            return logs
        except Exception as e:
            logger.error(f"Log Error for {player_name}: {e}")
            return None

    def get_team_roster(self, team_id):
        """Get active roster for a team."""
        try:
            roster = commonteamroster.CommonTeamRoster(team_id=team_id)
            return roster.get_data_frames()[0]
        except Exception as e:
            logger.error(f"Roster Error {team_id}: {e}")
            return None
