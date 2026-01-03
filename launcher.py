"""
Athena Launcher - Application Launch Helper
Handles opening applications and system commands for Athena CLI
"""

import subprocess
import os
import platform
from pathlib import Path


# =============================================================================
# APPLICATION REGISTRY
# Define common applications and their paths/commands
# =============================================================================

WINDOWS_APPS = {
    # Development
    "code": "code",
    "vscode": "code",
    "vs code": "code",
    "terminal": "wt",  # Windows Terminal
    "cmd": "cmd",
    "powershell": "powershell",
    
    # Browsers
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge": "msedge",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    
    # Productivity
    "notepad": "notepad",
    "explorer": "explorer",
    "files": "explorer",
    "calc": "calc",
    "calculator": "calc",
    
    # Microsoft Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    
    # Media
    "spotify": r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
    
    # Communication
    "discord": r"C:\Users\%USERNAME%\AppData\Local\Discord\Update.exe --processStart Discord.exe",
    "slack": r"C:\Users\%USERNAME%\AppData\Local\slack\slack.exe",
    "teams": r"C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\Update.exe --processStart Teams.exe",
    
    # Utilities
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "control panel": "control",
}


# =============================================================================
# LAUNCHER FUNCTIONS
# =============================================================================

def expand_path(path: str) -> str:
    """Expand environment variables in path"""
    return os.path.expandvars(path)


def launch_app(app_name: str) -> dict:
    """
    Launch an application by name
    
    Args:
        app_name: Name of the application to launch
        
    Returns:
        dict with success status and message
    """
    app_name_lower = app_name.lower().strip()
    
    # Check if it's a registered app
    if app_name_lower in WINDOWS_APPS:
        command = expand_path(WINDOWS_APPS[app_name_lower])
        
        try:
            # Handle special cases (URLs/protocols)
            if command.startswith("ms-"):
                os.startfile(command)
                return {
                    "success": True,
                    "message": f"🚀 Opened {app_name}",
                    "command": command
                }
            
            # Check if it's a file path that exists
            if os.path.exists(command):
                subprocess.Popen([command], shell=True)
            else:
                # Try as a command
                subprocess.Popen(command, shell=True)
                
            return {
                "success": True,
                "message": f"🚀 Launched {app_name}",
                "command": command
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Failed to launch {app_name}: {str(e)}",
                "command": command
            }
    
    # Try to launch as a direct command
    try:
        subprocess.Popen(app_name, shell=True)
        return {
            "success": True,
            "message": f"🚀 Executed: {app_name}",
            "command": app_name
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Unknown application: {app_name}",
            "error": str(e)
        }


def launch_url(url: str, browser: str = "default") -> dict:
    """
    Open a URL in a browser
    
    Args:
        url: URL to open
        browser: Browser to use (default uses system default)
        
    Returns:
        dict with success status and message
    """
    import webbrowser
    
    try:
        if browser == "default":
            webbrowser.open(url)
        elif browser in WINDOWS_APPS:
            browser_path = expand_path(WINDOWS_APPS[browser])
            subprocess.Popen([browser_path, url], shell=True)
        else:
            webbrowser.open(url)
            
        return {
            "success": True,
            "message": f"🌐 Opened {url}",
            "browser": browser
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to open URL: {str(e)}",
            "url": url
        }


def list_available_apps() -> list:
    """Return list of available application names"""
    return sorted(WINDOWS_APPS.keys())


def run_command(command: str, cwd: str = None) -> dict:
    """
    Execute a shell command
    
    Args:
        command: Command to execute
        cwd: Working directory (optional)
        
    Returns:
        dict with output and status
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "⏱️ Command timed out after 30 seconds",
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Command failed: {str(e)}",
            "command": command
        }


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("🚀 Athena Launcher - Available Applications:")
    print("-" * 40)
    for app in list_available_apps():
        print(f"  • {app}")
    print("-" * 40)
    print("\nUsage: launcher.launch_app('chrome')")
