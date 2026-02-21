"""
Example usage of interactive prompts in a real application scenario.
"""

from interactive_prompts import InteractivePrompts
from rich.console import Console
from rich.panel import Panel


def survey_application():
    """Example survey application using interactive prompts."""
    prompts = InteractivePrompts()
    console = Console()
    
    console.print(Panel(
        "[bold blue]Customer Feedback Survey[/bold blue]\n"
        "Help us improve our service by answering a few questions.",
        title="Welcome",
        border_style="blue"
    ))
    
    # Collect user information
    console.print("\n[bold]Step 1: Contact Information[/bold]")
    email = prompts.validated_email_input()
    phone = prompts.validated_phone_input()
    
    # Service selection
    console.print("\n[bold]Step 2: Service Information[/bold]")
    service_type = prompts.radio_select(
        "Which service did you use?",
        ["Web Development", "Mobile App", "Consulting", "Support", "Other"]
    )
    
    # Feature feedback
    features_used = prompts.multi_select_checkboxes(
        "Which features did you use? (Select all that apply)",
        ["User Dashboard", "Analytics", "API Integration", "Custom Reports", 
         "Mobile Access", "Team Collaboration", "Data Export"],
        min_selections=1
    )
    
    # Budget and rating
    console.print("\n[bold]Step 3: Evaluation[/bold]")
    budget = prompts.budget_slider(
        min_value=500, 
        max_value=10000, 
        step=250,
        currency="$"
    )
    
    overall_rating = prompts.rating_input(
        "Overall satisfaction with our service:",
        labels={
            1: "Very Unsatisfied", 
            2: "Unsatisfied", 
            3: "Neutral", 
            4: "Satisfied", 
            5: "Very Satisfied"
        }
    )
    
    # Progress confirmation
    steps = [
        "Contact Information",
        "Service Information", 
        "Evaluation",
        "Review & Submit"
    ]
    
    if prompts.progress_confirmation(steps, 4):
        # Summary
        console.print("\n[bold]Survey Summary:[/bold]")
        console.print(f"Email: {email}")
        console.print(f"Phone: {phone}")
        console.print(f"Service: {service_type}")
        console.print(f"Features Used: {', '.join(features_used)}")
        console.print(f"Budget Range: ${budget:,.0f}")
        console.print(f"Rating: {overall_rating}/5")
        
        # Final confirmation
        if prompts.confirmation_dialog