import json
import os
import logging
from typing import Dict, Optional, List
from core.tasks.model import Task, TaskStatus

logger = logging.getLogger("athena.tasks")

class TaskManager:
    """
    Manages the lifecycle of user tasks.
    Persists to data/tasks.json.
    """
    
    FILE_PATH = "data/tasks.json"
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._load()
        
    def create_task(self, intent: str, slots: Dict = {}, confidence: float = 1.0) -> Task:
        """Spawn a new task."""
        task = Task(intent=intent, slots=slots, confidence=confidence)
        self._tasks[task.task_id] = task
        self._save()
        logger.info(f"Created Task {task.task_id} ({intent})")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_task_slot(self, task_id: str, key: str, value: str) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
            
        task.slots[key] = value
        task.updated_at = task.updated_at.now() # Update timestamp
        self._save()
        return task
        
    def set_status(self, task_id: str, status: str):
        task = self.get_task(task_id)
        if task:
            task.status = status
            self._save()

    def update_progress(self, task_id: str, step: str, progress_pct: int = 0):
        """Update task progress. Implements 'never silent' contract."""
        task = self.get_task(task_id)
        if task:
            task.slots["_progress_step"] = step
            task.slots["_progress_pct"] = progress_pct
            task.updated_at = task.updated_at.now()
            self._save()
            logger.info(f"Task {task_id}: {step} ({progress_pct}%)")
            
    def set_result(self, task_id: str, result_ref: str, summary: str):
        """Store task result. Implements 'never silent' contract."""
        task = self.get_task(task_id)
        if task:
            task.slots["_result_ref"] = result_ref
            task.slots["_summary"] = summary
            task.status = TaskStatus.COMPLETED
            task.updated_at = task.updated_at.now()
            self._save()
            logger.info(f"Task {task_id} COMPLETED: {summary[:50]}...")
            
    def get_status_report(self, task_id: str) -> str:
        """Get a formatted status report for a task. Never return empty."""
        task = self.get_task(task_id)
        if not task:
            return f"Task '{task_id}' not found. Use /tasks to list active tasks."
        
        step = task.slots.get("_progress_step", "Unknown")
        pct = task.slots.get("_progress_pct", 0)
        summary = task.slots.get("_summary", "No summary yet.")
        
        lines = [
            f"📋 **Task {task_id}** ({task.intent})",
            f"   Status: {task.status}",
            f"   Progress: {step} ({pct}%)",
        ]
        
        if task.status == TaskStatus.COMPLETED:
            lines.append(f"   Summary: {summary}")
            if "_result_ref" in task.slots:
                lines.append(f"   Result: {task.slots['_result_ref']}")
        
        return "\n".join(lines)

    def list_active_tasks(self) -> List[Task]:
        return [
            t for t in self._tasks.values() 
            if t.status in [TaskStatus.DRAFT, TaskStatus.READY, TaskStatus.RUNNING]
        ]
        
    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.FILE_PATH), exist_ok=True)
            data = {tid: t.model_dump(mode='json') for tid, t in self._tasks.items()}
            with open(self.FILE_PATH, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
            
    def _load(self):
        if not os.path.exists(self.FILE_PATH):
            return
        try:
            with open(self.FILE_PATH, 'r') as f:
                data = json.load(f)
                for tid, tdata in data.items():
                    self._tasks[tid] = Task(**tdata)
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
