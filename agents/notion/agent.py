#!/usr/bin/env python3
"""
Notion Agent
======================
Manage Notion database entries for Finance and Journal.
"The Scribe"

Scientist Job: Turn raw requests into structured Notion records.
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.notion_service import get_notion_service, Expense
from rich.console import Console
from rich.panel import Panel

console = Console()

def print_sci(observation: str, hypothesis: str = None, recommendation: str = None, evidence: str = None):
    """Print in Scientist format."""
    console.print(f"\n[bold cyan]OBSERVATION:[/bold cyan] {observation}")
    if hypothesis:
        console.print(f"[bold yellow]HYPOTHESIS:[/bold yellow] {hypothesis}")
    if recommendation:
        console.print(f"[bold green]RECOMMENDATION:[/bold green] {recommendation}")
    if evidence:
        console.print(f"[dim]EVIDENCE: {evidence}[/dim]")

def cmd_log_expense(args):
    """Log an expense."""
    svc = get_notion_service()
    
    if not svc.is_configured:
        print_sci("Notion API key or DB ID missing.", recommendation="Check .env configuration.")
        return

    try:
        amount = float(args.amount)
    except ValueError:
        print_sci(f"Invalid amount format: {args.amount}")
        return

    expense = Expense(
        amount=amount,
        category=args.category,
        description=args.description,
        vendor=args.vendor
    )
    
    result = svc.log_expense(expense)
    
    if result.get("success"):
        print_sci(
            observation=f"Logged expense: ${amount} for {args.category} ({args.description})",
            recommendation="Check budget status to ensure you stay on track.",
            evidence=f"Page ID: {result.get('page_id')}"
        )
    else:
        print_sci(f"Failed to log expense: {result.get('error')}")

def cmd_budget_status(args):
    """Check budget status."""
    svc = get_notion_service()
    if not svc.is_configured:
        print_sci("Notion configuration missing.")
        return
        
    status = svc.get_budget_status(budget_limit=float(args.limit))
    
    obs = f"Budget Status for {status.period}:\n"
    obs += f"Spent: ${status.total_spent:.2f} / ${status.budget_limit:.2f}\n"
    obs += f"Remaining: ${status.remaining:.2f} ({100 - status.percent_used:.1f}% left)"
    
    top_cat = max(status.by_category.items(), key=lambda x: x[1]) if status.by_category else ("None", 0)
    
    hyp = None
    rec = None
    
    if status.percent_used > 90:
        hyp = "Spending velocity is CRITICAL."
        rec = "Initiate spending freeze immediately."
    elif status.percent_used > 75:
        hyp = "Approaching budget limit."
        rec = "Review upcoming discretionary expenses."
    
    print_sci(observation=obs, hypothesis=hyp, recommendation=rec)

def cmd_log_journal(args):
    """Log a journal entry."""
    svc = get_notion_service()
    if not svc.is_configured:
        print_sci("Notion configuration missing.")
        return
        
    tags = args.tags.split(",") if args.tags else []
    result = svc.log_journal_entry(content=args.content, mood=args.mood, tags=tags)
    
    if result.get("success"):
        print_sci(
            observation="Journal entry recorded successfully.",
            evidence=f"Page ID: {result.get('page_id')}"
        )
    else:
        print_sci(f"Failed to log journal: {result.get('error')}")

def cmd_analyze(args):
    """Analyze a Notion page."""
    svc = get_notion_service()
    if not svc.is_configured:
        print_sci("Notion configuration missing.")
        return

    page_id = args.id
    title_query = args.target

    # 1. Resolve Page ID
    if not page_id and title_query:
        print_sci(f"Searching for page: '{title_query}'...")
        results = svc.search_page(title_query)
        if not results:
            print_sci(f"No pages found matching '{title_query}'")
            return
        
        # Pick the best match (first one)
        page = results[0]
        page_id = page["id"]
        print_sci(f"Found page: {page['title']} (ID: {page_id})")
    
    if not page_id:
        print_sci("No Target provided. Use --target 'Title' or --id 'UUID'")
        return

    # 2. Get Content
    content = svc.get_page_content(page_id)
    
    if content:
        # Sci Output
        print_sci(
            observation=f"Content of Page '{title_query or page_id}':\n\n{content[:2000]}", 
            recommendation="Review the content above for action items.", 
            evidence=f"Page ID: {page_id}"
        )
    else:
        print_sci("Page appears empty or could not be read.")

def main():
    parser = argparse.ArgumentParser(description="Athena Notion Agent")
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    # log-expense
    p_exp = subparsers.add_parser("log-expense", help="Log an expense")
    p_exp.add_argument("--amount", required=True, help="Amount")
    p_exp.add_argument("--category", required=True, help="Category")
    p_exp.add_argument("--description", required=True, help="Description")
    p_exp.add_argument("--vendor", help="Vendor name")
    
    # budget
    p_bud = subparsers.add_parser("budget", help="Check budget")
    p_bud.add_argument("--limit", default="2000", help="Monthly limit")
    
    # journal
    p_jour = subparsers.add_parser("journal", help="Log journal entry")
    p_jour.add_argument("--content", required=True, help="Journal text")
    p_jour.add_argument("--mood", help="Current mood")
    p_jour.add_argument("--tags", help="Comma-separated tags")

    # analyze
    p_ana = subparsers.add_parser("analyze", help="Read/Analyze a page")
    p_ana.add_argument("--target", help="Page Title Search")
    p_ana.add_argument("--id", help="Direct Page UUID")
    
    args = parser.parse_args()
    
    if args.action == "log-expense":
        cmd_log_expense(args)
    elif args.action == "budget":
        cmd_budget_status(args)
    elif args.action == "journal":
        cmd_log_journal(args)
    elif args.action == "analyze":
        cmd_analyze(args)

if __name__ == "__main__":
    main()
