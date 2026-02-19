"""
LLM-Powered Worker Agent - Actually writes code using Anthropic API.

This worker claims tasks from Redis and uses Claude to generate actual code.
"""

import time
import os
import sys
from typing import Optional, List
from agentcoord import CoordinationClient
from agentcoord.tasks import TaskQueue, TaskStatus

# Check for Anthropic API key (NEVER log the actual key value)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    print("❌ Error: ANTHROPIC_API_KEY not set")
    print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
    print("   See SECURITY.md for best practices")
    sys.exit(1)

# Validate key format but don't log it
if not ANTHROPIC_API_KEY.startswith("sk-ant-"):
    print("⚠️  Warning: API key doesn't match expected format (should start with 'sk-ant-')")
    print("   Proceeding anyway, but verify your key is correct")


class LLMWorkerAgent:
    """
    LLM-powered worker that actually writes code.

    Uses Claude API to generate code based on task descriptions.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        name: str = "LLMWorker",
        tags: Optional[List[str]] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        self.redis_url = redis_url
        self.name = name
        self.tags = tags or []
        self.model = model
        self.coord: Optional[CoordinationClient] = None
        self.running = False
        self.tasks_completed = 0
        self.tasks_failed = 0

        # Import Anthropic SDK
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        except ImportError:
            print("❌ Error: anthropic package not installed")
            print("   Install with: pip3 install anthropic")
            sys.exit(1)

    def start(self):
        """Start the worker session."""
        self.coord = CoordinationClient(redis_url=self.redis_url)
        self.coord.register_agent(
            role="LLMWorker",
            name=self.name,
            working_on="Ready for tasks"
        )
        self.running = True
        print(f"🤖 LLM Worker '{self.name}' started")
        print(f"   Model: {self.model}")
        if self.tags:
            print(f"   Tags: {self.tags}")

    def stop(self):
        """Stop the worker session."""
        if self.coord:
            self.coord.shutdown()
        self.running = False
        print(f"\n📊 LLM Worker '{self.name}' stopped")
        print(f"   Tasks completed: {self.tasks_completed}")
        print(f"   Tasks failed: {self.tasks_failed}")

    def execute_task_with_llm(self, task) -> bool:
        """
        Execute task using Claude to generate code.

        Args:
            task: Task object from queue

        Returns:
            True if successful, False if failed
        """
        print(f"\n▶️  Executing with LLM: {task.title}")
        print(f"   Description: {task.description}")

        # Update agent status
        if self.coord.mode == "redis" and self.coord.redis_client:
            from agentcoord.agent import AgentRegistry
            registry = AgentRegistry(self.coord.redis_client)
            registry.update_agent_status(
                self.coord.agent_id,
                working_on=task.title
            )

        try:
            # Prepare prompt for Claude
            prompt = f"""You are a coding agent working on this task:

TASK: {task.title}

DESCRIPTION:
{task.description}

TAGS: {', '.join(task.tags) if task.tags else 'none'}

Your job is to write the actual code to implement this task.

Provide:
1. The file path(s) to create/modify
2. The complete code for each file
3. Any necessary imports or dependencies

Be concise but complete. Write production-ready code.

Format your response as:
FILE: path/to/file.py
```python
code here
```

FILE: path/to/other.py
```python
more code
```
"""

            print(f"   🧠 Calling Claude API ({self.model})...")

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract response (NEVER log the full response - may contain sensitive data)
            code_response = response.content[0].text

            # Only log token counts, not content
            print(f"   ✅ LLM Response received ({response.usage.input_tokens} in, {response.usage.output_tokens} out)")

            # Parse and write files
            self._parse_and_write_files(code_response, task)

            print(f"   ✅ Task completed: {task.title}")

            # Log decision
            self.coord.log_decision(
                decision_type="llm_task_completion",
                context=task.title,
                reason=f"Completed using {self.model}"
            )

            return True

        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")

            # Log failure
            self.coord.log_decision(
                decision_type="llm_task_failure",
                context=task.title,
                reason=f"Error: {str(e)}"
            )

            return False

    def _parse_and_write_files(self, llm_response: str, task):
        """Parse LLM response and write files."""
        lines = llm_response.split('\n')
        current_file = None
        current_code = []
        in_code_block = False

        for line in lines:
            if line.startswith('FILE:'):
                # Save previous file
                if current_file and current_code:
                    self._write_file(current_file, '\n'.join(current_code))

                # Start new file
                current_file = line.replace('FILE:', '').strip()
                current_code = []
                in_code_block = False

            elif line.startswith('```'):
                if in_code_block:
                    # End of code block
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True

            elif in_code_block:
                current_code.append(line)

        # Write last file
        if current_file and current_code:
            self._write_file(current_file, '\n'.join(current_code))

    def _write_file(self, filepath: str, content: str):
        """Write file to disk."""
        # Make paths absolute if needed
        if not filepath.startswith('/'):
            filepath = os.path.join('/Users/johnmonty/agentcoord', filepath)

        # Create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Write file
        with open(filepath, 'w') as f:
            f.write(content)

        print(f"   📝 Wrote: {filepath}")

    def run_worker_loop(self, max_tasks: Optional[int] = None, poll_interval: int = 5):
        """
        Run the main worker loop.

        Args:
            max_tasks: Stop after completing this many tasks
            poll_interval: Seconds between task checks
        """
        print(f"\n🔄 Starting LLM worker loop")

        try:
            while self.running:
                # Claim a task
                task = self.coord.claim_task(tags=self.tags if self.tags else None)

                if task:
                    # Update status
                    if self.coord.mode == "redis" and self.coord.redis_client:
                        task_queue = TaskQueue(self.coord.redis_client)
                        task.status = TaskStatus.IN_PROGRESS
                        task_queue.update_task(task)

                    # Execute with LLM
                    success = self.execute_task_with_llm(task)

                    # Update task status
                    if self.coord.mode == "redis" and self.coord.redis_client:
                        if success:
                            task.status = TaskStatus.COMPLETED
                            from datetime import datetime, timezone
                            task.completed_at = datetime.now(timezone.utc).isoformat()
                            task_queue.update_task(task)
                            self.tasks_completed += 1
                        else:
                            task.status = TaskStatus.FAILED
                            task_queue.update_task(task)
                            self.tasks_failed += 1

                    # Check if we should stop
                    if max_tasks and self.tasks_completed >= max_tasks:
                        print(f"\n✅ Completed {max_tasks} tasks")
                        break

                else:
                    # No tasks available
                    print(f"⏳ No tasks available, waiting {poll_interval}s...")
                    time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")

        finally:
            self.stop()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='LLM-Powered Worker Agent')
    parser.add_argument('--name', type=str, default='LLMWorker', help='Worker name')
    parser.add_argument('--tags', type=str, help='Comma-separated tags')
    parser.add_argument('--redis-url', type=str, default='redis://localhost:6379')
    parser.add_argument('--max-tasks', type=int, help='Max tasks before stopping')
    parser.add_argument('--poll-interval', type=int, default=5)
    parser.add_argument('--model', type=str, default='claude-sonnet-4-20250514',
                        help='Claude model to use')

    args = parser.parse_args()

    tags = args.tags.split(',') if args.tags else []

    worker = LLMWorkerAgent(
        redis_url=args.redis_url,
        name=args.name,
        tags=tags,
        model=args.model
    )

    worker.start()
    worker.run_worker_loop(
        max_tasks=args.max_tasks,
        poll_interval=args.poll_interval
    )
