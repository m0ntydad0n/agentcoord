# Add these imports at the top
from .onboarding import OnboardingWizard

class InteractiveTUI:
    def __init__(self):
        self.console = Console()
        self.task_manager = TaskManager()
        self.worker_manager = WorkerManager()
        self.running = True
        self.current_panel = "tasks"
        self.onboarding_wizard = OnboardingWizard(self.console, self)
        
        # Tutorial mode state
        self.tutorial_mode = False
        self.tutorial_tasks_remaining = 0
        self._load_tutorial_state()
    
    def _load_tutorial_state(self):
        """Load tutorial mode state from config."""
        try:
            config = self.onboarding_wizard.load_config()
            self.tutorial_mode = config.get("tutorial_mode", False)
            self.tutorial_tasks_remaining = config.get("tutorial_tasks_remaining", 0)
            
            # Disable tutorial mode if no tasks remaining
            if self.tutorial_tasks_remaining <= 0:
                self.tutorial_mode = False
        except Exception:
            pass
    
    def _update_tutorial_state(self):
        """Update tutorial state after completing an action."""
        if self.tutorial_mode and self.tutorial_tasks_remaining > 0:
            self.tutorial_tasks_remaining -= 1
            config = self.onboarding_wizard.load_config()
            config["tutorial_tasks_remaining"] = self.tutorial_tasks_remaining
            
            if self.tutorial_tasks_remaining <= 0:
                config["tutorial_mode"] = False
                self.tutorial_mode = False
                self.console.print("\n🎓 [bold green]Tutorial completed![/] You're now an AgentCoord pro!")
            
            self.onboarding_wizard.save_config(config)
    
    def show_startup_wizard(self) -> bool:
        """Show the startup wizard for first-time users."""
        return self.onboarding_wizard.run_wizard()
    
    def show_tutorial_hint(self, action: str):
        """Show tutorial hints if tutorial mode is enabled."""
        if not self.tutorial_mode or self.tutorial_tasks_remaining <= 0:
            return
        
        hints = {
            "create_task": "💡 Use 'n' to create new tasks quickly!",
            "spawn_worker": "💡 Press 's' to spawn workers for your tasks!",
            "select_item": "💡 Use Enter to select items and Space to toggle status!",
            "switch_panels": "💡 Use Tab to switch between task and worker panels!",
            "refresh": "💡 Press 'r' to refresh the display anytime!"
        }
        
        hint = hints.get(action)
        if hint:
            self.console.print(f"\n[yellow]{hint}[/]")
            self.console.print(f"[dim]Tutorial: {self.tutorial_tasks_remaining} actions remaining[/]")
    
    def run(self):
        """Main TUI loop with onboarding support."""
        # Check if we should show the startup wizard
        if self.onboarding_wizard.is_first_run():
            if self.show_startup_wizard():
                self.console.clear()
                self._load_tutorial_state()  # Reload tutorial state after wizard
        
        # Show initial tutorial hint
        if self.tutorial_mode:
            self.show_tutorial_hint("create_task")
        
        # Main loop
        while self.running:
            try:
                self.render()
                self.handle_input()
            except KeyboardInterrupt:
                break
        
        self.console.print("\n[yellow]Goodbye![/]")
    
    def handle_input(self):
        """Enhanced input handling with tutorial support."""
        # Get user input (existing implementation)
        key = self._get_key_input()
        
        # Handle tutorial hints
        if key == 'n':  # Create new task
            self.show_tutorial_hint("create_task")
            # ... existing create task logic ...
            self._update_tutorial_state()
            
        elif key == 's':  # Spawn worker
            self.show_tutorial_hint("spawn_worker")
            # ... existing spawn worker logic ...
            self._update_tutorial_state()
            
        elif key == '\t':  # Switch panels
            self.show_tutorial_hint("switch_panels")
            # ... existing panel switch logic ...
            
        elif key == '\r' or key == '\n':  # Select item
            self.show_tutorial_hint("select_item")
            # ... existing select logic ...
            self._update_tutorial_state()
            
        elif key == 'r':  # Refresh
            self.show_tutorial_hint("refresh")
            # ... existing refresh logic ...
            
        # ... rest of existing input handling ...
    
    def render_header(self):
        """Enhanced header rendering with tutorial mode indicator."""
        title = "AgentCoord - Task Coordination System"
        
        if self.tutorial_mode and self.tutorial_tasks_remaining > 0:
            title += f" [Tutorial: {self.tutorial_tasks_remaining} remaining]"
        
        header = Panel(title, style="bold blue")
        self.console.