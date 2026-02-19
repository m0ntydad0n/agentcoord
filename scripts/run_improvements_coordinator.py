#!/usr/bin/env python3
"""
Run coordinator for AgentCoord improvements using the autoscaling framework.
This uses agentcoord's own spawning system to manage workers.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../examples'))

from autoscaling_coordinator import AutoScalingCoordinator
from agentcoord.spawner import SpawnMode

def main():
    print("🚀 Starting AgentCoord Improvements Coordinator")
    print("   Using agentcoord's autoscaling framework\n")

    # Create autoscaling coordinator
    coordinator = AutoScalingCoordinator(
        name="AgentCoord-Improvements-Coordinator",
        spawn_mode=SpawnMode.SUBPROCESS,  # Spawn workers as subprocesses
        min_workers=2,   # Always keep at least 2 workers
        max_workers=5,   # Scale up to 5 workers max
        tasks_per_worker=2  # Spawn 1 worker per 2 tasks
    )

    coordinator.start()

    # Tasks are already created in Redis, so just broadcast
    coordinator.broadcast_message(
        title="🔨 AgentCoord Improvements - Workers Needed",
        message="""
AgentCoord improvement tasks are ready in the queue!

Task categories:
- design: Architecture and schema design (2 tasks)
- implementation: Core implementation (4 tasks)
- cli: CLI enhancements (1 task)
- examples: Example code (1 task)
- testing/documentation: Integration work (1 task)

Workers will be spawned automatically based on queue depth.
Tags: design, implementation, llm, escalation, cli, examples, testing, documentation
        """,
        priority="high"
    )

    # Run the autoscaling loop
    print("\n" + "="*70)
    print("AUTO-SCALING COORDINATION MODE")
    print("="*70)
    print("\nCoordinator will:")
    print("  ✓ Spawn workers automatically based on queue depth")
    print("  ✓ Monitor worker health via heartbeats")
    print("  ✓ Track task progress")
    print("  ✓ Handle approvals (auto-approve for now)")
    print("  ✓ Reassign tasks from failed workers")
    print("\nMonitor with:")
    print("  python3 -m agentcoord.cli tasks    # View task queue")
    print("  python3 -m agentcoord.cli status   # View agents")
    print("  python3 -m agentcoord.cli board    # View messages")
    print("\nPress Ctrl+C to stop\n")

    coordinator.run_autoscaling_loop(
        interval=20,  # Check every 20 seconds
        max_iterations=None,  # Run until stopped
        auto_approve=True  # Auto-approve for demo
    )

if __name__ == "__main__":
    main()
