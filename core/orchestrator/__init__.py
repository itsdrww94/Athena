"""
Orchestrator package.

Re-exports handle_message from the sibling orchestrator.py module
to maintain backward compatibility with existing imports.
"""

# Import from the sibling .py file (core/orchestrator.py)
import sys
import os
import importlib.util

# Get the parent directory and import from orchestrator.py directly
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Import the actual module using importlib to avoid naming conflicts
_spec = importlib.util.spec_from_file_location(
    "orchestrator_module",
    os.path.join(_parent_dir, "orchestrator.py")
)
_orchestrator_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orchestrator_module)

# Re-export
handle_message = _orchestrator_module.handle_message

__all__ = ["handle_message"]
