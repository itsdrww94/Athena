#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                  C R E D E N T I A L   M A N A G E R                          ║
║                        "The Vault Keeper"                                      ║
║                                                                               ║
║  Secure credential storage for Athena with Claude-assisted formatting        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- Asks for user confirmation before saving
- Uses Claude to generate proper ENV variable names
- Auto-appends to .env file
- Categorizes by website/service

Usage:
    from services.credential_manager import save_credential, get_credential
    
    # Save new credential (returns True if saved)
    saved = await save_credential("pinterest.com", "user@email.com", "pass123")
    
    # Get credential
    user, password = get_credential("pinterest.com")
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Path to .env file
ENV_FILE = Path(__file__).parent.parent / ".env"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# =============================================================================
# CREDENTIAL MANAGER
# =============================================================================

def get_env_var_names(website: str) -> Tuple[str, str]:
    """
    Use Claude to generate proper ENV variable names for a website.
    
    Example: "pinterest.com" -> ("PINTEREST_USER", "PINTEREST_PASS")
    
    Falls back to simple generation if Claude unavailable.
    """
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            
            prompt = f"""Generate environment variable names for storing credentials for the website: {website}

Rules:
1. Use UPPERCASE with underscores
2. Create two variables: one for username/email and one for password
3. Keep it short and clear
4. Follow common conventions

Return ONLY two lines, nothing else:
USER_VAR_NAME
PASS_VAR_NAME

Example for "pinterest.com":
PINTEREST_USER
PINTEREST_PASS"""

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text.strip()
            lines = text.split("\n")
            
            if len(lines) >= 2:
                user_var = lines[0].strip()
                pass_var = lines[1].strip()
                
                # Validate format
                if re.match(r'^[A-Z][A-Z0-9_]+$', user_var) and re.match(r'^[A-Z][A-Z0-9_]+$', pass_var):
                    return (user_var, pass_var)
                    
        except Exception as e:
            print(f"Claude unavailable: {e}")
    
    # Fallback: Generate simple env var names
    # Extract domain name (e.g., "pinterest" from "pinterest.com")
    domain = website.lower().replace("www.", "")
    domain = domain.split(".")[0]  # Get first part
    domain = re.sub(r'[^a-z0-9]', '_', domain).upper()
    
    return (f"{domain}_USER", f"{domain}_PASS")


def append_to_env(key: str, value: str, comment: str = None) -> bool:
    """
    Append a new environment variable to .env file.
    
    Args:
        key: Variable name (e.g., PINTEREST_USER)
        value: Variable value
        comment: Optional comment to add above the variable
    """
    try:
        # Read existing content
        if ENV_FILE.exists():
            content = ENV_FILE.read_text()
        else:
            content = ""
        
        # Check if variable already exists
        if f"{key}=" in content:
            print(f"Variable {key} already exists in .env")
            return False
        
        # Build new entry
        entry = ""
        if comment:
            entry += f"\n# {comment}\n"
        entry += f"{key}={value}\n"
        
        # Append to file
        with open(ENV_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        
        print(f"Added {key} to .env")
        return True
        
    except Exception as e:
        print(f"Failed to write to .env: {e}")
        return False


def save_credential(website: str, username: str, password: str) -> Dict[str, any]:
    """
    Save credentials to .env file with proper variable names.
    
    Args:
        website: Website domain (e.g., "pinterest.com")
        username: Username or email
        password: Password
        
    Returns:
        Dict with status and variable names
    """
    # Get proper variable names from Claude
    user_var, pass_var = get_env_var_names(website)
    
    # Add comment timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")
    comment = f"{website} credentials (added {timestamp})"
    
    # Append to .env
    success_user = append_to_env(user_var, username, comment)
    success_pass = append_to_env(pass_var, password)
    
    if success_user or success_pass:
        # Reload environment
        load_dotenv(override=True)
        
        return {
            "success": True,
            "user_var": user_var,
            "pass_var": pass_var,
            "message": f"Saved {user_var} and {pass_var} to .env"
        }
    else:
        return {
            "success": False,
            "user_var": user_var,
            "pass_var": pass_var,
            "message": "Credentials may already exist in .env"
        }


def get_credential(website: str) -> Optional[Tuple[str, str]]:
    """
    Get credentials for a website from environment variables.
    
    Args:
        website: Website domain (e.g., "pinterest.com")
        
    Returns:
        Tuple of (username, password) or None if not found
    """
    # Try to get the variable names
    user_var, pass_var = get_env_var_names(website)
    
    username = os.getenv(user_var)
    password = os.getenv(pass_var)
    
    if username and password:
        return (username, password)
    
    return None


def list_saved_credentials() -> Dict[str, str]:
    """
    List all credential-like variables in .env (without showing values).
    
    Returns:
        Dict of variable_name -> "****" (masked)
    """
    creds = {}
    
    if not ENV_FILE.exists():
        return creds
    
    content = ENV_FILE.read_text()
    
    # Find all _USER and _PASS variables
    pattern = r'^([A-Z][A-Z0-9_]*(?:_USER|_PASS|_EMAIL|_PASSWORD))='
    
    for line in content.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            var_name = match.group(1)
            creds[var_name] = "****"
    
    return creds


# =============================================================================
# TELEGRAM FLOW HELPER
# =============================================================================

class CredentialFlow:
    """
    Manages the credential saving flow for Telegram conversations.
    
    Flow:
    1. User says "save my pinterest login: user@email.com / password123"
    2. Athena asks: "Should I save PINTEREST_USER and PINTEREST_PASS?"
    3. User confirms: "yes"
    4. Athena saves to .env
    """
    
    def __init__(self):
        self.pending = {}  # chat_id -> {website, username, password}
    
    def start_flow(self, chat_id: str, website: str, username: str, password: str) -> str:
        """
        Start the credential save flow. Returns confirmation message.
        """
        user_var, pass_var = get_env_var_names(website)
        
        self.pending[chat_id] = {
            "website": website,
            "username": username,
            "password": password,
            "user_var": user_var,
            "pass_var": pass_var
        }
        
        return (
            f"🔐 **Save Credentials?**\n\n"
            f"Website: `{website}`\n"
            f"Username: `{username}`\n"
            f"Password: `{'*' * min(len(password), 8)}`\n\n"
            f"I'll save these as:\n"
            f"• `{user_var}`\n"
            f"• `{pass_var}`\n\n"
            f"Reply **yes** to confirm or **no** to cancel."
        )
    
    def confirm_save(self, chat_id: str) -> str:
        """
        User confirmed - save the credentials.
        """
        if chat_id not in self.pending:
            return "❌ No pending credential save."
        
        data = self.pending.pop(chat_id)
        
        result = save_credential(
            data["website"],
            data["username"],
            data["password"]
        )
        
        if result["success"]:
            return (
                f"✅ **Credentials Saved!**\n\n"
                f"Added to `.env`:\n"
                f"• `{result['user_var']}`\n"
                f"• `{result['pass_var']}`\n\n"
                f"You can now use `/browse` with `--login` and Athena will auto-authenticate."
            )
        else:
            return f"⚠️ {result['message']}"
    
    def cancel_save(self, chat_id: str) -> str:
        """
        User cancelled - discard the pending save.
        """
        if chat_id in self.pending:
            del self.pending[chat_id]
            return "🚫 Credential save cancelled. Nothing was saved."
        return "No pending credential save."
    
    def has_pending(self, chat_id: str) -> bool:
        """Check if there's a pending save for this chat."""
        return chat_id in self.pending


# Singleton instance
_credential_flow: Optional[CredentialFlow] = None

def get_credential_flow() -> CredentialFlow:
    """Get or create the credential flow singleton."""
    global _credential_flow
    if _credential_flow is None:
        _credential_flow = CredentialFlow()
    return _credential_flow


# =============================================================================
# CLI FOR TESTING
# =============================================================================

def main():
    print("=" * 60)
    print("🔐 CREDENTIAL MANAGER - Test Suite")
    print("=" * 60)
    
    # Test variable name generation
    print("\n1. Testing variable name generation...")
    websites = ["pinterest.com", "amazon.com", "twitter.com", "my-bank.com"]
    
    for site in websites:
        user_var, pass_var = get_env_var_names(site)
        print(f"   {site} -> {user_var}, {pass_var}")
    
    # List existing credentials
    print("\n2. Existing credentials in .env:")
    creds = list_saved_credentials()
    for var, masked in creds.items():
        print(f"   {var}: {masked}")
    
    print("\n" + "=" * 60)
    print("✅ Credential manager ready!")


if __name__ == "__main__":
    main()
