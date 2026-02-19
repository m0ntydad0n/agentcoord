# Escalation System Design

**Author**: Agent-2-Escalation
**Date**: 2026-02-18
**Status**: Draft

## Overview

The escalation system provides automatic retry and escalation capabilities for failed tasks in AgentCoord. When a task fails, it can be automatically retried according to a configurable retry policy, or escalated to human/supervisor agents for intervention.

## State Model

### Task States (Extended)

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"  # NEW
```

### State Transitions

```
PENDING → CLAIMED → IN_PROGRESS → COMPLETED ✓
                              ↓
                          FAILED
                              ↓
                   [Retry Policy Check]
                         /      \
                [Retry]         [Escalate]
                    ↓               ↓
                PENDING         ESCALATED
                                    ↓
                          [Coordinator Action]
                                /      \
                    [Retry Manually]  [Archive]
                           ↓               ↓
                       PENDING        COMPLETED*
```

## Task Model Extensions

Add escalation fields to Task dataclass:

```python
@dataclass
class Task:
    # ... existing fields ...

    # Escalation fields
    retry_count: int = 0
    max_retries: int = 3
    retry_policy: str = "exponential"  # "linear", "exponential", "none"
    retry_delay_base: int = 60  # seconds
    escalated_at: Optional[str] = None
    escalation_reason: Optional[str] = None
    escalation_history: List[Dict[str, Any]] = None  # [{timestamp, reason, retry_count}, ...]
    parent_task_id: Optional[str] = None  # If this is a retry of another task
```

## Retry Policies

### Policy Types

1. **Linear**: Fixed delay between retries
   - Delay = `retry_delay_base` seconds
   - Example: 60s, 60s, 60s

2. **Exponential**: Exponential backoff
   - Delay = `retry_delay_base * (2 ^ retry_count)` seconds
   - Example: 60s, 120s, 240s

3. **None**: No automatic retries, escalate immediately
   - Go straight to ESCALATED state

### Configuration

Retry policy is set per task at creation:

```python
task = task_queue.create_task(
    title="Process data",
    description="...",
    retry_policy="exponential",
    max_retries=3,
    retry_delay_base=60
)
```

## Escalation Coordinator

### Architecture

```
┌─────────────────────────────────────────┐
│      EscalationCoordinator              │
│                                         │
│  - Subscribes to escalation events      │
│  - Manages retry scheduling             │
│  - Dead letter queue management         │
│  - Escalation notifications             │
└─────────────────────────────────────────┘
            ↓                    ↑
    [Redis Pub/Sub]      [Escalation Events]
            ↓                    ↑
┌─────────────────────────────────────────┐
│         TaskQueue                       │
│                                         │
│  - Mark task as FAILED                  │
│  - Publish escalation event             │
│  - Create retry tasks                   │
└─────────────────────────────────────────┘
```

### API Design

```python
class EscalationCoordinator:
    """Manages task escalation and retry logic."""

    def __init__(self, redis_client, escalation_channel="channel:escalations"):
        self.redis = redis_client
        self.pubsub = redis_client.pubsub()
        self.escalation_channel = escalation_channel

    def start_monitoring(self):
        """Start listening for escalation events."""
        self.pubsub.subscribe(self.escalation_channel)
        # Background thread or async loop

    def handle_failed_task(self, task_id: str, error: str):
        """
        Handle a failed task according to its retry policy.

        Args:
            task_id: The task that failed
            error: Error message/reason for failure

        Returns:
            Action taken: "retried", "escalated", "archived"
        """
        pass

    def escalate_task(self, task_id: str, reason: str):
        """
        Manually escalate a task to ESCALATED state.
        Publishes escalation event for notification.
        """
        pass

    def retry_task(self, task_id: str, delay: Optional[int] = None):
        """
        Schedule a retry for a failed task.
        Creates a new PENDING task with incremented retry_count.
        """
        pass

    def get_escalated_tasks(self) -> List[Task]:
        """Retrieve all currently escalated tasks."""
        pass

    def archive_task(self, task_id: str, reason: str):
        """Move task to dead letter queue."""
        pass

    def get_dead_letter_queue(self) -> List[Task]:
        """Retrieve tasks in dead letter queue."""
        pass
```

## Redis Data Structures

### Escalation Events (Pub/Sub)

**Channel**: `channel:escalations`

**Message Format** (JSON):
```json
{
    "event_type": "task_escalated",
    "task_id": "uuid-here",
    "task_title": "Process data batch",
    "reason": "Max retries exceeded (3/3)",
    "retry_count": 3,
    "timestamp": "2026-02-18T10:30:00Z",
    "claimed_by": "agent-123"
}
```

### Task Storage

Tasks stored as Redis hashes (existing):
- Key: `task:{task_id}`
- Fields include all Task dataclass fields (JSON for lists)

### Sorted Sets

1. **Pending Queue** (existing): `tasks:pending`
   - Score: priority * 1000000 + timestamp

2. **Retry Queue** (NEW): `tasks:retry`
   - Score: scheduled_retry_timestamp
   - Members: task_id
   - Coordinator polls this queue to re-queue tasks

3. **Escalated Set** (NEW): `tasks:escalated`
   - Score: escalation_timestamp
   - Members: task_id
   - For quick retrieval of escalated tasks

4. **Dead Letter Queue** (NEW): `tasks:dlq`
   - Score: archived_timestamp
   - Members: task_id
   - Terminal failures

### Escalation History

Stored as JSON list in task hash field `escalation_history`:

```json
[
    {
        "timestamp": "2026-02-18T10:25:00Z",
        "retry_count": 1,
        "reason": "Connection timeout",
        "action": "retried"
    },
    {
        "timestamp": "2026-02-18T10:26:30Z",
        "retry_count": 2,
        "reason": "Connection timeout",
        "action": "retried"
    },
    {
        "timestamp": "2026-02-18T10:28:45Z",
        "retry_count": 3,
        "reason": "Max retries exceeded",
        "action": "escalated"
    }
]
```

## TaskQueue Extensions

Add methods to TaskQueue class:

```python
class TaskQueue:
    # ... existing methods ...

    def fail_task(self, task_id: str, error: str):
        """
        Mark task as FAILED and publish escalation event.
        Triggers escalation coordinator to decide retry/escalate.
        """
        pass

    def schedule_retry(self, task: Task, delay: int) -> Task:
        """
        Schedule a task for retry after delay seconds.
        Creates new task with incremented retry_count.
        Adds to retry queue.
        """
        pass

    def escalate_task(self, task_id: str, reason: str):
        """
        Mark task as ESCALATED and add to escalated set.
        Publishes escalation event.
        """
        pass

    def get_retry_queue(self) -> List[Task]:
        """Get tasks scheduled for retry."""
        pass

    def get_escalated_tasks(self) -> List[Task]:
        """Get all escalated tasks."""
        pass
```

## Usage Examples

### Automatic Retry

```python
# Agent creates task with retry policy
task = task_queue.create_task(
    title="Fetch API data",
    description="Call external API",
    retry_policy="exponential",
    max_retries=3,
    retry_delay_base=60
)

# Agent processes task
task = coord.claim_task()
try:
    # ... do work ...
    task.status = TaskStatus.COMPLETED
    task_queue.update_task(task)
except Exception as e:
    # Mark as failed - triggers escalation coordinator
    task_queue.fail_task(task.id, str(e))

# EscalationCoordinator automatically:
# 1. Checks retry_count (0) < max_retries (3)
# 2. Calculates delay: 60 * (2^0) = 60 seconds
# 3. Schedules retry in 60 seconds
# 4. After 60 seconds, task goes back to PENDING
```

### Manual Escalation

```python
# Agent encounters unrecoverable error
task_queue.escalate_task(task.id, "Data corruption detected, human review needed")

# Escalation coordinator publishes event
# Supervisor agent receives notification
# Can manually retry or archive
```

### Coordinator Monitoring

```python
coordinator = EscalationCoordinator(redis_client)
coordinator.start_monitoring()

# Runs in background, processing:
# - Retry queue (move tasks back to PENDING when delay expires)
# - Escalation events (notify supervisors)
# - Dead letter queue management
```

## Implementation Plan

### Phase 1: Task Model Extensions
1. Add escalation fields to Task dataclass
2. Update TaskQueue.create_task() to accept retry policy
3. Add serialization/deserialization for new fields

### Phase 2: TaskQueue Extensions
1. Implement fail_task()
2. Implement schedule_retry()
3. Implement escalate_task()
4. Add retry queue and escalated set management

### Phase 3: EscalationCoordinator
1. Implement background monitoring
2. Implement retry queue polling
3. Implement escalation event publishing
4. Implement dead letter queue

### Phase 4: Integration
1. Add escalation support to CoordinationClient
2. CLI commands for viewing escalated tasks
3. Example autonomous agent with retry

## Testing Strategy

1. **Unit Tests**
   - Retry policy calculation
   - State transitions
   - Event publishing

2. **Integration Tests**
   - End-to-end retry flow
   - Escalation notification
   - Dead letter queue

3. **Stress Tests**
   - Many concurrent failures
   - Retry queue performance
   - Event throughput

## Security & Safety

- **Rate Limiting**: Prevent retry storms
- **Max Retry Cap**: Hard limit on retries (configurable, default 10)
- **Exponential Backoff Cap**: Max delay of 1 hour
- **DLQ Cleanup**: Automatic archival after 7 days
- **Event Validation**: Validate all pub/sub messages

## Future Enhancements

- Custom retry schedules (cron-like)
- Escalation routing (route to specific agents)
- Priority escalation (critical failures jump queue)
- Retry budgets (limit retries across all tasks)
- Human-in-the-loop approval before retry
- Metrics and dashboards
