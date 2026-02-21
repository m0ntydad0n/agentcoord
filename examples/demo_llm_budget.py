#!/usr/bin/env python3
"""
Demo script for LLM Budget tracking functionality.

Shows:
- Rate limiting with semaphores
- Cost tracking per model and agent
- Budget enforcement
- Statistics retrieval
"""

import redis
import time
from agentcoord.llm import LLMBudget, BudgetExceededError, SlotTimeoutError

def demo_basic_rate_limiting():
    """Demo basic rate limiting with semaphore."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Rate Limiting")
    print("="*60)

    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

    # Clean up any existing data
    for key in redis_client.scan_iter("llm:*"):
        redis_client.delete(key)

    # Create budget tracker with max 3 concurrent calls
    budget = LLMBudget(redis_client, max_concurrent=3)

    print("\nAcquiring 3 slots (should succeed)...")

    # Acquire 3 slots
    with budget.acquire_slot():
        print(f"  ✓ Slot 1 acquired. In-flight: {redis_client.get('llm:semaphore')}/3")

        with budget.acquire_slot():
            print(f"  ✓ Slot 2 acquired. In-flight: {redis_client.get('llm:semaphore')}/3")

            with budget.acquire_slot():
                print(f"  ✓ Slot 3 acquired. In-flight: {redis_client.get('llm:semaphore')}/3")
                print("\n  All 3 slots in use. Trying to acquire 4th slot (will timeout)...")

                try:
                    with budget.acquire_slot(timeout=2):
                        pass
                except SlotTimeoutError as e:
                    print(f"  ✓ Expected timeout: {e}")

    print(f"\n✓ All slots released. In-flight: {redis_client.get('llm:semaphore') or 0}/3")


def demo_cost_tracking():
    """Demo cost tracking per model and agent."""
    print("\n" + "="*60)
    print("DEMO 2: Cost Tracking")
    print("="*60)

    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

    # Clean up
    for key in redis_client.scan_iter("llm:*"):
        redis_client.delete(key)

    budget = LLMBudget(redis_client, max_concurrent=10)

    print("\nRecording LLM usage from 3 agents...")

    # Agent 1: Mostly uses Sonnet
    budget.record_usage("agent-backend-001", "claude-sonnet-4.5", 10000, 0.30)
    budget.record_usage("agent-backend-001", "claude-sonnet-4.5", 5000, 0.15)
    budget.record_usage("agent-backend-001", "claude-opus-4.6", 2000, 0.25)

    # Agent 2: Uses Haiku for fast tasks
    budget.record_usage("agent-qa-002", "claude-haiku-4.5", 50000, 0.12)
    budget.record_usage("agent-qa-002", "claude-haiku-4.5", 30000, 0.08)

    # Agent 3: Mixed usage
    budget.record_usage("agent-reviewer-003", "claude-sonnet-4.5", 8000, 0.24)
    budget.record_usage("agent-reviewer-003", "claude-opus-4.6", 3000, 0.35)

    print("\n  ✓ Recorded usage from 3 agents across 3 models")

    # Get statistics
    stats = budget.get_usage_stats()

    print(f"\n{'='*60}")
    print("USAGE STATISTICS")
    print(f"{'='*60}")
    print(f"\nTotal Tokens: {stats['total_tokens']:,}")
    print(f"Total Cost: ${stats['total_cost']:.2f}")
    print(f"In-Flight: {stats['in_flight']}/{stats['max_concurrent']}")

    print("\nBy Model:")
    for model, data in sorted(stats['by_model'].items()):
        print(f"  {model:<25} {data['tokens']:>8,} tokens  ${data['cost']:>6.2f}")

    print("\nBy Agent:")
    for agent_id, data in sorted(stats['by_agent'].items(),
                                  key=lambda x: x[1]['total_cost'],
                                  reverse=True):
        print(f"  {agent_id:<25} {data['calls']:>3} calls  "
              f"{data['total_tokens']:>8,} tokens  ${data['total_cost']:>6.2f}")


def demo_budget_enforcement():
    """Demo budget limit enforcement."""
    print("\n" + "="*60)
    print("DEMO 3: Budget Enforcement")
    print("="*60)

    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

    # Clean up
    for key in redis_client.scan_iter("llm:*"):
        redis_client.delete(key)

    # Set daily budget to $1.00
    budget = LLMBudget(
        redis_client,
        max_concurrent=10,
        daily_budget=1.00,
        per_agent_budget=0.50
    )

    print("\nBudget Limits:")
    print(f"  Daily Budget: $1.00")
    print(f"  Per-Agent Budget: $0.50")

    print("\nAgent 1: Using $0.30 (within limit)...")
    budget.record_usage("agent-1", "claude-sonnet-4.5", 10000, 0.30)

    if budget.check_budget_available("agent-1"):
        print("  ✓ Budget available for agent-1")
    else:
        print("  ✗ Budget exceeded!")

    print("\nAgent 1: Using another $0.25 (total $0.55, exceeds per-agent limit)...")
    budget.record_usage("agent-1", "claude-sonnet-4.5", 8000, 0.25)

    if budget.check_budget_available("agent-1"):
        print("  ✓ Budget available for agent-1")
    else:
        print("  ✓ Expected: Agent budget exceeded ($0.55 > $0.50)")

    print("\nAgent 2: Using $0.40 (within per-agent limit, but combined total approaching daily limit)...")
    budget.record_usage("agent-2", "claude-opus-4.6", 5000, 0.40)

    if budget.check_budget_available("agent-2"):
        print("  ✓ Budget still available for agent-2")
    else:
        print("  ✗ Budget exceeded!")

    print("\nAgent 3: Trying to use $0.15 (total $1.10, exceeds daily limit)...")
    budget.record_usage("agent-3", "claude-haiku-4.5", 10000, 0.15)

    if budget.check_budget_available("agent-3"):
        print("  ✗ Unexpected: Budget should be exceeded!")
    else:
        print("  ✓ Expected: Daily budget exceeded ($1.10 > $1.00)")


def demo_budget_reset():
    """Demo daily budget reset."""
    print("\n" + "="*60)
    print("DEMO 4: Budget Reset")
    print("="*60)

    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

    # Clean up
    for key in redis_client.scan_iter("llm:*"):
        redis_client.delete(key)

    budget = LLMBudget(redis_client, max_concurrent=10)

    print("\nRecording some usage...")
    budget.record_usage("agent-1", "claude-sonnet-4.5", 10000, 0.30)
    budget.record_usage("agent-2", "claude-opus-4.6", 5000, 0.50)

    stats_before = budget.get_usage_stats()
    print(f"  Before reset: ${stats_before['total_cost']:.2f} total cost")

    print("\nResetting daily budget...")
    budget.reset_daily_budget()

    stats_after = budget.get_usage_stats()
    print(f"  After reset: ${stats_after['total_cost']:.2f} total cost")
    print(f"  ✓ Budget reset successful!")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("LLM BUDGET TRACKING DEMO")
    print("="*60)

    try:
        demo_basic_rate_limiting()
        demo_cost_tracking()
        demo_budget_enforcement()
        demo_budget_reset()

        print("\n" + "="*60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nTry the CLI command:")
        print("  python3 -m agentcoord.cli budget")
        print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
