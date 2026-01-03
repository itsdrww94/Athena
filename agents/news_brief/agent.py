#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        N E W S   B R I E F                                    ║
║                          "The Anchor"                                          ║
║                                                                               ║
║  Division II: Intelligence (The News Room)                                    ║
║  Daily briefing from multiple sources with Philip DeFranco integration       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Sources:
  - AP News (RSS)
  - Dexerto (Gaming News)
  - Ground News (for bias/blindspot awareness)
  - Philip DeFranco (YouTube transcript summaries)

Usage:
  python news_brief.py --action brief
  python news_brief.py --action defranco
  python news_brief.py --action gaming
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# RSS Feeds
RSS_FEEDS = {
    "ap_news": "https://rsshub.app/apnews/topics/apf-topnews",
    "ap_politics": "https://rsshub.app/apnews/topics/politics",
    "dexerto": "https://www.dexerto.com/feed/",
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "hacker_news": "https://hnrss.org/frontpage",
}

# Philip DeFranco Channel ID
DEFRANCO_CHANNEL_ID = "UClFSU9_bUb4Rc6OYfTt5SPw"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class NewsItem:
    """A news article/story."""
    title: str
    source: str
    url: str
    published: str = ""
    summary: str = ""
    category: str = "General"


# =============================================================================
# RSS PARSING
# =============================================================================

def fetch_rss_feed(feed_url: str, max_items: int = 5) -> List[NewsItem]:
    """Fetch and parse an RSS feed."""
    try:
        import feedparser
        
        feed = feedparser.parse(feed_url)
        items = []
        
        for entry in feed.entries[:max_items]:
            item = NewsItem(
                title=entry.get("title", "No title"),
                source=feed.feed.get("title", "Unknown"),
                url=entry.get("link", ""),
                published=entry.get("published", ""),
                summary=entry.get("summary", "")[:200] if entry.get("summary") else ""
            )
            items.append(item)
        
        return items
        
    except ImportError:
        print("⚠️ feedparser not installed. Run: pip install feedparser")
        return []
    except Exception as e:
        print(f"⚠️ Error fetching {feed_url}: {e}")
        return []


def get_all_news(max_per_source: int = 3) -> Dict[str, List[NewsItem]]:
    """Fetch news from all configured sources."""
    all_news = {}
    
    for name, url in RSS_FEEDS.items():
        items = fetch_rss_feed(url, max_per_source)
        if items:
            all_news[name] = items
    
    return all_news


# =============================================================================
# PHILIP DEFRANCO INTEGRATION
# =============================================================================

def get_latest_defranco_video(check_memory: bool = True) -> Optional[Dict[str, str]]:
    """
    Get the latest Philip DeFranco Show video.
    Requires YOUTUBE_API_KEY.
    
    Args:
        check_memory: If True, skip videos we've already shown
    """
    if not YOUTUBE_API_KEY:
        return None
    
    try:
        import requests
        
        # Check memory for already-seen videos
        seen_videos = []
        if check_memory:
            try:
                from services.memory_core import get_memory
                memory = get_memory()
                state = memory.load_state("news_brief", "seen_video_ids")
                if state:
                    seen_videos = state if isinstance(state, list) else []
            except Exception:
                pass
        
        # Search for latest video from channel
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": YOUTUBE_API_KEY,
            "channelId": DEFRANCO_CHANNEL_ID,
            "order": "date",
            "part": "snippet",
            "type": "video",
            "maxResults": 5  # Get more results in case some are already seen
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("items"):
            for item in data["items"]:
                video_id = item["id"]["videoId"]
                
                # Skip if we've already shown this video
                if video_id in seen_videos:
                    continue
                
                return {
                    "video_id": video_id,
                    "title": item["snippet"]["title"],
                    "published": item["snippet"]["publishedAt"],
                    "url": f"https://youtube.com/watch?v={video_id}"
                }
        
        return None
        
    except Exception as e:
        print(f"⚠️ YouTube API error: {e}")
        return None


def mark_video_seen(video_id: str) -> None:
    """Mark a video as seen in memory."""
    try:
        from services.memory_core import get_memory
        memory = get_memory()
        
        # Get existing seen videos
        seen = memory.load_state("news_brief", "seen_video_ids")
        seen_list = seen if isinstance(seen, list) else []
        
        # Add new video (keep last 20)
        if video_id not in seen_list:
            seen_list.append(video_id)
            seen_list = seen_list[-20:]  # Keep only recent 20
            memory.save_state("news_brief", "seen_video_ids", seen_list)
    except Exception:
        pass


def get_video_transcript(video_id: str) -> Optional[str]:
    """
    Get transcript for a YouTube video.
    Uses youtube_transcript_api.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine all text
        full_text = " ".join([t["text"] for t in transcript_list])
        
        return full_text
        
    except ImportError:
        print("⚠️ youtube_transcript_api not installed. Run: pip install youtube-transcript-api")
        return None
    except Exception as e:
        print(f"⚠️ Transcript error: {e}")
        return None


def summarize_defranco(transcript: str) -> Optional[str]:
    """
    Use Gemini to summarize Philip DeFranco transcript into 3 main stories.
    """
    if not GEMINI_API_KEY or not transcript:
        return None
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""Summarize this Philip DeFranco Show transcript into the 3 MAIN stories covered.

For each story, provide:
1. A one-line headline
2. 2-3 sentence summary
3. Why it matters

Transcript:
{transcript[:15000]}

Format as:
**Story 1: [Headline]**
[Summary]

**Story 2: [Headline]**
[Summary]

**Story 3: [Headline]**
[Summary]
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        print(f"⚠️ Gemini summary error: {e}")
        return None


# =============================================================================
# BRIEFING GENERATION
# =============================================================================

def generate_daily_brief() -> str:
    """Generate a comprehensive daily news brief."""
    output = []
    output.append("=" * 60)
    output.append(f"📰 ATHENA DAILY BRIEF - {datetime.now().strftime('%B %d, %Y')}")
    output.append("=" * 60)
    output.append("")
    
    # Fetch all news
    all_news = get_all_news(max_per_source=3)
    
    if not all_news:
        output.append("⚠️ Could not fetch news. Check your internet connection.")
        return "\n".join(output)
    
    # Top Headlines (AP News)
    if "ap_news" in all_news:
        output.append("📌 TOP HEADLINES (AP News)")
        output.append("-" * 40)
        for item in all_news["ap_news"]:
            output.append(f"  • {item.title}")
            output.append(f"    🔗 {item.url}")
        output.append("")
    
    # Tech News
    if "ars_technica" in all_news or "hacker_news" in all_news:
        output.append("💻 TECH NEWS")
        output.append("-" * 40)
        for source in ["ars_technica", "hacker_news"]:
            if source in all_news:
                for item in all_news[source][:2]:
                    output.append(f"  • {item.title}")
                    output.append(f"    🔗 {item.url}")
        output.append("")
    
    # Gaming News
    if "dexerto" in all_news:
        output.append("🎮 GAMING NEWS (Dexerto)")
        output.append("-" * 40)
        for item in all_news["dexerto"]:
            output.append(f"  • {item.title}")
        output.append("")
    
    # Philip DeFranco
    output.append("🎬 PHILIP DEFRANCO")
    output.append("-" * 40)
    video = get_latest_defranco_video()
    if video:
        output.append(f"  Latest: {video['title']}")
        output.append(f"  🔗 {video['url']}")
        output.append("  (Use --action defranco for full summary)")
    else:
        if not YOUTUBE_API_KEY:
            output.append("  ⚠️ Set YOUTUBE_API_KEY in .env for DeFranco integration")
        else:
            output.append("  ⚠️ Could not fetch latest video")
    
    output.append("")
    output.append("=" * 60)
    
    return "\n".join(output)


def generate_defranco_brief() -> str:
    """Generate a DeFranco-specific brief with transcript summary."""
    output = []
    output.append("=" * 60)
    output.append("🎬 PHILIP DEFRANCO SHOW SUMMARY")
    output.append("=" * 60)
    output.append("")
    
    video = get_latest_defranco_video()
    if not video:
        output.append("⚠️ Could not fetch latest DeFranco video.")
        output.append("   Make sure YOUTUBE_API_KEY is set in .env")
        return "\n".join(output)
    
    output.append(f"📺 {video['title']}")
    output.append(f"📅 {video['published'][:10]}")
    output.append(f"🔗 {video['url']}")
    output.append("")
    
    # Get transcript
    print("📝 Fetching transcript...")
    transcript = get_video_transcript(video["video_id"])
    
    if not transcript:
        output.append("⚠️ Could not fetch transcript. Video may not have captions.")
        return "\n".join(output)
    
    # Summarize
    print("🤖 Generating summary with Gemini...")
    summary = summarize_defranco(transcript)
    
    if summary:
        output.append("📋 MAIN STORIES:")
        output.append("-" * 40)
        output.append(summary)
        
        # Mark video as seen in memory
        mark_video_seen(video["video_id"])
    else:
        output.append("⚠️ Could not generate summary.")
    
    output.append("")
    output.append("=" * 60)
    
    return "\n".join(output)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Athena News Brief - Daily news digest"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["brief", "defranco", "gaming", "tech"],
        default="brief",
        help="Type of briefing"
    )
    
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.action == "brief":
        result = generate_daily_brief()
    elif args.action == "defranco":
        result = generate_defranco_brief()
    elif args.action == "gaming":
        news = fetch_rss_feed(RSS_FEEDS["dexerto"], max_items=10)
        result = "🎮 GAMING NEWS\n" + "\n".join([f"• {n.title}" for n in news])
    elif args.action == "tech":
        news = fetch_rss_feed(RSS_FEEDS["ars_technica"], max_items=10)
        result = "💻 TECH NEWS\n" + "\n".join([f"• {n.title}" for n in news])
    else:
        result = "Unknown action"
    
    print(result)


if __name__ == "__main__":
    main()
