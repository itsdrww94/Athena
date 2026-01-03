import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key: {'Found' if key else 'Missing'}")

if not url or not key:
    print("[ERROR] Critical: Credentials missing.")
    exit(1)

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

print("Connecting to Supabase (REST)...")

# 3. Test Connection & Read Data
print(f"\n[INFO] Connecting to {url}...")

try:
    # GET request to fetch keys from user_facts
    read_url = f"{url}/rest/v1/user_facts?select=key,category&limit=20"
    resp = requests.get(read_url, headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"[OK] Connection Successful!")
        print(f"[INFO] Found {len(data)} (showing top 20) records in 'user_facts'.")
        
        if not data:
            print("   (Table is empty)")
        else:
            print("\n   Sample Data:")
            for item in data:
                print(f"   - [{item.get('category')}] {item.get('key')}")
                
        # Check specifically for Profile Snapshot
        url_prof = f"{url}/rest/v1/user_facts?key=eq.profile_snapshot&select=key"
        resp_prof = requests.get(url_prof, headers=headers)
        if resp_prof.json():
            print("\n   [OK] Profile Snapshot found!")
        else:
            print("\n   [WARN] Profile Snapshot NOT found.")
            
    else:
        print(f"[ERROR] Status: {resp.status_code} - {resp.text}")

except Exception as e:
    print(f"[ERROR] Connection Failed: {e}")
