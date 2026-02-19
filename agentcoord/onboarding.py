"""
Onboarding wizard for first-time users.
"""
import os
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown

class OnboardingWizard:
    """Handles first-time user onboarding experience."""
    
    def __init__(self, console: Console, tui_instance):
        self.console = console
        self.tui = tui_instance
        self.config_dir = Path.home() / ".agentcoord"
        self.first_run_marker = self.config_dir / "first_run"
        self.config_file = self.config_dir / "config.json"
        
    def is_first_run(self) -> bool:
        """Check if this is the first run."""
        return not self.first_run_marker.exists()
    
    def mark_completed(self):
        """Mark onboarding as completed."""
        self.config_dir.mkdir(exist_ok=True)
        self.first_run_marker.touch()
        
    def load_config(self) -> dict:
        """Load user configuration."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except json.JSONDecodeError:
                pass
        return {}
    
    def save_config(self, config: dict):
        """Save user configuration."""
        self.config_dir.mkdir(exist_ok=True)
        self.config_file.write_text(json.dumps(config, indent=2))
    
    def show_welcome(self) -> bool:
        """Step 1: Show welcome message. Returns True if user wants to continue."""
        self.console.clear()
        
        welcome_text = """
# Welcome to AgentCoord! 🎉

AgentCoord is a powerful task coordination system that helps you:

- **Manage Tasks**: Create, track, and organize your work
- **Coordinate Workers**: Spawn AI agents to help complete tasks  
- **Monitor Progress**: Real-time updates and status tracking
- **Scale Efficiently**: Distribute work across multiple agents

This quick setup wizard will get you started in just a few steps.
        """
        
        panel = Panel(
            Markdown(welcome_text),
            title="🚀 Getting Started",
            border_style="bright_blue"
        )
        
        self.console.print(panel)
        self.console.print()
        
        choice = Prompt.ask(
            "Ready to get started?",
            choices=["yes", "skip", "never"],
            default="yes"
        )
        
        if choice == "never":
            config = self.load_config()
            config["skip_onboarding"] = True
            self.save_config(config)
            self.mark_completed()
            return False
        elif choice == "skip":
            return False
            
        return True
    
    def check_redis_connection(self) -> bool:
        """Step 2: Check Redis connection and offer to start if needed."""
        self.console.print("\n[bold blue]Step 2:[/] Checking Redis Connection")
        
        try:
            # Try to connect to Redis
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            self.console.print("✅ Redis is running and accessible!")
            return True
            
        except Exception as e:
            self.console.print(f"❌ Redis connection failed: {e}")
            
            if Confirm.ask("Would you like me to try starting Redis?"):
                try:
                    import subprocess
                    subprocess.Popen(["redis-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.console.print("🔄 Starting Redis server...")
                    
                    # Wait a moment and try again
                    import time
                    time.sleep(2)
                    
                    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
                    r.ping()
                    self.console.print("✅ Redis started successfully!")
                    return True
                    
                except Exception as start_error:
                    self.console.print(f"❌ Failed to start Redis: {start_error}")
                    self.console.print("Please start Redis manually: `redis-server`")
                    
        return Confirm.ask("Continue anyway?", default=True)
    
    def create_first_task(self) -> Optional[str]:
        """Step 3: Guide user through creating their first task."""
        self.console.print("\n[bold blue]Step 3:[/] Create Your First Task")
        
        self.console.print("Let's create a simple task to get you started!")
        
        # Offer some example tasks
        examples = Table(title="Example Tasks")
        examples.add_column("Type", style="cyan")
        examples.add_column("Description", style="white")
        
        examples.add_row("Research", "Research the latest AI developments")
        examples.add_row("Analysis", "Analyze sales data from last quarter")  
        examples.add_row("Writing", "Write a blog post about productivity")
        examples.add_row("Planning", "Plan a project timeline")
        
        self.console.print(examples)
        self.console.print()
        
        task_name = Prompt.ask("What would you like to work on?", 
                              default="Research the latest AI developments")
        
        if Confirm.ask(f"Create task: '{task_name}'?"):
            try:
                # Create the task using TUI's task manager
                task_id = self.tui.task_manager.create_task(
                    name=task_name,
                    description=f"First task created through onboarding wizard",
                    priority="medium"
                )
                self.console.print(f"✅ Created task: {task_name} (ID: {task_id})")
                return task_id
            except Exception as e:
                self.console.print(f"❌ Failed to create task: {e}")
        
        return None
    
    def spawn_first_worker(self, task_id: Optional[str] = None) -> bool:
        """Step 4: Guide user through spawning their first worker."""
        self.console.print("\n[bold blue]Step 4:[/] Spawn Your First Worker")
        
        if task_id:
            self.console.print(f"Let's spawn a worker to help with your task!")
        else:
            self.console.print("Let's spawn a worker to help with your tasks!")
        
        worker_types = Table(title="Worker Types")
        worker_types.add_column("Type", style="cyan")
        worker_types.add_column("Best For", style="white")
        
        worker_types.add_row("research", "Information gathering and analysis")
        worker_types.add_row("writer", "Content creation and documentation")
        worker_types.add_row("analyst", "Data analysis and insights")
        worker_types.add_row("general", "General purpose tasks")
        
        self.console.print(worker_types)
        self.console.print()
        
        worker_type = Prompt.ask("What type of worker?", 
                               choices=["research", "writer", "analyst", "general"],
                               default="general")
        
        if Confirm.ask(f"Spawn a {worker_type} worker?"):
            try:
                # Spawn worker using TUI's worker manager
                worker_id = self.tui.worker_manager.spawn_worker(
                    worker_type=worker_type,
                    task_filter=f"task:{task_id}" if task_id else None
                )
                self.console.print(f"✅ Spawned {worker_type} worker (ID: {worker_id})")
                return True
            except Exception as e:
                self.console.print(f"❌ Failed to spawn worker: {e}")
        
        return False
    
    def show_keyboard_shortcuts(self):
        """Step 5: Show keyboard shortcuts cheat sheet."""
        self.console.print("\n[bold blue]Step 5:[/] Keyboard Shortcuts")
        
        shortcuts = Table(title="🎹 Keyboard Shortcuts")
        shortcuts.add_column("Key", style="cyan", width=15)
        shortcuts.add_column("Action", style="white")
        
        shortcuts.add_row("q", "Quit AgentCoord")
        shortcuts.add_row("r", "Refresh display")
        shortcuts.add_row("h", "Show/hide help")
        shortcuts.add_row("t", "Focus task panel")
        shortcuts.add_row("w", "Focus worker panel")
        shortcuts.add_row("n", "Create new task")
        shortcuts.add_row("s", "Spawn new worker")
        shortcuts.add_row("Tab", "Switch between panels")
        shortcuts.add_row("Enter", "Select/activate item")
        shortcuts.add_row("Space", "Toggle item status")
        
        self.console.print(shortcuts)
        self.console.print()
        
        # Save tutorial mode preference
        tutorial_mode = Confirm.ask("Enable tutorial mode? (highlights actions for first 5 tasks)", default=True)
        
        config = self.load_config()
        config["tutorial_mode"] = tutorial_mode
        config["tutorial_tasks_remaining"] = 5 if tutorial_mode else 0
        self.save_config(config)
        
        self.console.print("\n🎉 [bold green]Setup Complete![/]")
        self.console.print("You're ready to start coordinating with AgentCoord!")
        
        Prompt.ask("\nPress Enter to continue...")
    
    def run_wizard(self) -> bool:
        """Run the complete onboarding wizard."""
        if not self.is_first_run():
            config = self.load_config()
            if config.get("skip_onboarding", False):
                return False
        
        try:
            # Step 1: Welcome
            if not self.show_welcome():
                return False
            
            # Step 2: Redis check
            if not self.check_redis_connection():
                if not Confirm.ask("Continue without Redis?"):
                    return False
            
            # Step 3: Create first task
            task_id = self.create_first_task()
            
            # Step 4: Spawn first worker
            self.spawn_first_worker(task_id)
            
            # Step 5: Show shortcuts
            self.show_keyboard_shortcuts()
            
            # Mark as completed
            self.mark_completed()
            return True
            
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Onboarding cancelled.[/]")
            return False
        except Exception as e:
            self.console.print(f"\n[red]Error during onboarding: {e}[/]")
            return False