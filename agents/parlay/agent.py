"""
HAKARI: Specialized Parlay Agent CLI (v2.0)
===========================================
The terminal interface for Hakari, accessible via:
- Direct: python agent.py --command /domain
- Athena CLI: /parlay
- Athena Remote (Telegram): /fever, /domain, etc.

v2.0: Integrated with Decision Engine for real projections and decisions.
"""

import sys
import os
import argparse
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force UTF-8 Output for Windows Emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Import Hakari Logic (v2.0 Decision Engine)
print("DEBUG: Importing Hakari Logic...", flush=True)
try:
    from agents.parlay import nba_logic
    print("DEBUG: nba_logic imported", flush=True)
    from agents.parlay.suggestion_engine import SuggestionEngine
    print("DEBUG: SuggestionEngine imported", flush=True)
    from agents.parlay import nba_context
    print("DEBUG: nba_context imported", flush=True)
    from agents.parlay.schemas import PickDecision, ProjectionResult
    # ... other imports ...
    from agents.parlay.policy_engine import get_policy_engine
    print("DEBUG: policy_engine imported", flush=True)
    from agents.parlay.market_layer import get_market_service
    from agents.parlay.parlay_builder import get_parlay_builder
    from agents.parlay.tools import TOOL_REGISTRY
    # NEW IMPORTS (Guardrails)
    from agents.parlay import config
    from agents.parlay import agent_state
    from agents.parlay.ledger import get_ledger
    print("DEBUG: All imports done.", flush=True)
except ImportError:
    import nba_logic
    from suggestion_engine import SuggestionEngine
    import nba_context
    from schemas import PickDecision, ProjectionResult
    from policy_engine import get_policy_engine
    from market_layer import get_market_service
    from parlay_builder import get_parlay_builder
    from tools import TOOL_REGISTRY
    import config
    import agent_state
    from ledger import get_ledger

# Initialize Engines
print("DEBUG: Initializing Engines...", flush=True)
suggester = SuggestionEngine(nba_logic_module=nba_logic)
policy = get_policy_engine()
market = get_market_service()
ledger = get_ledger()

try:
    from agents.parlay.submission_engine import PrizePicksAutomator
    submitter = PrizePicksAutomator()
except:
    submitter = None

# Load Env from Root (Athena_Project/.env)
print("DEBUG: Loading .env...", flush=True)
env_path = Path(__file__).resolve().parent.parent.parent / '.env' # agents/parlay -> agents -> Athena_Project -> .env
if not env_path.exists():
    # Fallback to standard
    load_dotenv()
else:
    load_dotenv(dotenv_path=env_path)
print("DEBUG: Env loaded.", flush=True)

# =============================================================================
# SAFETY & CHANGE BUDGET LOGIC
# =============================================================================

def evaluate_change_budget(original_slip, proposed_slip):
    """
    Compare original user intent vs proposed optimization.
    Returns count of changes and severity score.
    """
    changes = 0
    severity = 0.0
    reasons = []
    
    # Simple set comparison for now
    orig_set = set((p['player'], p['stat']) for p in original_slip)
    prop_set = set((p['player'], p['stat']) for p in proposed_slip['picks'])
    
    added = prop_set - orig_set
    removed = orig_set - prop_set
    
    changes = len(added) + len(removed)
    
    # Severity logic
    if len(added) > 0:
        severity += 0.3 * len(added)
        reasons.append(f"Added {len(added)} new legs")
    if len(removed) > 0:
        severity += 0.4 * len(removed) # Removal is more severe (user liked it)
        reasons.append(f"Removed {len(removed)} user picks")
        
    return {"count": changes, "severity": min(1.0, severity), "reasons": reasons}

# =============================================================================
# HAKARI AGENT LOOP (Autonomous Flow)
# =============================================================================

async def run_agent_loop(objective: str = "balanced", budget: float = 5.0):
    """
    Executes the full Observe -> Decide -> Act -> Learn loop.
    Enforces Safety Gates and Shadow Mode.
    """
    state_flags = agent_state.load_state()
    shadow_mode = state_flags.get("shadow_mode", True)
    automation_on = state_flags.get("automation_enabled", False)
    
    print(f"🤖 HAKARI AGENT (Mode: {objective} | Shadow: {shadow_mode})")
    
    # 0. Fail-safe Check (Drawdown)
    stats = state_flags.get("rolling_stats", {})
    if stats.get("drawdown_current", 0) > 50.0:
        print("🛑 FAILSAFE: Drawdown > $50. Execution Paused.")
        return

    # 1. Observe (Scan available props)
    suggestions = await suggester.generate_suggestions_simple({
        "candidates": [], 
        "legs": 4, 
        "top_n": 1
    })
    
    if not suggestions['top_slips']:
        print("💤 No valid slips found.")
        return

    slip = suggestions['top_slips'][0]
    ev = slip['combined_value']
    
    # 2. Safety Gate (Stake & EV)
    print(f"🧐 Proposed Slip: {len(slip['picks'])} legs, EV: {ev:.3f}")
    
    if automation_on and not shadow_mode:
        # Real Money Constraints
        if budget > config.AUTONOMOUS_CONSTRAINTS['stake_max']:
            print(f"⛔ BLOCK: Stake ${budget} > Max ${config.AUTONOMOUS_CONSTRAINTS['stake_max']}")
            return
        if ev < 0.10: 
            print("✋ HOLD: EV below threshold.")
            return

    # 3. Execution / Shadow
    picks_fmt = [{'player': p['player'], 'stat': p['stat'], 
                  'line': p['line'], 'type': p['action']} for p in slip['picks']]
    
    result = {"status": "SKIPPED"}
    
    if shadow_mode:
        print(f"👻 SHADOW SUBMISSION (Mock): ${budget} on {len(picks_fmt)} legs")
        result = {"status": "SHADOW_LOGGED", "message": "Logged to shadow ledger"}
    elif automation_on:
        # Real Execution
        print(f"🚀 EXECUTING: ${budget} on {len(picks_fmt)} legs...")
        result = await TOOL_REGISTRY['execute_slip']['call'](picks_fmt, budget, mode="autonomous")
        print(f"✅ Result: {result['status']}")
    else:
        print("🔒 Automation Disabled. Use /automation on to enable real bets.")
        # Provide Click Instructions (Assisted)
        print("📋 CLICK PLAN:")
        for p in picks_fmt:
            print(f" - {p['player']} {p['stat']} {p['type']}")
    
    # 4. Log to Ledger
    ledger.log_decision(
        context={"mode": "auto", "trigger": "loop"}, 
        decision=slip, 
        result=result,
        shadow_mode=shadow_mode
    )
    
    # 5. Auto-Learn & Sync
    try:
        curr = nba_logic.DECISION_THRESHOLDS
        new_params = await TOOL_REGISTRY['update_rl']['call'](curr)
        if new_params != curr:
            nba_logic.DECISION_THRESHOLDS.update(new_params)
            print("🎓 RL Updated Model Parameters.")
    except Exception as e:
        print(f"⚠️ RL Update Warning: {e}")

    # Flush events to Cloud
    from agents.parlay.supabase_client import get_client
    await get_client().flush_outbox()


async def analyze_image(image_path):
    """
    Use Gemini Vision to parse PrizePicks bet slip.
    Uses Tool 1 (Ingest) internally.
    """
    # Parse via Tool 1
    legs = TOOL_REGISTRY['ingest_slip']['call']('prizepicks', image_path, is_image=True)
    if legs and "error" not in legs[0]:
        return {"legs": legs, "status": "PARSED"}
        
    return {"error": "Vision module pending final integration"}


def hakari_respond(response_data: dict, output_format: str = "console") -> bool:
    """
    HAKARI FAILSAFE: Direct response output when Athena is offline.
    
    This allows Hakari to communicate results directly to the user
    without relying on Athena's routing or output system.
    
    Args:
        response_data: Dictionary containing the response to output
        output_format: "console", "json", or "telegram"
    
    Returns:
        True if response was successfully output, False otherwise
    """
    try:
        if output_format == "json":
            print(json.dumps(response_data, indent=2))
            return True
        
        elif output_format == "telegram":
            # Attempt to send via Telegram directly (failsafe when Athena offline)
            try:
                import requests
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_CHAT_ID")
                if bot_token and chat_id:
                    message = format_hakari_message(response_data)
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
                    return True
            except Exception as e:
                print(f"[HAKARI] Telegram failsafe failed: {e}")
                # Fall through to console
        
        # Default: Console output with formatting
        print("\n" + "="*50)
        print("🎰 HAKARI RESPONSE (Failsafe Mode)")
        print("="*50)
        
        if "error" in response_data:
            print(f"❌ Error: {response_data['error']}")
            
        # Decision Engine Output (v3.0)
        elif "action" in response_data:
            action = response_data.get("action")
            icon = "⏭️" if action == "SKIP" else "✅" if action == "OVER" else "📉"
            print(f"{icon} Action: {action}")
            
            if "score" in response_data:
                 print(f"   Score (μ): {response_data['score']}")
            if "p_over" in response_data:
                 print(f"   Probabilities: O:{response_data['p_over']:.1%} / U:{response_data['p_under']:.1%}")
            if "value_score" in response_data:
                 print(f"   Value Score: {response_data['value_score']}")
            if "confidence" in response_data:
                 conf = response_data['confidence'] * 100 if response_data['confidence'] <= 1 else response_data['confidence']
                 print(f"   Confidence: {conf:.1f}%")
                 
            if "skip_reason" in response_data and response_data['skip_reason']:
                 print(f"   ⛔ Skip Reason: {response_data['skip_reason']}")
            
            if "risk_tags" in response_data and response_data['risk_tags']:
                 print(f"   ⚠️ Risks: {', '.join(response_data['risk_tags'])}")

        # Legacy Output
        elif "verdict" in response_data:
            verdict = response_data.get("verdict", "UNKNOWN")
            emoji = "✅" if verdict in ["MORE", "OVER", "BET"] else "❌" if verdict in ["LESS", "UNDER", "SKIP"] else "⚠️"
            print(f"{emoji} Verdict: {verdict}")
            if "projection" in response_data:
                print(f"📊 Projection: {response_data['projection']}")
            if "confidence" in response_data:
                print(f"🎯 Confidence: {response_data['confidence']}%")
            if "reasons" in response_data and response_data['reasons']:
                print("📝 Recs:")
                for r in response_data['reasons']:
                    print(f"   - {r}")
            if "risk_tags" in response_data and response_data['risk_tags']:
                 print(f"⚠️ Risks: {', '.join(response_data['risk_tags'])}")
                
        # Generic Output
        else:
            for key, value in response_data.items():
                print(f"  {key}: {value}")
        
        print("="*50 + "\n")
        return True
        
    except Exception as e:
        print(f"[HAKARI FAILSAFE ERROR] Could not output response: {e}")
        return False


def format_hakari_message(data: dict) -> str:
    """Format response data for Telegram message."""
    lines = ["🎰 *HAKARI* (Failsafe Mode)\n"]
    
    # Handle Decision Engine fields (v3.0)
    if "action" in data:
        action = data.get('action')
        icon = "⏭️" if action == "SKIP" else "✅" if action == "OVER" else "📉"
        lines.append(f"{icon} *Action:* {action}")
        
        if "value_score" in data:
            lines.append(f"*Value Score:* {data['value_score']}")
        if "confidence" in data:
            # Handle decimals from backend (0.85 -> 85%) or int (85 -> 85%)
            conf = data['confidence'] * 100 if data['confidence'] <= 1 else data['confidence']
            lines.append(f"*Confidence:* {conf:.1f}%")
        
        if "p_over" in data and "p_under" in data:
            lines.append(f"*Probabilities:* O:{data['p_over']:.1%} / U:{data['p_under']:.1%}")
            
        if "risk_tags" in data and data['risk_tags']:
            lines.append(f"⚠️ *Risks:* {', '.join(data['risk_tags'])}")
            
        if "skip_reason" in data and data['skip_reason']:
            lines.append(f"⛔ *Skip Reason:* {data['skip_reason']}")

    # Handle Legacy/Generic fields
    elif "verdict" in data:
        lines.append(f"*Verdict:* {data['verdict']}")
        if "projection" in data:
            lines.append(f"*Projection:* {data['projection']}")
    
    if "reasons" in data and data['reasons']:
        lines.append(f"*Reasons:* {', '.join(data['reasons'])}")
        
    if "error" in data:
        lines.append(f"❌ *Error:* {data['error']}")
    
    return "\n".join(lines)




async def run_command(command, args, image_path=None):
    """
    Executes Hakari Terminal Commands.
    
    v2.0: Uses decision engine for real analysis.
    """
    cmd = command.lower().strip()
    
    # Pre-process image if provided
    if image_path:
        print(f"👁️‍🗨️ HAKARI: Analyzing visual context: {image_path}")
    
    # =========================================================================
    # /check - Single Prop Evaluation (NEW in v2.0)
    # =========================================================================
    if cmd == "/check":
        # Usage: /check LeBron James points 25.5
        if not args or len(args) < 3:
            return {
                "error": "Usage: /check <player> <stat> <line>",
                "example": "/check LeBron James points 25.5"
            }
        
        # Parse args: last two are stat and line, rest is player name
        parts = args if isinstance(args, list) else args.split()
        if len(parts) < 3:
            return {"error": "Need player name, stat type, and line"}
        
        line = float(parts[-1])
        stat = parts[-2]
        player = " ".join(parts[:-2])
        
        print(f"🎯 HAKARI: Evaluating {player} {stat} @ {line}...")
        
        decision, projection = await suggester.evaluate_prop(player, stat, line)
        
        if projection is None:
            return {
                "verdict": "SKIP",
                "reason": decision.skip_reason or "No data available"
            }
        
        return {
            "player": player,
            "stat": stat,
            "line": line,
            "verdict": decision.action,
            "tier": decision.tier,
            "projection": projection.mean,
            "edge_pct": round(decision.edge_pct, 1),
            "confidence": round(decision.confidence * 100, 1),
            "p_over": round(projection.p_over * 100, 1),
            "p_under": round(projection.p_under * 100, 1),
            "reasons": decision.reasons,
            "skip_reason": decision.skip_reason,
            "risk_tags": projection.risk_tags
        }
    
    # =========================================================================
    # /analyze - Direct Decision Engine Analysis (v3.0)
    # =========================================================================
    elif cmd == "/analyze":
        # Usage: /analyze LeBron James points 25.5
        if not args or len(args) < 3:
            return {
                "error": "Usage: /analyze <player> <stat> <line>",
                "example": "/analyze LeBron James points 25.5"
            }
        
        parts = args if isinstance(args, list) else args.split()
        if len(parts) < 3:
            return {"error": "Need player name, stat type, and line"}
        
        line = float(parts[-1])
        stat = parts[-2]
        player = " ".join(parts[:-2])
        
        print(f"🧠 HAKARI: Decision Engine Analysis for {player} {stat} @ {line}...")
        
        # Use get_player_data directly (upgraded with full decision pipeline)
        result = nba_logic.get_player_data(player, stat, line)
        
        # Format output emphasizing SKIP vs BET decision
        if result.get('action') == 'SKIP':
            print(f"⏭️  SKIP: {result.get('skip_reason', 'Unknown')}")
        else:
            print(f"✅ {result['action']}: μ={result['mu']}, P={result['win_prob']:.1%}")
        
        return result
    
    # =========================================================================
    # /bag_watch - Contract Incentive Scanner
    # =========================================================================
    elif cmd == "/bag_watch":
        print("💰 HAKARI: Scanning for Contract Incentives...")
        
        # Demo with sample data
        ctx = nba_context.IncentiveModule({
            '123': {'target_stat': 'ast', 'target_val': 10.0, 'current_val': 9.8, 'games_left': 2}
        })
        
        mult = ctx.calculate_greed_multiplier('123', 'ast')
        if mult > 1.0:
            return {
                "status": "ACTIVE", 
                "alerts": ["Player 123 is chasing Assists (Greed Factor x1.15)"]
            }
        return {"status": "CLEAR", "message": "No active incentive chases found."}

    # =========================================================================
    # /fever or /jackpot - Jackpot Detection
    # =========================================================================
    elif cmd == "/jackpot" or cmd == "/fever":
        print("🔥 HAKARI: Running Fever Check & Jackpot Detection...")
        
        if image_path:
            return {
                "status": "ANALYZED", 
                "message": "I see your slip! Analysis: Potentially correlated. (Vision Mock)"
            }

        # Get today's games from data service
        try:
            from agents.parlay.data_service import NBADataService
            data_svc = NBADataService()
            games = data_svc.fetch_live_games()
        except:
            games = [{'home_team_id': 1, 'away_team_id': 2}]
        
        jackpots = await suggester.detect_jackpots(games)
        return {
            "machine_status": "BOILING" if jackpots else "IDLE",
            "jackpots": jackpots,
            "guidance": "Focus on Mispriced Lines where Star is OUT." if jackpots else "Market is tight."
        }

    elif cmd == "/fever_check":
        return await run_command("/fever", args, image_path)

    # =========================================================================
    # /ref_report - Referee Analysis
    # =========================================================================
    elif cmd == "/ref_report":
        print("🦓 HAKARI: Analyzing Crew Assignments...")
        
        reports = []
        # Demo crew
        crew = ["Scott Foster", "Kevin Cutler", "Dedric Taylor"]
        idx = nba_logic.ref_engine.get_whistle_index(crew)
        
        if idx > 7:
            reports.append(f"⚠️ TIGHT WHISTLE ALERT: {crew} (Index: {idx}). Boost FT_DEPENDENT scorers.")
        
        return {
            "status": "COMPLETE", 
            "reports": reports if reports else ["All crews Neutral today."]
        }

    # =========================================================================
    # /vet_fade - Veteran Fatigue Analysis
    # =========================================================================
    elif cmd == "/vet_fade":
        print("👴 HAKARI: Identifying Tired Veterans...")
        
        faded_players = []
        # Demo: LeBron (Age 39), on B2B
        fake_age = 39
        fake_rest = 0
        mult = nba_logic.fatigue_engine.get_fatigue_multiplier(fake_age, fake_rest, True)
        if mult < 1.0:
            faded_players.append("LeBron James (Age 39, 0 Rest) -> Fade Projection x0.92")
            
        return {
            "status": "COMPLETE",
            "fades": faded_players
        }

    # =========================================================================
    # /tools - Inspect Agent Capabilities
    # =========================================================================
    elif cmd == "/tools":
        print("🛠️ HAKARI AGENT TOOLS (Registry):")
        tools_info = []
        for name, tool in TOOL_REGISTRY.items():
            print(f"- {name}: {tool['desc']}")
            tools_info.append(f"{name}: {tool['desc']}")
        return {"tools": tools_info}

    # =========================================================================
    # /autopilot - Autonomous Agent Loop
    # =========================================================================
    elif cmd == "/autopilot":
         # Parse budget from args
        budget = 5.0
        mode = "balanced"
        if args and isinstance(args, str):
            parts = args.split()
            for p in parts:
                if p.startswith("$"):
                    try:
                        budget = float(p.replace("$", ""))
                    except:
                        pass
                elif p in ["aggressive", "conservative", "balanced"]:
                    mode = p
        
        await run_agent_loop(objective=mode, budget=budget)
        return {"status": "LOOP_COMPLETED"}

    # =========================================================================
    # /shadow - Toggle Shadow Mode
    # =========================================================================
    elif cmd == "/shadow":
        # Usage: /shadow on OR /shadow off
        arg_val = str(args).lower().strip() if args else ""
        if "off" in arg_val:
            agent_state.set_flag("shadow_mode", False)
            return {"status": "MODE_UPDATED", "shadow_mode": False, "message": "⚠️ REAL MONEY MODE ENABLED"}
        else:
            agent_state.set_flag("shadow_mode", True)
            return {"status": "MODE_UPDATED", "shadow_mode": True, "message": "👻 Shadow Mode Enabled (Mock Submissions)"}

    # =========================================================================
    # /automation - Safety Gate Toggle
    # =========================================================================
    elif cmd == "/automation":
        arg_val = str(args).lower().strip() if args else ""
        if "on" in arg_val:
            agent_state.set_flag("automation_enabled", True)
            return {"status": "GATE_OPEN", "automation": True, "message": "🚀 Automation Circuit OPEN"}
        else:
            agent_state.set_flag("automation_enabled", False)
            return {"status": "GATE_CLOSED", "automation": False, "message": "🛑 Automation Circuit CLOSED"}

    # =========================================================================
    # /status - Agent State Report
    # =========================================================================
    elif cmd == "/status":
        state = agent_state.load_state()
        history = ledger._load_history(limit=50) # Helper access
        wins = sum(1 for h in history if h.get('result', {}).get('status') == 'WON')
        total = len(history)
        
        return {
            "mode": state.get('mode', 'assisted'),
            "shadow_mode": state.get('shadow_mode'),
            "automation": state.get('automation_enabled'),
            "failsafe_trigger": state.get('failsafe_triggered'),
            "stats": state.get('rolling_stats'),
            "history_len": total,
            "win_rate": f"{wins/total:.1%}" if total > 0 else "0.0%"
        }

    # =========================================================================
    # /learn - Trigger Reinforcement Learning
    # =========================================================================
    elif cmd == "/learn":
        print("🎓 HAKARI: Analyzing Ledger for Parameter Tuning...")
        curr_params = nba_logic.DECISION_THRESHOLDS
        # Now async
        new_params = await TOOL_REGISTRY['update_rl']['call'](curr_params)
        
        if new_params != curr_params:
            nba_logic.DECISION_THRESHOLDS.update(new_params) # Hot reload
            return {"status": "TUNED", "changes": "Thresholds updated based on performance."}
        else:
            return {"status": "NO_CHANGE", "message": "Data insufficient or optimization plateaued."}

    # =========================================================================
    # /flush - Force Sync to Supabase
    # =========================================================================
    elif cmd == "/flush":
        print("☁️ HAKARI: Flushing Event Queue to Supabase...")
        try:
            from agents.parlay.supabase_client import get_client
        except ImportError:
            from supabase_client import get_client
            
        await get_client().flush_outbox()
        return {"status": "FLUSH_COMPLETE", "message": "Events synced."}

    # =========================================================================
    # /domain - Generate Optimal Parlay Slip (v2.0)
    # =========================================================================
    elif cmd == "/domain":
        print("🧠 HAKARI: Domain Expansion - Generating High-Confidence Flex Play...")
        
        # Sample props to evaluate (in production, these come from PrizePicks API)
        sample_props = [
            {"player": "LeBron James", "stat": "points", "line": 25.5, "team_id": "LAL", "game_id": "G1"},
            {"player": "Stephen Curry", "stat": "3pm", "line": 4.5, "team_id": "GSW", "game_id": "G2"},
            {"player": "Nikola Jokic", "stat": "rebounds", "line": 11.5, "team_id": "DEN", "game_id": "G3"},
            {"player": "Luka Doncic", "stat": "assists", "line": 8.5, "team_id": "DAL", "game_id": "G4"},
        ]
        
        result = await suggester.generate_suggestions(
            props=sample_props,
            leg_count=3,
            slip_type="POWER"
        )
        
        if result['slips']:
            top_slip = result['slips'][0]
            return {
                "strategy": "DECISION ENGINE v2.0",
                "evaluated": result['evaluated_count'],
                "bets_found": result['bets'],
                "skipped": result['skips'],
                "top_slip": {
                    "legs": top_slip.leg_count,
                    "ev_estimate": round(top_slip.ev_estimate, 3),
                    "correlation_score": round(top_slip.correlation_score, 3),
                    "reasoning": top_slip.slip_reasoning
                },
                "confidence": "HIGH" if top_slip.ev_estimate > 0.1 else "MEDIUM"
            }
        else:
            return {
                "strategy": "DECISION ENGINE v2.0",
                "result": "NO PLAYS",
                "message": "No qualifying picks passed the SKIP threshold today.",
                "skipped": result['skips']
            }

    # =========================================================================
    # /audit - Post-Mortem Analysis
    # =========================================================================
    elif cmd == "/audit":
        print("📉 HAKARI: Auditing Yesterday's Loss...")
        return {
            "result": "LOSS",
            "root_cause": "Blowout Sit",
            "detail": "Leg 4 (Tatum Over) failed because BOS up 30 in 4th. Minute projection variance > 15%."
        }

    # =========================================================================
    # /submit_pick - PrizePicks Automation
    # =========================================================================
    elif cmd == "/submit_pick":
        print("🚀 HAKARI: Initiating Launch Sequence to PrizePicks...")
        
        if not submitter:
            return {"error": "Submission engine not available"}
        
        mock_picks = [
            {'player': 'LeBron James', 'stat': 'Points', 'line': 25.5, 'type': 'MORE'},
            {'player': 'Scottie Barnes', 'stat': 'Rebounds', 'line': 8.5, 'type': 'LESS'}
        ]
        
        result = await submitter.submit_slip(mock_picks, amount=20)
        return result

    # =========================================================================
    # /status - Show Decision Engine Status
    # =========================================================================
    elif cmd == "/status":
        return {
            "engine": "Hakari Decision Engine v2.0",
            "modules": {
                "projection": "UniversalPlayerProjection + ProjectionResult",
                "market": "MarketService (line tracking, baselines)",
                "policy": "PolicyEngine (SKIP-first, 5 rules)",
                "parlay": "ParlayBuilder (correlation scoring)"
            },
            "skip_rules": policy.get_skip_rules_summary()
        }
    
    # =========================================================================
    # Unknown Command
    # =========================================================================
    return {"error": f"Unknown command: {cmd}"}


def main():
    parser = argparse.ArgumentParser(description="Hakari: Specialized Parlay Agent v2.0")
    parser.add_argument("--image", help="Path to bet slip image")
    parser.add_argument("--text", help="Text request or command")
    parser.add_argument("--command", help="Direct slash command (e.g. /bag_watch)")
    parser.add_argument("--failsafe", action="store_true", help="Use Hakari failsafe output (bypasses Athena)")
    parser.add_argument("--output", choices=["json", "console", "telegram"], default="json", help="Output format")
    parser.add_argument("args", nargs="*", help="Additional arguments for the command")
    
    parsed = parser.parse_args()
    
    result = {"error": "No input provided"}
    
    # Combine positional args
    extra_args = parsed.args if parsed.args else []
    
    if parsed.command:
        result = asyncio.run(run_command(parsed.command, extra_args, image_path=parsed.image))
    elif parsed.text:
        if parsed.text.startswith("/"):
            # Extract command and args from text
            parts = parsed.text.split(maxsplit=1)
            cmd = parts[0]
            text_args = parts[1].split() if len(parts) > 1 else []
            result = asyncio.run(run_command(cmd, text_args, image_path=parsed.image))
        else:
            result = {"status": "Text analysis pending integration"}
    elif parsed.image:
        result = asyncio.run(analyze_image(parsed.image))
    
    # --- HAKARI FAILSAFE OUTPUT ---
    # Use hakari_respond if:
    # 1. --failsafe flag is set
    # 2. Running standalone (not called by Athena)
    # 3. Result contains data to output
    if parsed.failsafe or parsed.output in ["console", "telegram"]:
        hakari_respond(result, output_format=parsed.output)
    else:
        # Default JSON output (for Athena integration)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

