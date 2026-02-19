"""
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
