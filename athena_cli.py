#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           A T H E N A   C L I                                  ║
║                    Personal Super Agentic AI System                            ║
║                                                                                ║
║  "The Body" - Local client connecting to the Cloud Brain (n8n + Gemini)        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Author: Project Athena
Python: 3.14+ Compatible (uses pygame for audio, not playsound)
"""

import os
import re
import sys
import time
import json
import subprocess
import tempfile

# Force UTF-8 encoding for Windows consoles to prevent crashes with emojis/ASCII art
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import requests

# =============================================================================
# WINDOWS CONSOLE ENCODING FIX (Must be early, before any emoji prints)
# =============================================================================
# Fix Windows cp1252 console encoding for emoji support
import io
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # Fallback if already wrapped

from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

# Rich library for beautiful terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich.theme import Theme
from rich.highlighter import RegexHighlighter
from rich.markdown import Markdown
from rich import box

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter, FuzzyCompleter, Completer, Completion
    from prompt_toolkit.styles import Style as PromptStyle
    from prompt_toolkit.formatted_text import HTML
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

# Environment and utilities
from dotenv import load_dotenv
import typer

# Initialize console early (before any code uses it)
console = Console()

# =============================================================================
# BOOT HEALTH CHECK
# =============================================================================
def print_boot_diagnostics():
    """Print interpreter info and environment status at startup."""
    console.print(f"[dim]Python: {sys.executable}[/dim]")
    console.print(f"[dim]Version: {sys.version.split()[0]}[/dim]")
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        console.print(f"[dim]Venv: {Path(venv).name}[/dim]")

print_boot_diagnostics()

# Local modules
import launcher
# Auto-import for startup sync
dna_ingest = None
causality_core = None
cloud_analyst = None

try:
    from agents.dna_ingest.agent import run_ingestion
    dna_ingest = type('Module', (), {'run_ingestion': run_ingestion})()
except ImportError as e:
    console.print(f"[dim yellow]Warning: dna_ingest not loaded: {e}[/dim yellow]")

try:
    from analysis_engines import causality_core
except ImportError as e:
    console.print(f"[dim yellow]Warning: causality_core not loaded: {e}[/dim yellow]")


try:
    from super_agents.Jarvis.core.orchestrator import JarvisOrchestrator
except ImportError:
    pass # Jarvis might not be set up yet


# =============================================================================
# AUTO-SYNC & ANALYSIS (Optional - can be skipped)
# =============================================================================

# Skip startup sync with environment variable: ATHENA_SKIP_SYNC=1
SKIP_STARTUP_SYNC = os.getenv("ATHENA_SKIP_SYNC", "0") == "1"

def sync_and_analyze():
    """
    Startup Routine (OPTIONAL):
    1. Ingest new personal files (DNA)
    2. Sync influence cloud to Supabase
    3. Run immediate analysis
    
    Set ATHENA_SKIP_SYNC=1 to skip this on startup for faster loading.
    """
    if SKIP_STARTUP_SYNC:
        console.print("[dim]⏭ Startup sync skipped (ATHENA_SKIP_SYNC=1)[/dim]")
        return
    
    console.print(Panel("[bold cyan]🔄 INITIATING CLOUD SYNC & ANALYSIS...[/bold cyan]", border_style="cyan"))
    
    errors_encountered = []
    
    # 1. Ingest DNA
    try:
        if dna_ingest:
            console.print("[dim]🧬 Checking for new personal data...[/dim]")
            results = dna_ingest.run_ingestion()
            if results.get("total_processed", 0) > 0:
                console.print(f"[green]✅ Ingested {results['total_processed']} new items.[/green]")
            else:
                console.print("[dim]   No new data found.[/dim]")
        else:
            console.print("[dim]   DNA ingest not available.[/dim]")
    except Exception as e:
        errors_encountered.append(f"DNA: {e}")

    # 2. Sync Influence Cloud (skip if credentials missing)
    try:
        if causality_core:
            console.print("[dim]☁️ Syncing Influence Cloud...[/dim]")
            cloud = causality_core.InfluenceCloud()
            count = cloud.sync_all_to_cloud()
            console.print(f"[green]✅ Synced {count} influences to cloud.[/green]")
        else:
            console.print("[dim]   Cloud sync not available.[/dim]")
    except Exception as e:
        error_msg = str(e)
        if "credentials" in error_msg.lower() or "authentication" in error_msg.lower():
            console.print("[dim yellow]   ⏭ Cloud sync skipped (credentials not configured)[/dim yellow]")
        else:
            errors_encountered.append(f"Cloud: {e}")

    # 3. Trigger Deep Mind Analysis
    try:
        console.print("[dim]🧠 Running Deep Mind Analysis...[/dim]")
        from analysis_engines.deep_mind import DeepMind
        
        dm = DeepMind()
        # Try without cloud upload first if credentials are missing
        try:
            profile = dm.run_deep_analysis(upload_to_cloud=True)
        except Exception as cloud_err:
            if "credentials" in str(cloud_err).lower():
                console.print("[dim yellow]   ⏭ Cloud upload skipped (continuing local analysis)[/dim yellow]")
                profile = dm.run_deep_analysis(upload_to_cloud=False)
            else:
                raise
        
        if profile:
            focus = profile.get("current_focus", "Unknown")
            mood = profile.get("emotional_state", "Neutral")
            summary = profile.get("summary", "Analysis complete.")
            console.print(f"[bold green]✅ Deep Analysis Complete![/bold green]")
            console.print(f"[cyan]   Focus: {focus}[/cyan]")
            console.print(f"[cyan]   Mood: {mood}[/cyan]")
            if summary and isinstance(summary, str):
                console.print(f"[dim]   {summary[:200]}...[/dim]")
        else:
            console.print("[dim]   Analysis returned no profile.[/dim]")
    except ImportError:
        console.print("[dim]   Deep Mind not available.[/dim]")
    except Exception as e:
        error_msg = str(e)
        if "credentials" in error_msg.lower():
            console.print("[dim yellow]   ⏭ Deep analysis skipped (cloud credentials not configured)[/dim yellow]")
        else:
            errors_encountered.append(f"DeepMind: {e}")
    
    # Summary
    if errors_encountered:
        console.print(Panel(f"[bold yellow]⚠ SYNC COMPLETED WITH {len(errors_encountered)} ISSUE(S)[/bold yellow]", border_style="yellow"))
        for err in errors_encountered[:3]:  # Show first 3 errors
            console.print(f"[dim red]   {err}[/dim red]")
    else:
        console.print(Panel("[bold green]✨ SYSTEM SYNCHRONIZED[/bold green]", border_style="green"))



# =============================================================================
# GLOBAL STATE & CORE
# =============================================================================

# Initialize Logic Cores
try:
    from core.memory.context_stack import ContextStack
    from core.orchestrator.semantic_router import SemanticRouter
    
    context_stack = ContextStack()
    router = SemanticRouter()
    console.print("[dim]🧠 Semantic Core Loaded.[/dim]")
except ImportError as e:
    console.print(f"[dim yellow]⚠ Semantic Core unavailable ({e}). Fallback to Keyword Mode.[/dim yellow]")
    context_stack = None
    router = None

# =============================================================================
# NEW ORCHESTRATOR INTEGRATION (2025 Architecture)
# =============================================================================
# Set ATHENA_USE_NEW_ORCHESTRATOR=1 to enable the new unified orchestrator
# This provides a gradual migration path while preserving existing functionality

NEW_ORCHESTRATOR_ENABLED = os.getenv("ATHENA_USE_NEW_ORCHESTRATOR", "0") == "1"

def try_new_orchestrator(user_input: str, interface: str = "cli") -> Optional[str]:
    """
    Attempt to process input through the new orchestrator.
    Returns response if handled, None to fall back to legacy processing.
    """
    if not NEW_ORCHESTRATOR_ENABLED:
        return None
    
    try:
        from core.app import run_athena
        response = run_athena(
            input_message=user_input,
            interface=interface,
            user_id="default",
            session_id="cli"
        )
        return response
    except ImportError:
        return None
    except Exception as e:
        console.print(f"[dim yellow]⚠ New orchestrator error: {e}[/dim yellow]")
        return None

if NEW_ORCHESTRATOR_ENABLED:
    console.print("[bold green]🚀 New Orchestrator: ENABLED (ATHENA_USE_NEW_ORCHESTRATOR=1)[/bold green]")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
VISION_CACHE_DIR = BASE_DIR / "vision_cache"
ASSETS_DIR = BASE_DIR / "assets"
SECURE_DATA_DIR = BASE_DIR / "secure_data"

# Ensure directories exist
VISION_CACHE_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
SECURE_DATA_DIR.mkdir(exist_ok=True)

# Cloud configuration
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# =============================================================================
# THEMES & VISUALS
# =============================================================================

class AthenaHighlighter(RegexHighlighter):
    """Apply Cyberpunk highlights to keywords"""
    base_style = "athena."
    highlights = [
        r"(?P<money>\$\d{1,3}(,\d{3})*(\.\d{2})?)",  # $12.34
        r"(?P<email>[\w\.-]+@[\w\.-]+)",             # Emails
        r"(?P<url>https?://\S+)",                    # URLs
        r"(?P<command>^/[a-z0-9_]+)",                # /commands
        r"(?P<keyword>Online|Connected|Ready|Logged)",
        r"(?P<error>Error|Failed|Unavailable)",
        r"(?P<warning>Warning|Attention)",
        r"(?P<prompt>ATHENA >)",
    ]

# Cyberpunk Neon Theme
cyber_theme = Theme({
    "athena.money": "bold #00ff00",
    "athena.email": "bold #00ffff",
    "athena.url": "underline #5e5ce6",
    "athena.command": "bold #ff00ff",
    "athena.keyword": "bold #39ff14",
    "athena.error": "bold red",
    "athena.warning": "bold yellow",
    "athena.prompt": "bold #00E676",
    "info": "#00ffff",
    "success": "#00ff00",
    "warning": "#ffaa00",
    "error": "#ff0000",
})

# Console with custom theme
console = Console(theme=cyber_theme, highlighter=AthenaHighlighter())

# =============================================================================
# COLOR SCHEME (Google CLI Inspired - Blue/Cyan)
# =============================================================================

COLORS = {
    "primary": "#4285F4",      # Google Blue
    "secondary": "#00BCD4",    # Cyan
    "accent": "#1DE9B6",       # Teal/Mint
    "success": "#00E676",      # Green
    "warning": "#FFAB00",      # Amber
    "error": "#FF5252",        # Red
    "text": "#E8EAED",         # Light gray
    "muted": "#9AA0A6",        # Muted gray
}

STYLE_PRIMARY = Style(color=COLORS["primary"], bold=True)
STYLE_SECONDARY = Style(color=COLORS["secondary"])
STYLE_ACCENT = Style(color=COLORS["accent"], bold=True)
STYLE_SUCCESS = Style(color=COLORS["success"])
STYLE_WARNING = Style(color=COLORS["warning"])
STYLE_ERROR = Style(color=COLORS["error"])
STYLE_MUTED = Style(color=COLORS["muted"])

# =============================================================================
# ASCII ART - GEAR 5 LUFFY (NIKA)
# =============================================================================

ATHENA_LOGO = """
[bold white]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠤⠄⠠⡀⠀⠀⢠⠻⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠊⠀⠀⠀⠹⠤⠔⢋⣰⡇⠀⠀⠀⠀⠀⠀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠄⢒⣒⢲⡦⠀⢘⠀⡠⠊⠉⣩⠗⠈⠉⠉⢀⣀⡀⠀⠀⠀⡜⡝⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠣⢄⠁⣸⡀⠀⠀⠘⠀⢇⠀⠀⢧⠀⠀⡠⢊⢠⣤⠞⠇⠀⠀⡆⣧⠀⠀⠀⠀⠀⢀⠀⠠⠀⠤⢖⠀⠀⠁⠀⠒⠤⢀⡀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢡⢈⠓⡲⠊⠁⡄⠈⠉⠒⠚⠉⠉⢰⢁⣸⣀⣀⣀⠠⠖⠀⡱⠑⣀⠠⠊⠁⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠁⠀⠀⠉⠒⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡴⡆⠀⠀⢀⠌⠈⠉⠀⠀⢰⢇⠀⠀⠀⠀⠀⠀⠈⠁⠀⠀⢀⡄⠀⠀⡰⠃⠀⢻⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⡉⠀⠀⠀⠀⠀⠀⠈⢂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣇⠙⠠⣶⢁⡶⡄⠘⡄⠀⢸⠀⠉⠉⠈⠝⠀⠀⠀⢀⡀⠤⢪⠃⠀⣼⣿⣟⡳⣏⠀⠀⣠⠇⠀⠀⠀⠀⠀⠀⣠⠖⢲⠋⠀⠈⡇⠀⠀⠀⠀⠂⠀⠀⠱⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡜⢸⠀⢸⡰⢼⣻⠃⢀⠛⣄⠸⣀⠀⡀⠀⠀⠀⠀⠀⠀⠀⡴⠁⠀⣴⡿⢉⡀⠱⣿⠀⢰⡏⠀⠀⠀⠀⠀⠀⢸⣁⣀⠀⠀⠀⠀⣹⠀⠀⠀⠀⠀⢡⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠔⠉⡰⠃⠀⡀⠑⠚⠁⠀⢸⠀⣠⠟⠉⢉⠩⣉⣙⣲⣦⣤⣀⡀⢧⠀⠀⢿⡼⣿⣾⠀⠛⠦⢏⠣⠎⠁⠐⠂⠒⠈⠲⡇⠀⠀⠀⢀⡰⠃⠀⠀⠀⠀⠀⠀⠀⠀⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⣸⠀⠀⠀⠟⠒⠐⠒⠒⣺⠛⢀⣠⣾⠵⠒⠒⠒⠒⠒⠲⣦⣿⣿⡦⠤⠠⠝⢛⡩⠀⠀⠀⢸⠀⡇⠀⠀⠀⠀⠀⠀⠈⡝⠋⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡄⠘⡄⠀⠀⠘⢆⠀⣠⠞⠁⠾⠋⣩⣤⠛⢶⡶⣶⠶⡶⣶⣾⣿⠿⢷⣀⠤⠔⠒⠁⠀⢀⡤⠊⢀⠇⠀⠀⠀⠀⠀⢠⠊⢀⡴⠒⠒⣄⠀⠀⠀⠀⠀⠀⢀⡜⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢦⠈⠢⡀⠀⠘⡴⠁⠀⠀⣠⣿⡿⠛⠆⠈⠃⢉⣙⣻⣉⣃⣀⣤⠘⢷⣤⣀⡀⠀⡴⣃⠄⠊⠁⠀⠀⠀⠀⠀⢀⠇⢠⡏⠀⠀⠀⢸⠀⠀⠀⠀⢀⣴⠃⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠴⠂⠀⢀⣴⠊⠉⠆⠀⣀⣀⠤⠤⠤⠘⠒⠒⠛⠂⠉⣁⣤⢶⣿⡿⠋⢀⡠⠔⠊⠉⠉⠉⠉⠉⠙⠛⡇⠀⢸⣽⣷⠉⠉⣰⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⢆⠀⠓⠤⡀⠀⡟⠀⠀⠠⠚⠉⠀⠀⠀⡥⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⠝⠈⠓⠒⠉⠀⠀⢸⠉⠀⠀⠀⠀⣀⣀⣠⢤⠴⣶⣯⣷⣾⠿⠋⣠⠖⠁⢀⣠⣴⣶⣿⣿⣷⣶⣦⣤⠃⠀⣸⡿⡟⢀⡤⠼⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠂⠀⠀⣠⠞⠀⠀⠀⡀⠀⠀⠀⠀⢀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⠃⠀⠀⠀⢀⡀⠀⠀⠀⠙⠒⢲⡞⣍⣳⠬⢶⠻⡏⡟⣾⣷⢧⣤⣴⠃⢀⣴⣿⣿⣿⠿⣟⡿⣿⣿⣿⡟⠀⢀⡯⠊⠀⠘⢦⠰⠀⢀⠤⠀⠂⠤⣀⠀⠀⠀⢀⣨⠔⠊⠁⠀⠀⠀⠊⠀⠀⠀⠀⣠⠊⠀⠀⠀⠀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡠⠐⠈⠀⠀⠀⢰⣄⠀⠿⡀⠀⠀⠀⠀⢀⡏⠁⢀⠴⠚⠈⢷⣾⢿⣼⡄⠙⠧⣀⣾⣿⣿⣿⣭⢟⢫⡙⢭⣹⠟⠀⢀⡾⠒⠉⠉⠉⠀⣀⠆⠁⠀⠀⠀⠀⠀⠈⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠠⠔⠋⠀⡠⠔⠀⠈⠀⠀⠀⠁⠢⡀⢀⣠⡀⠀⢀⠔⠈⣁⠱
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡔⠁⡆⠀⠀⠀⠀⠰⣌⡣⣽⡀⢳⡀⢀⣴⡾⠟⠁⠀⠘⣗⣒⣊⠥⣀⠸⣿⣿⡦⣀⠈⠙⠻⠿⢯⣔⣊⣦⡽⠖⠋⠀⣠⣾⠁⠀⠀⠀⠀⡔⠁⠀⠀⠀⢀⣀⠠⠠⠤⠀⠠⠀⠀⠐⠒⠒⠒⠒⠈⠁⠀⠀⠀⠀⠎⠀⠀⠀⣠⡴⢢⡀⠀⠀⢳⠎⡘⢀⡴⠡⠊⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⡇⠀⠀⠀⠀⠀⢨⣋⠈⢷⡘⡏⠁⠙⡆⠀⠀⠀⢠⠚⠀⠀⠀⠈⠣⡘⠛⢯⠭⠵⠢⢄⣀⡀⠀⠀⢀⣀⣠⢴⣺⡝⠱⠀⠀⠀⢀⠌⠀⠀⢀⡴⠚⠉⠉⠉⠐⢄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⠀⠀⠠⢠⠏⡆⢠⠇⠀⠀⣸⠀⠙⠊⠀⡇⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠐⠀⢣⠀⠀⠀⠀⠀⠀⠀⠙⢶⣿⠛⠉⠉⣠⠤⠐⠊⠁⠀⠀⠀⠀⠀⠀⠈⠉⠑⠛⠒⠊⠁⠙⢦⢹⠸⣌⠳⣘⠶⠃⠀⠀⣇⠀⣀⡎⠀⠀⢪⡏⠀⠀⣆⠀⠀⠀⠀⠡⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡸⠀⠀⠁⣏⠀⠛⠋⣀⡤⠞⠁⠀⠀⠀⠀⡆⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢆⠀⠀⢣⠀⠀⠀⠀⠀⠀⠀⠀⠙⢤⡀⡜⠁⠀⠀⠀⠀⣀⠤⠐⠈⠉⠉⠁⠢⡤⡀⠀⠀⠀⠀⠀⡯⠷⣌⡷⠋⠀⠀⠀⠀⠘⢯⢼⠁⠀⠠⡏⢳⣄⠀⣿⠀⠀⠀⠀⠀⢣⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⠁⠀⠀⠀⠘⢲⣒⠉⠁⠀⠀⠀⠀⠀⢀⡜⠀⠀⠀⠀⢀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠣⣀⠀⠣⡀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠐⠢⠤⠒⡈⢁⠀⠤⠠⠤⣤⠤⣀⠀⢁⠀⠱⡀⣀⠠⣤⠇⠀⠀⠀⠀⠀⠀⠀⣀⣠⣼⠾⡀⠀⠀⣷⢄⢿⡂⣹⡇⠀⠀⠀⠀⠀⠡⡀⠀⠀⠀⠀⠀⠀⠀⠀⠠⠃⠀⠀⠀⢀⠎⠥⠜⠀⠀⠀⠀⣀⡤⠖⠋⣀⠠⠄⠒⠈⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠑⣦⡘⠢⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠑⡌⣧⠘⡀⠀⢣⡏⣸⠀⣀⣀⣀⡀⠀⠀⠀⣼⡟⠋⠀⠀⣷⡀⠀⠹⡌⠳⣷⣸⡏⢆⠀⠀⠀⠀⠀⠐⢄⠀⠀⠀⠀⠀⢀⠔⠁⠀⠀⠀⣀⠮⠤⢄⡠⢤⠤⣶⡯⠗⠒⠉⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠔⠈⠈⠓⠾⣦⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢀⠀⢠⡄⢸⣺⡄⠁⠀⡸⢧⣻⠍⠟⠛⠛⢿⠷⠀⡀⠉⣠⣆⣤⡾⣿⣷⣄⠀⠈⢦⡈⢎⠳⣄⠱⡀⠀⠀⠀⠀⠀⠱⡆⠒⠒⠀⠁⠀⣠⠤⡤⠊⢀⣄⠀⡠⣤⡾⠒⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡎⠀⠀⠀⠀⠀⠀⠉⠓⠢⠄⣀⠀⠀⠀⠀⠀⠠⣄⡀⠘⢆⠣⠀⢧⠀⣿⠃⠀⠀⣽⢬⢯⡳⣷⢦⣤⠤⣿⠷⣷⡞⠉⢿⣿⡿⠃⣿⣏⢶⣄⠀⠙⠮⣀⠈⠳⡌⢢⡀⠀⠀⣀⡀⠈⠣⡀⠀⢠⠋⠀⠀⠀⢀⠎⢸⢉⡵⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣧⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢃⣀⡴⠀⠂⠠⡀⠀⠀⠀⠀⠀⠈⠑⠒⠠⢄⡀⠉⢮⠂⡌⣆⠱⡘⠀⣿⠀⠀⠘⠀⠀⢳⡑⡞⣾⢋⣶⣀⠀⢹⣷⠀⠀⢀⡄⣠⡿⢿⡈⠙⢵⡢⢄⣈⣉⡒⠼⢦⠈⢦⣼⢫⣿⠞⠉⢉⡦⡇⠀⠀⠀⢠⢻⣆⡼⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣯⡳⣄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠬⠒⠂⢄⡀⡾⠀⠀⠀⠀⠀⠀⠀⠀⠀⡔⠃⠀⠑⠢⢙⠢⢸⡄⢷⠀⡏⠠⠀⠀⠀⠘⣷⡄⠘⣿⣯⢿⣧⠀⢻⡆⠀⠺⡼⢋⣷⢬⣣⠀⡀⣀⢉⡒⢦⣌⣉⣉⡳⣼⢰⠏⣏⡀⣠⡿⠀⠀⠀⠀⢀⣼⢼⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠻⣼
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡰⠁⠀⣠⠖⠀⠘⣇⠀⠀⠀⠀⠀⠀⠀⠀⠸⠀⠀⠀⠀⠀⠀⠑⠢⡇⢼⢸⠁⠁⠀⠀⠀⠀⡏⢣⠀⣿⣿⠏⠃⠀⢸⣷⣄⣤⣤⡽⠶⠚⠉⠛⡣⠄⠀⢀⠉⠈⠁⠀⠉⠉⠉⠉⠉⠉⢓⠃⠀⠀⠀⣠⣞⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
[/bold white]
"""



ATHENA_BANNER = """
[bold cyan]
    ╔═══════════════════════════════════════════════════════════════╗
    ║     █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗         ║
    ║    ██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗        ║
    ║    ███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║        ║
    ║    ██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║        ║
    ║    ██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║        ║
    ║    ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝        ║
    ╚═══════════════════════════════════════════════════════════════╝
[/bold cyan]
[bold #4285F4]           ◆ PERSONAL SUPER AGENTIC SYSTEM ◆[/bold #4285F4]
[#00BCD4]                  「 SYSTEM ONLINE 」[/#00BCD4]
"""

# =============================================================================
# GEAR 5 OVERRIDE (Replaces ASCII Art)
# =============================================================================

ATHENA_LOGO = """
[bold #E0B0FF]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣷⣤⠀⠀⠀⠀⠀⠀⠀⡀⠀⣀⣀⣴⣶⠞⠁⣀⣤⠤⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣾⠿⣿⣿⡯⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣧⣤⣾⣿⣁⣀⠀⠀⠀⢀⣀⣤⣤⣄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⡏⠁⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⣰⣾⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⢈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣿⠟⠛⠿⣿⣿⣿⣿⣿⣶⣶⣦⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣶⣿⣿⣶⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡉⠀⠀⠀⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⣇⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⣠⣤⣤⣴⣿⣿⣿⣿⣿⣿⣿⡿⠃⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠛⠛⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣿⣿⣿⣿⣿⡿⠿⠿⠿⠿⠿⠋⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⠿⠿⣿⣿⣷⣶⣶⣶⣾⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣤⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣨⣿⠟⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⢿⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⠃⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⢸⣿⣿⣿⣿⡿⠇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⣤⣤⣤⣤⣶⣿⣷⣄⠀⠀⠀⠀⠸⣿⣿⣷⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇⠀⠀⠉⢹⣿⣿⠉⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⢿⣿⠇⠀⠀⠀⠀⠀⢸⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣿⡿⠛⠛⢛⣿⣿⣿⣿⣿⣿⣿⣿⣷⣤⣤⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣸⣿⡁⠀⠀⠀⠀⠀⣸⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⠟⠀⠀⠀⠀⠛⠛⠛⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⣠⣤⣴⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢸⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠄⠀⢿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠛⠋⠉⠻⢿⣷⣦⣼⣿⣿⣟⣉⣠⣤⣤⣄⠀⠀⠀⠀⠀
⠀⣠⣄⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⠀⢹⣿⣿⣿⣆⠀⢀⣴⣤⣤⡿⠉⠉⠉⠉⠉⠁⠀⠀⠀⠉⢷⠀⠀⠀⠀
⣼⣿⣿⣦⣤⣀⠀⢸⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣧⠀⠀⣿⣿⣿⣿⣿⠿⠿⢿⣿⠁⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀
⠈⠿⣿⣿⣿⣿⣷⣾⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠘⠛⠛⠋⠁⠀⢰⣿⣷⣶⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠉⢿⣿⣿⣿⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣷⡄⠀⠀⠀⠀⠀⢠⣾⢿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠹⣿⣿⠿⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⠇⠀⠀⠀⠀⢰⣿⠏⠀⠈⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠈⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣏⠀⠀⠀⢀⣴⡿⠋⠀⠀⠀⠸⣿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠙⢿⣿⣿⣿⣿⣷⣶⣶⣿⠟⠁⠀⠀⠀⠀⠀⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠻⠿⠿⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
[/bold #E0B0FF]
"""

ATHENA_BANNER = """
[bold #8F00FF] █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗ [/bold #8F00FF]
[bold #A100FF]██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗[/bold #A100FF]
[bold #B300FF]███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║[/bold #B300FF]
[bold #C400FF]██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║[/bold #C400FF]
[bold #D600FF]██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║[/bold #D600FF]
[bold #E0B0FF]╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝[/bold #E0B0FF]

[bold #00BCD4] ◆ Ä†HÈñÄ SYSTEM: ONLINE ◆ [/bold #00BCD4]
"""

STARTUP_ANIMATION_FRAMES = [
    "[cyan]█[/cyan]",
    "[cyan]██[/cyan]",
    "[cyan]███[/cyan]",
    "[cyan]████[/cyan]",
    "[cyan]█████[/cyan]",
    "[cyan]██████[/cyan]",
    "[cyan]███████[/cyan]",
    "[cyan]████████[/cyan]",
    "[cyan]█████████[/cyan]",
    "[cyan]██████████[/cyan]",
]

# =============================================================================
# AUDIO SYSTEM (winsound - Python 3.14 Compatible, Windows built-in)
# =============================================================================

def init_audio():
    """Initialize audio system - using winsound (no init needed)"""
    try:
        import winsound
        return True
    except Exception as e:
        console.print(f"[yellow]⚠ Audio system unavailable: {e}[/yellow]")
        return False

def play_audio(audio_url: str) -> bool:
    """
    Download and play audio from URL using winsound
    
    Args:
        audio_url: URL to audio file
        
    Returns:
        bool: Success status
    """
    try:
        import winsound
        
        # Download audio to temp file
        response = requests.get(audio_url, timeout=10)
        response.raise_for_status()
        
        # Create temp file (winsound only supports WAV)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(response.content)
            temp_path = f.name
        
        # Play audio
        winsound.PlaySound(temp_path, winsound.SND_FILENAME)
        
        # Cleanup
        os.unlink(temp_path)
        
        return True
        
    except Exception as e:
        console.print(f"[yellow]⚠ Audio playback error: {e}[/yellow]")
        return False

def play_local_sound(sound_name: str) -> bool:
    """Play a local sound file from assets directory"""
    try:
        import winsound
        
        sound_path = ASSETS_DIR / f"{sound_name}.wav"
        
        if sound_path.exists():
            winsound.PlaySound(str(sound_path), winsound.SND_FILENAME)
            return True
        return False
        
    except Exception as e:
        return False

# =============================================================================
# STREAMING TEXT EFFECT
# =============================================================================

def stream_text(text: str, delay: float = 0.02, style: str = None):
    """
    Print text character by character with typing effect
    
    Args:
        text: Text to stream
        delay: Delay between characters (seconds)
        style: Rich style to apply
    """
    for char in text:
        if style:
            console.print(char, style=style, end="")
        else:
            console.print(char, end="")
        sys.stdout.flush()
        time.sleep(delay)
    console.print()  # Newline at end

def stream_response(text: str, delay: float = 0.015):
    """
    Stream a response with Gemini CLI style Panel
    """
    # Use Live display for streaming effect into a Panel
    with Live(Panel("", title="✦ Athena (Gemini 3.0 Pro)", border_style="#800080"), refresh_per_second=10) as live:
        current_text = ""
        chunk_size = 2
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            current_text += chunk
            live.update(Panel(Markdown(current_text), title="✦ Athena (Gemini 3.0 Pro)", border_style="#800080"))
            time.sleep(delay)
    console.print()

# =============================================================================
# ASCII ANIMATION SYSTEM
# =============================================================================

def animate_ascii(frames: list, cycles: int = 1, delay: float = 0.1):
    """
    Animate ASCII art frames
    
    Args:
        frames: List of ASCII art strings
        cycles: Number of animation cycles
        delay: Delay between frames
    """
    for _ in range(cycles):
        for frame in frames:
            console.clear()
            console.print(frame)
            time.sleep(delay)

def loading_animation(message: str = "Processing", duration: float = 2.0):
    """Show a loading spinner with message"""
    with console.status(f"[bold #E0B0FF]{message}...[/bold #E0B0FF]", spinner="dots", spinner_style="#BF40BF"):
        time.sleep(duration)

# =============================================================================
# GLOBAL STATE
# =============================================================================
ATHENA_STATE = "READY" # READY, THINKING, SPEAKING
ATHENA_ALLOW_ALL = False # If True, bypass permission gates

# =============================================================================
# VISION SYSTEM
# =============================================================================

def capture_screen() -> Optional[Path]:
    """
    Capture the current screen and save to vision_cache
    
    Returns:
        Path to saved screenshot or None on failure
    """
    try:
        import pyautogui
        from PIL import Image
        
        # Small delay to hide terminal if needed
        time.sleep(0.5)
        
        # Capture screen
        screenshot = pyautogui.screenshot()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.png"
        filepath = VISION_CACHE_DIR / filename
        
        # Save screenshot
        screenshot.save(filepath)
        
        # Also save as current_view for quick access
        current_view = VISION_CACHE_DIR / "current_view.png"
        screenshot.save(current_view)
        
        return filepath
        
    except Exception as e:
        console.print(f"[red]❌ Screen capture failed: {e}[/red]")
        return None

def send_vision_to_cloud(image_path: Path) -> Optional[str]:
    """
    Send captured image to n8n webhook for analysis
    
    Args:
        image_path: Path to image file
        
    Returns:
        Analysis response or None
    """
    if not N8N_WEBHOOK_URL:
        console.print("[yellow]⚠ N8N_WEBHOOK_URL not configured. Cannot send to cloud.[/yellow]")
        return None
    
    try:
        with open(image_path, "rb") as f:
            files = {"image": (image_path.name, f, "image/png")}
            data = {"command": "vision", "timestamp": datetime.now().isoformat()}
            
            response = requests.post(
                N8N_WEBHOOK_URL,
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", result.get("text", str(result)))
            
    except Exception as e:
        console.print(f"[red]❌ Failed to send to cloud: {e}[/red]")
        return None

# =============================================================================
# CLOUD COMMUNICATION
# =============================================================================

def send_to_chatgpt(message: str) -> Optional[dict]:
    """
    Fallback to OpenAI's ChatGPT if Gemini fails.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        console.print("[dim]🤖 Using Fallback: OpenAI GPT-4o[/dim]")
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are Athena, a helpful AI assistant. You are a fallback brain because the primary system is offline. Be concise and helpful."},
                {"role": "user", "content": message}
            ]
        )
        
        return {"response": completion.choices[0].message.content}
        
    except Exception as e:
        console.print(f"[red]❌ ChatGPT Fallback Failed: {e}[/red]")
        return None

def send_to_cloud(message: str, command_type: str = "chat") -> Optional[dict]:
    """
    Send message to AI brain - uses Gemini directly, falls back to ChatGPT, then n8n.
    """
    response = None
    
    # 1. Try Gemini API (Primary)
    if GEMINI_API_KEY:
        try:
            response = send_to_gemini(message)
            # If Gemini explicitly returns an error message in the dict, trigger fallback
            if response and "response" in response and "Error" in response["response"]:
                 raise Exception(response["response"])
            if response:
                return response
        except Exception as e:
            console.print(f"[yellow]⚠ Gemini Primary Brain Failed: {e}[/yellow]")
    
    # 2. Fallback to OpenAI (ChatGPT)
    if os.getenv("OPENAI_API_KEY"):
        console.print("[bold yellow]⚠ Engaging Backup Brain (OpenAI)...[/bold yellow]")
        return send_to_chatgpt(message)

    # 3. Fallback to n8n webhook
    if N8N_WEBHOOK_URL:
        console.print("[bold yellow]⚠ Engaging Agent Network (n8n)...[/bold yellow]")
        return send_to_n8n(message, command_type)
    
    # No AI configured
    console.print("[red]❌ All AI Backends Offline[/red]")
    console.print("[muted]Check GEMINI_API_KEY or OPENAI_API_KEY in .env[/muted]")
    return {
        "response": "CRITICAL FAILURE: All AI systems are offline. Please check your configuration.",
        "audio_url": None
    }


def send_to_gemini(message: str) -> Optional[dict]:
    """
    Send message directly to Gemini API.
    
    Args:
        message: User message
        
    Returns:
        Response dict with 'response' key
    """
    try:
        from google import genai
        from google.genai import types
        
        # Suppress "Both keys set" warning by temporarily unsetting GOOGLE_API_KEY if needed
        # We prioritize GEMINI_API_KEY
        if "GEMINI_API_KEY" in os.environ:
             os.environ.pop("GOOGLE_API_KEY", None)

        # Initialize client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Tool Definitions
        search_email_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="search_emails",
                    description="Search for emails in the user's Gmail inbox. Use this when user asks to find, look for, or check emails.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "query": types.Schema(type="STRING", description="Search query keywords (e.g. 'congratulations', 'receipt')"),
                            "days": types.Schema(type="INTEGER", description="Number of days back to search (default 7)"),
                        },
                        required=["query"]
                    )
                )
            ]
        )

        # System prompt for Athena's personality - EMPOWERED & GROUNDED
        system_instruction = """You are Athena, a Personal Super Agentic System.
You have FULL ACCESS to the local computer and the internet.

**ENVIRONMENT**:
- OS: Windows 11 (assume Windows paths like C:\\Users\\...)
- Shell: PowerShell (Use `dir`, `Get-ChildItem`, `type`, `Get-Content`)
- **Common Issue**: 'Downloads' might be in `OneDrive\\Downloads` or on another drive (D:\\).
- **Registry**: To find real folders, use `Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders'`

**CRITICAL RULES FOR TOOL USE**:
1. **DO NOT ASK FOR PERMISSION IN CHAT.** The system has built-in permission gates.
   - ❌ WRONG: "Should I create the file 'test.txt'?"
   - ✅ CORRECT: [Call Tool: write_file("test.txt", ...)] -> System asks user -> Success/Fail.
2. **BE DIRECT.** If the user asks to create a file, just create it. If they ask to send a Telegram, just send it.
3. **NO META-COMMENTARY.** Do not say "I understand" or "I will follow conventions." Just execute the user's request immediately.
4. **STATEFULNESS & MEMORY.** Remember the output of previous tools. If you just found 5 emails, and the user says "tell me about the first one", YOU KNOW what the first one is. Do not search again unless necessary.
   - **TELEGRAM MEMORY**: If a user references something you sent on Telegram (like "number 5" or "that list"), use `get_telegram_history()` to see what you previously sent. This gives you context about the conversation.

**CAPABILITIES**:
- **Files**: Read/Write files, List directories.
- **Telegram**: Send messages to the user AND retrieve conversation history.
- **Web**: Search real-time info.
- **Multi-Agent**: You can call MULTIPLE tools in a single turn. (e.g., Check News AND Check Finance).

**NOTION CAPABILITIES**:
- Update Journal: `python agents/notion_agent.py journal --content "..." --mood Happy`
- Log Expense: `python agents/notion_agent.py log-expense --amount 50 --category Food --description "Lunch"`
- Analyze Page: `python agents/notion_agent.py analyze --target "Page Title"`
"""

        # Send to Gemini with Spinner
        # Loop for Function Calling (Max 10 turns)
        history = []
        
        global ATHENA_STATE
        ATHENA_STATE = "THINKING"
        
        try:
            from services.supabase_service import get_supabase_service
            db = get_supabase_service()
            db.initialize()
            
            # --- Tool Definitions ---
            
            # 1. Monologue Tool (Agent MUST use this)
            log_thought_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="log_thought",
                    description="Log your internal reasoning before taking action. REQUIRED.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "thought": types.Schema(type="STRING", description="Your reasoning process"),
                            "category": types.Schema(type="STRING", description="Category: planning, analysis, reflection"),
                        },
                        required=["thought"]
                    )
                )
            ])
            
            # 2. File System Tools
            write_file_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="write_file",
                    description="Write code or content to a file. Just do it, don't ask.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "filename": types.Schema(type="STRING", description="Relative path to file"),
                            "content": types.Schema(type="STRING", description="The full content to write"),
                        },
                        required=["filename", "content"]
                    )
                )
            ])
            
            read_file_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="read_file",
                    description="Read the contents of a file.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "filename": types.Schema(type="STRING", description="Path to file"),
                        },
                        required=["filename"]
                    )
                )
            ])

            # 3. Shell Tool
            run_command_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="run_command",
                    description="Execute a shell command (PowerShell). Just do it, don't ask.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "command": types.Schema(type="STRING", description="Command to run"),
                        },
                        required=["command"]
                    )
                )
            ])
            
            # 4. Web Search Tool
            search_web_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="search_web",
                    description="Search the internet for real-time info.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "query": types.Schema(type="STRING", description="Search query"),
                        },
                        required=["query"]
                    )
                )
            ])
            
            # 5. Vision Tool
            see_screen_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="see_screen",
                    description="Look at the user's screen.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "query": types.Schema(type="STRING", description="Specific question (optional)"),
                        },
                    )
                )
            ])
            
            # 6. Telegram Tool (NEW)
            send_telegram_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="send_telegram",
                    description="Send a message to the user via Telegram.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "message": types.Schema(type="STRING", description="The text to send"),
                        },
                        required=["message"]
                    )
                )
            ])

            # 7. Telegram History Tool (NEW)
            get_telegram_history_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="get_telegram_history",
                    description="Retrieve recent Telegram conversation history to see what you previously sent to the user. Use this when the user references something you sent before (like 'number 5' or 'that email').",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "limit": types.Schema(type="INTEGER", description="Number of recent messages to retrieve (default 20)"),
                        },
                    )
                )
            ])

            # 8. Parlay Control Tool (NEW)
            parlay_control_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="parlay_control",
                    description="Control the Parlay Assistant webapp. Use when user says 'turn on parlay', 'start parlay website', 'stop parlay bot', etc.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "action": types.Schema(type="STRING", description="Action to perform: 'start', 'stop', 'status', or 'web'"),
                        },
                        required=["action"]
                    )
                )
            ])

            # 9. Finance Tools (CFO Brain)
            finance_check_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="finance_check_purchase",
                    description="Check if a purchase is financially safe. Also recommends the best credit card to use. Use when user asks 'can I afford X', 'should I buy X', 'is $X safe to spend'.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "amount": types.Schema(type="NUMBER", description="Purchase amount in dollars"),
                            "item": types.Schema(type="STRING", description="What they want to buy"),
                            "merchant": types.Schema(type="STRING", description="Store/merchant name (optional)"),
                            "category": types.Schema(type="STRING", description="Category: Food, Tech, Entertainment, Bills, General"),
                        },
                        required=["amount", "item"]
                    )
                )
            ])

            finance_status_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="finance_status",
                    description="Get financial status dashboard. Shows total liquid cash, upcoming bills, daily budget, and risk level. Use when user asks 'how much money do I have', 'what's my financial status', 'am I broke'.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={},
                    )
                )
            ])

            add_card_deal_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="add_card_deal",
                    description="Add a credit card deal to the registry. Use when user says 'add deal: Chase 5%% off Starbucks' or 'my Chase card has 10%% back at Amazon'.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "card_name": types.Schema(type="STRING", description="Card name, e.g. 'Chase Freedom Flex'"),
                            "merchant": types.Schema(type="STRING", description="Merchant name or '*' for all"),
                            "reward_rate": types.Schema(type="NUMBER", description="Reward rate as decimal, e.g. 0.05 for 5%%"),
                            "category": types.Schema(type="STRING", description="Category if applicable"),
                        },
                        required=["card_name", "merchant", "reward_rate"]
                    )
                )
            ])

            # 13. JARVIS Investigation Tool
            investigate_target_tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="investigate_target",
                    description="Trigger JARVIS for OSINT investigation on a target (email, username, etc). Use when user asks to 'investigate', 'check risk', or 'hack' someone.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "target": types.Schema(type="STRING", description="Target identifier (email, username, IP)"),
                            "redact": types.Schema(type="BOOLEAN", description="Whether to redact sensitive info in output (default false)"),
                        },
                        required=["target"]
                    )
                )
            ])

            # Combine all tools
            all_tools = [search_email_tool, log_thought_tool, write_file_tool, read_file_tool, run_command_tool, search_web_tool, see_screen_tool, send_telegram_tool, get_telegram_history_tool, parlay_control_tool, finance_check_tool, finance_status_tool, add_card_deal_tool, investigate_target_tool]

            # ReAct Loop (Max 10 turns for autonomy)
            chat_history = []
            final_response_text = ""
            
            # --- CONTEXT SUPER-INJECTION ---
            # Give Athena knowledge of the local system state
            current_dir = os.getcwd()
            user_home = os.path.expanduser("~")
            system_context = f"""
SYSTEM CONTEXT:
- Working Dir: {current_dir}
- User Home: {user_home}
- OS: Windows
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Note: 'Downloads' folder is often in {user_home}\\OneDrive\\Downloads or D:\\Downloads.
"""
            chat_history.append(types.Content(role="user", parts=[types.Part(text=system_context)]))
            # -------------------------------
            
            # Initial User Message
            chat_history.append(types.Content(role="user", parts=[types.Part(text=message)]))
            
            # --- Helper: Web Search Implementation ---
            def do_web_search(query: str) -> str:
                # 1. SPECIAL CASE: WEATHER using wttr.in
                if "weather" in query.lower():
                    try:
                        # Extract location logic or just pass query
                        # "weather in minnesota" -> "minnesota"
                        loc = query.lower().replace("weather", "").replace("in ", "").strip()
                        if not loc: loc = ""
                        
                        # wttr.in provides excellent text-based weather
                        # format=3: "Minneapolis: -5C, snow"
                        url = f"https://wttr.in/{loc}?format=3"
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            report = f"Weather Report: {resp.text.strip()}\n(Source: wttr.in)"
                            console.print(Panel(report, title="Observation", border_style="blue"))
                            return report
                    except:
                        pass # Fallback to normal search

                # 2. GENERAL SEARCH (DuckDuckGo Lite)
                try:
                    # Use Lite version - easier to scrape, less blocking
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    payload = {'q': query}
                    resp = requests.post("https://lite.duckduckgo.com/lite/", data=payload, headers=headers, timeout=10)
                    
                    if resp.status_code == 200:
                        # Parse Lite HTML (very simple structure)
                        # Results are in tables
                        import re
                        # Find links
                        results = []
                        # Regex for Lite result links
                        # <a rel="nofollow" href="LINK" class="result-link">TITLE</a>
                        matches = re.findall(r'<a rel="nofollow" href="(.*?)" class="result-link">(.*?)</a>', resp.text)
                        
                        output = f"Search Results for '{query}':\n"
                        count = 0
                        for link, title in matches:
                            if count >= 4: break
                            if "duckduckgo" in link: continue # Skip internal links
                            
                            # Clean snippet lookup (Lite has snippets in standard text after link)
                            # This is basic scraping, might not get perfect snippets, but Title + Link is often enough for Gemini
                            output += f"{count+1}. {title}\n   Source: {link}\n\n"
                            count += 1
                            
                        if count == 0:
                             return "Search failed: No results found (DuckDuckGo Lite)."
                        
                        # Debug Print for User
                        console.print(Panel(output.strip(), title="Observation: Web Data", border_style="cyan"))
                        return output
                    return f"Search failed: Status {resp.status_code}"
                except Exception as e:
                    return f"Search error: {e}"

            # --- Helper: Vision Implementation (Sub-Agent) ---
            def do_see_screen(query: str = "Describe this screen.") -> str:
                try:
                    img_path = capture_screen() # Reuse existing function
                    if not img_path:
                        return "Failed to capture screen."
                    
                    # Call Gemini with Image for Analysis
                    from PIL import Image
                    vision_client = genai.Client(api_key=GEMINI_API_KEY)
                    image = Image.open(img_path)
                    
                    response = vision_client.models.generate_content(
                        model="gemini-2.0-flash-exp",
                        contents=[query, image]
                    )
                    return f"[Vision Analysis]: {response.text}"
                except Exception as e:
                    # Silent fail for monologue if DB not ready
                    # console.print(f"[dim red]Monologue Error: {e}[/dim red]")
                    return "Logged."

            # --- Helper: Permission Gate ---
            def ask_permission(action_type: str, details: str, preview: str = "") -> bool:
                global ATHENA_ALLOW_ALL
                
                # SAFETY: Prevent background threads from blocking IO
                import threading
                if threading.current_thread() is not threading.main_thread():
                     console.print(f"[yellow]⚠ Background task attempted action ({action_type}). Auto-Allowing (Autonomous Mode).[/yellow]")
                     return True

                if ATHENA_ALLOW_ALL:
                    console.print(f"[bold green]✓ Auto-Allowed ({action_type})[/bold green]")
                    return True

                console.print(Panel(
                     f"[bold yellow]⚠ Permission Request: {action_type}[/bold yellow]\n\n{details}",
                     border_style="yellow"
                ))
                
                if preview:
                    from rich.syntax import Syntax
                    # Try to detect language
                    lexer = "bash"
                    if action_type == "WRITE FILE":
                        # Infer lexer from filename in details, or from content if it looks like code
                        filename_match = re.search(r"Target: (.*?)(?=\n|$)", details)
                        if filename_match:
                            filename = filename_match.group(1)
                            if filename.endswith(".py"): lexer = "python"
                            elif filename.endswith(".js"): lexer = "javascript"
                            elif filename.endswith(".json"): lexer = "json"
                            elif filename.endswith(".md"): lexer = "markdown"
                            elif filename.endswith(".sh") or filename.endswith(".ps1"): lexer = "bash" # PowerShell is often highlighted as bash
                        elif "def " in preview or "import " in preview: lexer = "python" # Basic content check
                        elif "function " in preview or "const " in preview: lexer = "javascript"
                        elif "{" in preview and "}" in preview and ":" in preview: lexer = "json"
                    
                    # Truncate large previews
                    display_preview = preview
                    if len(preview) > 500:
                        display_preview = preview[:500] + "\n... (truncated)"

                    permissions_panel = Panel(
                        display_preview if action_type == "RUN SHELL" else Syntax(display_preview, lexer, theme="monokai", line_numbers=True),
                        title="Preview",
                        border_style="dim"
                    )
                    console.print(permissions_panel)

                # Notify Telegram (Poll)
                try:
                    from services.telegram_service import get_telegram_service
                    ts = get_telegram_service()
                    if ts.is_configured:
                        import asyncio
                        # Fire and forget (sync wrapper needed or just log)
                        # Since we can't easily await here in this sync block without event loop issues if one is running...
                        # We'll skip complex async. 
                        pass 
                except:
                    pass

                # Prompt Loop for valid input
                while True:
                    choice = console.input("[bold yellow]Allow this action? (y/n/all/esc): [/bold yellow]").strip().lower()
                    if choice in ['y', 'yes']:
                        return True
                    elif choice in ['n', 'no']:
                        return False
                    elif choice in ['a', 'all']:
                        ATHENA_ALLOW_ALL = True
                        console.print("[bold red]⚠ SECURITY: ALL FUTURE ACTIONS WILL BE ALLOWED AUTOMATICALLY THIS SESSION.[/bold red]")
                        return True
                    elif choice in ['esc', 'cancel', 'q']:
                        console.print("[bold red]⛔ Action Cancelled (Escape). Stopping Agent.[/bold red]")
                        return False # Or raise StopIteration? False usually just skips this tool, but the user implies stopping the whole flow. 
                        # For tool execution loops, returning False denies the tool, which might stop the agent or make it retry.
                        # Assuming False is safer.
                    else:
                        console.print("[red]Invalid input. Please type 'y', 'n', 'all', or 'esc'.[/red]")

            current_turn = 0
            MAX_TURNS = 10
            
            while current_turn < MAX_TURNS:
                with console.status(f"[bold #E0B0FF]Thinking (Turn {current_turn+1})...[/bold #E0B0FF]", spinner="dots", spinner_style="#BF40BF"):
                    # Placeholder for Agent Loop
                    break
                    
                    if not user_input.strip():
                        continue

                    # A. Handle Commands (Priority 1)
                    if user_input.startswith("/"):
                        parts = user_input.split()
                        cmd = parts[0].lower()
                        args = " ".join(parts[1:])
                        
                        if cmd == "/email": cmd_email(args)
                        elif cmd == "/run": cmd_run(args)
                        elif cmd == "/ls": cmd_ls(args)
                        elif cmd == "/cat": cmd_cat(args)
                        elif cmd == "/search": cmd_search(args)
                        elif cmd == "/tldr": cmd_tldr(args)
                        elif cmd == "/ascii": cmd_ascii(args)
                        elif cmd == "/pattern": cmd_pattern(args)
                        elif cmd == "/clitools": cmd_clitools()
                        elif cmd == "/clear": cmd_clear()
                        elif cmd == "/exit": 
                            console.print("[bold red]Shutting down...[/bold red]")
                            sys.exit(0)
                        else:
                            execute_spoke_agent(cmd[1:], args)
                        continue

                    # B. Semantic Router (Athena 2.0)
                    if router and context_stack:
                        with console.status("[bold #E0B0FF]🧠 Thinking...[/bold #E0B0FF]", spinner="dots"):
                            # 1. Resolve References (#5, 'that one')
                            active_ref = context_stack.resolve_reference("terminal", user_input)
                            
                            # 2. Add to Context History
                            context_stack.push_entity("terminal", "USER_MSG", user_input)
                            
                            # 3. Route
                            # We need a history list for the router. For now, mock it or use stack.
                            # ContextStack entities are structure, Router wants dialogue history.
                            # We'll use a simple transient history for this session.
                            if 'dialogue_history' not in locals(): dialogue_history = []
                            dialogue_history.append({"role": "user", "content": user_input})
                            
                            route_result = router.route(
                                user_input, 
                                dialogue_history, 
                                active_task=None, # Todo: Track active task in CLI
                                active_reference=active_ref
                            )
                            
                            intent = route_result.get("intent")
                            slots = route_result.get("slots", {})
                            reasoning = route_result.get("reasoning", "")
                            
                            # console.print(f"[dim]Intent: {intent} | Ref: {active_ref is not None}[/dim]")

                            # 4. Execute Intent
                            
                            if intent == "email_search":
                                # Auto-execute email search
                                q = slots.get("query", "")
                                days = slots.get("days_back", 7)
                                # If reference found (e.g. "from that sender"), inject into query?
                                if active_ref and "from" in active_ref:
                                    q += f" from:{active_ref['from']}"
                                    
                                console.print(f"[cyan]🔍 Searching emails for '{q}'...[/cyan]")
                                from services.google_service import get_google_service
                                svc = get_google_service()
                                
                                # Use extended search (with body)
                                if hasattr(svc, "search_emails"):
                                    res = svc.search_emails(q, days=days)
                                else:
                                    res = svc.search_transaction_emails(days=days) # Fallback
                                    
                                if res and not (isinstance(res[0], dict) and "error" in res[0]):
                                    console.print(f"\n[bold cyan]📧 Found {len(res)} emails[/bold cyan]\n")
                                    # Push Result Set
                                    context_stack.push_result_set("terminal", "emails", res)
                                    
                                    for i, item in enumerate(res, 1):
                                        snippet = item.get("snippet", "")[:100]
                                        console.print(f"[bold]{i}.[/bold] {item.get('subject')} [dim]- {item.get('date')}[/dim]")
                                        console.print(f"   [dim]{snippet}...[/dim]")
                                else:
                                    console.print("[yellow]No emails found.[/yellow]")
                                    
                                response_text = f"Here are the emails matching '{q}'."

                            elif intent == "schedule_event":
                                console.print(f"[bold green]📅 Scheduling Event: {slots.get('title', 'Unknown')}[/bold green]")
                                # TODO: Call deep_mind or calendar service
                                response_text = f"I've noted that event request: {slots}"

                            elif intent == "research_topic":
                                topic = slots.get("query")
                                # Check if topic is a reference ("it", "#5")
                                if not topic and active_ref:
                                    topic = active_ref.get("subject") or active_ref.get("merchant_raw")
                                
                                console.print(f"[bold blue]🌐 Researching: {topic}[/bold blue]")
                                # Placeholder for DeepMind research
                                response_text = f"Researching '{topic}'. (Enable DeepMind full mode for real report)"

                            else: # general_chat or capture_note
                                # Simple Chat Response (could use Gemini to generate reply, but Router output is JSON)
                                # Let's ask Gemini for a text response now.
                                from google import genai
                                client = genai.Client(api_key=GEMINI_API_KEY)
                                
                                # Inject context
                                ref_context = ""
                                if active_ref:
                                    ref_context = f"User refers to: {json.dumps(active_ref)[:500]}"
                                    
                                chat_resp = client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=f"User said: {user_input}\nContext: {ref_context}\nReasoning: {reasoning}\nReply as Athena (helpful, concise).",
                                )
                                response_text = chat_resp.text
                                console.print(Markdown(response_text))
                                
                            # Add bot reply to history
                            dialogue_history.append({"role": "assistant", "content": response_text})
                            continue

                    # C. Legacy Fallback (Keyword Matching)
                    response = client.models.generate_content(
                        model="gemini-3-pro-preview",
                        contents=chat_history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                            tools=all_tools,
                            max_output_tokens=4096,
                        )
                    )
                
                # Check for Function Call
                if response.function_calls:
                    # Append model's thought/call to history
                    chat_history.append(response.candidates[0].content)
                    
                    for call in response.function_calls:
                        fn_name = call.name
                        fn_args = call.args
                        result_data = ""
                        
                        # --- ROUTER ---
                        
                        # A. Log Thought (Silent, Automatic)
                        if fn_name == "log_thought":
                            thought = fn_args.get("thought", "")
                            cat = fn_args.get("category", "analysis")
                            console.print(f"[dim]🧠 Thought: {thought}[/dim]")
                            
                        elif fn_name == "investigate_target":
                            target = fn_args.get("target")
                            redact = fn_args.get("redact", False)
                            console.print(f"[bold red]🕵️ JARVIS ACTIVATED: Investigating {target}...[/bold red]")
                            
                            try:
                                config = {"output_dir": "output/jarvis_inv", "redaction": redact, "mode": "CTF_LAB"}
                                orchestrator = JarvisOrchestrator(config)
                                report = orchestrator.run_investigation(target)
                                
                                # Summarize for LLM
                                result_data = json.dumps({
                                    "status": "success", 
                                    "target": target,
                                    "risk_score": report.get("risk", {}).get("score", 0),
                                    "findings_count": len(report.get("triage", {}).get("confirmed", [])),
                                    "top_findings": report.get("triage", {}).get("confirmed", [])[:5],
                                    "remediation": report.get("remediation", [])
                                }, default=str)
                            except Exception as e:
                                result_data = f"JARVIS Execution Failed: {e}"
                                console.print(f"[red]❌ Error: {e}[/red]")
                            
                            # Log to legacy supabase_service
                            try:
                                db.log_thought(thought, cat)
                            except Exception:
                                pass
                                
                            # Also log to new memory_core for analysis
                            try:
                                from services.memory_core import get_memory
                                memory = get_memory()
                                memory.log_thought(thought, category=cat)
                            except Exception:
                                pass
                                
                            result_data = "Thought logged."

                        # B. Write File (GATED)
                        elif fn_name == "write_file":
                            filename = fn_args.get("filename", "")
                            content = fn_args.get("content", "")
                            if ask_permission("WRITE FILE", f"Target: {filename}", content):
                                try:
                                    path = Path(filename)
                                    path.parent.mkdir(parents=True, exist_ok=True)
                                    with open(path, "w", encoding="utf-8") as f:
                                        f.write(content)
                                    result_data = f"File {filename} written successfully."
                                    console.print(f"[#E0B0FF]✓ {filename} saved.[/#E0B0FF]")
                                except Exception as e:
                                    result_data = f"Error writing file: {e}"
                            else:
                                result_data = "User DENIED permission."
                                console.print("[red]✗ Action Denied.[/red]")
                        
                        # C. Read File (Automatic/Silent)
                        elif fn_name == "read_file":
                            filename = fn_args.get("filename", "")
                            try:
                                if os.path.exists(filename):
                                    with open(filename, "r", encoding="utf-8") as f:
                                        result_data = f.read()
                                        if len(result_data) > 5000: result_data = result_data[:5000] + "...(truncated)"
                                    console.print(f"[dim]📄 Read {filename}[/dim]")
                                else:
                                    result_data = "File not found."
                            except Exception as e:
                                result_data = f"Error reading file: {e}"

                        # D. Run Command (GATED)
                        elif fn_name == "run_command":
                            cmd = fn_args.get("command", "")
                            if ask_permission("RUN SHELL", f"Command: {cmd}", cmd):
                                try:
                                    # Use subprocess
                                    cmd_res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
                                    result_data = f"Exit Code: {cmd_res.returncode}\nSTDOUT: {cmd_res.stdout}\nSTDERR: {cmd_res.stderr}"
                                    console.print(f"[dim]{result_data.strip()}[/dim]")
                                except Exception as e:
                                    result_data = f"Execution Error: {e}"
                            else:
                                result_data = "User DENIED permission."
                                console.print("[red]✗ Action Denied.[/red]")
                                
                        # E. Email Search (Allowed)
                        elif fn_name == "search_emails":
                            # Existing logic
                            from services.google_service import get_google_service
                            svc = get_google_service()
                            days = int(fn_args.get("days", 7))
                            query = fn_args.get("query", "")
                            console.print(f"[#E0B0FF]📧 Scanning emails for '{query}'...[/#E0B0FF]")
                            data = svc.search_emails(query=query, days=days)
                            result_data = str(data)

                        # F. Web Search (Automatic)
                        elif fn_name == "search_web":
                            q = fn_args.get("query", "")
                            console.print(f"[dim]🌐 Searching web: {q}...[/dim]")
                            result_data = do_web_search(q)

                        # G. Vision (Automatic)
                        elif fn_name == "see_screen":
                            q = fn_args.get("query", "Describe this screen")
                            console.print(f"[dim]👁️ Looking at screen...[/dim]")
                            result_data = do_see_screen(q)
                            
                        # H. Send Telegram (Automatic)
                        elif fn_name == "send_telegram":
                            msg_text = fn_args.get("message", "")
                            console.print(f"[#E0B0FF]✈ Sending Telegram: {msg_text}[/#E0B0FF]")
                            try:
                                # Just use the CLI tool we installed, or the service directly
                                from services.telegram_service import get_telegram_service
                                import asyncio
                                # Create a temporary event loop just for this sync call
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                svc = get_telegram_service()
                                loop.run_until_complete(svc.send_text(msg_text))
                                loop.close()
                                result_data = "Message sent successfully."
                            except Exception as e:
                                result_data = f"Failed to send Telegram: {e}"

                        # I. Get Telegram History (Automatic)
                        elif fn_name == "get_telegram_history":
                            limit = int(fn_args.get("limit", 20))
                            console.print(f"[dim]📜 Retrieving Telegram history (last {limit} messages)...[/dim]")
                            try:
                                from services.telegram_service import get_telegram_service
                                svc = get_telegram_service()
                                messages = svc.get_recent_messages(limit=limit)

                                if not messages:
                                    result_data = "No conversation history found."
                                else:
                                    # Format messages for Athena to understand
                                    formatted_msgs = []
                                    for i, msg in enumerate(messages, 1):
                                        direction = msg.get("direction", "unknown")
                                        text = msg.get("text", "")
                                        timestamp = msg.get("timestamp", "")
                                        msg_type = msg.get("type", "text")

                                        if direction == "sent":
                                            formatted_msgs.append(f"{i}. [ATHENA SENT]: {text}")
                                        else:
                                            formatted_msgs.append(f"{i}. [USER]: {text}")

                                    result_data = "Recent Telegram conversation:\n" + "\n".join(formatted_msgs)
                                    console.print(f"[dim]Found {len(messages)} messages in history[/dim]")
                            except Exception as e:
                                result_data = f"Failed to retrieve Telegram history: {e}"

                        # J. Finance Check Purchase (CFO Brain)
                        elif fn_name == "finance_check_purchase":
                            amount = float(fn_args.get("amount", 0))
                            item = fn_args.get("item", "Unknown")
                            merchant = fn_args.get("merchant", item)
                            category = fn_args.get("category", "General")
                            console.print(f"[#E0B0FF]💰 Checking purchase: ${amount} for {item}...[/#E0B0FF]")
                            try:
                                from agents.financial_advisor import get_bank_ecosystem, get_card_optimizer
                                ecosystem = get_bank_ecosystem()
                                cards = get_card_optimizer()
                                
                                # Safe-to-Spend check
                                sts = ecosystem.safe_to_spend(amount)
                                
                                # Card optimization
                                card_rec = cards.get_best_card(merchant, category, amount)
                                
                                if sts.approved:
                                    result_data = f"✅ APPROVED: {sts.message}\n💳 {card_rec.message}\nRisk Level: {sts.risk_level}"
                                else:
                                    result_data = f"❌ NOT RECOMMENDED: {sts.message}\nRisk Level: {sts.risk_level}"
                                
                                console.print(f"[dim]{result_data}[/dim]")
                            except Exception as e:
                                result_data = f"Finance check error: {e}"

                        # K. Finance Status Dashboard
                        elif fn_name == "finance_status":
                            console.print(f"[#E0B0FF]📊 Getting financial status...[/#E0B0FF]")
                            try:
                                from agents.financial_advisor import get_bank_ecosystem
                                ecosystem = get_bank_ecosystem()
                                
                                liquid = ecosystem.get_total_liquid()
                                bills = ecosystem.get_upcoming_bills(7)
                                sts = ecosystem.safe_to_spend(100)
                                velocity = ecosystem.get_velocity("cap1_checking", 14)
                                
                                result_data = (
                                    f"💵 Total Liquid: ${liquid:.2f}\n"
                                    f"📋 Upcoming Bills (7d): ${bills:.2f}\n"
                                    f"✅ Available to Spend: ${sts.available:.2f}\n"
                                    f"🔥 Daily Budget: ${velocity:.2f}/day\n"
                                    f"⚠️ Risk Level: {sts.risk_level}"
                                )
                                console.print(f"[dim]{result_data}[/dim]")
                            except Exception as e:
                                result_data = f"Finance status error: {e}"

                        # L. Add Card Deal
                        elif fn_name == "add_card_deal":
                            card_name = fn_args.get("card_name", "")
                            merchant = fn_args.get("merchant", "*")
                            rate = float(fn_args.get("reward_rate", 0))
                            category = fn_args.get("category", None)
                            console.print(f"[#E0B0FF]💳 Adding deal: {card_name} -> {merchant} ({rate*100:.0f}%)...[/#E0B0FF]")
                            try:
                                from agents.financial_advisor import get_card_optimizer
                                cards = get_card_optimizer()
                                deal = cards.add_deal(card_name, merchant, rate, category=category)
                                result_data = f"Deal added: {deal.card_name} gives {deal.reward_rate*100:.0f}% back at {deal.merchant_pattern}"
                                console.print(f"[dim]✓ {result_data}[/dim]")
                            except Exception as e:
                                result_data = f"Failed to add deal: {e}"

                        # Handle Tool Return
                        # Create FunctionResponse part
                        func_resp_part = types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"result": result_data}
                            )
                        )
                        
                        # Add to history
                        chat_history.append(types.Content(role="user", parts=[func_resp_part]))
                        
                    current_turn += 1
                    
                else:
                    # Text response - We are done
                    final_response_text = response.text
                    break

            # Return final text
            ATHENA_STATE = "READY"
            
            # Log conversation to memory (v3.0)
            try:
                from services.memory_core import get_memory
                memory = get_memory()
                # This now handles Supabase + Cloud Archival automatically
                memory.log_interaction(
                    user_input=user_input,
                    athena_response=final_response_text[:500] if final_response_text else "Task completed",
                    source="cli"
                )
                
                # Trigger Background Extraction (Fire & Forget)
                import threading
                def _bg_extract():
                    try:
                        # 1. Update preferences from trends
                        memory.update_from_trends()
                        # 2. (Future) Extract specific tasks/entities here
                    except Exception as e:
                        pass
                
                t = threading.Thread(target=_bg_extract, daemon=True)
                t.start()
                
            except Exception:
                pass
            
            return {
                "response": final_response_text if final_response_text else "Task completed silently.",
                "audio_url": None
            }

        except Exception as e:
            console.print(f"[red]❌ Gemini API error: {e}[/red]")
            return {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "audio_url": None
            }

    except Exception as e:
        console.print(f"[red]❌ Error initializing Gemini: {e}[/red]")
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "audio_url": None
        }


def send_to_n8n(message: str, command_type: str = "chat") -> Optional[dict]:
    """
    Send message to n8n webhook (for complex agent workflows).
    
    Args:
        message: Message to send
        command_type: Type of command (chat, vision, action)
        
    Returns:
        Response dict or None
    """
    try:
        loading_animation("Connecting to Agent Network", 0.5)
        
        payload = {
            "message": message,
            "command_type": command_type,
            "timestamp": datetime.now().isoformat(),
            "source": "athena_cli"
        }
        
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.Timeout:
        console.print("[red]❌ Request timed out. n8n may be busy.[/red]")
        return None
    except requests.exceptions.ConnectionError:
        console.print("[red]❌ Cannot connect to n8n. Check your network.[/red]")
        return None
    except Exception as e:
        console.print(f"[red]❌ n8n communication error: {e}[/red]")
        return None

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def cmd_help():
    """Display available commands"""
    help_text = """
[bold cyan]╔══════════════════════════════════════════════════════════════╗
║                    ATHENA COMMAND REFERENCE                   ║
╚══════════════════════════════════════════════════════════════╝[/bold cyan]

[bold #4285F4]CORE COMMANDS[/bold #4285F4]
  [cyan]/help[/cyan]              Show this help message
  [cyan]/status[/cyan]            Show system status & component health (Supabase, API, etc.)
  [cyan]/clear[/cyan]             Clear the terminal screen
  [cyan]/exit[/cyan]              Exit Athena

[bold #4285F4]TOOLS & UTILITIES[/bold #4285F4]
  [cyan]/look[/cyan]              Capture screen for vision analysis (Athena calls this herself)
  [cyan]/launch <app>[/cyan]      Launch an application (e.g., /launch chrome)
  [cyan]/apps[/cyan]              List available applications to launch
  [cyan]/email <days>[/cyan]      Scan Gmail for transaction emails (default 7 days)
  [cyan]/ascii <text>[/cyan]      Generate ASCII art (Use '/ascii rain' for Matrix effect)
  [cyan]/clitools[/cyan]          Cheat sheet for installed power tools (bat, eza, fzf)
  [cyan]/tldr <cmd>[/cyan]        Show cheat sheet for a shell command

[bold #4285F4]FILE SYSTEM[/bold #4285F4]
  [cyan]/ls [path][/cyan]         List files (uses 'eza' if available)
  [cyan]/cat <file>[/cyan]        Read file (uses 'bat' if available)
  [cyan]/search <q>[/cyan]        Search files (uses 'rg')
  [cyan]/run <cmd>[/cyan]         Execute raw shell command

[bold #4285F4]AGENTS[/bold #4285F4]
  [cyan]/parlay[/cyan]            Parlay Assistant (Analysis & Advice)
      [dim]Usage: /parlay check lebron points 25.5[/dim]
  [cyan]/medic[/cyan]             System Health Check (triggers Medic Agent)
  [cyan]/news[/cyan]              Daily Briefing (triggers News Agent)

[bold #4285F4]NATURAL LANGUAGE[/bold #4285F4]
  Type naturally! Athena routes requests to specific agents or the Cloud Brain.
  [dim]"Log $50 for gas" -> Finance Agent
  "Do the rain effect" -> Matrix Animation
  "Check system status" -> Medic Agent[/dim]
"""
    console.print(help_text)

    # Dynamic Agent Listing
    try:
        agents_dir = BASE_DIR / "agents"
        if agents_dir.exists():
            agents = []
            for f in agents_dir.glob("*.py"):
                if f.name.startswith("__") or f.name == "agent_factory.py":
                    continue
                name = f.stem
                if name.endswith("_agent"):
                    name = name.replace("_agent", "")
                agents.append(f"/{name}")
            
            if agents:
                console.print("[bold #4285F4]DETECTED AGENTS[/bold #4285F4]")
                
                # Format into columns
                cols = 4
                agents.sort()
                for i in range(0, len(agents), cols):
                    row = agents[i:i+cols]
                    console.print("  " + "  ".join(f"[cyan]{a:<20}[/cyan]" for a in row))
                console.print()
    except Exception as e:
        console.print(f"[dim]Could not list agents: {e}[/dim]")

def cmd_look():
    """Capture screen and optionally send to cloud for analysis"""
    console.print("[cyan]👁 Capturing screen...[/cyan]")
    
    filepath = capture_screen()
    
    if filepath:
        console.print(f"[green]✓ Screenshot saved: {filepath.name}[/green]")
        
        # Ask if user wants to analyze
        console.print("[cyan]Sending to Cloud Brain for analysis...[/cyan]")
        
        result = send_vision_to_cloud(filepath)
        
        if result:
            console.print()
            stream_response(result)
        else:
            console.print("[yellow]Screenshot saved locally. Cloud analysis unavailable.[/yellow]")

def cmd_launch(app_name: str):
    """Launch an application"""
    if not app_name:
        console.print("[yellow]Usage: /launch <app_name>[/yellow]")
        console.print("[muted]Example: /launch chrome[/muted]")
        return
    
    console.print(f"[cyan]🚀 Launching {app_name}...[/cyan]")
    result = launcher.launch_app(app_name)
    
    if result["success"]:
        console.print(f"[green]{result['message']}[/green]")
    else:
        console.print(f"[red]{result['message']}[/red]")

def cmd_apps():
    """List available applications"""
    apps = launcher.list_available_apps()
    console.print("[bold cyan]Available Applications:[/bold cyan]")
    
    # Print in columns
    cols = 4
    for i in range(0, len(apps), cols):
        row = apps[i:i+cols]
        formatted = "  ".join(f"[cyan]{app:<15}[/cyan]" for app in row)
        console.print(f"  {formatted}")

# =============================================================================
# PARLAY BOT CONTROL
# =============================================================================

PARLAY_PROJECT_PATH = Path.home() / "OneDrive" / "Parlay bot 2.0" / "mobile_app"
PARLAY_PROCESS = None  # Track running process

def cmd_parlay(action: str = ""):
    """
    Control the Parlay Assistant webapp.
    
    Usage:
        /parlay start - Start the Parlay webapp (Expo web)
        /parlay stop  - Stop the running server
        /parlay status - Check if running
    """
    global PARLAY_PROCESS
    
    action = action.lower().strip() if action else ""
    
    if not action or action == "help":
        console.print(Panel("""[bold cyan]Parlay Bot Controls[/bold cyan]

[cyan]/parlay start[/cyan]   Start the Parlay webapp
[cyan]/parlay stop[/cyan]    Stop the running server  
[cyan]/parlay status[/cyan]  Check if running
[cyan]/parlay web[/cyan]     Open Parlay in browser (after starting)
""", border_style="cyan"))
        return
    
    if action == "start":
        if PARLAY_PROCESS and PARLAY_PROCESS.poll() is None:
            console.print("[yellow]⚠ Parlay is already running![/yellow]")
            console.print("[muted]Use /parlay stop to stop it first.[/muted]")
            return
        
        if not PARLAY_PROJECT_PATH.exists():
            console.print(f"[red]❌ Parlay project not found at: {PARLAY_PROJECT_PATH}[/red]")
            return
        
        console.print("[cyan]🚀 Starting Parlay Assistant...[/cyan]")
        console.print(f"[dim]Project: {PARLAY_PROJECT_PATH}[/dim]")
        
        try:
            import subprocess
            # Start Expo in web mode
            PARLAY_PROCESS = subprocess.Popen(
                ["npm", "run", "web"],
                cwd=str(PARLAY_PROJECT_PATH),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            console.print("[green]✅ Parlay webapp starting...[/green]")
            console.print("[muted]→ Open http://localhost:8081 in your browser[/muted]")
            console.print("[muted]→ Use /parlay stop to shut down[/muted]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to start Parlay: {e}[/red]")
    
    elif action == "stop":
        if PARLAY_PROCESS and PARLAY_PROCESS.poll() is None:
            console.print("[yellow]🛑 Stopping Parlay...[/yellow]")
            PARLAY_PROCESS.terminate()
            try:
                PARLAY_PROCESS.wait(timeout=5)
            except:
                PARLAY_PROCESS.kill()
            PARLAY_PROCESS = None
            console.print("[green]✅ Parlay stopped.[/green]")
        else:
            console.print("[yellow]Parlay is not running.[/yellow]")
    
    elif action == "status":
        if PARLAY_PROCESS and PARLAY_PROCESS.poll() is None:
            console.print("[green]✅ Parlay is RUNNING[/green]")
            console.print("[muted]→ http://localhost:8081[/muted]")
        else:
            console.print("[yellow]⚪ Parlay is STOPPED[/yellow]")
    
    elif action == "web":
        import webbrowser
        webbrowser.open("http://localhost:8081")
        console.print("[cyan]🌐 Opening Parlay in browser...[/cyan]")
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[muted]Try: /parlay start, /parlay stop, /parlay status[/muted]")

def cmd_status():
    """Show system status"""
    from rich.table import Table
    
    # Create status table
    table = Table(title="Athena System Status", border_style="cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Details", style="white")
    table.add_column("Status", style="green")
    
    # System logic
    cloud_status = "[green]Connected[/green]" if N8N_WEBHOOK_URL else "[red]Offline[/red]"
    api_status = "[green]Ready[/green]" if GEMINI_API_KEY else "[red]Missing Key[/red]"
    audio_status = "[green]Ready[/green]" if init_audio() else "[red]Silent[/red]"
    
    table.add_row("System", "Athena Core 2.0", "[green]Online[/green]")
    table.add_row("Brain", "Gemini 2.0 Flash", api_status)
    table.add_row("Cloud", "n8n Webhook", cloud_status)
    table.add_row("Audio", "Winsound", audio_status)
    table.add_row("Vision", f"{len(list(VISION_CACHE_DIR.glob('*.png')))} snapshots", "[green]Enabled[/green]")
    
    console.print(Panel(table, border_style="cyan", expand=False))


def cmd_email(args: str = ""):
    """Scan Gmail for transaction-related emails"""
    try:
        from services.google_service import get_google_service
    except ImportError:
        console.print("[red]❌ Google Service not available[/red]")
        return
    
    console.print("[cyan]📧 Scanning Gmail for transactions...[/cyan]")
    
    # Parse days argument
    days = 7
    if args:
        try:
            days = int(args)
        except ValueError:
            pass
    
    google = get_google_service()
    
    # Check for credentials
    if not google.is_authenticated():
        console.print("[yellow]⚠ Google not authenticated[/yellow]")
        console.print("[muted]To set up Gmail access:[/muted]")
        console.print("1. Copy credentials.json from Project_Cortex to Athena_Project")
        console.print("2. Run /email again - a browser will open for Google login")
        return
    
    # Search for transactions
    transactions = google.search_transaction_emails(days=days, max_results=15)
    
    if not transactions:
        console.print(f"[green]✓ No transaction emails found in the last {days} days[/green]")
        return
    
    if isinstance(transactions[0], dict) and "error" in transactions[0]:
        console.print(f"[red]❌ Error: {transactions[0]['error']}[/red]")
        return
    
    # Display results
    console.print(f"\n[bold cyan]📧 Found {len(transactions)} transaction emails (last {days} days)[/bold cyan]\n")
    
    # NEW: Push to Context Stack for reference resolution
    if context_stack:
        context_stack.push_result_set(
            chat_id="terminal", # Special ID for CLI
            result_type="emails",
            items=transactions, # Contains 'id', 'subject' etc.
            surface="terminal"
        )

    for i, tx in enumerate(transactions, 1):
        amount_str = f" [bold green]{tx.get('amount')}[/bold green]" if tx.get('amount') else ""
        console.print(f"[bold]{i}.[/bold] {tx.get('subject', 'No Subject')[:60]}{amount_str}")
        console.print(f"   [muted]From: {tx.get('from', 'Unknown')[:40]}[/muted]")
        console.print()


def cmd_run(command: str):
    """Execute a shell command"""
    if not command:
        console.print("[yellow]Usage: /run <command>[/yellow]")
        console.print("[muted]Example: /run dir[/muted]")
        console.print("[muted]Example: /run Copy-Item source.txt dest.txt[/muted]")
        return
    
    console.print(Panel(f"[cyan]💻 Executing: [bold]{command}[/bold][/cyan]", border_style="cyan"))
    
    try:
        import subprocess
        
        # Run the command in PowerShell
        with console.status(f"[bold cyan]Executing: {command}...[/bold cyan]", spinner="dots"):
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=60
            )
        
        output_text = ""
        if result.stdout:
            output_text += f"[green]Output:[/green]\n{result.stdout}\n"
        
        if result.stderr:
            output_text += f"[yellow]Warnings/Errors:[/yellow]\n{result.stderr}\n"
            
        if not output_text:
            output_text = "[dim]No output returned.[/dim]"
            
        title = f"✓ Shell: {command}" if result.returncode == 0 else f"⚠ Shell (Exit {result.returncode}): {command}"
        border = "green" if result.returncode == 0 else "yellow"
        
        console.print(Panel(output_text.strip(), title=title, border_style=border, expand=False))

    except subprocess.TimeoutExpired:
        console.print(Panel("[red]❌ Command timed out after 60 seconds[/red]", title="Execution Error", border_style="red"))
    except Exception as e:
        console.print(f"[red]❌ Execution error: {e}[/red]")


def cmd_ls(args: str = ""):
    """List directory contents using eza/ls"""
    import shutil
    import subprocess
    
    path = args if args else "."
    
    # Check for eza
    if shutil.which("eza"):
        cmd = f"eza --icons --classify --group-directories-first --grid {path}"
        console.print(Panel(f"[#E0B0FF]📂 Listing: {path}[/#E0B0FF]", border_style="#800080"))
        subprocess.run(["powershell", "-Command", cmd])
    else:
        # Fallback to standard dir
        cmd_run(f"dir {path}")


def cmd_cat(args: str = ""):
    """View file contents using bat/type"""
    import shutil
    import subprocess
    
    if not args:
        console.print("[yellow]Usage: /cat <filename>[/yellow]")
        return
        
    if shutil.which("bat"):
        subprocess.run(["bat", "--style=plain", "--paging=never", args])
    else:
        cmd_run(f"Get-Content {args}")


def cmd_search(args: str = ""):
    """Search using ripgrep"""
    import shutil
    import subprocess
    
    if not args:
        console.print("[yellow]Usage: /search <pattern> [path][/yellow]")
        return
        
    if shutil.which("rg"):
        console.print(f"[#E0B0FF]🔍 Searching for: {args}[/#E0B0FF]")
        subprocess.run(["rg", "--pretty", "--smart-case", args])
    else:
        cmd_run(f"Select-String -Pattern '{args}' -Path *")

def cmd_tldr(args: str = ""):
    """Show cheatsheet using tealdeer"""
    import shutil
    import subprocess
    
    if not args:
        console.print("[yellow]Usage: /tldr <command>[/yellow]")
        return
        
    if shutil.which("tldr"):
        subprocess.run(["tldr", args])
    else:
        console.print("[red]❌ 'tldr' not found. Run setup_tools.ps1 to install it.[/red]")


# =============================================================================
# ASCII ART GENERATOR
# =============================================================================

# ASCII font - block style letters
ASCII_FONT = {
    'A': [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝"
    ],
    'B': [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔══██╗",
        "██████╔╝",
        "╚═════╝ "
    ],
    'C': [
        " ██████╗",
        "██╔════╝",
        "██║     ",
        "██║     ",
        "╚██████╗",
        " ╚═════╝"
    ],
    'D': [
        "██████╗ ",
        "██╔══██╗",
        "██║  ██║",
        "██║  ██║",
        "██████╔╝",
        "╚═════╝ "
    ],
    'E': [
        "███████╗",
        "██╔════╝",
        "█████╗  ",
        "██╔══╝  ",
        "███████╗",
        "╚══════╝"
    ],
    'F': [
        "███████╗",
        "██╔════╝",
        "█████╗  ",
        "██╔══╝  ",
        "██║     ",
        "╚═╝     "
    ],
    'G': [
        " ██████╗ ",
        "██╔════╝ ",
        "██║  ███╗",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ "
    ],
    'H': [
        "██╗  ██╗",
        "██║  ██║",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝"
    ],
    'I': [
        "██╗",
        "██║",
        "██║",
        "██║",
        "██║",
        "╚═╝"
    ],
    'J': [
        "     ██╗",
        "     ██║",
        "     ██║",
        "██   ██║",
        "╚█████╔╝",
        " ╚════╝ "
    ],
    'K': [
        "██╗  ██╗",
        "██║ ██╔╝",
        "█████╔╝ ",
        "██╔═██╗ ",
        "██║  ██╗",
        "╚═╝  ╚═╝"
    ],
    'L': [
        "██╗     ",
        "██║     ",
        "██║     ",
        "██║     ",
        "███████╗",
        "╚══════╝"
    ],
    'M': [
        "███╗   ███╗",
        "████╗ ████║",
        "██╔████╔██║",
        "██║╚██╔╝██║",
        "██║ ╚═╝ ██║",
        "╚═╝     ╚═╝"
    ],
    'N': [
        "███╗   ██╗",
        "████╗  ██║",
        "██╔██╗ ██║",
        "██║╚██╗██║",
        "██║ ╚████║",
        "╚═╝  ╚═══╝"
    ],
    'O': [
        " ██████╗ ",
        "██╔═══██╗",
        "██║   ██║",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ "
    ],
    'P': [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔═══╝ ",
        "██║     ",
        "╚═╝     "
    ],
    'Q': [
        " ██████╗  ",
        "██╔═══██╗ ",
        "██║   ██║ ",
        "██║▄▄ ██║ ",
        "╚██████╔╝ ",
        " ╚══▀▀═╝  "
    ],
    'R': [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔══██╗",
        "██║  ██║",
        "╚═╝  ╚═╝"
    ],
    'S': [
        "███████╗",
        "██╔════╝",
        "███████╗",
        "╚════██║",
        "███████║",
        "╚══════╝"
    ],
    'T': [
        "████████╗",
        "╚══██╔══╝",
        "   ██║   ",
        "   ██║   ",
        "   ██║   ",
        "   ╚═╝   "
    ],
    'U': [
        "██╗   ██╗",
        "██║   ██║",
        "██║   ██║",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ "
    ],
    'V': [
        "██╗   ██╗",
        "██║   ██║",
        "██║   ██║",
        "╚██╗ ██╔╝",
        " ╚████╔╝ ",
        "  ╚═══╝  "
    ],
    'W': [
        "██╗    ██╗",
        "██║    ██║",
        "██║ █╗ ██║",
        "██║███╗██║",
        "╚███╔███╔╝",
        " ╚══╝╚══╝ "
    ],
    'X': [
        "██╗  ██╗",
        "╚██╗██╔╝",
        " ╚███╔╝ ",
        " ██╔██╗ ",
        "██╔╝ ██╗",
        "╚═╝  ╚═╝"
    ],
    'Y': [
        "██╗   ██╗",
        "╚██╗ ██╔╝",
        " ╚████╔╝ ",
        "  ╚██╔╝  ",
        "   ██║   ",
        "   ╚═╝   "
    ],
    'Z': [
        "███████╗",
        "╚══███╔╝",
        "  ███╔╝ ",
        " ███╔╝  ",
        "███████╗",
        "╚══════╝"
    ],
    '0': [
        " ██████╗ ",
        "██╔═████╗",
        "██║██╔██║",
        "████╔╝██║",
        "╚██████╔╝",
        " ╚═════╝ "
    ],
    '1': [
        " ██╗",
        "███║",
        "╚██║",
        " ██║",
        " ██║",
        " ╚═╝"
    ],
    '2': [
        "██████╗ ",
        "╚════██╗",
        " █████╔╝",
        "██╔═══╝ ",
        "███████╗",
        "╚══════╝"
    ],
    '3': [
        "██████╗ ",
        "╚════██╗",
        " █████╔╝",
        " ╚═══██╗",
        "██████╔╝",
        "╚═════╝ "
    ],
    '4': [
        "██╗  ██╗",
        "██║  ██║",
        "███████║",
        "╚════██║",
        "     ██║",
        "     ╚═╝"
    ],
    '5': [
        "███████╗",
        "██╔════╝",
        "███████╗",
        "╚════██║",
        "███████║",
        "╚══════╝"
    ],
    '6': [
        " ██████╗",
        "██╔════╝",
        "███████╗",
        "██╔═══██╗",
        "╚██████╔╝",
        " ╚═════╝"
    ],
    '7': [
        "███████╗",
        "╚════██║",
        "    ██╔╝",
        "   ██╔╝ ",
        "   ██║  ",
        "   ╚═╝  "
    ],
    '8': [
        " █████╗ ",
        "██╔══██╗",
        "╚█████╔╝",
        "██╔══██╗",
        "╚█████╔╝",
        " ╚════╝ "
    ],
    '9': [
        " █████╗ ",
        "██╔══██╗",
        "╚██████║",
        " ╚═══██║",
        " █████╔╝",
        " ╚════╝ "
    ],
    '!': [
        "██╗",
        "██║",
        "██║",
        "╚═╝",
        "██╗",
        "╚═╝"
    ],
    '?': [
        "██████╗ ",
        "╚════██╗",
        "  ▄███╔╝",
        "  ▀▀══╝ ",
        "  ██╗   ",
        "  ╚═╝   "
    ],
    ' ': [
        "   ",
        "   ",
        "   ",
        "   ",
        "   ",
        "   "
    ]
}

def generate_ascii_art(text: str, color: str = "cyan") -> str:
    """
    Generate ASCII art from text using block letters
    
    Args:
        text: Text to convert
        color: Rich color to use
        
    Returns:
        ASCII art string
    """
    text = text.upper()
    lines = ["", "", "", "", "", ""]
    
    for char in text:
        if char in ASCII_FONT:
            for i, line in enumerate(ASCII_FONT[char]):
                lines[i] += line
        else:
            # Unknown character, add spaces
            for i in range(6):
                lines[i] += "   "
    
    return "\n".join(lines)

def cmd_ascii(text: str):
    """Generate and display ASCII art from text"""
    if not text:
        console.print("[yellow]Usage: /ascii <text>[/yellow]")
        console.print("[muted]Example: /ascii ATHENA[/muted]")
        return
    
    # Secret Matrix Rain Mode
    if text.lower() == "rain":
        try:
            import random
            console.clear()
            width = console.width
            # Characters to drop
            chars = ["0", "1", "日", "ﾊ", "ﾐ", "ﾋ", "ｰ", "ｳ", "ｼ", "ﾅ", "ﾓ", "ﾆ", "ｻ", "ﾜ", "ﾂ", "ｵ", "ﾘ", "ｱ", "ﾎ", "ﾃ", "ﾏ", "ｹ", "ﾒ", "ｴ", "ｶ", "ｷ", "ﾑ", "ﾕ", "ﾗ", "ｾ", "ﾈ", "ｽ", "ﾀ", "ﾇ", "ﾍ"]
            
            # Columns state: 0 = empty, >0 = trail length remaining
            columns = [0] * width
            
            # Run for 200 frames/lines
            for _ in range(300):
                line = ""
                for i in range(width):
                    if columns[i] > 0:
                        # Continue trail
                        columns[i] -= 1
                        char = random.choice(chars)
                        # Bright head, dim tail
                        if columns[i] > 15:
                            line += f"[bold white]{char}[/bold white]"
                        elif columns[i] > 5:
                            line += f"[bold green]{char}[/bold green]"
                        else:
                            line += f"[dim green]{char}[/dim green]"
                    else:
                        # Chance to start new trail
                        if random.random() < 0.02:
                            columns[i] = random.randint(10, 25)
                            line += f"[bold white]{random.choice(chars)}[/bold white]"
                        else:
                            line += " "
                
                print(line) # Use raw print for speed/overlap handling? No, console.print handles styles
                # console.print(line, highlight=False) 
                # Actually, plain print might be smoother for this specific effect on some terminals
                # Let's stick to rich but with markup
                time.sleep(0.03)
                
            console.clear()
            # Restore banner
            print_banner(animate=False)
            return
        except KeyboardInterrupt:
            console.clear()
            print_banner(animate=False)
            return

    # Normal ASCII Art
    # Limit text length to avoid overflow
    if len(text) > 12:
        console.print("[yellow]⚠ Text too long. Maximum 12 characters.[/yellow]")
        text = text[:12]
    
    ascii_art = generate_ascii_art(text)
    console.print(f"\n[bold cyan]{ascii_art}[/bold cyan]\n")


def cmd_clear():
    """Clear the terminal screen"""
    console.clear()
    print_banner(animate=False)

# =============================================================================
# PATTERN MANAGER
# =============================================================================

def cmd_pattern(args: str):
    """
    Manage Athena's Pattern Registry.
    Usage:
        /pattern list [domain]
        /pattern rate <id> <yes/no>
    """
    from services.pattern_engine import get_pattern_engine
    engine = get_pattern_engine()
    
    parts = args.split()
    if not parts:
        console.print("[yellow]Usage: /pattern list [domain] OR /pattern rate <id> <yes/no>[/yellow]")
        return
        
    action = parts[0].lower()
    
    if action == "list":
        domain = parts[1] if len(parts) > 1 else None
        
        # 1. Active Patterns
        patterns = engine.get_active_patterns(domain)
        
        console.print(f"\n[bold #4285F4]🧠 Active Patterns ({len(patterns)})[/bold #4285F4]")
        if domain: console.print(f"[dim]Domain: {domain}[/dim]")
        
        for p in patterns:
            status_color = "green" if p.status == "confirmed" else "yellow"
            conf_str = f"{p.confidence*100:.0f}%"
            
            console.print(Panel(
                f"[bold]{p.name}[/bold]\n"
                f"{p.description}\n"
                f"[dim]ID: {p.id} | Support: {p.support} | Conf: {conf_str}[/dim]",
                title=f"[{status_color}]{p.status.upper()}[/{status_color}]",
                border_style=status_color
            ))
            
    elif action == "rate":
        if len(parts) < 3:
            console.print("[red]Usage: /pattern rate <id> <yes/no>[/red]")
            return
            
        pid = parts[1]
        decision = parts[2].lower() in ("yes", "y", "true", "correct")
        
        if engine.rate_pattern(pid, decision):
            console.print(f"[green]✅ Pattern '{pid}' updated. (Feedback Recorded)[/green]")
        else:
            console.print(f"[red]❌ Pattern '{pid}' not found.[/red]")

def cmd_clitools():
    """Display Cheat Sheet for CLI Power Tools"""
    from rich.table import Table
    
    table = Table(
        title="[bold #BF40BF]⚡ CLI Power Tools Cheat Sheet[/bold #BF40BF]",
        border_style="#800080",
        header_style="bold cyan",
        box=box.ROUNDED,
        padding=(0, 2)
    )
    
    table.add_column("Tool", style="bold #E0B0FF")
    table.add_column("What it is", style="dim white")
    table.add_column("Example Usage", style="#00BCD4")
    
    tools = [
        ("bat", "Cat with wings (syntax highlighting)", "bat file.py"),
        ("eza", "Modern ls (icons, colors)", "eza -la --icons"),
        ("rg", "Ripgrep (super fast search)", "rg 'pattern' ./src"),
        ("fzf", "Fuzzy finder", "ls | fzf"),
        ("zoxide", "Smarter cd (learns directories)", "z project_name"),
        ("tldr", "Simplified man pages", "tldr tar"),
        ("httpie", "API testing (like curl)", "http GET example.com"),
        ("jq", "JSON processor", "cat data.json | jq ."),
        ("fd", "Simple find", "fd logo.png"),
        ("hyperfine", "Command benchmarking", "hyperfine 'sleep 0.5'"),
        ("micro", "Intuitive terminal editor", "micro config.txt")
    ]
    
    for tool, desc, example in tools:
        table.add_row(tool, desc, example)
        
    console.print(table)
    console.print("[dim]Use /run <example> to try them out![/dim]\n")

# =============================================================================
# MAIN CLI LOOP
# =============================================================================

# =============================================================================
# SPOKE AGENT EXECUTOR (The Scientist Protocol)
# =============================================================================

def execute_spoke_agent(agent_name: str, args: str, domain: str = "general"):
    """
    Execute a Spoke Agent with Context Capsule and Pattern Engine ingestion.
    Ref: 1. Context Capsules & 2. Event Logger
    """
    try:
        from services.athena_schemas import ContextCapsule
        from services.pattern_engine import get_pattern_engine, AgentOutput, AthenaEvent
        from services.access_control import get_access_control, AgentPolicy
        import json
        
        # 0. ACCESS CONTROL CHECK
        # =========================================================================
        ac = get_access_control()
        policy = ac.get_policy(agent_name)
        
        if not policy:
            # If strict mode, block unknown agents. For now, warn.
            console.print(f"[yellow]⚠ Policy Warning: No access policy found for '{agent_name}'. Defaulting to Level 0 (Observe Only).[/yellow]")
        
        # 1. Generate Capsule (Real Data)
        # =========================================================================
        engine = get_pattern_engine()
        # Mock preferences for now, or fetch from MemoryCore if available
        # from services.memory_core import get_memory
        # mem = get_memory()
        # prefs = mem.get_preferences(domain)
        
        capsule = ContextCapsule(
            task_goal=f"Execute {agent_name}",
            relevant_preferences={}, # Wired to MemoryCore in future step
            relevant_constraints={},
            recent_trends=engine.trends.get(domain, []), # REAL TRENDS
            domain=domain,
            # Inject Read Scopes from Policy
            do_not_use=["EV", "private_messages"] if not policy or "EV" not in policy.read_scopes else []
        )
        capsule_json = capsule.to_json()
        
        # 2. Construct Command
        # Handle Module Paths (e.g. financial_advisor/agent) vs Scripts
        if "/" in agent_name:
             script_path = f"{agent_name}.py"
        else:
             script_path = f"agents/{agent_name}.py"
             
        command = f'python {script_path} {args} --context \'{capsule_json}\''
        
        console.print(Panel(f"[dim]🧪 Lab Protocol: Running {agent_name} with Context[/dim]", border_style="cyan"))
        
        # 3. Execute
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True
        )
        
        output = result.stdout
        
        # 4. Parse Envelope & Ingest
        # =========================================================================
        if "START_ENVELOPE" in output and "END_ENVELOPE" in output:
            try:
                json_part = output.split("START_ENVELOPE")[1].split("END_ENVELOPE")[0].strip()
                data = json.loads(json_part)
                
                # A. Print Observations/Recs
                if "observations" in data:
                    for obs in data["observations"]:
                        console.print(f"[bold cyan]👁 OBS:[/bold cyan] {obs}")
                if "recommendations" in data:
                    for rec in data["recommendations"]:
                        console.print(f"[bold green]💡 REC:[/bold green] {rec}")
                
                # B. Ingest Events (The Nervous System)
                if "events_to_log" in data and data["events_to_log"]:
                    count = 0
                    triggers = []
                    
                    for evt_dict in data["events_to_log"]:
                        # Convert dict to AthenaEvent
                        # (Assume agent sends valid dict matching schema)
                        from services.athena_schemas import AthenaEvent
                        if "timestamp" not in evt_dict:
                             evt_dict["timestamp"] = None # Let constructor handle or default
                        
                        try:
                            # Basic validation/cleanup before ingestion
                            event = AthenaEvent(**evt_dict)
                            # Check Write Scope
                            if policy and "events" in policy.write_scopes:
                                engine.events.append(event) # Ingest to Memory
                                count += 1
                                
                                # CHECK TRIGGERS
                                if event.type == "purchase" and event.domain == "finance":
                                    triggers.append("finance_reconcile")
                            else:
                                console.print(f"[red]⛔ Event Blocked: Agent '{agent_name}' lacks 'events' write scope.[/red]")
                        except Exception as e:
                            console.print(f"[red]Event Ingestion Error: {e}[/red]")
                            
                    if count > 0:
                        engine.save_state() # PERSIST
                        console.print(f"[dim]📝 Ingested {count} events -> Pattern Engine.[/dim]")
                    
                    # C. Fire Triggers (The Reflex)
                    for t in triggers:
                        if t == "finance_reconcile":
                            console.print("[bold yellow]⚡ REFLEX: Triggering Financial Advisor (Auto-Event)...[/bold yellow]")
                            # Recursive call - careful of loops!
                            # We launch it as a separate command to avoid recursion depth issues in this simple CLI
                            # In a real async system, we'd await it.
                            execute_spoke_agent("financial_advisor/agent", "auto-event --event_type purchase", domain="finance")

                # D. Check Permissions for Proposed Updates
                if "proposed_memory_updates" in data and data["proposed_memory_updates"]:
                    if policy and "memory_proposals" in policy.write_scopes:
                         for update in data["proposed_memory_updates"]:
                             console.print(f"[dim green]🧠 Memory Proposal ({update.get('type')}): {update.get('statement')}[/dim green]")
                    else:
                        console.print(f"[red]⛔ Memory Update Blocked: Agent '{agent_name}' lacks 'memory_proposals' scope.[/red]")
                
            except Exception as e:
                console.print(f"[red]Failed to parse agent envelope: {e}[/red]")
                console.print(output)
        else:
            # Legacy/Raw Output
            if output.strip():
                console.print(output)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")

    except ImportError:
        # Fallback
        console.print("[yellow]⚠ Services not found, running legacy mode...[/yellow]")
        cmd_run(f"python agents/{agent_name}.py {args}")
    except Exception as e:
        console.print(f"[red]Agent Execution Error: {e}[/red]")

def print_banner(animate: bool = True):
    """Print the Athena startup banner with optional animation"""
    console.clear()
    
    if animate:
        # Quick loading bar animation
        console.print("\n[#E0B0FF]Initializing ATHENA...[/#E0B0FF]")
        for frame in STARTUP_ANIMATION_FRAMES:
            console.print(f"\r{frame}", end="")
            time.sleep(0.05)
        console.print()
        time.sleep(0.3)
        console.clear()
    
    # Print logo and banner in Purple Panel
    # Combine logo and banner cleanly
    full_banner = f"{ATHENA_LOGO}\n{ATHENA_BANNER}"
    
    console.print(Panel(
        Align.center(full_banner),
        border_style="#800080",
        box=box.DOUBLE,
        subtitle="[dim]System Online[/dim]",
        padding=(1, 2)
    ))
    
    console.print()
    console.print(f"[muted]  {datetime.now().strftime('%A, %B %d, %Y • %H:%M')}[/muted]")
    console.print(f"[muted]  Type /help for commands • Type naturally to chat[/muted]")
    console.print()

def process_command(user_input: str):
    """
    Process user input - route to local commands or cloud
    
    Args:
        user_input: Raw user input string
    """
    # Clean input of common prompt artifacts
    user_input = user_input.strip()
    if "ATHENA >" in user_input:
        user_input = user_input.replace("ATHENA >", "").strip()
    
    if not user_input:
        return
        
    # MULTI-COMMAND SUPPORT (&&)
    if " && " in user_input:
        commands = user_input.split(" && ")
        console.print(f"[dim]⛓️ Chained Sequence Detected: {len(commands)} actions[/dim]")
        for cmd in commands:
            process_command(cmd.strip())
        return

    # Local command (starts with /)
    if user_input.startswith("/"):
        parts = user_input[1:].split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "help":
            cmd_help()
        elif command == "look":
            cmd_look()
        elif command == "launch":
            cmd_launch(args)
        elif command == "apps":
            cmd_apps()
        elif command == "parlay":
            cmd_parlay(args)
        elif command == "status":
            cmd_status()
        elif command == "clitools" or command == "tools":
            cmd_clitools()
        elif command == "ascii":
            cmd_ascii(args)
        # --- HAKARI (PARLAY AGENT) COMMANDS ---
        elif command == "fever":
            execute_spoke_agent("parlay/agent", "--command /fever " + args)
        elif command == "bag_watch":
            execute_spoke_agent("parlay/agent", "--command /bag_watch " + args)
        elif command == "ref_report":
            execute_spoke_agent("parlay/agent", "--command /ref_report " + args)
        elif command == "vet_fade":
            execute_spoke_agent("parlay/agent", "--command /vet_fade " + args)
        elif command == "domain":
            execute_spoke_agent("parlay/agent", "--command /domain " + args)
        elif command == "audit":
            execute_spoke_agent("parlay/agent", "--command /audit " + args)
        # --------------------------------------
        elif command == "notebook":
            execute_spoke_agent("notebooklm/agent", args)
        # --------------------------------------
        elif command == "notion":
            execute_spoke_agent("notion/agent", "--action " + args if args else "--help")
        # --------------------------------------
        elif command == "finance":
            # Map /finance to the new Financial Advisor Module (CFO Brain)
            # We call the module path: financial_advisor/agent.py
            execute_spoke_agent("financial_advisor/agent", args)
        elif command == "email":
            cmd_email(args)
        elif command == "pattern":
            cmd_pattern(args)
        elif command == "ls":
            cmd_ls(args)
        elif command == "cat":
            cmd_cat(args)
        elif command == "search":
            cmd_search(args)
        elif command == "tldr":
            cmd_tldr(args)
        elif command == "run" or command == "exec" or command == "!":
            cmd_run(args)
        elif command == "clear":
            cmd_clear()
        elif command in ("exit", "quit", "bye"):
            console.print("\n[cyan]👋 ATHENA signing off. Until next time![/cyan]\n")
            sys.exit(0)
        else:
            # DYNAMIC AGENT DISCOVERY
            # Check if agents/{command}.py or agents/{command}_agent.py exists
            agent_path = BASE_DIR / "agents" / f"{command}.py"
            agent_path_alt = BASE_DIR / "agents" / f"{command}_agent.py"
            
            if agent_path.exists():
                execute_spoke_agent(command, args)
                return
            elif agent_path_alt.exists():
                execute_spoke_agent(f"{command}_agent", args)
                return
                
            console.print(f"[yellow]Unknown command: /{command}[/yellow]")
            console.print("[muted]Type /help for available commands[/muted]")
    
    # Cloud message - SMART ROUTER
    else:
        # --- SMART ROUTER (Hub & Spoke) ---
        lower_input = user_input.lower()
        
        # FINANCE AGENT ROUTER
        # Detects: "log $50 for gas", "spent 20 on food", etc.
        if any(x in lower_input for x in ["log", "spent", "paid"]) and "$" in user_input:
            console.print("[dim]🤖 Routing to Finance Agent...[/dim]")
            
            # Extract amount (simple regex)
            import re
            amount_match = re.search(r'\$(\d+(\.\d{2})?)', user_input)
            amount = amount_match.group(1) if amount_match else "0"
            
            # Extract category (simple heuristic)
            category = "General"
            for cat in ["gas", "food", "groceries", "rent", "utilities", "entertainment", "dining"]:
                if cat in lower_input:
                    category = cat.title()
                    break
                
            # Run Financial Advisor Agent (check-purchase for gate-keeping)
            execute_spoke_agent("financial_advisor/agent", f"check-purchase --amount {amount} --item \"{user_input[:50]}\" --category {category}")
            return

        # MEDIC AGENT ROUTER
        if any(x in lower_input for x in ["medic", "health check", "system status", "/medic"]):
            console.print("[dim]🏥 Routing to Medic Agent...[/dim]")
            cmd_run('python agents/medic.py --action check')
            return

        # NEWS AGENT ROUTER
        if any(x in lower_input for x in ["news", "briefing", "daily brief", "/news"]):
            console.print("[dim]📰 Routing to News Agent...[/dim]")
            cmd_run('python agents/news_brief.py --action brief')
            return
            
        # HEALTH/STEPS AGENT ROUTER
        if any(x in lower_input for x in ["steps", "walking", "heart rate", "sleep", "health data", "fitness"]):
            console.print("[dim]❤️ Routing to Health Agent...[/dim]")
            # Default to fetching today's summary or last 7 days
            cmd_run('python agents/health_sync.py --action sync')
            return

        # ARCHIVE SEARCH ROUTER (Memory)
        if any(x in lower_input for x in ["search chat", "search history", "what did i say about", "find conversation"]):
             console.print("[dim]🧠 Routing to Archive Search...[/dim]")
             # Remove trigger words to get query
             query = user_input.replace("search chat", "").replace("search history", "").strip()
             cmd_run(f'python agents/archive_search.py --query "{query}"')
             return

        if any(x in lower_input for x in ["rain effect", "matrix rain", "digital rain", "do the rain"]):
             console.print("[dim]🕶️ Entering the Matrix...[/dim]")
             cmd_ascii("rain")
             return

        # DEFAULT: Send to Cloud Brain
        # But first, check for Shell Commands (pip, npm, git, etc.)
        shell_verbs = ["pip", "npm", "git", "python", "py", "node", "winget", "choco", "docker"]
        first_word = user_input.split()[0].lower() if user_input.split() else ""
        
        if first_word in shell_verbs:
             console.print(f"[dim]⚡ Auto-detected shell command: {first_word}[/dim]")
             cmd_run(user_input)
             return

        # Default Cloud Chat
        response = send_to_cloud(user_input)
        
        if response:
            # Stream the text response
            text = response.get("response", response.get("text", str(response)))
            stream_response(text)
            
            # Play audio if available
            audio_url = response.get("audio_url")
            if audio_url:
                play_audio(audio_url)

# =============================================================================
# BACKGROUND SERVICES
# =============================================================================

def init_telegram_bot():
    """Start the Telegram bot in a background thread"""
    from services.telegram_service import get_telegram_service
    
    # Check if configured
    service = get_telegram_service()
    if not service.is_configured:
        return

    import threading
    import asyncio
    
    def telegram_loop():
        """Async loop for polling telegram"""
        async def poll():
            offset = 0
            console.print("[dim]🤖 Telegram Bot Active (Background)...[/dim]")
            
            # --- TASK ENGINE ---
            from core.tasks.manager import TaskManager
            from core.tasks.model import TaskStatus
            
            # --- PROACTIVE NUDGES ---
            try:
                from core.nudges.proactive_nudge import get_proactive_engine
                nudge_engine = get_proactive_engine()
            except Exception:
                nudge_engine = None
            
            # --- FEEDBACK STORE ---
            try:
                from core.learning.feedback_store import get_feedback_store
                feedback_store = get_feedback_store()
            except Exception:
                feedback_store = None
            
            # Access global context_stack if possible.
            try:
                global context_stack
                global router
            except:
                pass # Use local if needed
                
            task_manager = TaskManager()
            local_stack = context_stack if 'context_stack' in globals() and context_stack else None
            
            # Send startup message
            await service.send_text("🚀 Athena CLI Online!")
            
            # Track last nudge check time
            last_nudge_check = 0
            
            while True:
                try:
                    # --- PROACTIVE NUDGES CHECK (every 60s) ---
                    import time
                    now_ts = time.time()
                    if nudge_engine and (now_ts - last_nudge_check) > 60:
                        last_nudge_check = now_ts
                        nudge = nudge_engine.check_pending()
                        if nudge:
                            await service.send_text(nudge["message"])
                            console.print(f"[yellow]📣 Proactive Nudge: {nudge['name']}[/yellow]")
                    
                    updates = await service.get_updates(offset=offset, limit=10)
                    for update in updates:
                        offset = update["update_id"] + 1
                        
                        # A. HANDLE CALLBACKS (Buttons)
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            cb_id = cb["id"]
                            data = cb.get("data", "")
                            msg_ref = cb.get("message")
                            chat_id = str(msg_ref["chat"]["id"])
                            
                            # Acknowledge immediately to stop spinner
                            await service.answer_callback_query(cb_id)
                            
                            # Format: action:task_id
                            if ":" in data:
                                action, tid = data.split(":", 1)
                                task = task_manager.get_task(tid)
                                
                                if task:
                                    if action == "confirm":
                                        # EXECUTE
                                        task.status = TaskStatus.RUNNING
                                        await service.send_plan_card(task, chat_id=chat_id) 
                                        
                                        # 1. Update Context Stack (Persistence)
                                        if local_stack:
                                            # Push entities
                                            for k, v in task.slots.items():
                                                if k in ["location", "who", "when"]:
                                                    local_stack.push_entity(chat_id, k.upper(), str(v))
                                        
                                        # Todo: Real dispatch. For now, mock success.
                                        await service.send_text(f"✅ Executing intent: {task.intent}...", chat_id=chat_id)
                                        
                                        # Execute Logic (New)
                                        if task.intent == "email_search":
                                             # Run the search and return results
                                             q = task.slots.get("query", "")
                                             days = task.slots.get("days_back", 7)
                                             from services.google_service import get_google_service
                                             res = get_google_service().search_transaction_emails(days=days)
                                             count = len(res) if res else 0
                                             await service.send_text(f"Found {count} emails for '{q}'.", chat_id=chat_id)
                                             if local_stack:
                                                 local_stack.push_result_set(chat_id, "emails", res or [], surface="telegram")
                                        
                                        elif task.intent == "schedule_event":
                                            # Calendar Integration
                                            try:
                                                from services.calendar_helper import parse_natural_datetime, format_event_confirmation
                                                from services.google_service import get_google_service
                                                
                                                title = task.slots.get("title", "Untitled Event")
                                                when_str = task.slots.get("start_time", task.slots.get("when", "tomorrow"))
                                                location = task.slots.get("location")
                                                
                                                start_dt, duration = parse_natural_datetime(when_str)
                                                
                                                if start_dt:
                                                    result = get_google_service().create_calendar_event(
                                                        title=title,
                                                        start_time=start_dt,
                                                        duration_minutes=duration,
                                                        location=location
                                                    )
                                                    
                                                    if result.get("success"):
                                                        confirm_msg = format_event_confirmation(title, start_dt, duration)
                                                        await service.send_text(f"✅ Created!\n\n{confirm_msg}\n\n[Open]({result['link']})", chat_id=chat_id)
                                                    else:
                                                        await service.send_text(f"❌ Failed: {result.get('error')}", chat_id=chat_id)
                                                else:
                                                    await service.send_text("❌ Couldn't parse the date/time. Try 'tomorrow at 3pm'.", chat_id=chat_id)
                                            except Exception as e:
                                                await service.send_text(f"❌ Calendar error: {e}", chat_id=chat_id)
                                        
                                        # Log for learning
                                        if feedback_store:
                                            feedback_store.log_decision(
                                                surface="telegram",
                                                user_input=str(task.slots),
                                                intent=task.intent,
                                                confidence=task.confidence,
                                                slots=task.slots,
                                                reasoning=getattr(task, 'reasoning', '')
                                            )
                                        
                                        task.status = TaskStatus.COMPLETED
                                        await service.send_plan_card(task, chat_id=chat_id) 
                                        
                                    elif action == "cancel":
                                        task.status = TaskStatus.CANCELED
                                        await service.send_plan_card(task, chat_id=chat_id)
                                        await service.send_text("❌ Task canceled.", chat_id=chat_id)
                                        
                                    elif action == "edit_menu":
                                        await service.send_text("✏️ Reply with the change (e.g. 'tomorrow instead').", chat_id=chat_id)
                                        if local_stack:
                                            local_stack.get_state(chat_id).active_task_id = tid # Set focus

                                    elif action == "why":
                                        # Explain assumptions
                                        explanation = "🤔 **Reasoning:**\n"
                                        if task.assumptions:
                                            for k, v in task.assumptions.items():
                                                explanation += f"• Assumed **{k}** = `{v}` based on context.\n"
                                        else:
                                            explanation += "• All parameters were explicitly provided.\n"
                                        
                                        explanation += f"\nConfidence: {task.confidence}"
                                        await service.send_text(explanation, chat_id=chat_id)
                                    
                                    # --- FEEDBACK CALLBACKS ---
                                    elif action in ["fb_win", "fb_spiral", "fb_bad"]:
                                        feedback_type = action.replace("fb_", "")
                                        
                                        if feedback_store and task:
                                            # Find the most recent log entry for this task
                                            feedback_store.add_feedback(task.created_at if hasattr(task, 'created_at') else "", feedback_type)
                                        
                                        emoji = {"win": "⭐", "spiral": "🌀", "bad": "👎"}.get(feedback_type, "📝")
                                        await service.send_text(f"{emoji} Feedback recorded: **{feedback_type}**. This helps me learn!", chat_id=chat_id)
                                    
                                    # --- SAVE PREFERENCE CALLBACKS ---
                                    elif action == "save_pref":
                                        await service.send_text("💾 Preference saved to memory!", chat_id=chat_id)
                                        # TODO: Actually persist to semantic memory
                                    elif action == "skip_save":
                                        await service.send_text("👍 Got it, not saving.", chat_id=chat_id)
                            
                            continue

                        # B. HANDLE MESSAGES
                        msg = service.parse_update(update)
                        
                        if msg:
                            # Prepare display text
                            display_text = msg.text if msg.text else ("[Photo]" if msg.has_photo else "[Unknown Message]")
                            console.print(Panel(f"[blue]📨 Telegram from {msg.sender}:[/blue]\n{display_text}", border_style="blue"))
                            
                            # Process as command
                            lower_text = msg.text.lower() if msg.text else ""
                            chat_id = msg.chat_id
                            
                            # --- SEMANTIC ROUTER (New) ---
                            if 'router' in globals() and router and local_stack:
                                try:
                                    # 1. Resolve References
                                    active_ref = local_stack.resolve_reference(chat_id, msg.text or "")
                                    
                                    # 2. Route
                                    route_result = router.route(msg.text or "", [{"role": "user", "content": msg.text}], active_reference=active_ref)
                                    
                                    intent = route_result.get("intent")
                                    slots = route_result.get("slots", {})
                                    confidence = route_result.get("confidence", 0.0)
                                    reasoning = route_result.get("reasoning", "")
                                    
                                    # Create Task Draft if confident
                                    if intent not in ["general_chat", None] and confidence > 0.6:
                                        task = task_manager.create_task(intent, slots, confidence)
                                        task.assumptions = route_result.get("assumptions", {})
                                        task.reasoning = reasoning
                                        
                                        # Send Proposal
                                        await service.send_plan_card(task, chat_id=chat_id)
                                        continue
                                except Exception as e:
                                    console.print(f"[yellow]Telegram Router Error: {e}[/yellow]")
                            
                            # --- LEGACY FALLBACK ---
                            # 1. MEDIC AGENT
                            if "/medic" in lower_text or "health check" in lower_text:
                                await service.send_typing_action(msg.chat_id)
                                try:
                                    # Run subprocess
                                    proc = subprocess.run(["python", "agents/medic.py", "--action", "check"], capture_output=True, text=True)
                                    output = proc.stdout if proc.returncode == 0 else proc.stderr
                                    # Send back to Telegram (strip color codes if needed, or wrap in code block)
                                    await service.send_text(f"```\n{output[:4000]}\n```", chat_id=msg.chat_id, parse_mode="Markdown")
                                except Exception as e:
                                    await service.send_text(f"Error running Medic: {e}", chat_id=msg.chat_id)

                            # 2. NEWS AGENT
                            elif "/news" in lower_text or "briefing" in lower_text:
                                await service.send_typing_action(msg.chat_id)
                                try:
                                    proc = subprocess.run(["python", "agents/news_brief.py", "--action", "brief"], capture_output=True, text=True)
                                    output = proc.stdout if proc.returncode == 0 else proc.stderr
                                    await service.send_text(f"```\n{output[:4000]}\n```", chat_id=msg.chat_id, parse_mode="Markdown")
                                except Exception as e:
                                    await service.send_text(f"Error running News: {e}", chat_id=msg.chat_id)

                            # 3. PARLAY AGENT - INSTRUCTIONS
                            elif "/parlay" in lower_text or "/parley" in lower_text:
                                await service.send_text("🏀 **Parlay Assistant Ready**\n\nPlease upload a screenshot of your pick slip, or type a player name and stat to analyze.\n\n*Examples:*\n- Upload an image\n- \"LeBron James Points 25.5\"\n- \"Curry over 4.5 threes\"", chat_id=msg.chat_id, parse_mode="Markdown")

                            # 4. PARLAY AGENT - TEXT ANALYSIS
                            elif any(x in lower_text for x in ["points", "rebounds", "assists", "pts", "reb", "ast", "threes", "3pm", "fantasy score"]) and any(c.isdigit() for c in lower_text):
                                await service.send_typing_action(msg.chat_id)
                                await service.send_text("🔍 Analyzing stats...", chat_id=msg.chat_id)
                                try:
                                    # Run analysis in thread executor
                                    loop = asyncio.get_event_loop()
                                    result = await loop.run_in_executor(None, lambda: asyncio.run(service.analyze_parlay_text(msg.text)))
                                    
                                    if result.get("error"):
                                        # Fallback to normal chat if analysis failed (maybe it wasn't a bet)
                                        await service.send_text(f"⚠️ Analysis failed, trying normal chat...", chat_id=msg.chat_id)
                                        # Fallback logic here if needed, or just let it fail gracefully
                                        loop = asyncio.get_event_loop()
                                        response = await loop.run_in_executor(None, send_to_cloud, msg.text)
                                        if response and "response" in response:
                                            await service.send_text(response["response"], chat_id=msg.chat_id)
                                    else:
                                        # Format output
                                        picks = result.get("picks", [])
                                        reply = f"📊 **Stat Analysis**\n\n"
                                        for p in picks:
                                            icon = "✅" if p.get("agree") else "❌"
                                            reply += f"{icon} **{p.get('player')}**\n"
                                            reply += f"   Type: {p.get('stat')} {p.get('line')}\n"
                                            reply += f"   You: {p.get('your_pick')} | Model: {p.get('verdict', 'N/A')}\n"
                                            if p.get("edge"):
                                                reply += f"   Edge: {p.get('edge')}%\n"
                                            reply += "\n"
                                        
                                        await service.send_text(reply, chat_id=msg.chat_id, parse_mode="Markdown")

                                except Exception as e:
                                     await service.send_text(f"Processing error: {e}", chat_id=msg.chat_id)
                            
                            # 5. PHOTO ANALYSIS (Vision & Parlay)
                            elif msg.has_photo and msg.photo_file_id:
                                await service.send_typing_action(msg.chat_id)
                                
                                caption = (msg.text or "").lower()
                                
                                # A. Parlay Agent (Explicit or Contextual)
                                if "parlay" in caption or "prize" in caption or "bet" in caption or "slip" in caption:
                                    await service.send_text("🏀 Analyzing PrizePicks slip...", chat_id=msg.chat_id)
                                    try:
                                        # Run Parlay Agent
                                        loop = asyncio.get_event_loop()
                                        result = await loop.run_in_executor(None, lambda: asyncio.run(service.analyze_parlay_screenshot(msg.photo_file_id)))
                                        
                                        if result.get("error"):
                                            await service.send_text(f"❌ Analysis failed: {result['error']}", chat_id=msg.chat_id)
                                        else:
                                            # Format output
                                            picks = result.get("picks", [])
                                            reply = f"📊 **PrizePicks Analysis**\n\n"
                                            for p in picks:
                                                icon = "✅" if p.get("agree") else "❌"
                                                reply += f"{icon} **{p.get('player')}**\n"
                                                reply += f"   Type: {p.get('stat')} {p.get('line')}\n"
                                                reply += f"   You: {p.get('your_pick')} | Model: {p.get('verdict', 'N/A')}\n"
                                                if p.get("edge"):
                                                    reply += f"   Edge: {p.get('edge')}%\n"
                                                reply += "\n"
                                            await service.send_text(reply, chat_id=msg.chat_id, parse_mode="Markdown")
                                    except Exception as e:
                                        await service.send_text(f"Parlay Error: {e}", chat_id=msg.chat_id)
                                
                                # B. General Vision (Default)
                                else:
                                    prompt = msg.text if msg.text else "Describe this image in detail. What is interesting about it?"
                                    await service.send_text("👁️ Analyzing image...", chat_id=msg.chat_id)
                                    try:
                                        loop = asyncio.get_event_loop()
                                        description = await loop.run_in_executor(None, lambda: asyncio.run(service.analyze_general_image(msg.photo_file_id, prompt)))
                                        await service.send_text(f"**Athena Vision:**\n{description}", chat_id=msg.chat_id, parse_mode="Markdown")
                                    except Exception as e:
                                        await service.send_text(f"Vision Error: {e}", chat_id=msg.chat_id)


                            # 6. GENERIC AI CHAT
                            else:
                                await service.send_typing_action(msg.chat_id)
                                # Run the synchronous send_to_cloud in a thread to not block the loop
                                loop = asyncio.get_event_loop()
                                response = await loop.run_in_executor(None, send_to_cloud, msg.text)
                                
                                if response and "response" in response:
                                    # Send text response
                                    await service.send_text(response["response"], chat_id=msg.chat_id)
                                    
                                    # Send audio if available (as voice note)
                                    if response.get("audio_url"):
                                        await service.send_text(f"[Audio: {response['audio_url']}]", chat_id=msg.chat_id)
                                else:
                                    await service.send_text("I heard you, but I couldn't process that.", chat_id=msg.chat_id)

                            # Echo back to Telegram (Removed to avoid double messages)
                            # await service.send_text(f"Received: {msg.text}", chat_id=msg.chat_id)
                            
                    await asyncio.sleep(1)
                except Exception as e:
                    # console.print(f"[red]Telegram Error: {e}[/red]")
                    await asyncio.sleep(5)

        # Run async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(poll())

    # Start thread
    t = threading.Thread(target=telegram_loop, daemon=True)
    t.start()

def check_startup_data():
    """
    Background task: Cloud-First Sync & Automatic Analysis.
    1. Check Cloud Storage for existing data.
    2. Scan Local folder.
    3. Upload missing files to Cloud.
    4. Trigger Analysis (Rebuild Search Index) if data changed.
    """
    try:
        user_data_path = Path(r"C:\Users\itsdr\athena_data\me")
        if not user_data_path.exists():
            return

        from services.cloud_storage import get_cloud_storage
        cloud = get_cloud_storage()
        
        # 1. Get Cloud State
        cloud_files = set()
        if cloud.initialized:
            # console.print("[dim]☁️  Checking Cloud Storage state...[/dim]")
            try:
                # We assume files are stored under user_data/me/
                blob_names = cloud.list_files(prefix="user_data/me/")
                # Convert blob names to simple filenames for comparison (e.g. "user_data/me/notes.txt" -> "notes.txt")
                cloud_files = {name.split('/')[-1] for name in blob_names}
            except Exception as e:
                # console.print(f"[dim]⚠ Cloud check failed: {e}[/dim]")
                pass
        
        # 2. Compare Local vs Cloud
        files_to_sync = []
        local_files_found = False
        
        for file_path in user_data_path.rglob("*"):
            if file_path.is_file() and file_path.name != ".sync_state":
                local_files_found = True
                # If file NOT in cloud, mark for sync
                if file_path.name not in cloud_files:
                    files_to_sync.append(file_path)

        # 3. Upload Missing Files
        if files_to_sync:
            console.print(f"[dim]🔄 Syncing {len(files_to_sync)} new files to Cloud...[/dim]")
            
            uploaded_count = 0
            for file_path in files_to_sync:
                try:
                    blob_name = f"user_data/me/{file_path.name}"
                    if cloud.upload_file(str(file_path), blob_name):
                        uploaded_count += 1
                except Exception:
                    pass
            
            if uploaded_count > 0:
                console.print(f"[dim]✅ Uploaded {uploaded_count} files to Google Cloud.[/dim]")

        # 4. Automatic Analysis (Rebuild Index)
        # We run this if we found local files, just to be sure the Search Index is fresh
        if local_files_found:
            # Check if index exists or if we just synced new data
            index_path = Path(r"C:\Users\itsdr\athena_data\search_index")
            should_analyze = False
            
            if not index_path.exists():
                should_analyze = True
            elif files_to_sync: # We added new data, so update index
                should_analyze = True
            
            if should_analyze:
                # console.print("[dim]🧠 Auto-Analyzing data (Building Search Index)...[/dim]")
                def _run_indexer():
                    try:
                        # Run without 'check=True' to avoid crashing the thread on minor errors
                        # Capture output to log file instead of pipe to avoid buffer filling
                        log_path = Path("archive_search.log")
                        with open(log_path, "w") as log_file:
                            subprocess.run(
                                [sys.executable, "agents/archive_search.py", "--index"],
                                check=False,
                                stdout=log_file,
                                stderr=log_file,
                                cwd=str(BASE_DIR) # Ensure CWD is correct
                            )
                        # console.print("[dim]✅ Memory Analysis Complete.[/dim]")
                        
                        # Log to Memory Core
                        from services.memory_core import get_memory
                        mem = get_memory()
                        mem.log_interaction("System", "Startup Analysis: Rebuilt search index.", source="system")
                    except Exception:
                        pass

                # Run in background thread
                import threading
                t = threading.Thread(target=_run_indexer, daemon=True)
                t.start()

    except Exception as e:
        # console.print(f"[dim]Sync Error: {e}[/dim]")
        pass

def main():
    """Main entry point for Athena CLI"""
    # Initialize audio system
    init_audio()
    
    # Initialize Telegram Bot
    init_telegram_bot()
    
    # Check for new data in background
    import threading
    sync_thread = threading.Thread(target=check_startup_data, daemon=True)
    sync_thread.start()
    
    # Print startup banner
    print_banner(animate=True)

    # Trigger Auto-Sync & Analysis
    sync_and_analyze()
    
    # Setup Autocomplete (Gemini Style)
    session = None
    if HAS_PROMPT_TOOLKIT:
        # Command Metadata for Help & Autocomplete
        command_meta = {
            '/help': 'Show help menu',
            '/status': 'System status check',
            '/look': 'Vision capture (Athena sees screen)',
            '/launch': 'Launch an application', 
            '/apps': 'List installed applications',
            '/parlay': 'Control Parlay Assistant webapp',
            '/ascii': 'Generate ASCII art',
            '/clitools': 'Cheat Sheet for CLI Power Tools',
            '/email': 'Search Gmail',
            '/ls': 'List files (eza)',
            '/cat': 'Read file (bat)',
            '/search': 'Search files (rg)',
            '/tldr': 'Command cheatsheets',
            '/run': 'Execute shell command',
            '/clear': 'Clear screen',
            '/exit': 'Quit Athena',
            # HAKARI COMMANDS
            '/fever': '🔥 Detect Jackpots (Hakari)',
            '/bag_watch': '💰 Scan Incentives (Hakari)',
            '/ref_report': '🦓 Referee Analysis (Hakari)',
            '/vet_fade': '👴 Veteran Fatigue (Hakari)',
            '/domain': '🧠 Generate Slip (Hakari)',
            '/audit': '📉 Post-Mortem (Hakari)',
            '/notebook': '📒 Google NotebookLM Agent',
            '/notion': '📝 Manage Notion (Expenses/Journal)',
            '/jarvis': '🕵️ Jarvis OSINT Investigation',
            '/redact': '🕵️ Jarvis Investigation (Redacted)'
        }
        commands = list(command_meta.keys())
        
        # Custom Completer to restrict to slash commands
        class AthenaSlashCompleter(Completer):
            def __init__(self, commands, meta):
                self.word_completer = WordCompleter(commands, meta_dict=meta, ignore_case=True)
                self.fuzzy_completer = FuzzyCompleter(self.word_completer)

            def get_completions(self, document, complete_event):
                # ONLY show if starts with /
                if document.text.lstrip().startswith('/'):
                    yield from self.fuzzy_completer.get_completions(document, complete_event)

        # Initialize
        completer = AthenaSlashCompleter(commands, command_meta)
        
        # Purple Gemini Theme
        style = PromptStyle.from_dict({
            'completion-menu.completion': 'bg:#202124 fg:#F5F5F5', # Dark Charcoal / Off-white
            'completion-menu.completion.current': 'bg:#4B0082 fg:#E0B0FF', # Indigo / Mauve
            'completion-menu.meta.completion': 'bg:#2d2d2d fg:#E0B0FF', # Mauve descriptions
            'scrollbar.background': 'bg:#202124',
            'scrollbar.button': 'bg:#8F00FF', # Electric Violet
            'prompt': 'fg:#BF40BF bold', # Neon Violet
            'arrow': '#800080 bold', # Purple Arrow
            'bottom-toolbar': 'bg:#202124 fg:#E0B0FF',
        })
        
        # Dynamic Status Logic
        global ATHENA_STATE
        ATHENA_STATE = "READY"
        
        def get_bottom_toolbar():
            # Get Context Tags for display
            context_str = ""
            try:
                from core.context.context_tags import get_context_tagger
                tags = get_context_tagger().get_current_tags()
                context_str = f"{tags.time_of_day} | {tags.day_type}"
            except Exception:
                context_str = "..."
            
            if ATHENA_STATE == "THINKING":
                status_style = 'style="bg:#BF40BF fg:#FFFFFF"' # Neon status
                status_text = "Thinking 🧠"
            else:
                status_style = 'style="bg:#202124 fg:#E0B0FF"' # Default status
                status_text = "Ready 🔮"
                
            return HTML(f' <b>User:</b> Drew  |  <b>Context:</b> <style fg="#E0B0FF">{context_str}</style>  |  <b>Status:</b> <span {status_style}> {status_text} </span> ')

        # Gradient Lexer for Dynamic Typing Colors
        # Gradient Lexer for Dynamic Typing Colors
        from prompt_toolkit.lexers import Lexer
        
        class GradientLexer(Lexer):
            def lex_document(self, document):
                text = document.text
                length = len(text)
                if length == 0:
                    return lambda i: []

                def hex_to_rgb(h):
                    h = h.lstrip('#')
                    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                
                def rgb_to_hex(rgb):
                    return '#{:02x}{:02x}{:02x}'.format(*[int(c) for c in rgb])

                # Google Blue (#4285F4) -> Deep Purple (#8F00FF) -> Cyan (#00BCD4)
                start_rgb = hex_to_rgb('4285F4')
                end_rgb = hex_to_rgb('00BCD4')

                def get_line(lineno):
                    processed = []
                    line_text = document.lines[lineno]
                    
                    for i, char in enumerate(line_text):
                        # Calculate gradient factor based on position in total text
                        # Makes it "slowly transform" as you type
                        factor = min(1.0, i / max(10, length)) 
                        
                        r = start_rgb[0] + (end_rgb[0] - start_rgb[0]) * factor
                        g = start_rgb[1] + (end_rgb[1] - start_rgb[1]) * factor
                        b = start_rgb[2] + (end_rgb[2] - start_rgb[2]) * factor
                        
                        color_hex = rgb_to_hex((r, g, b))
                        processed.append((color_hex, char))
                        
                    return processed
                return get_line
                
        session = PromptSession(
            completer=completer, 
            style=style,
            complete_while_typing=True,
            bottom_toolbar=get_bottom_toolbar,
            lexer=GradientLexer() # Apply the gradient typing effect
        )

    # --- ATHENA 2.0 INITIALIZATION ---
    try:
        from core.memory.manager import MemoryManager
        from core.orchestrator.context_slate import ContextSlateBuilder
        from core.interventions.engine import InterventionEngine
        from core.pattern_engine.modes import ModeCalculator
        
        console.print("[dim]🧠 Loading Fluid Memory & Pattern Engines...[/dim]")
        
        # Initialize
        mem_manager = MemoryManager()
        ctx_builder = ContextSlateBuilder(mem_manager)
        intervention_engine = InterventionEngine()
        mode_calc = ModeCalculator() # Placeholder for real signal inputs
        
        # Global State for 2.0
        active_modes = [] # Will be updated by signals
        
        console.print("[dim]✅ Athena 2.0 Core Active[/dim]")
        
    except ImportError as e:
        console.print(f"[red]⚠️ DEGRADED MODE: {e}[/red]")
        console.print("[yellow]Memory/pattern features OFFLINE. Possible fixes:[/yellow]")
        if "supabase" in str(e).lower():
            console.print("[dim]  → pip install supabase[/dim]")
        else:
            console.print(f"[dim]  → Check module: {str(e).split()[-1]}[/dim]")
        console.print("[dim]  → Verify SUPABASE_URL and SUPABASE_KEY in .env[/dim]")
        ctx_builder = None
        intervention_engine = None

    # Main input loop
    try:
        while True:
            try:
                # 1. Routine Coach (Interventions)
                if intervention_engine:
                    # Mock signals for now (would come from real sensors)
                    # For demo: randomly trigger autopilot if late night
                    import datetime
                    hr = datetime.datetime.now().hour
                    signals = {"late_night_minutes": 65 if hr < 5 else 0}
                    
                    # Recalculate Modes
                    active_mode_scores = mode_calc.compute_modes(signals)
                    active_modes = [m.mode for m in active_mode_scores]
                    
                    # Generate Nudge
                    nudge = intervention_engine.generate_nudge(active_mode_scores)
                    if nudge:
                        console.print(Panel(
                            f"[bold yellow]💡 {nudge['message']}[/bold yellow]\n[dim]{nudge['reason']}[/dim]", 
                            title="Routine Coach",
                            border_style="yellow"
                        ))

                user_input = ""
                if HAS_PROMPT_TOOLKIT and session:
                    # Interactive prompt with autocomplete (Purple Theme)
                    user_input = session.prompt([
                        ('class:prompt', 'ATHENA'),
                        ('class:arrow', ' > '),
                    ], style=style)
                else:
                    # Fallback standard prompt
                    console.print("[bold #BF40BF]ATHENA[/bold #BF40BF] [#800080]>[/#800080] ", end="")
                    user_input = input()
                
                # ============================================================
                # NEW ORCHESTRATOR HOOK (2025 Architecture)
                # ============================================================
                # If new orchestrator is enabled, try it first
                if NEW_ORCHESTRATOR_ENABLED:
                    orchestrator_response = try_new_orchestrator(user_input)
                    if orchestrator_response is not None:
                        # Response handled by new orchestrator
                        from rich.markdown import Markdown
                        console.print(Markdown(orchestrator_response))
                        continue  # Skip legacy processing
                
                # 2. Context Injection & Semantic Routing
                # Only inject context for Chat, not Commands
                if not user_input.strip().startswith("/"):
                    # Enrich with Fluid Memory if available
                    final_input = user_input
                    if ctx_builder:
                        slate = ctx_builder.build_slate(user_input, active_modes)
                        final_input = f"<SYSTEM_CONTEXT>\n{slate}\n</SYSTEM_CONTEXT>\n\n{user_input}"
                    
                    # A. HARD ROUTING (Deterministic - runs BEFORE LLM)
                    # This prevents "analyze data folder" from going to web research
                    handled = False
                    try:
                        from core.orchestrator.tool_registry import get_tool_registry
                        registry = get_tool_registry()
                        matched_tool = registry.match_routing_trigger(user_input, surface="terminal")
                        
                        if matched_tool:
                            # Local Data Analyzer - highest priority for file operations
                            if matched_tool.name == "local_data_analyzer":
                                console.print("[bold cyan]📊 Analyzing local data...[/bold cyan]")
                                from agents.local_data_analyzer.agent import run_local_data_analysis
                                result = run_local_data_analysis(user_input)
                                console.print(Markdown(result))
                                handled = True
                            
                            # Telegram Notifier - distinct from calendar
                            elif matched_tool.name == "telegram_notifier":
                                console.print("[bold cyan]📱 Scheduling Telegram reminder...[/bold cyan]")
                                # Extract time and message from user input
                                import re
                                from datetime import datetime
                                import pytz
                                
                                # Parse time (e.g., "4pm", "16:00")
                                time_match = re.search(r'(\d{1,2})(:\d{2})?\s*(am|pm)?', user_input, re.IGNORECASE)
                                msg_match = re.search(r'(to|reminder[:\s]+|about[:\s]+|that[:\s]+)(.+?)(?:\s+at\s+|$)', user_input, re.IGNORECASE)
                                
                                if time_match:
                                    hour = int(time_match.group(1))
                                    if time_match.group(3) and time_match.group(3).lower() == 'pm' and hour < 12:
                                        hour += 12
                                    
                                    reminder_msg = msg_match.group(2).strip() if msg_match else "Reminder"
                                    tz = pytz.timezone("America/Chicago")
                                    scheduled = datetime.now(tz).replace(hour=hour, minute=0, second=0)
                                    
                                    console.print(f"[green]✓ Telegram reminder scheduled for {scheduled.strftime('%I:%M %p')} CT[/green]")
                                    console.print(f"[dim]   Message: \"{reminder_msg}\"[/dim]")
                                    
                                    # TODO: Actually schedule via TelegramService.schedule_reminder when implemented
                                    from services.telegram_service import get_telegram_service
                                    ts = get_telegram_service()
                                    if ts.is_configured:
                                        # For now, send immediately with time note
                                        ts.send_text(f"⏰ **Reminder Scheduled**\nAt {scheduled.strftime('%I:%M %p')} CT:\n{reminder_msg}")
                                else:
                                    console.print("[yellow]Please specify a time (e.g., 'at 4pm')[/yellow]")
                                handled = True
                            
                            # Calendar - only for explicit calendar requests
                            elif matched_tool.name == "calendar_scheduler":
                                console.print(f"[bold green]📅 Creating calendar event...[/bold green]")
                                # Fall through to let existing calendar logic handle
                                handled = False  # Let LLM router extract event details
                            
                            # Tool unavailable
                            elif not registry.is_available(matched_tool.name):
                                console.print(f"[yellow]{registry.get_unavailable_message(matched_tool.name)}[/yellow]")
                                handled = True
                    except ImportError:
                        pass  # ToolRegistry not available, continue to LLM router
                    
                    # B. Semantic Router Logic (LLM-based - runs only if not hard-routed)
                    if not handled and router and context_stack:
                        with console.status("[bold #E0B0FF]🧠 Thinking...[/bold #E0B0FF]", spinner="dots"):
                            try:
                                # 1. Resolve References
                                active_ref = context_stack.resolve_reference("terminal", user_input)
                                
                                # 2. History
                                context_stack.push_entity("terminal", "USER_MSG", user_input)
                                dialogue_history = [{"role": "user", "content": user_input}] # Simplified history
                                
                                # 3. Route
                                route_result = router.route(user_input, dialogue_history, active_reference=active_ref)
                                intent = route_result.get("intent")
                                slots = route_result.get("slots", {})
                                
                                # 4. Execute High-Confidence Intents
                                if intent == "email_search":
                                    q = slots.get("query", "")
                                    if active_ref and "from" in active_ref: q += f" from:{active_ref['from']}"
                                    
                                    console.print(f"[cyan]🔍 Auto-Search: {q}[/cyan]")
                                    from services.google_service import get_google_service
                                    res = get_google_service().search_transaction_emails(days=slots.get("days_back", 7))
                                    
                                    if res:
                                        context_stack.push_result_set("terminal", "emails", res)
                                        console.print(f"[green]✓ Found {len(res)} emails.[/green]")
                                        for i, item in enumerate(res, 1):
                                            console.print(f"[bold]{i}.[/bold] {item.get('subject')}")
                                    else:
                                        console.print("[yellow]No results.[/yellow]")
                                    handled = True
                                    
                                elif intent == "schedule_event":
                                    console.print(f"[bold green]📅 Scheduling: {slots}[/bold green]")
                                    handled = True
                                    
                                elif intent == "research_topic":
                                    topic = slots.get("query")
                                    if not topic and active_ref: topic = active_ref.get("subject")
                                    console.print(f"[bold blue]🌐 Researching: {topic}[/bold blue]")
                                    handled = True
                                    
                            except Exception as e:
                                console.print(f"[red]Router Error: {e}[/red]")
                    
                    if not handled:
                         # JARVIS COMMAND INTERCEPT
                         if final_input.strip().startswith("/jarvis") or final_input.strip().startswith("/redact"):
                             parts = final_input.split()
                             cmd = parts[0]
                             target = parts[1] if len(parts) > 1 else ""
                             if not target:
                                 console.print("[yellow]Usage: /jarvis <target>[/yellow]")
                             else:
                                 redact_flag = "--redact" if cmd == "/redact" else ""
                                 command_line = f"python agents/jarvis_runner.py {target} {redact_flag}"
                                 os.system(command_line) # Simple passthrough
                                 
                         else:
                             process_command(final_input) # Legacy Fallback
                else:
                    if user_input.strip().startswith("/jarvis") or user_input.strip().startswith("/redact"):
                        parts = user_input.split()
                        cmd = parts[0]
                        target = parts[1] if len(parts) > 1 else ""
                        if not target:
                            console.print("[yellow]Usage: /jarvis <target>[/yellow]")
                        else:
                             redact_flag = "--redact" if cmd == "/redact" else ""
                             command_line = f"python agents/jarvis_runner.py {target} {redact_flag}"
                             os.system(command_line)
                    else:
                        process_command(user_input) # Commands /...
                
            except KeyboardInterrupt:
                console.print("\n[cyan]Use /exit to quit properly[/cyan]")
                continue
                
    except EOFError:
        console.print("\n[cyan]👋 ATHENA signing off.[/cyan]\n")
        sys.exit(0)

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
