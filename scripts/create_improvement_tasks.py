#!/usr/bin/env python3
"""
Create tasks for AgentCoord improvements using AgentCoord itself.
This is dogfooding at its finest.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agentcoord import CoordinationClient
from agentcoord.tasks import TaskQueue
import redis

def main():
    # Connect to Redis directly for task creation
    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
    task_queue = TaskQueue(redis_client)

    # Also create coordination client for board posts
    with CoordinationClient.session(
        redis_url="redis://localhost:6379",
        role="Coordinator",
        name="AgentCoord-Improvements-Coordinator",
        working_on="Creating tasks for LLM module and Escalation system"
    ) as coord:

        print("🚀 Creating tasks for AgentCoord improvements...\n")

        tasks = [
            # Phase 1: Design
            {
                "title": "Design LLM Budget Schema",
                "description": """
Design Redis schema for LLM budget tracking in agentcoord/llm.py:

Requirements:
- Semaphore for max concurrent LLM calls (Redis counter)
- Cost tracking: tokens and dollars per model/agent
- Budget enforcement with hard limits
- Per-agent and per-model breakdowns

Deliverables:
- Design doc with Redis key structure
- API design for LLMBudget class
- Usage examples

Redis keys to define:
- llm:semaphore (current in-flight calls)
- llm:costs:tokens:{model} (token usage)
- llm:costs:dollars:{model} (cost in dollars)
- llm:costs:by_agent:{agent_id} (per-agent tracking)
                """,
                "tags": ["design", "llm"],
                "priority": 5
            },

            {
                "title": "Design Escalation System Schema",
                "description": """
Design escalation system for agentcoord/escalation.py:

Requirements:
- Add "escalated" state to Task model
- Escalation channel pub/sub (channel:escalations)
- Retry policy configuration (linear, exponential, give up)
- Dead letter queue for terminal failures
- Escalation history tracking

Deliverables:
- Design doc with state transitions
- Redis pub/sub channel structure
- Retry policy configuration format
- API design for EscalationCoordinator class

State flow:
queued → assigned → in_progress → [completed | escalated]
escalated → (coordinator creates retry task) → queued
                """,
                "tags": ["design", "escalation"],
                "priority": 5
            },

            # Phase 2: LLM Module Implementation
            {
                "title": "Implement LLMBudget class",
                "description": """
Implement agentcoord/llm.py - LLMBudget class:

Class: LLMBudget
Methods:
- __init__(redis_client, max_concurrent=5, daily_budget=None)
- acquire_slot(timeout=30) -> context manager
- release_slot()
- record_cost(model, tokens, cost_dollars)
- get_current_usage() -> dict
- check_budget_available() -> bool
- reset_daily_budget()

Features:
- Redis-backed semaphore for rate limiting
- Blocking acquire until slot available
- Auto-release on context exit
- Cost accumulation in Redis hashes
- Budget enforcement (raise BudgetExceeded)

Tests:
- Test concurrent slot acquisition
- Test budget enforcement
- Test cost tracking accuracy
- Test Redis persistence
                """,
                "tags": ["implementation", "llm"],
                "priority": 4
            },

            {
                "title": "Implement LLM Fallback Handler",
                "description": """
Implement agentcoord/llm.py - Fallback handling:

Classes:
- LLMConfig (dataclass): primary_model, fallback_models, retry_strategy
- CircuitBreaker: track model failures, open circuit after N failures

Functions:
- call_llm_with_fallback(prompt, config) -> response
- Tries primary model
- Falls back through fallback_models list
- Implements exponential backoff
- Respects circuit breaker state
- Logs failures and fallbacks

Tests:
- Test fallback on AuthenticationError
- Test fallback on RateLimitError
- Test circuit breaker opens after failures
- Test all models fail scenario
                """,
                "tags": ["implementation", "llm"],
                "priority": 4
            },

            # Phase 3: Escalation System Implementation
            {
                "title": "Extend TaskQueue with Escalation",
                "description": """
Extend agentcoord/tasks.py with escalation support:

Add to Task dataclass:
- escalation_count: int = 0
- escalation_history: List[Dict] = []
- max_escalations: int = 3

Add to TaskQueue:
- escalate_task(task_id, reason, escalated_by)
  - Set status to "escalated"
  - Append to escalation_history
  - Increment escalation_count
  - Publish to channel:escalations
  - Add to dead letter queue if max_escalations reached

Redis:
- Update task status in Redis
- Publish escalation event
- Add to dlq:tasks sorted set if terminal

Tests:
- Test escalation state transition
- Test escalation history tracking
- Test pub/sub notification
- Test dead letter queue
                """,
                "tags": ["implementation", "escalation"],
                "priority": 4
            },

            {
                "title": "Implement EscalationCoordinator",
                "description": """
Create agentcoord/escalation.py - Auto-retry coordinator:

Class: EscalationCoordinator
- Subscribe to channel:escalations
- Listen for escalated tasks
- Apply retry policy
- Create retry tasks with increased priority
- Log to audit trail

Retry Policies:
- immediate: retry right away
- linear_backoff: wait N * attempt seconds
- exponential_backoff: wait 2^attempt seconds
- give_up: move to dead letter queue

Methods:
- handle_escalation(task_id)
- apply_retry_policy(task, policy)
- create_retry_task(original_task)
- log_escalation_decision()

Tests:
- Test immediate retry
- Test backoff delays
- Test max escalations → DLQ
- Test audit logging
                """,
                "tags": ["implementation", "escalation"],
                "priority": 4
            },

            # Phase 4: CLI & Integration
            {
                "title": "Add LLM Budget CLI Commands",
                "description": """
Extend agentcoord/cli.py with budget commands:

Commands:
- agentcoord budget
  - Show total costs (tokens + dollars)
  - Break down by model
  - Break down by agent
  - Show current in-flight calls
  - Show budget limits and remaining

- agentcoord budget reset
  - Reset daily budget counters

- agentcoord budget set --daily-limit <amount>
  - Configure budget limit

Output format (table):
Model               Tokens    Cost      In-Flight
claude-sonnet-4.5   125000    $0.45     2/5
claude-opus-4.6     50000     $1.20     0/5
Total                         $1.65     2/5

Tests:
- Test CLI output formatting
- Test budget display accuracy
                """,
                "tags": ["cli", "llm"],
                "priority": 3
            },

            {
                "title": "Create Autonomous Agent Example",
                "description": """
Create examples/autonomous_coordinator.py:

Demonstrates:
- Coordinator creates tasks
- Workers claim tasks
- Workers use LLMBudget for cost control
- Workers escalate on failure
- Coordinator handles escalations with auto-retry
- Full autonomous operation

Components:
- AutonomousCoordinator class
  - Spawns workers
  - Monitors queue
  - Handles escalations

- AutonomousWorker class
  - Claims tasks
  - Calls LLM with budget control
  - Escalates on errors
  - Respects rate limits

Usage:
python examples/autonomous_coordinator.py --max-workers 3 --budget 5.00

Should demonstrate resilient operation with LLM fallback and auto-retry.
                """,
                "tags": ["examples", "integration"],
                "priority": 3
            },

            {
                "title": "Integration Tests & Documentation",
                "description": """
Final integration work:

1. Integration tests (tests/test_llm_escalation_integration.py):
   - Full flow: task created → claimed → LLM call → failure → escalation → retry → success
   - Budget enforcement prevents runaway costs
   - Fallback works when primary model fails
   - Circuit breaker opens after repeated failures
   - Dead letter queue captures terminal failures

2. Documentation:
   - Update README.md with LLM module section
   - Update README.md with Escalation section
   - Add examples to README
   - Document Redis schema

3. Example update:
   - Update examples/coordinator_agent.py to use new features
   - Update examples/worker_agent.py to use LLMBudget

Acceptance criteria:
- All tests pass
- README is up to date
- Examples demonstrate new features
- Can run autonomous agents with cost control
                """,
                "tags": ["testing", "documentation", "integration"],
                "priority": 2
            }
        ]

        # Create all tasks
        task_ids = []
        for i, task_spec in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] Creating: {task_spec['title']}")
            task = task_queue.create_task(
                title=task_spec['title'],
                description=task_spec['description'],
                tags=task_spec.get('tags', []),
                priority=task_spec.get('priority', 3)
            )
            task_ids.append(task.id)
            print(f"    ✓ Task ID: {task.id}")

        print(f"\n✅ Created {len(task_ids)} tasks in Redis")

        # Post summary to board
        coord.post_thread(
            title="🚀 AgentCoord Improvements: LLM & Escalation",
            message=f"""
Created {len(tasks)} tasks for building LLM module and Escalation system.

**Phases:**
1. Design (2 tasks) - Define schemas and APIs
2. LLM Implementation (2 tasks) - Budget tracking & fallback
3. Escalation Implementation (2 tasks) - Auto-retry & DLQ
4. Integration (3 tasks) - CLI, examples, tests, docs

**Tags:**
- design: Architecture and schema design
- implementation: Core implementation work
- llm: LLM module features
- escalation: Escalation system features
- cli: CLI commands
- examples: Example code
- testing: Test coverage
- documentation: Docs and README

**Next Steps:**
Workers can start claiming tasks with:
- `agentcoord tasks` to see queue
- Claim by tags (e.g., design, implementation)
- Work through in priority order

Let's build this! 🔨
            """,
            priority="high"
        )

        print("\n📋 Posted summary to board")
        print("\n🎯 Next: Run workers to claim and execute tasks")
        print("   agentcoord tasks    # View task queue")
        print("   agentcoord board    # View board threads")
        print("   agentcoord status   # View agent status")

if __name__ == "__main__":
    main()
