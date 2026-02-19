"""Rich panels and tables for cyberpunk terminal UI."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align
from typing import List, Dict
from .theme import get_console, ICONS, get_status_indicator, get_priority_indicator


def create_task_table(tasks: List[Dict]) -> Table:
    """Create cyberpunk-styled task table."""
    table = Table(
        title="[neon.cyan]TASK QUEUE[/neon.cyan]",
        border_style="border",
        header_style="header",
        show_lines=True
    )

    table.add_column("ID", style="bright_black", width=8)
    table.add_column("●", justify="center", width=3)
    table.add_column("Priority", justify="center", width=4)
    table.add_column("Title", style="value")
    table.add_column("Status", justify="center", width=12)
    table.add_column("Model", justify="center", width=12)

    for task in tasks:
        task_id = task.get('id', 'N/A')[:8]
        priority = task.get('priority', 3)
        title = task.get('title', 'Untitled')
        status = task.get('status', 'pending')
        model = task.get('model', 'haiku')

        # Status indicator
        status_icon = get_status_indicator(status)

        # Priority indicator
        priority_icon = get_priority_indicator(priority)

        # Status color
        status_colors = {
            'pending': 'task.pending',
            'claimed': 'task.claimed',
            'in_progress': 'task.running',
            'completed': 'task.complete',
            'failed': 'task.failed'
        }
        status_style = status_colors.get(status, 'value')

        # Model color
        model_colors = {
            'haiku': 'model.haiku',
            'sonnet': 'model.sonnet',
            'opus': 'model.opus'
        }
        model_style = model_colors.get(model, 'value')

        table.add_row(
            task_id,
            status_icon,
            f"P{priority}",
            title,
            f"[{status_style}]{status}[/{status_style}]",
            f"[{model_style}]{model}[/{model_style}]"
        )

    return table


def create_agent_table(agents: List[Dict]) -> Table:
    """Create cyberpunk-styled agent status table."""
    table = Table(
        title="[neon.green]AGENT FLEET[/neon.green]",
        border_style="border",
        header_style="header",
        show_lines=True
    )

    table.add_column("Agent", style="bright_cyan", width=20)
    table.add_column("●", justify="center", width=3)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Working On", style="value")
    table.add_column("Progress", justify="right", width=10)

    for agent in agents:
        name = agent.get('name', 'Unknown')
        status = agent.get('status', 'idle')
        working_on = agent.get('working_on', '-')
        progress = agent.get('progress', 0)

        # Status icon and color
        status_icon = '●' if status == 'active' else '○'
        status_color = 'agent.working' if status == 'active' else 'agent.idle'

        # Progress bar
        progress_pct = f"{int(progress * 100)}%" if progress else "-"

        table.add_row(
            name,
            f"[{status_color}]{status_icon}[/{status_color}]",
            f"[{status_color}]{status}[/{status_color}]",
            working_on,
            progress_pct
        )

    return table


def create_cost_panel(total_cost: float, budget: float = None) -> Panel:
    """Create cost tracking panel."""
    cost_color = "cost.cheap" if total_cost < 1.0 else "cost.moderate" if total_cost < 10.0 else "cost.expensive"

    content = f"[{cost_color}]${total_cost:.2f}[/{cost_color}]"

    if budget:
        pct = (total_cost / budget) * 100
        bar_length = 20
        filled = int((pct / 100) * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        content += f"\n\n{bar}\n{pct:.1f}% of ${budget:.2f} budget"

    return Panel(
        Align.center(content),
        title="[neon.yellow]💰 COST[/neon.yellow]",
        border_style="border"
    )


def create_progress_panel(completed: int, total: int) -> Panel:
    """Create progress tracking panel."""
    pct = (completed / total * 100) if total > 0 else 0

    bar_length = 30
    filled = int((pct / 100) * bar_length)
    bar = '█' * filled + '░' * (bar_length - filled)

    content = f"""[neon.green]{completed}[/neon.green] / {total} tasks complete

{bar}

[neon.cyan]{pct:.1f}%[/neon.cyan]"""

    return Panel(
        Align.center(content),
        title="[neon.cyan]📊 PROGRESS[/neon.cyan]",
        border_style="border"
    )


def create_summary_panels(stats: Dict) -> Columns:
    """Create summary statistics panels."""
    panels = [
        create_cost_panel(stats.get('total_cost', 0), stats.get('budget')),
        create_progress_panel(stats.get('completed', 0), stats.get('total', 0)),
        Panel(
            Align.center(f"[neon.green]{stats.get('agents', 0)}[/neon.green]\nactive"),
            title="[neon.green]🤖 AGENTS[/neon.green]",
            border_style="border"
        ),
        Panel(
            Align.center(f"[neon.yellow]{stats.get('eta', '~')}[/neon.yellow]\nremaining"),
            title="[neon.yellow]⏱ ETA[/neon.yellow]",
            border_style="border"
        )
    ]

    return Columns(panels, equal=True, expand=True)
