#!/usr/bin/env python3
"""Quick script to create a task in agentcoord."""

import sys
from pathlib import Path

# Add agentcoord to path
sys.path.insert(0, str(Path.home() / "agentcoord" / "agentcoord"))
from tasks import TaskQueue

# Set up workspace and database
WORKSPACE = Path.home() / "agentcoord" / "workspace" / "my-tasks"
WORKSPACE.mkdir(parents=True, exist_ok=True)
db_path = WORKSPACE / "tasks.db"

# Create task queue
task_queue = TaskQueue(db_path=str(db_path))

# Create your task
task = task_queue.create_task(
    title=input("Task title: "),
    description=input("Task description: ")
)

print(f"\n✅ Task created!")
print(f"   ID: {task.id}")
print(f"   Database: {db_path}")
print(f"\nNext: Deploy worker with:")
print(f"  python3 ~/agentcoord/run_worker.py")
