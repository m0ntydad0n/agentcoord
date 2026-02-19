import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .interactive_prompts import InteractivePrompts
from .task_manager import TaskManager

@dataclass
class TaskData:
    title: str = ""
    description: str = ""
    priority: int = 1
    tags: List[str] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []

class TaskCreationWizard:
    def __init__(self, task_manager: TaskManager):
        self.prompts = InteractivePrompts()
        self.task_manager = task_manager
        self.task_data = TaskData()
        self.current_step = 1
        self.total_steps = 6
        
    def show_progress(self):
        """Display progress bar for current step"""
        progress = "=" * self.current_step + "-" * (self.total_steps - self.current_step)
        self.prompts.display_info(f"Step {self.current_step}/{self.total_steps} [{progress}]")
        
    def step_1_title(self) -> bool:
        """Step 1: Task title with validation"""
        self.show_progress()
        self.prompts.display_header("Task Title")
        
        while True:
            title = self.prompts.text_input(
                "Enter task title",
                default=self.task_data.title,
                required=True
            )
            
            if not title or len(title.strip()) == 0:
                self.prompts.display_error("Title cannot be empty")
                continue
                
            if len(title) > 100:
                self.prompts.display_error("Title must be 100 characters or less")
                continue
                
            # Check for duplicate titles
            existing_tasks = self.task_manager.get_all_tasks()
            if any(task.title.lower() == title.lower() for task in existing_tasks):
                self.prompts.display_warning("A task with this title already exists")
                if not self.prompts.confirm("Continue anyway?"):
                    continue
                    
            self.task_data.title = title.strip()
            return True
    
    def step_2_description(self) -> bool:
        """Step 2: Multi-line description"""
        self.show_progress()
        self.prompts.display_header("Task Description")
        
        description = self.prompts.multiline_text_input(
            "Enter task description (press Ctrl+D when finished)",
            default=self.task_data.description,
            placeholder="Detailed description of the task..."
        )
        
        self.task_data.description = description.strip()
        return True
    
    def step_3_priority(self) -> bool:
        """Step 3: Priority slider (1-5)"""
        self.show_progress()
        self.prompts.display_header("Task Priority")
        
        priority_labels = {
            1: "Very Low",
            2: "Low", 
            3: "Medium",
            4: "High",
            5: "Critical"
        }
        
        self.prompts.display_info("Priority levels:")
        for level, label in priority_labels.items():
            self.prompts.display_info(f"  {level} - {label}")
        
        priority = self.prompts.slider_input(
            "Select priority level",
            min_value=1,
            max_value=5,
            default=self.task_data.priority,
            step=1,
            show_value=lambda x: f"{x} ({priority_labels[x]})"
        )
        
        self.task_data.priority = priority
        return True
    
    def step_4_tags(self) -> bool:
        """Step 4: Tags selection with checkboxes"""
        self.show_progress()
        self.prompts.display_header("Task Tags")
        
        # Get existing tags from other tasks
        existing_tasks = self.task_manager.get_all_tasks()
        all_tags = set()
        for task in existing_tasks:
            all_tags.update(task.tags if hasattr(task, 'tags') else [])
        
        # Common predefined tags
        predefined_tags = ["urgent", "feature", "bug", "documentation", "testing", "research"]
        available_tags = sorted(list(all_tags.union(predefined_tags)))
        
        if available_tags:
            selected_tags = self.prompts.checkbox_input(
                "Select tags for this task",
                options=available_tags,
                selected=self.task_data.tags
            )
        else:
            selected_tags = []
        
        # Allow custom tags
        custom_tags = self.prompts.text_input(
            "Add custom tags (comma-separated)",
            default=",".join([tag for tag in self.task_data.tags if tag not in selected_tags])
        )
        
        if custom_tags:
            custom_tag_list = [tag.strip() for tag in custom_tags.split(",") if tag.strip()]
            selected_tags.extend(custom_tag_list)
        
        self.task_data.tags = list(set(selected_tags))  # Remove duplicates
        return True
    
    def step_5_dependencies(self) -> bool:
        """Step 5: Dependencies with autocomplete"""
        self.show_progress()
        self.prompts.display_header("Task Dependencies")
        
        existing_tasks = self.task_manager.get_all_tasks()
        available_tasks = [task.title for task in existing_tasks]
        
        if not available_tasks:
            self.prompts.display_info("No existing tasks found for dependencies")
            self.task_data.dependencies = []
            return True
        
        self.prompts.display_info("Select tasks that must be completed before this task:")
        
        selected_deps = self.prompts.checkbox_input(
            "Select dependencies",
            options=available_tasks,
            selected=self.task_data.dependencies,
            optional=True
        )
        
        self.task_data.dependencies = selected_deps or []
        return True
    
    def step_6_confirmation(self) -> bool:
        """Step 6: Confirmation and preview"""
        self.show_progress()
        self.prompts.display_header("Task Preview")
        
        # Display task summary
        self.prompts.display_info("Review your task:")
        self.prompts.display_box([
            f"Title: {self.task_data.title}",
            f"Description: {self.task_data.description[:100]}{'...' if len(self.task_data.description) > 100 else ''}",
            f"Priority: {self.task_data.priority}",
            f"Tags: {', '.join(self.task_data.tags) if self.task_data.tags else 'None'}",
            f"Dependencies: {', '.join(self.task_data.dependencies) if self.task_data.dependencies else 'None'}"
        ])
        
        return self.prompts.confirm("Create this task?", default=True)
    
    def run_wizard(self) -> Optional[Dict[str, Any]]:
        """Run the complete wizard"""
        self.prompts.display_header("Task Creation Wizard")
        self.prompts.display_info("Create a new task with guided steps")
        
        steps = [
            self.step_1_title,
            self.step_2_description, 
            self.step_3_priority,
            self.step_4_tags,
            self.step_5_dependencies,
            self.step_6_confirmation
        ]
        
        while self.current_step <= len(steps):
            try:
                # Show navigation options (except on first step)
                if self.current_step > 1:
                    nav_choice = self.prompts.menu_select(
                        "Navigation",
                        options=["Continue", "Back", "Cancel"],
                        default=0
                    )
                    
                    if nav_choice == 1:  # Back
                        if self.current_step > 1:
                            self.current_step -= 1
                        continue
                    elif nav_choice == 2:  # Cancel
                        if self.prompts.confirm("Are you sure you want to cancel?"):
                            return None
                        continue
                
                # Execute current step
                if steps[self.current_step - 1]():
                    self.current_step += 1
                else:
                    # Step failed, stay on current step
                    continue
                    
            except KeyboardInterrupt:
                if self.prompts.confirm("\nCancel task creation?"):
                    return None
                continue
        
        # Create the task
        task_dict = {
            "title": self.task_data.title,
            "description": self.task_data.description,
            "priority": self.task_data.priority,
            "tags": self.task_data.tags,
            "dependencies": self.task_data.dependencies,
            "status": "pending"
        }
        
        return task_dict

def create_task(task_manager: TaskManager = None) -> bool:
    """Interactive task creation function"""
    if task_manager is None:
        task_manager = TaskManager()
    
    wizard = TaskCreationWizard(task_manager)
    
    try:
        task_data = wizard.run_wizard()
        
        if task_data is None:
            wizard.prompts.display_warning("Task creation cancelled")
            return False
        
        # Create the task
        task = task_manager.create_task(
            title=task_data["title"],
            description=task_data["description"],
            priority=task_data["priority"],
            tags=task_data["tags"],
            dependencies=task_data["dependencies"]
        )
        
        wizard.prompts.display_success(f"Task '{task.title}' created successfully!")
        wizard.prompts.display_info(f"Task ID: {task.id}")
        
        return True
        
    except Exception as e:
        wizard.prompts.display_error(f"Failed to create task: {str(e)}")
        return False

# Integration function for command line
def create_task_command():
    """Command line entry point for task creation"""
    return create_task()