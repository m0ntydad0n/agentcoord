"""
Coordinator Agent - Orchestrates multiple worker agents.

This demonstrates the "orchestrator pattern" where one agent manages
a group of workers through the coordination system.
"""

import time
from datetime import datetime
from typing import List, Dict, Optional
from agentcoord import CoordinationClient
from agentcoord.agent import AgentRegistry
from agentcoord.tasks import TaskQueue, Task, TaskStatus
from agentcoord.board import Board, BoardThread
from agentcoord.approvals import ApprovalWorkflow
from agentcoord.audit import AuditLog


class CoordinatorAgent:
    """
    Orchestrator agent that manages worker agents.

    Responsibilities:
    - Create and prioritize tasks
    - Monitor worker health
    - Handle approval requests
    - Track progress and report status
    - Reassign work from failed agents
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", name: str = "Coordinator"):
        self.redis_url = redis_url
        self.name = name
        self.coord: Optional[CoordinationClient] = None
        self.running = False

    def start(self):
        """Start the coordinator session."""
        self.coord = CoordinationClient(redis_url=self.redis_url)
        self.coord.register_agent(
            role="Coordinator",
            name=self.name,
            working_on="Orchestrating worker agents"
        )
        self.running = True
        print(f"🎯 Coordinator '{self.name}' started in {self.coord.mode} mode")

    def stop(self):
        """Stop the coordinator session."""
        if self.coord:
            self.coord.shutdown()
        self.running = False
        print(f"🛑 Coordinator '{self.name}' stopped")

    def create_tasks(self, task_list: List[Dict]):
        """
        Create tasks from a list of task definitions.

        Args:
            task_list: List of dicts with 'title', 'description', 'priority', 'tags'
        """
        if self.coord.mode != "redis" or not self.coord.redis_client:
            print("⚠️  Task creation requires Redis connection")
            return

        task_queue = TaskQueue(self.coord.redis_client)

        for task_def in task_list:
            task = task_queue.create_task(
                title=task_def['title'],
                description=task_def.get('description', ''),
                priority=task_def.get('priority', 3),
                tags=task_def.get('tags', [])
            )
            print(f"📝 Created task: {task.title} (priority: {task.priority})")

        self.coord.log_decision(
            decision_type="task_creation",
            context=f"Created {len(task_list)} tasks",
            reason="Initial task distribution"
        )

    def monitor_workers(self, threshold_seconds: int = 300) -> Dict:
        """
        Monitor worker agent health.

        Args:
            threshold_seconds: Consider agent stale if no heartbeat in this time

        Returns:
            Dict with active and stale agent info
        """
        if self.coord.mode != "redis" or not self.coord.redis_client:
            return {'active': [], 'stale': []}

        registry = AgentRegistry(self.coord.redis_client)

        # Get all agents
        all_agents = registry.list_agents()

        # Filter out self
        workers = {
            agent_id: data
            for agent_id, data in all_agents.items()
            if agent_id != self.coord.agent_id
        }

        # Check for stale agents
        stale_agents = registry.get_stale_agents(threshold_seconds=threshold_seconds)

        active_count = len(workers) - len(stale_agents)

        print(f"\n👥 Worker Status:")
        print(f"   Active: {active_count}")
        print(f"   Stale: {len(stale_agents)}")

        if stale_agents:
            print(f"   ⚠️  Stale agents detected:")
            for agent_id, data in stale_agents.items():
                print(f"      - {data.get('name', agent_id)}: {data.get('working_on', 'N/A')}")

        return {
            'active': [
                {'id': aid, **data}
                for aid, data in workers.items()
                if aid not in stale_agents
            ],
            'stale': [
                {'id': aid, **data}
                for aid, data in stale_agents.items()
            ]
        }

    def check_task_progress(self) -> Dict:
        """Check progress of all tasks."""
        if self.coord.mode != "redis" or not self.coord.redis_client:
            return {}

        task_queue = TaskQueue(self.coord.redis_client)
        all_tasks = task_queue.list_pending_tasks()

        status_counts = {
            'pending': 0,
            'claimed': 0,
            'in_progress': 0,
            'completed': 0,
            'failed': 0
        }

        for task in all_tasks:
            status_counts[task.status.value] += 1

        total = len(all_tasks)
        completed = status_counts['completed']
        progress = (completed / total * 100) if total > 0 else 0

        print(f"\n📊 Task Progress:")
        print(f"   Total: {total} | Completed: {completed} ({progress:.1f}%)")
        print(f"   Pending: {status_counts['pending']}")
        print(f"   In Progress: {status_counts['in_progress']}")
        print(f"   Failed: {status_counts['failed']}")

        return status_counts

    def handle_approvals(self, auto_approve: bool = False):
        """
        Check and handle pending approval requests.

        Args:
            auto_approve: If True, automatically approve all requests
        """
        if self.coord.mode != "redis" or not self.coord.redis_client:
            return

        workflow = ApprovalWorkflow(self.coord.redis_client)
        pending = workflow.list_pending_approvals()

        if not pending:
            return

        print(f"\n✋ Pending Approvals: {len(pending)}")

        for approval in pending:
            print(f"\n   Request from: {approval.requested_by}")
            print(f"   Action: {approval.action_type}")
            print(f"   Description: {approval.description}")

            if auto_approve:
                workflow.approve(approval.id, self.coord.agent_id)
                print(f"   ✅ Auto-approved")

                self.coord.log_decision(
                    decision_type="approval",
                    context=f"Approved {approval.action_type}",
                    reason=f"Auto-approval for {approval.requested_by}"
                )
            else:
                print(f"   ⏳ Waiting for manual approval via CLI:")
                print(f"      agentcoord approve {approval.id}")

    def broadcast_message(self, title: str, message: str, priority: str = "normal"):
        """
        Broadcast a message to all workers via the board.

        Args:
            title: Message title
            message: Message content
            priority: "high", "normal", or "low"
        """
        thread = self.coord.post_thread(title, message, priority)

        if thread:
            print(f"\n📢 Broadcast: {title}")
            self.coord.log_decision(
                decision_type="broadcast",
                context=title,
                reason=message
            )

    def reassign_stale_tasks(self, stale_agents: List[Dict]):
        """
        Reassign tasks from stale/failed agents.

        Args:
            stale_agents: List of stale agent info dicts
        """
        if not stale_agents or self.coord.mode != "redis":
            return

        task_queue = TaskQueue(self.coord.redis_client)
        all_tasks = task_queue.list_pending_tasks()

        reassigned_count = 0

        for task in all_tasks:
            # Check if task is claimed by a stale agent
            if task.claimed_by in [a['id'] for a in stale_agents]:
                # Mark as pending again
                task_queue.update_task_status(task.id, TaskStatus.PENDING)
                task.claimed_by = None
                reassigned_count += 1

                print(f"♻️  Reassigned task: {task.title}")

        if reassigned_count > 0:
            self.coord.log_decision(
                decision_type="task_reassignment",
                context=f"Reassigned {reassigned_count} tasks",
                reason=f"Recovered from {len(stale_agents)} stale agents"
            )

    def run_orchestration_loop(
        self,
        interval: int = 30,
        max_iterations: Optional[int] = None,
        auto_approve: bool = False
    ):
        """
        Run the main orchestration loop.

        Args:
            interval: Seconds between monitoring cycles
            max_iterations: Stop after this many iterations (None = run forever)
            auto_approve: Auto-approve all approval requests
        """
        iteration = 0

        print(f"\n🔄 Starting orchestration loop (interval: {interval}s)")

        try:
            while self.running:
                iteration += 1
                print(f"\n{'='*60}")
                print(f"Cycle #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")

                # Monitor workers
                worker_status = self.monitor_workers()

                # Check task progress
                self.check_task_progress()

                # Handle approval requests
                self.handle_approvals(auto_approve=auto_approve)

                # Reassign tasks from failed agents
                if worker_status['stale']:
                    self.reassign_stale_tasks(worker_status['stale'])

                # Check if we should stop
                if max_iterations and iteration >= max_iterations:
                    print(f"\n✅ Completed {max_iterations} iterations")
                    break

                # Wait for next cycle
                if self.running:
                    print(f"\n⏳ Waiting {interval}s until next cycle...")
                    time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")

        finally:
            self.stop()


def example_usage():
    """Example: Coordinator managing a team of workers."""

    # Create coordinator
    coordinator = CoordinatorAgent(name="MainCoordinator")
    coordinator.start()

    # Create initial task list
    tasks = [
        {
            'title': 'Implement user authentication',
            'description': 'Add JWT-based auth to API',
            'priority': 5,
            'tags': ['backend', 'security']
        },
        {
            'title': 'Design landing page',
            'description': 'Create responsive landing page mockup',
            'priority': 4,
            'tags': ['frontend', 'design']
        },
        {
            'title': 'Write API documentation',
            'description': 'Document all REST endpoints',
            'priority': 3,
            'tags': ['documentation']
        },
        {
            'title': 'Set up CI/CD pipeline',
            'description': 'Configure GitHub Actions for testing and deployment',
            'priority': 5,
            'tags': ['devops', 'backend']
        },
        {
            'title': 'Implement data export feature',
            'description': 'Allow users to export their data as JSON',
            'priority': 3,
            'tags': ['backend', 'feature']
        }
    ]

    print("\n📋 Creating initial task list...")
    coordinator.create_tasks(tasks)

    # Broadcast to workers
    coordinator.broadcast_message(
        title="Project Kickoff",
        message="New project started. Tasks available in queue. Claim with tags: backend, frontend, devops, documentation",
        priority="high"
    )

    # Run orchestration loop
    print("\n" + "="*60)
    print("ORCHESTRATION MODE")
    print("="*60)
    print("\nCoordinator will now monitor and manage workers.")
    print("In another terminal, you can:")
    print("  - Start worker agents that claim tasks")
    print("  - Monitor with: agentcoord status")
    print("  - View tasks with: agentcoord tasks")
    print("\nPress Ctrl+C to stop\n")

    coordinator.run_orchestration_loop(
        interval=10,  # Check every 10 seconds
        max_iterations=6,  # Run for 6 cycles (1 minute)
        auto_approve=True  # Auto-approve requests for demo
    )


if __name__ == '__main__':
    example_usage()
