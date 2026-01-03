#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    C I N E M A   C O M P A N I O N                            ║
║                         "The Movie Buff"                                       ║
║                                                                               ║
║  Division III: LifeOS (Health & Leisure)                                      ║
║  Track watchlist, get recommendations, check new releases                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
  - TMDB integration for movie/TV info
  - Track your Notion watchlist
  - Alert on new seasons of watched shows
  - Check local showtimes

Usage:
  python cinema_companion.py --action search --query "Dune"
  python cinema_companion.py --action trending
  python cinema_companion.py --action watchlist
"""

import os
import sys
import json
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Movie:
    """A movie or TV show."""
    id: int
    title: str
    year: str
    rating: float
    overview: str
    poster_path: str = ""
    media_type: str = "movie"
    genres: List[str] = None
    
    def __post_init__(self):
        if self.genres is None:
            self.genres = []
    
    @property
    def poster_url(self) -> str:
        if self.poster_path:
            return f"{TMDB_IMAGE_BASE}{self.poster_path}"
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "rating": self.rating,
            "overview": self.overview[:200],
            "poster_url": self.poster_url,
            "media_type": self.media_type,
            "genres": self.genres
        }


# =============================================================================
# TMDB API
# =============================================================================

def tmdb_request(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """Make a request to TMDB API."""
    if not TMDB_API_KEY:
        print("⚠️ TMDB_API_KEY not set in .env")
        print("   Get a free key at: https://www.themoviedb.org/settings/api")
        return None
    
    try:
        import requests
        
        params = params or {}
        params["api_key"] = TMDB_API_KEY
        
        url = f"{TMDB_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        print(f"⚠️ TMDB API error: {e}")
        return None


def search_movies(query: str, media_type: str = "multi") -> List[Movie]:
    """Search for movies or TV shows."""
    endpoint = f"search/{media_type}"
    data = tmdb_request(endpoint, {"query": query})
    
    if not data:
        return []
    
    movies = []
    for item in data.get("results", [])[:10]:
        # Handle both movie and TV
        title = item.get("title") or item.get("name", "Unknown")
        date_str = item.get("release_date") or item.get("first_air_date", "")
        year = date_str[:4] if date_str else "N/A"
        m_type = item.get("media_type", media_type)
        if m_type == "multi":
            m_type = "movie" if "title" in item else "tv"
        
        movies.append(Movie(
            id=item.get("id", 0),
            title=title,
            year=year,
            rating=item.get("vote_average", 0),
            overview=item.get("overview", ""),
            poster_path=item.get("poster_path", ""),
            media_type=m_type
        ))
    
    return movies


def get_trending(media_type: str = "all", time_window: str = "week") -> List[Movie]:
    """Get trending movies/TV."""
    endpoint = f"trending/{media_type}/{time_window}"
    data = tmdb_request(endpoint)
    
    if not data:
        return []
    
    movies = []
    for item in data.get("results", [])[:10]:
        title = item.get("title") or item.get("name", "Unknown")
        date_str = item.get("release_date") or item.get("first_air_date", "")
        year = date_str[:4] if date_str else "N/A"
        
        movies.append(Movie(
            id=item.get("id", 0),
            title=title,
            year=year,
            rating=item.get("vote_average", 0),
            overview=item.get("overview", ""),
            poster_path=item.get("poster_path", ""),
            media_type=item.get("media_type", "movie")
        ))
    
    return movies


def get_movie_details(movie_id: int, media_type: str = "movie") -> Optional[Dict]:
    """Get detailed info about a movie/show."""
    endpoint = f"{media_type}/{movie_id}"
    return tmdb_request(endpoint)


def get_upcoming_movies() -> List[Movie]:
    """Get upcoming movie releases."""
    today = date.today().isoformat()
    endpoint = "movie/upcoming"
    data = tmdb_request(endpoint, {"region": "US"})
    
    if not data:
        return []
    
    movies = []
    for item in data.get("results", [])[:10]:
        movies.append(Movie(
            id=item.get("id", 0),
            title=item.get("title", "Unknown"),
            year=item.get("release_date", "")[:4] if item.get("release_date") else "TBA",
            rating=item.get("vote_average", 0),
            overview=item.get("overview", ""),
            poster_path=item.get("poster_path", ""),
            media_type="movie"
        ))
    
    return movies


def check_new_seasons(show_id: int) -> Optional[Dict]:
    """Check if a TV show has new seasons."""
    details = get_movie_details(show_id, "tv")
    if not details:
        return None
    
    return {
        "name": details.get("name"),
        "status": details.get("status"),
        "last_air_date": details.get("last_air_date"),
        "next_episode": details.get("next_episode_to_air"),
        "seasons": details.get("number_of_seasons"),
        "in_production": details.get("in_production")
    }


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_movies(movies: List[Movie], title: str = "Results") -> str:
    """Format movie list for display."""
    output = []
    output.append("=" * 60)
    output.append(f"🎬 CINEMA COMPANION - {title}")
    output.append("=" * 60)
    output.append("")
    
    if not movies:
        output.append("📭 No results found.")
        return "\n".join(output)
    
    for i, movie in enumerate(movies, 1):
        emoji = "🎬" if movie.media_type == "movie" else "📺"
        stars = "⭐" * int(movie.rating / 2)
        
        output.append(f"{emoji} [{i}] {movie.title} ({movie.year})")
        output.append(f"     Rating: {movie.rating}/10 {stars}")
        output.append(f"     {movie.overview[:100]}...")
        output.append("")
    
    output.append("=" * 60)
    
    return "\n".join(output)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Cinema Companion - Movie & TV tracker"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["search", "trending", "upcoming", "details", "seasons"],
        default="trending",
        help="Action to perform"
    )
    
    parser.add_argument("--query", "-q", type=str, help="Search query")
    parser.add_argument("--id", type=int, help="Movie/Show ID for details")
    parser.add_argument("--type", "-t", choices=["movie", "tv", "all"], default="all", help="Media type")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.action == "search":
        if not args.query:
            print("❌ --query required for search")
            sys.exit(1)
        movies = search_movies(args.query, "multi" if args.type == "all" else args.type)
        result = format_movies(movies, f"Search: {args.query}")
        
    elif args.action == "trending":
        movies = get_trending(args.type)
        result = format_movies(movies, "Trending This Week")
        
    elif args.action == "upcoming":
        movies = get_upcoming_movies()
        result = format_movies(movies, "Upcoming Releases")
        
    elif args.action == "details":
        if not args.id:
            print("❌ --id required for details")
            sys.exit(1)
        details = get_movie_details(args.id, args.type if args.type != "all" else "movie")
        result = json.dumps(details, indent=2) if details else "Not found"
        
    elif args.action == "seasons":
        if not args.id:
            print("❌ --id required for seasons check")
            sys.exit(1)
        seasons = check_new_seasons(args.id)
        if seasons:
            result = f"""
📺 {seasons['name']}
Status: {seasons['status']}
Seasons: {seasons['seasons']}
In Production: {seasons['in_production']}
Last Aired: {seasons['last_air_date']}
"""
            if seasons['next_episode']:
                result += f"Next Episode: {seasons['next_episode']}"
        else:
            result = "❌ Show not found"
    else:
        result = "Unknown action"
    
    if args.json and args.action in ["search", "trending", "upcoming"]:
        movies = search_movies(args.query) if args.action == "search" else get_trending() if args.action == "trending" else get_upcoming_movies()
        print(json.dumps([m.to_dict() for m in movies], indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
