"""
Local Data Analyzer Agent
=========================
Scan, classify, parse, and summarize local data files.
Handles exports from ChatGPT, Spotify, Uber, and other sources.

This agent is the HARD ROUTE for requests like "analyze the data folder".
It should NEVER be confused with web research.
"""

import os
import json
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger("athena.agents.local_data_analyzer")


@dataclass
class FileInfo:
    """Information about a scanned file."""
    path: str
    name: str
    extension: str
    size_bytes: int
    source_type: str = "unknown"  # chatgpt, spotify, uber, unknown
    parsed_items: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AnalysisResult:
    """Result of a local data analysis."""
    task_id: str
    data_path: str
    total_files: int
    files_by_source: Dict[str, int]
    summary: str
    top_patterns: List[str]
    recommendations: List[str]
    file_details: List[FileInfo]
    status: str = "COMPLETED"
    error: Optional[str] = None


class LocalDataAnalyzer:
    """
    Local Data Analyzer - Scans and analyzes local files.
    
    This is DETERMINISTICALLY routed to when user says:
    - "analyze the data folder"
    - "scan local files"
    - "check my chatgpt/spotify/uber logs"
    
    It should NEVER trigger web research.
    """
    
    # Known file signatures for classification
    SOURCE_SIGNATURES = {
        "chatgpt": [
            "conversations.json",
            "chat.html",
            "message_",
        ],
        "spotify": [
            "StreamingHistory",
            "YourLibrary",
            "Playlist",
            "endsong_",
        ],
        "uber": [
            "Rider",
            "trips_data",
            "account_data",
        ],
        "google": [
            "Takeout",
            "My Activity",
        ],
    }
    
    def __init__(self, default_path: str = "./data"):
        self.default_path = Path(default_path)
        self.base_dir = Path(__file__).parent.parent.parent  # Athena_Project root
        
    def scan(self, data_path: str = None) -> Dict[str, Any]:
        """
        Scan folder and create file inventory.
        
        Args:
            data_path: Path to scan (defaults to ./data)
            
        Returns:
            Dict with file inventory and metadata
        """
        path = Path(data_path) if data_path else self.default_path
        
        # Handle relative paths
        if not path.is_absolute():
            path = self.base_dir / path
        
        if not path.exists():
            return {
                "error": f"Path does not exist: {path}",
                "suggestion": "Please provide a valid path. Available directories:",
                "available": self._list_available_dirs()
            }
        
        files_found: List[FileInfo] = []
        
        # Scan recursively
        for item in path.rglob("*"):
            if item.is_file():
                file_info = FileInfo(
                    path=str(item),
                    name=item.name,
                    extension=item.suffix.lower(),
                    size_bytes=item.stat().st_size
                )
                file_info.source_type = self._classify_file(item)
                files_found.append(file_info)
        
        # Count by source type
        source_counts = {}
        for f in files_found:
            source_counts[f.source_type] = source_counts.get(f.source_type, 0) + 1
        
        return {
            "path": str(path),
            "total_files": len(files_found),
            "files_by_source": source_counts,
            "files": files_found,
            "scan_time": datetime.now().isoformat()
        }
    
    def classify(self, file_path: str) -> str:
        """
        Classify a single file by its probable source.
        
        Returns: chatgpt, spotify, uber, google, or unknown
        """
        return self._classify_file(Path(file_path))
    
    def _classify_file(self, file_path: Path) -> str:
        """Internal classification logic."""
        name = file_path.name.lower()
        
        for source, signatures in self.SOURCE_SIGNATURES.items():
            for sig in signatures:
                if sig.lower() in name:
                    return source
        
        # Try to peek inside if it's a JSON file
        if file_path.suffix.lower() == ".json":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # Read first 1KB
                    
                if "mapping" in content and "create_time" in content:
                    return "chatgpt"
                if "endTime" in content and "msPlayed" in content:
                    return "spotify"
                if "startCity" in content or "driver" in content:
                    return "uber"
            except:
                pass
        
        return "unknown"
    
    def parse(self, file_path: str, source_type: str = None) -> List[Dict]:
        """
        Parse file into normalized events.
        
        Args:
            file_path: Path to file
            source_type: Optional source hint (auto-detects if not provided)
            
        Returns:
            List of normalized event dicts
        """
        path = Path(file_path)
        if not path.exists():
            return [{"error": f"File not found: {file_path}"}]
        
        source = source_type or self._classify_file(path)
        
        if source == "chatgpt":
            return self._parse_chatgpt(path)
        elif source == "spotify":
            return self._parse_spotify(path)
        elif source == "uber":
            return self._parse_uber(path)
        else:
            return self._parse_generic(path)
    
    def _parse_chatgpt(self, path: Path) -> List[Dict]:
        """Parse ChatGPT conversation export."""
        events = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for conv in data[:50]:  # Limit for speed
                    events.append({
                        "type": "conversation",
                        "source": "chatgpt",
                        "title": conv.get("title", "Untitled"),
                        "create_time": conv.get("create_time"),
                        "message_count": len(conv.get("mapping", {})),
                    })
        except Exception as e:
            events.append({"error": str(e)})
        
        return events
    
    def _parse_spotify(self, path: Path) -> List[Dict]:
        """Parse Spotify streaming history."""
        events = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data[:100]:  # Limit
                    events.append({
                        "type": "stream",
                        "source": "spotify",
                        "track": item.get("trackName") or item.get("master_metadata_track_name"),
                        "artist": item.get("artistName") or item.get("master_metadata_album_artist_name"),
                        "played_at": item.get("endTime") or item.get("ts"),
                        "duration_ms": item.get("msPlayed") or item.get("ms_played"),
                    })
        except Exception as e:
            events.append({"error": str(e)})
        
        return events
    
    def _parse_uber(self, path: Path) -> List[Dict]:
        """Parse Uber trip data."""
        events = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            trips = data if isinstance(data, list) else data.get("trips", [])
            for trip in trips[:50]:
                events.append({
                    "type": "trip",
                    "source": "uber",
                    "start": trip.get("startCity") or trip.get("start_city"),
                    "fare": trip.get("fare") or trip.get("total_fare"),
                    "date": trip.get("requestTime") or trip.get("request_time"),
                })
        except Exception as e:
            events.append({"error": str(e)})
        
        return events
    
    def _parse_generic(self, path: Path) -> List[Dict]:
        """Generic file parsing for unknown types."""
        events = []
        try:
            if path.suffix.lower() == ".json":
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                events.append({
                    "type": "json_file",
                    "source": "unknown",
                    "keys": list(data.keys()) if isinstance(data, dict) else f"array[{len(data)}]",
                    "size": path.stat().st_size
                })
            else:
                events.append({
                    "type": "file",
                    "source": "unknown",
                    "name": path.name,
                    "size": path.stat().st_size,
                    "extension": path.suffix
                })
        except Exception as e:
            events.append({"error": str(e)})
        
        return events
    
    def summarize(self, scan_result: Dict) -> AnalysisResult:
        """
        Generate summary with top patterns and recommendations.
        
        Args:
            scan_result: Output from scan()
            
        Returns:
            AnalysisResult with summary, patterns, and recommendations
        """
        import uuid
        task_id = f"DATA-{str(uuid.uuid4())[:6].upper()}"
        
        if "error" in scan_result:
            return AnalysisResult(
                task_id=task_id,
                data_path=scan_result.get("path", "unknown"),
                total_files=0,
                files_by_source={},
                summary=scan_result["error"],
                top_patterns=[],
                recommendations=[scan_result.get("suggestion", "")],
                file_details=[],
                status="FAILED",
                error=scan_result["error"]
            )
        
        total = scan_result["total_files"]
        by_source = scan_result["files_by_source"]
        
        # Build summary
        source_parts = []
        for source, count in by_source.items():
            if source != "unknown":
                source_parts.append(f"{count} {source.title()}")
        
        unknown_count = by_source.get("unknown", 0)
        if unknown_count:
            source_parts.append(f"{unknown_count} Other")
        
        summary = f"Found {total} files: {', '.join(source_parts) if source_parts else 'all unclassified'}"
        
        # Generate patterns (placeholder - would do real analysis)
        patterns = []
        if by_source.get("chatgpt", 0) > 0:
            patterns.append("ChatGPT conversation history detected")
        if by_source.get("spotify", 0) > 0:
            patterns.append("Spotify listening data available for routine analysis")
        if by_source.get("uber", 0) > 0:
            patterns.append("Uber trip history found for location patterns")
        
        # Generate recommendations
        recommendations = []
        if total > 0:
            recommendations.append(f"Run deep analysis on {list(by_source.keys())[0]} data for behavioral insights")
            recommendations.append("Cross-reference timestamps to find activity correlations")
            recommendations.append("Consider setting up auto-sync for continuous analysis")
        else:
            recommendations.append("Add data exports to the data folder")
            recommendations.append("Supported: ChatGPT, Spotify, Uber exports")
        
        return AnalysisResult(
            task_id=task_id,
            data_path=scan_result["path"],
            total_files=total,
            files_by_source=by_source,
            summary=summary,
            top_patterns=patterns,
            recommendations=recommendations,
            file_details=scan_result.get("files", []),
            status="COMPLETED"
        )
    
    def analyze(self, data_path: str = None) -> AnalysisResult:
        """
        Full analysis pipeline: scan → classify → summarize.
        
        This is the main entry point for the "analyze data folder" command.
        
        Args:
            data_path: Path to analyze (defaults to ./data)
            
        Returns:
            AnalysisResult with full summary
        """
        # Scan
        scan_result = self.scan(data_path)
        
        # Summarize
        result = self.summarize(scan_result)
        
        return result
    
    def _list_available_dirs(self) -> List[str]:
        """List directories that exist in the project root."""
        available = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and not item.name.startswith(('.', '_')):
                available.append(item.name)
        return available[:10]  # Limit


def run_local_data_analysis(user_input: str, data_path: str = None) -> str:
    """
    CLI-friendly wrapper for LocalDataAnalyzer.
    Uses FocusTerminal for a dedicated progress view.
    
    Args:
        user_input: The user's request (for context)
        data_path: Optional explicit path
        
    Returns:
        Formatted string response
    """
    import time
    
    # Try to extract path from user input if not provided
    if not data_path:
        import re
        path_match = re.search(r'(\./[\w/]+|/[\w/]+|[A-Za-z]:\\[\w\\]+)', user_input)
        if path_match:
            data_path = path_match.group(1)
    
    analyzer = LocalDataAnalyzer()
    
    # Try to use FocusTerminal for visual progress
    try:
        from services.ui.focus_terminal import FocusTerminal
        
        with FocusTerminal("Analyzing Local Data", theme="purple") as focus:
            # Step 1: Scan
            focus.update("Scanning directory...", progress=10)
            time.sleep(0.3)  # Brief pause for visual effect
            
            scan_result = analyzer.scan(data_path)
            
            if "error" in scan_result:
                focus.error(scan_result["error"])
                return f"❌ {scan_result['error']}\n{scan_result.get('suggestion', '')}"
            
            total_files = scan_result["total_files"]
            focus.add_substep(f"Found {total_files} files")
            
            # Step 2: Classify
            focus.update("Classifying files...", progress=40)
            time.sleep(0.2)
            
            by_source = scan_result["files_by_source"]
            for source, count in by_source.items():
                if source != "unknown":
                    focus.add_substep(f"{source.title()} detected: {count} files")
            
            # Step 3: Summarize
            focus.update("Generating insights...", progress=70)
            time.sleep(0.2)
            
            result = analyzer.summarize(scan_result)
            
            # Step 4: Complete
            summary_items = [
                f"{result.total_files} files analyzed",
            ]
            for source, count in result.files_by_source.items():
                if source != "unknown":
                    emoji = {"chatgpt": "💬", "spotify": "🎵", "uber": "🚗"}.get(source, "📄")
                    summary_items.append(f"{emoji} {source.title()}: {count}")
            
            if result.top_patterns:
                summary_items.append(f"📊 {len(result.top_patterns)} patterns found")
            
            focus.complete("Analysis Complete!", summary=summary_items)
            time.sleep(1.5)  # Keep visible
            
    except ImportError:
        # Fallback if FocusTerminal not available
        result = analyzer.analyze(data_path)
    
    # Format response (never silent!)
    lines = []
    lines.append(f"📊 **Analysis Complete** (Task: {result.task_id})")
    lines.append(f"📁 Path: `{result.data_path}`")
    lines.append("")
    lines.append(f"**{result.summary}**")
    
    if result.files_by_source:
        lines.append("")
        lines.append("**Files by Source:**")
        for source, count in result.files_by_source.items():
            emoji = {"chatgpt": "💬", "spotify": "🎵", "uber": "🚗"}.get(source, "📄")
            lines.append(f"  {emoji} {source.title()}: {count} files")
    
    if result.top_patterns:
        lines.append("")
        lines.append("**Top Patterns:**")
        for i, pattern in enumerate(result.top_patterns, 1):
            lines.append(f"  {i}. {pattern}")
    
    if result.recommendations:
        lines.append("")
        lines.append("**Recommendations:**")
        for rec in result.recommendations[:3]:
            lines.append(f"  → {rec}")
    
    return "\n".join(lines)

