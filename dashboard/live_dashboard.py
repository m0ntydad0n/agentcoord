#!/usr/bin/env python3
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any
from collections import deque
import json
import threading
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import keyboard
import signal
import sys

class LiveDashboard:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.running = False
        self.refresh_rate = 0.5  # seconds
        
        # Data storage
        self.tasks = {}
        self.agents = {}
        self.logs = deque(maxlen=100)
        self.costs = {"total": 0.0, "current_session": 0.0}
        self.selected_pane = 0  # 0: tasks, 1: agents, 2: logs, 3: costs
        
        # Setup layout
        self._setup_layout()
        
        # Keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
    def _setup_layout(self):
        """Initialize the dashboard layout"""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        self.layout["left"].split_column(
            Layout(name="tasks"),
            Layout(name="agents")
        )
        
        self.layout["right"].split_column(
            Layout(name="logs"),
            Layout(name="costs")
        )
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard event handlers"""
        keyboard.add_hotkey('tab', self._next_pane)
        keyboard.add_hotkey('shift+tab', self._prev_pane)
        keyboard.add_hotkey('r', self._refresh)
        keyboard.add_hotkey('c', self._clear_logs)
        keyboard.add_hotkey('q', self._quit)
        keyboard.add_hotkey('ctrl+c', self._quit)
    
    def _next_pane(self):
        """Switch to next pane"""
        self.selected_pane = (self.selected_pane + 1) % 4
    
    def _prev_pane(self):
        """Switch to previous pane"""
        self.selected_pane = (self.selected_pane - 1) % 4
    
    def _refresh(self):
        """Force refresh display"""
        pass  # Handled by live update
    
    def _clear_logs(self):
        """Clear log entries"""
        self.logs.clear()
    
    def _quit(self):
        """Quit the dashboard"""
        self.running = False
        sys.exit(0)
    
    def _get_header(self) -> Panel:
        """Generate header panel"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = Text("🚀 Live Status Dashboard", style="bold blue")
        subtitle = Text(f"Last Updated: {current_time} | Press 'q' to quit, 'tab' to navigate", style="dim")
        
        header_text = Text()
        header_text.append(title)
        header_text.append("\n")
        header_text.append(subtitle)
        
        return Panel(header_text, style="blue")
    
    def _get_footer(self) -> Panel:
        """Generate footer panel with shortcuts"""
        shortcuts = [
            ("Tab", "Next Pane"),
            ("Shift+Tab", "Prev Pane"), 
            ("R", "Refresh"),
            ("C", "Clear Logs"),
            ("Q", "Quit")
        ]
        
        shortcut_text = Text()
        for i, (key, desc) in enumerate(shortcuts):
            if i > 0:
                shortcut_text.append(" | ")
            shortcut_text.append(f"{key}: {desc}", style="bold")
        
        return Panel(shortcut_text, title="Shortcuts", style="green")
    
    def _get_tasks_panel(self) -> Panel:
        """Generate tasks panel"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Progress")
        table.add_column("ETA")
        
        for task_id, task in self.tasks.items():
            status_style = {
                "running": "yellow",
                "completed": "green", 
                "failed": "red",
                "pending": "blue"
            }.get(task["status"], "white")
            
            progress_bar = f"{'█' * int(task['progress'] * 10 / 100)}{'░' * (10 - int(task['progress'] * 10 / 100))}"
            
            table.add_row(
                str(task_id)[:8],
                task["name"],
                f"[{status_style}]{task['status']}[/{status_style}]",
                f"{progress_bar} {task['progress']}%",
                task.get("eta", "N/A")
            )
        
        style = "bold white" if self.selected_pane == 0 else "white"
        return Panel(table, title="🔄 Tasks", border_style=style)
    
    def _get_agents_panel(self) -> Panel:
        """Generate agents panel"""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Agent", style="dim", width=12)
        table.add_column("Status")
        table.add_column("Current Task")
        table.add_column("CPU %")
        table.add_column("Memory")
        
        for agent_id, agent in self.agents.items():
            status_style = {
                "active": "green",
                "idle": "yellow",
                "error": "red"
            }.get(agent["status"], "white")
            
            table.add_row(
                agent_id,
                f"[{status_style}]{agent['status']}[/{status_style}]",
                agent.get("current_task", "None"),
                f"{agent.get('cpu_usage', 0):.1f}%",
                f"{agent.get('memory_usage', 0):.1f}MB"
            )
        
        style = "bold white" if self.selected_pane == 1 else "white"
        return Panel(table, title="🤖 Agents", border_style=style)
    
    def _get_logs_panel(self) -> Panel:
        """Generate logs panel"""
        log_text = Text()
        
        for log_entry in list(self.logs)[-20:]:  # Show last 20 entries
            timestamp = log_entry["timestamp"].strftime("%H:%M:%S")
            level = log_entry["level"]
            message = log_entry["message"]
            
            level_style = {
                "INFO": "blue",
                "WARNING": "yellow", 
                "ERROR": "red",
                "DEBUG": "dim"
            }.get(level, "white")
            
            log_text.append(f"[{timestamp}] ", style="dim")
            log_text.append(f"{level}: ", style=level_style)
            log_text.append(f"{message}\n")
        
        style = "bold white" if self.selected_pane == 2 else "white"
        return Panel(log_text, title="📋 Logs", border_style=style)
    
    def _get_costs_panel(self) -> Panel:
        """Generate costs panel"""
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Metric")
        table.add_column("Value")
        
        table.add_row("Total Cost", f"${self.costs['total']:.4f}")
        table.add_row("Session Cost", f"${self.costs['current_session']:.4f}")
        table.add_row("Avg per Task", f"${self._get_avg_cost_per_task():.4f}")
        table.add_row("Cost Rate", f"${self._get_cost_rate():.4f}/hr")
        
        style = "bold white" if self.selected_pane == 3 else "white"
        return Panel(table, title="💰 Costs", border_style=style)
    
    def _get_avg_cost_per_task(self) -> float:
        """Calculate average cost per task"""
        completed_tasks = len([t for t in self.tasks.values() if t["status"] == "completed"])
        return self.costs["total"] / max(completed_tasks, 1)
    
    def _get_cost_rate(self) -> float:
        """Calculate cost rate per hour"""
        # Simple estimation - would need actual session start time
        return self.costs["current_session"] * 2  # Assume 30min sessions
    
    def update_display(self) -> Layout:
        """Update the entire display"""
        self.layout["header"].update(self._get_header())
        self.layout["tasks"].update(self._get_tasks_panel())
        self.layout["agents"].update(self._get_agents_panel())
        self.layout["logs"].update(self._get_logs_panel())
        self.layout["costs"].update(self._get_costs_panel())
        self.layout["footer"].update(self._get_footer())
        
        return self.layout
    
    # API methods for updating data
    def add_task(self, task_id: str, name: str, status: str = "pending"):
        """Add or update a task"""
        self.tasks[task_id] = {
            "name": name,
            "status": status,
            "progress": 0,
            "eta": "N/A"
        }
    
    def update_task(self, task_id: str, **kwargs):
        """Update task properties"""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
    
    def add_agent(self, agent_id: str, status: str = "idle"):
        """Add or update an agent"""
        self.agents[agent_id] = {
            "status": status,
            "current_task": None,
            "cpu_usage": 0.0,
            "memory_usage": 0.0
        }
    
    def update_agent(self, agent_id: str, **kwargs):
        """Update agent properties"""
        if agent_id in self.agents:
            self.agents[agent_id].update(kwargs)
    
    def add_log(self, level: str, message: str):
        """Add a log entry"""
        self.logs.append({
            "timestamp": datetime.now(),
            "level": level,
            "message": message
        })
    
    def update_costs(self, total: float = None, session: float = None):
        """Update cost information"""
        if total is not None:
            self.costs["total"] = total
        if session is not None:
            self.costs["current_session"] = session
    
    def run(self):
        """Start the live dashboard"""
        self.running = True
        
        # Add some sample data
        self._load_sample_data()
        
        try:
            with Live(self.update_display(), refresh_per_second=int(1/self.refresh_rate)) as live:
                while self.running:
                    live.update(self.update_display())
                    time.sleep(self.refresh_rate)
                    
                    # Simulate some updates
                    self._simulate_updates()
                    
        except KeyboardInterrupt:
            self.running = False
    
    def _load_sample_data(self):
        """Load sample data for demonstration"""
        # Sample tasks
        self.add_task("task1", "Data Processing", "running")
        self.update_task("task1", progress=65, eta="5 min")
        
        self.add_task("task2", "Model Training", "completed")
        self.update_task("task2", progress=100)
        
        self.add_task("task3", "Report Generation", "pending")
        
        # Sample agents
        self.add_agent("agent1", "active")
        self.update_agent("agent1", current_task="task1", cpu_usage=85.5, memory_usage=512.3)
        
        self.add_agent("agent2", "idle")
        self.update_agent("agent2", cpu_usage=15.2, memory_usage=128.7)
        
        # Sample logs
        self.add_log("INFO", "Dashboard started successfully")
        self.add_log("INFO", "Agent1 started processing task1")
        self.add_log("WARNING", "High CPU usage detected on agent1")
        
        # Sample costs
        self.update_costs(total=12.4567, session=2.3456)
    
    def _simulate_updates(self):
        """Simulate real-time updates for demo"""
        import random
        
        # Update task progress
        for task_id, task in self.tasks.items():
            if task["status"] == "running" and task["progress"] < 100:
                task["progress"] = min(100, task["progress"] + random.randint(0, 3))
                if task["progress"] == 100:
                    task["status"] = "completed"
                    self.add_log("INFO", f"Task {task_id} completed")
        
        # Update agent stats
        for agent_id, agent in self.agents.items():
            if agent["status"] == "active":
                agent["cpu_usage"] = max(0, min(100, agent["cpu_usage"] + random.randint(-5, 5)))
                agent["memory_usage"] = max(0, agent["memory_usage"] + random.randint(-10, 10))
        
        # Add random log entries occasionally
        if random.randint(1, 10) == 1:
            levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
            messages = [
                "Processing batch data",
                "Memory usage optimized", 
                "Network connection stable",
                "Cache cleared successfully"
            ]
            self.add_log(random.choice(levels), random.choice(messages))
        
        # Update costs
        self.costs["current_session"] += random.uniform(0, 0.001)
        self.costs["total"] += random.uniform(0, 0.001)


if __name__ == "__main__":
    dashboard = LiveDashboard()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        dashboard.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Live Status Dashboard...")
    print("Press Ctrl+C to exit")
    
    dashboard.run()