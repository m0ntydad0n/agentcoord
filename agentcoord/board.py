"""
Board-style threaded communication system.

Replaces BOARD.md with Redis-backed threads.
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    RESOLVED = "resolved"


@dataclass
class BoardThread:
    """Represents a board thread."""
    id: str
    title: str
    status: ThreadStatus
    priority: str  # "high", "normal", "low"
    posted_by: str
    posted_at: str
    resolved_at: Optional[str] = None
    messages: List[Dict] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


class Board:
    """Redis-backed board communication system."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.threads_list = "board:threads"

    def post_thread(
        self,
        title: str,
        message: str,
        posted_by: str,
        priority: str = "normal",
        status: ThreadStatus = ThreadStatus.ACTIVE
    ) -> BoardThread:
        """Create a new board thread."""
        thread = BoardThread(
            id=str(uuid.uuid4()),
            title=title,
            status=status,
            priority=priority,
            posted_by=posted_by,
            posted_at=datetime.now(timezone.utc).isoformat(),
            messages=[{
                "author": posted_by,
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        )

        # Store thread
        thread_key = f"thread:{thread.id}"
        self.redis.hset(thread_key, mapping={
            "id": thread.id,
            "title": thread.title,
            "status": thread.status.value,
            "priority": thread.priority,
            "posted_by": thread.posted_by,
            "posted_at": thread.posted_at,
            "resolved_at": thread.resolved_at or "",
            "messages": json.dumps(thread.messages)
        })

        # Add to threads list
        self.redis.lpush(self.threads_list, thread.id)

        # Publish event
        self.redis.publish("channel:board:updates", json.dumps({
            "event": "thread_created",
            "thread_id": thread.id,
            "title": title,
            "posted_by": posted_by
        }))

        logger.info(f"Posted thread {thread.id}: {title}")
        return thread

    def add_message(self, thread_id: str, author: str, content: str):
        """Add a message to existing thread."""
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        message = {
            "author": author,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        thread.messages.append(message)

        # Update in Redis
        self.redis.hset(
            f"thread:{thread_id}",
            "messages",
            json.dumps(thread.messages)
        )

        logger.info(f"Added message to thread {thread_id} by {author}")

    def resolve_thread(self, thread_id: str):
        """Mark thread as resolved."""
        thread_key = f"thread:{thread_id}"
        self.redis.hset(thread_key, mapping={
            "status": ThreadStatus.RESOLVED.value,
            "resolved_at": datetime.now(timezone.utc).isoformat()
        })

        # Publish event
        self.redis.publish("channel:board:updates", json.dumps({
            "event": "thread_resolved",
            "thread_id": thread_id
        }))

        logger.info(f"Resolved thread {thread_id}")

    def get_thread(self, thread_id: str) -> Optional[BoardThread]:
        """Retrieve thread by ID."""
        thread_key = f"thread:{thread_id}"
        data = self.redis.hgetall(thread_key)
        if not data:
            return None

        return BoardThread(
            id=data["id"],
            title=data["title"],
            status=ThreadStatus(data["status"]),
            priority=data["priority"],
            posted_by=data["posted_by"],
            posted_at=data["posted_at"],
            resolved_at=data.get("resolved_at") or None,
            messages=json.loads(data.get("messages", "[]"))
        )

    def list_threads(
        self,
        status: Optional[ThreadStatus] = None,
        limit: int = 100
    ) -> List[BoardThread]:
        """List board threads, optionally filtered by status."""
        thread_ids = self.redis.lrange(self.threads_list, 0, limit - 1)
        threads = []

        for thread_id in thread_ids:
            thread = self.get_thread(thread_id)
            if thread and (status is None or thread.status == status):
                threads.append(thread)

        return threads
