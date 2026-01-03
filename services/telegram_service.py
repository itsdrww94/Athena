"""
Athena Telegram Service
========================
Dedicated service for Telegram bot integration.

Setup:
1. Create a bot via @BotFather on Telegram
2. Set TELEGRAM_BOT_TOKEN in your .env
3. Set TELEGRAM_CHAT_ID (your chat ID) in .env
4. Optionally set GIPHY_API_KEY for GIF support

Usage:
    from services.telegram_service import TelegramService
    
    telegram = TelegramService()
    await telegram.send_text("Hello!")
"""

import os
import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

import httpx

# =============================================================================
# CONFIGURATION
# =============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")

# Data directory for conversation history
DATA_DIR = Path(__file__).parent.parent / "data" / "telegram"
HISTORY_FILE = DATA_DIR / "conversation_history.jsonl"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TelegramMessage:
    """A Telegram message."""
    message_id: int
    chat_id: str
    sender: str
    text: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    has_photo: bool = False
    photo_file_id: Optional[str] = None
    has_document: bool = False
    document_file_id: Optional[str] = None
    reply_to: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TELEGRAM SERVICE
# =============================================================================

class TelegramService:
    """
    Telegram bot service for Athena.

    Features:
    - Send/receive text messages
    - Send photos and GIFs
    - Typing indicators
    - File downloads
    """

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.default_chat_id = TELEGRAM_CHAT_ID
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _save_message(self, direction: str, text: str, message_type: str = "text", metadata: Dict = None) -> None:
        """
        Save a message to conversation history.

        Args:
            direction: "sent" or "received"
            text: Message content
            message_type: "text", "photo", "gif", etc.
            metadata: Additional metadata
        """
        try:
            message_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "direction": direction,
                "type": message_type,
                "text": text,
                "metadata": metadata or {}
            }

            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(message_record) + "\n")
        except Exception as e:
            print(f"Failed to save message to history: {e}")

    def get_recent_messages(self, limit: int = 20) -> List[Dict]:
        """
        Retrieve recent messages from conversation history.

        Args:
            limit: Number of recent messages to retrieve

        Returns:
            List of message dictionaries
        """
        if not HISTORY_FILE.exists():
            return []

        try:
            messages = []
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))

            # Return most recent messages
            return messages[-limit:] if len(messages) > limit else messages
        except Exception as e:
            print(f"Failed to read message history: {e}")
            return []

    def get_last_sent_message(self) -> Optional[Dict]:
        """Get the last message Athena sent."""
        recent = self.get_recent_messages(limit=50)
        for msg in reversed(recent):
            if msg.get("direction") == "sent":
                return msg
        return None

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token)

    def _api_url(self, method: str) -> str:
        """Build Telegram API URL."""
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    # =========================================================================
    # SENDING MESSAGES
    # =========================================================================

    async def send_text(self, text: str, chat_id: str = None, parse_mode: str = "Markdown", reply_markup: Optional[Dict] = None) -> dict:
        """
        Send a text message with optional buttons.

        Args:
            text: Message content
            chat_id: Target chat (uses default if not provided)
            parse_mode: "Markdown" or "HTML"
            reply_markup: JSON dict for inline keyboard
        """
        if not self.is_configured:
            return {"ok": False, "error": "Telegram not configured"}

        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            return {"ok": False, "error": "No chat_id provided"}

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._api_url("sendMessage"),
                    json=payload,
                    timeout=30.0
                )
            result = response.json()
            
            # Save sent message to history
            if result.get("ok"):
                self._save_message("sent", text, "text", {"chat_id": chat_id})

            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def send_plan_card(self, task: Any, chat_id: str = None) -> dict:
        """Render and send a Task Plan Card."""
        try:
            from services.ui.plan_renderer import PlanRenderer
            text, markup = PlanRenderer.render(task)
            return await self.send_text(text, chat_id=chat_id, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            return {"ok": False, "error": f"Render failed: {str(e)}"}

    async def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False) -> bool:
        """
        Answer a callback query to stop the loading animation.
        """
        if not self.is_configured:
            return False

        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._api_url("answerCallbackQuery"),
                    json=payload,
                    timeout=10.0
                )
            return True
        except Exception:
            return False

    async def send_photo(self, photo_url: str, caption: str = "", chat_id: str = None) -> dict:
        """Send a photo by URL."""
        if not self.is_configured:
            return {"ok": False, "error": "Telegram not configured"}

        chat_id = chat_id or self.default_chat_id
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._api_url("sendPhoto"),
                    json={
                        "chat_id": chat_id,
                        "photo": photo_url,
                        "caption": caption
                    },
                    timeout=30.0
                )
            result = response.json()

            # Save sent message to history
            if result.get("ok"):
                self._save_message("sent", caption or "[Photo]", "photo",
                                 {"chat_id": chat_id, "photo_url": photo_url})

            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def send_gif(self, gif_url: str, caption: str = "", chat_id: str = None) -> dict:
        """Send a GIF/animation by URL."""
        if not self.is_configured:
            return {"ok": False, "error": "Telegram not configured"}

        chat_id = chat_id or self.default_chat_id
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._api_url("sendAnimation"),
                    json={
                        "chat_id": chat_id,
                        "animation": gif_url,
                        "caption": caption
                    },
                    timeout=30.0
                )
            result = response.json()

            # Save sent message to history
            if result.get("ok"):
                self._save_message("sent", caption or "[GIF]", "gif",
                                 {"chat_id": chat_id, "gif_url": gif_url})

            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def send_typing_action(self, chat_id: str = None) -> None:
        """Send 'typing...' indicator."""
        chat_id = chat_id or self.default_chat_id
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._api_url("sendChatAction"),
                    json={"chat_id": chat_id, "action": "typing"},
                    timeout=5.0
                )
        except Exception:
            pass

    # =========================================================================
    # RECEIVING MESSAGES
    # =========================================================================

    async def delete_webhook(self) -> bool:
        """Delete any existing webhook (required before using getUpdates)."""
        if not self.is_configured:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._api_url("deleteWebhook"),
                    json={"drop_pending_updates": False},
                    timeout=10.0
                )
            result = response.json()
            return result.get("ok", False)
        except Exception:
            return False

    async def get_file_path(self, file_id: str) -> Optional[str]:
        """Get the download path for a file from Telegram."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._api_url("getFile"),
                    params={"file_id": file_id},
                    timeout=10.0
                )
            result = response.json()
            if result.get("ok"):
                return result["result"]["file_path"]
        except Exception as e:
            print(f"Failed to get file path: {e}")
        return None

    async def download_file(self, file_id: str, dest_path: str) -> bool:
        """Download a file from Telegram to local path."""
        try:
            remote_path = await self.get_file_path(file_id)
            if not remote_path:
                return False
            
            download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{remote_path}"
            async with httpx.AsyncClient() as client:
                response = await client.get(download_url, timeout=30.0)
                if response.status_code == 200:
                    with open(dest_path, "wb") as f:
                        f.write(response.content)
                    return True
        except Exception as e:
            print(f"Download failed: {e}")
        return False

    async def get_updates(self, offset: int = None, limit: int = 100) -> List[dict]:
        """Poll for new messages (getUpdates method)."""
        if not self.is_configured:
            return []

        params = {
            "limit": limit, 
            "timeout": 30,
            "allowed_updates": ["message", "edited_message", "callback_query"]
        }
        if offset:
            params["offset"] = offset

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._api_url("getUpdates"),
                    json=params,
                    timeout=httpx.Timeout(35.0, connect=5.0, read=35.0)
                )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"Telegram getUpdates failed: {e}")
            return []

        if not result.get("ok"):
            return []

        return result.get("result", [])

    def parse_update(self, update: dict) -> Optional[TelegramMessage]:
        """Parse a Telegram update into a TelegramMessage."""
        msg_data = update.get("message") or update.get("edited_message")
        if not msg_data:
            return None

        chat_id = str(msg_data.get("chat", {}).get("id", ""))
        sender = msg_data.get("from", {}).get("username") or \
                 msg_data.get("from", {}).get("first_name", "unknown")
        text = msg_data.get("text", "") or msg_data.get("caption", "")

        # Check for media
        photo = msg_data.get("photo")
        photo_file_id = photo[-1].get("file_id") if photo else None

        document = msg_data.get("document")
        document_file_id = document.get("file_id") if document else None

        # Save incoming message to history
        if text:
            msg_type = "photo" if photo else "document" if document else "text"
            self._save_message("received", text, msg_type, {"sender": sender, "chat_id": chat_id})

        return TelegramMessage(
            message_id=msg_data.get("message_id", 0),
            chat_id=chat_id,
            sender=sender,
            text=text,
            has_photo=bool(photo),
            photo_file_id=photo_file_id,
            has_document=bool(document),
            document_file_id=document_file_id,
            metadata={
                "update_id": update.get("update_id"),
                "raw": msg_data
            }
        )

    # =========================================================================
    # GIPHY INTEGRATION
    # =========================================================================

    async def search_gif(self, query: str, limit: int = 1) -> Optional[str]:
        """Search for a GIF on Giphy and return the URL."""
        if not GIPHY_API_KEY:
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.giphy.com/v1/gifs/search",
                    params={
                        "api_key": GIPHY_API_KEY,
                        "q": query,
                        "limit": limit,
                        "rating": "pg-13"
                    },
                    timeout=10.0
                )
            result = response.json()
            if result.get("data"):
                return result["data"][0]["images"]["original"]["url"]
        except Exception as e:
            print(f"Giphy search failed: {e}")
        return None

    async def send_gif_search(self, query: str, caption: str = "", chat_id: str = None) -> dict:
        """Search for a GIF and send it."""
        gif_url = await self.search_gif(query)
        if gif_url:
            return await self.send_gif(gif_url, caption or f"Here's a {query} GIF!", chat_id)
        return {"ok": False, "error": f"No GIF found for '{query}'"}

    # =========================================================================
    # PARLAY SCREENSHOT ANALYSIS (PrizePicks)
    # =========================================================================

    async def analyze_parlay_text(self, text: str) -> dict:
        """
        Analyze a text-based parlay request by calling the Parlay Agent.
        """
        import subprocess
        import json
        import sys
        
        try:
            # Use sys.executable to ensure we use the same python env
            cmd = [sys.executable, "agents/parlay_agent.py", "--text", text]
            
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if proc.returncode != 0:
                print(f"Parlay Agent Error: {proc.stderr}")
                return {"error": f"Agent failed: {proc.stderr}"}
                
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON from agent: {proc.stdout}"}
                
        except Exception as e:
            return {"error": f"Text analysis failed: {str(e)}"}

    async def analyze_parlay_screenshot(self, file_id: str) -> dict:
        """
        Analyze a parlay screenshot by calling the Parlay Agent.
        """
        import subprocess
        import json
        import tempfile
        import sys
        from pathlib import Path
        
        # Download the image
        temp_path = Path(tempfile.gettempdir()) / f"parlay_{file_id}.jpg"
        success = await self.download_file(file_id, str(temp_path))
        
        if not success:
            return {"error": "Failed to download image from Telegram"}
            
        try:
            # Call Agent
            cmd = [sys.executable, "agents/parlay_agent.py", "--image", str(temp_path)]
            
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if proc.returncode != 0:
                print(f"Parlay Agent Error: {proc.stderr}")
                return {"error": f"Agent failed: {proc.stderr}"}
                
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON from agent: {proc.stdout}"}

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}
        finally:
            # Cleanup temp file
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

    async def analyze_general_image(self, file_id: str, prompt: str = "What is in this image? Be concise.") -> str:
        """
        Analyze any image using Gemini 2.0 Vision.
        """
        import tempfile
        from pathlib import Path
        import os
        from google import genai
        from google.genai import types

        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        if not GEMINI_API_KEY:
            return "Error: GEMINI_API_KEY not configured."

        # Download
        temp_path = Path(tempfile.gettempdir()) / f"vision_{file_id}.jpg"
        success = await self.download_file(file_id, str(temp_path))
        
        if not success:
            return "Error: Failed to download image from Telegram."

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Read image bytes
            with open(temp_path, "rb") as f:
                image_bytes = f.read()

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ]
            )
            return response.text
            
        except Exception as e:
            return f"Vision Error: {str(e)}"
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_telegram_instance: Optional[TelegramService] = None

def get_telegram_service() -> TelegramService:
    """Get or create the Telegram service singleton."""
    global _telegram_instance
    if _telegram_instance is None:
        _telegram_instance = TelegramService()
    return _telegram_instance
