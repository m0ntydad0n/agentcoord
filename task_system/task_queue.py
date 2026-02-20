from typing import Optional, List, Dict, Any
from .task_repository import TaskRepository, Task
from .task_claimer import TaskClaimer
from .task_filter import TaskFilter


class TaskQueue:
    """
    Orchestrator for task management - thin layer that composes other components.
    Maintains backwards compatibility with existing API.
    """
    
    def __init__(self):
        self._repository = TaskRepository()
        self._claimer = TaskClaimer(self._repository)
        self._filter = TaskFilter(self._repository)
    
    # Repository operations (CRUD)
    def add_task(self, data: Dict[str, Any], priority: int = 0, 
                 tags: list = None) -> str:
        """Add a new task to the queue."""
        return self._repository.create(data, priority, tags)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._repository.get(task_id)
    
    def update_task(self, task_id: str, **updates) -> bool:
        """Update a task."""
        return self._repository.update(task_id, **updates)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        return self._repository.delete(task_id)
    
    # Claiming operations
    def claim_task(self, task_id: str, claimer_id: str) -> bool:
        """Claim a task for processing."""
        return self._claimer.claim_task(task_id, claimer_id)
    
    def release_task(self, task_id: str, claimer_id: str = None) -> bool:
        """Release a claimed task."""
        return self._claimer.release_task(task_id, claimer_id)
    
    def complete_task(self, task_id: str, claimer_id: str = None) -> bool:
        """Mark a task as completed."""
        return self._claimer.complete_task(task_id, claimer_id)
    
    # Query operations
    def get_tasks_by_status(self, status: str) -> List[Task]:
        """Get tasks by status."""
        return self._filter.get_by_status(status)
    
    def get_tasks_by_tags(self, tags: List[str], match_all: bool = False) -> List[Task]:
        """Get tasks by tags."""
        return self._filter.get_by_tags(tags, match_all)
    
    def get_tasks_by_priority(self, min_priority: int = None, 
                             max_priority: int = None) -> List[Task]:
        """Get tasks by priority range."""
        return self._filter.get_by_priority(min_priority, max_priority)
    
    def get_available_tasks(self) -> List[Task]:
        """Get all available tasks."""
        return self._filter.get_available_tasks()
    
    def get_claimed_tasks(self, claimer_id: str) -> List[Task]:
        """Get tasks claimed by a specific claimer."""
        return self._filter.get_by_claimer(claimer_id)
    
    # Convenience methods for backwards compatibility
    def size(self) -> int:
        """Get total number of tasks."""
        return len(self._repository.get_all())
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.size() == 0
    
    def clear(self) -> None:
        """Clear all tasks."""
        tasks = list(self._repository.get_all().keys())
        for task_id in tasks:
            self._repository.delete(task_id)