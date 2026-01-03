#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     D A T A   H A R V E S T   P A R S E R S                   ║
║                   "The Life Coach Data Loaders"                                ║
║                                                                               ║
║  Specialized parsers for major platform exports                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Tier 1 (Easy Button):
- Spotify - Mood & music patterns
- ChatGPT - Thought archive & learning topics
- TikTok - Dopamine map & micro-interests
- YouTube - Learning log (via Google Takeout)

Tier 2 (Real World):
- Uber/Uber Eats - Movement & food ordering
- DoorDash - Diet patterns

Tier 3 (Manual):
- Crunchyroll - Anime watch history
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator
from collections import defaultdict, Counter

from .utils import normalize_timestamp, clean_pii, load_json_stream


# =============================================================================
# TIER 1: THE "EASY BUTTON" PARSERS
# =============================================================================

class SpotifyParser:
    """
    Parse Spotify streaming history exports.
    
    Files: StreamingHistory0.json, StreamingHistory1.json, etc.
    
    Insights:
    - Top artists and tracks
    - Listening patterns by time of day
    - Mood correlation (sad playlists on certain days)
    """
    
    def __init__(self):
        self.streams = []
        self.artist_playtime = defaultdict(int)  # artist -> ms played
        self.hourly_listening = defaultdict(int)  # hour -> ms played
        self.daily_listening = defaultdict(int)   # date -> ms played
    
    def load(self, filepath: Path) -> int:
        """Load a Spotify streaming history file."""
        count = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for entry in data:
                ts = normalize_timestamp(entry.get("endTime"))
                artist = entry.get("artistName", "Unknown")
                track = entry.get("trackName", "Unknown")
                ms_played = entry.get("msPlayed", 0)
                
                if ts and ms_played > 30000:  # At least 30 seconds
                    self.streams.append({
                        "timestamp": ts,
                        "artist": artist,
                        "track": track,
                        "ms_played": ms_played
                    })
                    
                    self.artist_playtime[artist] += ms_played
                    self.hourly_listening[ts.hour] += ms_played
                    self.daily_listening[ts.date()] += ms_played
                    count += 1
                    
        except Exception as e:
            print(f"Error loading Spotify: {e}")
        
        return count
    
    def get_top_artists(self, limit: int = 20) -> List[Dict]:
        """Get most listened artists."""
        sorted_artists = sorted(
            self.artist_playtime.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"artist": a, "hours": round(ms / 3600000, 1)}
            for a, ms in sorted_artists
        ]
    
    def get_listening_heatmap(self) -> Dict[int, float]:
        """Get listening hours by time of day."""
        return {
            hour: round(ms / 3600000, 2)
            for hour, ms in sorted(self.hourly_listening.items())
        }
    
    def get_mood_patterns(self) -> Dict[str, Any]:
        """Analyze potential mood patterns based on listening."""
        # Heavy listening hours might indicate specific moods
        peak_hour = max(self.hourly_listening.items(), 
                        key=lambda x: x[1])[0] if self.hourly_listening else None
        
        late_night_ms = sum(
            self.hourly_listening.get(h, 0) 
            for h in range(23, 24)
        ) + sum(
            self.hourly_listening.get(h, 0)
            for h in range(0, 5)
        )
        
        total_ms = sum(self.hourly_listening.values())
        late_night_pct = (late_night_ms / total_ms * 100) if total_ms else 0
        
        return {
            "peak_listening_hour": peak_hour,
            "late_night_listening_pct": round(late_night_pct, 1),
            "total_hours_listened": round(total_ms / 3600000, 1),
            "unique_artists": len(self.artist_playtime)
        }
    
    def analyze(self) -> Dict[str, Any]:
        """Full Spotify analysis."""
        return {
            "parser": "spotify",
            "streams_analyzed": len(self.streams),
            "top_artists": self.get_top_artists(10),
            "listening_heatmap": self.get_listening_heatmap(),
            "mood_patterns": self.get_mood_patterns()
        }


class ChatGPTParser:
    """
    Parse ChatGPT conversation exports.
    
    Files: conversations.json from ChatGPT export
    
    Insights:
    - Active learning projects
    - Topic clusters
    - Question patterns
    """
    
    def __init__(self):
        self.prompts = []  # User prompts only (ignore AI)
        self.topics = defaultdict(int)
        self.daily_usage = defaultdict(int)  # date -> prompt count
    
    def load(self, filepath: Path) -> int:
        """Load ChatGPT export."""
        count = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different export formats
            conversations = data if isinstance(data, list) else data.get("conversations", [])
            
            for conv in conversations:
                mapping = conv.get("mapping", {})
                
                for node_id, node in mapping.items():
                    message = node.get("message", {})
                    
                    if message and message.get("author", {}).get("role") == "user":
                        content = message.get("content", {})
                        
                        # Extract text
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            text = " ".join(str(p) for p in parts if isinstance(p, str))
                        elif isinstance(content, str):
                            text = content
                        else:
                            continue
                        
                        if text:
                            ts = normalize_timestamp(message.get("create_time"))
                            
                            self.prompts.append({
                                "timestamp": ts,
                                "text": clean_pii(text[:500])  # Truncate and clean
                            })
                            
                            if ts:
                                self.daily_usage[ts.date()] += 1
                            
                            count += 1
                            
        except Exception as e:
            print(f"Error loading ChatGPT: {e}")
        
        return count
    
    def cluster_topics(self) -> Dict[str, int]:
        """Simple keyword-based topic clustering."""
        topic_keywords = {
            "coding": ["python", "code", "function", "error", "debug", "api", "javascript", "sql"],
            "writing": ["write", "essay", "email", "draft", "letter", "story"],
            "learning": ["explain", "how does", "what is", "teach me", "learn"],
            "productivity": ["schedule", "todo", "organize", "plan", "goals"],
            "health": ["workout", "diet", "sleep", "health", "exercise"],
            "finance": ["budget", "money", "invest", "save", "expense"],
            "creative": ["design", "image", "logo", "color", "style"],
            "personal": ["advice", "feel", "help me", "should i", "decide"]
        }
        
        for prompt in self.prompts:
            text = prompt["text"].lower()
            
            for topic, keywords in topic_keywords.items():
                if any(kw in text for kw in keywords):
                    self.topics[topic] += 1
        
        return dict(self.topics)
    
    def get_active_projects(self) -> List[str]:
        """Identify current active learning/projects."""
        # Sort topics by frequency
        sorted_topics = sorted(self.topics.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_topics[:5]]
    
    def analyze(self) -> Dict[str, Any]:
        """Full ChatGPT analysis."""
        self.cluster_topics()
        
        return {
            "parser": "chatgpt",
            "prompts_analyzed": len(self.prompts),
            "topic_clusters": dict(self.topics),
            "active_projects": self.get_active_projects(),
            "daily_usage": {
                str(d): c for d, c in sorted(self.daily_usage.items())[-30:]
            }
        }


class TikTokParser:
    """
    Parse TikTok data exports.
    
    Files: Various JSON files from TikTok export
    
    Insights:
    - Watch history categories
    - Like patterns
    - Micro-interests (food, tech, comedy, etc.)
    """
    
    def __init__(self):
        self.watch_history = []
        self.likes = []
        self.category_counts = defaultdict(int)
    
    def load(self, data_dir: Path) -> int:
        """Load TikTok export directory."""
        count = 0
        
        # Look for various TikTok files
        files_to_check = [
            "user_data.json",
            "Video Browsing History.json",
            "Like List.json"
        ]
        
        try:
            for filename in files_to_check:
                filepath = data_dir / filename
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle watch history
                    if "VideoList" in data:
                        for video in data["VideoList"]:
                            ts = normalize_timestamp(video.get("Date"))
                            link = video.get("Link", "")
                            
                            self.watch_history.append({
                                "timestamp": ts,
                                "link": link
                            })
                            count += 1
                    
                    # Handle likes
                    if "ItemFavoriteList" in data or "LikeList" in data:
                        likes = data.get("ItemFavoriteList", data.get("LikeList", []))
                        for item in likes:
                            ts = normalize_timestamp(item.get("Date"))
                            self.likes.append({"timestamp": ts})
                            count += 1
                            
        except Exception as e:
            print(f"Error loading TikTok: {e}")
        
        return count
    
    def get_usage_patterns(self) -> Dict[str, Any]:
        """Analyze usage patterns."""
        hourly = defaultdict(int)
        
        for video in self.watch_history:
            ts = video.get("timestamp")
            if ts:
                hourly[ts.hour] += 1
        
        peak_hour = max(hourly.items(), key=lambda x: x[1])[0] if hourly else None
        
        return {
            "total_videos_watched": len(self.watch_history),
            "total_likes": len(self.likes),
            "peak_usage_hour": peak_hour,
            "hourly_distribution": dict(hourly)
        }
    
    def analyze(self) -> Dict[str, Any]:
        """Full TikTok analysis."""
        return {
            "parser": "tiktok",
            "videos_analyzed": len(self.watch_history),
            "usage_patterns": self.get_usage_patterns(),
            "insight": f"Watched {len(self.watch_history)} videos, liked {len(self.likes)}"
        }


# =============================================================================
# TIER 2: THE "REAL WORLD" PARSERS
# =============================================================================

class UberParser:
    """
    Parse Uber/Uber Eats exports.
    
    Insights:
    - Movement patterns (where you go)
    - Food ordering habits
    - Spending on transport vs food
    """
    
    def __init__(self):
        self.rides = []
        self.food_orders = []
        self.locations = defaultdict(int)  # location -> visit count
    
    def load(self, filepath: Path) -> int:
        """Load Uber data export."""
        count = 0
        
        try:
            # Handle CSV or JSON
            if filepath.suffix.lower() == '.csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                
                for _, row in df.iterrows():
                    ts = normalize_timestamp(row.get("Request Time", row.get("Order Time")))
                    
                    if "Pickup" in df.columns:  # Rides
                        self.rides.append({
                            "timestamp": ts,
                            "pickup": row.get("Pickup", ""),
                            "dropoff": row.get("Dropoff", ""),
                            "fare": float(row.get("Fare", 0))
                        })
                        self.locations[row.get("Dropoff", "unknown")] += 1
                    else:  # Eats
                        self.food_orders.append({
                            "timestamp": ts,
                            "restaurant": row.get("Restaurant", ""),
                            "total": float(row.get("Total", 0))
                        })
                    count += 1
                    
            else:  # JSON
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Process based on structure
                if "trips" in data:
                    for trip in data["trips"]:
                        ts = normalize_timestamp(trip.get("request_time"))
                        self.rides.append({
                            "timestamp": ts,
                            "dropoff": trip.get("dropoff", {}).get("name", ""),
                            "fare": trip.get("fare", 0)
                        })
                        count += 1
                        
        except Exception as e:
            print(f"Error loading Uber: {e}")
        
        return count
    
    def get_movement_patterns(self) -> Dict[str, Any]:
        """Analyze where you go."""
        top_locations = sorted(
            self.locations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_rides": len(self.rides),
            "top_destinations": top_locations,
            "total_spent_rides": sum(r.get("fare", 0) for r in self.rides)
        }
    
    def get_food_patterns(self) -> Dict[str, Any]:
        """Analyze food ordering habits."""
        late_night_orders = [
            o for o in self.food_orders
            if o.get("timestamp") and o["timestamp"].hour >= 22 or o["timestamp"].hour < 5
        ]
        
        total_spent = sum(o.get("total", 0) for o in self.food_orders)
        
        return {
            "total_orders": len(self.food_orders),
            "late_night_orders": len(late_night_orders),
            "late_night_pct": round(len(late_night_orders) / len(self.food_orders) * 100, 1) if self.food_orders else 0,
            "total_spent_food": round(total_spent, 2)
        }
    
    def analyze(self) -> Dict[str, Any]:
        """Full Uber analysis."""
        return {
            "parser": "uber",
            "rides_analyzed": len(self.rides),
            "orders_analyzed": len(self.food_orders),
            "movement_patterns": self.get_movement_patterns(),
            "food_patterns": self.get_food_patterns()
        }


class DoorDashParser:
    """
    Parse DoorDash order history.
    
    Insights:
    - Ordering frequency
    - Late night ordering correlation with sleep
    - Restaurant preferences
    """
    
    def __init__(self):
        self.orders = []
        self.restaurant_counts = defaultdict(int)
        self.daily_orders = defaultdict(int)
    
    def load(self, filepath: Path) -> int:
        """Load DoorDash export."""
        count = 0
        
        try:
            if filepath.suffix.lower() == '.csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                
                for _, row in df.iterrows():
                    ts = normalize_timestamp(row.get("Order Date", row.get("Date")))
                    restaurant = row.get("Restaurant", row.get("Store", "Unknown"))
                    total = float(row.get("Total", row.get("Amount", 0)))
                    
                    if ts:
                        self.orders.append({
                            "timestamp": ts,
                            "restaurant": restaurant,
                            "total": total
                        })
                        
                        self.restaurant_counts[restaurant] += 1
                        self.daily_orders[ts.date()] += 1
                        count += 1
                        
            else:  # JSON
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                orders = data.get("orders", data if isinstance(data, list) else [])
                
                for order in orders:
                    ts = normalize_timestamp(order.get("created_at", order.get("date")))
                    restaurant = order.get("store_name", order.get("restaurant", "Unknown"))
                    total = order.get("total", order.get("amount", 0))
                    
                    if ts:
                        self.orders.append({
                            "timestamp": ts,
                            "restaurant": restaurant,
                            "total": total
                        })
                        
                        self.restaurant_counts[restaurant] += 1
                        self.daily_orders[ts.date()] += 1
                        count += 1
                        
        except Exception as e:
            print(f"Error loading DoorDash: {e}")
        
        return count
    
    def get_diet_analysis(self) -> Dict[str, Any]:
        """Analyze ordering habits."""
        top_restaurants = sorted(
            self.restaurant_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        late_night = [
            o for o in self.orders
            if o.get("timestamp") and (o["timestamp"].hour >= 22 or o["timestamp"].hour < 4)
        ]
        
        total_spent = sum(o.get("total", 0) for o in self.orders)
        avg_order = total_spent / len(self.orders) if self.orders else 0
        
        return {
            "total_orders": len(self.orders),
            "total_spent": round(total_spent, 2),
            "avg_order_value": round(avg_order, 2),
            "top_restaurants": top_restaurants[:5],
            "late_night_orders": len(late_night),
            "late_night_pct": round(len(late_night) / len(self.orders) * 100, 1) if self.orders else 0
        }
    
    def analyze(self) -> Dict[str, Any]:
        """Full DoorDash analysis."""
        return {
            "parser": "doordash",
            "orders_analyzed": len(self.orders),
            "diet_analysis": self.get_diet_analysis()
        }


class CrunchyrollParser:
    """
    Parse Crunchyroll watch history.
    
    Insights:
    - Anime preferences
    - Watch patterns
    - Completion rates
    """
    
    def __init__(self):
        self.watched = []
        self.series_episodes = defaultdict(int)
    
    def load(self, filepath: Path) -> int:
        """Load Crunchyroll export (usually CSV or PDF parsed)."""
        count = 0
        
        try:
            if filepath.suffix.lower() == '.csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                
                for _, row in df.iterrows():
                    ts = normalize_timestamp(row.get("Date", row.get("Watched Date")))
                    series = row.get("Series", row.get("Title", "Unknown"))
                    episode = row.get("Episode", "")
                    
                    self.watched.append({
                        "timestamp": ts,
                        "series": series,
                        "episode": episode
                    })
                    
                    self.series_episodes[series] += 1
                    count += 1
                    
        except Exception as e:
            print(f"Error loading Crunchyroll: {e}")
        
        return count
    
    def analyze(self) -> Dict[str, Any]:
        """Full Crunchyroll analysis."""
        top_series = sorted(
            self.series_episodes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "parser": "crunchyroll",
            "episodes_watched": len(self.watched),
            "unique_series": len(self.series_episodes),
            "top_anime": top_series[:5],
            "binge_worthy": [s for s, e in top_series if e >= 10][:3]
        }


# =============================================================================
# MASTER HARVESTER
# =============================================================================

class DataHarvester:
    """
    Master class that orchestrates all parsers.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        
        self.spotify = SpotifyParser()
        self.chatgpt = ChatGPTParser()
        self.tiktok = TikTokParser()
        self.uber = UberParser()
        self.doordash = DoorDashParser()
        self.crunchyroll = CrunchyrollParser()
    
    def harvest_all(self) -> Dict[str, Any]:
        """Load all available data sources."""
        results = {}
        
        # Spotify
        spotify_files = list(self.data_dir.rglob("StreamingHistory*.json"))
        for f in spotify_files:
            self.spotify.load(f)
        if self.spotify.streams:
            results["spotify"] = self.spotify.analyze()
        
        # ChatGPT
        chatgpt_files = list(self.data_dir.rglob("conversations.json"))
        for f in chatgpt_files:
            self.chatgpt.load(f)
        if self.chatgpt.prompts:
            results["chatgpt"] = self.chatgpt.analyze()
        
        # TikTok
        tiktok_dirs = list(self.data_dir.rglob("tiktok*"))
        for d in tiktok_dirs:
            if d.is_dir():
                self.tiktok.load(d)
        if self.tiktok.watch_history:
            results["tiktok"] = self.tiktok.analyze()
        
        # Uber
        uber_files = list(self.data_dir.rglob("*uber*.csv")) + \
                     list(self.data_dir.rglob("*uber*.json"))
        for f in uber_files:
            self.uber.load(f)
        if self.uber.rides or self.uber.food_orders:
            results["uber"] = self.uber.analyze()
        
        # DoorDash
        doordash_files = list(self.data_dir.rglob("*doordash*.csv")) + \
                         list(self.data_dir.rglob("*doordash*.json"))
        for f in doordash_files:
            self.doordash.load(f)
        if self.doordash.orders:
            results["doordash"] = self.doordash.analyze()
        
        # Crunchyroll
        crunchy_files = list(self.data_dir.rglob("*crunchyroll*.csv"))
        for f in crunchy_files:
            self.crunchyroll.load(f)
        if self.crunchyroll.watched:
            results["crunchyroll"] = self.crunchyroll.analyze()
        
        return results
