#!/usr/bin/env python3
"""
Apply Athena Schema to Supabase
===============================
This script applies the canonical schema to your Supabase database.

Usage:
    python scripts/apply_schema.py
    
The script reads from services/memory/migrations/001_init.sql and executes
each statement against your Supabase database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def apply_schema():
    """Apply the canonical schema to Supabase."""
    
    import requests
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False
    
    # Read schema file
    schema_file = Path(__file__).parent.parent / "services" / "memory" / "migrations" / "001_init.sql"
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    schema_sql = schema_file.read_text(encoding="utf-8")
    
    print(f"📄 Read schema from: {schema_file.name}")
    print(f"   Size: {len(schema_sql)} bytes")
    
    # Use Supabase REST API to execute SQL
    # Note: This requires the new SQL API or using Postgres directly
    # For now, we'll just print instructions
    
    print("\n" + "=" * 60)
    print("📋 APPLY SCHEMA INSTRUCTIONS")
    print("=" * 60)
    print()
    print("1. Go to your Supabase Dashboard:")
    print(f"   {supabase_url.replace('.supabase.co', '.supabase.com')}")
    print()
    print("2. Click 'SQL Editor' in the left sidebar")
    print()
    print("3. Create a 'New query' and paste the contents of:")
    print(f"   {schema_file}")
    print()
    print("4. Click 'Run' to execute the schema")
    print()
    print("=" * 60)
    print("💡 TIP: The schema is idempotent - safe to run multiple times")
    print("=" * 60)
    
    # Quick connectivity test
    print("\n🔍 Testing Supabase connectivity...")
    
    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
        }
        
        # Try to list tables
        resp = requests.get(
            f"{supabase_url}/rest/v1/",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            print("✅ Supabase connection successful!")
            
            # Check if memory_events table exists
            resp2 = requests.get(
                f"{supabase_url}/rest/v1/memory_events?limit=1",
                headers=headers,
                timeout=10
            )
            
            if resp2.status_code == 200:
                print("✅ memory_events table exists!")
            elif resp2.status_code == 404:
                print("⚠️  memory_events table not found - schema not yet applied")
            else:
                print(f"⚠️  memory_events check returned: {resp2.status_code}")
                
            # Check memory_facts
            resp3 = requests.get(
                f"{supabase_url}/rest/v1/memory_facts?limit=1",
                headers=headers,
                timeout=10
            )
            
            if resp3.status_code == 200:
                print("✅ memory_facts table exists!")
            else:
                print("⚠️  memory_facts table not found")
                
        else:
            print(f"⚠️  Supabase returned status: {resp.status_code}")
            
    except Exception as e:
        print(f"⚠️  Connection test failed: {e}")
    
    return True


if __name__ == "__main__":
    apply_schema()
