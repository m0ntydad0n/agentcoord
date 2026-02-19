"""
Interactive Planning CLI for AgentCoord.

User-facing interface for planning and executing multi-agent workflows
with cost/quality optimization preferences.
"""

import click
import sys
from typing import Optional, List, Dict
from .client import CoordinationClient
from .tasks import TaskQueue
from .planner import TaskPlanner, OptimizationMode, format_plan_summary, ExecutionPlan
from .spawner import WorkerSpawner, SpawnMode


@click.group()
def interactive():
    """Interactive planning and execution for AgentCoord."""
    pass


@interactive.command()
@click.option('--redis-url', envvar='REDIS_URL', default='redis://localhost:6379',
              help='Redis connection URL')
@click.option('--auto-execute', is_flag=True, help='Auto-execute plan without confirmation')
def plan(redis_url: str, auto_execute: bool):
    """
    Interactive planning workflow.

    Analyzes pending tasks, estimates costs, and generates execution plan
    with user preferences.
    """
    click.echo("\n🤖 AgentCoord Interactive Planning\n")

    # Connect to Redis
    try:
        import redis
        redis_client = redis.from_url(redis_url, socket_connect_timeout=1, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        click.echo(f"❌ Cannot connect to Redis at {redis_url}", err=True)
        click.echo(f"   Error: {e}", err=True)
        click.echo(f"\n   Start Redis with: brew services start redis", err=True)
        sys.exit(1)

    # Get pending tasks
    task_queue = TaskQueue(redis_client)
    pending_tasks = task_queue.list_pending_tasks()

    if not pending_tasks:
        click.echo("📭 No pending tasks in queue")
        click.echo("\n   Create tasks first using:")
        click.echo("   python -m agentcoord.cli tasks")
        sys.exit(0)

    click.echo(f"📋 Found {len(pending_tasks)} pending tasks\n")

    # Show task list
    click.echo("Tasks:")
    for i, task in enumerate(pending_tasks, 1):
        click.echo(f"  {i}. {task.title} (priority: {task.priority})")

    click.echo()

    # Ask for optimization preference
    if not auto_execute:
        click.echo("How should I optimize this workflow?\n")
        click.echo("  1. Cost - Minimize cost, use smaller/faster models")
        click.echo("  2. Balanced - Balance cost and quality (recommended)")
        click.echo("  3. Quality - Maximize quality, use best models\n")

        mode_choice = click.prompt("Choose optimization mode", type=click.Choice(['1', '2', '3']), default='2')

        mode_map = {
            '1': OptimizationMode.COST,
            '2': OptimizationMode.BALANCED,
            '3': OptimizationMode.QUALITY
        }
        optimization_mode = mode_map[mode_choice]
    else:
        optimization_mode = OptimizationMode.BALANCED

    # Ask for budget limit
    budget_limit = None
    if not auto_execute:
        has_budget = click.confirm("\nDo you want to set a budget limit?", default=False)
        if has_budget:
            budget_limit = click.prompt("Enter budget limit in dollars", type=float)

    # Create plan
    click.echo(f"\n🧠 Analyzing tasks and creating execution plan...\n")

    planner = TaskPlanner()
    tasks_dict = [
        {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'depends_on': task.depends_on or [],
            'tags': task.tags or []
        }
        for task in pending_tasks
    ]

    plan = planner.create_execution_plan(
        tasks=tasks_dict,
        optimization_mode=optimization_mode,
        budget_limit=budget_limit,
        max_agents=10
    )

    # Show plan
    plan_summary = format_plan_summary(plan)
    click.echo(plan_summary)

    # Budget check
    if not plan.within_budget:
        click.echo("⚠️  WARNING: Plan exceeds budget limit!")
        click.echo(f"   Estimated: ${plan.total_estimated_cost:.2f}")
        click.echo(f"   Budget: ${plan.budget_limit:.2f}")
        click.echo(f"   Overage: ${plan.total_estimated_cost - plan.budget_limit:.2f}\n")

        if not auto_execute:
            continue_anyway = click.confirm("Continue anyway?", default=False)
            if not continue_anyway:
                click.echo("\n❌ Aborted by user")
                sys.exit(0)

    # Confirm execution
    if not auto_execute:
        click.echo()
        execute = click.confirm(
            f"Execute this plan? (Will spawn {plan.recommended_agents} agents)",
            default=True
        )

        if not execute:
            click.echo("\n✅ Plan saved but not executed")
            # TODO: Save plan to file
            sys.exit(0)

    # Execute plan
    click.echo(f"\n🚀 Executing plan with {plan.recommended_agents} agents...\n")

    spawner = WorkerSpawner(redis_url=redis_url)

    # Spawn workers
    for i in range(plan.recommended_agents):
        worker = spawner.spawn_worker(
            name=f"PlanWorker-{i+1}",
            tags=None,  # Claim any task
            mode=SpawnMode.SUBPROCESS,
            max_tasks=None,  # Work until queue empty
            poll_interval=3
        )
        click.echo(f"  ✅ Spawned {worker.name}")

    click.echo(f"\n✅ Spawned {plan.recommended_agents} workers")
    click.echo(f"\n📊 Monitor progress:")
    click.echo(f"   python -m agentcoord.cli status   # View agent status")
    click.echo(f"   python -m agentcoord.cli tasks    # View task queue")
    click.echo(f"   python -m agentcoord.cli budget   # View cost tracking\n")

    click.echo("Workers will run in background until queue is empty.")
    click.echo("Use Ctrl+C to stop this session (workers continue running).\n")


@interactive.command()
@click.option('--redis-url', envvar='REDIS_URL', default='redis://localhost:6379',
              help='Redis connection URL')
@click.option('--title', prompt='Task title', help='Short task title')
@click.option('--description', prompt='Task description', help='Detailed task description')
@click.option('--priority', type=int, default=3, help='Priority 1-5 (5 highest)')
@click.option('--tags', help='Comma-separated tags')
def create_task(redis_url: str, title: str, description: str, priority: int, tags: Optional[str]):
    """Create a new task interactively."""
    try:
        import redis
        redis_client = redis.from_url(redis_url, socket_connect_timeout=1, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        click.echo(f"❌ Cannot connect to Redis at {redis_url}", err=True)
        sys.exit(1)

    tag_list = [t.strip() for t in tags.split(',')] if tags else []

    task_queue = TaskQueue(redis_client)
    task = task_queue.create_task(
        title=title,
        description=description,
        priority=priority,
        tags=tag_list
    )

    click.echo(f"\n✅ Created task: {task.id}")
    click.echo(f"   Title: {task.title}")
    click.echo(f"   Priority: {task.priority}")
    if tag_list:
        click.echo(f"   Tags: {', '.join(tag_list)}")


@interactive.command()
@click.option('--redis-url', envvar='REDIS_URL', default='redis://localhost:6379',
              help='Redis connection URL')
def estimate(redis_url: str):
    """Estimate costs for pending tasks without executing."""
    click.echo("\n💰 Cost Estimation for Pending Tasks\n")

    # Connect to Redis
    try:
        import redis
        redis_client = redis.from_url(redis_url, socket_connect_timeout=1, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        click.echo(f"❌ Cannot connect to Redis at {redis_url}", err=True)
        sys.exit(1)

    # Get pending tasks
    task_queue = TaskQueue(redis_client)
    pending_tasks = task_queue.list_pending_tasks()

    if not pending_tasks:
        click.echo("📭 No pending tasks in queue")
        sys.exit(0)

    click.echo(f"📋 Analyzing {len(pending_tasks)} tasks...\n")

    planner = TaskPlanner()
    tasks_dict = [
        {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'depends_on': task.depends_on or [],
            'tags': task.tags or []
        }
        for task in pending_tasks
    ]

    # Generate estimates for all modes
    modes = [OptimizationMode.COST, OptimizationMode.BALANCED, OptimizationMode.QUALITY]

    click.echo(f"{'Mode':<12} {'Cost':<12} {'Time':<12} {'Agents':<8}")
    click.echo("=" * 50)

    for mode in modes:
        plan = planner.create_execution_plan(
            tasks=tasks_dict,
            optimization_mode=mode,
            max_agents=10
        )

        click.echo(
            f"{mode.value:<12} "
            f"${plan.total_estimated_cost:<11.2f} "
            f"~{plan.total_estimated_duration_minutes} min{'':<6} "
            f"{plan.recommended_agents}"
        )

    click.echo()
    click.echo("💡 Run 'agentcoord-plan plan' to execute with your preferred mode")


if __name__ == '__main__':
    interactive()
