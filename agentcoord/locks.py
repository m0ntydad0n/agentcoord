"""
File locking primitives with Redis and file-based fallback.

Provides atomic file locking with TTL auto-expiry to prevent zombie locks.
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LockAcquireTimeout(Exception):
    """Raised when unable to acquire a file lock within timeout period."""
    pass


class FileLock:
    """
    Context manager for atomic file locking.

    Uses Redis SET NX EX for atomic lock acquisition with TTL.
    Automatically releases lock on context exit.

    Example:
        with FileLock(redis_client, "backend/main.py", "agent-123", "Add endpoint"):
            # File is locked, safe to edit
            pass
        # Lock automatically released
    """

    def __init__(
        self,
        redis_client,
        file_path: str,
        agent_id: str,
        intent: str = "",
        ttl: int = 3600,  # 1 hour default
        timeout: float = 30.0,  # Wait up to 30s to acquire
        retry_interval: float = 0.5
    ):
        self.redis = redis_client
        self.file_path = file_path
        self.agent_id = agent_id
        self.intent = intent
        self.ttl = ttl
        self.timeout = timeout
        self.retry_interval = retry_interval

        # Hash file path to create valid Redis key
        path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:16]
        self.lock_key = f"lock:file:{path_hash}"
        self.acquired = False

    def __enter__(self):
        """Acquire lock with exponential backoff retry."""
        start_time = time.time()
        retry_count = 0

        while True:
            # Attempt atomic lock acquisition
            # SET key value NX EX seconds
            acquired = self.redis.set(
                self.lock_key,
                self.agent_id,
                nx=True,  # Only set if doesn't exist
                ex=self.ttl  # Auto-expiry
            )

            if acquired:
                # Store metadata about the lock
                self.redis.hset(
                    f"{self.lock_key}:meta",
                    mapping={
                        "file_path": self.file_path,
                        "owner": self.agent_id,
                        "intent": self.intent,
                        "locked_at": datetime.now(timezone.utc).isoformat()
                    }
                )
                self.redis.expire(f"{self.lock_key}:meta", self.ttl)

                self.acquired = True
                logger.info(f"Acquired lock on {self.file_path} for {self.agent_id}")
                return self

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= self.timeout:
                # Who owns the lock?
                current_owner = self.redis.get(self.lock_key)
                meta = self.redis.hgetall(f"{self.lock_key}:meta")
                owner_info = f"{current_owner} ({meta.get('intent', 'unknown intent')})" if meta else current_owner

                raise LockAcquireTimeout(
                    f"Could not acquire lock on {self.file_path} after {elapsed:.1f}s. "
                    f"Currently locked by {owner_info}"
                )

            # Exponential backoff
            wait = min(self.retry_interval * (2 ** retry_count), 5.0)
            logger.debug(f"Lock on {self.file_path} held by another agent, retrying in {wait:.1f}s...")
            time.sleep(wait)
            retry_count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock if we own it."""
        if not self.acquired:
            return

        # Only release if we still own it (prevent releasing someone else's lock)
        current_owner = self.redis.get(self.lock_key)
        if current_owner == self.agent_id:
            self.redis.delete(self.lock_key)
            self.redis.delete(f"{self.lock_key}:meta")
            logger.info(f"Released lock on {self.file_path} for {self.agent_id}")
        else:
            logger.warning(
                f"Lock on {self.file_path} no longer owned by {self.agent_id} "
                f"(now owned by {current_owner}). Did not release."
            )
