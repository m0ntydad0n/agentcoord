#!/usr/bin/env python3
"""Coordinator for personal usability improvements - parallel implementation."""

import sys
from pathlib import Path

# Add agentcoord to path
sys.path.insert(0, str(Path.home() / "agentcoord" / "agentcoord"))

# Import tasks directly (avoid broken __init__.py imports)
from tasks import TaskQueue, TaskStatus

# Workspace for this operation
WORKSPACE = Path.home() / "agentcoord" / "workspace" / "usability-improvements"
WORKSPACE.mkdir(parents=True, exist_ok=True)

def main():
    # Use SQLite-based task queue
    db_path = WORKSPACE / "tasks.db"
    task_queue = TaskQueue(db_path=str(db_path))

    print("=" * 70)
    print("  PERSONAL USABILITY IMPROVEMENTS - PARALLEL IMPLEMENTATION")
    print("=" * 70)
    print()

    # Define implementation tasks
    tasks = [
        {
            "title": "IMPLEMENT: janus validate command",
            "description": """CLI config validation: python3 -m janus.cli validate
Shows warnings, checks settings, exits 0 if valid / 1 if invalid.
Working directory: ~/Desktop/Janus_Engine"""
        },
        {
            "title": "IMPLEMENT: /performance bot command",
            "description": """Bot performance dashboard: /performance
Shows last 30 days metrics, IV rank filter impact.
Working directory: ~/Desktop/Janus_Engine"""
        },
        {
            "title": "IMPLEMENT: Enhanced config validation warnings",
            "description": """Config validation warnings in config.py
Checks IV rank, stop loss, DTE range, etc.
Working directory: ~/Desktop/Janus_Engine"""
        },
    ]

    # Create tasks in queue
    task_objs = []
    for task_def in tasks:
        task = task_queue.create_task(
            title=task_def["title"],
            description=task_def["description"],
        )
        task_objs.append(task)
        print(f"✅ Created task: {task.title}")
        print(f"   Task ID: {task.id}")
        print()

    print("=" * 70)
    print(f"  ✅ {len(tasks)} TASKS CREATED IN QUEUE")
    print("=" * 70)
    print()
    print(f"Database: {db_path}")
    print(f"Tasks: {len(task_objs)}")
    print()
    print("Next: Deploy workers to claim and execute tasks")
    print()

if __name__ == "__main__":
    main()
