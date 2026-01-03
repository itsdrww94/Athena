import os
import json
import shutil
import logging
from typing import List, Dict

logger = logging.getLogger("Hakari.Sync")

OUTBOX_PATH = os.path.join(os.path.dirname(__file__), "data", "outbox_events.jsonl")
PROCESSING_PATH = os.path.join(os.path.dirname(__file__), "data", "outbox_processing.jsonl")

def write_outbox_event(event: Dict):
    """Buffer an event to local JSONL for later sync."""
    try:
        os.makedirs(os.path.dirname(OUTBOX_PATH), exist_ok=True)
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to outbox: {e}")

def get_batch_for_sync(max_batch=100) -> List[Dict]:
    """
    Move current outbox to processing stage and return events.
    Returns empty list if nothing to sync.
    MAX_BATCH is a soft limit (we read the whole file currently for simplicity of rotation).
    """
    if not os.path.exists(OUTBOX_PATH):
        return []

    try:
        # Rotate file to processing
        if os.path.exists(PROCESSING_PATH):
            # Previous sync failed or crashed. Append new outbox to it?
            # Or just process existing processing file first.
            # Strategy: if processing exists, return that first.
            pass
        else:
            try:
                os.rename(OUTBOX_PATH, PROCESSING_PATH)
            except OSError:
                return [] # File locked or busy

        events = []
        with open(PROCESSING_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except:
                    continue
        return events
    except Exception as e:
        logger.error(f"Sync rotation failed: {e}")
        return []

def confirm_sync_success():
    """Delete the processing file after successful upload."""
    try:
        if os.path.exists(PROCESSING_PATH):
            os.remove(PROCESSING_PATH)
    except Exception as e:
        logger.error(f"Failed to clear processing file: {e}")

def revert_sync_failure(events: List[Dict]):
    """Put events back into outbox if sync failed."""
    # Append content of processing back to outbox (or prepend?)
    # Simplest: Just leave them in 'processing' and retry next time?
    # But get_batch checks existence.
    # If we failed, we keep PROCESSING_PATH. Next retry pick it up.
    # But write_outbox_event keeps writing to OUTBOX.
    # So we have two queues.
    # My logic in get_batch handles this: "if processing exists... pass" (return it).
    pass 
