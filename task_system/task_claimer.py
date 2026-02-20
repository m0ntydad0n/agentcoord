from typing import Optional
import threading
from datetime import datetime
from .task_repository import TaskRepository, Task


class TaskClaimer:
    """Handles task claiming logic with atomic operations."""
    
    def __init__(self, task_repository: TaskRepository):
        self._repository = task_repository
        self._lock = threading.RLock()
    
    def claim_task(self, task_id: str, claimer_id: str) -> bool:
        """
        Atomically claim a task for processing.
        Returns True if successfully claimed, False if already claimed or not found.
        """
        with self._lock:
            task = self._repository.get(task_id)
            if not task:
                return False
            
            # Check if task is available for claiming
            if task.status != "pending" or task.claimed_by is not None:
                return False
            
            # Atomically claim the task
            task.claimed_by = claimer_id
            task.claimed_at = datetime.utcnow()
            task.status = "claimed"
            return True
    
    def release_task(self, task_id: str, claimer_id: str = None) -> bool:
        """
        Release a claimed task back to pending status.
        If claimer_id is provided, only release if claimed by that claimer.
        """
        with self._lock:
            task = self._repository.get(task_id)
            if not task:
                return False
            
            # If claimer_id specified, verify ownership
            if claimer_id and task.claimed_by != claimer_id:
                return False
            
            # Release the task
            task.claimed_by = None
            task.claimed_at = None
            task.status = "pending"
            return True
    
    def complete_task(self, task_id: str, claimer_id: str = None) -> bool:
        """Mark a task as completed."""
        with self._lock:
            task = self._repository.get(task_id)
            if not task:
                return False
            
            # If claimer_id specified, verify ownership
            if claimer_id and task.claimed_by != claimer_id:
                return False
            
            task.status = "completed"
            return True