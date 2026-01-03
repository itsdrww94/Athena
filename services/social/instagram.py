"""
Instagram Tool (Stub)
=====================
Placeholder for Instagram integration.
Currently BLOCKED by default in tool registry.
"""

from typing import Optional, Dict, Any

class InstagramClient:
    """Instagram client stub."""
    
    def __init__(self):
        self.is_connected = False
        
    def post_image(self, image_path: str, caption: str) -> Dict[str, Any]:
        """
        Post an image to Instagram.
        
        Args:
            image_path: Path to image file
            caption: Post caption
            
        Returns:
            Dict with success status
        """
        # This would use instagrapi or similar
        return {
            "success": False,
            "error": "Instagram posting not yet implemented",
            "requires_approval": True
        }

def post_instagram(image_path: str, caption: str) -> str:
    """Tool function for Instagram posting."""
    return str(InstagramClient().post_image(image_path, caption))
