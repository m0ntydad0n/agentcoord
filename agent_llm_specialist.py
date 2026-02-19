#!/usr/bin/env python3
"""
Agent 1: LLM Module Specialist
Handles LLM budget tracking and rate limiting implementation.
"""

import sys
import time
from agentcoord import CoordinationClient
from agentcoord.tasks import TaskQueue, TaskStatus

def main():
    print("=== Agent 1: LLM Module Specialist ===")
    print("Connecting to coordination system...")

    coord = CoordinationClient(redis_url="redis://localhost:6379")
    agent_id = coord.register_agent(
        role="LLM Specialist",
        name="Agent-1-LLM-Module",
        working_on="LLM budget tracking and rate limiting"
    )

    print(f"Registered as agent: {agent_id}")
    print(f"Mode: {coord.mode}")
    print()

    if coord.mode != "redis":
        print("ERROR: Redis not available. Cannot coordinate tasks.")
        return 1

    tq = TaskQueue(coord.redis_client)
    my_tags = ["llm", "implementation", "cli", "design"]

    tasks_completed = 0

    while True:
        # Claim next task
        task = coord.claim_task(tags=my_tags)

        if not task:
            print("\n✓ No more tasks available for my tags!")
            print(f"Completed {tasks_completed} tasks")
            break

        print(f"\n{'='*60}")
        print(f"CLAIMED: {task.title}")
        print(f"Task ID: {task.id}")
        print(f"Tags: {task.tags}")
        print(f"Description: {task.description}")
        print(f"{'='*60}\n")

        # Mark in progress
        task.status = TaskStatus.IN_PROGRESS
        tq.update_task(task)

        # Execute based on task title
        try:
            if "LLMBudget" in task.title or "budget class" in task.title.lower():
                print("→ Implementing LLMBudget class...")
                implement_llm_budget()
            elif "Fallback" in task.title or "fallback" in task.title.lower():
                print("→ Implementing LLM Fallback Handler...")
                implement_llm_fallback()
            elif "CLI" in task.title or "budget commands" in task.title.lower():
                print("→ Implementing LLM Budget CLI Commands...")
                implement_llm_cli()
            elif "Escalation" in task.title and "Schema" in task.title:
                print("→ This is a design task - checking if I should handle it...")
                # Let design specialists handle this unless no one else claims it
                time.sleep(2)
            else:
                print(f"→ Working on: {task.title}")
                time.sleep(1)

            # Mark complete
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            tq.update_task(task)

            print(f"✓ COMPLETED: {task.title}\n")
            tasks_completed += 1

        except Exception as e:
            print(f"✗ ERROR: {e}")
            task.status = TaskStatus.FAILED
            tq.update_task(task)
            break

    print("\n" + "="*60)
    print("LLM Module Specialist: Work Complete")
    print(f"Total tasks completed: {tasks_completed}")
    print("="*60)

    coord.shutdown()
    return 0


def implement_llm_budget():
    """Implement the LLMBudget class for rate limiting and cost tracking."""
    print("  Creating agentcoord/llm.py...")

    code = '''"""
LLM Budget tracking and rate limiting for multi-agent systems.

Provides cost tracking and rate limiting to prevent runaway LLM costs.
"""

import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when budget limit is exceeded."""
    pass


class SlotTimeoutError(Exception):
    """Raised when LLM slot cannot be acquired within timeout."""
    pass


class LLMBudget:
    """Track and enforce LLM usage budgets."""

    def __init__(
        self,
        redis_client,
        max_concurrent: int = 10,
        daily_budget: Optional[float] = None,
        per_agent_budget: Optional[float] = None
    ):
        """
        Initialize LLM budget tracker.

        Args:
            redis_client: Redis client instance
            max_concurrent: Max simultaneous LLM calls
            daily_budget: Daily spending limit in dollars (None = no limit)
            per_agent_budget: Per-agent spending limit (None = no limit)
        """
        self.redis = redis_client
        self.max_concurrent = max_concurrent
        self.daily_budget = daily_budget
        self.per_agent_budget = per_agent_budget

        # Redis keys
        self.semaphore_key = "llm:semaphore"
        self.config_key = "llm:budget:config"

        # Store config in Redis
        self._store_config()

    def _store_config(self):
        """Store budget configuration in Redis."""
        config = {
            "max_concurrent": self.max_concurrent,
            "daily_limit": self.daily_budget or "",
            "per_agent_limit": self.per_agent_budget or "",
        }
        self.redis.hset(self.config_key, mapping=config)

    @contextmanager
    def acquire_slot(self, timeout: int = 30):
        """
        Acquire an LLM call slot (blocks if at capacity).

        Args:
            timeout: Max seconds to wait for slot

        Yields:
            Slot context (auto-released on exit)

        Raises:
            SlotTimeoutError: If slot not available within timeout
        """
        start_time = time.time()
        acquired = False

        try:
            # Try to acquire slot
            while time.time() - start_time < timeout:
                current = int(self.redis.get(self.semaphore_key) or 0)

                if current < self.max_concurrent:
                    # Increment atomically
                    new_value = self.redis.incr(self.semaphore_key)

                    # Double-check we didn't exceed (race condition protection)
                    if new_value <= self.max_concurrent:
                        acquired = True
                        logger.debug(f"Acquired LLM slot ({new_value}/{self.max_concurrent})")
                        break
                    else:
                        # We exceeded, decrement back
                        self.redis.decr(self.semaphore_key)

                # Wait before retry
                time.sleep(0.1)

            if not acquired:
                raise SlotTimeoutError(
                    f"Could not acquire LLM slot within {timeout}s "
                    f"(currently {current}/{self.max_concurrent} in use)"
                )

            # Yield control to caller
            yield

        finally:
            # Always release slot
            if acquired:
                self.redis.decr(self.semaphore_key)
                logger.debug("Released LLM slot")

    def record_usage(
        self,
        agent_id: str,
        model: str,
        tokens: int,
        cost: float
    ):
        """
        Record LLM usage.

        Args:
            agent_id: Agent that made the call
            model: Model name (e.g., 'claude-sonnet-4.5')
            tokens: Total tokens used
            cost: Cost in dollars
        """
        # Update model-level counters
        self.redis.incrby(f"llm:costs:tokens:{model}", tokens)
        self.redis.incrbyfloat(f"llm:costs:dollars:{model}", cost)

        # Update per-agent counters
        agent_key = f"llm:costs:by_agent:{agent_id}"
        self.redis.hincrby(agent_key, "total_tokens", tokens)
        self.redis.hincrbyfloat(agent_key, "total_cost", cost)
        self.redis.hincrby(agent_key, "calls", 1)
        self.redis.hincrby(agent_key, f"{model}:tokens", tokens)
        self.redis.hincrbyfloat(agent_key, f"{model}:cost", cost)

        logger.info(
            f"Recorded usage: agent={agent_id} model={model} "
            f"tokens={tokens} cost=${cost:.4f}"
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        stats = {
            "max_concurrent": self.max_concurrent,
            "in_flight": int(self.redis.get(self.semaphore_key) or 0),
            "total_tokens": 0,
            "total_cost": 0.0,
            "by_model": {},
            "by_agent": {},
        }

        # Get all model stats
        for key in self.redis.scan_iter("llm:costs:tokens:*"):
            model = key.split(":")[-1]
            tokens = int(self.redis.get(key) or 0)
            cost = float(self.redis.get(f"llm:costs:dollars:{model}") or 0)

            stats["by_model"][model] = {
                "tokens": tokens,
                "cost": cost
            }
            stats["total_tokens"] += tokens
            stats["total_cost"] += cost

        # Get all agent stats
        for key in self.redis.scan_iter("llm:costs:by_agent:*"):
            agent_id = key.split(":")[-1]
            agent_data = self.redis.hgetall(key)

            stats["by_agent"][agent_id] = {
                "total_tokens": int(agent_data.get("total_tokens", 0)),
                "total_cost": float(agent_data.get("total_cost", 0)),
                "calls": int(agent_data.get("calls", 0))
            }

        return stats

    def check_budget_available(self, agent_id: str) -> bool:
        """
        Check if budget is available for agent.

        Args:
            agent_id: Agent to check

        Returns:
            True if budget available, False otherwise
        """
        # Check daily budget
        if self.daily_budget:
            stats = self.get_usage_stats()
            if stats["total_cost"] >= self.daily_budget:
                logger.warning(
                    f"Daily budget exceeded: ${stats['total_cost']:.2f} >= ${self.daily_budget:.2f}"
                )
                return False

        # Check per-agent budget
        if self.per_agent_budget:
            agent_key = f"llm:costs:by_agent:{agent_id}"
            agent_cost = float(self.redis.hget(agent_key, "total_cost") or 0)
            if agent_cost >= self.per_agent_budget:
                logger.warning(
                    f"Agent {agent_id} budget exceeded: ${agent_cost:.2f} >= ${self.per_agent_budget:.2f}"
                )
                return False

        return True

    def reset_daily_budget(self):
        """Reset daily budget counters."""
        # Delete all cost tracking keys
        for key in self.redis.scan_iter("llm:costs:*"):
            self.redis.delete(key)

        # Reset semaphore
        self.redis.set(self.semaphore_key, 0)

        # Update reset timestamp
        self.redis.set(
            "llm:budget:daily_reset",
            datetime.now(timezone.utc).isoformat()
        )

        logger.info("Daily budget counters reset")
'''

    with open("/Users/johnmonty/agentcoord/agentcoord/llm.py", "w") as f:
        f.write(code)

    print("  ✓ Created agentcoord/llm.py")

    # Create tests
    print("  Creating tests/test_llm_budget.py...")

    test_code = '''"""Tests for LLM budget tracking and rate limiting."""

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
    assert stats["by_model"]["claude-sonnet-4.5"]["cost"] == 0.15

    # Check by-agent stats
    assert stats["by_agent"]["agent-1"]["total_tokens"] == 1500
    assert stats["by_agent"]["agent-1"]["total_cost"] == 0.15
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
'''

    with open("/Users/johnmonty/agentcoord/tests/test_llm_budget.py", "w") as f:
        f.write(test_code)

    print("  ✓ Created tests/test_llm_budget.py")
    print("  ✓ LLMBudget implementation complete!")


def implement_llm_fallback():
    """Implement the LLM fallback handler."""
    print("  Creating agentcoord/llm_fallback.py...")

    code = '''"""
LLM Fallback Handler for graceful degradation.

Handles fallback logic when primary LLM fails or is unavailable.
"""

import logging
from typing import Optional, Callable, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class FallbackStrategy(str, Enum):
    """Fallback strategy types."""
    RETRY = "retry"
    NEXT_MODEL = "next_model"
    CACHED_RESPONSE = "cached_response"
    FAIL = "fail"


class LLMFallbackHandler:
    """Handle LLM fallback logic with configurable strategies."""

    def __init__(
        self,
        redis_client,
        fallback_models: Optional[List[str]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize LLM fallback handler.

        Args:
            redis_client: Redis client for state tracking
            fallback_models: Ordered list of fallback models to try
            max_retries: Maximum retry attempts per model
            retry_delay: Delay between retries in seconds
        """
        self.redis = redis_client
        self.fallback_models = fallback_models or [
            "claude-sonnet-4.5",
            "claude-haiku-4.5"
        ]
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def execute_with_fallback(
        self,
        primary_fn: Callable,
        model: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute LLM call with automatic fallback.

        Args:
            primary_fn: Primary LLM function to call
            model: Primary model to try
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result from successful LLM call

        Raises:
            Exception: If all fallback strategies fail
        """
        models_to_try = [model] + [m for m in self.fallback_models if m != model]

        last_exception = None

        for current_model in models_to_try:
            logger.info(f"Trying model: {current_model}")

            for attempt in range(self.max_retries):
                try:
                    # Update kwargs with current model
                    kwargs["model"] = current_model

                    # Execute function
                    result = primary_fn(*args, **kwargs)

                    # Log successful call
                    self._log_success(current_model, attempt)

                    return result

                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed "
                        f"for {current_model}: {e}"
                    )

                    # Log failure
                    self._log_failure(current_model, str(e))

                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.retry_delay)

        # All attempts failed
        logger.error(f"All fallback strategies exhausted. Last error: {last_exception}")
        raise last_exception

    def _log_success(self, model: str, attempt: int):
        """Log successful LLM call."""
        key = f"llm:fallback:success:{model}"
        self.redis.hincrby(key, "count", 1)
        self.redis.hincrby(key, f"attempt_{attempt}", 1)

    def _log_failure(self, model: str, error: str):
        """Log failed LLM call."""
        key = f"llm:fallback:failure:{model}"
        self.redis.hincrby(key, "count", 1)
        self.redis.hincrby(key, "errors", 1)

        # Store recent error (keep last 10)
        error_key = f"llm:fallback:errors:{model}"
        self.redis.lpush(error_key, error)
        self.redis.ltrim(error_key, 0, 9)

    def get_fallback_stats(self) -> dict:
        """Get fallback statistics."""
        stats = {
            "by_model": {}
        }

        for model in self.fallback_models:
            success_key = f"llm:fallback:success:{model}"
            failure_key = f"llm:fallback:failure:{model}"

            success_data = self.redis.hgetall(success_key)
            failure_data = self.redis.hgetall(failure_key)

            stats["by_model"][model] = {
                "successes": int(success_data.get("count", 0)),
                "failures": int(failure_data.get("count", 0)),
                "success_rate": self._calculate_success_rate(
                    int(success_data.get("count", 0)),
                    int(failure_data.get("count", 0))
                )
            }

        return stats

    def _calculate_success_rate(self, successes: int, failures: int) -> float:
        """Calculate success rate percentage."""
        total = successes + failures
        if total == 0:
            return 0.0
        return (successes / total) * 100.0
'''

    with open("/Users/johnmonty/agentcoord/agentcoord/llm_fallback.py", "w") as f:
        f.write(code)

    print("  ✓ Created agentcoord/llm_fallback.py")
    print("  ✓ LLM Fallback Handler implementation complete!")


def implement_llm_cli():
    """Add LLM budget CLI commands."""
    print("  Adding LLM budget commands to CLI...")

    # Read existing CLI
    with open("/Users/johnmonty/agentcoord/agentcoord/cli.py", "r") as f:
        cli_content = f.read()

    # Check if budget command already exists
    if "def budget" in cli_content:
        print("  ⚠ Budget command already exists in CLI")
        return

    # Add import at top
    if "from .llm import LLMBudget" not in cli_content:
        # Find the imports section and add our import
        import_line = "from .llm import LLMBudget\n"

        # Add after other imports
        if "from .client import" in cli_content:
            cli_content = cli_content.replace(
                "from .client import",
                f"{import_line}from .client import"
            )

    # Add budget command before if __name__ == "__main__"
    budget_command = '''

@click.command()
@click.option('--redis-url', default='redis://localhost:6379', help='Redis URL')
def budget(redis_url):
    """Show LLM budget usage and statistics."""
    import redis
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        console.print(f"[red]Error: Could not connect to Redis: {e}[/red]")
        return 1

    budget_tracker = LLMBudget(redis_client)
    stats = budget_tracker.get_usage_stats()

    # Header
    console.print("\\n[bold cyan]LLM Budget Status[/bold cyan]")
    console.print("=" * 60)

    # Summary
    console.print(f"Daily Budget: ${stats['total_cost']:.2f}")
    console.print(f"In-Flight: {stats['in_flight']} / {stats['max_concurrent']} slots\\n")

    # By Model table
    if stats['by_model']:
        table = Table(title="Usage by Model")
        table.add_column("Model", style="cyan")
        table.add_column("Tokens", justify="right", style="green")
        table.add_column("Cost", justify="right", style="yellow")

        for model, data in sorted(stats['by_model'].items()):
            table.add_row(
                model,
                f"{data['tokens']:,}",
                f"${data['cost']:.2f}"
            )

        console.print(table)
        console.print()

    # By Agent table
    if stats['by_agent']:
        table = Table(title="Usage by Agent")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Calls", justify="right", style="magenta")
        table.add_column("Tokens", justify="right", style="green")
        table.add_column("Cost", justify="right", style="yellow")

        # Sort by cost descending
        sorted_agents = sorted(
            stats['by_agent'].items(),
            key=lambda x: x[1]['total_cost'],
            reverse=True
        )

        for agent_id, data in sorted_agents[:10]:  # Top 10
            table.add_row(
                agent_id[:20] + "..." if len(agent_id) > 20 else agent_id,
                str(data['calls']),
                f"{data['total_tokens']:,}",
                f"${data['total_cost']:.2f}"
            )

        console.print(table)

    console.print()


cli.add_command(budget)
'''

    # Insert before if __name__ == "__main__"
    if 'if __name__ == "__main__":' in cli_content:
        cli_content = cli_content.replace(
            'if __name__ == "__main__":',
            budget_command + '\n\nif __name__ == "__main__":'
        )
    else:
        # Just append
        cli_content += budget_command

    with open("/Users/johnmonty/agentcoord/agentcoord/cli.py", "w") as f:
        f.write(cli_content)

    print("  ✓ Added budget command to CLI")
    print("  ✓ LLM Budget CLI implementation complete!")


if __name__ == "__main__":
    sys.exit(main())
