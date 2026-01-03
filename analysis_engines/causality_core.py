#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     C A U S A L I T Y   E N G I N E                           ║
║                   "The Inspiration Graph"                                      ║
║                                                                               ║
║  Connects Input (what you watch/read) to Output (what you buy/do)            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Principle: Not just WHAT you spent, but WHY you spent it.

Architecture:
1. Influence Mapping - Extract keywords from media consumption
2. Attribution Check - Match purchases against influence cloud  
3. Insight Reporting - Calculate "Influence Cost" by source

Example:
    Watch: Bleach anime
    Buy: "Zangetsu sword" 
    → Detected: Purchase inspired by Bleach ($50)
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Influence window (days)
INFLUENCE_WINDOW_DAYS = 45
INFLUENCE_EXPIRY_DAYS = 60

# Cache for local testing
ATHENA_DATA_DIR = Path.home() / "athena_data"
INFLUENCE_CACHE = ATHENA_DATA_DIR / ".influence_cloud.json"


# =============================================================================
# INFLUENCE CLOUD STORAGE
# =============================================================================

class InfluenceCloud:
    """
    Stores active influences from media consumption.
    
    Each influence has:
    - source: Where it came from (YouTube, Anime, Book, etc.)
    - title: The specific content
    - keywords: Associated purchasable/actionable keywords
    - timestamp: When it was consumed
    - expires: When influence fades (60 days default)
    """
    
    def __init__(self):
        self.influences = []
        self._load()
    
    def _load(self) -> None:
        """Load from cache or Supabase."""
        if INFLUENCE_CACHE.exists():
            try:
                self.influences = json.loads(INFLUENCE_CACHE.read_text())
            except:
                self.influences = []
        
        # Clean expired
        self._clean_expired()
    
    def _save(self) -> None:
        """Save to cache and optionally Supabase."""
        ATHENA_DATA_DIR.mkdir(parents=True, exist_ok=True)
        INFLUENCE_CACHE.write_text(json.dumps(self.influences, indent=2, default=str))
        
        # Sync to Supabase if configured
        if SUPABASE_URL and SUPABASE_KEY:
            self._sync_to_supabase()
    
    def _sync_to_supabase(self) -> None:
        """Sync influence cloud to Supabase."""
        try:
            import requests
            
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            # Sync only the most recent/active influences to avoid massive payloads
            # In a real scenario, we might track which ones are dirty/new
            active_influences = self.get_active_influences()
            
            # Prepare batch upsert
            rows = []
            for inf in active_influences:
                 rows.append({
                     "source": inf["source"],
                     "title": inf["title"],
                     "category": inf.get("category", "media"),
                     "keywords": inf.get("keywords", []),
                     "consumed_at": inf["timestamp"],
                     "expires_at": inf["expires"],
                     "metadata": {} 
                 })
                 
            if not rows:
                return

            # Batch insert/upsert
            # Note: unique constraints might not be set on title/source in schema yet, 
            # so we just insert. If duplicates are an issue, we'd need a unique index.
            # For now, let's just insert new ones (ignoring existing is harder without a unique key)
            # A simple approach for this agentic context: just insert the last added one if we are adding one by one,
            # but since this syncs the whole list, let's try to just insert the last 5 to keep it simple and avoid massive duplications on every run
            
            # Better approach: The script seems to add items one by one or in batch.
            # Let's just modify add_influence to sync THAT specific item, rather than full sync.
            pass 

        except Exception as e:
            print(f"Sync error: {e}")

    def _sync_item_to_supabase(self, influence_item: Dict) -> None:
        """Sync a single influence item to Supabase."""
        if not (SUPABASE_URL and SUPABASE_KEY):
            return

        try:
            import requests
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            row = {
                 "source": influence_item["source"],
                 "title": influence_item["title"],
                 "category": influence_item.get("category", "media"),
                 "keywords": influence_item.get("keywords", []),
                 "consumed_at": influence_item["timestamp"],
                 "expires_at": influence_item["expires"]
            }
            
            requests.post(
                f"{SUPABASE_URL}/rest/v1/influence_cloud",
                headers=headers,
                json=row,
                timeout=10
            )
        except Exception as e:
             print(f"Supabase sync error: {e}")
    
    def _clean_expired(self) -> None:
        """Remove expired influences."""
        now = datetime.now()
        self.influences = [
            inf for inf in self.influences
            if datetime.fromisoformat(inf.get("expires", now.isoformat())) > now
        ]
    
    def add_influence(self, source: str, title: str, keywords: List[str],
                      category: str = "media") -> None:
        """Add a new influence to the cloud."""
        now = datetime.now()
        
        influence = {
            "source": source,
            "title": title,
            "category": category,
            "keywords": [kw.lower() for kw in keywords],
            "timestamp": now.isoformat(),
            "expires": (now + timedelta(days=INFLUENCE_EXPIRY_DAYS)).isoformat()
        }
        
        self.influences.append(influence)
        self._save()
        self._sync_item_to_supabase(influence)
    
    
    def sync_all_to_cloud(self) -> int:
        """
        Force sync all active influences to Supabase.
        Returns number of items synced.
        """
        active = self.get_active_influences()
        count = 0
        for inf in active:
            # We use individual item sync for now as it handles the logic
            self._sync_item_to_supabase(inf)
            count += 1
        return count
    
    def find_matches(self, text: str, window_days: int = INFLUENCE_WINDOW_DAYS
                     ) -> List[Dict[str, Any]]:
        """
        Find influences that match a text (product name, search, etc).
        
        Returns list of matching influences with match score.
        """
        text_lower = text.lower()
        text_words = set(re.findall(r'\b\w+\b', text_lower))
        
        cutoff = datetime.now() - timedelta(days=window_days)
        matches = []
        
        for inf in self.influences:
            inf_time = datetime.fromisoformat(inf["timestamp"])
            
            # Must be within window
            if inf_time < cutoff:
                continue
            
            # Check keyword matches
            keywords = set(inf.get("keywords", []))
            overlap = text_words & keywords
            
            # Also check if title words appear
            title_words = set(re.findall(r'\b\w+\b', inf["title"].lower()))
            title_overlap = text_words & title_words
            
            total_matches = len(overlap) + len(title_overlap)
            
            if total_matches > 0:
                matches.append({
                    "influence": inf,
                    "matched_keywords": list(overlap | title_overlap),
                    "score": total_matches / max(len(text_words), 1),
                    "days_ago": (datetime.now() - inf_time).days
                })
        
        # Sort by score
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches
    
    def get_active_influences(self, category: str = None) -> List[Dict]:
        """Get all active (non-expired) influences."""
        self._clean_expired()
        
        if category:
            return [inf for inf in self.influences if inf.get("category") == category]
        return self.influences


# =============================================================================
# INFLUENCE EXTRACTOR (Gemini)
# =============================================================================

def extract_influence_keywords(title: str, source: str = "media") -> List[str]:
    """
    Use Gemini to extract purchasable/actionable keywords from media titles.
    
    Example:
        "Bleach" → ["sword", "katana", "kimono", "figure", "poster"]
        "Atomic Habits" → ["journal", "planner", "habit tracker"]
    """
    if not GEMINI_API_KEY:
        # Fallback to simple extraction
        return title.lower().split()[:5]
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""Extract 5-8 related PHYSICAL OBJECTS or PRODUCTS that someone might buy after consuming this media.

Source: {source}
Title: "{title}"

Return ONLY a JSON array of lowercase keywords. Examples:
- If title is "Bleach" (anime): ["sword", "katana", "kimono", "figure", "poster", "cosplay"]
- If title is "Atomic Habits" (book): ["journal", "planner", "habit tracker", "notebook", "calendar"]
- If title is "MKBHD" (tech channel): ["smartphone", "laptop", "headphones", "camera", "gadget"]

Return only the JSON array, nothing else."""

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        keywords = json.loads(text)
        return [str(kw).lower() for kw in keywords if isinstance(kw, str)]
        
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        # Fallback
        return title.lower().split()[:5]


def batch_extract_influences(media_items: List[Dict]) -> List[Dict]:
    """
    Process multiple media items and extract influences.
    
    Each item should have: title, source, category
    """
    results = []
    
    for item in media_items:
        title = item.get("title", "")
        source = item.get("source", "unknown")
        category = item.get("category", "media")
        
        if not title:
            continue
        
        keywords = extract_influence_keywords(title, source)
        
        results.append({
            "title": title,
            "source": source,
            "category": category,
            "keywords": keywords
        })
    
    return results


# =============================================================================
# ATTRIBUTION ENGINE
# =============================================================================

class AttributionEngine:
    """
    Attributes purchases/actions to their inspirations.
    
    Connects Output (purchases) to Input (media consumption).
    """
    
    def __init__(self):
        self.cloud = InfluenceCloud()
        self.attributed_purchases = []
    
    def attribute_purchase(self, item_name: str, amount: float,
                            timestamp: datetime = None) -> Optional[Dict]:
        """
        Check if a purchase was influenced by recent media.
        
        Returns attribution data if match found.
        """
        timestamp = timestamp or datetime.now()
        
        # Find matching influences
        matches = self.cloud.find_matches(item_name)
        
        if not matches:
            return None
        
        # Take best match
        best = matches[0]
        
        attribution = {
            "item": item_name,
            "amount": amount,
            "timestamp": timestamp.isoformat(),
            "inspired_by": {
                "title": best["influence"]["title"],
                "source": best["influence"]["source"],
                "category": best["influence"]["category"],
                "consumed_at": best["influence"]["timestamp"]
            },
            "matched_keywords": best["matched_keywords"],
            "confidence": min(best["score"], 1.0),
            "days_after_consumption": best["days_ago"]
        }
        
        self.attributed_purchases.append(attribution)
        
        # Sync to Supabase
        self._sync_attribution(attribution)
        
        return attribution

    def _sync_attribution(self, attr: Dict) -> None:
        """Save attribution to Supabase."""
        if not (SUPABASE_URL and SUPABASE_KEY):
            return

        try:
            import requests
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            row = {
                "item_name": attr["item"],
                "amount": attr["amount"],
                "purchase_date": attr["timestamp"],
                "influence_source": attr["inspired_by"]["title"],
                "influence_category": attr["inspired_by"]["category"],
                "matched_keywords": attr["matched_keywords"],
                "confidence": attr["confidence"],
                "days_after_consumption": attr["days_after_consumption"]
            }
            
            requests.post(
                f"{SUPABASE_URL}/rest/v1/purchase_attributions",
                headers=headers,
                json=row,
                timeout=10
            )
        except Exception as e:
            print(f"Attribution sync error: {e}")
    
    def get_influence_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate "Influence Cost" report.
        
        Shows how much you spent inspired by each category/source.
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        # Group by category
        by_category = defaultdict(lambda: {"total": 0, "items": []})
        by_source = defaultdict(lambda: {"total": 0, "items": []})
        
        for attr in self.attributed_purchases:
            attr_time = datetime.fromisoformat(attr["timestamp"])
            if attr_time < cutoff:
                continue
            
            insp = attr["inspired_by"]
            amount = attr["amount"]
            
            # By category
            cat = insp["category"]
            by_category[cat]["total"] += amount
            by_category[cat]["items"].append(attr["item"])
            
            # By specific source
            source = f"{insp['title']} ({insp['source']})"
            by_source[source]["total"] += amount
            by_source[source]["items"].append(attr["item"])
        
        # Sort by total
        sorted_categories = sorted(
            by_category.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )
        
        sorted_sources = sorted(
            by_source.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )
        
        return {
            "period_days": days,
            "total_attributed": sum(c[1]["total"] for c in sorted_categories),
            "by_category": dict(sorted_categories[:10]),
            "by_source": dict(sorted_sources[:10]),
            "top_influence": sorted_sources[0] if sorted_sources else None
        }
    
    def format_report(self, report: Dict) -> str:
        """Format influence report for display."""
        output = [
            "💰 **INFLUENCE COST REPORT**",
            f"   Period: Last {report['period_days']} days",
            f"   Total Attributed: ${report['total_attributed']:.2f}",
            "\n📊 **By Category:**"
        ]
        
        for cat, data in report.get("by_category", {}).items():
            output.append(f"   • {cat}: ${data['total']:.2f} ({len(data['items'])} items)")
        
        if report.get("top_influence"):
            source, data = report["top_influence"]
            output.append(f"\n🎯 **Top Influence:** {source}")
            output.append(f"   Cost: ${data['total']:.2f}")
        
        return "\n".join(output)


# =============================================================================
# INTEGRATION WITH DNA INGEST
# =============================================================================

def process_media_for_influences(media_data: List[Dict]) -> int:
    """
    Process ingested media and add to influence cloud.
    
    Called by dna_ingest.py after parsing YouTube/Spotify/Anime data.
    """
    cloud = InfluenceCloud()
    added = 0
    
    for item in media_data:
        title = item.get("title", "")
        source = item.get("source", "unknown")
        category = item.get("category", "media")
        
        if not title or len(title) < 3:
            continue
        
        # Extract keywords
        keywords = extract_influence_keywords(title, source)
        
        if keywords:
            cloud.add_influence(
                source=source,
                title=title,
                keywords=keywords,
                category=category
            )
            added += 1
    
    return added


def tag_transaction(item_name: str, amount: float, 
                    timestamp: datetime = None) -> Optional[Dict]:
    """
    Tag a transaction with its inspiration source.
    
    Called by finance_manager.py when logging expenses.
    
    Returns:
        Attribution metadata if influence found, else None
    """
    engine = AttributionEngine()
    return engine.attribute_purchase(item_name, amount, timestamp)


# =============================================================================
# MAIN CLI
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Causality Engine - Inspiration Tracking")
    parser.add_argument("--add", nargs=3, metavar=("SOURCE", "TITLE", "CATEGORY"),
                        help="Add an influence manually")
    parser.add_argument("--check", help="Check if a purchase was influenced")
    parser.add_argument("--amount", type=float, default=0, help="Purchase amount")
    parser.add_argument("--report", action="store_true", help="Show influence report")
    parser.add_argument("--list", action="store_true", help="List active influences")
    
    args = parser.parse_args()
    
    print("🔗 Causality Engine - The Inspiration Graph")
    print("=" * 50)
    
    cloud = InfluenceCloud()
    engine = AttributionEngine()
    
    if args.add:
        source, title, category = args.add
        keywords = extract_influence_keywords(title, source)
        cloud.add_influence(source, title, keywords, category)
        print(f"✅ Added influence: {title}")
        print(f"   Keywords: {', '.join(keywords)}")
        
    elif args.check:
        attr = engine.attribute_purchase(args.check, args.amount)
        if attr:
            insp = attr["inspired_by"]
            print(f"🎯 ATTRIBUTION DETECTED!")
            print(f"   Item: {args.check}")
            print(f"   Inspired by: {insp['title']} ({insp['source']})")
            print(f"   Matched: {', '.join(attr['matched_keywords'])}")
            print(f"   Consumed: {attr['days_after_consumption']} days ago")
        else:
            print(f"❌ No influence match found for: {args.check}")
            
    elif args.report:
        # Add some demo data if empty
        if not engine.attributed_purchases:
            print("⚠️ No attributions yet. Demo mode:")
            engine.attribute_purchase("Zangetsu Sword", 45.0)
            engine.attribute_purchase("Straw Hat", 15.0)
        
        report = engine.get_influence_report()
        print(engine.format_report(report))
        
    elif args.list:
        influences = cloud.get_active_influences()
        print(f"📚 Active Influences ({len(influences)}):")
        for inf in influences[:20]:
            days_left = (datetime.fromisoformat(inf["expires"]) - datetime.now()).days
            print(f"   • {inf['title']} ({inf['source']}) - {days_left}d left")
            print(f"     Keywords: {', '.join(inf['keywords'][:5])}")
            
    else:
        # Demo
        print("\n📺 Adding demo influences...")
        
        cloud.add_influence("Anime", "Bleach", 
                           ["sword", "katana", "zangetsu", "figure", "poster"], "anime")
        cloud.add_influence("Anime", "One Piece",
                           ["straw hat", "pirate", "figure", "poster", "ship"], "anime")
        cloud.add_influence("YouTube", "MKBHD Tech Review",
                           ["smartphone", "laptop", "headphones", "gadget"], "tech")
        
        print("✅ Added demo influences")
        print("\n🛒 Checking purchases...")
        
        # Reload engine to pick up new cloud data
        engine = AttributionEngine()
        
        purchases = [
            ("Zangetsu replica sword", 50),
            ("Straw Hat cosplay", 20),
            ("New headphones", 150),
            ("Groceries", 45)  # No match expected
        ]
        
        for item, amount in purchases:
            attr = engine.attribute_purchase(item, amount)
            if attr:
                insp = attr["inspired_by"]
                print(f"   ✅ {item} (${amount}) ← {insp['title']}")
            else:
                print(f"   ❌ {item} (${amount}) ← No influence detected")
        
        print(f"\n" + engine.format_report(engine.get_influence_report()))


if __name__ == "__main__":
    main()
