#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         M S P   S C O U T                                     ║
║                        "The Local Guide"                                       ║
║                                                                               ║
║  Division II: Intelligence (The News Room)                                    ║
║  Find events in Minneapolis / Roseville area                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Focuses on: Tech meetups, Art events, Food festivals, Concerts
Areas: Minneapolis, Roseville, St. Paul

Usage:
  python msp_scout.py --action scan
  python msp_scout.py --action scan --category tech
  python msp_scout.py --action scan --days 14
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

# Event sources
EVENT_SOURCES = {
    "racket_mn": "https://racketmn.com/events/",
    "mpls_org": "https://www.minneapolis.org/calendar/",
    "meetup_tech": "https://www.meetup.com/find/?location=us--mn--Minneapolis&source=EVENTS&categoryId=546",
    "eventbrite_mpls": "https://www.eventbrite.com/d/mn--minneapolis/events/",
}

# Interest categories
CATEGORIES = {
    "tech": ["tech", "coding", "python", "javascript", "ai", "startup", "developer", "hackathon", "meetup"],
    "art": ["art", "gallery", "museum", "exhibition", "painting", "sculpture", "photography"],
    "food": ["food", "restaurant", "tasting", "brewery", "wine", "cooking", "culinary", "foodie"],
    "music": ["concert", "music", "live", "band", "show", "festival", "dj"],
    "outdoor": ["hiking", "biking", "outdoor", "park", "nature", "lake", "trail"],
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class LocalEvent:
    """A local event."""
    name: str
    date: str
    location: str
    category: str
    url: str
    source: str
    price: str = "Free"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "date": self.date,
            "location": self.location,
            "category": self.category,
            "url": self.url,
            "source": self.source,
            "price": self.price
        }


# =============================================================================
# WEB SCRAPING
# =============================================================================

def scrape_eventbrite_rss() -> List[LocalEvent]:
    """
    Fetch Minneapolis events from Eventbrite RSS feed.
    """
    events = []
    
    try:
        import feedparser
        import requests
        
        # Use a search-based approach
        # Note: Eventbrite doesn't have a public RSS, so we'll use their API-like endpoints
        url = "https://www.eventbrite.com/d/mn--minneapolis/events/"
        
        # For now, return placeholder - in production would use BeautifulSoup
        # or the Eventbrite API
        
    except Exception as e:
        print(f"⚠️ Eventbrite scrape error: {e}")
    
    return events


def scrape_meetup_tech() -> List[LocalEvent]:
    """
    Scrape tech meetups from Meetup.com Minneapolis.
    """
    events = []
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Tech meetups in Minneapolis
        url = "https://www.meetup.com/find/?location=us--mn--Minneapolis&source=EVENTS&categoryId=546"
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find event cards (structure may vary)
            event_cards = soup.find_all('div', class_=re.compile('eventCard'))
            
            for card in event_cards[:10]:
                try:
                    title_elem = card.find('h2') or card.find('h3')
                    link_elem = card.find('a', href=True)
                    
                    if title_elem and link_elem:
                        events.append(LocalEvent(
                            name=title_elem.get_text(strip=True),
                            date="See link",
                            location="Minneapolis, MN",
                            category="tech",
                            url=link_elem['href'],
                            source="Meetup"
                        ))
                except:
                    continue
                    
    except ImportError:
        print("⚠️ beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    except Exception as e:
        print(f"⚠️ Meetup scrape error: {e}")
    
    return events


def get_sample_events() -> List[LocalEvent]:
    """
    Return sample Minneapolis events for demo purposes.
    In production, these would come from actual scraping.
    """
    return [
        LocalEvent(
            name="Python Minneapolis Meetup",
            date="Every 2nd Thursday",
            location="Clockwork, Minneapolis",
            category="tech",
            url="https://www.meetup.com/python-minneapolis/",
            source="Meetup",
            price="Free"
        ),
        LocalEvent(
            name="JavaScript MN",
            date="Monthly",
            location="Various locations, Minneapolis",
            category="tech",
            url="https://www.meetup.com/JavaScriptMN/",
            source="Meetup",
            price="Free"
        ),
        LocalEvent(
            name="First Avenue Concerts",
            date="Various",
            location="First Avenue, Minneapolis",
            category="music",
            url="https://first-avenue.com/calendar/",
            source="First Avenue",
            price="Varies"
        ),
        LocalEvent(
            name="Walker Art Center Events",
            date="Ongoing",
            location="Walker Art Center",
            category="art",
            url="https://walkerart.org/calendar",
            source="Walker",
            price="Free-$20"
        ),
        LocalEvent(
            name="Mill City Farmers Market",
            date="Saturdays, May-Oct",
            location="Mill City Museum",
            category="food",
            url="https://millcityfarmersmarket.org/",
            source="Local",
            price="Free entry"
        ),
        LocalEvent(
            name="Roseville Skating Center",
            date="Winter Season",
            location="Roseville, MN",
            category="outdoor",
            url="https://www.cityofroseville.com/skating",
            source="City of Roseville",
            price="Free-$10"
        ),
    ]


# =============================================================================
# EVENT FILTERING
# =============================================================================

def filter_by_category(events: List[LocalEvent], category: str) -> List[LocalEvent]:
    """Filter events by category."""
    if not category or category == "all":
        return events
    
    keywords = CATEGORIES.get(category.lower(), [category.lower()])
    
    filtered = []
    for event in events:
        event_text = f"{event.name} {event.description} {event.category}".lower()
        if any(kw in event_text for kw in keywords):
            filtered.append(event)
    
    return filtered


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_events(events: List[LocalEvent], category: str = None) -> str:
    """Format events for display."""
    output = []
    output.append("=" * 60)
    output.append(f"🏙️ MSP SCOUT - Minneapolis Events")
    if category:
        output.append(f"📂 Category: {category.capitalize()}")
    output.append("=" * 60)
    output.append("")
    
    if not events:
        output.append("📭 No events found matching your criteria.")
        output.append("")
        output.append("Try: --category tech | art | food | music | outdoor")
        return "\n".join(output)
    
    # Group by category
    by_category: Dict[str, List[LocalEvent]] = {}
    for event in events:
        cat = event.category.capitalize()
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(event)
    
    for cat, cat_events in by_category.items():
        emoji = {
            "Tech": "💻", "Art": "🎨", "Food": "🍕", 
            "Music": "🎵", "Outdoor": "🌲"
        }.get(cat, "📅")
        
        output.append(f"{emoji} {cat.upper()}")
        output.append("-" * 40)
        
        for event in cat_events[:5]:
            output.append(f"  📍 {event.name}")
            output.append(f"     📅 {event.date}")
            output.append(f"     📍 {event.location}")
            output.append(f"     💰 {event.price}")
            output.append(f"     🔗 {event.url}")
            output.append("")
    
    output.append("=" * 60)
    output.append(f"Total: {len(events)} events found")
    
    return "\n".join(output)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="MSP Scout - Find Minneapolis events"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["scan", "list-categories"],
        default="scan",
        help="Action to perform"
    )
    
    parser.add_argument(
        "--category", "-c",
        choices=["tech", "art", "food", "music", "outdoor", "all"],
        default="all",
        help="Event category filter"
    )
    
    parser.add_argument("--days", "-d", type=int, default=7, help="Days ahead to search")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.action == "list-categories":
        print("📂 Available Categories:")
        for cat, keywords in CATEGORIES.items():
            print(f"  • {cat}: {', '.join(keywords[:4])}...")
        return
    
    # Get events
    print("🔍 Scanning for Minneapolis events...")
    
    # Get from various sources
    events = []
    events.extend(get_sample_events())  # Demo data
    events.extend(scrape_meetup_tech())  # Live scraping attempt
    
    # Filter by category
    if args.category != "all":
        events = filter_by_category(events, args.category)
    
    if args.json:
        print(json.dumps([e.to_dict() for e in events], indent=2))
    else:
        print(format_events(events, args.category if args.category != "all" else None))


if __name__ == "__main__":
    main()
