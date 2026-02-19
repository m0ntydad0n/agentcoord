# AgentCoord

Redis-based multi-agent coordination system for building reliable multi-agent AI systems.

## Features

- 🔒 **Atomic file locking** - Prevent race conditions with Redis-backed locks
- 🤝 **Agent coordination** - Register agents, track heartbeats, detect hung agents
- 📋 **Task queue** - Priority-based task claiming with atomic operations
- 💬 **Board system** - Threaded communication between agents
- ✅ **Approval workflows** - Blocking approval requests for critical operations
- 📝 **Audit logging** - Append-only decision log with Redis Streams
- 🔄 **Automatic fallback** - Gracefully degrades to file-based mode when Redis unavailable

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from agentcoord import CoordinationClient

# Using context manager (recommended)
with CoordinationClient.session(
    redis_url="redis://localhost:6379",
    role="Engineer",
    name="Agent-1",
    working_on="Building features"
) as coord:
    # Lock files atomically
    with coord.lock_file("backend/main.py", intent="Add /health endpoint"):
        # Safe to edit - lock auto-released on exit
        pass

    # Claim tasks from queue
    task = coord.claim_task(tags=["backend"])
    if task:
        print(f"Working on: {task.title}")

    # Post to board
    coord.post_thread(
        title="Deployment Complete",
        message="Backend v2.0 deployed successfully",
        priority="high"
    )

    # Log decisions
    coord.log_decision(
        decision_type="deployment",
        context="Backend v2.0",
        reason="New features tested and ready"
    )
```

## CLI

Monitor and manage coordination state:

```bash
# View all agents
agentcoord status

# Show file locks
agentcoord locks

# View task queue
agentcoord tasks

# Show board threads
agentcoord board

# Detect hung agents
agentcoord hung --threshold 300

# Approve pending requests
agentcoord approve <approval-id>
```

## Running Redis

```bash
# Local development
docker run -d -p 6379:6379 redis:7-alpine

# Production (Railway)
railway add redis
```

## Testing

```bash
# Run test suite
pytest tests/ -v

# Test with file mode (no Redis needed)
python3 examples/basic_usage.py

# Test with Redis
docker run -d -p 6379:6379 redis:7-alpine
python3 examples/basic_usage.py
```

## Architecture

**Redis Primary + File Fallback:**
- Real-time coordination via Redis when available
- Automatic fallback to file-based mode when Redis unavailable
- No code changes needed - transparent failover

**Core Components:**
- `CoordinationClient` - Main API for agent coordination
- `FileLock` - Atomic file locking with TTL auto-expiry
- `AgentRegistry` - Agent registration and heartbeat monitoring
- `TaskQueue` - Priority-based task queue with atomic claiming
- `Board` - Threaded communication system
- `ApprovalWorkflow` - Blocking approval requests
- `AuditLog` - Append-only decision logging

## Use Cases

- **Multi-agent AI systems** - Coordinate multiple Claude instances
- **Distributed development** - Prevent file conflicts between agents
- **Workflow orchestration** - Task queue and approval gates
- **System monitoring** - Track agent health and decisions

## License

MIT

## Contributing

Contributions welcome! This is an early-stage project built to support multi-agent AI coordination.
