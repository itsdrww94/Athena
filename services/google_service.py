"""
Google Service for Athena
==========================
Integration with Google Workspace (Calendar, Gmail) via API.

Setup:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a project and enable Gmail API & Calendar API
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download credentials.json to Athena_Project folder
5. Run Athena and use /email - it will prompt for auth
"""

import os.path
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import re

logger = logging.getLogger("athena.google")

# Scopes - Read/Write Calendar, Read Gmail
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.modify',
]

# Transaction keywords to search for
TRANSACTION_KEYWORDS = [
    "receipt", "order confirmation", "payment", "purchase", 
    "charged", "transaction", "invoice", "billing",
    "your order", "order shipped", "delivery", "subscription"
]


class GoogleService:
    """Service for interacting with Google APIs."""

    def __init__(self):
        self.creds = None
        self.service_calendar = None
        self.service_gmail = None
        
        # Paths
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.token_path = os.path.join(self.base_path, "google_token.json")
        self.credentials_path = os.path.join(self.base_path, "credentials.json")

    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self.authenticate()

    def authenticate(self) -> bool:
        """Authenticate with Google."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            logger.error("Google API libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client")
            return False

        if self.creds and self.creds.valid:
            return True

        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Refresh failed: {e}")
                    self.creds = None
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)
            
            if not self.creds:
                if os.path.exists(self.token_path):
                    os.remove(self.token_path)

                if not os.path.exists(self.credentials_path):
                    logger.warning("No credentials.json found. Please set up Google OAuth.")
                    return False
                    
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    
                    print(f"\n🔐 Opening browser for Google authentication...")
                    self.creds = flow.run_local_server(port=8080, open_browser=True)
                    
                    # Save the credentials for next run
                    with open(self.token_path, 'w') as token:
                        token.write(self.creds.to_json())
                    print("✅ Google authentication successful!")
                except Exception as e:
                    logger.error(f"Auth Flow Failed: {e}")
                    return False

        # Build services
        try:
            self.service_calendar = build('calendar', 'v3', credentials=self.creds)
            self.service_gmail = build('gmail', 'v1', credentials=self.creds)
            logger.info("Google Service Connected.")
            return True
        except Exception as e:
            logger.error(f"Service Build Failed: {e}")
            return False

    def get_upcoming_events(self, max_results=10) -> List[str]:
        """Get upcoming calendar events."""
        if not self.service_calendar and not self.authenticate():
            return ["⚠️ Google Service not authenticated. Please add credentials.json."]

        try:
            from googleapiclient.errors import HttpError
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service_calendar.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                return ["No upcoming events found."]
            
            summary_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary_list.append(f"• {start}: {event['summary']}")
            return summary_list

        except Exception as error:
            logger.error(f"An error occurred: {error}")
            return [f"Google API Error: {error}"]

    def create_calendar_event(
        self, 
        title: str, 
        start_time: datetime, 
        duration_minutes: int = 60,
        location: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Create a new Google Calendar event.
        
        Args:
            title: Event title/summary
            start_time: When the event starts
            duration_minutes: Duration in minutes (default 60)
            location: Optional location
            description: Optional description
            
        Returns:
            Dict with event details or error
        """
        if not self.service_calendar and not self.authenticate():
            return {"error": "Google Service not authenticated."}
        
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event_body = {
                'summary': title,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Chicago',  # Adjust to user's timezone
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Chicago',
                },
            }
            
            if location:
                event_body['location'] = location
            if description:
                event_body['description'] = description
            
            event = self.service_calendar.events().insert(
                calendarId='primary', 
                body=event_body
            ).execute()
            
            logger.info(f"Calendar event created: {event.get('htmlLink')}")
            
            return {
                "success": True,
                "event_id": event.get('id'),
                "link": event.get('htmlLink'),
                "title": title,
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return {"error": str(e)}

    def list_events_for_day(self, target_date: datetime = None) -> List[Dict]:
        """
        List all events for a specific day.
        
        Args:
            target_date: The day to check (defaults to today)
            
        Returns:
            List of event dicts
        """
        if not self.service_calendar and not self.authenticate():
            return [{"error": "Google Service not authenticated."}]
        
        target = target_date or datetime.now()
        start_of_day = target.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        try:
            events_result = self.service_calendar.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return [
                {
                    "id": e.get('id'),
                    "title": e.get('summary'),
                    "start": e['start'].get('dateTime', e['start'].get('date')),
                    "end": e['end'].get('dateTime', e['end'].get('date')),
                    "location": e.get('location', '')
                }
                for e in events
            ]
            
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            return [{"error": str(e)}]

    def get_unread_emails(self, max_results=5) -> List[str]:
        """Get recent unread emails."""
        if not self.service_gmail and not self.authenticate():
            return ["⚠️ Google Service not authenticated."]

        try:
            results = self.service_gmail.users().messages().list(
                userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return ["No unread messages."]

            email_summaries = []
            for msg in messages:
                txt = self.service_gmail.users().messages().get(
                    userId='me', id=msg['id'], format='metadata').execute()
                
                headers = txt['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                
                email_summaries.append(f"• From: {sender} | Subj: {subject}")
            
            return email_summaries
            
        except Exception as error:
            logger.error(f"An error occurred: {error}")
            return [f"Google API Error: {error}"]

    def search_transaction_emails(self, days: int = 7, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for transaction-related emails.
        
        Args:
            days: How many days back to search
            max_results: Maximum results to return
            
        Returns:
            List of transaction email summaries
        """
        if not self.service_gmail and not self.authenticate():
            return [{"error": "Google Service not authenticated."}]

        try:
            # Build search query for transaction keywords
            keyword_query = " OR ".join([f'"{kw}"' for kw in TRANSACTION_KEYWORDS])
            date_filter = f"newer_than:{days}d"
            query = f"({keyword_query}) {date_filter}"
            
            results = self.service_gmail.users().messages().list(
                userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return []

            transactions = []
            for msg in messages:
                msg_data = self.service_gmail.users().messages().get(
                    userId='me', id=msg['id'], format='full').execute()
                
                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Try to extract amount from snippet
                snippet = msg_data.get('snippet', '')
                amount = self._extract_amount(snippet)
                
                transactions.append({
                    "id": msg['id'],
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "amount": amount,
                    "snippet": snippet[:150] + "..." if len(snippet) > 150 else snippet
                })
            
            return transactions
            
        except Exception as error:
            logger.error(f"Transaction search failed: {error}")
            return [{"error": str(error)}]

    def _extract_amount(self, text: str) -> Optional[str]:
        """Extract dollar amount from text."""
        # Match patterns like $12.34, $1,234.56, USD 12.34
        patterns = [
            r'\$[\d,]+\.?\d*',
            r'USD\s*[\d,]+\.?\d*',
            r'[\d,]+\.?\d*\s*USD',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None


            return email_list
            
        except Exception as error:
            logger.error(f"Email search failed: {error}")
            return [{"error": str(error)}]

    def _get_body(self, payload: Dict[str, Any]) -> str:
        """Extract plain text body from payload."""
        import base64
        
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode()
                elif 'parts' in part:
                    # Recursive
                    body += self._get_body(part)
        elif payload.get('mimeType') == 'text/plain':
            data = payload['body'].get('data')
            if data:
                body += base64.urlsafe_b64decode(data).decode()
        
        return body

    def search_emails(self, query: str = "", days: int = 7, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Generic email search for Agentic use.
        
        Args:
            query: Search terms (e.g., "subject:meeting", "congratulations")
            days: How many days back to search
            max_results: Max results
            
        Returns:
            List of email summaries with FULL BODY.
        """
        if not self.service_gmail and not self.authenticate():
            return [{"error": "Google Service not authenticated."}]

        try:
            # Construct Gmail query
            date_filter = f"newer_than:{days}d"
            full_query = f"{query} {date_filter}".strip()
            
            results = self.service_gmail.users().messages().list(
                userId='me', q=full_query, maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return []

            email_list = []
            for msg in messages:
                msg_data = self.service_gmail.users().messages().get(
                    userId='me', id=msg['id'], format='full').execute()
                
                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                snippet = msg_data.get('snippet', '')
                
                # NEW: Get full body
                body = self._get_body(msg_data['payload'])
                
                email_list.append({
                    "id": msg['id'],
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "snippet": snippet,
                    "body": body[:5000] # Cap to avoid context overflow, but significantly more than snippet
                })
            
            return email_list
            
        except Exception as error:
            logger.error(f"Email search failed: {error}")
            return [{"error": str(error)}]


# Singleton
_google_service = None

def get_google_service() -> GoogleService:
    """Get or create the Google service singleton."""
    global _google_service
    if _google_service is None:
        _google_service = GoogleService()
    return _google_service
