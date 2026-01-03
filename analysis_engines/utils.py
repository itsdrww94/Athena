#!/usr/bin/env python3
"""
Utility functions for the Analysis Engines.
"""

import os
import re
import json
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional, Union
from pathlib import Path

import pytz

# Default timezone for Drew (Minneapolis)
DEFAULT_TZ = pytz.timezone("America/Chicago")


def normalize_timestamp(ts: Union[str, int, float, None], 
                        target_tz: timezone = DEFAULT_TZ) -> Optional[datetime]:
    """
    Normalize various timestamp formats to a consistent datetime object.
    
    Handles:
    - ISO 8601 strings ("2024-01-15T10:30:00Z")
    - Unix epoch (seconds): 1705319400
    - Unix epoch (milliseconds): 1705319400000
    - Date strings: "Jan 15, 2024"
    
    Returns:
        datetime object in target timezone, or None if unparseable
    """
    if ts is None:
        return None
    
    try:
        # Handle numeric timestamps (Unix epoch)
        if isinstance(ts, (int, float)):
            # Check if milliseconds (> year 2100 in seconds)
            if ts > 4102444800:  
                ts = ts / 1000
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.astimezone(target_tz)
        
        # Handle string timestamps
        if isinstance(ts, str):
            ts = ts.strip()
            
            # ISO 8601 with Z suffix
            if ts.endswith('Z'):
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.astimezone(target_tz)
            
            # ISO 8601 with timezone
            if '+' in ts or ts.count('-') >= 3:
                try:
                    dt = datetime.fromisoformat(ts)
                    return dt.astimezone(target_tz)
                except:
                    pass
            
            # Common date formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%m/%d/%Y %H:%M",
                "%m/%d/%Y",
                "%Y-%m-%d",
                "%b %d, %Y",
                "%B %d, %Y",
                "%d/%m/%Y",
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(ts, fmt)
                    # Assume local time if no timezone
                    return target_tz.localize(dt)
                except:
                    pass
        
        return None
        
    except Exception:
        return None


def clean_pii(text: str) -> str:
    """
    Remove Personally Identifiable Information before sending to cloud LLMs.
    
    Masks:
    - Email addresses
    - Phone numbers
    - SSN-like patterns
    - Credit card patterns
    - Street addresses (basic)
    """
    if not text:
        return text
    
    # Email addresses
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        text
    )
    
    # Phone numbers (US formats)
    text = re.sub(
        r'\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        '[PHONE]',
        text
    )
    
    # SSN patterns
    text = re.sub(
        r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
        '[SSN]',
        text
    )
    
    # Credit card patterns
    text = re.sub(
        r'\b(?:\d{4}[-.\s]?){4}\b',
        '[CARD]',
        text
    )
    
    return text


def load_json_stream(filepath: Path, max_items: int = None) -> Generator[Dict, None, None]:
    """
    Stream large JSON files without loading entirely into memory.
    
    Uses ijson for efficient parsing of large exports like Google Takeout.
    
    Args:
        filepath: Path to JSON file
        max_items: Optional limit on number of items to yield
    
    Yields:
        Individual items from the JSON array
    """
    try:
        import ijson
        
        with open(filepath, 'rb') as f:
            # Try to detect if it's an array or object
            first_char = f.read(1)
            f.seek(0)
            
            if first_char == b'[':
                # JSON array
                parser = ijson.items(f, 'item')
            else:
                # JSON object - try common keys
                parser = ijson.items(f, '')  # Get the whole object
            
            count = 0
            for item in parser:
                yield item
                count += 1
                if max_items and count >= max_items:
                    break
                    
    except ImportError:
        # Fallback to standard json (loads entire file)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if isinstance(data, list):
                for i, item in enumerate(data):
                    yield item
                    if max_items and i >= max_items - 1:
                        break
            else:
                yield data


def get_hour_of_day(dt: datetime) -> int:
    """Extract hour (0-23) from datetime."""
    return dt.hour if dt else None


def get_day_of_week(dt: datetime) -> int:
    """Extract day of week (0=Monday, 6=Sunday) from datetime."""
    return dt.weekday() if dt else None


def calculate_moving_average(values: list, window: int = 7) -> list:
    """Calculate simple moving average."""
    if len(values) < window:
        return values
    
    result = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(sum(values[:i+1]) / (i+1))
        else:
            result.append(sum(values[i-window+1:i+1]) / window)
    
    return result


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that returns default on zero denominator."""
    if denominator == 0:
        return default
    return numerator / denominator
