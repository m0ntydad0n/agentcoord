#!/usr/bin/env python3
"""
Create tasks for building a proper interactive TUI with good UX.

The current UI is passive (monitoring only). We need active interaction:
- Text entry for creating tasks
- Task management interface
- Agent control
- Interactive workflow
"""

import redis
import sys
from agentcoord.tasks import TaskQueue

# Connect to Redis
try:
    redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
    redis_client.ping()
except Exception as e:
    print(f"Error connecting to Redis: {e}")
    print("Start Redis with: brew services start redis")
    sys.exit(1)

task_queue = TaskQueue(redis_client)

# Define interactive UX tasks
interactive_ux_tasks = [
    {
        'title': 'Build main interactive TUI with keyboard navigation',
        'description': '''Create a full-screen interactive TUI using Rich's Layout and Live components.

Requirements:
1. Multi-panel layout:
   - Top: Task queue (scrollable list)
   - Middle: Task detail/editor pane
   - Bottom: Command bar with keybindings

2. Keyboard navigation:
   - Up/Down arrows: Navigate task list
   - Enter: Select/edit task
   - N: New task
   - D: Delete task
   - E: Edit task
   - Space: Toggle task status
   - Q: Quit
   - ?: Show help

3. Visual feedback:
   - Highlight selected task
   - Show current keybinding mode
   - Status bar with hints

4. Use Rich's components:
   - Layout for panels
   - Table for task list
   - Panel for details
   - Text for command bar

File: agentcoord/tui.py
Class: InteractiveTUI

Reference textual library patterns if helpful, but use Rich.
''',
        'priority': 5,
        'tags': ['tui', 'ux', 'interaction', 'keyboard']
    },

    {
        'title': 'Add inline task creation form in TUI',
        'description': '''Build a modal dialog for creating tasks directly in the TUI.

Requirements:
1. When user presses 'N', show modal overlay:
   - Title field (text input)
   - Description field (multi-line text area)
   - Priority selector (1-5, use arrow keys)
   - Tags field (comma-separated)

2. Field validation:
   - Title required (min 5 chars)
   - Description required (min 10 chars)
   - Priority must be 1-5
   - Tags optional

3. Navigation:
   - Tab/Shift+Tab: Move between fields
   - Enter: Submit (when valid)
   - Esc: Cancel

4. Visual feedback:
   - Show which field is active
   - Show validation errors in real-time
   - Preview task before creation

5. After creation:
   - Close modal
   - Refresh task list
   - Select newly created task

File: agentcoord/tui.py
Method: InteractiveTUI.show_create_task_modal()
''',
        'priority': 5,
        'tags': ['tui', 'forms', 'input', 'modal']
    },

    {
        'title': 'Add task detail view and inline editing',
        'description': '''Show selected task details and allow inline editing.

Requirements:
1. When task is selected, show in detail pane:
   - Full title
   - Full description (scrollable)
   - Priority (editable with +/-)
   - Tags (editable)
   - Status
   - Created/updated timestamps
   - Claimed by (if applicable)

2. Inline editing:
   - Press 'E' to edit mode
   - Edit title/description directly
   - Auto-save on blur or Ctrl+S
   - Esc to cancel

3. Quick actions:
   - C: Claim task
   - X: Complete task
   - F: Mark failed
   - D: Delete (with confirmation)

4. Visual hierarchy:
   - Clear separation of fields
   - Color-code by status
   - Show edit mode indicator

File: agentcoord/tui.py
Method: InteractiveTUI.show_task_details()
''',
        'priority': 5,
        'tags': ['tui', 'editing', 'ux']
    },

    {
        'title': 'Add command palette for quick actions',
        'description': '''Build a command palette (like VSCode Cmd+Shift+P) for quick actions.

Requirements:
1. Press '/' or ':' to open command palette
2. Fuzzy search commands:
   - "create task" → Create new task
   - "spawn worker" → Spawn new worker
   - "plan" → Run planning workflow
   - "export" → Export to file
   - "clear completed" → Clear completed tasks
   - "show stats" → Show statistics modal

3. Search functionality:
   - Type to filter commands
   - Arrow keys to select
   - Enter to execute
   - Esc to cancel

4. Show keyboard shortcuts next to commands
5. Remember recent commands (MRU)

File: agentcoord/tui.py
Method: InteractiveTUI.show_command_palette()
Class: CommandPalette
''',
        'priority': 4,
        'tags': ['tui', 'commands', 'search', 'ux']
    },

    {
        'title': 'Add agent control panel',
        'description': '''Create interactive agent management panel.

Requirements:
1. Accessible via Tab key or 'A' hotkey
2. Show agent list with:
   - Name
   - Status (color-coded)
   - Current task
   - Uptime
   - Tasks completed

3. Actions:
   - S: Spawn new worker (show modal with options)
   - K: Kill selected worker (with confirmation)
   - R: Restart worker
   - V: View worker logs

4. Spawn worker modal:
   - Name (auto-generated or custom)
   - Tags (multi-select)
   - Max tasks (slider or number)
   - LLM enabled (toggle)
   - Confirm and spawn

File: agentcoord/tui.py
Method: InteractiveTUI.show_agent_panel()
''',
        'priority': 4,
        'tags': ['tui', 'agents', 'control']
    },

    {
        'title': 'Add planning workflow integration',
        'description': '''Integrate the planning workflow into TUI.

Requirements:
1. Press 'P' to start planning workflow
2. Show modal with:
   - Pending tasks count
   - Optimization mode selector (Cost/Balanced/Quality)
   - Budget limit toggle and input
   - Estimated cost preview

3. Show plan preview:
   - Tasks to execute
   - Model assignments
   - Total cost/time estimates
   - Number of workers needed

4. Confirm or cancel
5. If confirmed:
   - Spawn workers
   - Return to main view
   - Show progress in real-time

File: agentcoord/tui.py
Method: InteractiveTUI.show_planning_workflow()
''',
        'priority': 3,
        'tags': ['tui', 'planning', 'workflow']
    },

    {
        'title': 'Add help modal with keyboard shortcuts',
        'description': '''Create comprehensive help modal.

Requirements:
1. Press '?' to show help
2. Tabbed interface:
   - Keyboard shortcuts
   - Getting started
   - Commands reference

3. Keyboard shortcuts organized by category:
   - Navigation
   - Task management
   - Agent control
   - Planning
   - Global

4. Searchable (type to filter)
5. Print-friendly view (Ctrl+P exports to text)

File: agentcoord/tui.py
Method: InteractiveTUI.show_help_modal()
''',
        'priority': 3,
        'tags': ['tui', 'help', 'documentation']
    },

    {
        'title': 'Add statistics and cost tracking modal',
        'description': '''Build comprehensive stats dashboard.

Requirements:
1. Press 'S' for statistics modal
2. Show:
   - Task statistics (total, completed, failed, pending)
   - Agent statistics (active, idle, total spawned)
   - Cost breakdown (by agent, by task, total)
   - Time statistics (avg task time, total uptime)
   - Success rate graphs (simple ASCII charts)

3. Export options:
   - JSON export
   - CSV export
   - Markdown report

4. Time range selector (Last hour, Today, All time)

File: agentcoord/tui.py
Method: InteractiveTUI.show_statistics_modal()
''',
        'priority': 2,
        'tags': ['tui', 'stats', 'analytics']
    },

    {
        'title': 'Add startup wizard for first-time users',
        'description': '''Create friendly onboarding experience.

Requirements:
1. Detect first run (check ~/.agentcoord/first_run marker)
2. Show welcome wizard:
   - Step 1: Welcome message explaining what AgentCoord is
   - Step 2: Check Redis connection (auto-start if needed)
   - Step 3: Create first task (guided)
   - Step 4: Spawn first worker (guided)
   - Step 5: Show keyboard shortcuts cheat sheet

3. Skip option on every step
4. "Don't show again" checkbox
5. Tutorial mode toggle (highlights actions for first 5 tasks)

File: agentcoord/tui.py
Method: InteractiveTUI.show_startup_wizard()
Class: OnboardingWizard
''',
        'priority': 2,
        'tags': ['tui', 'onboarding', 'ux']
    },

    {
        'title': 'Add CLI command to launch interactive TUI',
        'description': '''Make the TUI the default interactive interface.

Requirements:
1. Add 'agentcoord' command (no subcommand) to launch TUI
2. Add 'agentcoord interactive' as alias
3. Add flag '--tui' to other commands to launch in TUI mode
4. Graceful fallback to CLI if TUI fails
5. Detect terminal capabilities and warn if not supported

Changes:
- agentcoord/cli.py: Add tui command
- agentcoord/__main__.py: Default to TUI if no args

Make it the primary interface - CLI commands become secondary.
''',
        'priority': 5,
        'tags': ['cli', 'integration', 'tui']
    }
]

# Create tasks
print(f"Creating {len(interactive_ux_tasks)} tasks for interactive TUI with great UX...\n")

created_tasks = []
for task_data in interactive_ux_tasks:
    task = task_queue.create_task(
        title=task_data['title'],
        description=task_data['description'],
        priority=task_data['priority'],
        tags=task_data['tags']
    )
    created_tasks.append(task)
    print(f"✅ Created: {task.title} (priority {task.priority})")

print(f"\n✅ Created {len(created_tasks)} tasks")
print(f"\nGoal: Build a REAL interactive TUI where users can actually DO things:")
print(f"  • Create tasks with text entry")
print(f"  • Edit tasks inline")
print(f"  • Control agents")
print(f"  • Run workflows")
print(f"  • Navigate with keyboard")
print(f"\nNot just watching - actual interaction!")
print(f"\nNext: Spawn LLM workers to build it")
print(f"  python3 scripts/spawn_ui_workers.py")
