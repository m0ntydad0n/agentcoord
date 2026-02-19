#!/usr/bin/env python3
"""
Simple worker that claims and executes tasks from agentcoord queue.
This is me (Claude Code) working as an agentcoord worker!
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agentcoord import CoordinationClient

def main():
    # Register as a worker
    with CoordinationClient.session(
        redis_url="redis://localhost:6379",
        role="Implementation Worker",
        name="Claude-Code-Worker",
        working_on="Building AgentCoord improvements"
    ) as coord:
        print("🤖 Worker registered and ready!")
        print("   Claiming tasks from queue...\n")

        # Claim a task
        task = coord.claim_task(tags=["design", "implementation"])

        if task:
            print(f"✓ Claimed task: {task.title}")
            print(f"  Priority: {task.priority}")
            print(f"  Tags: {task.tags}")
            print(f"\n--- TASK DESCRIPTION ---")
            print(task.description)
            print("--- END DESCRIPTION ---\n")
            print(f"📋 Task ID: {task.id}")
            print(f"   Status: {task.status.value}")
            print(f"\n🔨 Ready to work on this task!")
            return task.id
        else:
            print("❌ No tasks available to claim")
            return None

if __name__ == "__main__":
    task_id = main()
    if task_id:
        print(f"\nNext: Work on task {task_id}")
