"""Tests for LLM budget tracking and rate limiting."""

import pytest
import time
from agentcoord.llm import LLMBudget, BudgetExceededError, SlotTimeoutError


def test_acquire_slot_basic(redis_client):
    """Test basic slot acquisition and release."""
    budget = LLMBudget(redis_client, max_concurrent=5)

    with budget.acquire_slot(timeout=5):
        # Should acquire slot
        in_flight = int(redis_client.get("llm:semaphore") or 0)
        assert in_flight == 1

    # Should release after context
    in_flight = int(redis_client.get("llm:semaphore") or 0)
    assert in_flight == 0


def test_acquire_slot_concurrent(redis_client):
    """Test concurrent slot acquisition."""
    budget = LLMBudget(redis_client, max_concurrent=2)

    # Acquire two slots
    with budget.acquire_slot():
        in_flight_1 = int(redis_client.get("llm:semaphore") or 0)
        assert in_flight_1 == 1

        with budget.acquire_slot():
            in_flight_2 = int(redis_client.get("llm:semaphore") or 0)
            assert in_flight_2 == 2

    # All released
    in_flight = int(redis_client.get("llm:semaphore") or 0)
    assert in_flight == 0


def test_acquire_slot_timeout(redis_client):
    """Test slot acquisition timeout."""
    budget = LLMBudget(redis_client, max_concurrent=1)

    with budget.acquire_slot():
        # Second acquisition should timeout
        with pytest.raises(SlotTimeoutError):
            with budget.acquire_slot(timeout=1):
                pass


def test_record_usage(redis_client):
    """Test usage recording."""
    budget = LLMBudget(redis_client)

    budget.record_usage(
        agent_id="agent-123",
        model="claude-sonnet-4.5",
        tokens=1000,
        cost=0.05
    )

    # Check model counters
    tokens = int(redis_client.get("llm:costs:tokens:claude-sonnet-4.5"))
    assert tokens == 1000

    cost = float(redis_client.get("llm:costs:dollars:claude-sonnet-4.5"))
    assert cost == 0.05

    # Check agent counters
    agent_data = redis_client.hgetall("llm:costs:by_agent:agent-123")
    assert int(agent_data["total_tokens"]) == 1000
    assert float(agent_data["total_cost"]) == 0.05
    assert int(agent_data["calls"]) == 1


def test_get_usage_stats(redis_client):
    """Test usage statistics retrieval."""
    budget = LLMBudget(redis_client, max_concurrent=10)

    # Record some usage
    budget.record_usage("agent-1", "claude-sonnet-4.5", 1000, 0.05)
    budget.record_usage("agent-1", "claude-opus-4.6", 500, 0.10)
    budget.record_usage("agent-2", "claude-sonnet-4.5", 2000, 0.10)

    stats = budget.get_usage_stats()

    assert stats["max_concurrent"] == 10
    assert stats["in_flight"] == 0
    assert stats["total_tokens"] == 3500
    assert stats["total_cost"] == 0.25

    # Check by-model stats
    assert stats["by_model"]["claude-sonnet-4.5"]["tokens"] == 3000
    assert abs(stats["by_model"]["claude-sonnet-4.5"]["cost"] - 0.15) < 0.001

    # Check by-agent stats
    assert stats["by_agent"]["agent-1"]["total_tokens"] == 1500
    assert abs(stats["by_agent"]["agent-1"]["total_cost"] - 0.15) < 0.001
    assert stats["by_agent"]["agent-1"]["calls"] == 2


def test_check_budget_available_daily(redis_client):
    """Test daily budget checking."""
    budget = LLMBudget(redis_client, daily_budget=1.00)

    # Should be available initially
    assert budget.check_budget_available("agent-1") is True

    # Record usage up to limit
    budget.record_usage("agent-1", "claude-sonnet-4.5", 10000, 0.60)
    assert budget.check_budget_available("agent-1") is True

    # Exceed limit
    budget.record_usage("agent-2", "claude-opus-4.6", 5000, 0.50)
    assert budget.check_budget_available("agent-1") is False


def test_check_budget_available_per_agent(redis_client):
    """Test per-agent budget checking."""
    budget = LLMBudget(redis_client, per_agent_budget=0.50)

    # Should be available initially
    assert budget.check_budget_available("agent-1") is True

    # Record usage under limit
    budget.record_usage("agent-1", "claude-sonnet-4.5", 5000, 0.25)
    assert budget.check_budget_available("agent-1") is True

    # Exceed per-agent limit
    budget.record_usage("agent-1", "claude-sonnet-4.5", 6000, 0.30)
    assert budget.check_budget_available("agent-1") is False

    # Other agent should still be OK
    assert budget.check_budget_available("agent-2") is True


def test_reset_daily_budget(redis_client):
    """Test daily budget reset."""
    budget = LLMBudget(redis_client)

    # Record some usage
    budget.record_usage("agent-1", "claude-sonnet-4.5", 1000, 0.05)

    stats_before = budget.get_usage_stats()
    assert stats_before["total_cost"] > 0

    # Reset
    budget.reset_daily_budget()

    stats_after = budget.get_usage_stats()
    assert stats_after["total_cost"] == 0
    assert stats_after["total_tokens"] == 0
    assert stats_after["in_flight"] == 0

    # Check reset timestamp exists
    reset_time = redis_client.get("llm:budget:daily_reset")
    assert reset_time is not None


@pytest.fixture
def redis_client():
    """Provide clean Redis client for each test."""
    import redis
    client = redis.from_url("redis://localhost:6379", decode_responses=True)

    # Clean up before test
    for key in client.scan_iter("llm:*"):
        client.delete(key)

    yield client

    # Clean up after test
    for key in client.scan_iter("llm:*"):
        client.delete(key)
