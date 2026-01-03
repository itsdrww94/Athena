import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import re

from core.contracts.event_schema import CanonicalEvent

logger = logging.getLogger("athena.connectors.youtube")

class YouTubeConnector:
    """
    Media Diet Analyst (Ingestor).
    Parses Google Takeout Watch History and generates WATCH events.
    """
    
    SOURCE = "youtube_takeout"
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        
    def process(self) -> List[CanonicalEvent]:
        """Parse file and return events."""
        if not self.file_path.exists():
            logger.error(f"File not found: {self.file_path}")
            return []
            
        # Support JSON format from Takeout
        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        events = []
        for item in raw_data:
            evt = self._parse_item(item)
            if evt:
                events.append(evt)
                
        return events

    def _parse_item(self, item: Dict) -> Any:
        try:
            # Extract core fields
            title = item.get("title", "Unknown Video")
            if title.startswith("Watched "):
                title = title[8:]
                
            title_url = item.get("titleUrl", "")
            time_str = item.get("time", "")
            
            # Parse Timestamp (ISO 8601 expected from Takeout JSON)
            # Example: "2023-12-25T21:19:47.123Z"
            try:
                # Handle variants
                ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except ValueError:
                return None

            source_id = title_url # Use URL as ID if available
            if not source_id:
                source_id = title + time_str
                
            # Create Event ID
            event_id = CanonicalEvent.create_id(self.SOURCE, source_id, ts)
            
            # Extract Channel
            channel = ""
            if "subtitles" in item:
                channel = item["subtitles"][0].get("name", "")
                
            return CanonicalEvent(
                event_id=event_id,
                event_type="WATCH",
                source=self.SOURCE,
                timestamp=ts,
                data={
                    "video_title": title,
                    "channel_name": channel,
                    "url": title_url
                },
                derived={}
            )
        except Exception as e:
            logger.warning(f"Failed to parse item: {e}")
            return None

class Sessionizer:
    """
    Groups WATCH events into Sessions.
    Rule: 30 minutes gap ends a session.
    """
    
    GAP_THRESHOLD_MINUTES = 30
    
    @staticmethod
    def sessionize(events: List[CanonicalEvent]) -> List[Dict]:
        """
        Sorts events and groups them. Returns list of Session objects (dicts).
        """
        if not events:
            return []
            
        # Sort by time
        sorted_events = sorted(events, key=lambda x: x.timestamp)
        
        sessions = []
        current_session = []
        
        for evt in sorted_events:
            if not current_session:
                current_session.append(evt)
                continue
                
            last_evt = current_session[-1]
            gap = (evt.timestamp - last_evt.timestamp).total_seconds() / 60
            
            if gap <= Sessionizer.GAP_THRESHOLD_MINUTES:
                current_session.append(evt)
            else:
                # End session
                sessions.append(Sessionizer._finalize_session(current_session))
                current_session = [evt]
                
        if current_session:
            sessions.append(Sessionizer._finalize_session(current_session))
            
        return sessions

    @staticmethod
    def _finalize_session(events: List[CanonicalEvent]) -> Dict:
        start = events[0].timestamp
        end = events[-1].timestamp
        duration_minutes = (end - start).total_seconds() / 60
        
        # Heuristics
        is_late_night = False
        if start.hour < 5 or start.hour >= 23:
            is_late_night = True
            
        return {
            "session_id": hashlib.md5(f"{start.isoformat()}".encode()).hexdigest(),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "video_count": len(events),
            "duration_minutes": duration_minutes,
            "is_late_night": is_late_night,
            "titles": [e.data.get("video_title") for e in events]
        }
