"""Enhanced task queue with metrics integration."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime

from .metrics import metrics

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Priority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Task:
    """Task representation with metrics integration."""
    
    id: str
    type: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def mark_running(self, worker_id: str):
        """Mark task as running and start metrics timer."""
        self.status = TaskStatus.RUNNING
        self.worker_id = worker_id
        self.started_at = datetime.utcnow()
        metrics.start_task_timer(self.id)
        logger.info(f"Task {self.id} started by worker {worker_id}")
    
    def mark_completed(self, result: Optional[Dict[str, Any]] = None):
        """Mark task as completed and record metrics."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        metrics.record_task_completed(self.id, self.type)
        logger.info(f"Task {self.id} completed successfully")
    
    def mark_failed(self, error_message: str, error_type: str = "execution_error"):
        """Mark task as failed and record metrics."""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        metrics.record_task_failed(self.id, self.type, error_type)
        logger.error(f"Task {self.id} failed: {error_message}")

class TaskQueue:
    """Task queue with Prometheus metrics integration."""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.local_queue = asyncio.Queue()
        self.tasks: Dict[str, Task] = {}
        self._running = False
        self._monitor_task = None
        
    async def create_task(self, task_type: str, payload: Dict[str, Any], 
                         priority: Priority = Priority.NORMAL) -> Task:
        """Create a new task with metrics tracking."""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            type=task_type,
            payload=payload,
            priority=priority
        )
        
        # Store task
        self.tasks[task_id] = task
        
        # Add to queue
        await self.local_queue.put(task)
        
        # Record metrics
        metrics.record_task_created(task_type)
        self._update_pending_tasks_metric()
        
        logger.info(f"Created task {task_id} of type {task_type}")
        return task
    
    async def get_next_task(self, worker_id: str) -> Optional[Task]:
        """Get next task from queue with priority ordering."""
        try:
            task = await asyncio.wait_for(self.local_queue.get(), timeout=1.0)
            task.mark_running(worker_id)
            self._update_pending_tasks_metric()
            return task
        except asyncio.TimeoutError:
            return None
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
    
    def get_running_tasks(self) -> List[Task]:
        """Get all running tasks."""
        return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]
    
    def _update_pending_tasks_metric(self):
        """Update pending tasks metrics by priority."""
        pending = self.get_pending_tasks()
        priority_counts = {p.value: 0 for p in Priority}
        
        for task in pending:
            priority_counts[task.priority.value] += 1
            
        for priority, count in priority_counts.items():
            metrics.set_pending_tasks(count, priority)
    
    async def start_monitoring(self):
        """Start background task monitoring."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self):
        """Background loop to update metrics."""
        while self._running:
            try:
                self._update_pending_tasks_metric()
                await asyncio.sleep(10)  # Update every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)