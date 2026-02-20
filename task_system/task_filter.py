from typing import List, Dict
from .task_repository import TaskRepository, Task


class TaskFilter:
    """Handles query operations for tasks."""
    
    def __init__(self, task_repository: TaskRepository):
        self._repository = task_repository
    
    def get_by_status(self, status: str) -> List[Task]:
        """Get all tasks with the specified status."""
        tasks = self._repository.get_all()
        return [task for task in tasks.values() if task.status == status]
    
    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[Task]:
        """
        Get tasks that match the specified tags.
        If match_all=True, task must have all tags.
        If match_all=False, task must have at least one tag.
        """
        tasks = self._repository.get_all()
        result = []
        
        for task in tasks.values():
            if match_all:
                if all(tag in task.tags for tag in tags):
                    result.append(task)
            else:
                if any(tag in task.tags for tag in tags):
                    result.append(task)
        
        return result
    
    def get_by_priority(self, min_priority: int = None, 
                       max_priority: int = None) -> List[Task]:
        """Get tasks within the specified priority range."""
        tasks = self._repository.get_all()
        result = []
        
        for task in tasks.values():
            if min_priority is not None and task.priority < min_priority:
                continue
            if max_priority is not None and task.priority > max_priority:
                continue
            result.append(task)
        
        return result
    
    def get_available_tasks(self) -> List[Task]:
        """Get all tasks available for claiming (pending status, not claimed)."""
        tasks = self._repository.get_all()
        return [
            task for task in tasks.values() 
            if task.status == "pending" and task.claimed_by is None
        ]
    
    def get_by_claimer(self, claimer_id: str) -> List[Task]:
        """Get all tasks claimed by a specific claimer."""
        tasks = self._repository.get_all()
        return [task for task in tasks.values() if task.claimed_by == claimer_id]