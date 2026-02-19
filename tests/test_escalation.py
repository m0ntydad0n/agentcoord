"""Tests for escalation system."""

import time
import json
import pytest
from agentcoord.tasks import Task, TaskQueue, TaskStatus
from agentcoord.escalation import EscalationCoordinator


@pytest.fixture
def redis_client(fake_redis):
    """Provide a fake Redis client."""
    return fake_redis


@pytest.fixture
def task_queue(redis_client):
    """Create a TaskQueue instance."""
    return TaskQueue(redis_client)


@pytest.fixture
def coordinator(redis_client, task_queue):
    """Create an EscalationCoordinator instance."""
    return EscalationCoordinator(redis_client, task_queue)


def test_task_with_escalation_fields(task_queue):
    """Test creating task with escalation fields."""
    task = task_queue.create_task(
        title="Test task",
        description="Test description",
        retry_policy="exponential",
        max_retries=5,
        retry_delay_base=30
    )

    assert task.retry_count == 0
    assert task.max_retries == 5
    assert task.retry_policy == "exponential"
    assert task.retry_delay_base == 30
    assert task.escalation_history == []

    # Verify task can be retrieved with escalation fields
    retrieved = task_queue.get_task(task.id)
    assert retrieved.retry_count == 0
    assert retrieved.max_retries == 5
    assert retrieved.retry_policy == "exponential"
    assert retrieved.retry_delay_base == 30


def test_fail_task_publishes_event(task_queue, redis_client):
    """Test that failing a task publishes escalation event."""
    task = task_queue.create_task(
        title="Test task",
        description="Test"
    )

    # Subscribe to escalation channel
    pubsub = redis_client.pubsub()
    pubsub.subscribe("channel:escalations")
    time.sleep(0.1)  # Let subscription register

    # Fail the task
    task_queue.fail_task(task.id, "Connection timeout")

    # Check event was published
    message = pubsub.get_message(timeout=1)
    while message and message["type"] != "message":
        message = pubsub.get_message(timeout=1)

    assert message is not None
    event = json.loads(message["data"])
    assert event["event_type"] == "task_failed"
    assert event["task_id"] == task.id
    assert event["reason"] == "Connection timeout"


def test_fail_task_updates_status(task_queue):
    """Test that failing a task updates its status."""
    task = task_queue.create_task(
        title="Test task",
        description="Test"
    )

    task_queue.fail_task(task.id, "Error occurred")

    failed_task = task_queue.get_task(task.id)
    assert failed_task.status == TaskStatus.FAILED
    assert len(failed_task.escalation_history) == 1
    assert failed_task.escalation_history[0]["reason"] == "Error occurred"
    assert failed_task.escalation_history[0]["action"] == "failed"


def test_schedule_retry_creates_new_task(task_queue):
    """Test that scheduling retry creates a new task."""
    original_task = task_queue.create_task(
        title="Test task",
        description="Test",
        max_retries=3
    )

    # Fail it once
    task_queue.fail_task(original_task.id, "First failure")
    failed_task = task_queue.get_task(original_task.id)

    # Schedule retry
    retry_task = task_queue.schedule_retry(failed_task, delay=60)

    assert retry_task.id != original_task.id
    assert retry_task.retry_count == 1
    assert retry_task.parent_task_id == original_task.id
    assert retry_task.title == original_task.title
    assert len(retry_task.escalation_history) == 2  # Failed + retried

    # Verify task is in retry queue
    retry_queue = task_queue.get_retry_queue()
    assert len(retry_queue) == 1
    assert retry_queue[0].id == retry_task.id


def test_escalate_task_updates_status(task_queue):
    """Test escalating a task."""
    task = task_queue.create_task(
        title="Test task",
        description="Test"
    )

    task_queue.escalate_task(task.id, "Max retries exceeded")

    escalated = task_queue.get_task(task.id)
    assert escalated.status == TaskStatus.ESCALATED
    assert escalated.escalation_reason == "Max retries exceeded"
    assert escalated.escalated_at is not None
    assert len(escalated.escalation_history) == 1
    assert escalated.escalation_history[0]["action"] == "escalated"


def test_get_escalated_tasks(task_queue):
    """Test retrieving escalated tasks."""
    task1 = task_queue.create_task(title="Task 1", description="Test")
    task2 = task_queue.create_task(title="Task 2", description="Test")
    task3 = task_queue.create_task(title="Task 3", description="Test")

    task_queue.escalate_task(task1.id, "Reason 1")
    task_queue.escalate_task(task3.id, "Reason 3")

    escalated_tasks = task_queue.get_escalated_tasks()
    assert len(escalated_tasks) == 2
    escalated_ids = {t.id for t in escalated_tasks}
    assert task1.id in escalated_ids
    assert task3.id in escalated_ids
    assert task2.id not in escalated_ids


def test_calculate_retry_delay_linear(coordinator):
    """Test linear retry delay calculation."""
    task = Task(
        id="test",
        title="Test",
        description="Test",
        status=TaskStatus.FAILED,
        priority=3,
        created_at="2024-01-01T00:00:00Z",
        retry_policy="linear",
        retry_delay_base=30,
        retry_count=0
    )

    delay = coordinator._calculate_retry_delay(task)
    assert delay == 30

    task.retry_count = 2
    delay = coordinator._calculate_retry_delay(task)
    assert delay == 30  # Still 30, linear


def test_calculate_retry_delay_exponential(coordinator):
    """Test exponential retry delay calculation."""
    task = Task(
        id="test",
        title="Test",
        description="Test",
        status=TaskStatus.FAILED,
        priority=3,
        created_at="2024-01-01T00:00:00Z",
        retry_policy="exponential",
        retry_delay_base=60,
        retry_count=0
    )

    # 60 * (2^0) = 60
    delay = coordinator._calculate_retry_delay(task)
    assert delay == 60

    # 60 * (2^1) = 120
    task.retry_count = 1
    delay = coordinator._calculate_retry_delay(task)
    assert delay == 120

    # 60 * (2^2) = 240
    task.retry_count = 2
    delay = coordinator._calculate_retry_delay(task)
    assert delay == 240

    # Cap at 1 hour
    task.retry_count = 10
    delay = coordinator._calculate_retry_delay(task)
    assert delay == 3600


def test_handle_failed_task_retry(coordinator, task_queue):
    """Test handling failed task with retry."""
    task = task_queue.create_task(
        title="Test task",
        description="Test",
        retry_policy="linear",
        max_retries=3,
        retry_delay_base=30
    )

    task_queue.fail_task(task.id, "Error")
    action = coordinator.handle_failed_task(task.id, "Error")

    assert action == "retried"

    # Check retry queue
    retry_queue = task_queue.get_retry_queue()
    assert len(retry_queue) == 1
    assert retry_queue[0].retry_count == 1


def test_handle_failed_task_escalate_max_retries(coordinator, task_queue):
    """Test handling failed task that exceeded max retries."""
    task = task_queue.create_task(
        title="Test task",
        description="Test",
        retry_policy="exponential",
        max_retries=2,
        retry_delay_base=60
    )

    # Simulate multiple failures
    task_queue.fail_task(task.id, "Error 1")
    coordinator.handle_failed_task(task.id, "Error 1")  # Retry 1

    retry_queue = task_queue.get_retry_queue()
    retry_task = task_queue.get_task(retry_queue[0].id)

    task_queue.fail_task(retry_task.id, "Error 2")
    coordinator.handle_failed_task(retry_task.id, "Error 2")  # Retry 2

    retry_queue = task_queue.get_retry_queue()
    retry_task2 = task_queue.get_task(retry_queue[0].id)

    task_queue.fail_task(retry_task2.id, "Error 3")
    action = coordinator.handle_failed_task(retry_task2.id, "Error 3")  # Should escalate

    assert action == "escalated"

    escalated_tasks = task_queue.get_escalated_tasks()
    assert len(escalated_tasks) == 1


def test_handle_failed_task_no_retry_policy(coordinator, task_queue):
    """Test handling failed task with no retry policy."""
    task = task_queue.create_task(
        title="Test task",
        description="Test",
        retry_policy="none",
        max_retries=3
    )

    task_queue.fail_task(task.id, "Error")
    action = coordinator.handle_failed_task(task.id, "Error")

    assert action == "escalated"

    escalated_tasks = task_queue.get_escalated_tasks()
    assert len(escalated_tasks) == 1


def test_archive_task_to_dlq(coordinator, task_queue):
    """Test archiving task to dead letter queue."""
    task = task_queue.create_task(
        title="Test task",
        description="Test"
    )

    task_queue.escalate_task(task.id, "Failed permanently")
    coordinator.archive_task(task.id, "Unrecoverable error")

    # Check DLQ
    dlq = coordinator.get_dead_letter_queue()
    assert len(dlq) == 1
    assert dlq[0].id == task.id

    # Check history
    archived_task = task_queue.get_task(task.id)
    assert any(h["action"] == "archived" for h in archived_task.escalation_history)


def test_process_retry_queue(task_queue, redis_client):
    """Test processing retry queue to move tasks to pending."""
    task = task_queue.create_task(
        title="Test task",
        description="Test"
    )

    # Manually schedule a retry with immediate time
    task_queue.fail_task(task.id, "Error")
    retry_task = task_queue.schedule_retry(task_queue.get_task(task.id), delay=0)

    time.sleep(1)  # Wait for time to pass

    # Process retry queue
    task_queue.process_retry_queue()

    # Check task is now in pending queue
    pending_tasks = task_queue.list_pending_tasks()
    pending_ids = {t.id for t in pending_tasks}
    assert retry_task.id in pending_ids


def test_get_statistics(coordinator, task_queue):
    """Test getting escalation statistics."""
    # Create various tasks
    task1 = task_queue.create_task(title="Task 1", description="Test")
    task2 = task_queue.create_task(title="Task 2", description="Test")
    task3 = task_queue.create_task(title="Task 3", description="Test")

    # Escalate one
    task_queue.escalate_task(task1.id, "Reason")

    # Schedule retry for another
    task_queue.fail_task(task2.id, "Error")
    task_queue.schedule_retry(task_queue.get_task(task2.id), delay=60)

    # Archive one
    task_queue.escalate_task(task3.id, "Reason")
    coordinator.archive_task(task3.id, "Archive")

    stats = coordinator.get_statistics()
    assert stats["escalated_count"] == 1  # task1 (task3 was archived)
    assert stats["retry_queue_count"] == 1  # task2
    assert stats["dlq_count"] == 1  # task3


def test_get_retry_queue_with_times(coordinator, task_queue):
    """Test getting retry queue with scheduled times."""
    task = task_queue.create_task(title="Test", description="Test")

    task_queue.fail_task(task.id, "Error")
    task_queue.schedule_retry(task_queue.get_task(task.id), delay=120)

    retry_queue = coordinator.get_retry_queue()
    assert len(retry_queue) == 1
    assert retry_queue[0]["task"].retry_count == 1
    assert retry_queue[0]["seconds_until_retry"] > 0


def test_monitoring_lifecycle(coordinator):
    """Test starting and stopping monitoring."""
    assert not coordinator._monitoring

    coordinator.start_monitoring()
    assert coordinator._monitoring
    assert coordinator._monitor_thread is not None
    assert coordinator._poll_thread is not None

    time.sleep(0.5)  # Let threads start

    coordinator.stop_monitoring()
    assert not coordinator._monitoring


def test_escalation_event_handling(coordinator, task_queue, redis_client):
    """Test end-to-end escalation event handling."""
    coordinator.start_monitoring()
    time.sleep(0.5)

    task = task_queue.create_task(
        title="Test task",
        description="Test",
        retry_policy="exponential",
        max_retries=2
    )

    # Fail the task - should trigger coordinator
    task_queue.fail_task(task.id, "Test error")

    time.sleep(1)  # Let coordinator process

    # Should have been retried
    retry_queue = task_queue.get_retry_queue()
    assert len(retry_queue) == 1

    coordinator.stop_monitoring()
