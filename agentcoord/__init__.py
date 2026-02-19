"""
AgentCoord - Redis-based multi-agent coordination system

Provides real-time coordination primitives for multiple Claude agents:
- Atomic file locking
- Task queue with priority
- Board-style threaded communication
- Approval workflows
- Decision audit logging
- Heartbeat monitoring
- Automatic fallback to file-based coordination

Usage:
    from agentcoord import CoordinationClient

    with CoordinationClient.session(
        redis_url="redis://localhost:6379",
        role="CTO",
        name="Claude"
    ) as coord:
        with coord.lock_file("backend/main.py", intent="Add /health endpoint"):
            # Safe to edit
            pass
"""

from .client import CoordinationClient
from .locks import LockAcquireTimeout, FileLock
from .tasks import Task, TaskStatus
from .board import BoardThread, ThreadStatus
from .approvals import Approval, ApprovalStatus

__version__ = "0.1.0"
__all__ = [
    "CoordinationClient",
    "LockAcquireTimeout",
    "FileLock",
    "Task",
    "TaskStatus",
    "BoardThread",
    "ThreadStatus",
    "Approval",
    "ApprovalStatus",
]
