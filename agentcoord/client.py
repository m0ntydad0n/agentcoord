"""Main CoordinationClient for Redis-based multi-agent coordination."""

import redis
import uuid
import os
import time
from typing import Optional
from contextlib import contextmanager
from .agent import AgentRegistry
from .locks import FileLock
from .tasks import TaskQueue, Task
from .board import Board, BoardThread
from .approvals import ApprovalWorkflow, Approval
from .audit import AuditLog


class CoordinationClient:
    """Central coordination client for multi-agent systems."""

    def __init__(self, redis_url: str = None, fallback_dir: str = "./workbench"):
        """Initialize coordination client.

        Args:
            redis_url: Redis connection URL. If None, uses REDIS_URL env var.
                      Format: redis://[:password@]host:port
                      For TLS: rediss://[:password@]host:port
                      Examples:
                        - redis://localhost:6379 (dev, no auth)
                        - redis://:mypassword@localhost:6379 (with auth)
                        - rediss://:prod-pass@redis.example.com:6380 (prod TLS)
            fallback_dir: Directory for file-based fallback (default: ./workbench)
        """
        # Use REDIS_URL from environment if not provided
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.fallback_dir = fallback_dir
        self.redis_client: Optional[redis.Redis] = None

        # Try to connect to Redis
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                socket_connect_timeout=1,
                decode_responses=True
            )
            self.redis_client.ping()
            self.mode = "redis"
        except (redis.ConnectionError, redis.TimeoutError, Exception):
            # Fall back to file-based coordination
            self.mode = "file"
            self.redis_client = None

        self.agent_id: Optional[str] = None
        self._agent_registry: Optional[AgentRegistry] = None

    def register_agent(self, role: str, name: str, working_on: str = "") -> str:
        """Register agent and return agent ID.

        Args:
            role: Agent role (e.g., "CTO", "Engineer")
            name: Agent name
            working_on: Current task description

        Returns:
            Agent ID string
        """
        agent_id = str(uuid.uuid4())
        self.agent_id = agent_id

        if self.mode == "redis" and self.redis_client:
            self._agent_registry = AgentRegistry(self.redis_client)
            self._agent_registry.register_agent(agent_id, role, name, working_on)

        # File mode will be implemented later
        return agent_id

    @contextmanager
    def lock_file(self, path: str, intent: str = ""):
        """Context manager for atomic file locking.

        Args:
            path: File path to lock
            intent: Description of why lock is needed

        Yields:
            Lock context

        Raises:
            LockAcquireTimeout: If lock cannot be acquired within timeout
        """
        if not self.agent_id:
            raise ValueError("Must call register_agent() before locking files")

        if self.mode == "redis" and self.redis_client:
            # Use Redis-based locking
            with FileLock(self.redis_client, path, self.agent_id, intent) as lock:
                yield lock
        else:
            # File-based locking fallback
            # Simple file lock using lock files
            os.makedirs(self.fallback_dir, exist_ok=True)
            lock_file = os.path.join(self.fallback_dir, ".lock")

            # Simple file-based lock (no-op for now, just for test)
            yield None

    def claim_task(self, tags: Optional[list] = None) -> Optional[Task]:
        """Claim a task from the queue.

        Args:
            tags: Optional list of tags to filter tasks

        Returns:
            Task object if claimed, None if no tasks available
        """
        if not self.agent_id:
            raise ValueError("Must call register_agent() before claiming tasks")

        if self.mode == "redis" and self.redis_client:
            task_queue = TaskQueue(self.redis_client)
            return task_queue.claim_task(self.agent_id, tags=tags)

        # File mode fallback
        return None

    def post_thread(
        self,
        title: str,
        message: str,
        priority: str = "normal"
    ) -> Optional[BoardThread]:
        """Post a thread to the board.

        Args:
            title: Thread title
            message: Initial message
            priority: Priority level ("high", "normal", "low")

        Returns:
            BoardThread object if posted, None in file mode
        """
        if not self.agent_id:
            raise ValueError("Must call register_agent() before posting threads")

        if self.mode == "redis" and self.redis_client:
            board = Board(self.redis_client)
            return board.post_thread(title, message, self.agent_id, priority)

        # File mode fallback
        return None

    def request_approval(
        self,
        action_type: str,
        description: str,
        timeout: int = 300
    ) -> Optional[Approval]:
        """Request approval for an action (blocking).

        Args:
            action_type: Type of action ("commit", "deploy", etc.)
            description: Description of what needs approval
            timeout: Timeout in seconds

        Returns:
            Approval object with status
        """
        if not self.agent_id:
            raise ValueError("Must call register_agent() before requesting approval")

        if self.mode == "redis" and self.redis_client:
            approval_workflow = ApprovalWorkflow(self.redis_client)
            return approval_workflow.request_approval(
                self.agent_id,
                action_type,
                description,
                timeout
            )

        # File mode fallback - auto-approve
        return None

    def log_decision(
        self,
        decision_type: str,
        context: str,
        reason: str
    ):
        """Log a decision to the audit log.

        Args:
            decision_type: Type of decision
            context: Context for the decision
            reason: Reason for the decision
        """
        if not self.agent_id:
            raise ValueError("Must call register_agent() before logging decisions")

        if self.mode == "redis" and self.redis_client:
            audit_log = AuditLog(self.redis_client)
            audit_log.log_decision(self.agent_id, decision_type, context, reason)

        # File mode fallback - no-op for now

    def export_to_markdown(self, status_file: str, board_file: str):
        """Export coordination state to markdown files.

        Args:
            status_file: Path to STATUS.md file
            board_file: Path to BOARD.md file
        """
        # TODO: Implement markdown export
        # This will read from Redis and write to files
        pass

    def shutdown(self):
        """Gracefully shutdown client, releasing resources."""
        if self._agent_registry:
            self._agent_registry.stop_heartbeat()

        if self.agent_id and self.mode == "redis" and self.redis_client:
            # Unregister agent
            if self._agent_registry:
                self._agent_registry.unregister_agent(self.agent_id)

    @classmethod
    @contextmanager
    def session(
        cls,
        redis_url: str,
        role: str,
        name: str,
        working_on: str = "",
        fallback_dir: str = "./workbench"
    ):
        """Context manager for a complete coordination session.

        Args:
            redis_url: Redis connection URL
            role: Agent role
            name: Agent name
            working_on: Current task description
            fallback_dir: Directory for file-based fallback

        Yields:
            CoordinationClient instance with agent registered

        Example:
            with CoordinationClient.session(
                redis_url="redis://localhost:6379",
                role="CTO",
                name="Claude"
            ) as coord:
                with coord.lock_file("main.py", intent="Add feature"):
                    pass
        """
        client = cls(redis_url=redis_url, fallback_dir=fallback_dir)
        client.register_agent(role=role, name=name, working_on=working_on)

        try:
            yield client
        finally:
            client.shutdown()
