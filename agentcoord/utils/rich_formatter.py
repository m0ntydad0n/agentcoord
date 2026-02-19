from rich.table import Table
from rich.text import Text
from rich.console import Console
from datetime import datetime, timedelta
import time

class RichFormatter:
    """Rich formatting utilities for agent coordination display"""
    
    @staticmethod
    def create_agent_status_table(agents):
        """Create a Rich table showing agent status information"""
        table = Table(
            title=None,
            show_header=True,
            header_style="bold bright_cyan",
            border_style="bright_black",
            row_styles=["", "dim"]
        )
        
        # Add columns
        table.add_column("Agent", style="bold white", min_width=15)
        table.add_column("Status", justify="center", min_width=8)
        table.add_column("Current Task", style="cyan", min_width=20)
        table.add_column("Load", justify="center", min_width=8)
        table.add_column("Uptime", justify="right", min_width=10)
        
        # Add agent rows
        for agent in agents:
            status_symbol, status_color = RichFormatter._get_status_display(agent.status)
            load_display = RichFormatter._format_load(agent.load if hasattr(agent, 'load') else 0.0)
            uptime_display = RichFormatter._format_uptime(agent.start_time if hasattr(agent, 'start_time') else time.time())
            current_task = getattr(agent, 'current_task', 'None') or 'None'
            
            table.add_row(
                agent.name,
                f"[{status_color}]{status_symbol}[/{status_color}]",
                current_task,
                load_display,
                uptime_display
            )
        
        return table
    
    @staticmethod
    def _get_status_display(status):
        """Get status symbol and color for display"""
        status_map = {
            'active': ('●', 'green'),
            'idle': ('◉', 'yellow'),
            'error': ('○', 'red'),
            'stopped': ('○', 'dim white'),
            'starting': ('◐', 'blue'),
            'stopping': ('◑', 'orange3')
        }
        return status_map.get(status.lower(), ('?', 'white'))
    
    @staticmethod
    def _format_load(load):
        """Format load percentage with color coding"""
        load_percent = int(load * 100) if isinstance(load, float) else int(load)
        
        if load_percent >= 80:
            return f"[red]{load_percent}%[/red]"
        elif load_percent >= 60:
            return f"[yellow]{load_percent}%[/yellow]"
        else:
            return f"[green]{load_percent}%[/green]"
    
    @staticmethod
    def _format_uptime(start_time):
        """Format uptime duration"""
        if not start_time:
            return "Unknown"
        
        uptime_seconds = time.time() - start_time
        uptime_delta = timedelta(seconds=int(uptime_seconds))
        
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    @staticmethod
    def create_loading_spinner(text="Loading..."):
        """Create a loading spinner with cyberpunk styling"""
        return Text(f"⚡ {text}", style="bold bright_cyan")