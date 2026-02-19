"""
Spawn parallel development teams using agentcoord.

Team 1: Rich Terminal UI (90s cyberpunk aesthetic)
Team 2: Hierarchical Coordination

Demonstrating agentcoord building agentcoord.
"""

import redis
from agentcoord.tasks import TaskQueue

# Connect to Redis
redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
redis_client.ping()

# Clear old tasks
redis_client.flushdb()
print("✅ Redis cleared\n")

task_queue = TaskQueue(redis_client)

print("🎯 Creating parallel development tasks...\n")

# ============================================================================
# TEAM 1: RICH TERMINAL UI (90s Cyberpunk Aesthetic)
# ============================================================================

ui_tasks = [
    {
        'title': 'Design cyberpunk color scheme and ASCII art',
        'description': '''Create 90s-inspired terminal aesthetic:
        - Neon green/cyan/magenta color palette
        - ASCII art logo for AgentCoord
        - Matrix-style characters and glyphs
        - Retro-futuristic borders and panels
        - Think: WarGames, Hackers, The Matrix''',
        'priority': 5,
        'tags': ['ui', 'design', 'ascii-art']
    },
    {
        'title': 'Implement Rich panels and tables',
        'description': '''Add Rich library formatting:
        - Color-coded task status (red/yellow/green)
        - Bordered panels for sections
        - Tables for task lists and agent status
        - Syntax highlighting for code snippets
        - Professional yet retro styling''',
        'priority': 5,
        'tags': ['ui', 'rich', 'formatting']
    },
    {
        'title': 'Add progress bars and live spinners',
        'description': '''Real-time visual feedback:
        - Progress bars for task execution
        - Animated spinners during waiting
        - Live percentage updates
        - ETA calculations
        - Pulsing effects for active workers''',
        'priority': 4,
        'tags': ['ui', 'progress', 'animation']
    },
    {
        'title': 'Create live status dashboard',
        'description': '''Build live-updating terminal dashboard:
        - Auto-refreshing status display
        - Multi-pane layout (tasks, agents, logs)
        - Streaming log output
        - Real-time cost tracking
        - Keyboard shortcuts for navigation''',
        'priority': 4,
        'tags': ['ui', 'dashboard', 'live-updates']
    },
    {
        'title': 'Build interactive prompts with Rich',
        'description': '''Better user input experience:
        - Radio button selections
        - Slider for budget input
        - Confirmation dialogs
        - Multi-select checkboxes
        - Input validation with visual feedback''',
        'priority': 3,
        'tags': ['ui', 'prompts', 'input']
    },
]

print("📺 TEAM 1: Rich Terminal UI")
for task_data in ui_tasks:
    task = task_queue.create_task(**task_data)
    print(f"   ✅ {task.title}")

print()

# ============================================================================
# TEAM 2: HIERARCHICAL COORDINATION
# ============================================================================

hierarchy_tasks = [
    {
        'title': 'Design MasterCoordinator architecture',
        'description': '''Top-level orchestrator design:
        - Define MasterCoordinator class interface
        - Project decomposition algorithm
        - Budget allocation strategy
        - Sub-coordinator spawning logic
        - Progress aggregation from children''',
        'priority': 5,
        'tags': ['hierarchy', 'architecture', 'coordinator']
    },
    {
        'title': 'Design SubCoordinator architecture',
        'description': '''Middle-tier coordinator design:
        - Define SubCoordinator class interface
        - Task breakdown from sub-project
        - Worker team management
        - Upward status reporting
        - Peer coordinator communication''',
        'priority': 5,
        'tags': ['hierarchy', 'architecture', 'coordinator']
    },
    {
        'title': 'Implement hierarchy Redis schema',
        'description': '''Multi-level coordination data structures:
        - Coordinator registry (master, sub, worker)
        - Parent-child relationships
        - Budget cascade tracking
        - Progress roll-up queries
        - Escalation chains''',
        'priority': 4,
        'tags': ['hierarchy', 'redis', 'schema']
    },
    {
        'title': 'Build budget allocation system',
        'description': '''Hierarchical budget management:
        - Top-down budget distribution
        - Dynamic reallocation based on progress
        - Budget enforcement at each level
        - Usage tracking and reporting
        - Alert on budget threshold''',
        'priority': 4,
        'tags': ['hierarchy', 'budget', 'allocation']
    },
    {
        'title': 'Implement progress aggregation',
        'description': '''Bottom-up status reporting:
        - Worker → Sub-coordinator progress
        - Sub-coordinator → Master progress
        - Weighted progress calculations
        - Bottleneck detection
        - Real-time dashboard updates''',
        'priority': 3,
        'tags': ['hierarchy', 'progress', 'aggregation']
    },
]

print("🏢 TEAM 2: Hierarchical Coordination")
for task_data in hierarchy_tasks:
    task = task_queue.create_task(**task_data)
    print(f"   ✅ {task.title}")

print()

# ============================================================================
# SUMMARY
# ============================================================================

all_tasks = task_queue.list_pending_tasks()

print("=" * 70)
print(f"🚀 SPAWNED {len(all_tasks)} TASKS ACROSS 2 PARALLEL TEAMS")
print("=" * 70)
print()
print("Team 1 (UI):        5 tasks | Focus: 90s cyberpunk terminal aesthetic")
print("Team 2 (Hierarchy): 5 tasks | Focus: Multi-tier orchestration")
print()
print("Next steps:")
print("  agentcoord-plan estimate  # See cost breakdown")
print("  agentcoord-plan plan      # Generate execution plan")
print("  agentcoord tasks          # View task queue")
print()
