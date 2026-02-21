#!/usr/bin/env python3
"""
Interactive demo of the AgentCoord UI system.

Shows both cyberpunk ASCII art and Rich terminal UI components.
"""

import time
import sys
from datetime import datetime
from ui.rich_formatter import RichFormatter, TaskStatus

def demo_cyberpunk():
    """Demo the cyberpunk ASCII art UI."""
    from cyberpunk_ui import CyberpunkUI, Colors

    ui = CyberpunkUI()

    # Clear screen
    print("\033[2J\033[H")

    # Show logo
    print(ui.agent_coord_logo())

    # Matrix rain effect
    print(f"\n{Colors.NEON_GREEN}INITIALIZING MATRIX CONNECTION...{Colors.RESET}")
    for _ in range(3):
        print(ui.matrix_rain_line(80))
        time.sleep(0.3)

    # Status panel
    status_content = [
        "SYSTEM STATUS: ONLINE",
        "AGENTS CONNECTED: 3",
        "LLM WORKERS: ACTIVE",
        "TASKS COMPLETED: 10",
        "CODE GENERATED: 3,832 LINES"
    ]
    print(ui.status_panel("AGENTCOORD CONTROL PANEL", status_content))

    # Loading demonstration
    print(f"\n{Colors.NEON_CYAN}SPAWNING LLM WORKERS...{Colors.RESET}")
    for i in range(0, 101, 10):
        print(f"\r{ui.loading_bar(i, 50, 'INITIALIZING')}", end="", flush=True)
        time.sleep(0.2)

    print(f"\n\n{Colors.NEON_GREEN}WORKERS READY{Colors.RESET}")
    print(ui.terminal_prompt(), end="")
    print("\n")


def demo_rich():
    """Demo the Rich terminal UI components."""
    formatter = RichFormatter()

    # Header
    formatter.print_header(
        "🤖 AGENTCOORD RICH UI DEMO",
        "Autonomous Multi-Agent Coordination System"
    )

    # Sample tasks with different statuses
    tasks = [
        {
            "id": "task-001",
            "name": "Design cyberpunk color scheme",
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "updated": datetime.now()
        },
        {
            "id": "task-002",
            "name": "Build MasterCoordinator architecture",
            "status": TaskStatus.RUNNING,
            "progress": 65,
            "updated": datetime.now()
        },
        {
            "id": "task-003",
            "name": "Implement budget allocation system",
            "status": TaskStatus.RUNNING,
            "progress": 45,
            "updated": datetime.now()
        },
        {
            "id": "task-004",
            "name": "Add live status dashboard",
            "status": TaskStatus.PENDING,
            "progress": 0,
            "updated": datetime.now()
        },
        {
            "id": "task-005",
            "name": "Create interactive prompts",
            "status": TaskStatus.PENDING,
            "progress": 0,
            "updated": datetime.now()
        }
    ]

    # Sample agents
    agents = [
        {
            "name": "UI-Worker-1",
            "status": "active",
            "current_task": "Building Rich panels",
            "load": 75,
            "uptime": "12m"
        },
        {
            "name": "UI-Worker-2",
            "status": "active",
            "current_task": "Creating progress bars",
            "load": 60,
            "uptime": "12m"
        },
        {
            "name": "Hierarchy-1",
            "status": "active",
            "current_task": "Implementing MasterCoordinator",
            "load": 85,
            "uptime": "11m"
        }
    ]

    # Stats
    stats = {
        "total_tasks": 10,
        "completed": 10,
        "running": 0,
        "agents_active": 3,
        "cost_usd": "$1.47"
    }

    # Show dashboard
    formatter.create_dashboard(tasks, agents, stats)

    # Success message
    print("\n")
    formatter.print_success("All LLM workers completed their tasks successfully!")

    # Code example
    print("\n")
    formatter.print_section(
        "Generated Code Example",
        "LLM workers autonomously generated 29 files with 3,832 lines of code",
        style="cyan"
    )

    sample_code = '''class MasterCoordinator:
    """Top-level orchestrator for hierarchical coordination."""

    def decompose_goal(self, goal: str) -> List[SubProject]:
        """Break high-level goal into sub-projects."""
        # LLM-generated implementation
        pass

    def allocate_budget(self, sub_projects: List[SubProject]) -> bool:
        """Validate and allocate budget across sub-projects."""
        # LLM-generated implementation
        pass'''

    formatter.print_code_snippet(sample_code, "python", "MasterCoordinator.py")


def demo_interactive():
    """Interactive menu to choose demo."""
    from rich.console import Console
    from rich.prompt import Prompt
    from rich.panel import Panel

    console = Console()

    console.print(Panel(
        "[bold cyan]Welcome to AgentCoord UI Demo[/bold cyan]\n\n"
        "This demo showcases the 90s cyberpunk aesthetic UI system\n"
        "built by autonomous LLM-powered agent workers.",
        title="🤖 AgentCoord",
        border_style="cyan",
        padding=(1, 2)
    ))

    while True:
        console.print("\n[bold]Choose a demo:[/bold]")
        console.print("  [cyan]1[/cyan] - Cyberpunk ASCII Art UI (Matrix vibes)")
        console.print("  [cyan]2[/cyan] - Rich Terminal UI (Modern formatted output)")
        console.print("  [cyan]3[/cyan] - Both (run them sequentially)")
        console.print("  [cyan]q[/cyan] - Quit")

        choice = Prompt.ask("\nYour choice", choices=["1", "2", "3", "q"], default="3")

        if choice == "q":
            console.print("\n[bold green]Thanks for trying AgentCoord! 🚀[/bold green]\n")
            break
        elif choice == "1":
            demo_cyberpunk()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        elif choice == "2":
            demo_rich()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        elif choice == "3":
            console.print("\n[bold cyan]Running Cyberpunk Demo...[/bold cyan]\n")
            demo_cyberpunk()
            console.print("\n[dim]Press Enter for Rich Demo...[/dim]")
            input()

            # Clear and show rich demo
            print("\033[2J\033[H")
            demo_rich()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()


if __name__ == "__main__":
    try:
        demo_interactive()
    except KeyboardInterrupt:
        print("\n\n[bold green]Goodbye! 🚀[/bold green]\n")
        sys.exit(0)
