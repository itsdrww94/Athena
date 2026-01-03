import time
from typing import Dict, Any, List
try:
    import pyautogui
except ImportError:
    pyautogui = None

class ActionAgent:
    """
    Agent: The Body.
    Wraps: PyAutoGUI
    Capabilities: Mouse movement, keyboard input, screenshotting.
    """
    
    def __init__(self):
        self._enabled = pyautogui is not None
        if self._enabled:
            # Safety checks
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 1.0 # 1 second pause between actions

    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a physical desktop action.
        """
        if not self._enabled:
            return {"error": "PyAutoGUI not installed."}

        try:
            if action_name == "screenshot":
                path = params.get("path", "screenshot.png")
                pyautogui.screenshot(path)
                return {"status": "success", "file": path}
            
            elif action_name == "type":
                text = params.get("text", "")
                interval = params.get("interval", 0.1)
                pyautogui.write(text, interval=interval)
                return {"status": "success", "typed": text}
            
            elif action_name == "click":
                x = params.get("x")
                y = params.get("y")
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                else:
                    pyautogui.click()
                return {"status": "success", "action": "click"}
                
            elif action_name == "locate_on_screen":
                image_path = params.get("image_path")
                location = pyautogui.locateOnScreen(image_path)
                return {"status": "success", "location": location}
                
            return {"error": f"Unknown action: {action_name}"}

        except Exception as e:
            return {"error": str(e)}
