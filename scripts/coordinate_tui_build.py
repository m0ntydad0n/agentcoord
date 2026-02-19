#!/usr/bin/env python3
"""
Master Coordinator for building the interactive TUI.

This coordinator uses AgentCoord's own planning and coordination
infrastructure to orchestrate the TUI build - ultimate dogfooding!
"""

import os
import sys
import time
import redis
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box

# Setup
console = Console()

# Ensure API key
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    janus_env = os.path.expanduser('~/Desktop/Janus_Engine/.env')
    if os.path.exists(janus_env):
        with open(janus_env) as f:
            for line in f:
                if line.startswith('ANTHROPIC_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    os.environ['ANTHROPIC_API_KEY'] = api_key
                    break

if not api_key:
    console.print("[red]❌ ANTHROPIC_API_KEY not found[/red]")
    console.print("[yellow]Set it in environment or ~/Desktop/Janus_Engine/.env[/yellow]")
    sys.exit(1)

# Connect to Redis
try:
    redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
    redis_client.ping()
except Exception as e:
    console.print(f"[red]❌ Cannot connect to Redis: {e}[/red]")
    console.print("[yellow]Start Redis with: brew services start redis[/yellow]")
    sys.exit(1)

# Import agentcoord modules
from agentcoord.tasks import TaskQueue
from agentcoord.planner import TaskPlanner, OptimizationMode
from agentcoord.spawner import WorkerSpawner, SpawnMode
from agentcoord.agent import AgentRegistry

# Show coordinator header
console.clear()
console.print(Panel.fit(
    "[bold cyan]🤖 AGENTCOORD MASTER COORDINATOR[/bold cyan]\n"
    "[dim]Building Interactive TUI via Self-Coordination[/dim]",
    border_style="cyan",
    padding=(1, 2)
))

console.print("\n[bold]Phase 1: Task Analysis[/bold]")
console.print("=" * 60)

# Get pending tasks
task_queue = TaskQueue(redis_client)
pending_tasks = task_queue.list_pending_tasks()

console.print(f"\n📋 Found [cyan]{len(pending_tasks)}[/cyan] pending tasks")

# Show task breakdown
task_table = Table(title="Task Queue", box=box.ROUNDED, show_header=True)
task_table.add_column("Priority", style="magenta", width=8)
task_table.add_column("Title", style="cyan")
task_table.add_column("Tags", style="dim")

for task in sorted(pending_tasks, key=lambda t: t.priority, reverse=True)[:10]:
    tags_str = ", ".join(task.tags[:3]) if task.tags else ""
    task_table.add_row(
        str(task.priority),
        task.title[:60] + "..." if len(task.title) > 60 else task.title,
        tags_str
    )

console.print(task_table)

# Planning phase
console.print("\n[bold]Phase 2: Execution Planning[/bold]")
console.print("=" * 60)

planner = TaskPlanner()

# Convert tasks for planner
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

# Create execution plan with balanced optimization
console.print("\n🧠 Analyzing tasks and creating execution plan...")
plan = planner.create_execution_plan(
    tasks=tasks_dict,
    optimization_mode=OptimizationMode.BALANCED,
    budget_limit=10.0,  # $10 budget limit
    max_agents=4
)

# Show plan summary
console.print(f"\n[bold green]✓[/bold green] Plan created")
console.print(f"  • Recommended workers: [cyan]{plan.recommended_agents}[/cyan]")
console.print(f"  • Estimated cost: [yellow]${plan.total_estimated_cost:.2f}[/yellow]")
console.print(f"  • Estimated duration: [blue]~{plan.total_estimated_duration_minutes} min[/blue]")
console.print(f"  • Within budget: [{'green' if plan.within_budget else 'red'}]{'✓' if plan.within_budget else '✗'}[/]")

# Model distribution
console.print("\n📊 Model Distribution:")
for model, count in plan.model_distribution.items():
    console.print(f"  • {model}: {count} tasks")

# Confirm execution
console.print("\n[bold]Phase 3: Worker Deployment[/bold]")
console.print("=" * 60)

console.print(f"\n[bold cyan]Ready to deploy {plan.recommended_agents} LLM workers[/bold cyan]")
console.print(f"Estimated cost: [yellow]${plan.total_estimated_cost:.2f}[/yellow]")
console.print(f"Estimated time: [blue]~{plan.total_estimated_duration_minutes} minutes[/blue]")

# Auto-confirm for now (coordinator autonomy)
console.print("\n[dim]Auto-confirming (coordinator autonomy)...[/dim]")
time.sleep(1)

# Spawn workers
console.print(f"\n🚀 Spawning {plan.recommended_agents} LLM workers...")

spawner = WorkerSpawner(redis_url='redis://localhost:6379')
workers = []

for i in range(plan.recommended_agents):
    worker = spawner.spawn_worker(
        name=f"TUI-Builder-{i+1}",
        tags=['tui', 'ux', 'interaction', 'keyboard', 'forms', 'modal', 'commands'],
        mode=SpawnMode.SUBPROCESS,
        max_tasks=3,
        poll_interval=5,
        use_llm=True
    )
    workers.append(worker)
    console.print(f"  [green]✓[/green] Spawned {worker.name}")
    time.sleep(0.5)

console.print(f"\n[bold green]✓ {len(workers)} workers deployed[/bold green]")

# Monitoring phase
console.print("\n[bold]Phase 4: Execution Monitoring[/bold]")
console.print("=" * 60)

console.print("\n📊 Real-time monitoring:")
console.print("  • Workers executing tasks autonomously")
console.print("  • Coordinator monitoring progress")
console.print("  • Press Ctrl+C to stop monitoring (workers continue)\n")

# Monitor progress
agent_registry = AgentRegistry(redis_client)
start_time = time.time()
last_task_count = len(pending_tasks)

try:
    iteration = 0
    while True:
        iteration += 1

        # Get current state
        alive_workers = spawner.count_alive_workers()
        current_tasks = task_queue.list_pending_tasks()
        current_task_count = len(current_tasks)

        # Calculate progress
        completed = last_task_count - current_task_count
        elapsed = int(time.time() - start_time)

        # Show status
        status_line = (
            f"\r⚡ Workers: [cyan]{alive_workers}[/cyan] | "
            f"Tasks remaining: [yellow]{current_task_count}[/yellow] | "
            f"Completed: [green]{completed}[/green] | "
            f"Elapsed: [blue]{elapsed // 60}m {elapsed % 60}s[/blue]"
        )

        console.print(status_line, end='')

        # Check if done
        if alive_workers == 0 and current_task_count < last_task_count:
            console.print(f"\n\n[bold green]✓ All workers finished![/bold green]")
            break

        if current_task_count == 0:
            console.print(f"\n\n[bold green]✓ All tasks completed![/bold green]")
            break

        # Every 30 seconds, show a more detailed update
        if iteration % 6 == 0:
            console.print("")  # New line
            agents = agent_registry.list_agents()
            active = sum(1 for a in agents.values() if a.get('status') == 'working')
            console.print(f"  Active agents: {active}, Tasks in queue: {current_task_count}")

        time.sleep(5)

except KeyboardInterrupt:
    console.print("\n\n[yellow]⚠️  Monitoring stopped (workers continue in background)[/yellow]")
    console.print(f"   {spawner.count_alive_workers()} workers still active")

finally:
    spawner.cleanup_dead_workers()

# Summary
console.print("\n[bold]Phase 5: Completion Summary[/bold]")
console.print("=" * 60)

elapsed_total = int(time.time() - start_time)
final_tasks = task_queue.list_pending_tasks()
tasks_completed = last_task_count - len(final_tasks)

summary_table = Table(box=box.ROUNDED, show_header=False)
summary_table.add_column("Metric", style="cyan")
summary_table.add_column("Value", style="bold white")

summary_table.add_row("Tasks Completed", f"{tasks_completed}/{last_task_count}")
summary_table.add_row("Workers Deployed", str(plan.recommended_agents))
summary_table.add_row("Total Time", f"{elapsed_total // 60}m {elapsed_total % 60}s")
summary_table.add_row("Estimated Cost", f"${plan.total_estimated_cost:.2f}")
summary_table.add_row("Status", "[green]✓ Complete[/green]" if len(final_tasks) == 0 else "[yellow]In Progress[/yellow]")

console.print(summary_table)

console.print("\n[bold green]✨ Interactive TUI build coordinated successfully![/bold green]")
console.print("\nNext steps:")
console.print("  1. Check generated files: [cyan]ls -la agentcoord/tui.py[/cyan]")
console.print("  2. Test the TUI: [cyan]agentcoord[/cyan]")
console.print("  3. View dashboard: [cyan]agentcoord dashboard[/cyan]")
console.print("\n[dim]Coordination complete. Workers may still be finishing final tasks.[/dim]\n")
