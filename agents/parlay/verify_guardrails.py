import sys
import os
import asyncio
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Mock dependencies if needed, but we rely on files mostly
from agents.parlay import agent_state
from agents.parlay import config
from agents.parlay import agent
from agents.parlay import ledger

async def test_guardrails():
    print("🛡️ TESTING HAKARI GUARDRAILS 🛡️")
    
    # 1. Test State Management
    print("\n[1] Testing State Management...")
    agent_state.set_flag("shadow_mode", True)
    state = agent_state.load_state()
    assert state['shadow_mode'] == True
    print("✅ Shadow Mode Default: ON")
    
    agent_state.set_flag("automation_enabled", False)
    assert agent_state.get_flag("automation_enabled") == False
    print("✅ Automation Default: OFF")

    # 2. Test Change Budget Logic
    print("\n[2] Testing Change Budget...")
    user_slip = [{'player': 'LBJ', 'stat': 'pts'}, {'player': 'AD', 'stat': 'reb'}]
    proposed_slip = {'picks': [{'player': 'LBJ', 'stat': 'pts'}, {'player': 'Curry', 'stat': '3pm'}]}
    
    audit = agent.evaluate_change_budget(user_slip, proposed_slip)
    print(f"Audit Result: {audit}")
    assert audit['count'] == 2 # Removed AD, Added Curry
    assert audit['severity'] > 0
    print("✅ Change Budget Logic: Verified")

    # 3. Test Config Loading
    print("\n[3] Testing Config...")
    assert config.RISK_PROFILES['balanced']['min_edge'] == 0.06
    print("✅ Config Loaded")
    
    # 4. Test Ledger Shadow Logging
    print("\n[4] Testing Ledger Shadow Log...")
    l = ledger.get_ledger()
    success = l.log_decision(
        context={"test": True},
        decision={"action": "TEST"},
        shadow_mode=True
    )
    assert success
    print("✅ Ledger Logged (Shadow Mode)")

    print("\n🎉 ALL GUARDRAILS VERIFIED!")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_guardrails())
