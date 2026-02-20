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

from .coordination_client import CoordinationClient
from .locks import LockAcquireTimeout, FileLock
from .tasks import Task, TaskStatus, TaskQueue
from .board import BoardThread, ThreadStatus
from .approvals import Approval, ApprovalStatus
from .escalation import EscalationCoordinator
from .llm import LLMBudget, BudgetExceededError, SlotTimeoutError
from .llm_fallback import LLMFallbackHandler, FallbackStrategy

__version__ = "0.1.0"
__all__ = [
    "CoordinationClient",
    "LockAcquireTimeout",
    "FileLock",
    "Task",
    "TaskStatus",
    "TaskQueue",
    "BoardThread",
    "ThreadStatus",
    "Approval",
    "ApprovalStatus",
    "EscalationCoordinator",
    "LLMBudget",
    "BudgetExceededError",
    "SlotTimeoutError",
    "LLMFallbackHandler",
    "FallbackStrategy",
]
