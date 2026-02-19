"""
Worker Agent - Autonomous agent that claims and executes tasks.

This demonstrates a worker in the orchestrator pattern that:
- Claims tasks from the queue
- Executes work
- Reports completion
- Handles failures gracefully
"""

import time
import random
from typing import Optional, List
from agentcoord import CoordinationClient
from agentcoord.tasks import TaskQueue, TaskStatus


class WorkerAgent:
    """
    Autonomous worker agent that claims and executes tasks.

    The worker continuously polls for tasks, claims them, executes them,
    and reports completion.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        name: str = "Worker",
        tags: Optional[List[str]] = None
    ):
        self.redis_url = redis_url
        self.name = name
        self.tags = tags or []
        self.coord: Optional[CoordinationClient] = None
        self.running = False
        self.tasks_completed = 0
        self.tasks_failed = 0

    def start(self):
        """Start the worker session."""
        self.coord = CoordinationClient(redis_url=self.redis_url)
        self.coord.register_agent(
            role="Worker",
            name=self.name,
            working_on="Ready for tasks"
        )
        self.running = True
        print(f"🤖 Worker '{self.name}' started in {self.coord.mode} mode")
        if self.tags:
            print(f"   Claiming tasks with tags: {self.tags}")

    def stop(self):
        """Stop the worker session."""
        if self.coord:
            self.coord.shutdown()
        self.running = False
        print(f"\n📊 Worker '{self.name}' stopped")
        print(f"   Tasks completed: {self.tasks_completed}")
        print(f"   Tasks failed: {self.tasks_failed}")

    def execute_task(self, task) -> bool:
        """
        Execute a task (simulated work).

        Args:
            task: Task object to execute

        Returns:
            True if successful, False if failed
        """
        print(f"\n▶️  Executing: {task.title}")
        print(f"   Description: {task.description}")
        print(f"   Priority: {task.priority}")

        # Update agent status
        if self.coord.mode == "redis" and self.coord.redis_client:
            from agentcoord.agent import AgentRegistry
            registry = AgentRegistry(self.coord.redis_client)
            registry.update_agent_status(
                self.coord.agent_id,
                working_on=task.title
            )

        try:
            # Simulate work (random duration 2-5 seconds)
            duration = random.uniform(2, 5)
            print(f"   ⏳ Working... (estimated {duration:.1f}s)")

            # Simulate occasional failures (10% chance)
            if random.random() < 0.1:
                time.sleep(1)
                raise Exception("Simulated failure")

            time.sleep(duration)

            print(f"   ✅ Completed: {task.title}")

            # Log decision
            self.coord.log_decision(
                decision_type="task_completion",
                context=task.title,
                reason=f"Successfully completed by {self.name}"
            )

            return True

        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")

            # Log failure
            self.coord.log_decision(
                decision_type="task_failure",
                context=task.title,
                reason=f"Failed with error: {str(e)}"
            )

            return False

    def run_worker_loop(self, max_tasks: Optional[int] = None, poll_interval: int = 5):
        """
        Run the main worker loop.

        Args:
            max_tasks: Stop after completing this many tasks (None = run forever)
            poll_interval: Seconds to wait between task checks
        """
        print(f"\n🔄 Starting worker loop (poll interval: {poll_interval}s)")

        try:
            while self.running:
                # Try to claim a task
                task = self.coord.claim_task(tags=self.tags if self.tags else None)

                if task:
                    # Update task status to in_progress
                    if self.coord.mode == "redis" and self.coord.redis_client:
                        task_queue = TaskQueue(self.coord.redis_client)
                        task.status = TaskStatus.IN_PROGRESS
                        task_queue.update_task(task)

                    # Execute the task
                    success = self.execute_task(task)

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


def example_single_worker():
    """Example: Single worker claiming tasks."""
    worker = WorkerAgent(
        name=f"Worker-{random.randint(1000, 9999)}",
        tags=["backend"]  # Only claim backend tasks
    )

    worker.start()
    worker.run_worker_loop(max_tasks=3, poll_interval=3)


def example_multi_worker():
    """Example: Launch multiple workers with different specializations."""
    import threading

    workers = [
        WorkerAgent(name="Backend-Worker-1", tags=["backend"]),
        WorkerAgent(name="Backend-Worker-2", tags=["backend"]),
        WorkerAgent(name="Frontend-Worker", tags=["frontend"]),
        WorkerAgent(name="DevOps-Worker", tags=["devops"]),
        WorkerAgent(name="Generalist-Worker", tags=[]),  # Claims any task
    ]

    threads = []

    print("🚀 Launching worker fleet...\n")

    for worker in workers:
        worker.start()

        # Run each worker in a thread
        thread = threading.Thread(
            target=worker.run_worker_loop,
            kwargs={'max_tasks': 2, 'poll_interval': 3}
        )
        thread.start()
        threads.append(thread)

        time.sleep(0.5)  # Stagger starts

    # Wait for all workers to complete
    for thread in threads:
        thread.join()

    print("\n✅ All workers completed")


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='AgentCoord Worker Agent')
    parser.add_argument('--name', type=str, help='Worker name')
    parser.add_argument('--tags', type=str, help='Comma-separated tags (e.g., backend,frontend)')
    parser.add_argument('--redis-url', type=str, default='redis://localhost:6379', help='Redis URL')
    parser.add_argument('--max-tasks', type=int, help='Max tasks before stopping')
    parser.add_argument('--poll-interval', type=int, default=5, help='Seconds between task checks')
    parser.add_argument('--multi', action='store_true', help='Run multi-worker example')

    args = parser.parse_args()

    if args.multi:
        example_multi_worker()
    elif args.name:
        # CLI mode - spawn single worker with specific config
        tags = args.tags.split(',') if args.tags else []
        worker = WorkerAgent(
            redis_url=args.redis_url,
            name=args.name,
            tags=tags
        )
        worker.start()
        worker.run_worker_loop(
            max_tasks=args.max_tasks,
            poll_interval=args.poll_interval
        )
    else:
        example_single_worker()
