"""Rich formatting utilities for enhanced terminal output."""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
from rich import box
from datetime import datetime

console = Console()

class TaskStatus:
    """Task status constants with color coding."""
    PENDING = "pending"
    RUNNING = "running"  
    COMPLETED = "completed"
    FAILED = "failed"
    
    COLORS = {
        PENDING: "yellow",
        RUNNING: "blue", 
        COMPLETED: "green",
        FAILED: "red"
    }
    
    SYMBOLS = {
        PENDING: "⏳",
        RUNNING: "⚡", 
        COMPLETED: "✅",
        FAILED: "❌"
    }

class RichFormatter:
    """Rich formatting utilities with retro styling."""
    
    def __init__(self):
        self.console = console
        
    def print_header(self, title: str, subtitle: str = None):
        """Print a styled header panel."""
        header_text = f"[bold cyan]{title}[/bold cyan]"
        if subtitle:
            header_text += f"\n[dim]{subtitle}[/dim]"
            
        panel = Panel(
            Align.center(header_text),
            box=box.DOUBLE_EDGE,
            style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()

    def print_section(self, title: str, content: str, style: str = "blue"):
        """Print a bordered section panel."""
        panel = Panel(
            content,
            title=f"[bold]{title}[/bold]",
            box=box.ROUNDED,
            style=style,
            padding=(1, 2)
        )
        self.console.print(panel)

    def create_task_table(self, tasks: List[Dict[str, Any]]) -> Table:
        """Create a formatted table for tasks."""
        table = Table(
            title="[bold cyan]Task Overview[/bold cyan]",
            box=box.HEAVY_EDGE,
            header_style="bold magenta",
            show_lines=True
        )
        
        table.add_column("ID", style="dim", width=8)
        table.add_column("Task", style="bold")
        table.add_column("Status", justify="center", width=12)
        table.add_column("Progress", width=20)
        table.add_column("Updated", style="dim", width=12)
        
        for task in tasks:
            status = task.get("status", TaskStatus.PENDING)
            color = TaskStatus.COLORS.get(status, "white")
            symbol = TaskStatus.SYMBOLS.get(status, "◯")
            
            # Format status with color and symbol
            status_text = f"[{color}]{symbol} {status.upper()}[/{color}]"
            
            # Progress bar for running tasks
            progress = task.get("progress", 0)
            if status == TaskStatus.RUNNING and progress > 0:
                progress_bar = f"{'█' * int(progress/5)}{'░' * (20-int(progress/5))}"
                progress_text = f"[green]{progress_bar}[/green] {progress}%"
            elif status == TaskStatus.COMPLETED:
                progress_text = "[green]████████████████████[/green] 100%"
            else:
                progress_text = "░" * 20 + " 0%"
                
            # Format timestamp
            updated = task.get("updated", datetime.now())
            if isinstance(updated, datetime):
                time_str = updated.strftime("%H:%M:%S")
            else:
                time_str = str(updated)
            
            table.add_row(
                str(task.get("id", "N/A")),
                task.get("name", "Unnamed Task"),
                status_text,
                progress_text,
                time_str
            )
            
        return table

    def create_agent_status_table(self, agents: List[Dict[str, Any]]) -> Table:
        """Create a formatted table for agent status."""
        table = Table(
            title="[bold cyan]Agent Status[/bold cyan]",
            box=box.HEAVY_HEAD,
            header_style="bold green",
            show_header=True
        )
        
        table.add_column("Agent", style="bold cyan", width=15)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Current Task", style="italic")
        table.add_column("Load", justify="center", width=8)
        table.add_column("Uptime", style="dim", width=10)
        
        for agent in agents:
            status = agent.get("status", "offline")
            status_color = "green" if status == "active" else "red" if status == "error" else "yellow"
            
            load = agent.get("load", 0)
            load_color = "red" if load > 80 else "yellow" if load > 50 else "green"
            
            table.add_row(
                agent.get("name", "Unknown"),
                f"[{status_color}]●[/{status_color}] {status}",
                agent.get("current_task", "Idle"),
                f"[{load_color}]{load}%[/{load_color}]",
                agent.get("uptime", "0m")
            )
            
        return table

    def print_code_snippet(self, code: str, language: str = "python", title: str = None):
        """Print syntax-highlighted code snippet."""
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            background_color="default"
        )
        
        if title:
            panel = Panel(
                syntax,
                title=f"[bold yellow]{title}[/bold yellow]",
                box=box.ROUNDED,
                style="dim"
            )
            self.console.print(panel)
        else:
            self.console.print(syntax)

    def print_error(self, message: str, details: str = None):
        """Print an error message with styling."""
        error_text = f"[bold red]ERROR:[/bold red] {message}"
        if details:
            error_text += f"\n[dim red]{details}[/dim red]"
            
        panel = Panel(
            error_text,
            title="[bold red]⚠ Error[/bold red]",
            box=box.HEAVY,
            style="red",
            padding=(1, 2)
        )
        self.console.print(panel)

    def print_success(self, message: str):
        """Print a success message with styling."""
        panel = Panel(
            f"[bold green]✓ {message}[/bold green]",
            box=box.ROUNDED,
            style="green",
            padding=(0, 2)
        )
        self.console.print(panel)

    def print_warning(self, message: str):
        """Print a warning message with styling."""
        panel = Panel(
            f"[bold yellow]⚠ {message}[/bold yellow]",
            box=box.ROUNDED,
            style="yellow",
            padding=(0, 2)
        )
        self.console.print(panel)

    def create_dashboard(self, tasks: List[Dict], agents: List[Dict], stats: Dict[str, Any]):
        """Create a comprehensive dashboard view."""
        self.print_header("🤖 AI Agent Dashboard", f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Stats panels
        panels = []
        for key, value in stats.items():
            color = "green" if "success" in key.lower() else "red" if "error" in key.lower() else "blue"
            panels.append(
                Panel(
                    Align.center(f"[bold {color}]{value}[/bold {color}]\n[dim]{key.replace('_', ' ').title()}[/dim]"),
                    box=box.ROUNDED,
                    style=color,
                    width=15
                )
            )
        
        if panels:
            self.console.print(Columns(panels, equal=True, expand=True))
            self.console.print()
        
        # Tables
        if tasks:
            task_table = self.create_task_table(tasks)
            self.console.print(task_table)
            self.console.print()
            
        if agents:
            agent_table = self.create_agent_status_table(agents)
            self.console.print(agent_table)

    def progress_context(self, description: str = "Processing..."):
        """Create a progress context manager."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )

# Global formatter instance
formatter = RichFormatter()