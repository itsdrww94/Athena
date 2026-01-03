#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     A N I L I S T   M O D U L E                               ║
║                   "The Otaku Upgrade"                                          ║
║                                                                               ║
║  Specialized anime tracking and recommendations via AniList GraphQL API      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- Episode tracking (Are you caught up on One Piece?)
- Similar anime recommendations
- Seasonal anime lookup
- Uses AniList GraphQL API (free, no key required)

Usage:
    from services.anilist import AniListAPI
    
    api = AniListAPI()
    info = api.get_anime_info("One Piece")
    similar = api.get_recommendations("Bleach")

For Cinema Companion:
    When genre == "Anime" or title in ANIME_TRIGGERS,
    use this module instead of TMDB.
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

ANILIST_API_URL = "https://graphql.anilist.co"

# Known anime titles that should trigger AniList instead of TMDB
ANIME_TRIGGERS = {
    "one piece", "naruto", "bleach", "dragon ball", "dbz", "dbs",
    "attack on titan", "demon slayer", "jujutsu kaisen", "my hero academia",
    "mob psycho", "hunter x hunter", "death note", "fullmetal alchemist",
    "cowboy bebop", "chainsaw man", "spy x family", "vinland saga",
    "tokyo ghoul", "black clover", "solo leveling", "blue lock", "kaiju no. 8"
}


# =============================================================================
# GRAPHQL QUERIES
# =============================================================================

ANIME_SEARCH_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title {
      romaji
      english
      native
    }
    episodes
    nextAiringEpisode {
      episode
      airingAt
      timeUntilAiring
    }
    status
    averageScore
    genres
    description(asHtml: false)
    coverImage {
      large
    }
    startDate {
      year
      month
      day
    }
    endDate {
      year
      month
      day
    }
    studios {
      nodes {
        name
      }
    }
    relations {
      edges {
        relationType
        node {
          id
          title {
            romaji
            english
          }
          type
          status
        }
      }
    }
    recommendations(perPage: 5) {
      nodes {
        mediaRecommendation {
          id
          title {
            romaji
            english
          }
          averageScore
          genres
        }
      }
    }
  }
}
"""

RECOMMENDATIONS_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    recommendations(perPage: 10, sort: RATING_DESC) {
      nodes {
        rating
        mediaRecommendation {
          id
          title {
            romaji
            english
          }
          description(asHtml: false)
          averageScore
          episodes
          genres
          status
          coverImage {
            medium
          }
        }
      }
    }
  }
}
"""

SEASONAL_QUERY = """
query ($season: MediaSeason, $year: Int) {
  Page(perPage: 20) {
    media(season: $season, seasonYear: $year, type: ANIME, sort: POPULARITY_DESC) {
      id
      title {
        romaji
        english
      }
      averageScore
      episodes
      genres
      status
      nextAiringEpisode {
        episode
        airingAt
      }
    }
  }
}
"""


# =============================================================================
# ANILIST API CLIENT
# =============================================================================

class AniListAPI:
    """
    Client for AniList GraphQL API.
    
    No API key required - completely free.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _query(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Execute a GraphQL query."""
        try:
            response = self.session.post(
                ANILIST_API_URL,
                json={"query": query, "variables": variables or {}},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json().get("data")
            else:
                print(f"AniList error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"AniList request failed: {e}")
            return None
    
    def search_anime(self, title: str) -> Optional[Dict]:
        """
        Search for an anime by title.
        
        Returns detailed info including airing status.
        """
        data = self._query(ANIME_SEARCH_QUERY, {"search": title})
        
        if data and "Media" in data:
            return self._format_anime(data["Media"])
        return None
    
    def _format_anime(self, media: Dict) -> Dict:
        """Format raw API response into clean structure."""
        title = media.get("title", {})
        
        # Get next airing info
        next_ep = media.get("nextAiringEpisode")
        if next_ep:
            airing_at = datetime.fromtimestamp(next_ep["airingAt"])
            next_airing = {
                "episode": next_ep["episode"],
                "airing_at": airing_at.strftime("%Y-%m-%d %H:%M"),
                "time_until": self._format_time_until(next_ep["timeUntilAiring"])
            }
        else:
            next_airing = None
        
        # Get studios
        studios = [s["name"] for s in media.get("studios", {}).get("nodes", [])]
        
        # Get relations (sequels, prequels)
        relations = []
        for edge in media.get("relations", {}).get("edges", []):
            node = edge.get("node", {})
            rel_title = node.get("title", {})
            relations.append({
                "type": edge.get("relationType"),
                "title": rel_title.get("english") or rel_title.get("romaji"),
                "status": node.get("status")
            })
        
        # Get recommendations
        recs = []
        for rec_node in media.get("recommendations", {}).get("nodes", []):
            rec = rec_node.get("mediaRecommendation", {})
            if rec:
                rec_title = rec.get("title", {})
                recs.append({
                    "title": rec_title.get("english") or rec_title.get("romaji"),
                    "score": rec.get("averageScore"),
                    "genres": rec.get("genres", [])
                })
        
        return {
            "id": media.get("id"),
            "title": title.get("english") or title.get("romaji"),
            "title_romaji": title.get("romaji"),
            "title_native": title.get("native"),
            "episodes": media.get("episodes"),
            "status": media.get("status"),
            "score": media.get("averageScore"),
            "genres": media.get("genres", []),
            "description": (media.get("description") or "")[:500],
            "cover_image": media.get("coverImage", {}).get("large"),
            "studios": studios,
            "next_airing": next_airing,
            "relations": relations[:5],
            "recommendations": recs[:5]
        }
    
    def _format_time_until(self, seconds: int) -> str:
        """Format seconds into human readable time."""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        
        if days > 0:
            return f"{days} days, {hours} hours"
        elif hours > 0:
            return f"{hours} hours"
        else:
            minutes = (seconds % 3600) // 60
            return f"{minutes} minutes"
    
    def get_recommendations(self, title: str, limit: int = 10) -> List[Dict]:
        """
        Get anime recommendations based on a title.
        """
        # First get the anime ID
        search_result = self.search_anime(title)
        if not search_result:
            return []
        
        anime_id = search_result.get("id")
        
        # Get recommendations
        data = self._query(RECOMMENDATIONS_QUERY, {"id": anime_id})
        
        if not data or "Media" not in data:
            return []
        
        recommendations = []
        for node in data["Media"].get("recommendations", {}).get("nodes", []):
            rec = node.get("mediaRecommendation", {})
            if rec:
                rec_title = rec.get("title", {})
                recommendations.append({
                    "title": rec_title.get("english") or rec_title.get("romaji"),
                    "score": rec.get("averageScore"),
                    "episodes": rec.get("episodes"),
                    "genres": rec.get("genres", []),
                    "status": rec.get("status"),
                    "description": (rec.get("description") or "")[:200]
                })
        
        return recommendations[:limit]
    
    def get_current_season(self) -> List[Dict]:
        """Get popular anime from the current season."""
        now = datetime.now()
        month = now.month
        year = now.year
        
        # Determine season
        if month in [1, 2, 3]:
            season = "WINTER"
        elif month in [4, 5, 6]:
            season = "SPRING"
        elif month in [7, 8, 9]:
            season = "SUMMER"
        else:
            season = "FALL"
        
        data = self._query(SEASONAL_QUERY, {"season": season, "year": year})
        
        if not data or "Page" not in data:
            return []
        
        anime_list = []
        for media in data["Page"].get("media", []):
            title = media.get("title", {})
            anime_list.append({
                "title": title.get("english") or title.get("romaji"),
                "score": media.get("averageScore"),
                "episodes": media.get("episodes"),
                "genres": media.get("genres", [])[:3],
                "status": media.get("status")
            })
        
        return anime_list
    
    def check_progress(self, title: str, current_episode: int) -> Dict:
        """
        Check if user is caught up on a series.
        
        Returns status and how many episodes behind.
        """
        info = self.search_anime(title)
        
        if not info:
            return {"error": f"Anime '{title}' not found"}
        
        total_episodes = info.get("episodes")
        status = info.get("status")
        next_airing = info.get("next_airing")
        
        # Calculate how far behind
        if status == "FINISHED":
            if current_episode >= total_episodes:
                caught_up = True
                behind = 0
            else:
                caught_up = False
                behind = total_episodes - current_episode
        elif status == "RELEASING" and next_airing:
            latest = next_airing["episode"] - 1  # Current latest is one before next
            if current_episode >= latest:
                caught_up = True
                behind = 0
            else:
                caught_up = False
                behind = latest - current_episode
        else:
            caught_up = current_episode >= (total_episodes or 0)
            behind = max(0, (total_episodes or 0) - current_episode)
        
        return {
            "title": info["title"],
            "current_episode": current_episode,
            "total_episodes": total_episodes,
            "status": status,
            "caught_up": caught_up,
            "episodes_behind": behind,
            "next_airing": next_airing,
            "message": self._progress_message(caught_up, behind, next_airing, info)
        }
    
    def _progress_message(self, caught_up: bool, behind: int, 
                          next_airing: Optional[Dict], info: Dict) -> str:
        """Generate human-readable progress message."""
        title = info["title"]
        
        if caught_up:
            if next_airing:
                return f"✅ You're caught up on {title}! Episode {next_airing['episode']} airs in {next_airing['time_until']}"
            elif info["status"] == "FINISHED":
                return f"✅ You've completed {title}!"
            else:
                return f"✅ You're caught up on {title}!"
        else:
            return f"📺 You're {behind} episodes behind on {title}. Latest: Ep {info['total_episodes'] or '?'}"


def is_anime_query(text: str) -> bool:
    """Check if a query is likely about anime."""
    text_lower = text.lower()
    
    # Check for known anime titles
    for trigger in ANIME_TRIGGERS:
        if trigger in text_lower:
            return True
    
    # Check for anime keywords
    anime_keywords = ["anime", "manga", "ova", "sub", "dub", "shonen", "seinen", "isekai"]
    return any(kw in text_lower for kw in anime_keywords)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AniList - Anime Information")
    parser.add_argument("--search", "-s", help="Search for an anime")
    parser.add_argument("--recommend", "-r", help="Get recommendations for an anime")
    parser.add_argument("--progress", nargs=2, metavar=("TITLE", "EPISODE"),
                        help="Check progress on a series")
    parser.add_argument("--season", action="store_true", help="Show current season anime")
    
    args = parser.parse_args()
    
    api = AniListAPI()
    
    if args.search:
        print(f"🔍 Searching for: {args.search}")
        result = api.search_anime(args.search)
        
        if result:
            print(f"\n📺 {result['title']}")
            print(f"   Score: {result['score']}/100 | Episodes: {result['episodes']} | Status: {result['status']}")
            print(f"   Genres: {', '.join(result['genres'][:5])}")
            print(f"   Studios: {', '.join(result['studios'][:3])}")
            
            if result['next_airing']:
                print(f"   📡 Next: Ep {result['next_airing']['episode']} in {result['next_airing']['time_until']}")
            
            if result['recommendations']:
                print(f"\n   Similar: {', '.join([r['title'] for r in result['recommendations'][:3]])}")
        else:
            print("❌ Not found")
            
    elif args.recommend:
        print(f"🎯 Recommendations based on: {args.recommend}")
        recs = api.get_recommendations(args.recommend)
        
        for i, rec in enumerate(recs[:5], 1):
            print(f"   {i}. {rec['title']} (Score: {rec['score']})")
            
    elif args.progress:
        title, episode = args.progress
        result = api.check_progress(title, int(episode))
        print(result.get("message", result))
        
    elif args.season:
        print("🌸 Current Season Anime:")
        anime_list = api.get_current_season()
        
        for i, anime in enumerate(anime_list[:10], 1):
            print(f"   {i}. {anime['title']} (Score: {anime['score']})")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
