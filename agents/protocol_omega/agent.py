#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    P R O T O C O L   O M E G A                                ║
║                       "Dead Man's Switch"                                      ║
║                                                                               ║
║  Division IV: Red Alert (Safety)                                              ║
║  Emergency procedures and inactivity alerts                                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
  - /panic command: Send location to emergency contact
  - Inactivity check: Alert if no activity for X days
  - Digital will: Instructions for digital assets

SECURITY NOTE: This is a safety feature. Handle with care.

Usage:
  python protocol_omega.py --action panic
  python protocol_omega.py --action check-activity
  python protocol_omega.py --action configure
"""

import os
import sys
import json
import argparse
import socket
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "omega_config.json"
ACTIVITY_FILE = DATA_DIR / "last_activity.json"

# Ensure data directory
DATA_DIR.mkdir(exist_ok=True)

# Thresholds
DEFAULT_INACTIVITY_DAYS = 30

# Emergency contact (from env or config)
EMERGENCY_CONTACT_NAME = os.getenv("EMERGENCY_CONTACT_NAME", "Skylar")
EMERGENCY_CONTACT_TELEGRAM = os.getenv("EMERGENCY_CONTACT_TELEGRAM", "")
EMERGENCY_EMAIL = os.getenv("EMERGENCY_EMAIL", "")

# =============================================================================
# DATA PERSISTENCE
# =============================================================================

def load_config() -> Dict[str, Any]:
    """Load Omega configuration."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {
        "emergency_contact": {
            "name": EMERGENCY_CONTACT_NAME,
            "telegram_id": EMERGENCY_CONTACT_TELEGRAM,
            "email": EMERGENCY_EMAIL
        },
        "inactivity_threshold_days": DEFAULT_INACTIVITY_DAYS,
        "enabled": False,  # Must be explicitly enabled
        "digital_will_location": "",
        "notes": ""
    }


def save_config(config: Dict[str, Any]) -> None:
    """Save Omega configuration."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def record_activity() -> None:
    """Record that user is active."""
    with open(ACTIVITY_FILE, 'w') as f:
        json.dump({
            "last_seen": datetime.now().isoformat(),
            "hostname": socket.gethostname()
        }, f)


def get_last_activity() -> Optional[datetime]:
    """Get last recorded activity."""
    if ACTIVITY_FILE.exists():
        try:
            with open(ACTIVITY_FILE, 'r') as f:
                data = json.load(f)
                return datetime.fromisoformat(data["last_seen"])
        except:
            pass
    return None


# =============================================================================
# LOCATION SERVICES
# =============================================================================

def get_approximate_location() -> Dict[str, Any]:
    """
    Get approximate location via IP geolocation.
    NOTE: This is not GPS-accurate, just city-level.
    """
    try:
        import requests
        
        response = requests.get("https://ipinfo.io/json", timeout=5)
        data = response.json()
        
        return {
            "city": data.get("city", "Unknown"),
            "region": data.get("region", ""),
            "country": data.get("country", ""),
            "loc": data.get("loc", ""),  # lat,lon
            "ip": data.get("ip", ""),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# ALERT ACTIONS
# =============================================================================

async def send_panic_alert(location: Dict[str, Any], message: str = "") -> Dict[str, bool]:
    """
    Send panic alert to emergency contact via Telegram.
    """
    results = {"telegram": False, "email": False}
    config = load_config()
    
    contact = config.get("emergency_contact", {})
    contact_telegram = contact.get("telegram_id")
    
    if not contact_telegram:
        return results
    
    try:
        from services.telegram_service import get_telegram_service
        
        telegram = get_telegram_service()
        
        loc_str = f"{location.get('city', 'Unknown')}, {location.get('region', '')}"
        maps_link = ""
        if location.get("loc"):
            lat, lon = location["loc"].split(",")
            maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        alert_message = f"""🚨 **EMERGENCY ALERT**

From: Drew (Athena User)
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📍 Approximate Location: {loc_str}
{f'🗺️ Map: {maps_link}' if maps_link else ''}

{f'Message: {message}' if message else 'Panic button activated - please check in.'}

---
_This is an automated alert from Project Athena Protocol Omega._
"""
        
        result = await telegram.send_text(alert_message, contact_telegram)
        results["telegram"] = result.get("ok", False)
        
    except Exception as e:
        print(f"⚠️ Telegram alert failed: {e}")
    
    return results


def check_inactivity() -> Dict[str, Any]:
    """
    Check if user has been inactive beyond threshold.
    Returns status and days since last activity.
    """
    config = load_config()
    threshold = config.get("inactivity_threshold_days", DEFAULT_INACTIVITY_DAYS)
    
    last_activity = get_last_activity()
    
    if not last_activity:
        return {
            "status": "unknown",
            "message": "No activity recorded yet. Run 'python protocol_omega.py --action heartbeat' to start tracking."
        }
    
    days_inactive = (datetime.now() - last_activity).days
    
    if days_inactive >= threshold:
        return {
            "status": "alert",
            "days_inactive": days_inactive,
            "threshold": threshold,
            "last_activity": last_activity.isoformat(),
            "message": f"⚠️ ALERT: {days_inactive} days since last activity (threshold: {threshold})"
        }
    else:
        return {
            "status": "ok",
            "days_inactive": days_inactive,
            "threshold": threshold,
            "last_activity": last_activity.isoformat(),
            "message": f"✅ Active. Last seen {days_inactive} days ago."
        }


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_config_status(config: Dict[str, Any]) -> str:
    """Format configuration status."""
    output = []
    output.append("=" * 60)
    output.append("🔴 PROTOCOL OMEGA - Configuration")
    output.append("=" * 60)
    output.append("")
    
    enabled = config.get("enabled", False)
    output.append(f"Status: {'🟢 ENABLED' if enabled else '🔴 DISABLED'}")
    output.append("")
    
    contact = config.get("emergency_contact", {})
    output.append("📞 Emergency Contact:")
    output.append(f"   Name: {contact.get('name', 'Not set')}")
    output.append(f"   Telegram: {contact.get('telegram_id', 'Not set')[:10]}..." if contact.get('telegram_id') else "   Telegram: Not set")
    output.append("")
    
    output.append(f"⏰ Inactivity Threshold: {config.get('inactivity_threshold_days', DEFAULT_INACTIVITY_DAYS)} days")
    output.append("")
    
    # Activity status
    activity = check_inactivity()
    output.append(f"📊 Activity Status: {activity['message']}")
    
    output.append("")
    output.append("=" * 60)
    output.append("")
    output.append("⚠️  SAFETY FEATURE - Use responsibly")
    output.append("    To enable: python protocol_omega.py --action enable")
    
    return "\n".join(output)


# =============================================================================
# CLI
# =============================================================================

def main():
    import asyncio
    
    parser = argparse.ArgumentParser(
        description="Protocol Omega - Emergency procedures"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["status", "panic", "heartbeat", "check-activity", "enable", "disable", "configure"],
        default="status",
        help="Action to perform"
    )
    
    parser.add_argument("--message", "-m", type=str, help="Custom panic message")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    config = load_config()
    
    if args.action == "status":
        print(format_config_status(config))
        
    elif args.action == "panic":
        if not config.get("enabled"):
            print("⚠️ Protocol Omega is disabled. Enable with: --action enable")
            return
        
        print("🚨 INITIATING PANIC PROTOCOL...")
        print("📍 Getting location...")
        location = get_approximate_location()
        print(f"   Location: {location.get('city', 'Unknown')}, {location.get('region', '')}")
        
        print("📤 Sending alert...")
        results = asyncio.run(send_panic_alert(location, args.message))
        
        if results["telegram"]:
            print("✅ Alert sent via Telegram!")
        else:
            print("⚠️ Could not send alert. Check configuration.")
        
    elif args.action == "heartbeat":
        record_activity()
        print(f"✅ Activity recorded at {datetime.now().isoformat()}")
        
    elif args.action == "check-activity":
        result = check_inactivity()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["message"])
            
    elif args.action == "enable":
        config["enabled"] = True
        save_config(config)
        print("🟢 Protocol Omega ENABLED")
        print("⚠️  Make sure emergency contact is configured!")
        
    elif args.action == "disable":
        config["enabled"] = False
        save_config(config)
        print("🔴 Protocol Omega DISABLED")
        
    elif args.action == "configure":
        print("📝 Configuration saved at:", CONFIG_FILE)
        print("   Edit this file to set emergency contacts.")
        print("")
        print("Required .env variables:")
        print("   EMERGENCY_CONTACT_NAME=Skylar")
        print("   EMERGENCY_CONTACT_TELEGRAM=123456789")
        print("   EMERGENCY_EMAIL=contact@email.com")


if __name__ == "__main__":
    main()
