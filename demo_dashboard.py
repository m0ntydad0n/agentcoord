#!/usr/bin/env python3
"""
Quick demo of the AgentCoord live dashboard.
Shows a snapshot of the dashboard UI.
"""

import redis
from agentcoord.dashboard import AgentCoordDashboard
from rich.console import Console

console = Console()

# Connect to Redis
try:
    redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
    redis_client.ping()
except Exception as e:
    console.print(f"[red]❌ Cannot connect to Redis: {e}[/red]")
    console.print("[yellow]Start Redis with: brew services start redis[/yellow]")
    exit(1)

# Create dashboard
dashboard = AgentCoordDashboard(redis_client, refresh_rate=1.0)

# Show header
console.clear()
console.print("\n[bold cyan]🎉 AgentCoord Live Dashboard - Preview[/bold cyan]\n")
console.print("[dim]This is what the live dashboard looks like.[/dim]")
console.print("[dim]Run 'agentcoord dashboard' to launch the full live version.[/dim]\n")

# Generate and display one snapshot
layout = dashboard.generate_dashboard()
console.print(layout)

console.print("\n[bold green]✓ Dashboard is working![/bold green]\n")
console.print("To launch the live updating dashboard:")
console.print("  [cyan]agentcoord dashboard[/cyan]")
console.print("\nTo set custom refresh rate:")
console.print("  [cyan]agentcoord dashboard --refresh-rate 0.5[/cyan]  # Updates every 0.5s")
console.print()
