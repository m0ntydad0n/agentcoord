"""
Autonomous Coordinator - Self-Managing Agent System.

Demonstrates autonomous agent coordination with:
- Self-coordinating workers that claim and execute tasks
- Resilient operation with error handling
- Automatic worker spawning and management
- Full lifecycle management without human intervention

This example shows the core autonomous pattern that AgentCoord enables.
"""

import time
import sys
import os
import argparse
from typing import Optional, List
from datetime import datetime

# Add examples directory to path
sys.path.insert(0, os.path.dirname(__file__))

from agentcoord import CoordinationClient
from agentcoord.tasks import TaskQueue, TaskStatus, Task
from agentcoord.spawner import WorkerSpawner, SpawnMode


class AutonomousWorker:
    """
    Autonomous worker that claims and executes tasks independently.

    Features:
    - Self-directed task claiming
    - Simulated LLM work with configurable failure rate
    - Error handling and status reporting
    - Graceful shutdown
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        name: str = "AutonomousWorker",
        tags: Optional[List[str]] = None,
        max_tasks: Optional[int] = None,
        poll_interval: int = 5,
        failure_rate: float = 0.1
    ):
        self.coord = CoordinationClient(redis_url=redis_url)
        self.name = name
        self.tags = tags or []
        self.max_tasks = max_tasks
        self.poll_interval = poll_interval
        self.failure_rate = failure_rate
        self.running = True
        self.tasks_completed = 0

    def register(self):
        """Register this worker with the coordination system."""
        self.coord.register_agent(
            role="Worker",
            name=self.name,
            working_on="Autonomous task execution"
        )
        print(f"[{self.name}] Registered as {self.coord.agent_id}")

    def execute_task(self, task: Task) -> bool:
        """
        Execute a task (simulated work).

        Args:
            task: Task to execute

        Returns:
            True if successful, False if failed
        """
        print(f"[{self.name}] Executing: {task.title}")

        # Simulate LLM work
        import random
        work_time = random.uniform(1, 3)

        # Simulate potential failure
        if random.random() < self.failure_rate:
            print(f"[{self.name}] ❌ Task failed: {task.title}")
            return False

        time.sleep(work_time)
        print(f"[{self.name}] ✅ Task completed: {task.title}")
        return True

    def run(self):
        """Run the worker loop."""
        self.register()

        print(f"[{self.name}] Starting autonomous operation")
        print(f"[{self.name}] Tags: {self.tags}")
        print(f"[{self.name}] Max tasks: {self.max_tasks or 'unlimited'}")

        task_queue = TaskQueue(self.coord.redis_client)

        try:
            while self.running:
                # Check if we've hit max tasks
                if self.max_tasks and self.tasks_completed >= self.max_tasks:
                    print(f"[{self.name}] Reached max tasks ({self.max_tasks}), shutting down")
                    break

                # Claim a task
                task = self.coord.claim_task(tags=self.tags if self.tags else None)

                if not task:
                    print(f"[{self.name}] No tasks available, waiting {self.poll_interval}s...")
                    time.sleep(self.poll_interval)
                    continue

                # Mark as in progress
                task.status = TaskStatus.IN_PROGRESS
                task_queue.update_task(task)

                # Execute the task
                success = self.execute_task(task)

                # Update task status
                if success:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow().isoformat()
                    self.tasks_completed += 1
                else:
                    task.status = TaskStatus.FAILED
                    # In real system, would escalate here

                task_queue.update_task(task)

        except KeyboardInterrupt:
            print(f"[{self.name}] Interrupted by user")
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown the worker."""
        print(f"[{self.name}] Shutting down (completed {self.tasks_completed} tasks)")
        self.running = False
        self.coord.shutdown()


class AutonomousCoordinator:
    """
    Autonomous coordinator that spawns and manages workers.

    Features:
    - Dynamic worker spawning based on workload
    - Worker lifecycle management
    - Task creation and monitoring
    - Auto-scaling based on queue depth
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        name: str = "AutonomousCoordinator",
        max_workers: int = 3,
        spawn_mode: SpawnMode = SpawnMode.SUBPROCESS
    ):
        self.coord = CoordinationClient(redis_url=redis_url)
        self.name = name
        self.max_workers = max_workers
        self.spawner = WorkerSpawner(redis_url=redis_url)
        self.spawn_mode = spawn_mode
        self.running = True

    def register(self):
        """Register this coordinator."""
        self.coord.register_agent(
            role="Coordinator",
            name=self.name,
            working_on="Autonomous worker management"
        )
        print(f"[{self.name}] Registered as {self.coord.agent_id}")

    def create_sample_tasks(self, count: int = 10):
        """Create sample tasks for workers to process."""
        print(f"\n[{self.name}] Creating {count} sample tasks...")

        task_queue = TaskQueue(self.coord.redis_client)

        tasks_data = [
            {
                'title': f'Process Data Batch {i}',
                'description': f'Autonomous task {i}: Process incoming data batch',
                'priority': 3,
                'tags': ['autonomous', 'data-processing']
            }
            for i in range(1, count + 1)
        ]

        for task_data in tasks_data:
            task_queue.create_task(**task_data)

        print(f"[{self.name}] Created {count} tasks")

    def spawn_workers(self, count: int = 1, tags: Optional[List[str]] = None):
        """Spawn worker agents."""
        print(f"\n[{self.name}] Spawning {count} workers...")

        workers = []
        for i in range(count):
            worker_name = f"AutoWorker-{int(time.time())}-{i}"

            # Spawn worker using spawner
            worker_info = self.spawner.spawn_worker(
                name=worker_name,
                tags=tags or ['autonomous'],
                mode=self.spawn_mode,
                max_tasks=None,  # Run until queue is empty
                poll_interval=3
            )

            workers.append(worker_info)
            print(f"[{self.name}] ✓ Spawned {worker_name}")

        return workers

    def monitor_progress(self):
        """Monitor task queue and worker progress."""
        task_queue = TaskQueue(self.coord.redis_client)
        pending = task_queue.list_pending_tasks()

        print(f"\n[{self.name}] Progress Report:")
        print(f"  Pending tasks: {len(pending)}")

        # Get worker stats
        stats = self.spawner.get_worker_stats()
        print(f"  Active workers: {stats['alive']}/{stats['total_spawned']}")

        return len(pending), stats['alive']

    def run(self, task_count: int = 10, worker_count: int = 3, monitor_interval: int = 10):
        """
        Run autonomous coordination demo.

        Args:
            task_count: Number of tasks to create
            worker_count: Number of workers to spawn
            monitor_interval: Seconds between progress checks
        """
        self.register()

        print(f"\n{'='*70}")
        print(f"AUTONOMOUS COORDINATOR DEMO")
        print(f"{'='*70}")
        print(f"Tasks: {task_count}")
        print(f"Workers: {worker_count}")
        print(f"Spawn mode: {self.spawn_mode.value}")
        print(f"{'='*70}\n")

        try:
            # Create tasks
            self.create_sample_tasks(count=task_count)

            # Spawn workers
            self.spawn_workers(count=worker_count, tags=['autonomous'])

            # Monitor until complete
            print(f"\n[{self.name}] Monitoring autonomous operation...")
            print(f"[{self.name}] Press Ctrl+C to stop\n")

            while self.running:
                pending, alive = self.monitor_progress()

                # Check if work is complete
                if pending == 0 and alive == 0:
                    print(f"\n[{self.name}] ✅ All tasks completed, all workers finished!")
                    break

                # Wait before next check
                time.sleep(monitor_interval)

        except KeyboardInterrupt:
            print(f"\n[{self.name}] Interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown coordinator and all workers."""
        print(f"\n[{self.name}] Shutting down...")

        # Terminate all spawned workers
        print(f"[{self.name}] Terminating workers...")
        self.spawner.terminate_all()

        # Cleanup
        self.running = False
        self.coord.shutdown()

        print(f"[{self.name}] Shutdown complete")


def main():
    """Run autonomous coordinator demo."""
    parser = argparse.ArgumentParser(description='Autonomous Coordinator Demo')
    parser.add_argument('--tasks', type=int, default=10, help='Number of tasks to create')
    parser.add_argument('--workers', type=int, default=3, help='Number of workers to spawn')
    parser.add_argument('--mode', type=str, default='subprocess', choices=['subprocess', 'thread'],
                        help='Worker spawn mode')
    parser.add_argument('--interval', type=int, default=10, help='Monitor interval in seconds')

    args = parser.parse_args()

    # Convert mode string to enum
    spawn_mode = SpawnMode.SUBPROCESS if args.mode == 'subprocess' else SpawnMode.THREAD

    # Create and run coordinator
    coordinator = AutonomousCoordinator(
        name="AutonomousDemo",
        max_workers=args.workers,
        spawn_mode=spawn_mode
    )

    coordinator.run(
        task_count=args.tasks,
        worker_count=args.workers,
        monitor_interval=args.interval
    )


if __name__ == '__main__':
    main()
