#!/usr/bin/env python3
"""Simple task dashboard for agentcoord."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "agentcoord" / "agentcoord"))
from tasks import TaskQueue, TaskStatus

# Accept database path as argument
if len(sys.argv) > 1:
    db_path = Path(sys.argv[1])
else:
    # Default to coordination workspace
    db_path = Path.home() / "agentcoord" / "workspace" / "coordination" / "tasks.db"

if not db_path.exists():
    print(f"❌ No tasks database found")
    print(f"   Create tasks first with: python3 ~/agentcoord/create_task.py")
    sys.exit(1)

task_queue = TaskQueue(db_path=str(db_path))

print("\n" + "="*70)
print("  AGENTCOORD TASK DASHBOARD")
print("="*70 + "\n")

# Get all tasks
import sqlite3
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
tasks = cursor.fetchall()

if not tasks:
    print("No tasks found.\n")
    sys.exit(0)

# Count by status
pending = sum(1 for t in tasks if t['status'] == TaskStatus.PENDING.value)
claimed = sum(1 for t in tasks if t['status'] == TaskStatus.CLAIMED.value)
completed = sum(1 for t in tasks if t['status'] == TaskStatus.COMPLETED.value)
failed = sum(1 for t in tasks if t['status'] == TaskStatus.FAILED.value)

print(f"Total Tasks: {len(tasks)}")
print(f"  Pending:   {pending}")
print(f"  Claimed:   {claimed}")
print(f"  Completed: {completed}")
print(f"  Failed:    {failed}")
print()

# Show each task
for task in tasks:
    status_icon = {
        TaskStatus.PENDING.value: "⏳",
        TaskStatus.CLAIMED.value: "🔄",
        TaskStatus.COMPLETED.value: "✅",
        TaskStatus.FAILED.value: "❌",
    }.get(task['status'], "❓")

    print(f"{status_icon} [{task['status'].upper()}] {task['title']}")
    print(f"   ID: {task['id'][:8]}...")
    if task['agent_id']:
        print(f"   Agent: {task['agent_id']}")
    print(f"   Created: {task['created_at']}")
    if task['status'] == TaskStatus.COMPLETED.value and task['result']:
        result_preview = task['result'][:100] + "..." if len(task['result']) > 100 else task['result']
        print(f"   Result: {result_preview}")
    print()

conn.close()

print("="*70)
print(f"Database: {db_path}")
print("="*70 + "\n")
