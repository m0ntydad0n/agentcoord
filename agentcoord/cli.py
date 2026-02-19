"""Command-line interface for agentcoord monitoring and management."""

import click
import os
import sys
from datetime import datetime
from .llm import LLMBudget
from .client import CoordinationClient
from .agent import AgentRegistry
from .tasks import TaskQueue
from .board import Board
from .approvals import ApprovalWorkflow


def launch_tui():
    """Launch the TUI interface."""
    try:
        from .tui import TUIApp
        app = TUIApp()
        app.run()
        return True
    except ImportError as e:
        click.echo(f"TUI not available: {e}", err=True)
        return False
    except Exception as e:
        click.echo(f"TUI error: {e}", err=True)
        return False


@click.group()
@click.option('--redis-url', envvar='REDIS_URL', default='redis://localhost:6379',
              help='Redis connection URL')
@click.pass_context
def cli(ctx, redis_url):
    """AgentCoord - Multi-agent coordination CLI."""
    ctx.ensure_object(dict)
    ctx.obj['redis_url'] = redis_url

    # Try to connect to Redis
    try:
        import redis
        client = redis.from_url(redis_url, socket_connect_timeout=1, decode_responses=True)
        client.ping()
        ctx.obj['redis'] = client
        ctx.obj['mode'] = 'redis'
    except:
        click.echo(f"⚠️  Redis unavailable at {redis_url}, some commands may not work", err=True)
        ctx.obj['redis'] = None
        ctx.obj['mode'] = 'file'


@cli.command()
@click.pass_context
def status(ctx):
    """Show all registered agents and their status."""
    if ctx.obj['mode'] == 'file':
        click.echo("Status command requires Redis connection")
        return

    registry = AgentRegistry(ctx.obj['redis'])
    agents = registry.list_agents()

    if not agents:
        click.echo("No agents registered")
        return

    click.echo(f"\n{'AGENT ID':<36} {'ROLE':<15} {'NAME':<20} {'STATUS':<10} {'WORKING ON'}")
    click.echo("=" * 120)

    for agent_id, data in agents.items():
        click.echo(
            f"{agent_id:<36} "
            f"{data.get('role', 'N/A'):<15} "
            f"{data.get('name', 'N/A'):<20} "
            f"{data.get('status', 'N/A'):<10} "
            f"{data.get('working_on', '')}"
        )

    click.echo()


@cli.command()
@click.pass_context
def locks(ctx):
    """Show all active file locks."""
    if ctx.obj['mode'] == 'file':
        click.echo("Locks command requires Redis connection")
        return

    redis = ctx.obj['redis']
    lock_keys = redis.keys("lock:file:*")

    if not lock_keys:
        click.echo("No active file locks")
        return

    click.echo(f"\n{'FILE PATH':<50} {'OWNER':<36} {'INTENT'}")
    click.echo("=" * 120)

    for key in lock_keys:
        meta_key = f"{key}:meta"
        meta = redis.hgetall(meta_key)
        if meta:
            click.echo(
                f"{meta.get('file_path', 'N/A'):<50} "
                f"{meta.get('owner', 'N/A'):<36} "
                f"{meta.get('intent', '')}"
            )

    click.echo()


@cli.command()
@click.pass_context
def tasks(ctx):
    """Show task queue."""
    if ctx.obj['mode'] == 'file':
        click.echo("Tasks command requires Redis connection")
        return

    task_queue = TaskQueue(ctx.obj['redis'])
    all_tasks = task_queue.list_pending_tasks()

    if not all_tasks:
        click.echo("No tasks in queue")
        return

    click.echo(f"\n{'TASK ID':<36} {'STATUS':<12} {'PRIORITY':<8} {'TITLE'}")
    click.echo("=" * 120)

    for task in all_tasks:
        click.echo(
            f"{task.id:<36} "
            f"{task.status.value:<12} "
            f"{task.priority:<8} "
            f"{task.title}"
        )

    click.echo()


@cli.command()
@click.pass_context
def board(ctx):
    """Show board threads."""
    if ctx.obj['mode'] == 'file':
        click.echo("Board command requires Redis connection")
        return

    board_obj = Board(ctx.obj['redis'])
    threads = board_obj.list_threads()

    if not threads:
        click.echo("No board threads")
        return

    click.echo(f"\n{'THREAD ID':<36} {'STATUS':<12} {'PRIORITY':<8} {'TITLE'}")
    click.echo("=" * 120)

    for thread in threads:
        click.echo(
            f"{thread.id:<36} "
            f"{thread.status.value:<12} "
            f"{thread.priority:<8} "
            f"{thread.title}"
        )

    click.echo()


@cli.command()
@click.argument('approval_id')
@click.pass_context
def approve(ctx, approval_id):
    """Approve a pending approval request."""
    if ctx.obj['mode'] == 'file':
        click.echo("Approve command requires Redis connection")
        return

    workflow = ApprovalWorkflow(ctx.obj['redis'])

    try:
        approver_id = f"cli-{os.getenv('USER', 'unknown')}"
        workflow.approve(approval_id, approver_id)
        click.echo(f"✓ Approved {approval_id}")
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)


@cli.command()
@click.option('--status-file', default='./workbench/STATUS.md',
              help='Path to STATUS.md output file')
@click.option('--board-file', default='./workbench/BOARD.md',
              help='Path to BOARD.md output file')
@click.pass_context
def export(ctx, status_file, board_file):
    """Export Redis state to markdown files."""
    if ctx.obj['mode'] == 'file':
        click.echo("Export command requires Redis connection")
        return

    click.echo(f"Exporting to {status_file} and {board_file}...")
    click.echo("⚠️  Export functionality not yet implemented")
    # TODO: Implement export


@cli.command()
@click.option('--threshold', default=300, help='Threshold in seconds')
@click.pass_context
def hung(ctx, threshold):
    """Detect hung/stale agents with no recent heartbeat."""
    if ctx.obj['mode'] == 'file':
        click.echo("Hung command requires Redis connection")
        return

    registry = AgentRegistry(ctx.obj['redis'])
    stale_agents = registry.get_stale_agents(threshold_seconds=threshold)

    if not stale_agents:
        click.echo(f"No hung agents (threshold: {threshold}s)")
        return

    click.echo(f"\n⚠️  Found {len(stale_agents)} hung agent(s) (no heartbeat in {threshold}s):")
    click.echo()
    click.echo(f"{'AGENT ID':<36} {'ROLE':<15} {'NAME':<20} {'LAST HEARTBEAT'}")
    click.echo("=" * 120)

    for agent_id, data in stale_agents.items():
        click.echo(
            f"{agent_id:<36} "
            f"{data.get('role', 'N/A'):<15} "
            f"{data.get('name', 'N/A'):<20} "
            f"{data.get('last_heartbeat', 'N/A')}"
        )

    click.echo()


@cli.command()
@click.pass_context
def budget(ctx):
    """Show LLM budget usage and statistics."""
    if ctx.obj['mode'] == 'file':
        click.echo("Budget command requires Redis connection")
        return

    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        click.echo("This command requires the 'rich' package. Install with: pip install rich")
        return

    console = Console()

    budget_tracker = LLMBudget(ctx.obj['redis'])
    stats = budget_tracker.get_usage_stats()

    # Header
    console.print("\n[bold cyan]LLM Budget Status[/bold cyan]")
    console.print("=" * 60)

    # Summary
    console.print(f"Daily Budget: ${stats['total_cost']:.2f}")
    console.print(f"In-Flight: {stats['in_flight']} / {stats['max_concurrent']} slots\n")

    # By Model table
    if stats['by_model']:
        table = Table(title="Usage by Model")
        table.add_column("Model", style="cyan")
        table.add_column("Tokens", justify="right", style="green")
        table.add_column("Cost", justify="right", style="yellow")

        for model, data in sorted(stats['by_model'].items()):
            table.add_row(
                model,
                f"{data['tokens']:,}",
                f"${data['cost']:.2f}"
            )

        console.print(table)
        console.print()

    # By Agent table
    if stats['by_agent']:
        table = Table(title="Usage by Agent")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Calls", justify="right", style="magenta")
        table.add_column("Tokens", justify="right", style="green")
        table.add_column("Cost", justify="right", style="yellow")

        # Sort by cost descending
        sorted_agents = sorted(
            stats['by_agent'].items(),
            key=lambda x: x[1]['total_cost'],
            reverse=True
        )

        for agent_id, data in sorted_agents[:10]:  # Top 10
            table.add_row(
                agent_id[:20] + "..." if len(agent_id) > 20 else agent_id,
                str(data['calls']),
                f"{data['total_tokens']:,}",
                f"${data['total_cost']:.2f}"
            )

        console.print(table)

    console.print()


@cli.command()
@click.option('--refresh-rate', default=1.0, type=float,
              help='Dashboard refresh rate in seconds')
@click.pass_context
def dashboard(ctx, refresh_rate):
    """Launch live monitoring dashboard with cyberpunk UI."""
    if ctx.obj['mode'] == 'file':
        click.echo("Dashboard requires Redis connection")
        return

    try:
        from .dashboard import AgentCoordDashboard
    except ImportError:
        click.echo("❌ Dashboard requires 'rich' package. Install with: pip install rich")
        return

    dash = AgentCoordDashboard(ctx.obj['redis'], refresh_rate=refresh_rate)

    click.echo("\n🚀 Launching live dashboard...")
    click.echo("   Press Ctrl+C to exit\n")

    dash.run()


if __name__ == '__main__':
    cli(obj={})
