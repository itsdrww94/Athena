#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           M E D I C                                           ║
║                      "System Health Monitor"                                   ║
║                                                                               ║
║  Division IV: Red Alert (Safety)                                              ║
║  Monitor system health, detect issues, attempt repairs                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
  - CPU/RAM/Disk monitoring
  - Network connectivity checks
  - Process monitoring
  - Auto-repair for common issues

Usage:
  python medic.py --action check
  python medic.py --action repair --issue network
  python medic.py --action monitor --interval 60
"""

import os
import sys
import json
import argparse
import socket
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Thresholds
CPU_WARN_THRESHOLD = 80  # %
RAM_WARN_THRESHOLD = 85  # %
DISK_WARN_THRESHOLD = 90  # %

# DNS servers to check
DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SystemStatus:
    """System health status."""
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_ok: bool
    ping_ms: Optional[float]
    uptime_hours: float
    issues: List[str]
    
    @property
    def is_healthy(self) -> bool:
        return len(self.issues) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_gb": self.ram_used_gb,
            "ram_total_gb": self.ram_total_gb,
            "disk_percent": self.disk_percent,
            "disk_used_gb": self.disk_used_gb,
            "network_ok": self.network_ok,
            "ping_ms": self.ping_ms,
            "uptime_hours": self.uptime_hours,
            "issues": self.issues,
            "healthy": self.is_healthy
        }


# =============================================================================
# SYSTEM CHECKS
# =============================================================================

def check_cpu() -> float:
    """Get CPU usage percentage."""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        # Fallback for Windows
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "loadpercentage"],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    return float(line)
        except:
            pass
    return 0.0


def check_ram() -> Dict[str, float]:
    """Get RAM usage."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used_gb": mem.used / (1024**3),
            "total_gb": mem.total / (1024**3)
        }
    except ImportError:
        # Fallback
        return {"percent": 0, "used_gb": 0, "total_gb": 0}


def check_disk() -> Dict[str, float]:
    """Get disk usage for system drive."""
    try:
        import psutil
        # Get the drive where Python is installed
        path = Path(sys.executable).anchor
        usage = psutil.disk_usage(path)
        return {
            "percent": usage.percent,
            "used_gb": usage.used / (1024**3),
            "total_gb": usage.total / (1024**3)
        }
    except ImportError:
        return {"percent": 0, "used_gb": 0, "total_gb": 0}


def check_network() -> Dict[str, Any]:
    """Check network connectivity."""
    result = {"ok": False, "ping_ms": None}
    
    for dns in DNS_SERVERS:
        try:
            start = datetime.now()
            socket.create_connection((dns, 53), timeout=3)
            end = datetime.now()
            
            result["ok"] = True
            result["ping_ms"] = (end - start).total_seconds() * 1000
            break
        except:
            continue
    
    return result


def get_uptime() -> float:
    """Get system uptime in hours."""
    try:
        import psutil
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        return uptime.total_seconds() / 3600
    except:
        return 0.0


def get_system_status() -> SystemStatus:
    """Get complete system status."""
    issues = []
    
    # Check CPU
    cpu = check_cpu()
    if cpu > CPU_WARN_THRESHOLD:
        issues.append(f"High CPU usage: {cpu:.1f}%")
    
    # Check RAM
    ram = check_ram()
    if ram["percent"] > RAM_WARN_THRESHOLD:
        issues.append(f"High RAM usage: {ram['percent']:.1f}%")
    
    # Check Disk
    disk = check_disk()
    if disk["percent"] > DISK_WARN_THRESHOLD:
        issues.append(f"Low disk space: {100-disk['percent']:.1f}% free")
    
    # Check Network
    network = check_network()
    if not network["ok"]:
        issues.append("Network connectivity issues")
    
    return SystemStatus(
        cpu_percent=cpu,
        ram_percent=ram["percent"],
        ram_used_gb=ram["used_gb"],
        ram_total_gb=ram["total_gb"],
        disk_percent=disk["percent"],
        disk_used_gb=disk["used_gb"],
        disk_total_gb=disk["total_gb"],
        network_ok=network["ok"],
        ping_ms=network["ping_ms"],
        uptime_hours=get_uptime(),
        issues=issues
    )


# =============================================================================
# REPAIR ACTIONS
# =============================================================================

def repair_network() -> str:
    """Attempt to repair network connectivity."""
    output = ["🔧 Attempting network repair...", ""]
    
    if platform.system() == "Windows":
        commands = [
            ("Flushing DNS cache", ["ipconfig", "/flushdns"]),
            ("Releasing IP", ["ipconfig", "/release"]),
            ("Renewing IP", ["ipconfig", "/renew"]),
            ("Resetting Winsock", ["netsh", "winsock", "reset"]),
        ]
    else:
        commands = [
            ("Restarting NetworkManager", ["sudo", "systemctl", "restart", "NetworkManager"]),
        ]
    
    for description, cmd in commands:
        output.append(f"• {description}...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                output.append("  ✅ Success")
            else:
                output.append(f"  ⚠️ {result.stderr[:100]}")
        except Exception as e:
            output.append(f"  ❌ Error: {e}")
    
    # Verify fix
    network = check_network()
    if network["ok"]:
        output.append("")
        output.append("✅ Network connectivity restored!")
    else:
        output.append("")
        output.append("⚠️ Issues persist. May need manual intervention.")
    
    return "\n".join(output)


def clear_temp_files() -> str:
    """Clear temporary files to free disk space."""
    output = ["🔧 Clearing temporary files...", ""]
    
    if platform.system() == "Windows":
        temp_dirs = [
            Path(os.environ.get("TEMP", "C:\\Temp")),
            Path(os.environ.get("TMP", "C:\\Temp")),
        ]
    else:
        temp_dirs = [Path("/tmp")]
    
    total_cleared = 0
    
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            try:
                count = 0
                for item in temp_dir.glob("*"):
                    try:
                        if item.is_file():
                            item.unlink()
                            count += 1
                    except:
                        continue
                total_cleared += count
                output.append(f"• Cleared {count} files from {temp_dir}")
            except Exception as e:
                output.append(f"• Could not clean {temp_dir}: {e}")
    
    output.append("")
    output.append(f"✅ Cleared {total_cleared} temporary files")
    
    return "\n".join(output)


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_status(status: SystemStatus) -> str:
    """Format system status for display."""
    output = []
    output.append("=" * 60)
    output.append("🏥 MEDIC - System Health Check")
    output.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("=" * 60)
    output.append("")
    
    # Health indicator
    if status.is_healthy:
        output.append("✅ SYSTEM HEALTHY")
    else:
        output.append("⚠️ ISSUES DETECTED")
    
    output.append("")
    
    # CPU
    cpu_bar = "█" * int(status.cpu_percent / 5) + "░" * (20 - int(status.cpu_percent / 5))
    cpu_emoji = "✅" if status.cpu_percent < CPU_WARN_THRESHOLD else "⚠️"
    output.append(f"🖥️ CPU:  [{cpu_bar}] {status.cpu_percent:.1f}% {cpu_emoji}")
    
    # RAM
    ram_bar = "█" * int(status.ram_percent / 5) + "░" * (20 - int(status.ram_percent / 5))
    ram_emoji = "✅" if status.ram_percent < RAM_WARN_THRESHOLD else "⚠️"
    output.append(f"💾 RAM:  [{ram_bar}] {status.ram_percent:.1f}% ({status.ram_used_gb:.1f}/{status.ram_total_gb:.1f} GB) {ram_emoji}")
    
    # Disk
    disk_bar = "█" * int(status.disk_percent / 5) + "░" * (20 - int(status.disk_percent / 5))
    disk_emoji = "✅" if status.disk_percent < DISK_WARN_THRESHOLD else "⚠️"
    output.append(f"💿 Disk: [{disk_bar}] {status.disk_percent:.1f}% ({status.disk_used_gb:.0f}/{status.disk_total_gb:.0f} GB) {disk_emoji}")
    
    # Network
    net_emoji = "✅" if status.network_ok else "❌"
    ping_str = f"{status.ping_ms:.0f}ms" if status.ping_ms else "N/A"
    output.append(f"🌐 Net:  {net_emoji} {'Online' if status.network_ok else 'OFFLINE'} (ping: {ping_str})")
    
    # Uptime
    output.append(f"⏱️ Uptime: {status.uptime_hours:.1f} hours")
    
    output.append("")
    
    # Issues
    if status.issues:
        output.append("🚨 Issues:")
        for issue in status.issues:
            output.append(f"   • {issue}")
        output.append("")
        output.append("💡 Run: python medic.py --action repair --issue <type>")
    
    output.append("=" * 60)
    
    return "\n".join(output)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Medic - System health monitor"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["check", "repair", "monitor", "clear-temp"],
        default="check",
        help="Action to perform"
    )
    
    parser.add_argument("--issue", "-i", choices=["network", "disk"], help="Issue to repair")
    parser.add_argument("--interval", type=int, default=60, help="Monitor interval in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.action == "check":
        status = get_system_status()
        if args.json:
            print(json.dumps(status.to_dict(), indent=2))
        else:
            print(format_status(status))
            
    elif args.action == "repair":
        if args.issue == "network":
            print(repair_network())
        elif args.issue == "disk":
            print(clear_temp_files())
        else:
            print("❌ Specify --issue (network or disk)")
            
    elif args.action == "clear-temp":
        print(clear_temp_files())
        
    elif args.action == "monitor":
        import time
        print(f"🏥 Monitoring every {args.interval}s (Ctrl+C to stop)")
        try:
            while True:
                status = get_system_status()
                print(format_status(status))
                if not status.is_healthy:
                    print("⚠️ Issues detected!")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
    
    else:
        print("Unknown action")


if __name__ == "__main__":
    main()
