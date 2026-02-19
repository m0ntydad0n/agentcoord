"""
Task queue operations using Redis Sorted Sets for priority ordering.

Tasks are stored in a priority queue and can be claimed atomically by agents.
"""

import json
import uuid
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Represents a task in the coordination system."""
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: int  # 1-5, 5 is highest
    created_at: str
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    tags: List[str] = None
    depends_on: List[str] = None
    blocking: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.depends_on is None:
            self.depends_on = []
        if self.blocking is None:
            self.blocking = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create Task from Redis dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            status=TaskStatus(data["status"]),
            priority=int(data["priority"]),
            created_at=data["created_at"],
            claimed_by=data.get("claimed_by"),
            claimed_at=data.get("claimed_at"),
            completed_at=data.get("completed_at"),
            tags=json.loads(data.get("tags", "[]")),
            depends_on=json.loads(data.get("depends_on", "[]")),
            blocking=json.loads(data.get("blocking", "[]"))
        )


class TaskQueue:
    """
    Redis-based task queue with priority ordering and atomic claiming.

    Uses Sorted Set for priority queue (score = priority * 1000000 + timestamp)
    and Hashes for task details.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "tasks:pending"

    def create_task(
        self,
        title: str,
        description: str,
        priority: int = 3,
        tags: Optional[List[str]] = None,
        depends_on: Optional[List[str]] = None
    ) -> Task:
        """Create a new task and add to queue."""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags=tags or [],
            depends_on=depends_on or []
        )

        # Store task details in hash
        task_key = f"task:{task.id}"
        task_dict = task.to_dict()
        # Convert lists to JSON strings for Redis
        task_dict["tags"] = json.dumps(task_dict["tags"])
        task_dict["depends_on"] = json.dumps(task_dict["depends_on"])
        task_dict["blocking"] = json.dumps(task_dict["blocking"])
        task_dict["status"] = task_dict["status"].value

        self.redis.hset(task_key, mapping=task_dict)

        # Add to priority queue
        # Score = priority * 1000000 + timestamp (for tiebreaking)
        score = priority * 1000000 + int(time.time())
        self.redis.zadd(self.queue_key, {task.id: score})

        logger.info(f"Created task {task.id}: {title} (priority {priority})")
        return task

    def claim_task(
        self,
        agent_id: str,
        tags: Optional[List[str]] = None
    ) -> Optional[Task]:
        """
        Atomically claim the highest-priority available task.

        If tags are specified, only claim tasks matching those tags.
        """
        # Get highest priority task (ZREVRANGE returns highest scores first)
        task_ids = self.redis.zrevrange(self.queue_key, 0, -1)

        for task_id in task_ids:
            task = self.get_task(task_id)
            if not task:
                continue

            # Filter by tags if specified
            if tags and not any(tag in task.tags for tag in tags):
                continue

            # Check dependencies
            if task.depends_on and not self._dependencies_complete(task.depends_on):
                continue

            # Attempt atomic claim
            # Remove from queue and mark as claimed
            removed = self.redis.zrem(self.queue_key, task_id)
            if removed:
                # Successfully claimed
                task.status = TaskStatus.CLAIMED
                task.claimed_by = agent_id
                task.claimed_at = datetime.now(timezone.utc).isoformat()

                self.update_task(task)
                logger.info(f"Agent {agent_id} claimed task {task.id}: {task.title}")
                return task

        # No tasks available
        return None

    def update_task(self, task: Task):
        """Update task details in Redis."""
        task_key = f"task:{task.id}"
        task_dict = task.to_dict()
        task_dict["tags"] = json.dumps(task_dict["tags"])
        task_dict["depends_on"] = json.dumps(task_dict["depends_on"])
        task_dict["blocking"] = json.dumps(task_dict["blocking"])
        task_dict["status"] = task_dict["status"].value

        self.redis.hset(task_key, mapping=task_dict)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID."""
        task_key = f"task:{task_id}"
        data = self.redis.hgetall(task_key)
        if not data:
            return None
        return Task.from_dict(data)

    def list_pending_tasks(self, limit: int = 100) -> List[Task]:
        """List all pending tasks in priority order."""
        task_ids = self.redis.zrevrange(self.queue_key, 0, limit - 1)
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def _dependencies_complete(self, dependency_ids: List[str]) -> bool:
        """Check if all dependency tasks are completed."""
        for dep_id in dependency_ids:
            dep_task = self.get_task(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
