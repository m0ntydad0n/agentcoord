#!/usr/bin/env python3
"""LLM-powered worker for implementing Janus usability improvements."""

import os
import sys
import time
from pathlib import Path
from anthropic import Anthropic

# Add agentcoord to path (import directly to avoid broken __init__.py)
sys.path.insert(0, str(Path.home() / "agentcoord" / "agentcoord"))
from tasks import TaskQueue, TaskStatus

WORKSPACE = Path.home() / "agentcoord" / "workspace" / "usability-improvements"
JANUS_ROOT = Path.home() / "Desktop" / "Janus_Engine"

def execute_task_with_llm(task, client: Anthropic, worker_name: str):
    """Execute task using Claude API."""
    print(f"\n{'='*70}")
    print(f"  [{worker_name}] EXECUTING: {task.title}")
    print(f"{'='*70}\n")

    # Build implementation prompt
    prompt = f"""You are an implementation specialist working on the Janus Engine.

TASK: {task.title}

DESCRIPTION:
{task.description}

INSTRUCTIONS:
1. Read relevant files in ~/Desktop/Janus_Engine to understand current implementation
2. Make minimal necessary changes to implement the feature
3. Run full test suite: cd ~/Desktop/Janus_Engine && python3 -m pytest tests/ -v
4. Ensure all 340 tests pass
5. Commit changes with descriptive message
6. Return implementation summary with evidence

CRITICAL CONSTRAINTS:
- Follow ~/Desktop/Janus_Engine/CLAUDE.md strictly
- Maintain determinism contract
- Preserve all architectural boundaries
- All tests must pass
- Minimal diffs - no drive-by refactors

Working directory: {JANUS_ROOT}

Begin implementation now.
"""

    print(f"Calling Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract text response
    output_text = ""
    for block in response.content:
        if block.type == "text":
            output_text += block.text + "\n"

    # Save log
    log_file = WORKSPACE / "logs" / f"{task.id}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    log_file.write_text(f"""# {task.title}

Worker: {worker_name}
Task ID: {task.id}

## Output
{output_text}

## API Usage
- Input tokens: {response.usage.input_tokens}
- Output tokens: {response.usage.output_tokens}
""")

    print(f"\n✅ Task completed")
    print(f"   Log: {log_file}")

    return output_text


def main():
    worker_name = os.getenv("WORKER_NAME", "USABILITY-WORKER")

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Connect to task queue
    db_path = WORKSPACE / "tasks.db"
    task_queue = TaskQueue(db_path=str(db_path))

    print(f"🤖 {worker_name} started")
    print(f"   Database: {db_path}")
    print(f"   Polling for tasks...")
    print()

    tasks_completed = 0

    # Poll for tasks
    while True:
        # Claim a task
        task = task_queue.claim_task(agent_id=worker_name)

        if task:
            try:
                # Execute with LLM
                result = execute_task_with_llm(task, client, worker_name)

                # Mark complete
                task_queue.complete_task(task.id, result=result)
                tasks_completed += 1

                print(f"\n📊 Progress: {tasks_completed} task(s) completed\n")

            except Exception as e:
                print(f"\n❌ Task failed: {e}")
                task_queue.fail_task(task.id)
        else:
            # No tasks available
            print(".", end="", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
