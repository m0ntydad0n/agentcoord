"""CoordinationClient - Main interface for agentcoord framework."""

import redis
from typing import Optional
from pathlib import Path

from .tasks import TaskQueue
from .board import Board
from .agent import AgentRegistry
from .audit import AuditLog


class CoordinationClient:
    """Main client for coordinating multiple agents via Redis."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        fallback_dir: Optional[str] = None
    ):
        """Initialize coordination client.

        Args:
            redis_url: Redis connection URL
            fallback_dir: Directory for file-based fallback (unused, for compatibility)
        """
        # Parse redis URL
        if redis_url.startswith("redis://"):
            parts = redis_url.replace("redis://", "").split(":")
            host = parts[0] if len(parts) > 0 else "localhost"
            port = int(parts[1]) if len(parts) > 1 else 6379
        else:
            host = "localhost"
            port = 6379

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True
        )

        # Test connection
        try:
            self.redis_client.ping()
            self.mode = "redis"
        except redis.ConnectionError:
            self.mode = "fallback"
            self.redis_client = None

        # Initialize components
        if self.redis_client:
            # TaskQueue uses SQLite, not Redis (fix for type mismatch)
            db_path = fallback_dir + "/tasks.db" if fallback_dir else "agentcoord_tasks.db"
            self.task_queue = TaskQueue(db_path)
            self.board = Board(self.redis_client)
            self.agent_registry = AgentRegistry(self.redis_client)
            self.audit_log = AuditLog(self.redis_client)
        else:
            # Fallback mode - not fully implemented
            self.task_queue = None
            self.board = None
            self.agent_registry = None
            self.audit_log = None

        self.agent_id = None

    @classmethod
    def session(cls, redis_url: str, role: str, name: str, working_on: str = "", fallback_dir: Optional[str] = None):
        """Create a client session with auto-registration.

        Args:
            redis_url: Redis connection URL
            role: Agent role (e.g., "CTO", "Engineer")
            name: Agent name
            working_on: Current task description
            fallback_dir: Directory for file-based fallback

        Returns:
            CoordinationClient instance
        """
        client = cls(redis_url=redis_url, fallback_dir=fallback_dir)
        client.register_agent(role=role, name=name, working_on=working_on)
        return client

    def register_agent(self, role: str, name: str, working_on: str = "") -> str:
        """Register this agent in the registry.

        Args:
            role: Agent role
            name: Agent name
            working_on: Current task description

        Returns:
            Agent ID
        """
        if not self.agent_registry:
            raise RuntimeError("Agent registry not available (Redis connection failed)")

        self.agent_id = self.agent_registry.register(
            agent_id=f"{role}-{name}",
            agent_type=role,
            capabilities=[role.lower(), "general"]
        )
        return self.agent_id

    def claim_task(self, tags: Optional[list] = None):
        """Claim a task from the queue.

        Args:
            tags: Task tags to filter by

        Returns:
            Task object or None
        """
        if not self.task_queue:
            return None

        agent_id = self.agent_id or "unknown"
        return self.task_queue.claim_task(agent_id, tags=tags)

    def lock_file(self, file_path: str, intent: str = ""):
        """Lock a file for exclusive editing (context manager).

        Args:
            file_path: Path to file to lock
            intent: Description of intended changes

        Returns:
            Context manager
        """
        # Simple no-op context manager for now
        class FileLock:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return FileLock()

    def post_thread(self, title: str, message: str = "", priority: str = "normal", tags: Optional[list] = None):
        """Post a message thread to the board.

        Args:
            title: Thread title
            message: Thread content
            priority: Priority level
            tags: Thread tags

        Returns:
            Thread object or None
        """
        if not self.board:
            return None

        content = f"# {title}\n\n{message}" if message else title
        return self.board.post_thread(
            title=title,
            content=content,
            author=self.agent_id or "unknown",
            tags=tags or []
        )

    def log_decision(self, decision_type: str, context: str, reason: str):
        """Log a decision to the audit log.

        Args:
            decision_type: Type of decision
            context: Decision context
            reason: Reason for decision
        """
        if self.audit_log:
            self.audit_log.log(
                agent_id=self.agent_id or "unknown",
                action=decision_type,
                details={
                    "context": context,
                    "reason": reason
                }
            )

    def shutdown(self):
        """Cleanup and close connections."""
        if self.agent_registry and self.agent_id:
            self.agent_registry.unregister(self.agent_id)

        if self.redis_client:
            self.redis_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.shutdown()
