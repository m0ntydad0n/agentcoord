#!/usr/bin/env python3
"""
Create tasks for integrating the cyberpunk Rich UI into agentcoord CLI.

This script defines the work needed to make the UI system usable.
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

# Define integration tasks
ui_integration_tasks = [
    {
        'title': 'Add live dashboard command to CLI',
        'description': '''Add a new `dashboard` command to agentcoord/cli.py that launches the AgentCoordDashboard.

Requirements:
- Import AgentCoordDashboard from agentcoord.dashboard
- Add @cli.command() for `dashboard`
- Pass Redis client to dashboard
- Add --refresh-rate option (default 0.5)
- Handle keyboard interrupt gracefully
- Show message on startup

Example:
```python
@cli.command()
@click.option('--refresh-rate', default=0.5, help='Dashboard refresh rate in seconds')
@click.pass_context
def dashboard(ctx, refresh_rate):
    """Launch live monitoring dashboard with cyberpunk UI."""
    if ctx.obj['mode'] == 'file':
        click.echo("Dashboard requires Redis connection")
        return

    from .dashboard import AgentCoordDashboard
    dash = AgentCoordDashboard(ctx.obj['redis'], refresh_rate=refresh_rate)
    dash.run()
```

File to modify: agentcoord/cli.py
''',
        'priority': 5,
        'tags': ['ui', 'cli', 'integration']
    },

    {
        'title': 'Enhance agentcoord-plan with Rich UI',
        'description': '''Replace plain text output in agentcoord/interactive_cli.py with Rich formatted panels and tables.

Requirements:
1. Import RichFormatter from ui.rich_formatter
2. Replace click.echo() calls with Rich panels:
   - Header with cyberpunk logo
   - Task list as Rich table with color-coded status
   - Optimization mode selection with styled prompts
   - Execution plan as formatted panel
   - Progress updates with spinners

3. Use cyberpunk theme from ui/theme.py
4. Add progress bars for agent spawning
5. Show real-time status updates

File to modify: agentcoord/interactive_cli.py
Functions to enhance: plan(), create_task(), estimate()
''',
        'priority': 5,
        'tags': ['ui', 'planning', 'rich']
    },

    {
        'title': 'Replace tasks command with Rich table',
        'description': '''Replace plain text task listing in cli.py with Rich formatted table.

Requirements:
- Use RichFormatter.create_task_table()
- Show color-coded status (pending=yellow, claimed=blue, completed=green, failed=red)
- Add status symbols (⏳ ⚡ ✅ ❌)
- Include priority highlighting
- Show claimed_by worker if applicable
- Add panel border with title "TASK QUEUE"

File to modify: agentcoord/cli.py
Function: tasks()

Expected output:
╔═══════════════════════════════ TASK QUEUE ═══════════════════════════════╗
║ ID       │ Title                │ Status      │ Priority │ Worker        ║
║──────────┼──────────────────────┼─────────────┼──────────┼───────────────║
║ abc123   │ Implement feature    │ ⚡ CLAIMED  │ 5        │ Worker-1      ║
╚═══════════════════════════════════════════════════════════════════════════╝
''',
        'priority': 4,
        'tags': ['ui', 'cli', 'tasks']
    },

    {
        'title': 'Replace status command with Rich panels',
        'description': '''Replace plain text agent status with Rich agent status table.

Requirements:
- Use RichFormatter.create_agent_status_table()
- Show agent name, status (●/◉/○), current task, load, uptime
- Color-code status: active=green, idle=yellow, error=red
- Add summary panel with total agents, active count
- Include cyberpunk border styling

File to modify: agentcoord/cli.py
Function: status()
''',
        'priority': 4,
        'tags': ['ui', 'cli', 'agents']
    },

    {
        'title': 'Add interactive task creation wizard',
        'description': '''Create rich interactive wizard for creating tasks using interactive_prompts.py.

Requirements:
- Use InteractivePrompts class for input
- Multi-step wizard:
  1. Task title (validated input)
  2. Description (multi-line text editor)
  3. Priority slider (1-5)
  4. Tags (multi-select checkboxes)
  5. Dependencies (optional, autocomplete from existing tasks)
  6. Confirmation screen with summary

- Show progress through wizard steps
- Allow back/cancel at any step
- Preview final task before creating
- Integrate into agentcoord-plan create-task command

File to modify: agentcoord/interactive_cli.py
Function: create_task()
''',
        'priority': 3,
        'tags': ['ui', 'wizard', 'tasks']
    },

    {
        'title': 'Add cyberpunk splash screen to CLI startup',
        'description': '''Add cyberpunk ASCII logo splash screen when running agentcoord commands.

Requirements:
- Show AGENTCOORD ASCII logo from ui/theme.py on first command
- Only show once per session (use environment variable or file marker)
- Add system status line: Redis connection, agent count, task count
- Use matrix rain effect for 0.5 seconds
- Make it skippable with --no-splash flag

File to modify: agentcoord/cli.py
Function: cli() (main entrypoint)

Use LOGO_ASCII_SMALL for compact display.
''',
        'priority': 2,
        'tags': ['ui', 'splash', 'aesthetic']
    },

    {
        'title': 'Fix dashboard rendering bugs',
        'description': '''Fix issues in agentcoord/dashboard.py rendering logic.

Known issues:
1. render_agents() tries to concatenate Table object with Text - fix to use proper Rich layout
2. Need to handle empty agent/task lists gracefully
3. Add error handling for Redis connection issues
4. Fix stats display when no cost data available

Requirements:
- Use proper Rich Layout for combining components
- Add try/except for Redis operations
- Show friendly message when no data available
- Test with empty queues

File to modify: agentcoord/dashboard.py
''',
        'priority': 5,
        'tags': ['bugfix', 'dashboard', 'ui']
    },

    {
        'title': 'Add export command for dashboard screenshot',
        'description': '''Add ability to export dashboard view to SVG or HTML.

Requirements:
- Use Rich console.export_svg() or export_html()
- Add --export flag to dashboard command
- Save to agentcoord_dashboard_{timestamp}.svg
- Include option for single snapshot vs continuous capture
- Add to documentation

File to modify: agentcoord/dashboard.py
New function: export_snapshot()
''',
        'priority': 2,
        'tags': ['export', 'dashboard', 'enhancement']
    }
]

# Create tasks
print(f"Creating {len(ui_integration_tasks)} tasks for UI integration...\n")

created_tasks = []
for task_data in ui_integration_tasks:
    task = task_queue.create_task(
        title=task_data['title'],
        description=task_data['description'],
        priority=task_data['priority'],
        tags=task_data['tags']
    )
    created_tasks.append(task)
    print(f"✅ Created: {task.title} (priority {task.priority})")

print(f"\n✅ Created {len(created_tasks)} tasks")
print(f"\nNext steps:")
print(f"  1. View tasks: agentcoord tasks")
print(f"  2. Plan execution: agentcoord-plan plan")
print(f"  3. Or spawn workers directly: python -m agentcoord.spawner")
