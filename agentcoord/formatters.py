from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from typing import List, Dict, Any


class RichFormatter:
    """Rich formatting utilities for CLI output"""
    
    @staticmethod
    def create_task_table(tasks: List[Dict[str, Any]]) -> Panel:
        """Create a Rich table for displaying tasks with color coding and symbols"""
        
        # Status mappings
        STATUS_CONFIG = {
            'pending': {'color': 'yellow', 'symbol': '⏳'},
            'claimed': {'color': 'blue', 'symbol': '⚡'},
            'completed': {'color': 'green', 'symbol': '✅'},
            'failed': {'color': 'red', 'symbol': '❌'}
        }
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Status", style="white")
        table.add_column("Priority", style="white", justify="center")
        table.add_column("Worker", style="white")
        
        # Add rows
        for task in tasks:
            task_id = task.get('id', '')
            title = task.get('title', '')
            status = task.get('status', 'pending').lower()
            priority = str(task.get('priority', ''))
            claimed_by = task.get('claimed_by', '')
            
            # Get status config
            status_info = STATUS_CONFIG.get(status, STATUS_CONFIG['pending'])
            
            # Format status with symbol and color
            status_text = Text(f"{status_info['symbol']} {status.upper()}")
            status_text.stylize(status_info['color'])
            
            # Highlight high priority tasks
            priority_text = Text(priority)
            if priority and int(priority) >= 8:
                priority_text.stylize("bold red")
            elif priority and int(priority) >= 5:
                priority_text.stylize("bold yellow")
            
            table.add_row(
                task_id,
                title,
                status_text,
                priority_text,
                claimed_by
            )
        
        # Wrap in panel with border
        return Panel(
            table,
            title="[bold cyan]TASK QUEUE[/bold cyan]",
            border_style="blue",
            padding=(0, 1)
        )