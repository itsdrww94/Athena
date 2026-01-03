#!/usr/bin/env python3
"""
NotebookLM Agent
Uses Playwright + Gemini Vision to interact with notebooklm.google.com
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

ATHENA_DATA_DIR = Path.home() / "athena_data"
BROWSER_STATE_DIR = ATHENA_DATA_DIR / "browser_state"
TEMP_DIR = ATHENA_DATA_DIR / "temp"
STORAGE_STATE_FILE = BROWSER_STATE_DIR / "storage_state.json"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

MAX_VISION_STEPS = 15

# Ensure directories exist
for d in [ATHENA_DATA_DIR, BROWSER_STATE_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# BROWSER SETUP
# =============================================================================

def setup_browser(headless: bool = False):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed.")
        sys.exit(1)
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--no-first-run"]
    )
    
    context_args = {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if STORAGE_STATE_FILE.exists():
        print(f"📦 Loading session: {STORAGE_STATE_FILE.name}")
        try:
            context = browser.new_context(storage_state=str(STORAGE_STATE_FILE), **context_args)
        except Exception:
            print("⚠️ Session load failed, starting fresh.")
            context = browser.new_context(**context_args)
    else:
        print("🆕 Starting fresh session. Please login if visible!")
        context = browser.new_context(**context_args)
    
    page = context.new_page()
    return playwright, browser, context, page

def cleanup_browser(playwright, browser, context):
    try:
        context.storage_state(path=str(STORAGE_STATE_FILE))
        print(f"💾 Session saved.")
    except Exception as e:
        print(f"⚠️ Save failed: {e}")
    context.close()
    browser.close()
    playwright.stop()

# =============================================================================
# VISION LOGIC
# =============================================================================

def capture_screenshot(page, name="step") -> str:
    path = TEMP_DIR / f"notebook_{name}_{int(time.time())}.png"
    page.screenshot(path=str(path))
    return str(path)

def get_vision_action(screenshot_path: str, goal: str, context: str) -> Optional[Dict]:
    if not GEMINI_API_KEY:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        with open(screenshot_path, "rb") as f:
            img_data = base64.standard_b64encode(f.read()).decode("utf-8")

        system_prompt = """You are navigating Google NotebookLM.
Analyze the screenshot and determine the NEXT SINGLE ACTION to achieve the goal.
Return valid JSON only.

Format:
{
    "action": "click" | "type" | "wait" | "complete" | "error",
    "coordinates": [x, y],
    "text_to_type": "string",
    "reasoning": "brief explanation"
}

Common Targets:
- "New Notebook": Huge plus button or card.
- "Add Source": Button usually on left sidebar.
- "Chat": Input box at bottom.
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                {"role": "user", "parts": [
                    {"text": f"{system_prompt}\n\nGOAL: {goal}\nCONTEXT: {context}"},
                    {"inline_data": {"mime_type": "image/png", "data": img_data}}
                ]}
            ]
        )
        
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    
    except Exception as e:
        print(f"❌ Vision Error: {e}")
        return None

def execute_action(page, action: Dict) -> bool:
    act = action.get("action")
    coords = action.get("coordinates", [0,0])
    
    try:
        if act == "click":
            print(f"🖱️ Clicking {coords}")
            page.mouse.click(coords[0], coords[1])
            time.sleep(2)
        elif act == "type":
            text = action.get("text_to_type", "")
            print(f"⌨️ Typing: {text}")
            page.mouse.click(coords[0], coords[1])
            time.sleep(0.5)
            page.keyboard.type(text)
            page.keyboard.press("Enter")
            time.sleep(2)
        elif act == "wait":
            print("⏳ Waiting...")
            time.sleep(3)
        return True
    except Exception:
        return False

# =============================================================================
# MAIN LOOP
# =============================================================================

def run_notebook_task(command: str, argument: str, visible: bool):
    playwright, browser, context, page = setup_browser(not visible)
    
    try:
        url = "https://notebooklm.google.com/"
        print(f"🌐 Opening {url}")
        page.goto(url)
        time.sleep(3)

        # Construct Goal
        if command == "create":
            goal = f"Create a new notebook titled '{argument}'"
        elif command == "source":
            goal = f"Add a new website source with URL: {argument}"
        elif command == "query":
            goal = f"Type '{argument}' into the chat box and submit"
        else:
            goal = f"Perform action: {command} {argument}"

        print(f"🎯 Goal: {goal}")

        steps = 0
        while steps < MAX_VISION_STEPS:
            steps += 1
            print(f"--- Step {steps} ---")
            
            # 1. Capture
            shot = capture_screenshot(page)
            
            # 2. Analyze
            action = get_vision_action(shot, goal, f"Current Step: {steps}")
            
            if not action:
                print("❌ No action determined.")
                break
                
            print(f"🤖 Plan: {action.get('reasoning')}")
            
            if action.get("action") == "complete":
                print("✅ Task Complete.")
                break
            
            if action.get("action") == "error":
                print("❌ Agent gave up.")
                break

            # 3. Execute
            execute_action(page, action)
            
    finally:
        cleanup_browser(playwright, browser, context)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create", "source", "query"])
    parser.add_argument("argument", help="Name, URL, or Question")
    parser.add_argument("--visible", action="store_true")
    # Athena CLI injects --context, so we use parse_known_args to ignore it (or add it if needed later)
    args, unknown = parser.parse_known_args()
    
    run_notebook_task(args.command, args.argument, args.visible)

if __name__ == "__main__":
    main()
