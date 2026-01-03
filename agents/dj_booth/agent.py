#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         D J   B O O T H                                       ║
║                    "The Vibe Manager"                                          ║
║                                                                               ║
║  Spotify controller for context-aware music control                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- Mode presets (focus, hype, chill, sleep)
- Device transfer (PC → Speaker → Phone)
- Smart recommendations based on listening history
- Weather-aware playlist selection

Usage:
    python dj_booth.py --mode focus
    python dj_booth.py --device speaker
    python dj_booth.py --recommend
    python dj_booth.py --play "Deep Focus"

Environment Variables:
    SPOTIPY_CLIENT_ID
    SPOTIPY_CLIENT_SECRET
    SPOTIPY_REDIRECT_URI (default: http://localhost:8888/callback)
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

# Cache file for Spotify auth
CACHE_PATH = Path.home() / "athena_data" / ".spotify_cache"

# Mode presets (map to playlist URIs or names)
MODE_PRESETS = {
    "focus": {
        "playlist": "Deep Focus",
        "volume": 40,
        "shuffle": False
    },
    "hype": {
        "playlist": "Workout",
        "volume": 70,
        "shuffle": True
    },
    "chill": {
        "playlist": "Chill Vibes",
        "volume": 50,
        "shuffle": True
    },
    "sleep": {
        "playlist": "Sleep",
        "volume": 25,
        "shuffle": False
    },
    "anime": {
        "playlist": "Anime OST",
        "volume": 50,
        "shuffle": True
    }
}

# Device aliases
DEVICE_ALIASES = {
    "pc": ["computer", "desktop", "laptop"],
    "phone": ["mobile", "iphone", "android"],
    "speaker": ["living room", "alexa", "echo", "sonos"]
}


# =============================================================================
# SPOTIFY CLIENT
# =============================================================================

def get_spotify_client():
    """Initialize authenticated Spotify client."""
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        print("❌ spotipy not installed. Run: pip install spotipy")
        sys.exit(1)
    
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        print("❌ Spotify credentials not found in .env")
        print("   Add SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET")
        sys.exit(1)
    
    scope = "user-modify-playback-state user-read-playback-state user-read-currently-playing playlist-read-private user-top-read"
    
    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=scope,
        cache_path=str(CACHE_PATH)
    )
    
    return spotipy.Spotify(auth_manager=auth_manager)


# =============================================================================
# PLAYBACK CONTROL
# =============================================================================

def get_devices(sp) -> List[Dict]:
    """Get available Spotify devices."""
    devices = sp.devices()
    return devices.get("devices", [])


def find_device(sp, name: str) -> Optional[str]:
    """Find device ID by name or alias."""
    devices = get_devices(sp)
    name_lower = name.lower()
    
    for device in devices:
        device_name = device.get("name", "").lower()
        
        # Check direct match
        if name_lower in device_name:
            return device["id"]
        
        # Check aliases
        for alias, keywords in DEVICE_ALIASES.items():
            if name_lower == alias or name_lower in keywords:
                if any(kw in device_name for kw in keywords + [alias]):
                    return device["id"]
    
    return None


def transfer_playback(sp, device_name: str) -> Dict[str, Any]:
    """Transfer playback to a specific device."""
    device_id = find_device(sp, device_name)
    
    if not device_id:
        devices = get_devices(sp)
        device_list = [d["name"] for d in devices]
        return {
            "success": False,
            "error": f"Device '{device_name}' not found",
            "available_devices": device_list
        }
    
    try:
        sp.transfer_playback(device_id, force_play=True)
        return {
            "success": True,
            "message": f"Transferred playback to {device_name}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_volume(sp, volume: int) -> Dict[str, Any]:
    """Set playback volume (0-100)."""
    volume = max(0, min(100, volume))
    
    try:
        sp.volume(volume)
        return {"success": True, "volume": volume}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_shuffle(sp, state: bool) -> Dict[str, Any]:
    """Set shuffle state."""
    try:
        sp.shuffle(state)
        return {"success": True, "shuffle": state}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# PLAYLIST MANAGEMENT
# =============================================================================

def find_playlist(sp, name: str) -> Optional[str]:
    """Find playlist by name (searches user's playlists)."""
    name_lower = name.lower()
    
    # Get user's playlists
    offset = 0
    while True:
        playlists = sp.current_user_playlists(limit=50, offset=offset)
        
        for playlist in playlists.get("items", []):
            if playlist and name_lower in playlist.get("name", "").lower():
                return playlist["uri"]
        
        if not playlists.get("next"):
            break
        offset += 50
    
    return None


def play_playlist(sp, playlist_name: str, shuffle: bool = True) -> Dict[str, Any]:
    """Play a playlist by name."""
    playlist_uri = find_playlist(sp, playlist_name)
    
    if not playlist_uri:
        return {
            "success": False,
            "error": f"Playlist '{playlist_name}' not found"
        }
    
    try:
        sp.shuffle(shuffle)
        sp.start_playback(context_uri=playlist_uri)
        return {
            "success": True,
            "message": f"Now playing: {playlist_name}",
            "shuffle": shuffle
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def activate_mode(sp, mode: str) -> Dict[str, Any]:
    """Activate a preset mode (focus, hype, chill, sleep)."""
    if mode not in MODE_PRESETS:
        return {
            "success": False,
            "error": f"Unknown mode '{mode}'",
            "available_modes": list(MODE_PRESETS.keys())
        }
    
    preset = MODE_PRESETS[mode]
    results = []
    
    # Play the playlist
    play_result = play_playlist(sp, preset["playlist"], preset.get("shuffle", True))
    results.append(play_result)
    
    # Set volume
    if "volume" in preset:
        vol_result = set_volume(sp, preset["volume"])
        results.append(vol_result)
    
    return {
        "success": all(r.get("success", False) for r in results),
        "mode": mode,
        "playlist": preset["playlist"],
        "volume": preset.get("volume"),
        "results": results
    }


# =============================================================================
# SMART RECOMMENDATIONS
# =============================================================================

def get_recommendations(sp, seed_type: str = "tracks") -> Dict[str, Any]:
    """Get personalized recommendations based on listening history."""
    try:
        # Get user's top tracks as seeds
        top_tracks = sp.current_user_top_tracks(limit=5, time_range="short_term")
        track_ids = [t["id"] for t in top_tracks.get("items", [])]
        
        if not track_ids:
            return {"success": False, "error": "No listening history found"}
        
        # Get recommendations
        recs = sp.recommendations(seed_tracks=track_ids[:5], limit=20)
        
        recommended = []
        for track in recs.get("tracks", []):
            recommended.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "uri": track["uri"]
            })
        
        return {
            "success": True,
            "recommendations": recommended[:10],
            "seed_tracks": [t["name"] for t in top_tracks.get("items", [])][:5]
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def play_recommendations(sp) -> Dict[str, Any]:
    """Queue recommended tracks."""
    recs = get_recommendations(sp)
    
    if not recs.get("success"):
        return recs
    
    try:
        # Queue the first few tracks
        for track in recs["recommendations"][:5]:
            sp.add_to_queue(track["uri"])
        
        # Skip to next (the first queued track)
        sp.next_track()
        
        return {
            "success": True,
            "message": "Playing personalized recommendations",
            "tracks_queued": len(recs["recommendations"][:5])
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# STATUS
# =============================================================================

def get_current_playback(sp) -> Dict[str, Any]:
    """Get current playback status."""
    try:
        current = sp.current_playback()
        
        if not current:
            return {"playing": False, "message": "Nothing playing"}
        
        track = current.get("item", {})
        device = current.get("device", {})
        
        return {
            "playing": current.get("is_playing", False),
            "track": track.get("name", "Unknown"),
            "artist": track.get("artists", [{}])[0].get("name", "Unknown"),
            "device": device.get("name", "Unknown"),
            "volume": device.get("volume_percent", 0),
            "shuffle": current.get("shuffle_state", False)
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="DJ Booth - Spotify Controller")
    parser.add_argument("--mode", choices=list(MODE_PRESETS.keys()),
                        help="Activate a mood preset")
    parser.add_argument("--device", help="Transfer to device")
    parser.add_argument("--play", help="Play a playlist by name")
    parser.add_argument("--volume", type=int, help="Set volume (0-100)")
    parser.add_argument("--recommend", action="store_true",
                        help="Play personalized recommendations")
    parser.add_argument("--status", action="store_true",
                        help="Show current playback")
    parser.add_argument("--devices", action="store_true",
                        help="List available devices")
    
    args = parser.parse_args()
    
    print("🎵 DJ Booth - Vibe Manager")
    print("=" * 40)
    
    sp = get_spotify_client()
    
    if args.status:
        result = get_current_playback(sp)
        print(json.dumps(result, indent=2))
        
    elif args.devices:
        devices = get_devices(sp)
        print(f"Available devices ({len(devices)}):")
        for d in devices:
            active = "▶" if d.get("is_active") else " "
            print(f"  {active} {d['name']} ({d['type']})")
            
    elif args.mode:
        result = activate_mode(sp, args.mode)
        if result["success"]:
            print(f"✅ Activated {args.mode} mode")
            print(f"   Playlist: {result['playlist']}")
            print(f"   Volume: {result.get('volume', 'unchanged')}%")
        else:
            print(f"❌ {result.get('error')}")
            
    elif args.device:
        result = transfer_playback(sp, args.device)
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
            if "available_devices" in result:
                print(f"   Available: {', '.join(result['available_devices'])}")
                
    elif args.play:
        result = play_playlist(sp, args.play)
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
            
    elif args.volume is not None:
        result = set_volume(sp, args.volume)
        if result["success"]:
            print(f"✅ Volume set to {result['volume']}%")
        else:
            print(f"❌ {result['error']}")
            
    elif args.recommend:
        result = play_recommendations(sp)
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
            
    else:
        # Default: show status
        result = get_current_playback(sp)
        if result.get("playing"):
            print(f"🎵 Now playing: {result['track']} - {result['artist']}")
            print(f"   Device: {result['device']} | Volume: {result['volume']}%")
        else:
            print("⏸️ Nothing currently playing")
        
        print(f"\nModes: {', '.join(MODE_PRESETS.keys())}")
        print("Use --help for more options")


if __name__ == "__main__":
    main()
