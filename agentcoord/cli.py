import click
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .coordinator import TaskCoordinator
from .worker import Worker
from .llm_worker import LLMWorker
from .storage import TaskStorage, WorkerStorage

console = Console()

@click.group()
def cli():
    """AgentCoord - Distributed Task Coordination System"""
    pass

@cli.command()
@click.option('--storage-path', default='./agentcoord_data', help='Path to storage directory')
def workers(storage_path: str):
    """List all active workers with their status"""
    try:
        worker_storage = WorkerStorage(storage_path)
        task_storage = TaskStorage(storage_path)
        
        active_workers = worker_storage.get_active_workers()
        
        if not active_workers:
            console.print("[yellow]No active workers found[/yellow]")
            return
        
        table = Table(title="Active Workers", box=box.ROUNDED)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Tags", style="green")
        table.add_column("Tasks Completed", justify="right", style="blue")
        table.add_column("Uptime", style="magenta")
        table.add_column("Last Heartbeat", style="yellow")
        
        for worker in active_workers:
            # Calculate uptime
            start_time = datetime.fromisoformat(worker['started_at'])
            uptime = datetime.now() - start_time
            uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
            
            # Format last heartbeat
            last_heartbeat = datetime.fromisoformat(worker['last_heartbeat'])
            heartbeat_ago = datetime.now() - last_heartbeat
            if heartbeat_ago.seconds < 60:
                heartbeat_str = f"{heartbeat_ago.seconds}s ago"
            elif heartbeat_ago.seconds < 3600:
                heartbeat_str = f"{heartbeat_ago.seconds//60}m ago"
            else:
                heartbeat_str = f"{heartbeat_ago.seconds//3600}h ago"
            
            # Get completed tasks count
            completed_tasks = task_storage.get_completed_tasks_count(worker['id'])
            
            table.add_row(
                worker['name'],
                ', '.join(worker.get('tags', [])),
                str(completed_tasks),
                uptime_str,
                heartbeat_str
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing workers: {str(e)}[/red]")

@cli.command()
@click.option('--storage-path', default='./agentcoord_data', help='Path to storage directory')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without actually doing it')
def cleanup(storage_path: str, dry_run: bool):
    """Remove stale tasks, dead agents, and orphaned locks"""
    try:
        coordinator = TaskCoordinator(storage_path)
        
        console.print("[blue]Starting cleanup process...[/blue]")
        
        # Define cleanup thresholds
        stale_task_threshold = datetime.now() - timedelta(hours=24)
        dead_agent_threshold = datetime.now() - timedelta(hours=1)
        
        cleanup_stats = {
            'stale_tasks': 0,
            'dead_agents': 0,
            'orphaned_locks': 0
        }
        
        # Clean stale tasks
        stale_tasks = coordinator.storage.get_stale_tasks(stale_task_threshold)
        cleanup_stats['stale_tasks'] = len(stale_tasks)
        
        if not dry_run:
            for task in stale_tasks:
                coordinator.storage.remove_task(task['id'])
        
        # Clean dead agents
        dead_agents = coordinator.worker_storage.get_dead_workers(dead_agent_threshold)
        cleanup_stats['dead_agents'] = len(dead_agents)
        
        if not dry_run:
            for agent in dead_agents:
                coordinator.worker_storage.remove_worker(agent['id'])
        
        # Clean orphaned locks
        orphaned_locks = coordinator.storage.get_orphaned_locks()
        cleanup_stats['orphaned_locks'] = len(orphaned_locks)
        
        if not dry_run:
            coordinator.storage.clear_orphaned_locks()
        
        # Display results
        table = Table(title=f"Cleanup Results {'(DRY RUN)' if dry_run else ''}", box=box.ROUNDED)
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Description", style="yellow")
        
        table.add_row(
            "Stale Tasks",
            str(cleanup_stats['stale_tasks']),
            "Tasks created >24h ago, not claimed"
        )
        table.add_row(
            "Dead Agents",
            str(cleanup_stats['dead_agents']),
            "Agents with no heartbeat >1h"
        )
        table.add_row(
            "Orphaned Locks",
            str(cleanup_stats['orphaned_locks']),
            "Locks without active workers"
        )
        
        console.print(table)
        
        if dry_run:
            console.print("[yellow]This was a dry run. Use without --dry-run to perform actual cleanup.[/yellow]")
        else:
            console.print("[green]Cleanup completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Error during cleanup: {str(e)}[/red]")

@cli.command()
@click.option('--storage-path', default='./agentcoord_data', help='Path to storage directory')
def stats(storage_path: str):
    """Show comprehensive system statistics"""
    try:
        coordinator = TaskCoordinator(storage_path)
        
        # Get system stats
        system_stats = coordinator.storage.get_system_stats()
        worker_stats = coordinator.worker_storage.get_worker_stats()
        
        # System Stats Panel
        system_table = Table(box=box.SIMPLE)
        system_table.add_column("Metric", style="cyan")
        system_table.add_column("Value", style="green", justify="right")
        
        system_table.add_row("Total Tasks", str(system_stats.get('total_tasks', 0)))
        system_table.add_row("Completed Tasks", str(system_stats.get('completed_tasks', 0)))
        system_table.add_row("Pending Tasks", str(system_stats.get('pending_tasks', 0)))
        system_table.add_row("Failed Tasks", str(system_stats.get('failed_tasks', 0)))
        
        completion_rate = 0
        if system_stats.get('total_tasks', 0) > 0:
            completion_rate = (system_stats.get('completed_tasks', 0) / system_stats.get('total_tasks', 0)) * 100
        
        system_table.add_row("Completion Rate", f"{completion_rate:.1f}%")
        
        avg_time = system_stats.get('avg_completion_time', 0)
        system_table.add_row("Avg Completion Time", f"{avg_time:.2f}s")
        
        # Worker Stats Panel
        worker_table = Table(box=box.SIMPLE)
        worker_table.add_column("Metric", style="cyan")
        worker_table.add_column("Value", style="green", justify="right")
        
        worker_table.add_row("Total Workers Spawned", str(worker_stats.get('total_spawned', 0)))
        worker_table.add_row("Active Workers", str(worker_stats.get('active_count', 0)))
        worker_table.add_row("Total Tasks Completed", str(worker_stats.get('total_completed_tasks', 0)))
        
        # Cost estimation (rough estimate for LLM workers)
        llm_workers = worker_stats.get('llm_workers', 0)
        estimated_cost = llm_workers * system_stats.get('completed_tasks', 0) * 0.002  # Rough estimate
        worker_table.add_row("Estimated LLM Cost", f"${estimated_cost:.2f}")
        
        # Display panels
        console.print(Panel(system_table, title="System Statistics", border_style="blue"))
        console.print(Panel(worker_table, title="Worker Statistics", border_style="green"))
        
    except Exception as e:
        console.print(f"[red]Error retrieving stats: {str(e)}[/red]")

@cli.command()
@click.argument('name')
@click.option('--tags', default='', help='Comma-separated tags for the worker')
@click.option('--llm', is_flag=True, help='Spawn an LLM worker')
@click.option('--storage-path', default='./agentcoord_data', help='Path to storage directory')
@click.option('--detach', is_flag=True, help='Run worker in background')
def spawn(name: str, tags: str, llm: bool, storage_path: str, detach: bool):
    """Spawn a new worker"""
    try:
        coordinator = TaskCoordinator(storage_path)
        
        # Parse tags
        worker_tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        console.print(f"[blue]Spawning {'LLM ' if llm else ''}worker: {name}[/blue]")
        console.print(f"[yellow]Tags: {', '.join(worker_tags) if worker_tags else 'None'}[/yellow]")
        
        # Create worker instance
        if llm:
            worker = LLMWorker(name, coordinator, tags=worker_tags)
        else:
            worker = Worker(name, coordinator, tags=worker_tags)
        
        if detach:
            # Start worker in background
            import threading
            worker_thread = threading.Thread(target=worker.start, daemon=True)
            worker_thread.start()
            console.print(f"[green]Worker '{name}' started in background[/green]")
            console.print("[yellow]Note: Worker will stop when CLI exits. Use a process manager for production.[/yellow]")
        else:
            console.print(f"[green]Starting worker '{name}'... (Press Ctrl+C to stop)[/green]")
            try:
                worker.start()
            except KeyboardInterrupt:
                console.print(f"\n[yellow]Stopping worker '{name}'...[/yellow]")
                worker.stop()
                console.print("[green]Worker stopped successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]Error spawning worker: {str(e)}[/red]")

@cli.command()
@click.argument('task_id')
@click.option('--storage-path', default='./agentcoord_data', help='Path to storage directory')
def status(task_id: str, storage_path: str):
    """Show status of a specific task"""
    try:
        coordinator = TaskCoordinator(storage_path)
        task = coordinator.storage.get_task(task_id)
        
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("ID", task['id'])
        table.add_row("Type", task['type'])
        table.add_row("Status", task['status'])
        table.add_row("Priority", str(task.get('priority', 0)))
        table.add_row("Tags", ', '.join(task.get('tags', [])))
        table.add_row("Created", task['created_at'])
        
        if task.get('claimed_by'):
            table.add_row("Claimed By", task['claimed_by'])
            table.add_row("Claimed At", task.get('claimed_at', 'Unknown'))
        
        if task.get('completed_at'):
            table.add_row("Completed At", task['completed_at'])
        
        if task.get('error'):
            table.add_row("Error", task['error'])
        
        console.print(Panel(table, title=f"Task {task_id}", border_style="blue"))
        
    except Exception as e:
        console.print(f"[red]Error retrieving task status: {str(e)}[/red]")

if __name__ == '__main__':
    cli()