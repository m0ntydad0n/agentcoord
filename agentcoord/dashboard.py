"""
Live dashboard for monitoring AgentCoord execution in real-time.

Displays real-time task progress, agent status, and cost tracking
with the cyberpunk aesthetic UI.
"""

import time
import sys
from datetime import datetime
from typing import Dict, List, Optional
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich import box

console = Console()


class AgentCoordDashboard:
    """Real-time dashboard for AgentCoord monitoring."""

    def __init__(self, redis_client, refresh_rate: float = 1.0):
        """
        Initialize dashboard.

        Args:
            redis_client: Redis client for fetching data
            refresh_rate: Seconds between refreshes
        """
        self.redis = redis_client
        self.refresh_rate = refresh_rate
        self.start_time = datetime.now()

    def make_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="tasks", ratio=2),
            Layout(name="stats", ratio=1)
        )

        return layout

    def render_header(self) -> Panel:
        """Render the cyberpunk header."""
        uptime = datetime.now() - self.start_time
        uptime_str = f"{int(uptime.total_seconds() // 60)}m {int(uptime.total_seconds() % 60)}s"

        header_text = Text()
        header_text.append("⚡ AGENTCOORD ", style="bold cyan")
        header_text.append("LIVE DASHBOARD", style="bold green")
        header_text.append(f"  •  Uptime: {uptime_str}", style="dim")

        return Panel(
            header_text,
            box=box.DOUBLE_EDGE,
            style="cyan",
            padding=(0, 1)
        )

    def render_tasks(self, tasks: List[Dict]) -> Panel:
        """Render task queue table."""
        table = Table(
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
            expand=True
        )

        table.add_column("ID", style="dim", width=10, no_wrap=True)
        table.add_column("Title", style="bold")
        table.add_column("Status", justify="center", width=12)
        table.add_column("Priority", justify="center", width=8)

        # Status symbols
        status_symbols = {
            "pending": ("⏳", "yellow"),
            "claimed": ("⚡", "blue"),
            "completed": ("✅", "green"),
            "failed": ("❌", "red")
        }

        if not tasks:
            table.add_row(
                "[dim]—[/dim]",
                "[dim italic]No tasks in queue[/dim italic]",
                "[dim]—[/dim]",
                "[dim]—[/dim]"
            )
        else:
            for task in tasks[:15]:  # Show max 15 tasks
                task_id = task.get('id', 'N/A')[:8]
                title = task.get('title', 'Unknown')
                status = task.get('status', 'pending')
                priority = task.get('priority', 3)

                symbol, color = status_symbols.get(status, ("◯", "white"))
                status_display = f"[{color}]{symbol} {status.upper()}[/{color}]"

                # Truncate long titles
                if len(title) > 40:
                    title = title[:37] + "..."

                table.add_row(
                    task_id,
                    title,
                    status_display,
                    str(priority)
                )

        return Panel(
            table,
            title="[bold cyan]◈ TASK QUEUE ◈[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )

    def render_stats(self, agents: List[Dict], stats: Dict) -> Panel:
        """Render statistics panel."""
        # Stats section
        stats_text = Text()
        stats_text.append("SYSTEM STATS\n", style="bold cyan")
        stats_text.append("═" * 30 + "\n\n", style="cyan")

        total_tasks = stats.get('total_tasks', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        pending = stats.get('pending', 0)
        active_agents = len([a for a in agents if a.get('status') == 'working'])
        total_agents = len(agents)
        total_cost = stats.get('total_cost', 0.0)

        stats_text.append(f"Total Tasks:  ", style="dim")
        stats_text.append(f"{total_tasks}\n", style="bold white")

        stats_text.append(f"Completed:    ", style="dim")
        stats_text.append(f"{completed}\n", style="green")

        stats_text.append(f"Failed:       ", style="dim")
        stats_text.append(f"{failed}\n", style="red" if failed > 0 else "dim")

        stats_text.append(f"Pending:      ", style="dim")
        stats_text.append(f"{pending}\n\n", style="yellow")

        stats_text.append(f"Agents:       ", style="dim")
        stats_text.append(f"{active_agents}/{total_agents}\n", style="cyan")

        stats_text.append(f"Total Cost:   ", style="dim")
        stats_text.append(f"${total_cost:.4f}\n\n", style="magenta")

        # Progress bar
        if total_tasks > 0:
            progress_pct = int((completed / total_tasks) * 100)
            filled = int(progress_pct / 5)
            bar = "█" * filled + "░" * (20 - filled)
            stats_text.append(f"{bar} {progress_pct}%\n", style="green")

        # Agent list
        if agents:
            stats_text.append("\n" + "─" * 30 + "\n", style="cyan")
            stats_text.append("ACTIVE AGENTS\n\n", style="bold cyan")

            for agent in agents[:8]:  # Show max 8 agents
                name = agent.get('name', 'Unknown')[:15]
                status = agent.get('status', 'idle')

                if status == "working":
                    symbol = "●"
                    color = "green"
                elif status == "idle":
                    symbol = "◉"
                    color = "yellow"
                else:
                    symbol = "○"
                    color = "red"

                stats_text.append(f"[{color}]{symbol}[/{color}] ")
                stats_text.append(f"{name}\n", style="white")

        return Panel(
            stats_text,
            title="[bold green]◈ STATISTICS ◈[/bold green]",
            border_style="green",
            box=box.ROUNDED
        )

    def render_footer(self) -> Panel:
        """Render footer with controls."""
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold cyan")
        footer_text.append(" to exit  •  Refreshing every ", style="dim")
        footer_text.append(f"{self.refresh_rate}s", style="bold cyan")

        return Panel(
            footer_text,
            style="cyan",
            box=box.ROUNDED
        )

    def fetch_data(self) -> Dict:
        """Fetch current data from Redis."""
        try:
            from .tasks import TaskQueue
            from .agent import AgentRegistry
        except ImportError:
            # Fallback for when running as standalone script
            from agentcoord.tasks import TaskQueue
            from agentcoord.agent import AgentRegistry

        task_queue = TaskQueue(self.redis)
        agent_registry = AgentRegistry(self.redis)

        # Get tasks
        all_tasks = []
        try:
            # Get pending tasks
            pending = task_queue.list_pending_tasks()
            for t in pending:
                all_tasks.append({
                    'id': t.id,
                    'title': t.title,
                    'status': 'pending',
                    'priority': t.priority
                })
        except Exception as e:
            console.print(f"[yellow]Error fetching tasks: {e}[/yellow]")

        # Get agents
        agents = []
        try:
            agents_dict = agent_registry.list_agents()
            for agent_id, data in agents_dict.items():
                agents.append({
                    'id': agent_id,
                    'name': data.get('name', agent_id[:8]),
                    'status': data.get('status', 'unknown'),
                    'working_on': data.get('working_on', '')
                })
        except Exception as e:
            console.print(f"[yellow]Error fetching agents: {e}[/yellow]")

        # Calculate stats
        completed = sum(1 for t in all_tasks if t.get('status') == 'completed')
        failed = sum(1 for t in all_tasks if t.get('status') == 'failed')
        pending_count = sum(1 for t in all_tasks if t.get('status') == 'pending')

        # Get total cost from budget tracker
        total_cost = 0.0
        try:
            cost_str = self.redis.get("budget:total_cost")
            if cost_str:
                total_cost = float(cost_str)
        except:
            pass

        stats = {
            'total_tasks': len(all_tasks),
            'completed': completed,
            'failed': failed,
            'pending': pending_count,
            'total_cost': total_cost
        }

        return {
            'tasks': all_tasks,
            'agents': agents,
            'stats': stats
        }

    def generate_dashboard(self) -> Layout:
        """Generate the complete dashboard layout."""
        layout = self.make_layout()

        # Fetch current data
        data = self.fetch_data()

        # Render components
        layout["header"].update(self.render_header())
        layout["tasks"].update(self.render_tasks(data['tasks']))
        layout["stats"].update(self.render_stats(data['agents'], data['stats']))
        layout["footer"].update(self.render_footer())

        return layout

    def run(self):
        """Run the live dashboard."""
        console.clear()

        try:
            with Live(
                self.generate_dashboard(),
                console=console,
                refresh_per_second=1 / self.refresh_rate,
                screen=True
            ) as live:
                while True:
                    time.sleep(self.refresh_rate)
                    live.update(self.generate_dashboard())

        except KeyboardInterrupt:
            console.print("\n[bold green]✓ Dashboard stopped[/bold green]")
            sys.exit(0)


def main():
    """CLI entry point for standalone dashboard."""
    import argparse
    import redis

    parser = argparse.ArgumentParser(description="AgentCoord Live Dashboard")
    parser.add_argument("--redis-url", default="redis://localhost:6379",
                       help="Redis connection URL")
    parser.add_argument("--refresh-rate", type=float, default=1.0,
                       help="Refresh rate in seconds")

    args = parser.parse_args()

    try:
        redis_client = redis.from_url(args.redis_url, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        console.print(f"[red]❌ Cannot connect to Redis: {e}[/red]")
        console.print("[yellow]Start Redis with: brew services start redis[/yellow]")
        sys.exit(1)

    dashboard = AgentCoordDashboard(redis_client, refresh_rate=args.refresh_rate)
    dashboard.run()


if __name__ == "__main__":
    main()
