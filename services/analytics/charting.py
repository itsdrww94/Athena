"""
Analytics Charting Tool
=======================
Generates charts for spending and other metrics.
"""

from typing import List, Dict, Any, Optional
import json

def generate_spending_chart(
    data: List[Dict[str, Any]], 
    title: str = "Spending Analysis",
    output_path: Optional[str] = None
) -> str:
    """
    Generate a spending chart (ASCII or Image).
    
    Args:
        data: List of dicts with 'category' and 'amount'
        title: Chart title
        output_path: Path to save image (optional)
        
    Returns:
        String representation or path to file
    """
    if not data:
        return "No data to chart."
    
    # Simple ASCII Bar Chart for CLI
    chart = [f"📊 {title}", ""]
    
    # Aggregate by category
    totals = {}
    for item in data:
        cat = item.get("category", "Uncategorized")
        amt = float(item.get("amount", 0))
        totals[cat] = totals.get(cat, 0) + amt
    
    max_val = max(totals.values()) if totals else 0
    scale = 20 / max_val if max_val > 0 else 1
    
    for cat, total in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        bar_len = int(total * scale)
        bar = "█" * bar_len
        chart.append(f"{cat[:15]:<15} | {bar} ${total:.2f}")
    
    return "\n".join(chart)
