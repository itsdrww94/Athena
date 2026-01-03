#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   D R I V E   H A R V E S T E R                               ║
║                   "The Cloud Walker"                                          ║
║                                                                               ║
║  Scans Google Drive for specific log files and syncs them to Athena           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

** SETUP REQUIRED **
1. Enable Google Drive API in Cloud Console.
2. Download `credentials.json` (OAuth Client ID).
3. Place `credentials.json` in Athena root.

Usage:
    python agents/drive_harvester.py --scan "Studio Logs"
"""

import os
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Mock dependencies if not installed
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_LIB = True
except ImportError:
    HAS_GOOGLE_LIB = False

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Paths
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
DOWNLOAD_DIR = Path.home() / "athena_data" / "drive_imports"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def authenticate():
    """Authenticate with Google Drive API."""
    if not HAS_GOOGLE_LIB:
        print("❌ Google Client Library not installed.")
        print("   Run: pip install google-auth google-auth-oauthlib google-api-python-client")
        return None

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("❌ credentials.json not found. Cannot authenticate.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def search_files(service, query_name: str) -> List[Dict]:
    """Search for files in Drive."""
    results = []
    page_token = None
    
    print(f"🔍 Searching Drive for '{query_name}'...")
    
    # Query: name contains query_name and not trashed
    q = f"name contains '{query_name}' and trashed = false"
    
    while True:
        response = service.files().list(q=q, spaces='drive',
                                        fields='nextPageToken, files(id, name, mimeType)',
                                        pageToken=page_token).execute()
        for file in response.get('files', []):
            print(f"   Found: {file.get('name')} ({file.get('id')})")
            results.append(file)
            
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
            
    return results

def download_file(service, file_id: str, file_name: str):
    """Download a file from Drive."""
    request = service.files().get_media(fileId=file_id)
    file_path = DOWNLOAD_DIR / file_name
    
    import io
    fh = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    print(f"⬇️  Downloading {file_name}...", end='', flush=True)
    while done is False:
        status, done = downloader.next_chunk()
        # print(f"Download {int(status.progress() * 100)}%.", end='')
        
    print(" Done!")
    return file_path

def main():
    parser = argparse.ArgumentParser(description="Google Drive Harvester")
    parser.add_argument("--scan", type=str, default="Studio Logs", help="Name pattern to search for")
    args = parser.parse_args()
    
    creds = authenticate()
    if not creds:
        return

    service = build('drive', 'v3', credentials=creds)

    # Search
    files = search_files(service, args.scan)
    
    if not files:
        print("🤷 No files found.")
        return

    # Download
    print(f"\n📥 Downloading {len(files)} files to {DOWNLOAD_DIR}...")
    for file in files:
        # Skip folders
        if file['mimeType'] == 'application/vnd.google-apps.folder':
            continue
            
        try:
            download_file(service, file['id'], file['name'])
        except Exception as e:
            print(f"❌ Failed to download {file['name']}: {e}")

    print("\n✅ Drive harvest complete.")

if __name__ == "__main__":
    main()
