"""
Auto-Scaling Coordinator Agent.

Dynamically spawns and manages worker agents based on workload.
Demonstrates full lifecycle management and intelligent scaling.
"""

import time
import sys
import os
from typing import Optional

# Add examples directory to path
sys.path.insert(0, os.path.dirname(__file__))

from coordinator_agent import CoordinatorAgent
from agentcoord.spawner import WorkerSpawner, SpawnMode
from agentcoord.tasks import TaskQueue, TaskStatus


class AutoScalingCoordinator(CoordinatorAgent):
    """
    Coordinator with auto-scaling capabilities.

    Automatically spawns workers when queue is deep,
    terminates idle workers to conserve resources.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        name: str = "AutoScaleCoordinator",
        spawn_mode: SpawnMode = SpawnMode.SUBPROCESS,
        min_workers: int = 1,
        max_workers: int = 10,
        tasks_per_worker: int = 5
    ):
        super().__init__(redis_url=redis_url, name=name)
        self.spawner = WorkerSpawner(redis_url=redis_url)
        self.spawn_mode = spawn_mode
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.tasks_per_worker = tasks_per_worker

    def spawn_worker(
        self,
        name: Optional[str] = None,
        tags: Optional[list] = None,
        max_tasks: Optional[int] = None
    ):
        """
        Spawn a new worker agent.

        Args:
            name: Worker name (auto-generated if None)
            tags: Task tags to claim
            max_tasks: Max tasks before worker stops
        """
        worker = self.spawner.spawn_worker(
            name=name,
            tags=tags,
            mode=self.spawn_mode,
            max_tasks=max_tasks,
            poll_interval=3
        )

        print(f"🚀 Spawned worker: {worker.name} (tags: {worker.tags})")

        self.coord.log_decision(
            decision_type="worker_spawn",
            context=f"Spawned {worker.name}",
            reason="Auto-scaling based on queue depth"
        )

        return worker

    def scale_workers(self):
        """
        Auto-scale workers based on queue depth.

        Spawns workers if queue is deep, terminates idle workers.
        """
        if self.coord.mode != "redis" or not self.coord.redis_client:
            return

        task_queue = TaskQueue(self.coord.redis_client)
        all_tasks = task_queue.list_pending_tasks()

        # Count pending tasks
        pending_count = sum(
            1 for t in all_tasks
            if t.status in [TaskStatus.PENDING, TaskStatus.CLAIMED]
        )

        # Check worker count
        self.spawner.cleanup_dead_workers()
        current_workers = self.spawner.count_alive_workers()

        # Calculate desired workers
        desired_workers = min(
            max(
                self.min_workers,
                (pending_count + self.tasks_per_worker - 1) // self.tasks_per_worker
            ),
            self.max_workers
        )

        print(f"\n📊 Auto-Scaling Analysis:")
        print(f"   Pending tasks: {pending_count}")
        print(f"   Current workers: {current_workers}")
        print(f"   Desired workers: {desired_workers}")

        # Scale up if needed
        if desired_workers > current_workers:
            to_spawn = desired_workers - current_workers
            print(f"   ⬆️  Scaling UP: spawning {to_spawn} workers")

            for i in range(to_spawn):
                self.spawn_worker(name=f"AutoWorker-{int(time.time())}-{i}")

        # Scale down if needed (just report, don't kill)
        elif desired_workers < current_workers:
            to_remove = current_workers - desired_workers
            print(f"   ⬇️  Over-capacity: {to_remove} idle workers")
            print(f"       (Workers will naturally exit when queue empties)")

    def get_fleet_status(self):
        """Get status of spawned worker fleet."""
        stats = self.spawner.get_worker_stats()

        print(f"\n🚢 Worker Fleet Status:")
        print(f"   Total spawned: {stats['total_spawned']}")
        print(f"   Alive: {stats['alive']}")
        print(f"   Dead: {stats['dead']}")

        if stats['workers']:
            print(f"\n   Workers:")
            for w in stats['workers']:
                status = "✅" if w['alive'] else "❌"
                print(f"      {status} {w['name']} | tags: {w['tags']} | mode: {w['mode']}")

        return stats

    def run_autoscaling_loop(
        self,
        interval: int = 30,
        max_iterations: Optional[int] = None,
        auto_approve: bool = True
    ):
        """
        Run orchestration loop with auto-scaling.

        Args:
            interval: Seconds between cycles
            max_iterations: Stop after this many cycles
            auto_approve: Auto-approve approval requests
        """
        iteration = 0

        print(f"\n🤖 Starting auto-scaling coordinator")
        print(f"   Min workers: {self.min_workers}")
        print(f"   Max workers: {self.max_workers}")
        print(f"   Tasks per worker: {self.tasks_per_worker}")
        print(f"   Spawn mode: {self.spawn_mode.value}")

        try:
            while self.running:
                iteration += 1
                print(f"\n{'='*60}")
                print(f"Auto-Scale Cycle #{iteration}")
                print(f"{'='*60}")

                # Monitor workers
                self.monitor_workers()

                # Check task progress
                self.check_task_progress()

                # Auto-scale based on queue
                self.scale_workers()

                # Fleet status
                self.get_fleet_status()

                # Handle approvals
                self.handle_approvals(auto_approve=auto_approve)

                # Check stop condition
                if max_iterations and iteration >= max_iterations:
                    print(f"\n✅ Completed {max_iterations} iterations")
                    break

                # Wait for next cycle
                if self.running:
                    print(f"\n⏳ Next cycle in {interval}s...")
                    time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")

        finally:
            print(f"\n🛑 Shutting down...")
            self.spawner.terminate_all()
            self.stop()


def demo_autoscaling():
    """Demo: Auto-scaling coordinator with dynamic worker spawning."""

    coordinator = AutoScalingCoordinator(
        name="AutoScaleDemo",
        spawn_mode=SpawnMode.SUBPROCESS,
        min_workers=2,
        max_workers=5,
        tasks_per_worker=3
    )

    coordinator.start()

    # Create a bunch of tasks
    print("\n📋 Creating workload...")
    tasks = [
        {'title': f'Task {i}', 'description': f'Auto-generated task {i}', 'priority': 3, 'tags': ['auto']}
        for i in range(15)  # 15 tasks
    ]
    coordinator.create_tasks(tasks)

    # Broadcast
    coordinator.broadcast_message(
        title="Auto-Scaling Demo Started",
        message="Coordinator will spawn workers as needed",
        priority="high"
    )

    # Run with auto-scaling
    print("\n" + "="*60)
    print("AUTO-SCALING MODE")
    print("="*60)
    print("\nCoordinator will spawn workers as queue grows.")
    print("Workers will be spawned automatically based on:")
    print("  - Queue depth (pending tasks)")
    print("  - Min/max worker limits")
    print("  - Tasks per worker ratio")
    print("\nPress Ctrl+C to stop\n")

    coordinator.run_autoscaling_loop(
        interval=15,  # Check every 15 seconds
        max_iterations=8,  # Run for ~2 minutes
        auto_approve=True
    )


if __name__ == '__main__':
    demo_autoscaling()
