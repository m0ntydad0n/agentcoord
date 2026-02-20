# AgentCoord

Multi-agent coordination system that models real company structures with cross-functional workflows.

## Overview

AgentCoord orchestrates autonomous AI agents across Product, Engineering, QA, Marketing, and Support departments—mirroring how real companies coordinate work. Built for complexity: multi-role task routing, approval gates, and platform-agnostic communication.

## Features

### Company Model
- 🏢 **Real Org Structure** - 17 roles across 5 departments (Product, Engineering, QA, Marketing, Support)
- 🎯 **Role-Based Permissions** - 50+ capabilities with inheritance (VPs inherit department capabilities)
- 👥 **Hierarchical Teams** - Company → Department → Team → Agent with availability tracking
- 📋 **Workflow Routing** - Automated task generation from Epic workflows (feature, bug, launch, trading_strategy)
- ✅ **Approval Gates** - Multi-role sign-off for critical operations (production deploy requires EM + QA Lead + PM)
- 🏗️ **Company Templates** - Load org structures from YAML (startup, scaleup, custom)

### Communication
- 💬 **Platform-Agnostic Channels** - Works out-of-box (Terminal, File, Dashboard) with optional Slack/Discord
- 🔔 **Priority Messaging** - LOW, NORMAL, HIGH, URGENT with type tagging (STATUS, ERROR, SUCCESS)
- 🧵 **Threaded Conversations** - Multi-channel thread support with UUID tracking
- 📡 **Multi-Channel Broadcasting** - Post to all channels simultaneously

### Legacy Coordination (Redis-backed)
- 🤖 **LLM-Powered Workers** - Autonomous agents that write code using Claude/GPT APIs
- 🔒 **Atomic File Locking** - Prevent race conditions with Redis-backed locks
- 📋 **Task Queue** - Priority-based task claiming with atomic operations
- 🚀 **Dynamic Spawning** - Spawn workers on-demand (subprocess, Docker, Railway)
- 📝 **Audit Logging** - Append-only decision log with Redis Streams
- 🔄 **Automatic Fallback** - Gracefully degrades to file-based mode when Redis unavailable

## Installation

```bash
pip install -e .
```

## Quick Start - Interactive TUI

```bash
# Launch interactive dashboard (recommended for new users)
agentcoord

# Or launch dashboard directly
agentcoord dashboard
```

The TUI provides:
- Real-time task monitoring
- Worker status visualization
- Interactive task creation
- Onboarding wizard for first-time users
- Cyberpunk 90s aesthetic 🌈

## Quick Start - Company Model

Create a company and route work across departments:

```python
from agentcoord.company import Company
from agentcoord.workflows import Epic, WorkflowRouter, ArtifactStatus
from agentcoord.roles import Role

# Load company from template
company = Company.from_template("janus_dev")
# Creates: Product dept (PM, Designer), Engineering (EM, Engineers, SRE), QA (Lead, Engineers)

# Create epic for new trading strategy
epic = Epic(
    id="epic-001",
    title="Add IV Percentile Filter",
    description="Filter trades to only enter when IV > 50th percentile",
    workflow_type="trading_strategy",
    status=ArtifactStatus.PENDING,
    created_by="strategy_pm"
)

# Route epic - generates 8 tasks automatically
router = WorkflowRouter(company)
task_ids = router.route_epic(epic)
# Creates: PM define goals → Designer schema → Eng implement → Eng test →
#          QA backtest → QA validate → PM approve → SRE deploy

# Find available agent for first task
pm_agent = company.find_available_agent(role=Role.PRODUCT_MANAGER)
print(f"Assigned to: {pm_agent.name}")

# Agent claims and completes task
pm_agent.claim_task(task_ids[0])
pm_agent.complete_task(task_ids[0], result={"prd": "strategy_goals.md"})
```

### Communication Channels

```python
from agentcoord.channels import ChannelManager, TerminalChannel, FileChannel

# Set up multi-channel communication
channels = ChannelManager()
channels.add_channel(TerminalChannel(name="console"))
channels.add_channel(FileChannel(name="logs", log_dir="./logs"))

# Broadcast to all channels
channels.post(
    channel="engineering",
    message="Tests passing - ready for QA",
    priority="NORMAL",
    message_type="SUCCESS"
)

# Direct message
channels.dm(
    from_agent="backend_em",
    to_agent="qa_lead",
    message="Deploy candidate ready for validation"
)

# Create threaded conversation
thread_id = channels.create_thread(
    channel="design",
    title="New Config Schema Review",
    message="Proposed schema for IV percentile filter attached"
)
```

## Quick Start - Legacy Coordination

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

## LLM-Powered Autonomous Workers

Spawn workers that use Claude/GPT to write actual code:

```python
from agentcoord.spawner import WorkerSpawner, SpawnMode

spawner = WorkerSpawner(redis_url="redis://localhost:6379")

# Spawn LLM-powered worker that writes code
worker = spawner.spawn_worker(
    name="Backend-Worker-1",
    tags=["backend"],
    mode=SpawnMode.SUBPROCESS,
    use_llm=True,  # 🤖 This worker uses Claude to write code
    max_tasks=10
)

# The worker will:
# 1. Claim tasks matching its tags
# 2. Use Claude API to generate code
# 3. Write files autonomously
# 4. Mark tasks complete
```

**Example - Spawn 3 LLM workers to build UI in parallel:**

```python
# Create 10 UI building tasks
tasks = [
    {'title': 'Create dashboard component', 'tags': ['ui']},
    {'title': 'Add authentication form', 'tags': ['ui']},
    # ... 8 more tasks
]

for task_data in tasks:
    task_queue.create_task(**task_data)

# Spawn 3 LLM workers to execute in parallel
for i in range(3):
    spawner.spawn_worker(
        name=f"UI-Builder-{i+1}",
        tags=["ui"],
        use_llm=True,
        max_tasks=5
    )

# Workers autonomously generate ~2,000 lines of code in 10 minutes
# Cost: ~$1-2 total
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

## Hierarchical Coordination

Build coordinator hierarchies (CTO → Team Leads → Workers):

```python
# Example: CTO coordinates specialized review teams
from agentcoord.spawner import WorkerSpawner

spawner = WorkerSpawner(redis_url="redis://localhost:6379")

# CTO creates specialized tasks
task_queue.create_task(
    title="Security Review - Auth & Secrets",
    tags=["security", "review"],
    priority=5
)
task_queue.create_task(
    title="Architecture Review - Scalability",
    tags=["architecture", "review"],
    priority=5
)

# Spawn specialized team leads (each is an LLM agent)
spawner.spawn_worker(name="Security-Lead", tags=["security"], use_llm=True)
spawner.spawn_worker(name="Architect-Lead", tags=["architecture"], use_llm=True)

# Each lead autonomously completes their review
# See scripts/cto_code_review.py for full example
```

**Real Example - AgentCoord Reviewing Itself:**

```bash
python3 scripts/cto_code_review.py

# Spawns 6 specialized reviewers:
# - Security-Lead: finds API key exposure risks
# - Architect-Lead: analyzes scalability bottlenecks
# - Performance-Lead: identifies optimization opportunities
# - Quality-Lead: assesses test coverage
# - DevOps-Lead: reviews deployment readiness
# - Integration-Lead: maps component interactions

# Output: 6 comprehensive review reports in ~15 minutes
# Cost: ~$2-4 total
```

## CLI

Monitor and manage coordination state:

```bash
# Launch interactive dashboard
agentcoord

# Or use specific commands:
agentcoord dashboard        # Live monitoring dashboard
agentcoord status          # View all agents
agentcoord tasks           # View task queue
agentcoord locks           # Show file locks
agentcoord board           # Show board threads
agentcoord hung            # Detect hung agents
agentcoord approve <id>    # Approve pending requests
```

## Running Redis

### Local Development (No Auth)

```bash
# Dev only - NO PASSWORD
docker run -d -p 6379:6379 redis:7-alpine
```

### Production (Auth Required)

```bash
# With authentication (REQUIRED for production)
docker run -d -p 6379:6379 redis:7-alpine redis-server --requirepass your-strong-password

# Set Redis URL with auth
export REDIS_URL="redis://:your-strong-password@localhost:6379"

# Or use Railway/managed Redis (recommended)
railway add redis
export REDIS_URL=$(railway variables get REDIS_URL)
```

**⚠️ SECURITY WARNING:**
- **NEVER** run Redis without auth in production
- **NEVER** expose Redis port to internet without TLS
- **ALWAYS** use `REDIS_URL` with password in prod
- See `SECURITY.md` for full security guide

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

## Workflows

AgentCoord includes 4 built-in workflow types:

### 1. `trading_strategy` (8 tasks)
For developing trading strategies (Janus use case):
```
PM define goals → Designer schema → Eng implement → Eng test →
QA backtest → QA validate → PM approve → SRE deploy
```
**Approval gates:** strategy_config_schema, backtest_validation, production_trading_deploy (PM + QA Lead + EM)

### 2. `feature` (6 tasks)
Standard feature development:
```
PM PRD → Designer mocks → Eng implement → QA test → PM approve → Growth launch
```
**Approval gates:** design_kickoff, design_review, code_review, qa_signoff, production_release

### 3. `bug` (3 tasks)
Rapid bug fix cycle:
```
QA reproduce → Eng fix → QA verify
```
**Approval gates:** triage, code_review, qa_verification

### 4. `launch` (6 tasks)
Cross-functional product launch:
```
PM plan → (Growth content + Eng flags + Support docs) → QA regression → Growth execute
```
**Approval gates:** launch_plan_review, readiness_check

## Use Cases

### Company Model
- **Cross-Functional Coordination** - PM → Design → Eng → QA workflows with approval gates
- **Trading Strategy Development** - Backtest validation, multi-gate production deploy
- **Product Launches** - Coordinate Marketing, Engineering, QA, Support
- **Multi-Department Projects** - Route work across Product, Engineering, QA

### Legacy Coordination
- **Autonomous Code Generation** - Spawn LLM workers to write code in parallel
- **Hierarchical Coordination** - Build org charts of AI agents (CTO → Teams → Workers)
- **Code Reviews** - Specialized AI agents review code from different perspectives
- **Multi-agent AI Systems** - Coordinate multiple Claude/GPT instances
- **Distributed Development** - Prevent file conflicts between agents

## Real-World Results

**AgentCoord building itself:**
- 3 LLM workers generated 29 files (3,832 lines) of UI code
- Interactive TUI built by 4 autonomous agents (650 lines)
- 6 specialized reviewers performed comprehensive code audit
- Total autonomous code generation: ~4,500 lines
- Total cost: ~$3-4
- Total time: ~30 minutes of parallel execution

**Company Model (Phase 1):**
- 17 roles across 5 departments with 50+ capabilities
- 4 complete workflow types with automated task routing
- 107 passing tests (roles, company hierarchy, channels)
- Platform-agnostic communication (works with zero external dependencies)
- Janus trading strategy workflow with 3-gate production approval

**Dogfooding:** AgentCoord used AgentCoord to build and review AgentCoord. 🚀

## Architecture

**Company Model:**
- `Role` - 17 roles with capability-based permissions
- `Company` - Hierarchical org structure (Company → Department → Team → Agent)
- `Epic/Story/Task` - Work artifacts with workflow routing
- `WorkflowRouter` - Automated task generation from workflow type
- `CommunicationChannel` - Platform-agnostic messaging (Terminal, File, Dashboard, Slack)
- `ApprovalGate` - Multi-role approval requirements

**Legacy Coordination:**

## License

MIT

## Contributing

Contributions welcome! This is an early-stage project built to support multi-agent AI coordination.
