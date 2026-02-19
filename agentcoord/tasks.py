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
    ESCALATED = "escalated"


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
    # Escalation fields
    retry_count: int = 0
    max_retries: int = 3
    retry_policy: str = "exponential"  # "linear", "exponential", "none"
    retry_delay_base: int = 60  # seconds
    escalated_at: Optional[str] = None
    escalation_reason: Optional[str] = None
    escalation_history: List[Dict[str, Any]] = None
    parent_task_id: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.depends_on is None:
            self.depends_on = []
        if self.blocking is None:
            self.blocking = []
        if self.escalation_history is None:
            self.escalation_history = []

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
            claimed_by=data.get("claimed_by") or None,
            claimed_at=data.get("claimed_at") or None,
            completed_at=data.get("completed_at") or None,
            tags=json.loads(data.get("tags") or "[]"),
            depends_on=json.loads(data.get("depends_on") or "[]"),
            blocking=json.loads(data.get("blocking") or "[]"),
            retry_count=int(data.get("retry_count") or 0),
            max_retries=int(data.get("max_retries") or 3),
            retry_policy=data.get("retry_policy") or "exponential",
            retry_delay_base=int(data.get("retry_delay_base") or 60),
            escalated_at=data.get("escalated_at") or None,
            escalation_reason=data.get("escalation_reason") or None,
            escalation_history=json.loads(data.get("escalation_history") or "[]"),
            parent_task_id=data.get("parent_task_id") or None
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
        depends_on: Optional[List[str]] = None,
        retry_policy: str = "exponential",
        max_retries: int = 3,
        retry_delay_base: int = 60
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
            depends_on=depends_on or [],
            retry_policy=retry_policy,
            max_retries=max_retries,
            retry_delay_base=retry_delay_base
        )

        # Store task details in hash
        task_key = f"task:{task.id}"
        task_dict = task.to_dict()
        # Convert lists to JSON strings for Redis
        task_dict["tags"] = json.dumps(task_dict["tags"])
        task_dict["depends_on"] = json.dumps(task_dict["depends_on"])
        task_dict["blocking"] = json.dumps(task_dict["blocking"])
        task_dict["escalation_history"] = json.dumps(task_dict["escalation_history"])
        task_dict["status"] = task_dict["status"].value

        # Redis doesn't accept None values, convert to empty strings
        for key, value in list(task_dict.items()):
            if value is None:
                task_dict[key] = ""

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
        task_dict["escalation_history"] = json.dumps(task_dict["escalation_history"])
        task_dict["status"] = task_dict["status"].value

        # Redis doesn't accept None values, convert to empty strings
        for key, value in list(task_dict.items()):
            if value is None:
                task_dict[key] = ""

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

    def fail_task(self, task_id: str, error: str):
        """
        Mark task as FAILED and publish escalation event.

        Args:
            task_id: The task that failed
            error: Error message/reason for failure
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Cannot fail task {task_id}: task not found")
            return

        # Update task status
        task.status = TaskStatus.FAILED

        # Add to escalation history
        task.escalation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": task.retry_count,
            "reason": error,
            "action": "failed"
        })

        self.update_task(task)

        # Publish escalation event
        event = {
            "event_type": "task_failed",
            "task_id": task.id,
            "task_title": task.title,
            "reason": error,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "retry_policy": task.retry_policy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "claimed_by": task.claimed_by
        }
        self.redis.publish("channel:escalations", json.dumps(event))
        logger.info(f"Task {task_id} failed: {error}")

    def schedule_retry(self, task: Task, delay: int) -> Task:
        """
        Schedule a task for retry after delay seconds.

        Args:
            task: The task to retry
            delay: Delay in seconds before retry

        Returns:
            New task created for retry
        """
        # Create a new task for the retry
        retry_task = Task(
            id=str(uuid.uuid4()),
            title=task.title,
            description=task.description,
            status=TaskStatus.PENDING,
            priority=task.priority,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags=task.tags,
            depends_on=task.depends_on,
            retry_count=task.retry_count + 1,
            max_retries=task.max_retries,
            retry_policy=task.retry_policy,
            retry_delay_base=task.retry_delay_base,
            escalation_history=task.escalation_history.copy(),
            parent_task_id=task.parent_task_id or task.id
        )

        # Add history entry
        retry_task.escalation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_task.retry_count,
            "reason": f"Scheduled retry {retry_task.retry_count}/{retry_task.max_retries}",
            "action": "retried"
        })

        # Store task
        task_key = f"task:{retry_task.id}"
        task_dict = retry_task.to_dict()
        task_dict["tags"] = json.dumps(task_dict["tags"])
        task_dict["depends_on"] = json.dumps(task_dict["depends_on"])
        task_dict["blocking"] = json.dumps(task_dict["blocking"])
        task_dict["escalation_history"] = json.dumps(task_dict["escalation_history"])
        task_dict["status"] = task_dict["status"].value

        for key, value in list(task_dict.items()):
            if value is None:
                task_dict[key] = ""

        self.redis.hset(task_key, mapping=task_dict)

        # Add to retry queue with scheduled time
        retry_timestamp = int(time.time()) + delay
        self.redis.zadd("tasks:retry", {retry_task.id: retry_timestamp})

        logger.info(f"Scheduled retry for task {task.id} -> {retry_task.id} in {delay}s")
        return retry_task

    def escalate_task(self, task_id: str, reason: str):
        """
        Mark task as ESCALATED and add to escalated set.

        Args:
            task_id: Task to escalate
            reason: Reason for escalation
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Cannot escalate task {task_id}: task not found")
            return

        # Update task status
        task.status = TaskStatus.ESCALATED
        task.escalated_at = datetime.now(timezone.utc).isoformat()
        task.escalation_reason = reason

        # Add to escalation history
        task.escalation_history.append({
            "timestamp": task.escalated_at,
            "retry_count": task.retry_count,
            "reason": reason,
            "action": "escalated"
        })

        self.update_task(task)

        # Add to escalated set
        escalation_timestamp = int(time.time())
        self.redis.zadd("tasks:escalated", {task.id: escalation_timestamp})

        # Publish escalation event
        event = {
            "event_type": "task_escalated",
            "task_id": task.id,
            "task_title": task.title,
            "reason": reason,
            "retry_count": task.retry_count,
            "timestamp": task.escalated_at,
            "claimed_by": task.claimed_by
        }
        self.redis.publish("channel:escalations", json.dumps(event))
        logger.info(f"Task {task_id} escalated: {reason}")

    def get_retry_queue(self) -> List[Task]:
        """Get tasks scheduled for retry."""
        task_ids = self.redis.zrange("tasks:retry", 0, -1)
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def get_escalated_tasks(self) -> List[Task]:
        """Get all escalated tasks."""
        task_ids = self.redis.zrevrange("tasks:escalated", 0, -1)
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def process_retry_queue(self):
        """
        Process retry queue - move ready tasks back to pending.
        Called by EscalationCoordinator.
        """
        current_time = int(time.time())
        # Get all tasks ready for retry (score <= current_time)
        ready_tasks = self.redis.zrangebyscore("tasks:retry", 0, current_time)

        for task_id in ready_tasks:
            task = self.get_task(task_id)
            if task:
                # Remove from retry queue
                self.redis.zrem("tasks:retry", task_id)

                # Add to pending queue
                score = task.priority * 1000000 + int(time.time())
                self.redis.zadd(self.queue_key, {task.id: score})

                logger.info(f"Moved task {task_id} from retry to pending queue")
