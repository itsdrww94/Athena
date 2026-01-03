#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      A T H E N A   R E M O T E                                ║
║                     Telegram Satellite Bot System                             ║
║                                                                               ║
║  "The Satellite" - Remote access to Athena via Telegram                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Author: Project Athena
Description: Telegram bot that polls for commands and executes agents remotely.

Security: Only responds to whitelisted user IDs (TELEGRAM_CHAT_ID in .env)
"""

import os
import sys
import asyncio
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
AGENTS_DIR = BASE_DIR / "agents"

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Security: Whitelist of allowed user IDs (only your ID)
ALLOWED_USER_IDS = [TELEGRAM_CHAT_ID] if TELEGRAM_CHAT_ID else []

# =============================================================================
# NEW ORCHESTRATOR INTEGRATION (2025 Architecture)
# =============================================================================
NEW_ORCHESTRATOR_ENABLED = os.getenv("ATHENA_USE_NEW_ORCHESTRATOR", "0") == "1"

async def try_new_orchestrator_async(user_input: str, user_id: str, interface: str = "telegram") -> Optional[str]:
    """
    Attempt to process input through the new orchestrator (async wrapper).
    """
    if not NEW_ORCHESTRATOR_ENABLED:
        return None
    
    try:
        # Run synchronous orchestrator in thread pool to avoid blocking async loop
        from core.app import run_athena
        import asyncio
        from functools import partial
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            partial(
                run_athena, 
                input_message=user_input, 
                interface=interface, 
                user_id=user_id,
                session_id=f"tg_{user_id}"
            )
        )
        return response
    except Exception as e:
        print(f"⚠️ New orchestrator error: {e}")
        return None


# =============================================================================
# AGENT REGISTRY
# =============================================================================

# Maps command names to agent scripts
AGENT_REGISTRY = {
    # =========================================================================
    # PHASE 2: FINANCE DIVISION
    # =========================================================================
    "finance": {
        "script": "agents/finance_manager.py",
        "description": "💰 Log expenses and check budget status",
        "usage": "/finance log 25.50 Food \"Lunch\"\n/finance status\n/finance history 7"
    },
    "scan": {
        "script": "agents/transaction_hunter.py",
        "description": "📧 Scan emails for transactions",
        "usage": "/scan (scans last 7 days)\n/scan --days 14"
    },
    "deals": {
        "script": "agents/deal_sniper.py",
        "description": "🎯 Check for deals on your watchlist",
        "usage": "/deals (scan sources)\n/deals list (show watchlist)"
    },
    
    # =========================================================================
    # PHASE 3: INTEL DIVISION
    # =========================================================================
    "news": {
        "script": "agents/news_brief.py",
        "description": "📰 Daily news briefing",
        "usage": "/news (full brief)\n/news defranco (Philip DeFranco)\n/news tech"
    },
    "events": {
        "script": "agents/msp_scout.py",
        "description": "🏙️ Minneapolis events finder",
        "usage": "/events (all)\n/events --category tech"
    },
    
    # =========================================================================
    # PHASE 4: LIFEOS DIVISION
    # =========================================================================
    "movies": {
        "script": "agents/cinema_companion.py",
        "description": "🎬 Movie & TV tracker (TMDB)",
        "usage": "/movies trending\n/movies search Dune"
    },
    "health": {
        "script": "agents/health_sync.py",
        "description": "🏥 Sleep & activity tracker",
        "usage": "/health summary\n/health sleep"
    },
    "pets": {
        "script": "agents/vet_manager.py",
        "description": "🐱 Sushi & Astro care tracker",
        "usage": "/pets status\n/pets check"
    },
    
    # =========================================================================
    # PHASE 5: RED ALERT DIVISION
    # =========================================================================
    "medic": {
        "script": "agents/medic.py",
        "description": "🏥 System health monitor",
        "usage": "/medic check\n/medic repair network"
    },
    "omega": {
        "script": "agents/protocol_omega.py",
        "description": "🔴 Emergency protocol (Dead Man's Switch)",
        "usage": "/omega status\n/omega panic"
    },
    
    # =========================================================================
    # DIVISION V: EXPANSION (GOD MODE)
    # =========================================================================
    "browse": {
        "script": "agents/web_surfer.py",
        "description": "👁️ Universal browser agent (vision-powered)",
        "usage": '/browse --url "https://pinterest.com" --goal "Find recipes" --visible'
    },
    "factory": {
        "script": "agents/agent_factory.py",
        "description": "🏭 Build new agents with Claude AI",
        "usage": '/factory --task "Get crypto prices"'
    },
    "ingest": {
        "script": "agents/dna_ingest.py",
        "description": "🧬 Digital DNA - ingest personal data for profile",
        "usage": "/ingest (all files)\n/ingest --type photos\n/ingest --dry-run"
    },
    "dj": {
        "script": "agents/dj_booth.py",
        "description": "🎵 DJ Booth - Control Spotify playback",
        "usage": "/dj --mode focus\n/dj --device speaker\n/dj --recommend"
    },
    "recall": {
        "script": "agents/archive_search.py",
        "description": "🧠 Archive Search - Search your ChatGPT history",
        "usage": '/recall --query "fix python path"'
    },
    "notebook": {
        "script": "agents/notebooklm/agent.py",
        "description": "📒 Google NotebookLM Agent (Vision)",
        "usage": '/notebook create "Name"\n/notebook source "URL"\n/notebook query "Q"'
    },
    "notion": {
        "script": "agents/notion/agent.py",
        "description": "📝 Notion Agent - Manage Expenses, Journal, and Pages",
        "usage": '/notion analyze --target "Goals"\n/notion journal --content "Text"'
    },
    
    # =========================================================================
    # PHASE 6: SUPER AGENTS (JARVIS)
    # =========================================================================
    "jarvis": {
        "script": "agents/jarvis_runner.py",
        "description": "🔍 JARVIS - OSINT & Verification Suite",
        "usage": "/jarvis <target> [--redact]"
    },
    
    # =========================================================================
    # HAKARI DIVISION (SPORTSBOOK MANAGER)
    # =========================================================================
    "fever": {
        "script": "agents/parlay/agent.py",
        "description": "🔥 Hakari: Detect Jackpots and Fever",
        "usage": "/fever (scans for mispriced lines)"
    },
    "bag_watch": {
        "script": "agents/parlay/agent.py",
        "description": "💰 Hakari: Scan for Contract Incentives",
        "usage": "/bag_watch (scans for near-miss bonuses)"
    },
    "ref_report": {
        "script": "agents/parlay/agent.py",
        "description": "🦓 Hakari: Referee Assignments & Whistle Index",
        "usage": "/ref_report (analyzes crew bias)"
    },
    "vet_fade": {
        "script": "agents/parlay/agent.py",
        "description": "👴 Hakari: Identify Tired Veterans (B2B)",
        "usage": "/vet_fade (lists Age 33+ on 0 days rest)"
    },
    "domain": {
        "script": "agents/parlay/agent.py",
        "description": "🧠 Hakari: Domain Expansion (Generate Slip)",
        "usage": "/domain (generates high-confidence flex play)"
    },
    "audit": {
        "script": "agents/parlay/agent.py",
        "description": "📉 Hakari: Post-Mortem Analysis",
        "usage": "/audit (analyzes yesterday's results)"
    },
    
    # =========================================================================
    # BUILT-IN COMMANDS
    # =========================================================================
    "look": {
        "script": None,  # Built-in command
        "description": "👁️ Capture and analyze screen",
        "usage": "/look [optional query]"
    },
    "status": {
        "script": None,  # Built-in command
        "description": "🖥️ System status check",
        "usage": "/status"
    },
}



# =============================================================================
# TELEGRAM SERVICE (Import existing service)
# =============================================================================

# Add parent to path for imports
sys.path.insert(0, str(BASE_DIR))

try:
    from services.telegram_service import TelegramService, TelegramMessage
    HAS_TELEGRAM_SERVICE = True
except ImportError:
    HAS_TELEGRAM_SERVICE = False
    print("⚠️  telegram_service.py not found. Run from Athena_Project directory.")


# =============================================================================
# BOT LOGIC
# =============================================================================

class AthenaRemote:
    """
    Athena Remote - Telegram Bot Interface
    
    Features:
    - Polls for new messages via getUpdates
    - Executes agents via subprocess
    - Returns output to user
    - Strict user whitelist for security
    """
    
    def __init__(self):
        self.telegram = TelegramService() if HAS_TELEGRAM_SERVICE else None
        self.last_update_id = 0
        self.running = False
        self.pending_image = None # Track last uploaded image for analysis commands
    
    @property
    def is_ready(self) -> bool:
        """Check if bot is properly configured."""
        if not self.telegram:
            return False
        if not self.telegram.is_configured:
            return False
        if not ALLOWED_USER_IDS:
            return False
        return True
    
    def is_authorized(self, chat_id: str) -> bool:
        """Check if user is authorized."""
        return str(chat_id) in ALLOWED_USER_IDS
    
    async def handle_message(self, msg: TelegramMessage) -> None:
        """
        Process incoming message and route to appropriate handler.
        
        Security: Ignores messages from unauthorized users.
        """
        # Security check
        if not self.is_authorized(msg.chat_id):
            print(f"⚠️  Unauthorized message from {msg.sender} ({msg.chat_id})")
            return
        
        text = msg.text.strip()
        
        # 1. Handle Photo Uploads (Stateful)
        if msg.has_photo and msg.photo_file_id:
            self.pending_image = msg.photo_file_id
            print(f"📸 Image received from {msg.sender}. Holding in state.")
            
            # If no caption, just acknowledge and wait
            if not text:
                await self.telegram.send_text(
                    "📸 **Image Received.**\n\n"
                    "I'm holding this image context.\n"
                    "Reply with a command to analyze it:\n"
                    "• `/fever` - Check for Jackpots\n"
                    "• `/look` - General Vision\n"
                    "• `/scan` - Extract Receipts",
                    msg.chat_id,
                    parse_mode="Markdown"
                )
                return
        
        # Ignore empty messages (if no photo)
        if not text and not msg.has_photo:
            return
        
        print(f"📩 Message from {msg.sender}: {text}")
        
        # Show typing indicator
        await self.telegram.send_typing_action(msg.chat_id)

        # ============================================================
        # NEW ORCHESTRATOR HOOK (2025 Architecture)
        # ============================================================
        if NEW_ORCHESTRATOR_ENABLED:
            response = await try_new_orchestrator_async(text, msg.sender)
            if response:
                await self.telegram.send_text(response, msg.chat_id, parse_mode="Markdown")
                return

        
        # Route command or chat
        if text.startswith("/"):
            await self.handle_command(msg)
        else:
            await self.handle_chat(msg)
    
    async def handle_command(self, msg: TelegramMessage) -> None:
        """Route /commands to appropriate agents."""
        text = msg.text.strip()
        parts = text.split(maxsplit=1)
        command = parts[0].lower().lstrip("/")
        args = parts[1] if len(parts) > 1 else ""
        
        # Built-in commands
        if command == "start":
            await self.cmd_start(msg)
        elif command == "help":
            await self.cmd_help(msg)
        elif command == "status":
            await self.cmd_status(msg)
        elif command == "ping":
            await self.cmd_ping(msg)
        elif command == "gif":
            # /gif happy - sends a random GIF matching the keyword
            await self.cmd_gif(args, msg)
        elif command == "backup":
            # /backup - backup memory to Google Cloud Storage
            await self.cmd_backup(msg)
        elif command == "tutorial":
            # /tutorial - show all commands with descriptions
            await self.cmd_tutorial(msg)
        elif command in AGENT_REGISTRY:
            await self.run_agent(command, args, msg)
        elif command == "build":
            # Direct factory invocation: /build scrape crypto prices
            await self.trigger_factory(args, msg)
        else:
            # Unknown command -> TRIGGER THE FACTORY
            await self.handle_unknown_command(command, args, msg)
    
    async def handle_unknown_command(self, command: str, args: str, msg: TelegramMessage) -> None:
        """
        GOD MODE: When an unknown command is called, offer to build it.
        """
        # Check if agent file exists on disk (might not be in registry)
        agent_path = AGENTS_DIR / f"{command}.py"
        
        if agent_path.exists():
            # Agent exists but not in registry - just run it
            await self.telegram.send_text(f"🔧 Found `{command}.py` - running...", msg.chat_id)
            await self.run_dynamic_agent(command, args, msg)
        else:
            # Agent doesn't exist - offer to build
            await self.telegram.send_text(
                f"🤖 Agent `/{command}` not found.\n\n"
                f"*Should I build it using Claude AI?*\n\n"
                f"Reply with:\n"
                f"• `/build {command} [description]` to create it\n"
                f"• Or just chat naturally",
                msg.chat_id
            )
    
    async def trigger_factory(self, task: str, msg: TelegramMessage) -> None:
        """
        Trigger the Agent Factory to build a new agent.
        Usage: /build check_crypto Get current ETH price from CoinGecko
        """
        if not task.strip():
            await self.telegram.send_text(
                "🏭 **Agent Factory**\n\n"
                "Usage: `/build [name] [description]`\n\n"
                "Examples:\n"
                "• `/build check_crypto Get ETH price`\n"
                "• `/build server_status Check if my server is up`",
                msg.chat_id
            )
            return
        
        # Parse: first word might be agent name, rest is description
        parts = task.split(maxsplit=1)
        
        if len(parts) == 1:
            # Just a description, auto-name it
            agent_name = None
            description = parts[0]
        else:
            # First word is name, rest is description
            agent_name = parts[0]
            description = parts[1]
        
        await self.telegram.send_text(
            f"🏭 **Building agent...**\n\n"
            f"📋 Task: {description}\n"
            f"🤖 Using Claude 3.5 Sonnet\n\n"
            f"_This may take 10-30 seconds..._",
            msg.chat_id
        )
        
        try:
            # Run factory
            cmd = [sys.executable, str(BASE_DIR / "agents" / "agent_factory.py")]
            cmd.extend(["--task", description])
            if agent_name:
                cmd.extend(["--name", agent_name])
            cmd.append("--run")  # Auto-run after building
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(BASE_DIR)
            )
            
            output = result.stdout.strip() or result.stderr.strip()
            
            if "Agent ready at" in output or result.returncode == 0:
                await self.telegram.send_text(
                    f"✅ **Agent built successfully!**\n\n"
                    f"```\n{output[-2000:]}\n```",
                    msg.chat_id,
                    parse_mode="Markdown"
                )
            else:
                await self.telegram.send_text(
                    f"⚠️ Factory output:\n```\n{output[-1500:]}\n```",
                    msg.chat_id,
                    parse_mode="Markdown"
                )
                
        except subprocess.TimeoutExpired:
            await self.telegram.send_text("⏰ Factory timed out (60s limit)", msg.chat_id)
        except Exception as e:
            await self.telegram.send_text(f"❌ Factory error: {e}", msg.chat_id)
    
    async def run_dynamic_agent(self, name: str, args: str, msg: TelegramMessage) -> None:
        """Run an agent that exists on disk but not in registry."""
        agent_path = AGENTS_DIR / f"{name}.py"
        
        try:
            cmd = [sys.executable, str(agent_path)]
            if args:
                cmd.extend(args.split())
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(BASE_DIR)
            )
            
            output = result.stdout.strip() or result.stderr.strip() or "✅ Completed"
            if len(output) > 4000:
                output = output[:4000] + "\n\n... (truncated)"
            
            await self.telegram.send_text(f"```\n{output}\n```", msg.chat_id, parse_mode="Markdown")
            
        except subprocess.TimeoutExpired:
            await self.telegram.send_text("⏰ Agent timed out", msg.chat_id)
        except Exception as e:
            await self.telegram.send_text(f"❌ Error: {e}", msg.chat_id)
    
    async def handle_chat(self, msg: TelegramMessage) -> None:
        """Send natural language to Gemini for processing with memory context."""
        
        # --- SMART ROUTING (HAKARI) ---
        # Intercept parlay-related intents and route to agent
        routing_result = await self.check_for_smart_routing(msg)
        if routing_result:
            return
        
        try:
            from google import genai
            
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Get memory context (user profile + past conversations)
            memory_context = ""
            memory = None
            try:
                from services.memory_core import get_memory
                memory = get_memory()
                # Cloud Archival is handled inside log_interaction now
                memory_context = memory.get_full_context(chat_limit=5)
            except Exception:
                pass
            
            # Build prompt with context
            system_prompt = """You are Athena, a Personal Super Agentic System.
You communicate via Telegram. Be concise, direct, and helpful.
You have access to various agents: finance, news, deals, movies, health, etc.
If asked about capabilities, mention /help.

**MEMORY & CONTEXT:**
If the user references past events or preferences, use the context provided below.
If you learn new facts, they will be auto-extracted by the system."""
            
            if memory_context:
                system_prompt += f"\n\n{memory_context}"
            
            # Use Gemini 3.0 Pro for maximum reasoning
            response = client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=f"{system_prompt}\n\nUser: {msg.text}"
            )
            
            reply = response.text if response.text else "I couldn't generate a response."
            await self.telegram.send_text(reply, msg.chat_id)
            
            # Log interaction to memory (v3.0) -> This triggers Supabase + Cloud + Extraction
            if memory:
                try:
                    memory.log_interaction(
                        user_input=msg.text,
                        athena_response=reply[:5000],
                        source="telegram"
                    )
                except Exception:
                    pass
            
        except Exception as e:
            await self.telegram.send_text(f"❌ Error: {e}", msg.chat_id)
    
    async def check_for_smart_routing(self, msg: TelegramMessage) -> bool:
        """
        Detect simple intents and route to agents automatically.
        Returns True if routed, False if not.
        """
        text = msg.text.lower().strip()
        
        # HAKARI (PARLAY) TRIGGERS
        # "find me a parlay", "build a slip", "parlay details" -> /domain (Generator)
        if any(w in text for w in ["parlay", "bet slip", "build a bet", "generate a slip", "find a pick"]):
            await self.telegram.send_text("🧠 **Smart Route:** Redirecting to Hakari (Slip Generator)...", msg.chat_id)
            await self.run_agent("domain", "", msg) # /domain = Generate Slip
            return True
        
        # "check for jackpots", "fever check", "mispriced lines" -> /fever
        if any(w in text for w in ["jackpot", "fever", "mispriced", "bad line"]):
            await self.telegram.send_text("🔥 **Smart Route:** Redirecting to Hakari (Fever Check)...", msg.chat_id)
            await self.run_agent("fever", "", msg)
            return True

        # "bag watch", "incentives" -> /bag_watch
        if "incentive" in text or "contract bonus" in text:
             await self.telegram.send_text("💰 **Smart Route:** Redirecting to Hakari (Bag Watch)...", msg.chat_id)
             await self.run_agent("bag_watch", "", msg)
             return True

        return False

    async def run_agent(self, agent_name: str, args: str, msg: TelegramMessage) -> None:
        """
        Execute an agent script via subprocess.
        
        Error Handling: Agent crashes don't kill the bot.
        Memory: Logs all agent executions to Supabase.
        """
        agent_info = AGENT_REGISTRY.get(agent_name)
        if not agent_info or not agent_info.get("script"):
            await self.telegram.send_text(f"❌ Agent '{agent_name}' not found.", msg.chat_id)
            return
        
        script_path = BASE_DIR / agent_info["script"]
        
        if not script_path.exists():
            await self.telegram.send_text(f"❌ Agent script not found: {script_path.name}", msg.chat_id)
            return
        
        # Register agent execution in memory
        agent_id = None
        memory = None
        try:
            from services.memory_core import get_memory
            memory = get_memory()
            agent_id = memory.register_agent(
                agent_name=agent_name,
                task_description=f"/{agent_name} {args}",
                metadata={"source": "telegram", "user": msg.sender}
            )
            if agent_id:
                memory.update_agent_status(agent_id, "running")
        except Exception:
            pass
        
        try:
            # Build command with base script
            cmd = [sys.executable, str(script_path)]
            
            # === V3.0 STRATEGIST PATTERN ===
            # Get inferred preferences as arguments
            pref_args = {}
            if memory:
                pref_args = memory.get_agent_args(agent_name)
            
            # Parse user args for the agent
            if agent_name == "finance":
                # Example: /finance log 25.50 Food "desc"
                if args.startswith("log"):
                    parts = args.split(maxsplit=3)  # log, amount, category, [desc]
                    if len(parts) >= 3:
                        cmd.extend(["--action", "log"])
                        cmd.extend(["--amount", parts[1]])
                        cmd.extend(["--category", parts[2]])
                        if len(parts) > 3:
                            cmd.extend(["--description", parts[3].strip('"')])
                elif args.startswith("status"):
                    cmd.extend(["--action", "status"])
                else:
                    await self.telegram.send_text(
                        f"Usage:\n{agent_info['usage']}", 
                        msg.chat_id
                    )
                    return
            else:
                # Generic args passthrough
                if args:
                    cmd.extend(args.split())

            # 2. INJECT PENDING IMAGE (Vision)
            # If we have a pending image, download it and pass it to the agent
            if self.pending_image:
                await self.telegram.send_text("Processing attached image... 🖼️", msg.chat_id)
                import tempfile
                
                # Create temp file
                temp_dir = Path(tempfile.gettempdir())
                temp_path = temp_dir / f"athena_vision_{self.pending_image}.jpg"
                
                # Download
                if await self.telegram.download_file(self.pending_image, str(temp_path)):
                    cmd.extend(["--image", str(temp_path)])
                    print(f"Injecting image context: {temp_path}")
                else:
                    await self.telegram.send_text("⚠️ Failed to download image context.", msg.chat_id)
                
                # Consume the state
                self.pending_image = None
            
            # Add inferred preferences as arguments (Strategist passes to Soldier)
            for arg_name, arg_value in pref_args.items():
                # Don't override if user already specified
                if f"--{arg_name}" not in args:
                    cmd.extend([f"--{arg_name}", str(arg_value)])
            
            # Execute with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(BASE_DIR)
            )
            
            # Send output
            output = result.stdout.strip() or result.stderr.strip() or "✅ Command completed (no output)"
            
            # Truncate if too long for Telegram (max 4096 chars)
            if len(output) > 4000:
                output = output[:4000] + "\n\n... (truncated)"
            
            await self.telegram.send_text(f"```\n{output}\n```", msg.chat_id, parse_mode="Markdown")
            
            # Log success to memory
            if memory and agent_id:
                memory.update_agent_status(agent_id, "completed", output=output[:500])
            
            # Also log as chat for history
            if memory:
                memory.log_chat(
                    user_input=f"/{agent_name} {args}",
                    athena_response=output[:500],
                    summary=f"Ran {agent_name} agent",
                    intent="command",
                    source="telegram"
                )
            
        except subprocess.TimeoutExpired:
            await self.telegram.send_text("⏰ Agent timed out (30s limit)", msg.chat_id)
            if memory and agent_id:
                memory.update_agent_status(agent_id, "failed", error="Timeout after 30 seconds")
        except Exception as e:
            await self.telegram.send_text(f"❌ Agent error: {e}", msg.chat_id)
            print(f"Agent error: {traceback.format_exc()}")
            if memory and agent_id:
                memory.update_agent_status(agent_id, "failed", error=str(e))
    
    # =========================================================================
    # BUILT-IN COMMANDS
    # =========================================================================
    
    async def cmd_start(self, msg: TelegramMessage) -> None:
        """Welcome message."""
        welcome = """🛰️ **Athena Remote - Online**

Welcome back! I'm your personal AI satellite.

**Quick Commands:**
• `/status` - System health check
• `/help` - Show all commands
• `/finance status` - Check budget

Or just send me a message and I'll respond with AI!
"""
        await self.telegram.send_text(welcome, msg.chat_id)
    
    async def cmd_help(self, msg: TelegramMessage) -> None:
        """Show all available commands."""
        help_text = """📚 **ATHENA COMMAND REFERENCE**

**🌐 CORE SYSTEMS**
/status - 🖥️ System & Component Health
/backup - ☁️ Force Memory Backup
/medic - 🏥 System Diagnostics (Fixes errors)
/start - 🔄 Restart/Welcome

**💵 FINANCE & DEALS**
/finance log <amount> <category> [desc] - Log expense
/finance status - View budget status
/deals - 🎯 Check deal alerts
/scan - 📧 Scan emails for receipts

**📰 INTEL & LIFE**
/news - 🌍 Daily News Briefing
/events - 🏙️ Local Events (Minneapolis)
/movies trending - 🎬 Show trending movies
/health summary - 🏥 Health/Sleep metrics
/pets status - 🐱 Pet Care Tracker

**🤖 AGENT FACTORY (GOD MODE)**
/build [name] [task] - Build a NEW agent instantly
/factory --task "task description" - Advanced build
/browse --url "..." - 👁️ Vision-powered web browsing

**🛠️ UTILITIES**
/gif [keyword] - 🎬 Search/Send GIF
/help - ℹ️ Show this menu

**💬 NATURAL LANGUAGE**
Just type naturally! I'll use my Cloud Brain to help you.
_"Log $50 for gas"_ → Finance Agent
_"What's trending in tech?"_ → News Agent
"""
        await self.telegram.send_text(help_text, msg.chat_id)
    
    async def cmd_status(self, msg: TelegramMessage) -> None:
        """System status check."""
        import platform
        
        status = f"""🖥️ **Athena System Status**

• **Host:** {platform.node()}
• **OS:** {platform.system()} {platform.release()}
• **Python:** {platform.python_version()}
• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• **Uptime:** Bot is running ✅
• **Gemini:** {'✅ Configured' if GEMINI_API_KEY else '❌ Not set'}
"""
        await self.telegram.send_text(status, msg.chat_id)
    
    async def cmd_ping(self, msg: TelegramMessage) -> None:
        """Simple latency check."""
        latency = (datetime.now() - msg.timestamp).total_seconds() * 1000
        await self.telegram.send_text(f"🏓 Pong! Latency: {latency:.0f}ms", msg.chat_id)
    
    async def cmd_gif(self, query: str, msg: TelegramMessage) -> None:
        """Search and send a GIF. Usage: /gif happy"""
        if not query.strip():
            await self.telegram.send_text(
                "🎬 **GIF Search**\n\nUsage: `/gif [keyword]`\n\nExamples:\n• `/gif happy`\n• `/gif celebration`\n• `/gif thinking`",
                msg.chat_id
            )
            return
        
        result = await self.telegram.send_gif_search(query.strip(), "", msg.chat_id)
        if not result.get("ok"):
            await self.telegram.send_text(f"😕 Couldn't find a GIF for '{query}'", msg.chat_id)
    
    async def cmd_backup(self, msg: TelegramMessage) -> None:
        """Backup Athena's memory to Google Cloud Storage."""
        await self.telegram.send_text("☁️ Starting memory backup...", msg.chat_id)
        
        try:
            from services.cloud_storage import get_cloud_storage
            storage = get_cloud_storage()
            
            result = storage.backup_memory()
            
            if result:
                await self.telegram.send_text(
                    f"✅ **Backup Complete!**\n\n"
                    f"📦 Saved to: `{result}`\n\n"
                    f"Includes:\n"
                    f"• User profile\n"
                    f"• Chat history (last 1000)\n"
                    f"• Agent states\n"
                    f"• Agent registry",
                    msg.chat_id,
                    parse_mode="Markdown"
                )
            else:
                await self.telegram.send_text(
                    "⚠️ Backup saved locally (GCS not configured).\n"
                    "Set `GOOGLE_CLOUD_STORAGE_BUCKET` in .env for cloud backups.",
                    msg.chat_id
                )
                
        except Exception as e:
            await self.telegram.send_text(f"❌ Backup failed: {e}", msg.chat_id)
    
    async def cmd_tutorial(self, msg: TelegramMessage) -> None:
        """Show comprehensive tutorial with all commands."""
        tutorial = """📚 **ATHENA COMMAND TUTORIAL**

**🌐 How Athena Works:**
Athena is your personal AI operating system. You can chat naturally, or use specific commands.

---

**💵 FINANCE DIVISION:**
`/finance log 25.50 Food "Lunch"` - Log an expense
`/finance status` - Check monthly budget
`/scan` - Scan emails for receipts
`/deals` - Check deal alerts

**📰 INTEL DIVISION:**
`/news` - Daily news briefing
`/news defranco` - Philip DeFranco summary
`/events` - Minneapolis events

**🎬 LIFEOS DIVISION:**
`/movies trending` - Trending movies
`/movies search Dune` - Search for a movie
`/health summary` - Health metrics
`/pets status` - Sushi & Astro tracker

**🛠️ SYSTEM:**
`/medic check` - System diagnostics
`/backup` - Backup memory to cloud
`/status` - Quick status check

**🚀 GOD MODE:**
`/browse --url "https://site.com" --goal "Do something"` - Vision browser
`/browse --visible` - Watch browser live
`/factory --task "Build crypto tracker"` - Build new agent
`/build [name]` - Quick agent build

**💬 CHAT:**
Just type naturally! Athena will respond with AI.

---
*Type /help for quick command list*"""
        
        await self.telegram.send_text(tutorial, msg.chat_id, parse_mode="Markdown")
    
    # =========================================================================
    # MAIN POLLING LOOP
    # =========================================================================
    
    async def start(self) -> None:
        """Start the bot polling loop."""
        if not self.is_ready:
            print("❌ Bot not configured properly. Check:")
            print("   - TELEGRAM_BOT_TOKEN in .env")
            print("   - TELEGRAM_CHAT_ID in .env")
            return
        
        # Delete any existing webhook (required for polling)
        await self.telegram.delete_webhook()
        
        print("=" * 60)
        print("🛰️  ATHENA REMOTE - ONLINE")
        print("=" * 60)
        print(f"📡 Listening for messages from user: {TELEGRAM_CHAT_ID}")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        print()
        
        # Notify user that bot is online
        await self.telegram.send_text(
            "🛰️ **Athena Remote is now online!**\n\nType /help for commands.",
            TELEGRAM_CHAT_ID
        )
        
        self.running = True
        
        try:
            while self.running:
                try:
                    # Poll for updates
                    updates = await self.telegram.get_updates(
                        offset=self.last_update_id + 1 if self.last_update_id else None,
                        limit=10
                    )
                    
                    for update in updates:
                        self.last_update_id = update.get("update_id", self.last_update_id)
                        
                        # Parse and handle message
                        msg = self.telegram.parse_update(update)
                        if msg:
                            await self.handle_message(msg)
                    
                    # Small delay to avoid hammering the API
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"⚠️  Polling error: {e}")
                    await asyncio.sleep(5)  # Wait before retry
                    
        except KeyboardInterrupt:
            print("\n👋 Shutting down Athena Remote...")
            await self.telegram.send_text("🛰️ Athena Remote going offline.", TELEGRAM_CHAT_ID)
        
        self.running = False


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Launch Athena Remote bot."""
    if not HAS_TELEGRAM_SERVICE:
        print("❌ Missing telegram_service.py")
        print("   Make sure you're running from the Athena_Project directory.")
        sys.exit(1)
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)
    
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not set in .env")
        print("   Get your chat ID by messaging @userinfobot on Telegram")
        sys.exit(1)
    
    bot = AthenaRemote()
    asyncio.run(bot.start())


if __name__ == "__main__":
    main()
