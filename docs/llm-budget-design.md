# LLM Budget Design

**Status:** Design Phase
**Author:** Claude Code Coordinator
**Date:** 2026-02-18

## Overview

The LLM Budget system provides cost tracking and rate limiting for multi-agent systems that make LLM API calls. It prevents runaway costs and ensures fair resource allocation across agents.

## Goals

1. **Rate Limiting**: Cap maximum concurrent LLM calls to prevent API throttling
2. **Cost Tracking**: Track token usage and costs by model and agent
3. **Budget Enforcement**: Hard limits to prevent exceeding budget thresholds
4. **Observability**: Real-time visibility into LLM usage patterns

## Redis Schema

### 1. Semaphore (Rate Limiting)

**Key:** `llm:semaphore`
**Type:** String (integer counter)
**Purpose:** Track current in-flight LLM calls

```
Value: current number of active LLM calls (0-N)
```

**Operations:**
- `INCR llm:semaphore` - Acquire slot before LLM call
- `DECR llm:semaphore` - Release slot after LLM call
- `GET llm:semaphore` - Check current usage

**Enforcement:**
```python
current = redis.get('llm:semaphore') or 0
if current >= max_concurrent:
    wait_for_slot()  # Block until slot available
redis.incr('llm:semaphore')
```

### 2. Token Usage Tracking

**Keys:** `llm:costs:tokens:{model}`
**Type:** String (integer counter)
**Purpose:** Track total tokens used per model

**Examples:**
```
llm:costs:tokens:claude-sonnet-4.5    -> 1250000
llm:costs:tokens:claude-opus-4.6      -> 450000
llm:costs:tokens:claude-haiku-4.5     -> 2500000
```

**Operations:**
- `INCRBY llm:costs:tokens:{model} {tokens}` - Add tokens used
- `GET llm:costs:tokens:{model}` - Get total tokens for model

### 3. Dollar Cost Tracking

**Keys:** `llm:costs:dollars:{model}`
**Type:** String (float)
**Purpose:** Track total cost in dollars per model

**Examples:**
```
llm:costs:dollars:claude-sonnet-4.5    -> 4.56
llm:costs:dollars:claude-opus-4.6      -> 12.35
llm:costs:dollars:claude-haiku-4.5     -> 0.87
```

**Operations:**
- `INCRBYFLOAT llm:costs:dollars:{model} {cost}` - Add cost
- `GET llm:costs:dollars:{model}` - Get total cost for model

### 4. Per-Agent Tracking

**Keys:** `llm:costs:by_agent:{agent_id}`
**Type:** Hash
**Purpose:** Track usage breakdown for each agent

**Structure:**
```
llm:costs:by_agent:agent-123
    total_tokens    -> 50000
    total_cost      -> 1.25
    calls           -> 145
    claude-sonnet-4.5:tokens  -> 30000
    claude-sonnet-4.5:cost    -> 0.90
    claude-opus-4.6:tokens    -> 20000
    claude-opus-4.6:cost      -> 0.35
```

**Operations:**
- `HINCRBY llm:costs:by_agent:{agent_id} total_tokens {tokens}`
- `HINCRBYFLOAT llm:costs:by_agent:{agent_id} total_cost {cost}`
- `HINCRBY llm:costs:by_agent:{agent_id} calls 1`
- `HINCRBY llm:costs:by_agent:{agent_id} {model}:tokens {tokens}`
- `HINCRBYFLOAT llm:costs:by_agent:{agent_id} {model}:cost {cost}`
- `HGETALL llm:costs:by_agent:{agent_id}` - Get agent stats

### 5. Budget Limits

**Key:** `llm:budget:config`
**Type:** Hash
**Purpose:** Store budget configuration

**Structure:**
```
llm:budget:config
    max_concurrent     -> 10
    daily_limit        -> 50.00
    per_agent_limit    -> 5.00
    alert_threshold    -> 40.00
```

### 6. Daily Budget Reset

**Key:** `llm:budget:daily_reset`
**Type:** String (timestamp)
**Purpose:** Track when daily budget was last reset

**Value:** ISO timestamp of last reset

## API Design

### LLMBudget Class

```python
class LLMBudget:
    """Track and enforce LLM usage budgets."""

    def __init__(
        self,
        redis_client,
        max_concurrent: int = 10,
        daily_budget: Optional[float] = None,
        per_agent_budget: Optional[float] = None
    ):
        """
        Initialize LLM budget tracker.

        Args:
            redis_client: Redis client instance
            max_concurrent: Max simultaneous LLM calls
            daily_budget: Daily spending limit in dollars (None = no limit)
            per_agent_budget: Per-agent spending limit (None = no limit)
        """

    @contextmanager
    def acquire_slot(self, timeout: int = 30):
        """
        Acquire an LLM call slot (blocks if at capacity).

        Args:
            timeout: Max seconds to wait for slot

        Yields:
            Slot context (auto-released on exit)

        Raises:
            TimeoutError: If slot not available within timeout
        """

    def record_usage(
        self,
        agent_id: str,
        model: str,
        tokens: int,
        cost: float
    ):
        """
        Record LLM usage.

        Args:
            agent_id: Agent that made the call
            model: Model name (e.g., 'claude-sonnet-4.5')
            tokens: Total tokens used
            cost: Cost in dollars
        """

    def get_usage_stats(self) -> dict:
        """Get current usage statistics."""

    def check_budget_available(self, agent_id: str) -> bool:
        """Check if budget is available for agent."""

    def reset_daily_budget(self):
        """Reset daily budget counters."""
```

## Usage Examples

### Example 1: Basic Rate Limiting

```python
from agentcoord.llm import LLMBudget

budget = LLMBudget(
    redis_client=redis_client,
    max_concurrent=5  # Max 5 concurrent calls
)

# Acquire slot before LLM call
with budget.acquire_slot(timeout=30):
    response = call_llm_api(prompt)

# Slot auto-released after block
```

### Example 2: Cost Tracking

```python
budget = LLMBudget(
    redis_client=redis_client,
    max_concurrent=10,
    daily_budget=50.00  # $50/day limit
)

with budget.acquire_slot():
    response = call_llm_api(prompt)

    # Record usage
    budget.record_usage(
        agent_id=agent_id,
        model="claude-sonnet-4.5",
        tokens=response.usage.total_tokens,
        cost=calculate_cost(response.usage)
    )
```

### Example 3: Per-Agent Budgets

```python
budget = LLMBudget(
    redis_client=redis_client,
    max_concurrent=10,
    daily_budget=100.00,
    per_agent_budget=10.00  # $10 per agent
)

# Check budget before call
if not budget.check_budget_available(agent_id):
    raise BudgetExceededError(f"Agent {agent_id} exceeded budget")

with budget.acquire_slot():
    response = call_llm_api(prompt)
    budget.record_usage(agent_id, model, tokens, cost)
```

### Example 4: Get Usage Stats

```python
stats = budget.get_usage_stats()

print(f"Total cost: ${stats['total_cost']:.2f}")
print(f"Total tokens: {stats['total_tokens']:,}")
print(f"In-flight calls: {stats['in_flight']}/{stats['max_concurrent']}")

for model, data in stats['by_model'].items():
    print(f"{model}: {data['tokens']:,} tokens (${data['cost']:.2f})")

for agent_id, data in stats['by_agent'].items():
    print(f"{agent_id}: ${data['total_cost']:.2f}")
```

## Implementation Notes

### Atomic Operations

All Redis operations must be atomic to prevent race conditions:

- **Semaphore**: Use `INCR`/`DECR` (atomic counters)
- **Costs**: Use `INCRBY`/`INCRBYFLOAT` (atomic increments)
- **Slot Acquisition**: Use Lua script or Redis transactions for check-and-increment

### Blocking Behavior

When `max_concurrent` is reached:
1. `acquire_slot()` blocks and polls every 100ms
2. Times out after `timeout` seconds
3. Raises `TimeoutError` if slot never available

### Budget Enforcement

Budget checks happen at two points:
1. **Before call**: Check if budget available (fail fast)
2. **After call**: Record usage and update counters

### Daily Reset

Daily budget resets at midnight UTC:
- Cron job or coordinator checks `llm:budget:daily_reset`
- If last reset > 24h ago, reset all cost counters
- Update `llm:budget:daily_reset` timestamp

## Error Handling

```python
class BudgetExceededError(Exception):
    """Raised when budget limit is exceeded."""

class SlotTimeoutError(Exception):
    """Raised when LLM slot cannot be acquired within timeout."""
```

## Observability

### CLI Command

```bash
$ agentcoord budget

LLM Budget Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Daily Budget: $42.56 / $50.00 (85%)
In-Flight: 3 / 10 slots

By Model:
  claude-sonnet-4.5   125K tokens    $4.50
  claude-opus-4.6      50K tokens   $12.00
  claude-haiku-4.5    500K tokens    $1.25

Top Agents:
  agent-backend-001   $8.50  (45K tokens)
  agent-qa-002        $5.25  (28K tokens)
  agent-reviewer-001  $3.00  (15K tokens)
```

### Monitoring Integration

Export metrics for Prometheus/Grafana:
- `llm_budget_total_cost`
- `llm_budget_in_flight_calls`
- `llm_budget_tokens_total`
- `llm_budget_calls_total`

## Future Enhancements

1. **Per-model budgets**: Different limits for different models
2. **Time-based budgets**: Hourly/weekly limits in addition to daily
3. **Agent priorities**: Higher-priority agents get preferential slot allocation
4. **Cost predictions**: Estimate cost before making call
5. **Alerts**: Notify when approaching budget limits

## Testing Strategy

1. **Unit tests**: Test each Redis operation in isolation
2. **Concurrency tests**: Test semaphore under high load
3. **Budget enforcement tests**: Verify hard limits work
4. **Integration tests**: Full workflow with real Redis

## References

- Model pricing: https://www.anthropic.com/pricing
- Redis atomic operations: https://redis.io/commands/?group=generic
- Python context managers: https://docs.python.org/3/library/contextlib.html
