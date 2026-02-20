from typing import Optional, Dict, Any
import threading
import uuid
from datetime import datetime


class Task:
    def __init__(self, task_id: str, data: Dict[str, Any], priority: int = 0, 
                 tags: list = None, status: str = "pending"):
        self.id = task_id
        self.data = data
        self.priority = priority
        self.tags = tags or []
        self.status = status
        self.created_at = datetime.utcnow()
        self.claimed_by = None
        self.claimed_at = None


class TaskRepository:
    """Handles CRUD operations for tasks - data access only."""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()
    
    def create(self, data: Dict[str, Any], priority: int = 0, 
               tags: list = None, task_id: str = None) -> str:
        """Create a new task and return its ID."""
        with self._lock:
            task_id = task_id or str(uuid.uuid4())
            task = Task(task_id, data, priority, tags)
            self._tasks[task_id] = task
            return task_id
    
    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update(self, task_id: str, **updates) -> bool:
        """Update task fields. Returns True if task exists and was updated."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            return True
    
    def delete(self, task_id: str) -> bool:
        """Delete a task. Returns True if task existed and was deleted."""
        with self._lock:
            return self._tasks.pop(task_id, None) is not None
    
    def get_all(self) -> Dict[str, Task]:
        """Get all tasks (used by other components)."""
        with self._lock:
            return self._tasks.copy()