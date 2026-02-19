"""
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
