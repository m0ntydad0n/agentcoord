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

## Orchestrator Pattern

**Coordinator Agent** - One agent manages a team of workers:

```python
from examples.coordinator_agent import CoordinatorAgent

# Create coordinator
coordinator = CoordinatorAgent(name="MainCoordinator")
coordinator.start()

# Create tasks
coordinator.create_tasks([
    {'title': 'Implement auth', 'priority': 5, 'tags': ['backend']},
    {'title': 'Design UI', 'priority': 4, 'tags': ['frontend']},
])

# Broadcast to workers
coordinator.broadcast_message(
    title="Project Kickoff",
    message="Tasks ready - check queue",
    priority="high"
)

# Run orchestration loop
coordinator.run_orchestration_loop(interval=30, auto_approve=True)
```

**Worker Agents** - Autonomous agents that execute tasks:

```python
from examples.worker_agent import WorkerAgent

# Create specialized worker
worker = WorkerAgent(name="Backend-Worker", tags=["backend"])
worker.start()

# Run worker loop (claims and executes tasks)
worker.run_worker_loop(poll_interval=5)
```

**Full Demo:**
```bash
# Terminal 1: Start coordinator
python3 examples/coordinator_agent.py

# Terminal 2: Start workers
python3 examples/worker_agent.py multi

# Terminal 3: Monitor
agentcoord status
agentcoord tasks
```

## Dynamic Worker Spawning

Coordinators can spawn worker agents on-demand:

```python
from agentcoord.spawner import WorkerSpawner, SpawnMode

spawner = WorkerSpawner(redis_url="redis://localhost:6379")

# Spawn subprocess worker
worker = spawner.spawn_worker(
    name="Backend-Worker-1",
    tags=["backend"],
    mode=SpawnMode.SUBPROCESS,
    max_tasks=10
)

# Check worker status
print(f"Worker alive: {worker.is_alive()}")

# Terminate worker
worker.terminate()
```

**Spawn Modes:**
- `SUBPROCESS` - Local Python processes (default)
- `DOCKER` - Docker containers
- `RAILWAY` - Railway cloud deployment

## Auto-Scaling

Auto-scale workers based on queue depth:

```python
from examples.autoscaling_coordinator import AutoScalingCoordinator
from agentcoord.spawner import SpawnMode

coordinator = AutoScalingCoordinator(
    min_workers=2,      # Always keep 2 workers
    max_workers=10,     # Scale up to 10 workers
    tasks_per_worker=5, # Spawn 1 worker per 5 pending tasks
    spawn_mode=SpawnMode.SUBPROCESS
)

coordinator.start()

# Auto-scaling runs automatically
coordinator.run_autoscaling_loop(interval=30)
```

**Demo:**
```bash
python3 examples/autoscaling_coordinator.py
# Watch workers spawn/terminate as queue fluctuates
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
