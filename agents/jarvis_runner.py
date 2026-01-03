#!/usr/bin/env python3
"""
JARVIS RUNNER
Entry point for Athena CLI and Telegram Remote to invoke Jarvis.
"""

import sys
import argparse
import json
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force UTF-8 for Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from super_agents.Jarvis.core.orchestrator import JarvisOrchestrator
except ImportError:
    # Try alternative path if super_agents is in agents/
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))
        from super_agents.Jarvis.core.orchestrator import JarvisOrchestrator
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import JarvisOrchestrator: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Jarvis OSINT Runner")
    parser.add_argument("target", help="Target to investigate (email, username, etc.)")
    parser.add_argument("--redact", action="store_true", help="Redact sensitive info from output")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    args = parser.parse_args()
    
    # Configuration
    config = {
        "output_dir": "output/jarvis_reports",
        "redaction": args.redact,
        "mode": "GOD_MODE",  # UNRESTRICTED
        # "allowlist": [args.target]  # DISABLED: Allow all targets
    }
    
    print(f"[*] Initializing JARVIS (Target: {args.target})...", flush=True)
    
    try:
        print("DEBUG: Importing JarvisOrchestrator...", flush=True)
        # Re-import to ensure we catch any import-time hangs if it wasn't done at top level
        from super_agents.Jarvis.core.orchestrator import JarvisOrchestrator
        print("DEBUG: JarvisOrchestrator imported.", flush=True)

        orchestrator = JarvisOrchestrator(config)
        print("DEBUG: Orchestrator initialized. Running investigation...", flush=True)
        report = orchestrator.run_investigation(args.target)
        print("DEBUG: Investigation complete.", flush=True)
        
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            # Generate CLI Friendly Output
            print("\n" + "="*60)
            print(f"🔍 JARVIS REPORT: {args.target}")
            print("="*60)
            
            # Risk Section
            risk = report.get("risk", {})
            score = risk.get("score", 0)
            color = "\033[91m" if score > 70 else "\033[93m" if score > 40 else "\033[92m"
            reset = "\033[0m"
            print(f"\nrisk_score: {color}{score}/100{reset}")
            print(f"risk_level: {risk.get('level', 'UNKNOWN')}")
            
            # Triage Section
            triage = report.get("triage", {})
            confirmed = triage.get("confirmed", [])
            print(f"\n[+] CONFIRMED FINDINGS ({len(confirmed)}):")
            for f in confirmed:
                print(f"  - [{f.get('type')}] {f.get('value')} (Conf: {f.get('confidence')})")
            
            # Leads
            leads = triage.get("leads", [])
            print(f"\n[?] LEADS TO VERIFY ({len(leads)}):")
            for f in leads[:5]: # Show top 5
                print(f"  - [{f.get('type')}] {f.get('value')}")
            if len(leads) > 5:
                print(f"    ...and {len(leads)-5} more.")
                
            # Remediation
            pack = report.get("remediation", [])
            if pack:
                print("\n[!] RECOMMENDED ACTIONS:")
                for step in pack:
                    print(f"  - {step}")
            
            print("\n[+] Full report saved to local output directory.")
            
    except Exception as e:
        print(f"❌ JARVIS CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
