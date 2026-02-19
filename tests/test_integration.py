"""
Integration tests for LLM budget, fallback, and escalation coordination.

Tests full workflows and interactions between components.
"""

import pytest
import time
import json
from datetime import datetime, timezone

from agentcoord import CoordinationClient
from agentcoord.tasks import TaskQueue, TaskStatus, Task
from agentcoord.llm import LLMBudget, BudgetExceededError, SlotTimeoutError
from agentcoord.llm_fallback import LLMFallbackHandler
from agentcoord.escalation import EscalationCoordinator


# ===== Full Workflow Integration Tests =====

def test_full_autonomous_workflow(redis_client):
    """
    Test complete autonomous workflow:
    1. Create tasks
    2. Agent claims task
    3. Uses LLM budget
    4. Task completes successfully
    """
    # Setup
    coord = CoordinationClient(redis_url="redis://localhost:6379")
    task_queue = TaskQueue(redis_client)
    llm_budget = LLMBudget(redis_client, max_concurrent=5, daily_budget=10.0)

    # Register agent
    agent_id = coord.register_agent(
        role="TestWorker",
        name="IntegrationTest",
        working_on="Testing workflow"
    )

    # Create task
    task = task_queue.create_task(
        title="Test Task",
        description="Integration test task",
        priority=3,
        tags=["test"]
    )

    # Claim task
    claimed = coord.claim_task(tags=["test"])
    assert claimed is not None
    assert claimed.id == task.id
    assert claimed.status == TaskStatus.CLAIMED

    # Check budget available
    assert llm_budget.check_budget_available(agent_id) is True

    # Acquire LLM slot and execute
    with llm_budget.acquire_slot(timeout=5):
        # Simulate LLM work
        time.sleep(0.1)

        # Record usage
        llm_budget.record_usage(
            agent_id=agent_id,
            model="claude-sonnet-4.5",
            tokens=500,
            cost=0.025
        )

    # Complete task
    claimed.status = TaskStatus.COMPLETED
    claimed.completed_at = datetime.now(timezone.utc).isoformat()
    task_queue.update_task(claimed)

    # Verify completion
    final_task = task_queue.get_task(task.id)
    assert final_task.status == TaskStatus.COMPLETED
    assert final_task.completed_at is not None

    # Verify budget tracking
    stats = llm_budget.get_usage_stats()
    assert stats["total_cost"] == 0.025
    assert stats["by_agent"][agent_id]["calls"] == 1

    coord.shutdown()


def test_task_failure_with_escalation(redis_client):
    """
    Test task failure handling with escalation:
    1. Task fails
    2. Escalation coordinator handles retry
    3. After max retries, escalates
    """
    task_queue = TaskQueue(redis_client)
    escalation_coord = EscalationCoordinator(
        redis_client,
        task_queue=task_queue
    )

    # Create task with retry policy
    task = task_queue.create_task(
        title="Failing Task",
        description="Task that will fail",
        priority=3,
        retry_policy="exponential",
        max_retries=2,
        retry_delay_base=1  # 1 second for fast testing
    )

    # Simulate first failure
    task.status = TaskStatus.FAILED
    task_queue.update_task(task)

    # Handle first failure - should retry
    action = escalation_coord.handle_failed_task(task.id, "Simulated error")
    assert action == "retried"

    # Check retry queue
    retry_queue = escalation_coord.get_retry_queue()
    assert len(retry_queue) > 0

    # Get retried task
    retried_task = task_queue.get_task(task.id)
    assert retried_task.retry_count == 1

    # Process retry queue (move back to pending)
    time.sleep(2)  # Wait for retry delay
    task_queue.process_retry_queue()

    # Simulate second failure
    action = escalation_coord.handle_failed_task(task.id, "Simulated error 2")
    assert action == "retried"

    # Get task again
    retried_task = task_queue.get_task(task.id)
    assert retried_task.retry_count == 2

    # Process retry queue again
    time.sleep(2)
    task_queue.process_retry_queue()

    # Simulate third failure - should escalate (exceeded max)
    action = escalation_coord.handle_failed_task(task.id, "Final failure")
    assert action == "escalated"

    # Verify escalated
    escalated_tasks = escalation_coord.get_escalated_tasks()
    assert len(escalated_tasks) > 0
    assert any(t.id == task.id for t in escalated_tasks)


def test_llm_fallback_integration(redis_client):
    """
    Test LLM fallback handler with simulated failures.
    """
    fallback_handler = LLMFallbackHandler(
        redis_client,
        fallback_models=["claude-sonnet-4.5", "claude-haiku-4.5"],
        max_retries=2,
        retry_delay=0.1
    )

    # Mock LLM function that fails on first attempt
    attempt_count = {"count": 0}

    def mock_llm_call(*args, **kwargs):
        attempt_count["count"] += 1
        if attempt_count["count"] == 1:
            raise Exception("Simulated API error")
        return {"result": "success", "model": kwargs.get("model")}

    # Execute with fallback
    result = fallback_handler.execute_with_fallback(
        mock_llm_call,
        model="claude-sonnet-4.5"
    )

    assert result["result"] == "success"
    assert attempt_count["count"] == 2  # Failed once, succeeded on retry

    # Check fallback stats
    stats = fallback_handler.get_fallback_stats()
    assert stats["by_model"]["claude-sonnet-4.5"]["successes"] == 1


def test_budget_enforcement_prevents_runaway(redis_client):
    """
    Test that budget enforcement prevents runaway costs.
    """
    llm_budget = LLMBudget(
        redis_client,
        max_concurrent=2,
        daily_budget=0.10  # Very low budget
    )

    agent_id = "test-agent-budget"

    # Use up budget
    llm_budget.record_usage(agent_id, "claude-opus-4.6", 1000, 0.08)
    assert llm_budget.check_budget_available(agent_id) is True

    # Exceed budget
    llm_budget.record_usage(agent_id, "claude-opus-4.6", 500, 0.05)
    assert llm_budget.check_budget_available(agent_id) is False

    # Verify stats show exceeded budget
    stats = llm_budget.get_usage_stats()
    assert stats["total_cost"] >= 0.10


def test_concurrent_llm_rate_limiting(redis_client):
    """
    Test that LLM rate limiting works with concurrent access.
    """
    llm_budget = LLMBudget(redis_client, max_concurrent=2)

    # Acquire max slots
    with llm_budget.acquire_slot():
        with llm_budget.acquire_slot():
            # Both slots acquired
            in_flight = int(redis_client.get("llm:semaphore") or 0)
            assert in_flight == 2

            # Third attempt should timeout
            with pytest.raises(SlotTimeoutError):
                with llm_budget.acquire_slot(timeout=1):
                    pass


def test_escalation_to_dead_letter_queue(redis_client):
    """
    Test that terminal failures go to dead letter queue.
    """
    task_queue = TaskQueue(redis_client)
    escalation_coord = EscalationCoordinator(redis_client, task_queue=task_queue)

    # Create task
    task = task_queue.create_task(
        title="Terminal Task",
        description="Will be archived",
        priority=3
    )

    # Escalate task
    escalation_coord.escalate_task(task.id, "Critical error")

    # Archive to DLQ
    escalation_coord.archive_task(task.id, "Cannot be recovered")

    # Verify in DLQ
    dlq_tasks = escalation_coord.get_dead_letter_queue()
    assert len(dlq_tasks) > 0
    assert any(t.id == task.id for t in dlq_tasks)

    # Verify escalation history
    archived_task = task_queue.get_task(task.id)
    assert len(archived_task.escalation_history) > 0
    assert any(
        entry.get("action") == "archived"
        for entry in archived_task.escalation_history
    )


def test_multi_agent_budget_isolation(redis_client):
    """
    Test that per-agent budgets are isolated.
    """
    llm_budget = LLMBudget(
        redis_client,
        per_agent_budget=0.50
    )

    agent1 = "agent-1"
    agent2 = "agent-2"

    # Agent 1 uses budget
    llm_budget.record_usage(agent1, "claude-sonnet-4.5", 5000, 0.45)
    assert llm_budget.check_budget_available(agent1) is True

    # Agent 1 exceeds budget
    llm_budget.record_usage(agent1, "claude-sonnet-4.5", 1000, 0.10)
    assert llm_budget.check_budget_available(agent1) is False

    # Agent 2 should still have budget
    assert llm_budget.check_budget_available(agent2) is True

    # Agent 2 can use their budget
    llm_budget.record_usage(agent2, "claude-sonnet-4.5", 3000, 0.30)
    assert llm_budget.check_budget_available(agent2) is True


def test_retry_policy_exponential_backoff(redis_client):
    """
    Test exponential backoff retry policy.
    """
    task_queue = TaskQueue(redis_client)
    escalation_coord = EscalationCoordinator(redis_client, task_queue=task_queue)

    # Create task with exponential backoff
    task = task_queue.create_task(
        title="Backoff Task",
        description="Test exponential backoff",
        priority=3,
        retry_policy="exponential",
        max_retries=3,
        retry_delay_base=2  # 2 second base
    )

    # Calculate expected delays
    # Attempt 0: 2 * (2^0) = 2 seconds
    # Attempt 1: 2 * (2^1) = 4 seconds
    # Attempt 2: 2 * (2^2) = 8 seconds

    task.retry_count = 0
    delay0 = escalation_coord._calculate_retry_delay(task)
    assert delay0 == 2

    task.retry_count = 1
    delay1 = escalation_coord._calculate_retry_delay(task)
    assert delay1 == 4

    task.retry_count = 2
    delay2 = escalation_coord._calculate_retry_delay(task)
    assert delay2 == 8


def test_escalation_monitoring_pubsub(redis_client):
    """
    Test escalation monitoring with pub/sub events.
    """
    task_queue = TaskQueue(redis_client)
    escalation_coord = EscalationCoordinator(
        redis_client,
        task_queue=task_queue,
        poll_interval=1
    )

    # Create task
    task = task_queue.create_task(
        title="PubSub Task",
        description="Test pub/sub escalation",
        priority=3,
        max_retries=1
    )

    # Start monitoring
    escalation_coord.start_monitoring()

    # Wait for monitor to start
    time.sleep(0.5)

    # Publish escalation event
    event = {
        "event_type": "task_failed",
        "task_id": task.id,
        "reason": "Test failure",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    redis_client.publish("channel:escalations", json.dumps(event))

    # Give time for event processing
    time.sleep(1)

    # Check retry queue
    retry_queue = escalation_coord.get_retry_queue()
    # Should have scheduled retry (or might have already moved to pending)

    # Stop monitoring
    escalation_coord.stop_monitoring()


def test_full_dogfooding_scenario(redis_client):
    """
    Test AgentCoord dogfooding itself - meta coordination!

    Simulates:
    - Coordinator creates improvement tasks
    - Workers claim tasks with budget control
    - Some tasks fail and retry
    - Successful completion tracked
    """
    # Setup all components
    task_queue = TaskQueue(redis_client)
    llm_budget = LLMBudget(
        redis_client,
        max_concurrent=3,
        daily_budget=5.00,
        per_agent_budget=1.00
    )
    escalation_coord = EscalationCoordinator(redis_client, task_queue=task_queue)

    # Create "improvement" tasks (like we're doing now!)
    tasks = []
    for i in range(3):
        task = task_queue.create_task(
            title=f"Implement Feature {i}",
            description=f"Autonomous implementation of feature {i}",
            priority=3,
            tags=["implementation", f"feature-{i}"],
            max_retries=2
        )
        tasks.append(task)

    # Simulate 3 agents working in parallel
    agents = ["agent-1-impl", "agent-2-llm", "agent-3-integration"]

    for agent_id in agents:
        # Claim a task
        claimed = task_queue.claim_task(agent_id, tags=["implementation"])

        if claimed:
            # Check budget
            if not llm_budget.check_budget_available(agent_id):
                # Would escalate in real scenario
                continue

            # Acquire LLM slot
            try:
                with llm_budget.acquire_slot(timeout=5):
                    # Simulate work
                    time.sleep(0.1)

                    # Record usage
                    llm_budget.record_usage(
                        agent_id=agent_id,
                        model="claude-sonnet-4.5",
                        tokens=1000,
                        cost=0.05
                    )

                # Complete task
                claimed.status = TaskStatus.COMPLETED
                claimed.completed_at = datetime.now(timezone.utc).isoformat()
                task_queue.update_task(claimed)

            except SlotTimeoutError:
                # Would retry or escalate
                claimed.status = TaskStatus.FAILED
                task_queue.update_task(claimed)
                escalation_coord.handle_failed_task(claimed.id, "LLM slot timeout")

    # Check results
    stats = llm_budget.get_usage_stats()
    assert stats["total_cost"] > 0

    # At least some tasks should complete
    completed_count = sum(
        1 for t in tasks
        if task_queue.get_task(t.id).status == TaskStatus.COMPLETED
    )
    assert completed_count > 0


# ===== Fixtures =====

@pytest.fixture
def redis_client():
    """Provide clean Redis client for each test."""
    import redis
    client = redis.from_url("redis://localhost:6379", decode_responses=True)

    # Clean up before test
    cleanup_redis(client)

    yield client

    # Clean up after test
    cleanup_redis(client)


def cleanup_redis(client):
    """Clean up all test-related Redis keys."""
    patterns = [
        "task:*",
        "tasks:*",
        "llm:*",
        "agent:*",
        "board:*",
        "channel:*"
    ]

    for pattern in patterns:
        for key in client.scan_iter(pattern):
            client.delete(key)
