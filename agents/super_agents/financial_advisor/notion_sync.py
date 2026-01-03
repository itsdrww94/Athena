"""
Notion Sync — Notion API Integration
=====================================
Syncs Finance data to Notion Database.

Database: "Finance Command Center"
Fields: Date, Total Liquid Cash, Burn Rate, Safety Status, Recent Alerts
"""

import os
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("athena.finance.notion")


def push_daily_snapshot(
    total_liquid: float,
    burn_rate: float,
    safety_status: str,
    alerts: List[str],
    database_id: Optional[str] = None
) -> bool:
    """
    Push daily snapshot to Notion Database.
    
    Args:
        total_liquid: Total liquid cash across all accounts
        burn_rate: Daily spending allowance
        safety_status: "Low", "Medium", or "High" risk
        alerts: List of recent alert messages
        database_id: Override for NOTION_FINANCE_DB_ID env var
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from notion_client import Client
    except ImportError:
        logger.error("notion-client not installed. Run: pip install notion-client")
        return False
    
    api_key = os.getenv("NOTION_API_KEY")
    db_id = database_id or os.getenv("NOTION_FINANCE_DB_ID")
    
    if not api_key:
        logger.error("NOTION_API_KEY not set in environment")
        return False
    
    if not db_id:
        logger.error("NOTION_FINANCE_DB_ID not set in environment")
        return False
    
    try:
        notion = Client(auth=api_key)
        
        # Format alerts as rich text
        alerts_text = "\n".join(alerts) if alerts else "No alerts"
        
        # Create the page
        notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "Date": {
                    "date": {
                        "start": datetime.now().isoformat()[:10]
                    }
                },
                "Total Liquid Cash": {
                    "number": total_liquid
                },
                "Burn Rate": {
                    "number": round(burn_rate, 2)
                },
                "Safety Status": {
                    "select": {
                        "name": safety_status
                    }
                },
                "Recent Alerts": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": alerts_text[:2000]  # Notion limit
                            }
                        }
                    ]
                }
            }
        )
        
        logger.info(f"Pushed daily snapshot to Notion: ${total_liquid:.2f} liquid, {safety_status} risk")
        return True
        
    except Exception as e:
        logger.error(f"Failed to push to Notion: {e}")
        return False


def get_recent_snapshots(limit: int = 7, database_id: Optional[str] = None) -> List[dict]:
    """
    Fetch recent snapshots from Notion for trend analysis.
    
    Args:
        limit: Number of recent entries to fetch
        database_id: Override for NOTION_FINANCE_DB_ID env var
    
    Returns:
        List of snapshot dicts with date, liquid, burn_rate, status
    """
    try:
        from notion_client import Client
    except ImportError:
        logger.error("notion-client not installed")
        return []
    
    api_key = os.getenv("NOTION_API_KEY")
    db_id = database_id or os.getenv("NOTION_FINANCE_DB_ID")
    
    if not api_key or not db_id:
        return []
    
    try:
        notion = Client(auth=api_key)
        
        response = notion.databases.query(
            database_id=db_id,
            sorts=[{"property": "Date", "direction": "descending"}],
            page_size=limit
        )
        
        snapshots = []
        for page in response.get("results", []):
            props = page.get("properties", {})
            
            date_prop = props.get("Date", {}).get("date", {})
            liquid_prop = props.get("Total Liquid Cash", {}).get("number")
            burn_prop = props.get("Burn Rate", {}).get("number")
            status_prop = props.get("Safety Status", {}).get("select", {})
            
            snapshots.append({
                "date": date_prop.get("start") if date_prop else None,
                "total_liquid": liquid_prop,
                "burn_rate": burn_prop,
                "safety_status": status_prop.get("name") if status_prop else None
            })
        
        return snapshots
        
    except Exception as e:
        logger.error(f"Failed to fetch from Notion: {e}")
        return []


def calculate_trend(snapshots: List[dict]) -> dict:
    """
    Calculate trend from recent snapshots.
    
    Returns:
        dict with trend direction and magnitude
    """
    if len(snapshots) < 2:
        return {"direction": "stable", "change": 0}
    
    latest = snapshots[0].get("total_liquid", 0) or 0
    previous = snapshots[1].get("total_liquid", 0) or 0
    
    if previous == 0:
        return {"direction": "stable", "change": 0}
    
    change = latest - previous
    pct_change = (change / previous) * 100
    
    if pct_change > 5:
        direction = "up"
    elif pct_change < -5:
        direction = "down"
    else:
        direction = "stable"
    
    return {
        "direction": direction,
        "change": change,
        "percent_change": round(pct_change, 1)
    }
