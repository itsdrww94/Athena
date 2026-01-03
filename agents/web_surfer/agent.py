#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     T H E   U N I V E R S A L   E Y E                         ║
║                         `web_surfer.py`                                        ║
║                                                                               ║
║  A vision-powered browser agent with persistent sessions                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- Gemini Vision for element detection (no brittle XPaths)
- Persistent cookies/sessions (stay logged in)
- Natural language commands
- Automatic popup handling

Usage:
    python web_surfer.py --url "https://pinterest.com" --goal "Find mac and cheese recipes"
    python web_surfer.py --url "https://amazon.com" --goal "Search for wireless headphones" --headless

Output Format (for Telegram):
    [RESULT_IMAGE]: /path/to/screenshot.png
    [RESULT_TEXT]: Successfully completed the task.
"""

import os
import sys
import json
import argparse
import base64
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Data directories
ATHENA_DATA_DIR = Path.home() / "athena_data"
BROWSER_STATE_DIR = ATHENA_DATA_DIR / "browser_state"
TEMP_DIR = ATHENA_DATA_DIR / "temp"
SCREENSHOTS_DIR = ATHENA_DATA_DIR / "screenshots"

# Ensure directories exist
for d in [ATHENA_DATA_DIR, BROWSER_STATE_DIR, TEMP_DIR, SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# State file for cookies/localStorage
STORAGE_STATE_FILE = BROWSER_STATE_DIR / "storage_state.json"

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Known sites and their credential env vars
SITE_CREDENTIALS = {
    "pinterest.com": ("PINTEREST_USER", "PINTEREST_PASS"),
    "amazon.com": ("AMAZON_USER", "AMAZON_PASS"),
    "twitter.com": ("TWITTER_USERNAME", "TWITTER_PASSWORD"),
    "x.com": ("TWITTER_USERNAME", "TWITTER_PASSWORD"),
    "reddit.com": ("REDDIT_USER", "REDDIT_PASS"),
    "instagram.com": ("IG_USERNAME", "IG_PASSWORD"),
    "facebook.com": ("FACEBOOK_USER", "FACEBOOK_PASS"),
}

# Maximum steps in vision loop (prevent infinite loops)
MAX_VISION_STEPS = 20


# =============================================================================
# BROWSER SETUP (Playwright)
# =============================================================================

def setup_browser(headless: bool = False) -> Tuple[Any, Any, Any]:
    """
    Initialize Playwright browser with persistent session state.
    
    Returns:
        Tuple of (playwright, browser, context, page)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)
    
    playwright = sync_playwright().start()
    
    # Launch Chromium
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-first-run",
        ]
    )
    
    # Load existing session state (cookies, localStorage) if available
    if STORAGE_STATE_FILE.exists():
        print(f"📦 Loading saved session from {STORAGE_STATE_FILE.name}")
        try:
            context = browser.new_context(
                storage_state=str(STORAGE_STATE_FILE),
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        except Exception as e:
            print(f"⚠️ Could not load session: {e}. Starting fresh.")
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
    else:
        print("🆕 Starting fresh browser session")
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    
    page = context.new_page()
    
    return playwright, browser, context, page


def save_session_state(context) -> bool:
    """Save browser session state (cookies, localStorage) for persistence."""
    try:
        context.storage_state(path=str(STORAGE_STATE_FILE))
        print(f"💾 Session saved to {STORAGE_STATE_FILE.name}")
        return True
    except Exception as e:
        print(f"⚠️ Could not save session: {e}")
        return False


def cleanup_browser(playwright, browser, context):
    """Clean up browser resources."""
    try:
        save_session_state(context)
        context.close()
        browser.close()
        playwright.stop()
    except Exception:
        pass


# =============================================================================
# CREDENTIALS LOOKUP
# =============================================================================

def get_site_credentials(url: str) -> Optional[Tuple[str, str]]:
    """
    Look up credentials for a site from .env file.
    
    SECURITY: Never accept passwords via command line.
    """
    # Extract domain from URL
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    
    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Find matching site
    for site, (user_key, pass_key) in SITE_CREDENTIALS.items():
        if site in domain or domain in site:
            username = os.getenv(user_key)
            password = os.getenv(pass_key)
            
            if username and password:
                return (username, password)
            else:
                print(f"❌ Credentials for {site} not found in .env")
                print(f"   Please add {user_key} and {pass_key} to your .env file")
                return None
    
    return None


# =============================================================================
# VISION LOOP (Gemini Vision)
# =============================================================================

def capture_screenshot(page, name: str = "current") -> str:
    """Capture a screenshot and return the path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{name}_{timestamp}.png"
    filepath = TEMP_DIR / filename
    
    page.screenshot(path=str(filepath), full_page=False)
    return str(filepath)


def get_vision_action(screenshot_path: str, instruction: str, 
                      context_info: str = "") -> Optional[Dict[str, Any]]:
    """
    Send screenshot to Gemini Vision and get the action to perform.
    
    The Vision Loop:
    1. Capture screenshot
    2. Ask Gemini "What should I click/type to achieve [goal]?"
    3. Gemini returns coordinates and action type
    4. Execute the action
    
    Args:
        screenshot_path: Path to current screenshot
        instruction: What the user wants to accomplish
        context_info: Additional context (current URL, previous actions)
    
    Returns:
        Dict with action details or None if task complete/error
    """
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set in .env")
        return None
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Read and encode image
        with open(screenshot_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        system_prompt = """You are a web automation assistant analyzing a browser screenshot.
Your job is to determine the NEXT SINGLE ACTION to achieve the user's goal.

Guidelines:
- Return ONLY a valid JSON object
- If you see cookie consent banners, popups, or overlays blocking the view, dismiss them first
- Look for obvious buttons, links, input fields
- If the task appears complete, set action to "complete"
- If you can't determine what to do, set action to "error"

The viewport is 1280x800 pixels. Coordinates should be within this range.

Return JSON in this exact format:
{
    "action": "click" | "type" | "scroll" | "wait" | "complete" | "error",
    "target_description": "Description of what you're targeting",
    "coordinates": [x, y],
    "text_to_type": "text if action is type",
    "scroll_direction": "up" | "down" (if action is scroll),
    "reasoning": "Why you chose this action"
}"""

        user_prompt = f"""Current goal: {instruction}

{context_info}

Looking at the screenshot, what is the NEXT SINGLE action I should take to achieve this goal?
If the goal appears to be complete, set action to "complete".
Return ONLY valid JSON."""

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                {"role": "user", "parts": [
                    {"text": system_prompt + "\n\n" + user_prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_data}}
                ]}
            ]
        )
        
        # Parse response
        text = response.text.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            action_data = json.loads(json_match.group())
            return action_data
        else:
            print(f"⚠️ Could not parse vision response: {text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Vision API error: {e}")
        return None


def execute_action(page, action: Dict[str, Any]) -> bool:
    """
    Execute the action determined by Gemini Vision.
    
    Translates JSON into Playwright commands.
    """
    action_type = action.get("action", "").lower()
    coords = action.get("coordinates", [0, 0])
    text = action.get("text_to_type", "")
    scroll_dir = action.get("scroll_direction", "down")
    target = action.get("target_description", "unknown element")
    
    try:
        if action_type == "click":
            x, y = coords[0], coords[1]
            print(f"🖱️  Clicking: {target} at ({x}, {y})")
            page.mouse.click(x, y)
            time.sleep(1.5)  # Wait for page reaction
            return True
            
        elif action_type == "type":
            x, y = coords[0], coords[1]
            print(f"⌨️  Typing: '{text[:30]}...' into {target}")
            page.mouse.click(x, y)
            time.sleep(0.3)
            page.keyboard.type(text, delay=50)
            time.sleep(0.5)
            return True
            
        elif action_type == "scroll":
            print(f"📜 Scrolling {scroll_dir}")
            delta = -300 if scroll_dir == "up" else 300
            page.mouse.wheel(0, delta)
            time.sleep(1)
            return True
            
        elif action_type == "wait":
            print("⏳ Waiting for page to load...")
            time.sleep(2)
            return True
            
        elif action_type == "complete":
            print("✅ Task appears to be complete!")
            return True
            
        elif action_type == "error":
            reason = action.get("reasoning", "Unknown error")
            print(f"❌ Could not proceed: {reason}")
            return False
            
        else:
            print(f"⚠️ Unknown action type: {action_type}")
            return False
            
    except Exception as e:
        print(f"❌ Action execution error: {e}")
        return False


def handle_popups(page) -> bool:
    """
    Detect and dismiss common popups/overlays.
    
    Checks for:
    - Cookie consent banners
    - Newsletter signup modals
    - "Subscribe" overlays
    """
    # Common popup selectors to try clicking
    popup_dismiss_selectors = [
        # Cookie banners
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("Accept Cookies")',
        'button:has-text("I Accept")',
        'button:has-text("Got it")',
        'button:has-text("OK")',
        '[aria-label="Accept cookies"]',
        '#onetrust-accept-btn-handler',
        '.cookie-consent-accept',
        
        # Close buttons
        'button:has-text("Close")',
        'button:has-text("No thanks")',
        'button:has-text("Not now")',
        '[aria-label="Close"]',
        '.modal-close',
        '.popup-close',
    ]
    
    dismissed = False
    for selector in popup_dismiss_selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=500):
                element.click()
                print(f"🚫 Dismissed popup: {selector}")
                dismissed = True
                time.sleep(0.5)
        except Exception:
            pass
    
    return dismissed


# =============================================================================
# MAIN VISION LOOP
# =============================================================================

def run_vision_loop(page, url: str, goal: str) -> Tuple[bool, str, str]:
    """
    Main vision loop: repeatedly capture → analyze → act until goal is achieved.
    
    Args:
        page: Playwright page object
        url: Starting URL
        goal: Natural language goal
    
    Returns:
        Tuple of (success, result_text, screenshot_path)
    """
    print(f"\n🌐 Navigating to: {url}")
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Handle initial popups
    handle_popups(page)
    
    steps = 0
    previous_actions = []
    
    while steps < MAX_VISION_STEPS:
        steps += 1
        print(f"\n--- Step {steps}/{MAX_VISION_STEPS} ---")
        
        # Capture current state
        screenshot_path = capture_screenshot(page, f"step_{steps}")
        current_url = page.url
        
        # Build context
        context_info = f"Current URL: {current_url}\n"
        if previous_actions:
            context_info += "Previous actions:\n"
            for pa in previous_actions[-3:]:
                context_info += f"  - {pa}\n"
        
        # Get vision action
        action = get_vision_action(screenshot_path, goal, context_info)
        
        if not action:
            return (False, "Vision analysis failed", screenshot_path)
        
        print(f"🤖 Action: {action.get('action')} - {action.get('reasoning', '')[:50]}")
        
        # Check if complete
        if action.get("action") == "complete":
            final_screenshot = capture_screenshot(page, "final")
            return (True, action.get("reasoning", "Task completed"), final_screenshot)
        
        # Check if error
        if action.get("action") == "error":
            return (False, action.get("reasoning", "Could not proceed"), screenshot_path)
        
        # Execute action
        success = execute_action(page, action)
        
        if not success:
            return (False, "Action execution failed", screenshot_path)
        
        # Record action for context
        previous_actions.append(f"{action.get('action')}: {action.get('target_description', 'unknown')}")
        
        # Handle any popups that appeared
        handle_popups(page)
        
        # Check for page changes
        time.sleep(1)
    
    # Max steps reached
    final_screenshot = capture_screenshot(page, "max_steps")
    return (False, f"Reached maximum {MAX_VISION_STEPS} steps without completing goal", final_screenshot)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Universal Browser Agent - The Universal Eye")
    parser.add_argument("--url", required=True, help="Starting URL")
    parser.add_argument("--goal", required=True, help="Natural language goal")
    parser.add_argument("--visible", action="store_true", 
                        help="Show browser window (default: headless/invisible)")
    parser.add_argument("--login", action="store_true", help="Force login flow")
    
    args = parser.parse_args()
    
    # Headless is default (True), --visible makes it False
    headless = not args.visible
    
    print("=" * 60)
    print("👁️  UNIVERSAL EYE - Web Surfer Agent")
    print("=" * 60)
    print(f"URL: {args.url}")
    print(f"Goal: {args.goal}")
    print(f"Mode: {'👀 VISIBLE (watch live)' if args.visible else '🔇 HEADLESS (background)'}")
    
    # Setup browser with persistent session
    playwright, browser, context, page = setup_browser(headless=headless)
    
    try:
        # Check if login is needed
        if args.login:
            creds = get_site_credentials(args.url)
            if creds:
                print(f"🔑 Credentials found for site")
            else:
                print("⚠️ No credentials found, proceeding without login")
        
        # Run the vision loop
        success, result_text, screenshot_path = run_vision_loop(page, args.url, args.goal)
        
        # Output in format for Telegram
        print("\n" + "=" * 60)
        if success:
            print(f"[RESULT_TEXT]: {result_text}")
            print(f"[RESULT_IMAGE]: {screenshot_path}")
        else:
            print(f"[RESULT_TEXT]: ❌ {result_text}")
            print(f"[RESULT_IMAGE]: {screenshot_path}")
        
    except Exception as e:
        print(f"[RESULT_TEXT]: ❌ Error: {e}")
        
    finally:
        cleanup_browser(playwright, browser, context)


if __name__ == "__main__":
    main()
