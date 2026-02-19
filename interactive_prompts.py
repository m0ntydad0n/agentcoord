"""
Interactive prompts with Rich library for better user input experience.
Includes radio buttons, sliders, confirmation dialogs, multi-select checkboxes,
and input validation with visual feedback.
"""

from typing import List, Optional, Any, Dict
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
import re


class InteractivePrompts:
    def __init__(self):
        self.console = Console()

    def radio_select(self, 
                    question: str, 
                    choices: List[str], 
                    default: Optional[int] = None) -> str:
        """Display radio button-style selection."""
        self.console.print(f"\n[bold blue]?[/bold blue] {question}")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("", style="cyan")
        table.add_column("", style="white")
        
        for i, choice in enumerate(choices, 1):
            marker = "●" if default == i else "○"
            table.add_row(f"{i}.", f"{marker} {choice}")
        
        self.console.print(table)
        
        while True:
            try:
                selection = IntPrompt.ask(
                    "Select option",
                    choices=[str(i) for i in range(1, len(choices) + 1)],
                    default=str(default) if default else None
                )
                return choices[selection - 1]
            except (ValueError, IndexError):
                self.console.print("[red]Invalid selection. Please try again.[/red]")

    def multi_select_checkboxes(self, 
                               question: str, 
                               choices: List[str],
                               min_selections: int = 0,
                               max_selections: Optional[int] = None) -> List[str]:
        """Display multi-select checkboxes."""
        self.console.print(f"\n[bold blue]?[/bold blue] {question}")
        self.console.print("[dim]Enter numbers separated by commas (e.g., 1,3,5) or 'all' for all options[/dim]")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("", style="cyan")
        table.add_column("", style="white")
        
        for i, choice in enumerate(choices, 1):
            table.add_row(f"{i}.", f"☐ {choice}")
        
        self.console.print(table)
        
        while True:
            try:
                user_input = Prompt.ask("Select options").strip().lower()
                
                if user_input == 'all':
                    selected_indices = list(range(len(choices)))
                elif user_input == '':
                    selected_indices = []
                else:
                    selected_indices = [int(x.strip()) - 1 for x in user_input.split(',')]
                    # Validate indices
                    for idx in selected_indices:
                        if idx < 0 or idx >= len(choices):
                            raise ValueError("Invalid option number")
                
                # Check constraints
                if len(selected_indices) < min_selections:
                    self.console.print(f"[red]Please select at least {min_selections} option(s).[/red]")
                    continue
                
                if max_selections and len(selected_indices) > max_selections:
                    self.console.print(f"[red]Please select at most {max_selections} option(s).[/red]")
                    continue
                
                selected_choices = [choices[i] for i in selected_indices]
                
                # Show confirmation
                if selected_choices:
                    self.console.print("\n[green]Selected:[/green]")
                    for choice in selected_choices:
                        self.console.print(f"  ✓ {choice}")
                else:
                    self.console.print("\n[yellow]No options selected[/yellow]")
                
                return selected_choices
                
            except (ValueError, IndexError):
                self.console.print("[red]Invalid input. Please enter valid option numbers.[/red]")

    def budget_slider(self, 
                     min_value: float = 0, 
                     max_value: float = 10000, 
                     step: float = 100,
                     currency: str = "$") -> float:
        """Simulate a budget slider with visual feedback."""
        self.console.print(f"\n[bold blue]?[/bold blue] Set your budget")
        self.console.print(f"[dim]Range: {currency}{min_value:,.0f} - {currency}{max_value:,.0f} (step: {currency}{step:,.0f})[/dim]")
        
        while True:
            try:
                value = FloatPrompt.ask(
                    f"Enter budget amount ({currency})",
                    default=min_value + (max_value - min_value) / 2
                )
                
                if value < min_value or value > max_value:
                    self.console.print(f"[red]Please enter a value between {currency}{min_value:,.0f} and {currency}{max_value:,.0f}[/red]")
                    continue
                
                # Round to nearest step
                value = round(value / step) * step
                
                # Visual representation
                percentage = (value - min_value) / (max_value - min_value)
                bar_length = 30
                filled_length = int(bar_length * percentage)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                
                self.console.print(f"\n[cyan]Budget: {currency}{value:,.0f}[/cyan]")
                self.console.print(f"[blue]│{bar}│[/blue] {percentage:.0%}")
                
                return value
                
            except ValueError:
                self.console.print("[red]Please enter a valid number.[/red]")

    def confirmation_dialog(self, 
                          message: str, 
                          title: Optional[str] = None,
                          style: str = "yellow") -> bool:
        """Display a styled confirmation dialog."""
        if title:
            panel_content = f"[bold]{title}[/bold]\n\n{message}"
        else:
            panel_content = message
        
        panel = Panel(
            panel_content,
            border_style=style,
            padding=(1, 2)
        )
        
        self.console.print(panel)
        return Confirm.ask("Do you want to continue?")

    def validated_email_input(self) -> str:
        """Email input with validation and visual feedback."""
        self.console.print("\n[bold blue]?[/bold blue] Enter your email address")
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        while True:
            email = Prompt.ask("Email")
            
            if re.match(email_pattern, email):
                self.console.print(f"[green]✓ Valid email: {email}[/green]")
                return email
            else:
                self.console.print("[red]✗ Invalid email format. Please try again.[/red]")

    def validated_phone_input(self) -> str:
        """Phone number input with validation."""
        self.console.print("\n[bold blue]?[/bold blue] Enter your phone number")
        self.console.print("[dim]Format: (123) 456-7890 or 123-456-7890[/dim]")
        
        phone_pattern = r'^(\(\d{3}\)\s?|\d{3}[-.]?)\d{3}[-.]?\d{4}$'
        
        while True:
            phone = Prompt.ask("Phone number")
            
            if re.match(phone_pattern, phone):
                self.console.print(f"[green]✓ Valid phone: {phone}[/green]")
                return phone
            else:
                self.console.print("[red]✗ Invalid phone format. Please try again.[/red]")

    def rating_input(self, 
                    question: str, 
                    min_rating: int = 1, 
                    max_rating: int = 5,
                    labels: Optional[Dict[int, str]] = None) -> int:
        """Star rating input with visual feedback."""
        self.console.print(f"\n[bold blue]?[/bold blue] {question}")
        
        if labels:
            for rating, label in labels.items():
                self.console.print(f"  {rating}: {label}")
        
        while True:
            try:
                rating = IntPrompt.ask(
                    f"Rating ({min_rating}-{max_rating})",
                    choices=[str(i) for i in range(min_rating, max_rating + 1)]
                )
                
                # Visual representation
                stars = "★" * rating + "☆" * (max_rating - rating)
                self.console.print(f"[yellow]{stars}[/yellow] ({rating}/{max_rating})")
                
                return rating
                
            except ValueError:
                self.console.print(f"[red]Please enter a number between {min_rating} and {max_rating}.[/red]")

    def progress_confirmation(self, steps: List[str], current_step: int) -> bool:
        """Show progress and confirm continuation."""
        self.console.print("\n[bold]Progress Overview[/bold]")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("", style="white", width=3)
        table.add_column("", style="white")
        table.add_column("", style="dim")
        
        for i, step in enumerate(steps, 1):
            if i < current_step:
                status = "[green]✓[/green]"
                step_style = "[green]"
            elif i == current_step:
                status = "[blue]●[/blue]"
                step_style = "[bold blue]"
            else:
                status = "[dim]○[/dim]"
                step_style = "[dim]"
            
            table.add_row(
                status,
                f"{step_style}{step}[/{step_style.split('[')[1]}]",
                f"Step {i}/{len(steps)}"
            )
        
        self.console.print(table)
        
        if current_step <= len(steps):
            return Confirm.ask(f"\nContinue to step {current_step}?", default=True)
        else:
            self.console.print("\n[green]All steps completed![/green]")
            return False


def demo():
    """Demonstration of all interactive prompt features."""
    prompts = InteractivePrompts()
    console = Console()
    
    console.print("[bold green]Interactive Prompts Demo[/bold green]")
    console.print("=" * 50)
    
    # Demo each prompt type
    try:
        # Radio selection
        theme = prompts.radio_select(
            "Choose your preferred theme:",
            ["Dark Mode", "Light Mode", "Auto", "High Contrast"],
            default=1
        )
        console.print(f"Selected theme: {theme}\n")
        
        # Multi-select checkboxes
        features = prompts.multi_select_checkboxes(
            "Select features to enable:",
            ["Notifications", "Auto-save", "Dark theme", "Analytics", "Backup"],
            min_selections=1,
            max_selections=3
        )
        console.print(f"Selected features: {', '.join(features)}\n")
        
        # Budget slider
        budget = prompts.budget_slider(min_value=100, max_value=5000, step=50)
        console.print(f"Budget set: ${budget:,.0f}\n")
        
        # Rating
        rating = prompts.rating_input(
            "How would you rate this experience?",
            labels={1: "Poor", 2: "Fair", 3: "Good", 4: "Very Good", 5: "Excellent"}
        )
        console.print(f"Rating: {rating}/5\n")
        
        # Email validation
        email = prompts.validated_email_input()
        
        # Confirmation dialog
        confirmed = prompts.confirmation_dialog(
            "All information has been collected successfully!\n"
            "Your preferences will be saved and applied immediately.",
            title="Save Configuration",
            style="green"
        )
        
        if confirmed:
            console.print("\n[bold green]✓ Configuration saved successfully![/bold green]")
        else:
            console.print("\n[yellow]Configuration cancelled.[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    demo()