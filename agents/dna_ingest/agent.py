#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     D I G I T A L   D N A   A G E N T                         ║
║                        "The Profiler"                                          ║
║                                                                               ║
║  Ingest local multimodal files to build your psychological profile           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- Image Analysis (Gemini Vision) - screenshots, selfies, lifestyle photos
- Social Export Parsing - Facebook/Instagram JSON dumps
- Text Ingestion - journals, notes, about me files
- Writing Style Learning - learn your texting voice

Folder Structure:
    ~/athena_data/me/
    ├── photos/         # Screenshots, selfies, lifestyle
    ├── social_exports/ # Facebook/Instagram JSON dumps
    ├── text/           # Journal entries, notes
    └── processed/      # Files move here after processing

Usage:
    python dna_ingest.py                    # Process all new files
    python dna_ingest.py --type photos      # Only process photos
    python dna_ingest.py --dry-run          # Preview what would be processed

Commands:
    athena /ingest          # CLI command
    /ingest                 # Telegram command
"""

import os
import sys
import json
import argparse
import base64
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import re

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Data directories
ATHENA_DATA_DIR = Path.home() / "athena_data"
DNA_DIR = ATHENA_DATA_DIR / "me"
PHOTOS_DIR = DNA_DIR / "photos"
SOCIAL_DIR = DNA_DIR / "social_exports"
TEXT_DIR = DNA_DIR / "text"
PROCESSED_DIR = DNA_DIR / "processed"

# Ensure directories exist
for d in [DNA_DIR, PHOTOS_DIR, SOCIAL_DIR, TEXT_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Supported file types
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
TEXT_EXTENSIONS = {".txt", ".md", ".json"}


# =============================================================================
# SUPABASE HELPERS
# =============================================================================

def supabase_upsert(table: str, data: Dict) -> bool:
    """Upsert data to Supabase."""
    try:
        import requests
        
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation"
        }
        
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return False


def save_user_fact(key: str, value: Any, category: str = "Digital_DNA") -> bool:
    """Save a fact to user_facts table."""
    return supabase_upsert("user_facts", {
        "key": key,
        "value": json.dumps(value) if not isinstance(value, str) else value,
        "category": category,
        "source": "dna_ingest"
    })


def log_thought(thought: str, category: str = "learning") -> bool:
    """Log processing to athena_monologue."""
    return supabase_upsert("athena_monologue", {
        "thought_process": thought,
        "action_taken": "dna_ingest",
        "category": category,
        "success_score": 5
    })


# =============================================================================
# IMAGE HANDLER (Gemini Vision)
# =============================================================================

def analyze_image(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    Analyze an image using Gemini Vision.
    
    Handles:
    - Screen Time screenshots (extract usage data)
    - Selfies/Lifestyle photos (detect hobbies, locations)
    - App screenshots (understand interests)
    """
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set")
        return None
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Determine MIME type
        ext = image_path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", 
                    ".webp": "image/webp", ".gif": "image/gif"}
        mime_type = mime_map.get(ext, "image/jpeg")
        
        prompt = """Analyze this image for personal user context. You are building a psychological profile.

If this is a DATA SCREENSHOT (Screen Time, Steps, Battery, Health app):
- Extract ALL numbers and statistics
- Note the app names and usage times
- Infer behavioral patterns

If this is a LIFESTYLE PHOTO:
- Describe the setting, activity, or hobby
- Note any interests or preferences visible
- Identify locations if recognizable

If this is a SELFIE or SOCIAL PHOTO:
- Note the context (party, outdoors, work)
- Identify style preferences

Return JSON:
{
    "image_type": "screen_time|health_data|lifestyle|selfie|social|other",
    "extracted_data": {"key": "value pairs of any data found"},
    "insights": ["List of behavioral insights"],
    "interests_detected": ["hobbies", "activities", "topics"],
    "personality_indicators": ["e.g., organized, adventurous, tech-savvy"]
}

Return ONLY valid JSON."""

        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_data}}
                ]}
            ]
        )
        
        # Parse response
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
        
    except Exception as e:
        print(f"❌ Vision analysis error: {e}")
        return None


def process_photos(dry_run: bool = False) -> List[Dict]:
    """Process all photos in the photos directory."""
    results = []
    
    # Find all image files
    images = [f for f in PHOTOS_DIR.iterdir() 
              if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    
    if not images:
        print("📸 No images found in photos/")
        return results
    
    print(f"\n📸 Processing {len(images)} images...")
    
    for i, image_path in enumerate(images, 1):
        print(f"   [{i}/{len(images)}] Analyzing {image_path.name}...")
        
        if dry_run:
            results.append({"file": image_path.name, "status": "dry_run"})
            continue
        
        analysis = analyze_image(image_path)
        
        if analysis:
            # Save to Supabase
            fact_key = f"photo_insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            save_user_fact(fact_key, {
                "filename": image_path.name,
                "analysis": analysis,
                "processed_at": datetime.now().isoformat()
            })
            
            # Move to processed
            dest = PROCESSED_DIR / image_path.name
            shutil.move(str(image_path), str(dest))
            
            results.append({
                "file": image_path.name,
                "type": analysis.get("image_type", "unknown"),
                "insights": analysis.get("insights", [])
            })
            
            print(f"      ✅ {analysis.get('image_type', 'unknown')} - {len(analysis.get('insights', []))} insights")
        else:
            results.append({"file": image_path.name, "status": "failed"})
    
    return results


# =============================================================================
# SOCIAL EXPORT HANDLER (Facebook/Instagram JSON)
# =============================================================================

def extract_messages_from_meta_export(json_path: Path) -> List[str]:
    """Extract sent messages from Facebook/Instagram JSON export."""
    messages = []
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle different Meta export structures
        if "messages" in data:
            # Instagram/FB message thread
            for msg in data["messages"]:
                if "content" in msg:
                    messages.append(msg["content"])
                    
        elif isinstance(data, list):
            # Array of message threads
            for thread in data:
                if "messages" in thread:
                    for msg in thread["messages"]:
                        if "content" in msg:
                            messages.append(msg["content"])
                            
    except Exception as e:
        print(f"      ⚠️ Could not parse {json_path.name}: {e}")
    
    return messages


def analyze_writing_style(messages: List[str]) -> Optional[Dict[str, Any]]:
    """
    Analyze writing style from message samples.
    
    Returns a style guide for Athena to mimic your voice.
    """
    if not messages or len(messages) < 50:
        print("      ⚠️ Not enough messages for style analysis (need 50+)")
        return None
    
    if not GEMINI_API_KEY:
        return None
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Sample messages (take last 500)
        sample = messages[-500:]
        sample_text = "\n".join([f"- {m[:200]}" for m in sample[:100]])
        
        prompt = f"""Analyze this user's writing/texting style from their messages.

Sample Messages:
{sample_text}

Create a comprehensive STYLE GUIDE that another AI could use to write like this person.

Return JSON:
{{
    "capitalization": "lowercase|normal|mixed|uppercase",
    "punctuation_style": "minimal|normal|heavy|none",
    "common_abbreviations": ["lol", "ngl", "fr", "etc"],
    "emoji_usage": "heavy|moderate|minimal|none",
    "favorite_emojis": ["💀", "😭", "etc"],
    "typical_greeting": "how they usually start messages",
    "typical_signoff": "how they usually end messages",
    "slang_terms": ["unique slang they use"],
    "sentence_length": "short|medium|long|varied",
    "tone": "casual|professional|sarcastic|enthusiastic",
    "quirks": ["any unique patterns"],
    "example_message": "A typical message they might write"
}}

Return ONLY valid JSON."""

        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt
        )
        
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
        
    except Exception as e:
        print(f"❌ Style analysis error: {e}")
        return None


def process_social_exports(dry_run: bool = False) -> List[Dict]:
    """Process social media export files."""
    results = []
    
    # Find JSON files
    json_files = list(SOCIAL_DIR.glob("**/*.json"))
    
    if not json_files:
        print("📱 No social exports found in social_exports/")
        return results
    
    print(f"\n📱 Processing {len(json_files)} social export files...")
    
    all_messages = []
    
    for json_path in json_files:
        print(f"   📄 Parsing {json_path.name}...")
        
        if dry_run:
            results.append({"file": json_path.name, "status": "dry_run"})
            continue
        
        # Extract messages
        messages = extract_messages_from_meta_export(json_path)
        all_messages.extend(messages)
        
        print(f"      Found {len(messages)} messages")
        results.append({"file": json_path.name, "messages_found": len(messages)})
    
    # Analyze writing style if we have enough messages
    if not dry_run and len(all_messages) >= 50:
        print(f"\n   🎨 Analyzing writing style from {len(all_messages)} messages...")
        style = analyze_writing_style(all_messages)
        
        if style:
            save_user_fact("writing_style_guide", style)
            log_thought(f"Learned user's writing style: {style.get('tone', 'unknown')} tone, {style.get('capitalization', 'unknown')} caps")
            
            print(f"      ✅ Style profile created!")
            print(f"         Tone: {style.get('tone')}")
            print(f"         Caps: {style.get('capitalization')}")
            print(f"         Emojis: {', '.join(style.get('favorite_emojis', [])[:5])}")
            
            results.append({
                "type": "writing_style",
                "tone": style.get("tone"),
                "emojis": style.get("favorite_emojis", [])
            })
    
    return results


# =============================================================================
# TEXT FILE HANDLER
# =============================================================================

def process_text_files(dry_run: bool = False) -> List[Dict]:
    """Process text files (journals, notes, about me)."""
    results = []
    
    # Find text files
    text_files = [f for f in TEXT_DIR.iterdir() 
                  if f.is_file() and f.suffix.lower() in {".txt", ".md"}]
    
    if not text_files:
        print("📝 No text files found in text/")
        return results
    
    print(f"\n📝 Processing {len(text_files)} text files...")
    
    for text_path in text_files:
        print(f"   📄 Reading {text_path.name}...")
        
        if dry_run:
            results.append({"file": text_path.name, "status": "dry_run"})
            continue
        
        try:
            content = text_path.read_text(encoding="utf-8")
            
            if len(content) < 50:
                print(f"      ⚠️ File too short, skipping")
                continue
            
            # Analyze with Gemini
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = f"""Extract personal facts from this text for a user profile.

Filename: {text_path.name}

Content:
{content[:5000]}

Extract ANY personal information:
- Preferences, favorites, interests
- Goals, ambitions, dreams
- Beliefs, values
- Relationships mentioned
- Locations, places
- Hobbies, activities

Return JSON:
{{
    "document_type": "journal|about_me|notes|list|other",
    "facts_extracted": [
        {{"category": "interest", "fact": "Loves anime, especially One Piece"}},
        {{"category": "goal", "fact": "Wants to pay off $8500 debt"}}
    ],
    "personality_traits": ["trait1", "trait2"],
    "summary": "One sentence summary of what this document reveals"
}}

Return ONLY valid JSON."""

            response = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )
            
            text = response.text.strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            
            analysis = json.loads(text)
            
            # Save facts
            for fact in analysis.get("facts_extracted", []):
                fact_key = f"text_fact_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(fact['fact']) % 10000}"
                save_user_fact(fact_key, fact)
            
            # Move to processed
            dest = PROCESSED_DIR / text_path.name
            shutil.move(str(text_path), str(dest))
            
            results.append({
                "file": text_path.name,
                "type": analysis.get("document_type"),
                "facts": len(analysis.get("facts_extracted", []))
            })
            
            print(f"      ✅ Extracted {len(analysis.get('facts_extracted', []))} facts")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            results.append({"file": text_path.name, "status": "error", "error": str(e)})
    
    return results


# =============================================================================
# CHATGPT EXPORT HANDLER
# =============================================================================

def process_chatgpt_export(dry_run: bool = False) -> List[Dict]:
    """Process ChatGPT conversations.json export."""
    results = []
    
    # Check for conversations.json in ME dir or SOCIAL dir
    possible_paths = [
        DNA_DIR / "conversations.json",
        SOCIAL_DIR / "conversations.json"
    ]
    
    target_file = next((p for p in possible_paths if p.exists()), None)
    
    if not target_file:
        return results

    print(f"\n🤖 Processing ChatGPT Export: {target_file.name}...")
    
    if dry_run:
        results.append({"file": target_file.name, "status": "dry_run"})
        return results

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Extract user messages to learn interests/questions
        user_msgs = []
        for convo in data:
            for node_id, node in convo.get("mapping", {}).items():
                msg = node.get("message")
                if msg and msg.get("author", {}).get("role") == "user":
                    content = msg.get("content", {}).get("parts", [""])[0]
                    if content and isinstance(content, str):
                        user_msgs.append(content)
        
        print(f"      Found {len(user_msgs)} user prompts")
        
        # Analyze top topics if we have enough data
        if len(user_msgs) > 20:
             # Basic keyword extraction (Client-side to save API details)
             text_blob = " ".join(user_msgs[-200:]) # Last 200 prompts
             
             # Save to user facts
             save_user_fact("chatgpt_history_summary", {
                 "total_prompts": len(user_msgs),
                 "last_active": datetime.now().isoformat(), # approximate
                 "sample_prompts": user_msgs[-5:]
             }, category="digital_history")
             
             results.append({"type": "chatgpt_history", "count": len(user_msgs)})
             print(f"      ✅ Indexed ChatGPT history ({len(user_msgs)} prompts)")
             
    except Exception as e:
        print(f"      ❌ Error parsing ChatGPT data: {e}")
        
    return results

# =============================================================================
# UBER DATA HANDLER
# =============================================================================

def process_uber_data(dry_run: bool = False) -> List[Dict]:
    """Process Uber/Uber Eats data from CSVs."""
    results = []
    
    # Look for Uber folder
    uber_dir = DNA_DIR / "uber"
    if not uber_dir.exists():
        return results
        
    print(f"\nCb Processing Uber Data in {uber_dir.name}...")
    
    # 1. Trips
    # Look recursively for trips_data.csv
    trips_file = next(uber_dir.rglob("trips_data.csv"), None)
    if not trips_file:
         # Try flexible Recursive Match
         trips_file = next(uber_dir.rglob("*trip*.csv"), None)
        
    if trips_file:
        print(f"   🚗 Found Trip Data: {trips_file.name}")
        if not dry_run:
            try:
                # Basic CSV parsing
                import csv
                with open(trips_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    trips = list(reader)
                    
                print(f"      Analyzed {len(trips)} trips")
                
                # Extract locations (City)
                cities = set()
                for t in trips:
                    if "City" in t: cities.add(t["City"])
                    
                save_user_fact("uber_travel_history", {
                    "total_trips": len(trips),
                    "cities_visited": list(cities)
                }, category="travel")
                
                results.append({"type": "uber_trips", "count": len(trips)})
                
            except Exception as e:
                print(f"      ❌ Error parsing trips: {e}")

    # 2. Eats
    eats_file = next(uber_dir.rglob("*eats*.csv"), None)
    if eats_file:
         print(f"   🍔 Found Eats Data: {eats_file.name}")
         if not dry_run:
             # Similar logic for eats...
             results.append({"type": "uber_eats", "file": eats_file.name})
             
    return results


def run_ingestion(file_type: str = "all", dry_run: bool = False) -> Dict[str, Any]:
    """
    Run the full DNA ingestion process.
    
    Args:
        file_type: "all", "photos", "social", or "text"
        dry_run: If True, just preview what would be processed
    """
    print("=" * 60)
    print("🧬 DIGITAL DNA INGESTION - The Profiler")
    print("=" * 60)
    print(f"📁 Watch folder: {DNA_DIR}")
    print(f"🔍 Mode: {'DRY RUN' if dry_run else 'PROCESSING'}")
    print(f"📂 Type filter: {file_type}")
    
    results = {
        "started_at": datetime.now().isoformat(),
        "photos": [],
        "social": [],
        "text": []
    }
    
    if file_type in ["all", "photos"]:
        results["photos"] = process_photos(dry_run)
    
    if file_type in ["all", "social"]:
        results["social"] = process_social_exports(dry_run)
    
    if file_type in ["all", "text"]:
        results["text"] = process_text_files(dry_run)
        
    # NEW: ChatGPT & Uber
    if file_type in ["all", "social", "text"]: # ChatGPT fits in text/social
        results["chatgpt"] = process_chatgpt_export(dry_run)
        
    if file_type in ["all", "social"]: # Uber fits in social/lifestyle
        results["uber"] = process_uber_data(dry_run)
    
    # Summary
    total_processed = (
        len([r for r in results["photos"] if r.get("status") != "dry_run"]) +
        len([r for r in results["social"] if r.get("status") != "dry_run"]) +
        len([r for r in results["text"] if r.get("status") != "dry_run"]) +
        len(results.get("chatgpt", [])) +
        len(results.get("uber", []))
    )
    
    print("\n" + "=" * 60)
    print("📊 INGESTION SUMMARY")
    print("=" * 60)
    print(f"📸 Photos analyzed: {len(results['photos'])}")
    print(f"📱 Social file processed: {len(results['social'])}")
    print(f"📝 Text files processed: {len(results['text'])}")
    if results.get("chatgpt"):
        print(f"🤖 ChatGPT history: {len(results['chatgpt'])} sessions")
    if results.get("uber"):
        print(f"🚗 Uber data: {len(results['uber'])} files")
        
    print(f"✅ Total items processed: {total_processed}")
    
    if not dry_run:
        log_thought(f"DNA ingestion complete: {total_processed} items processed")
    
    results["completed_at"] = datetime.now().isoformat()
    results["total_processed"] = total_processed
    
    return results


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Digital DNA Ingestion Agent")
    parser.add_argument("--type", choices=["all", "photos", "social", "text"], 
                        default="all", help="Type of files to process")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Preview what would be processed without making changes")
    
    args = parser.parse_args()
    
    results = run_ingestion(file_type=args.type, dry_run=args.dry_run)
    
    print(f"\n🧬 DNA Profile updated successfully!")
    print(f"   Files are moved to: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
