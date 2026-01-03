"""
Athena Daily Worker
-------------------
Runs the Ingestion Pipeline and generates Daily Capsules.
Usage: python workers/run_ingest.py
"""
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from core.connectors.gmail import GmailConnector
from core.connectors.youtube import YouTubeConnector
from core.memory.curator import MemoryCurator
from core.memory.manager import MemoryManager

console = Console()
logging.basicConfig(level=logging.WARN)

def main():
    console.print("[bold cyan]🚀 Athena Daily Ingest Started[/bold cyan]")
    
    # 1. Ingest Data
    # ----------------
    events = []
    
    # Gmail
    console.print("[dim]📧 Checking Gmail...[/dim]")
    gmail = GmailConnector(dry_run=True) # Dry run for now
    # events.extend(gmail.process_messages([...]))
    console.print(f"[green]✓ Gmail processed (Mock)[/green]")
    
    # YouTube (Mock Takeout Path)
    console.print("[dim]📺 Processing Watch History...[/dim]")
    # yt = YouTubeConnector("path/to/takeout.json")
    # events.extend(yt.process())
    console.print(f"[green]✓ YouTube processed (Mock)[/green]")
    
    # 2. Curate Daily Capsule
    # -----------------------
    if events:
        console.print(f"[dim]💊 Generating Capsule for {datetime.now().date()}...[/dim]")
        curator = MemoryCurator()
        capsule = curator.generate_daily_capsule(str(datetime.now().date()), events)
        
        # 3. Save to Brain
        # ----------------
        console.print("[dim]💾 Saving to Memory...[/dim]")
        mem_manager = MemoryManager()
        if mem_manager.enabled:
            mem_id = mem_manager.add_episodic(capsule)
            console.print(f"[bold green]✅ Capsule Saved! ID: {mem_id}[/bold green]")
        else:
             console.print("[yellow]⚠ Memory Manager disabled (no Supabase creds).[/yellow]")
    else:
        console.print("[yellow]⚠ No events found today.[/yellow]")

if __name__ == "__main__":
    main()
