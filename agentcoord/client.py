"""AgentCoord client with robust error handling."""

import json
import logging
import time
from typing import Any, Dict, Optional, Union
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from .exceptions import RedisConnectionError, ValidationError

logger = logging.getLogger(__name__)

class AgentClient:
    """Client for interacting with AgentCoord with robust error handling."""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        connection_timeout: int = 30
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection_timeout = connection_timeout
        self._redis = None
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection with error handling."""
        try:
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
                retry_on_timeout=True,
                decode_responses=True
            )
            # Test connection
            self._redis.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(
                f"Failed to connect to Redis at {self.host}:{self.port}: {e}"
            ) from e
        except Exception as e:
            raise RedisConnectionError(
                f"Unexpected error connecting to Redis: {e}"
            ) from e

    def _validate_task_data(self, task_data: Dict[str, Any]) -> None:
        """Validate task data before sending."""
        if not isinstance(task_data, dict):
            raise ValidationError(f"Task data must be a dictionary, got {type(task_data)}")
        
        if 'task_id' not in task_data:
            raise ValidationError("Task data must include 'task_id'")
        
        if not task_data['task_id']:
            raise ValidationError("Task 'task_id' cannot be empty")
        
        # Validate JSON serializable
        try:
            json.dumps(task_data)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Task data must be JSON serializable: {e}") from e

    def _validate_queue_name(self, queue_name: str) -> None:
        """Validate queue name."""
        if not isinstance(queue_name, str):
            raise ValidationError(f"Queue name must be string, got {type(queue_name)}")
        
        if not queue_name or not queue_name.strip():
            raise ValidationError("Queue name cannot be empty")
        
        if len(queue_name) > 200:
            raise ValidationError(f"Queue name too long: {len(queue_name)} chars (max 200)")

    def _execute_with_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute Redis operation with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation_func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay)
                    # Try to reconnect
                    try:
                        self._connect()
                    except RedisConnectionError:
                        pass  # Will retry on next iteration
                else:
                    break
            except RedisError as e:
                # Non-connection Redis errors - don't retry
                raise RedisConnectionError(
                    f"{operation_name} failed with Redis error: {e}"
                ) from e
            except Exception as e:
                # Unexpected errors
                raise RedisConnectionError(
                    f"{operation_name} failed with unexpected error: {e}"
                ) from e
        
        raise RedisConnectionError(
            f"{operation_name} failed after {self.max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def submit_task(self, queue_name: str, task_data: Dict[str, Any]) -> bool:
        """Submit task to queue with validation and retry logic."""
        try:
            self._validate_queue_name(queue_name)
            self._validate_task_data(task_data)
        except ValidationError as e:
            logger.error(f"Task submission validation failed: {e}")
            raise

        def _submit():
            task_json = json.dumps(task_data)
            result = self._redis.lpush(f"queue:{queue_name}", task_json)
            logger.info(f"Task {task_data.get('task_id')} submitted to queue '{queue_name}'")
            return result > 0

        return self._execute_with_retry(
            f"Submit task to queue '{queue_name}'",
            _submit
        )

    def get_result(self, result_key: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Get task result with timeout and retry logic."""
        if not isinstance(result_key, str) or not result_key.strip():
            raise ValidationError("Result key must be a non-empty string")

        def _get_result():
            result = self._redis.brpop(f"result:{result_key}", timeout=timeout)
            if result:
                _, result_json = result
                try:
                    return json.loads(result_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse result JSON for key '{result_key}': {e}")
                    return {"error": "Invalid result format", "raw_data": result_json}
            return None

        try:
            return self._execute_with_retry(
                f"Get result for key '{result_key}'",
                _get_result
            )
        except RedisConnectionError:
            logger.error(f"Failed to get result for key '{result_key}' after retries")
            raise

    def get_queue_length(self, queue_name: str) -> int:
        """Get queue length with error handling."""
        try:
            self._validate_queue_name(queue_name)
        except ValidationError as e:
            logger.error(f"Queue length check validation failed: {e}")
            raise

        def _get_length():
            return self._redis.llen(f"queue:{queue_name}")

        return self._execute_with_retry(
            f"Get length of queue '{queue_name}'",
            _get_length
        )

    def health_check(self) -> Dict[str, Any]:
        """Check client and Redis health."""
        health = {
            "client_ok": True,
            "redis_connected": False,
            "redis_info": None,
            "errors": []
        }

        try:
            # Test Redis connection
            self._redis.ping()
            health["redis_connected"] = True
            
            # Get Redis info
            info = self._redis.info()
            health["redis_info"] = {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
            
        except Exception as e:
            health["client_ok"] = False
            health["errors"].append(f"Redis health check failed: {e}")
            logger.error(f"Health check failed: {e}")

        return health

    def close(self) -> None:
        """Close Redis connection gracefully."""
        if self._redis:
            try:
                self._redis.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()