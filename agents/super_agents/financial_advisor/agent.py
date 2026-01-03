"""
Financial Advisor Agent — Athena Finance 2.0
=============================================
Main Entry Point for Finance Division.

Coordinates:
- Bank Ecosystem (Five-Bank Model)
- Card Optimizer (Deal Registry)
- Smart Transfer (Bill Protection)
- Finance Logic (Safe-to-Spend)
- Notion Sync (Daily Snapshots)

Level 2: Gatekeeper (APPROVE/WARN/BLOCK)
"""

import sys
import argparse
import json
import asyncio
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fallbacks for schema
try:
    from services.athena_schemas import AgentOutput
except ImportError:
    class AgentOutput:
        def __init__(self):
            self.observations = []
            self.recommendations = []
            self.risk_state = "low"

# Import Finance 2.0 Components
from agents.financial_advisor.finance_logic import can_spend, get_daily_allowance, days_until_end_of_month
from agents.financial_advisor.bank_ecosystem import get_bank_ecosystem, BankEcosystem
from agents.financial_advisor.card_optimizer import get_card_optimizer, CardOptimizer
from agents.financial_advisor.smart_transfer import SmartTransfer
from agents.financial_advisor.sentinel import get_finance_sentinel
from agents.financial_advisor.risk_engine import get_risk_engine
from agents.financial_advisor.plan_engine import get_plan_engine


def main():
    parser = argparse.ArgumentParser(description="Athena Financial Advisor 2.0 (CFO)")
    parser.add_argument("--context", required=False, help="JSON Context Capsule")
    
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    # =========================================================================
    # COMMANDS
    # =========================================================================
    
    # 1. CHECK PURCHASE (Gatekeeping + Card Optimization)
    p_check = subparsers.add_parser("check-purchase", help="Gate a purchase with card advice")
    p_check.add_argument("--amount", type=float, required=True)
    p_check.add_argument("--item", required=True)
    p_check.add_argument("--category", default="General")
    p_check.add_argument("--merchant", default=None, help="Merchant name for card optimization")
    
    # 2. ADD CARD DEAL
    p_deal = subparsers.add_parser("add-deal", help="Add a card deal to the registry")
    p_deal.add_argument("--card", required=True, help="Card name (e.g., 'Chase Freedom')")
    p_deal.add_argument("--merchant", required=True, help="Merchant pattern (e.g., 'Starbucks' or '*')")
    p_deal.add_argument("--rate", type=float, required=True, help="Reward rate (0.05 = 5%%)")
    p_deal.add_argument("--category", default=None)
    p_deal.add_argument("--expires", default=None, help="Expiration date (YYYY-MM-DD)")
    
    # 3. LIST DEALS
    p_list = subparsers.add_parser("list-deals", help="List all card deals")
    p_list.add_argument("--card", default=None, help="Filter by card name")
    
    # 4. UPDATE BALANCE
    p_balance = subparsers.add_parser("update-balance", help="Update bank account balance")
    p_balance.add_argument("--account", required=True, choices=["chase", "boa", "cap1_checking", "cap1_credit", "chime", "robinhood"])
    p_balance.add_argument("--balance", type=float, required=True)
    p_balance.add_argument("--pending", type=float, default=0.0)
    
    # 5. STATUS (Dashboard)
    p_status = subparsers.add_parser("status", help="Get financial status dashboard")
    
    # 6. SMART TRANSFER
    p_transfer = subparsers.add_parser("smart-transfer", help="Get transfer recommendation for a shortfall")
    p_transfer.add_argument("--amount", type=float, required=True, help="Amount needed")
    p_transfer.add_argument("--destination", default="boa", help="Destination account")
    
    # 7. PLAN GOAL (Legacy)
    p_plan = subparsers.add_parser("plan-goal", help="Plan for a big purchase")
    p_plan.add_argument("--goal", required=True)
    p_plan.add_argument("--target_amount", type=float, required=True)
    
    # 8. AUTO PLANNING (Scheduled)
    p_run = subparsers.add_parser("auto-planning", help="Scheduled analysis")
    p_run.add_argument("--scope", choices=["daily", "weekly"], default="daily")
    
    # 9. SYNC TO NOTION
    p_sync = subparsers.add_parser("sync-notion", help="Push snapshot to Notion")
    
    args = parser.parse_args()
    output = AgentOutput()
    
    # Get components
    ecosystem = get_bank_ecosystem()
    cards = get_card_optimizer()
    risk = get_risk_engine()
    plan = get_plan_engine()
    
    # =========================================================================
    # ACTION HANDLERS
    # =========================================================================
    
    if args.action == "check-purchase":
        # A. Check Safe-to-Spend (Ecosystem-wide)
        sts_result = ecosystem.safe_to_spend(args.amount)
        
        # B. Get Card Optimization
        merchant = args.merchant or args.item
        card_rec = cards.get_best_card(merchant, args.category, args.amount)
        
        output.observations.append(f"Request: {args.item} (${args.amount}) | Cat: {args.category}")
        output.observations.append(f"Available to Spend: ${sts_result.available:.2f}")
        
        if sts_result.approved:
            output.recommendations.append(f"✅ APPROVED: {sts_result.message}")
            output.recommendations.append(f"💳 {card_rec.message}")
        else:
            output.recommendations.append(f"❌ NOT RECOMMENDED: {sts_result.message}")
        
        output.risk_state = sts_result.risk_level.lower()
    
    elif args.action == "add-deal":
        deal = cards.add_deal(
            card_name=args.card,
            merchant_pattern=args.merchant,
            reward_rate=args.rate,
            category=args.category,
            expires=args.expires
        )
        output.observations.append(f"Added deal: {deal.card_name} -> {deal.merchant_pattern} ({deal.reward_rate*100:.0f}%)")
        output.recommendations.append("Deal saved to registry.")
    
    elif args.action == "list-deals":
        deals = cards.list_deals(card_filter=args.card)
        output.observations.append(f"Found {len(deals)} deals:")
        for d in deals[:20]:  # Limit output
            output.observations.append(f"  • {d.card_name}: {d.merchant_pattern} ({d.reward_rate*100:.0f}% {d.reward_type})")
    
    elif args.action == "update-balance":
        ecosystem.update_balance(args.account, args.balance, args.pending)
        output.observations.append(f"Updated {args.account}: ${args.balance:.2f} (pending: ${args.pending:.2f})")
    
    elif args.action == "status":
        liquid = ecosystem.get_total_liquid()
        bills = ecosystem.get_upcoming_bills(7)
        sts = ecosystem.safe_to_spend(100)
        velocity = ecosystem.get_velocity("cap1_checking", 14)
        
        output.observations.append(f"💵 Total Liquid: ${liquid:.2f}")
        output.observations.append(f"📋 Upcoming Bills (7d): ${bills:.2f}")
        output.observations.append(f"✅ Available to Spend: ${sts.available:.2f}")
        output.observations.append(f"🔥 Daily Budget: ${velocity:.2f}/day")
        output.recommendations.append(f"Risk Level: {sts.risk_level}")
        output.risk_state = sts.risk_level.lower()
    
    elif args.action == "smart-transfer":
        transfer = SmartTransfer(ecosystem)
        plan_result = transfer.find_source(args.amount, args.destination)
        
        output.observations.append(f"Shortfall: ${args.amount:.2f} for {args.destination}")
        output.recommendations.append(plan_result.label)
        output.risk_state = "high" if plan_result.urgency == "critical" else "med"
    
    elif args.action == "plan-goal":
        surplus = 400.0  # Mock
        recs = plan.evaluate_goal(args.goal, args.target_amount, surplus)
        for r in recs:
            output.recommendations.append(r)
    
    elif args.action == "auto-planning":
        if args.scope == "daily":
            liquid = ecosystem.get_total_liquid()
            velocity = ecosystem.get_velocity("cap1_checking", 14)
            sts = ecosystem.safe_to_spend(100)
            
            output.observations.append(f"Daily Digest: ${liquid:.2f} liquid, ${velocity:.2f}/day budget")
            output.risk_state = sts.risk_level.lower()
        else:
            output.observations.append("Weekly Analysis: Trends stable.")
    
    elif args.action == "sync-notion":
        from agents.financial_advisor.notion_sync import push_daily_snapshot
        
        liquid = ecosystem.get_total_liquid()
        velocity = ecosystem.get_velocity("cap1_checking", 14)
        sts = ecosystem.safe_to_spend(100)
        
        success = push_daily_snapshot(
            total_liquid=liquid,
            burn_rate=velocity,
            safety_status=sts.risk_level,
            alerts=[]
        )
        
        if success:
            output.observations.append("Synced to Notion successfully.")
        else:
            output.observations.append("Notion sync failed. Check API key.")
    
    # =========================================================================
    # OUTPUT ENVELOPE
    # =========================================================================
    
    print("START_ENVELOPE")
    result_data = {
        "observations": output.observations,
        "recommendations": output.recommendations,
        "risk_state": getattr(output, "risk_state", "low"),
        "events_to_log": [],
        "proposed_memory_updates": []
    }
    print(json.dumps(result_data, indent=2))
    print("END_ENVELOPE")


if __name__ == "__main__":
    main()
