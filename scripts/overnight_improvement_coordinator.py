#!/usr/bin/env python3
"""
Overnight Improvement Coordinator

Spawns autonomous agents to improve AgentCoord while you sleep.
Focus: Actionable improvements, not just reviews.
"""

import os
import sys
import redis
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# Ensure API key from environment only
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    console.print("[red]❌ ANTHROPIC_API_KEY not set[/red]")
    console.print("[yellow]Set it with: export ANTHROPIC_API_KEY='your-key'[/yellow]")
    sys.exit(1)

# Connect to Redis
try:
    redis_client = redis.from_url(
        os.getenv('REDIS_URL', 'redis://localhost:6379'),
        decode_responses=True
    )
    redis_client.ping()
except Exception as e:
    console.print(f"[red]❌ Cannot connect to Redis: {e}[/red]")
    sys.exit(1)

from agentcoord.tasks import TaskQueue
from agentcoord.spawner import WorkerSpawner, SpawnMode

# Display header
console.clear()
console.print(Panel.fit(
    "[bold cyan]🌙 OVERNIGHT IMPROVEMENT COORDINATOR[/bold cyan]\n"
    "[dim]Autonomous agents improving AgentCoord while you sleep[/dim]\n"
    "[yellow]Focus: Ship actionable improvements, not just analysis[/yellow]",
    border_style="cyan",
    padding=(1, 2)
))

console.print("\n[bold]Mission: Make AgentCoord Better By Morning[/bold]")
console.print("=" * 80)

# Define improvement tasks (actionable, not just reviews)
improvement_tasks = [
    {
        'title': 'Add Missing Unit Tests - Core Modules',
        'description': '''Add comprehensive unit tests for core modules.

Focus on:
1. agentcoord/tasks.py - TaskQueue operations
   - Test task creation with all parameters
   - Test priority ordering
   - Test tag filtering
   - Test status transitions
   - Edge cases: empty queues, invalid IDs

2. agentcoord/locks.py - FileLock atomicity
   - Test lock acquisition/release
   - Test timeout behavior
   - Test race conditions (concurrent claims)
   - Test TTL expiry

3. agentcoord/spawner.py - Worker lifecycle
   - Test spawn_worker with all modes
   - Test worker termination
   - Test max_tasks enforcement

Create: tests/test_tasks.py, tests/test_locks.py, tests/test_spawner.py

Use pytest, include fixtures, aim for 80%+ coverage on these modules.
Write actual working tests that can be run immediately.
''',
        'priority': 5,
        'tags': ['testing', 'quality', 'unit-tests']
    },

    {
        'title': 'Add Integration Tests - End-to-End Workflows',
        'description': '''Create integration tests for real-world workflows.

Test scenarios:
1. Coordinator spawns workers → workers claim tasks → tasks complete
   - Verify full lifecycle works
   - Check Redis state at each step
   - Validate cleanup on completion

2. LLM worker executes actual task → generates code → marks complete
   - Mock Anthropic API (don't burn credits)
   - Verify file creation
   - Check audit log entries

3. Auto-scaling: queue fills → workers spawn → queue drains → workers terminate
   - Test threshold triggering
   - Verify worker count scales correctly

Create: tests/test_integration_workflows.py

Use fixtures for Redis cleanup, mock external APIs.
Make tests runnable with: pytest tests/test_integration_workflows.py -v
''',
        'priority': 5,
        'tags': ['testing', 'integration', 'e2e']
    },

    {
        'title': 'Improve Error Handling - Client & Spawner',
        'description': '''Add robust error handling and recovery.

1. agentcoord/client.py:
   - Handle Redis connection drops gracefully
   - Add retry logic for transient failures
   - Better error messages (include context)
   - Validate inputs before Redis calls

2. agentcoord/spawner.py:
   - Handle worker spawn failures (resource limits, permissions)
   - Add timeout for worker startup
   - Clean up zombie processes
   - Log spawn failures with diagnostics

3. examples/llm_worker_agent.py:
   - Handle Anthropic API rate limits (429 errors)
   - Retry with exponential backoff
   - Handle malformed LLM responses gracefully
   - Better error messages for debugging

Add try/except blocks, custom exceptions, helpful error messages.
''',
        'priority': 4,
        'tags': ['reliability', 'error-handling', 'resilience']
    },

    {
        'title': 'Add CLI Commands - Missing Functionality',
        'description': '''Extend agentcoord CLI with useful commands.

Add to agentcoord/cli.py:

1. agentcoord workers
   - List all active workers
   - Show: name, tags, tasks_completed, uptime
   - Table format with Rich

2. agentcoord cleanup
   - Remove stale tasks (created >24h ago, not claimed)
   - Remove dead agents (no heartbeat >1h)
   - Clear orphaned locks
   - Show what was cleaned

3. agentcoord stats
   - Show system stats: total tasks, completion rate, avg time
   - Worker stats: total spawned, active, completed tasks
   - Cost estimate (if using LLM workers)

4. agentcoord spawn <name> --tags <tags>
   - Quick spawn worker from CLI
   - Support --llm flag for LLM workers

Implement with Click decorators, use Rich for formatting.
''',
        'priority': 4,
        'tags': ['cli', 'ux', 'features']
    },

    {
        'title': 'Add Connection Pooling - Redis Performance',
        'description': '''Implement Redis connection pooling for better performance.

Current issue: Each worker/client creates new connection
Impact: Connection overhead, potential exhaustion at scale

Fix:
1. agentcoord/client.py:
   - Use redis.ConnectionPool
   - Share pool across instances where possible
   - Configure max_connections based on expected workers

2. agentcoord/spawner.py:
   - Pass pool to spawned workers
   - Reuse connections in worker processes

3. Add configuration:
   - REDIS_MAX_CONNECTIONS env var (default: 50)
   - Pool timeout settings

Implementation:
```python
pool = redis.ConnectionPool.from_url(
    redis_url,
    max_connections=50,
    decode_responses=True
)
client = redis.Redis(connection_pool=pool)
```

Test with stress test: spawn 20+ workers, verify connection reuse.
''',
        'priority': 4,
        'tags': ['performance', 'redis', 'optimization']
    },

    {
        'title': 'Improve Documentation - API Reference',
        'description': '''Create comprehensive API documentation.

1. Add docstrings (Google style) to all public methods:
   - agentcoord/client.py - CoordinationClient
   - agentcoord/tasks.py - TaskQueue, Task
   - agentcoord/spawner.py - WorkerSpawner
   - agentcoord/agent.py - AgentRegistry

2. Create docs/API.md with:
   - Quick start examples
   - All public classes/methods
   - Parameters, return values, exceptions
   - Code examples for common patterns

3. Add type hints everywhere missing them:
   - Use typing.Optional, List, Dict
   - Add return type annotations
   - Make mypy-compliant

Don't create separate doc files for each class - consolidate into API.md.
Focus on the most commonly used APIs first.
''',
        'priority': 3,
        'tags': ['documentation', 'api', 'types']
    },

    {
        'title': 'Add Worker Health Checks - Monitoring',
        'description': '''Implement health check system for workers.

1. Add health_check endpoint to workers:
   - Responds with status, uptime, tasks_completed
   - Memory usage, CPU if available
   - Last task timestamp

2. Coordinator monitors worker health:
   - Ping workers periodically
   - Detect hung workers (no heartbeat >5min)
   - Auto-restart failed workers (optional)

3. Add to agentcoord/agent.py:
   - health_status field in Redis
   - update_health() method
   - get_unhealthy_workers() query

4. Add agentcoord health CLI command:
   - Show all workers with health status
   - Highlight unhealthy workers in red
   - Show last heartbeat time

Store health in Redis: agents:{id}:health
''',
        'priority': 3,
        'tags': ['monitoring', 'reliability', 'health']
    },

    {
        'title': 'Add Task Dependencies - DAG Support',
        'description': '''Add task dependency system for complex workflows.

Enable tasks like:
- Task B can't start until Task A completes
- Task D depends on both B and C completing

Implementation:
1. agentcoord/tasks.py:
   - Add depends_on field (list of task IDs)
   - When claiming task, check dependencies resolved
   - Skip task if dependencies incomplete
   - Auto-claim when dependencies complete

2. TaskQueue methods:
   - create_task(..., depends_on=[task_ids])
   - get_ready_tasks() - tasks with all deps complete
   - update claim logic to respect dependencies

3. Add visualization:
   - agentcoord dag command
   - Show task dependency graph
   - Highlight ready vs blocked tasks

Example:
```python
task_a = queue.create_task("Setup database", ...)
task_b = queue.create_task("Run migrations", depends_on=[task_a.id])
task_c = queue.create_task("Seed data", depends_on=[task_b.id])
```

This enables complex multi-step workflows.
''',
        'priority': 3,
        'tags': ['features', 'workflows', 'dag']
    },

    {
        'title': 'Add Metrics & Observability - Prometheus Export',
        'description': '''Add metrics for monitoring AgentCoord in production.

1. Add prometheus_client dependency
2. Create agentcoord/metrics.py:
   - Counter: tasks_created, tasks_completed, tasks_failed
   - Gauge: active_workers, pending_tasks, active_locks
   - Histogram: task_duration_seconds, llm_response_time

3. Add /metrics endpoint:
   - Expose Prometheus metrics
   - Optional HTTP server on :9090
   - Enable with --metrics flag

4. Update core modules to record metrics:
   - TaskQueue.create_task() → increment tasks_created
   - Task.mark_complete() → increment tasks_completed
   - WorkerSpawner.spawn_worker() → increment active_workers

5. Add to README: Monitoring section with Prometheus/Grafana setup

This enables production observability.
''',
        'priority': 2,
        'tags': ['observability', 'metrics', 'monitoring']
    },

    {
        'title': 'Refactor TaskQueue - Reduce God Object',
        'description': '''Break up TaskQueue into focused classes.

Current issue: TaskQueue does too much (architecture review ARCH-002)

Refactor into:
1. TaskRepository - CRUD operations
   - create(), get(), update(), delete()
   - Just data access, no business logic

2. TaskClaimer - Claiming logic
   - claim_task() with atomic operations
   - release_task()
   - Handle race conditions

3. TaskFilter - Query operations
   - get_by_tags()
   - get_by_status()
   - get_by_priority()

4. TaskQueue - Orchestrator (thin layer)
   - Composes the above
   - Public API stays the same

Keep backwards compatibility - existing code should still work.
Add tests for each new class.
''',
        'priority': 2,
        'tags': ['refactoring', 'architecture', 'cleanup']
    }
]

# Create tasks
task_queue = TaskQueue(redis_client)

console.print("\n📋 Creating improvement tasks...\n")

created_tasks = []
for task_data in improvement_tasks:
    task = task_queue.create_task(
        title=task_data['title'],
        description=task_data['description'],
        priority=task_data['priority'],
        tags=task_data['tags']
    )
    created_tasks.append(task)

    # Extract category
    category = task_data['title'].split(' - ')[0]
    priority_stars = "⭐" * task_data['priority']
    console.print(f"  ✅ {category} {priority_stars}")

console.print(f"\n[bold green]✓ Created {len(created_tasks)} improvement tasks[/bold green]")

# Display task summary
console.print("\n[bold]Improvement Task Summary[/bold]")
console.print("=" * 80)

summary_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
summary_table.add_column("Category", style="cyan", width=35)
summary_table.add_column("Priority", justify="center", width=8)
summary_table.add_column("Tags", style="yellow")

for task_data in improvement_tasks:
    category = task_data['title'].split(' - ')[0]
    priority = "⭐" * task_data['priority']
    tags = ", ".join(task_data['tags'][:2])  # First 2 tags
    summary_table.add_row(category, priority, tags)

console.print(summary_table)

# Spawn autonomous workers
console.print("\n[bold]Spawning Autonomous Improvement Workers[/bold]")
console.print("=" * 80)

spawner = WorkerSpawner()

console.print(f"\n🚀 Deploying 6 specialized improvement workers...\n")

worker_configs = [
    {'name': 'Testing-Engineer-1', 'tags': ['testing', 'quality', 'unit-tests']},
    {'name': 'Testing-Engineer-2', 'tags': ['testing', 'integration', 'e2e']},
    {'name': 'Backend-Engineer-1', 'tags': ['reliability', 'error-handling', 'performance']},
    {'name': 'Backend-Engineer-2', 'tags': ['cli', 'features', 'ux']},
    {'name': 'Platform-Engineer', 'tags': ['monitoring', 'observability', 'health']},
    {'name': 'Architect', 'tags': ['refactoring', 'architecture', 'workflows']},
]

workers = []
for config in worker_configs:
    worker = spawner.spawn_worker(
        name=config['name'],
        tags=config['tags'],
        mode=SpawnMode.SUBPROCESS,
        use_llm=True,
        max_tasks=3,  # Each worker can handle up to 3 tasks
        poll_interval=5
    )
    workers.append(worker)
    console.print(f"  ✅ {config['name']} deployed ({', '.join(config['tags'][:2])})")

console.print(f"\n[bold green]✓ {len(workers)} improvement workers active[/bold green]")

# Monitoring info
console.print("\n[bold]🌙 Overnight Improvement Process Running[/bold]")
console.print("=" * 80)

console.print("""
[cyan]Autonomous workers are now improving AgentCoord overnight.[/cyan]

📊 Monitor progress:
   [yellow]agentcoord dashboard[/yellow]        # Live dashboard
   [yellow]agentcoord tasks[/yellow]            # Task status
   [yellow]agentcoord status[/yellow]           # Worker status

📝 Workers will create:
   - New test files (tests/test_*.py)
   - Improved error handling
   - New CLI commands
   - Performance optimizations
   - Better documentation
   - Refactored code

⏱️  Expected completion: 2-4 hours
💰 Estimated cost: $3-6 (6 workers × 2-3 tasks each)
📈 Expected improvements: 10+ files modified/created

[dim]Workers operate fully autonomously - no approvals needed.
They'll write code, tests, and documentation while you sleep.[/dim]

[bold green]Sleep well! AgentCoord will be better in the morning. 🚀[/bold green]
""")

console.print("=" * 80 + "\n")
