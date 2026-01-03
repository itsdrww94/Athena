"""
Focus Terminal for Athena
=========================
A dedicated terminal view for long-running tasks, similar to Claude CLI and Gemini CLI.
Shows a focused panel with real-time progress updates while processing.

Usage:
    with FocusTerminal("Analyzing Data") as focus:
        focus.update("Scanning files...", progress=10)
        # ... do work ...
        focus.update("Parsing ChatGPT logs...", progress=50)
        focus.update_substep("Found 127 conversations")
        focus.complete("Analysis complete!", summary=["5 patterns found", "3 recommendations"])
"""

import time
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED, HEAVY
from rich.align import Align
from rich.style import Style


@dataclass
class FocusStep:
    """A step within a focused task."""
    name: str
    status: str = "pending"  # pending, running, done, error
    substeps: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class FocusTerminal:
    """
    A dedicated terminal view for long-running tasks.
    
    Creates a focused panel that takes over the terminal while a task is running,
    showing real-time progress updates similar to Claude/Gemini CLI.
    
    Example:
        with FocusTerminal("Analyzing Data", task_id="DATA-123") as focus:
            focus.update("Scanning folder...", progress=10)
            time.sleep(1)
            focus.add_substep("Found 50 files")
            focus.update("Classifying files...", progress=40)
            time.sleep(1)
            focus.complete("Done!", summary=["ChatGPT: 30 files", "Spotify: 20 files"])
    """
    
    def __init__(
        self, 
        title: str, 
        task_id: Optional[str] = None,
        show_elapsed: bool = True,
        theme: str = "purple"  # purple, cyan, green
    ):
        self.title = title
        self.task_id = task_id or f"TASK-{int(time.time()) % 10000}"
        self.show_elapsed = show_elapsed
        self.theme = theme
        
        self.console = Console()
        self.live: Optional[Live] = None
        self.progress: Optional[Progress] = None
        self.progress_task: Optional[TaskID] = None
        
        self.current_step = ""
        self.current_progress = 0
        self.substeps: List[str] = []
        self.started_at = datetime.now()
        self.status = "running"  # running, complete, error
        self.result_summary: List[str] = []
        
        # Theme colors
        self.colors = {
            "purple": {"border": "#800080", "accent": "#BF40BF", "text": "#E0B0FF"},
            "cyan": {"border": "#00BCD4", "accent": "#00E5FF", "text": "#B2EBF2"},
            "green": {"border": "#00C853", "accent": "#69F0AE", "text": "#B9F6CA"},
        }.get(theme, {"border": "#800080", "accent": "#BF40BF", "text": "#E0B0FF"})
    
    def __enter__(self):
        """Start the focus terminal."""
        self.started_at = datetime.now()
        self.live = Live(
            self._render(), 
            console=self.console, 
            refresh_per_second=4,
            transient=False  # Keep the final state visible
        )
        self.live.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the focus terminal."""
        if exc_type is not None:
            self.error(f"Error: {exc_val}")
        self.live.stop()
        return False
    
    def _render(self) -> Panel:
        """Render the current state of the focus terminal."""
        # Build content
        content_parts = []
        
        # Header with task ID and elapsed time
        header = Text()
        header.append("📋 ", style="bold")
        header.append(f"Task: {self.task_id}", style=f"bold {self.colors['accent']}")
        if self.show_elapsed:
            elapsed = (datetime.now() - self.started_at).total_seconds()
            header.append(f"  ⏱ {elapsed:.1f}s", style="dim")
        content_parts.append(header)
        content_parts.append(Text(""))  # Spacer
        
        # Current step with spinner or checkmark
        step_line = Text()
        if self.status == "running":
            step_line.append("⟳ ", style=f"bold {self.colors['accent']}")
        elif self.status == "complete":
            step_line.append("✓ ", style="bold green")
        else:
            step_line.append("✗ ", style="bold red")
        step_line.append(self.current_step or "Initializing...", style="bold")
        content_parts.append(step_line)
        
        # Progress bar
        if self.current_progress > 0:
            progress_text = Text()
            bar_width = 30
            filled = int((self.current_progress / 100) * bar_width)
            progress_text.append("  [", style="dim")
            progress_text.append("━" * filled, style=f"bold {self.colors['accent']}")
            progress_text.append("─" * (bar_width - filled), style="dim")
            progress_text.append(f"] {self.current_progress}%", style="dim")
            content_parts.append(progress_text)
        
        # Substeps
        if self.substeps:
            content_parts.append(Text(""))  # Spacer
            for substep in self.substeps[-5:]:  # Show last 5 substeps
                sub_line = Text()
                sub_line.append("  → ", style="dim")
                sub_line.append(substep, style=self.colors['text'])
                content_parts.append(sub_line)
        
        # Result summary (when complete)
        if self.status == "complete" and self.result_summary:
            content_parts.append(Text(""))  # Spacer
            content_parts.append(Text("─" * 40, style="dim"))
            for item in self.result_summary:
                result_line = Text()
                result_line.append("  • ", style=f"bold {self.colors['accent']}")
                result_line.append(item, style="bold white")
                content_parts.append(result_line)
        
        # Build panel
        title_text = f"✦ {self.title}"
        if self.status == "complete":
            title_text += " ✓"
        elif self.status == "error":
            title_text += " ✗"
        
        border_style = self.colors['border']
        if self.status == "complete":
            border_style = "green"
        elif self.status == "error":
            border_style = "red"
        
        return Panel(
            Group(*content_parts),
            title=title_text,
            title_align="left",
            border_style=border_style,
            box=ROUNDED,
            padding=(1, 2),
        )
    
    def update(self, step: str, progress: Optional[int] = None):
        """Update the current step and optionally the progress."""
        self.current_step = step
        if progress is not None:
            self.current_progress = min(100, max(0, progress))
        if self.live:
            self.live.update(self._render())
    
    def add_substep(self, substep: str):
        """Add a substep to the current operation."""
        self.substeps.append(substep)
        if self.live:
            self.live.update(self._render())
    
    def complete(self, message: str, summary: Optional[List[str]] = None):
        """Mark the task as complete with optional summary."""
        self.status = "complete"
        self.current_step = message
        self.current_progress = 100
        if summary:
            self.result_summary = summary
        if self.live:
            self.live.update(self._render())
    
    def error(self, message: str):
        """Mark the task as errored."""
        self.status = "error"
        self.current_step = message
        if self.live:
            self.live.update(self._render())


class MiniFocusTerminal:
    """
    A lightweight inline focus indicator for shorter tasks.
    Uses a simple spinner with status text.
    """
    
    def __init__(self, initial_message: str = "Processing..."):
        self.console = Console()
        self.message = initial_message
        self.live: Optional[Live] = None
    
    def __enter__(self):
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
            transient=True
        )
        self.live.start()
        return self
    
    def __exit__(self, *args):
        self.live.stop()
    
    def _render(self) -> Text:
        text = Text()
        text.append("⟳ ", style="bold #BF40BF")
        text.append(self.message, style="#E0B0FF")
        return text
    
    def update(self, message: str):
        self.message = message
        if self.live:
            self.live.update(self._render())


@contextmanager
def focus_task(title: str, task_id: Optional[str] = None, theme: str = "purple"):
    """
    Context manager for creating a focus terminal.
    
    Example:
        with focus_task("Downloading Files", theme="cyan") as focus:
            focus.update("Connecting...", progress=0)
            # ... do work ...
            focus.complete("Downloaded 5 files")
    """
    focus = FocusTerminal(title, task_id=task_id, theme=theme)
    with focus:
        yield focus


# Demo function
def demo_focus_terminal():
    """Demo the focus terminal."""
    with FocusTerminal("Analyzing Data Folder", task_id="DATA-5F3A") as focus:
        focus.update("Scanning directory...", progress=10)
        time.sleep(0.8)
        
        focus.add_substep("Found 47 files")
        focus.update("Classifying files...", progress=30)
        time.sleep(0.6)
        
        focus.add_substep("ChatGPT export detected (23 files)")
        focus.add_substep("Spotify history detected (15 files)")
        focus.update("Parsing ChatGPT logs...", progress=50)
        time.sleep(0.8)
        
        focus.add_substep("Processed 127 conversations")
        focus.update("Parsing Spotify data...", progress=70)
        time.sleep(0.6)
        
        focus.add_substep("Processed 3,420 listening events")
        focus.update("Generating insights...", progress=90)
        time.sleep(0.5)
        
        focus.complete("Analysis Complete!", summary=[
            "47 files processed",
            "ChatGPT: 127 conversations",
            "Spotify: 3,420 listening events",
            "Top pattern: Late-night coding sessions",
        ])
        time.sleep(2)  # Keep visible for a moment


if __name__ == "__main__":
    demo_focus_terminal()
