#!/usr/bin/env python3
"""Simple worker that executes tasks using Claude API."""

import os
import sys
import time
from pathlib import Path
from anthropic import Anthropic, RateLimitError

# Add agentcoord to path
sys.path.insert(0, str(Path.home() / "agentcoord" / "agentcoord"))
from tasks import TaskQueue

JANUS_ROOT = Path.home() / "Desktop" / "Janus_Engine"

# Model configuration
MODEL = os.getenv("MODEL", "sonnet").lower()  # haiku or sonnet

MODEL_CONFIG = {
    "haiku": {
        "model_id": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "rate_limit_tokens_per_min": 50000,  # Much higher!
        "estimated_tokens_per_task": 2000,
        "cost_per_mtok_input": 0.80,
        "cost_per_mtok_output": 4.00,
    },
    "sonnet": {
        "model_id": "claude-sonnet-4-5-20250929",
        "max_tokens": 8000,
        "rate_limit_tokens_per_min": 8000,
        "estimated_tokens_per_task": 3000,
        "cost_per_mtok_input": 3.00,
        "cost_per_mtok_output": 15.00,
    }
}

config = MODEL_CONFIG.get(MODEL, MODEL_CONFIG["sonnet"])
DELAY_BETWEEN_TASKS = 60 * (config["estimated_tokens_per_task"] / config["rate_limit_tokens_per_min"])

def main():
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: Set ANTHROPIC_API_KEY first")
        print("   export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Use current directory for workspace (where coordinator launched us)
    workspace = Path.cwd()
    db_path = workspace / "tasks.db"
    if not db_path.exists():
        print(f"❌ No tasks database found at {db_path}")
        print("   Create a task first with: python3 ~/agentcoord/create_task.py")
        sys.exit(1)

    task_queue = TaskQueue(db_path=str(db_path))

    worker_name = os.getenv("WORKER_NAME", f"{MODEL}-worker")

    print(f"🤖 {MODEL.upper()} Worker started")
    print(f"   Model: {config['model_id']}")
    print(f"   Rate limit: {config['rate_limit_tokens_per_min']:,} tokens/min")
    print(f"   Delay between tasks: {DELAY_BETWEEN_TASKS:.1f}s")
    print(f"   Database: {db_path}")
    print("   Polling for tasks...\n")

    while True:
        # Claim a task
        task = task_queue.claim_task(agent_id=worker_name)

        if task:
            print(f"\n▶️  [{MODEL.upper()}] EXECUTING: {task.title}")
            print(f"   {task.description}\n")

            # Build prompt
            prompt = f"""You are a research analyst.

TASK: {task.title}

DESCRIPTION:
{task.description}

INSTRUCTIONS:
- Be thorough and specific
- Cite sources and data where possible
- Focus on actionable insights

Execute this research task now.
"""

            try:
                # Call Claude with configured model
                response = client.messages.create(
                    model=config["model_id"],
                    max_tokens=config["max_tokens"],
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract result
                result = ""
                for block in response.content:
                    if block.type == "text":
                        result += block.text

                # Save log with model info
                log_file = workspace / f"task_{task.id[:8]}.log"
                log_content = f"""# {task.title}
Model: {config['model_id']}
Worker: {worker_name}
Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out

---

{result}
"""
                log_file.write_text(log_content)

                # Mark complete
                task_queue.complete_task(task.id, result=result)

                print(f"✅ Task completed!")
                print(f"   Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
                print(f"   Log: {log_file}\n")

                # Rate limit delay
                if DELAY_BETWEEN_TASKS > 0:
                    print(f"⏱️  Waiting {DELAY_BETWEEN_TASKS:.1f}s (rate limit)...")
                    time.sleep(DELAY_BETWEEN_TASKS)

            except RateLimitError as e:
                print(f"⚠️  Rate limit hit! Releasing task and waiting 60s...")
                # Release task back to queue
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE tasks SET status='pending', agent_id=NULL WHERE id=?", (task.id,))
                conn.commit()
                conn.close()
                time.sleep(60)

            except Exception as e:
                print(f"❌ Task failed: {e}")
                task_queue.fail_task(task.id)
                time.sleep(5)
        else:
            print(".", end="", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    main()
