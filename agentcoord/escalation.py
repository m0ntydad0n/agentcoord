"""
Escalation coordinator for automatic task retry and escalation.

Manages failed tasks according to retry policies and escalates when needed.
"""

import json
import time
import threading
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .tasks import Task, TaskQueue, TaskStatus

logger = logging.getLogger(__name__)


class EscalationCoordinator:
    """
    Manages task escalation and retry logic.

    Subscribes to escalation events and handles failed tasks according to
    their retry policy. Runs a background thread to process retry queue.
    """

    def __init__(
        self,
        redis_client,
        task_queue: Optional[TaskQueue] = None,
        escalation_channel: str = "channel:escalations",
        poll_interval: int = 5
    ):
        """
        Initialize escalation coordinator.

        Args:
            redis_client: Redis client instance
            task_queue: TaskQueue instance (created if not provided)
            escalation_channel: Redis pub/sub channel for escalations
            poll_interval: Retry queue polling interval in seconds
        """
        self.redis = redis_client
        self.task_queue = task_queue or TaskQueue(redis_client)
        self.escalation_channel = escalation_channel
        self.poll_interval = poll_interval

        self.pubsub = self.redis.pubsub()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._poll_thread: Optional[threading.Thread] = None

    def start_monitoring(self):
        """Start background monitoring of escalation events and retry queue."""
        if self._monitoring:
            logger.warning("Escalation monitoring already started")
            return

        self._monitoring = True

        # Subscribe to escalation channel
        self.pubsub.subscribe(self.escalation_channel)

        # Start event monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_escalations,
            daemon=True,
            name="EscalationMonitor"
        )
        self._monitor_thread.start()

        # Start retry queue polling thread
        self._poll_thread = threading.Thread(
            target=self._poll_retry_queue,
            daemon=True,
            name="RetryQueuePoller"
        )
        self._poll_thread.start()

        logger.info("Escalation coordinator started monitoring")

    def stop_monitoring(self):
        """Stop background monitoring."""
        if not self._monitoring:
            return

        self._monitoring = False
        self.pubsub.unsubscribe(self.escalation_channel)
        self.pubsub.close()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        if self._poll_thread:
            self._poll_thread.join(timeout=5)

        logger.info("Escalation coordinator stopped monitoring")

    def _monitor_escalations(self):
        """Background thread to monitor escalation events."""
        logger.info("Escalation event monitor started")

        for message in self.pubsub.listen():
            if not self._monitoring:
                break

            if message["type"] != "message":
                continue

            try:
                event = json.loads(message["data"])
                self._handle_escalation_event(event)
            except Exception as e:
                logger.error(f"Error handling escalation event: {e}", exc_info=True)

    def _handle_escalation_event(self, event: Dict[str, Any]):
        """
        Handle an escalation event.

        Args:
            event: Escalation event dictionary
        """
        event_type = event.get("event_type")
        task_id = event.get("task_id")

        logger.info(f"Received escalation event: {event_type} for task {task_id}")

        if event_type == "task_failed":
            self.handle_failed_task(task_id, event.get("reason", "Unknown error"))

    def _poll_retry_queue(self):
        """Background thread to poll retry queue and move ready tasks to pending."""
        logger.info("Retry queue poller started")

        while self._monitoring:
            try:
                self.task_queue.process_retry_queue()
            except Exception as e:
                logger.error(f"Error processing retry queue: {e}", exc_info=True)

            time.sleep(self.poll_interval)

    def handle_failed_task(self, task_id: str, error: str) -> str:
        """
        Handle a failed task according to its retry policy.

        Args:
            task_id: The task that failed
            error: Error message/reason for failure

        Returns:
            Action taken: "retried", "escalated", "archived"
        """
        task = self.task_queue.get_task(task_id)
        if not task:
            logger.error(f"Cannot handle failed task {task_id}: task not found")
            return "error"

        logger.info(
            f"Handling failed task {task_id}: retry_count={task.retry_count}, "
            f"max_retries={task.max_retries}, policy={task.retry_policy}"
        )

        # Check retry policy
        if task.retry_policy == "none":
            # No retries, escalate immediately
            self.escalate_task(task_id, f"No retry policy - {error}")
            return "escalated"

        # Check if we've exceeded max retries
        if task.retry_count >= task.max_retries:
            self.escalate_task(task_id, f"Max retries exceeded ({task.retry_count}/{task.max_retries}) - {error}")
            return "escalated"

        # Calculate retry delay
        delay = self._calculate_retry_delay(task)
        self.retry_task(task_id, delay)
        return "retried"

    def _calculate_retry_delay(self, task: Task) -> int:
        """
        Calculate retry delay based on retry policy.

        Args:
            task: Task to calculate delay for

        Returns:
            Delay in seconds
        """
        if task.retry_policy == "linear":
            return task.retry_delay_base
        elif task.retry_policy == "exponential":
            # Exponential backoff: base * (2 ^ retry_count)
            delay = task.retry_delay_base * (2 ** task.retry_count)
            # Cap at 1 hour
            return min(delay, 3600)
        else:
            # Default to linear
            return task.retry_delay_base

    def escalate_task(self, task_id: str, reason: str):
        """
        Manually escalate a task to ESCALATED state.

        Args:
            task_id: Task to escalate
            reason: Reason for escalation
        """
        self.task_queue.escalate_task(task_id, reason)
        logger.info(f"Task {task_id} escalated: {reason}")

    def retry_task(self, task_id: str, delay: Optional[int] = None):
        """
        Schedule a retry for a failed task.

        Args:
            task_id: Task to retry
            delay: Optional delay in seconds (calculated from policy if not provided)
        """
        task = self.task_queue.get_task(task_id)
        if not task:
            logger.error(f"Cannot retry task {task_id}: task not found")
            return

        if delay is None:
            delay = self._calculate_retry_delay(task)

        retry_task = self.task_queue.schedule_retry(task, delay)
        logger.info(
            f"Scheduled retry for task {task_id} -> {retry_task.id} "
            f"in {delay}s (attempt {retry_task.retry_count}/{retry_task.max_retries})"
        )

    def get_escalated_tasks(self) -> List[Task]:
        """
        Retrieve all currently escalated tasks.

        Returns:
            List of escalated tasks
        """
        return self.task_queue.get_escalated_tasks()

    def archive_task(self, task_id: str, reason: str):
        """
        Move task to dead letter queue.

        Args:
            task_id: Task to archive
            reason: Reason for archival
        """
        task = self.task_queue.get_task(task_id)
        if not task:
            logger.error(f"Cannot archive task {task_id}: task not found")
            return

        # Remove from escalated set if present
        self.redis.zrem("tasks:escalated", task_id)

        # Add to dead letter queue
        archive_timestamp = int(time.time())
        self.redis.zadd("tasks:dlq", {task_id: archive_timestamp})

        # Add archive reason to history
        task.escalation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": task.retry_count,
            "reason": reason,
            "action": "archived"
        })

        self.task_queue.update_task(task)
        logger.info(f"Task {task_id} archived to DLQ: {reason}")

    def get_dead_letter_queue(self) -> List[Task]:
        """
        Retrieve tasks in dead letter queue.

        Returns:
            List of archived tasks
        """
        task_ids = self.redis.zrevrange("tasks:dlq", 0, -1)
        tasks = []
        for task_id in task_ids:
            task = self.task_queue.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def get_retry_queue(self) -> List[Dict[str, Any]]:
        """
        Get tasks in retry queue with scheduled times.

        Returns:
            List of dicts with task and scheduled_time
        """
        current_time = int(time.time())
        task_data = self.redis.zrange("tasks:retry", 0, -1, withscores=True)

        results = []
        for task_id, scheduled_timestamp in task_data:
            task = self.task_queue.get_task(task_id)
            if task:
                results.append({
                    "task": task,
                    "scheduled_time": scheduled_timestamp,
                    "seconds_until_retry": max(0, int(scheduled_timestamp - current_time))
                })

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get escalation system statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "escalated_count": self.redis.zcard("tasks:escalated"),
            "retry_queue_count": self.redis.zcard("tasks:retry"),
            "dlq_count": self.redis.zcard("tasks:dlq"),
            "monitoring": self._monitoring
        }
