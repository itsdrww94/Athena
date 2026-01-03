import logging
import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

from core.contracts.event_schema import CanonicalEvent

logger = logging.getLogger("athena.connectors.gmail")

class GmailConnector:
    """
    The Inbox Pilot.
    Ingests emails -> Parses Transactions -> Emits Canonical Events.
    """
    SOURCE = "gmail"
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        # TODO: Initialize Gmail Service here
    
    def process_messages(self, messages: List[Dict]) -> List[CanonicalEvent]:
        """
        Process a batch of raw email message dicts.
        """
        events = []
        parser = TransactionParser()
        
        for msg in messages:
            try:
                # Extract basic metadata
                msg_id = msg.get("id")
                subject = msg.get("subject", "")
                snippet = msg.get("snippet", "")
                sender = msg.get("from", "")
                timestamp_ms = msg.get("internalDate", "0")
                ts = datetime.fromtimestamp(int(timestamp_ms)/1000, tz=timezone.utc)
                
                # Check Key Candidates
                if not parser.is_candidate(sender, subject):
                    continue
                    
                # Parse
                tx_data = parser.parse(sender, subject, snippet)
                
                # If Regex failed, try Gemini (The user requested this specific capability)
                if not tx_data:
                    tx_data = parser.parse_with_gemini(subject, snippet)
                    
                if tx_data:
                    event_id = CanonicalEvent.create_id(self.SOURCE, msg_id, ts)
                    
                    events.append(CanonicalEvent(
                        event_id=event_id,
                        event_type="TRANSACTION",
                        source=self.SOURCE,
                        timestamp=ts,
                        privacy_level="HIGH", # Financial data is sensitive
                        data=tx_data,
                        derived={}
                    ))
                    
            except Exception as e:
                logger.error(f"Failed to process message {msg.get('id')}: {e}")
                
        return events

class TransactionParser:
    """
    Logic to extract Money, Merchant, and Category from text.
    """
    
    # Simple regex library (Expandable)
    PATTERNS = [
        # Example: "$12.50 paid to Starbucks"
        r"\$(\d+\.\d{2}) paid to (.+)",
        # Example: "You spent $5.00 at McDonald's"
        r"You spent \$(\d+\.\d{2}) at (.+)",
        # Example: "Charge of $10.99 by Netflix"
        r"Charge of \$(\d+\.\d{2}) by (.+)"
    ]
    
    def is_candidate(self, sender: str, subject: str) -> bool:
        """Filter noise."""
        keywords = ["receipt", "order", "invoice", "payment", "transaction", "charge"]
        sub = subject.lower()
        if any(k in sub for k in keywords):
            return True
        # Add Sender Allowlist checks here
        return False

    def parse(self, sender: str, subject: str, body: str) -> Optional[Dict]:
        """Attempt Regex parsing."""
        text = f"{subject} {body}"
        for pat in self.PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                merchant = match.group(2).strip()
                return {
                    "amount": amount,
                    "currency": "USD",
                    "merchant_raw": merchant,
                    "parse_method": "regex"
                }
        return None

    def parse_with_gemini(self, subject: str, snippet: str) -> Optional[Dict]:
        """
        Fallback: Use LLM to extract structure from unstructured text.
        """
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            return None
            
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            
            prompt = f"""
            Extract transaction details or return null.
            Input: Subject: {subject} | Body: {snippet}
            Output JSON: {{"amount": float, "currency": "USD", "merchant": "str"}}
            """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            # Basic parsing logic would go here (omitted for brevity)
            # return json.loads(response.text)
            return None # Placeholder
            
        except Exception as e:
            logger.warning(f"Gemini parse failed: {e}")
            return None
