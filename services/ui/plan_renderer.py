from typing import Dict, Any, List, Tuple
from core.tasks.model import Task, TaskStatus

class PlanRenderer:
    """
    Renders a Task into a Telegram Message (Text + Buttons).
    Returns raw JSON-compatible dicts for Telegram API.
    """
    
    @staticmethod
    def render(task: Task) -> Tuple[str, Dict[str, Any]]:
        # 1. Build Text Card
        icon = "🎫"
        if task.status == TaskStatus.DRAFT: icon = "📝"
        elif task.status == TaskStatus.READY: icon = "⚡"
        
        text = f"{icon} **Task: {task.intent}**\n"
        text += f"Status: `{task.status}`\n\n"
        
        # Slots
        if task.slots:
            text += "**Parameters:**\n"
            for k, v in task.slots.items():
                text += f"• {k}: {v}\n"
        else:
            text += "(No parameters set)\n"
            
        # Assumptions
        if task.assumptions:
            text += "\n**Assumptions:**\n"
            for k, v in task.assumptions.items():
                text += f"• {k}: {v} (Auto)\n"
                
        text += "\n----------------"
        
        # 2. Build Buttons (InlineKeyboardMarkup JSON structure)
        # https://core.telegram.org/bots/api#inlinekeyboardmarkup
        tid = task.task_id
        inline_keyboard = []
        
        if task.status in [TaskStatus.DRAFT, TaskStatus.READY]:
            # Main Action Row
            row1 = [
                {"text": "✅ Confirm", "callback_data": f"confirm:{tid}"},
                {"text": "❌ Cancel", "callback_data": f"cancel:{tid}"}
            ]
            inline_keyboard.append(row1)
            
            # Edit Row
            row2 = [
                {"text": "✏️ Edit Details", "callback_data": f"edit_menu:{tid}"},
                {"text": "🤔 Why?", "callback_data": f"why:{tid}"}
            ]
            inline_keyboard.append(row2)
            
        elif task.status == TaskStatus.RUNNING:
            inline_keyboard.append([{"text": "⏳ Running...", "callback_data": "noop"}])
            
        elif task.status == TaskStatus.COMPLETED:
            # Feedback Row
            row_fb = [
                {"text": "⭐ Win", "callback_data": f"fb_win:{tid}"},
                {"text": "🌀 Spiral", "callback_data": f"fb_spiral:{tid}"},
                {"text": "👎 Poor", "callback_data": f"fb_bad:{tid}"}
            ]
            inline_keyboard.append(row_fb)
            
            # Check if we should propose saving to semantic memory
            try:
                from core.memory.policy import MemoryWritePolicy
                if MemoryWritePolicy.should_propose_save(task.intent, task.slots):
                    save_row = [
                        {"text": "💾 Save as Preference", "callback_data": f"save_pref:{tid}"},
                        {"text": "🚫 Don't Save", "callback_data": f"skip_save:{tid}"}
                    ]
                    inline_keyboard.append(save_row)
            except Exception:
                pass

        return text, {"inline_keyboard": inline_keyboard}
