"""CLI commands for health monitoring."""
import click
import json
from datetime import datetime
from typing import Dict, Any

from ..agent import Agent
from ..coordinator import Coordinator


def format_timestamp(timestamp: float) -> str:
    """Format timestamp for display."""
    if not timestamp:
        return "Never"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def format_uptime(uptime: float) -> str:
    """Format uptime in human readable format."""
    if uptime < 60:
        return f"{uptime:.1f}s"
    elif uptime < 3600:
        return f"{uptime/60:.1f}m"
    else:
        return f"{uptime/3600:.1f}h"


def format_memory(memory_info: Dict[str, Any]) -> str:
    """Format memory usage."""
    if not memory_info:
        return "N/A"
    return f"{memory_info['percent']:.1f}% ({memory_info['used']//1024//1024}MB)"


@click.group()
def health():
    """Health monitoring commands."""
    pass


@health.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format')
@click.option('--unhealthy-only', is_flag=True, help='Show only unhealthy workers')
def status(json_output: bool, unhealthy_only: bool):
    """Show health status of all workers."""
    health_data = Agent.get_all_agents_health()
    unhealthy_workers = set(Agent.get_unhealthy_workers())
    
    if json_output:
        coordinator = Coordinator()
        summary = coordinator.get_cluster_health_summary()
        click.echo(json.dumps(summary, indent=2))
        return
    
    if not health_data:
        click.echo("No workers found")
        return
    
    # Print header
    click.echo(f"{'Worker ID':<15} {'Status':<10} {'Uptime':<10} {'Tasks':<8} {'Memory':<15} {'CPU':<6} {'Last Heartbeat'}")
    click.echo("-" * 90)
    
    for worker_id, health in health_data.items():
        is_unhealthy = worker_id in unhealthy_workers
        
        if unhealthy_only and not is_unhealthy:
            continue
        
        status_str = "UNHEALTHY" if is_unhealthy else "HEALTHY"
        uptime = format_uptime(health.get('uptime', 0))
        tasks = health.get('tasks_completed', 0)
        memory = format_memory(health.get('memory_usage'))
        cpu = f"{health.get('cpu_percent', 0):.1f}%" if health.get('cpu_percent') is not None else "N/A"
        last_heartbeat = format_timestamp(health.get('timestamp'))
        
        # Color coding for unhealthy workers
        if is_unhealthy:
            line = click.style(
                f"{worker_id:<15} {status_str:<10} {uptime:<10} {tasks:<8} {memory:<15} {cpu:<6} {last_heartbeat}",
                fg='red'
            )
        else:
            line = f"{worker_id:<15} {status_str:<10} {uptime:<10} {tasks:<8} {memory:<15} {cpu:<6} {last_heartbeat}"
        
        click.echo(line)
    
    # Summary
    total = len(health_data)
    unhealthy_count = len(unhealthy_workers)
    healthy_count = total - unhealthy_count
    
    click.echo(f"\nSummary: {total} total workers, {healthy_count} healthy, {unhealthy_count} unhealthy")


@health.command()
def summary():
    """Show cluster health summary."""
    coordinator = Coordinator()
    summary = coordinator.get_cluster_health_summary()
    
    click.echo(f"Cluster Health Summary")
    click.echo(f"=====================")
    click.echo(f"Total Workers: {summary['total_workers']}")
    click.echo(f"Healthy: {summary['healthy_workers']}")
    click.echo(f"Unhealthy: {summary['unhealthy_workers']}")
    
    if summary['unhealthy_worker_ids']:
        click.echo(f"Unhealthy Workers: {', '.join(summary['unhealthy_worker_ids'])}")
    
    click.echo(f"Last Updated: {format_timestamp(summary['timestamp'])}")


@health.command()
@click.argument('worker_id')
def detail(worker_id: str):
    """Show detailed health information for a specific worker."""
    health_data = Agent.get_all_agents_health()
    
    if worker_id not in health_data:
        click.echo(f"Worker {worker_id} not found", err=True)
        return
    
    health = health_data[worker_id]
    is_unhealthy = worker_id in Agent.get_unhealthy_workers()
    
    click.echo(f"Worker: {worker_id}")
    click.echo(f"Status: {'UNHEALTHY' if is_unhealthy else 'HEALTHY'}")
    click.echo(f"Uptime: {format_uptime(health.get('uptime', 0))}")
    click.echo(f"Tasks Completed: {health.get('tasks_completed', 0)}")
    click.echo(f"Last Task: {format_timestamp(health.get('last_task_timestamp'))}")
    click.echo(f"Last Heartbeat: {format_timestamp(health.get('timestamp'))}")
    
    if health.get('memory_usage'):
        mem = health['memory_usage']
        click.echo(f"Memory: {mem['percent']:.1f}% ({mem['used']//1024//1024}MB used, {mem['available']//1024//1024}MB available)")
    
    if health.get('cpu_percent') is not None:
        click.echo(f"CPU: {health['cpu_percent']:.1f}%")