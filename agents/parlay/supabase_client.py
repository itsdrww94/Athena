import os
import json
import logging
import asyncio
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional

# Dependencies
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
import requests

try:
    from . import sync_queue
except ImportError:
    import sync_queue

logger = logging.getLogger("Hakari.Supabase")

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY", ""))
        self.instance_id = os.getenv("HAKARI_INSTANCE_ID", str(uuid.uuid4()))
        self.enabled = bool(self.url and self.key)
        
        if not self.enabled:
            logger.warning("Supabase URL/KEY missing. Persisting strictly to local JSONL.")
        else:
            logger.info(f"Supabase Client Active (Instance: {self.instance_id})")

    async def emit_event(self, event_type: str, payload: Dict, 
                         platform: str = "unknown", mode: str = "assisted",
                         slip_id: str = None):
        """
        Async emit event to Supabase. Falls back to sync queue on failure.
        """
        event = {
            "instance_id": self.instance_id,
            "event_type": event_type,
            "platform": platform,
            "mode": mode,
            "slip_id": slip_id or payload.get("slip_id", str(uuid.uuid4())),
            "ts": datetime.utcnow().isoformat(),
            "payload": payload,
            "event_version": 1
        }
        
        if not self.enabled:
            sync_queue.write_outbox_event(event)
            return

        # Fire and forget (task)
        asyncio.create_task(self._send_to_supabase(event))

    async def _send_to_supabase(self, event: Dict):
        """Internal sender."""
        endpoint = f"{self.url}/rest/v1/hakari_events"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        try:
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.post(endpoint, json=event, headers=headers) as resp:
                        if resp.status not in [200, 201]:
                            text = await resp.text()
                            raise Exception(f"HTTP {resp.status}: {text}")
            else:
                # Synchronous fallback in thread
                await asyncio.to_thread(self._sync_post, endpoint, event, headers)
                
        except Exception as e:
            logger.error(f"Supabase Send Failed: {e}")
            sync_queue.write_outbox_event(event)

    def _sync_post(self, url, data, headers):
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        if resp.status_code not in [200, 201]:
            raise Exception(f"HTTP {resp.status_code}")

    async def query_recent_events(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """Fetch recent events from Supabase."""
        if not self.enabled:
            return [] # Fallback to local file handled by caller

        endpoint = f"{self.url}/rest/v1/hakari_events?select=*&order=ts.desc&limit={limit}"
        if event_type:
            endpoint += f"&event_type=eq.{event_type}"
            
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        
        try:
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
            else:
                resp = requests.get(endpoint, headers=headers, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Query Failed: {e}")
            
        return []

    async def flush_outbox(self):
        """Retry sending queued events."""
        if not self.enabled: return
        
        batch = sync_queue.get_batch_for_sync(max_batch=50)
        if not batch: return
        
        logger.info(f"Flushing {len(batch)} events to Supabase...")
        endpoint = f"{self.url}/rest/v1/hakari_events"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        try:
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.post(endpoint, json=batch, headers=headers) as resp:
                        if resp.status not in [200, 201]:
                            raise Exception(f"HTTP {resp.status}")
            else:
                await asyncio.to_thread(self._sync_post, endpoint, batch, headers)
            
            # Success
            sync_queue.confirm_sync_success()
            logger.info("Flush complete.")
            
        except Exception as e:
            logger.error(f"Flush Failed: {e}")
            # Do NOT confirm success, so processing file remains to be retried next time
            # (Logic depends on sync_queue implementation)

_client = SupabaseClient()
def get_client():
    return _client
