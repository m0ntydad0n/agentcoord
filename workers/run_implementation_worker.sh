#!/bin/bash
# Implementation worker - claims tasks and executes code changes

WORKER_NAME="${1:-IMPL-WORKER-$$}"
WORKSPACE="${2:-$HOME/agentcoord/workspace/usability-improvements}"

echo "Starting implementation worker: $WORKER_NAME"
echo "Workspace: $WORKSPACE"

mkdir -p "$WORKSPACE/implementations"
mkdir -p "$WORKSPACE/logs"

# Run the implementation worker
python3 - <<'PYTHON_SCRIPT'
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic

# Add agentcoord to path
sys.path.insert(0, str(Path.home() / "agentcoord"))
from agentcoord import TaskQueue, AgentRegistry

WORKER_NAME = os.environ.get("WORKER_NAME", "IMPL-WORKER")
WORKSPACE = Path(os.environ.get("WORKSPACE", Path.home() / "agentcoord/workspace/usability-improvements"))
JANUS_ROOT = Path.home() / "Desktop" / "Janus_Engine"

def execute_implementation(task: dict) -> dict:
    """Execute implementation task using Claude API."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    task_id = task["id"]
    title = task["title"]
    description = task["description"]

    print(f"\n{'='*70}")
    print(f"  EXECUTING: {title}")
    print(f"{'='*70}\n")

    # Build implementation prompt
    prompt = f"""You are an implementation specialist working on the Janus Engine.

TASK: {title}

REQUIREMENTS:
{description}

INSTRUCTIONS:
1. Read relevant files to understand current implementation
2. Make minimal necessary changes to implement the feature
3. Run full test suite: python3 -m pytest tests/ -v
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

    messages = [{"role": "user", "content": prompt}]

    # Call Claude API with extended thinking
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=messages,
        thinking={
            "type": "enabled",
            "budget_tokens": 5000
        }
    )

    # Extract response
    output_text = ""
    for block in response.content:
        if block.type == "text":
            output_text += block.text + "\n"

    # Save implementation log
    log_file = WORKSPACE / "implementations" / f"{task_id}.md"
    log_file.write_text(f"""# {title}

**Task ID:** {task_id}
**Worker:** {WORKER_NAME}
**Timestamp:** {datetime.now().isoformat()}

## Task Description
{description}

## Implementation Output
{output_text}

## API Usage
- Model: {response.model}
- Input tokens: {response.usage.input_tokens}
- Output tokens: {response.usage.output_tokens}
""")

    return {
        "task_id": task_id,
        "status": "completed",
        "output": output_text,
        "log_file": str(log_file),
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
    }

def main():
    task_queue = TaskQueue()
    registry = AgentRegistry()

    # Register worker
    registry.register_agent(
        agent_id=WORKER_NAME,
        agent_type="implementation_worker",
        capabilities=["code_implementation", "testing", "git_commits"],
    )

    print(f"Worker {WORKER_NAME} registered and ready")
    print("Polling for tasks...")

    while True:
        # Try to claim a task
        task = task_queue.claim_task(WORKER_NAME, tags=["usability", "implementation"])

        if task:
            try:
                result = execute_implementation(task)

                # Mark complete
                task_queue.complete_task(
                    task["id"],
                    result=result["output"],
                    metadata={"log_file": result["log_file"], "usage": result["usage"]},
                )

                print(f"\n✅ Task completed: {task['title']}")
                print(f"   Log: {result['log_file']}")

            except Exception as e:
                print(f"\n❌ Task failed: {e}")
                task_queue.fail_task(task["id"], error=str(e))
        else:
            # No tasks available, wait
            time.sleep(5)

if __name__ == "__main__":
    main()
PYTHON_SCRIPT
