#!/usr/bin/env python3
"""
CTO Coordinator for comprehensive codebase review.

Spawns specialized review teams in parallel:
- Security Team: Vulnerabilities, secrets, auth issues
- Architecture Team: Design patterns, modularity, scalability
- Performance Team: Efficiency, bottlenecks, optimization
- Quality Team: Code quality, testing, documentation
- DevOps Team: CI/CD, deployment, monitoring

Each team operates autonomously and reports findings.
"""

import os
import sys
import redis
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# Ensure API key
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    janus_env = os.path.expanduser('~/Desktop/Janus_Engine/.env')
    if os.path.exists(janus_env):
        with open(janus_env) as f:
            for line in f:
                if line.startswith('ANTHROPIC_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    os.environ['ANTHROPIC_API_KEY'] = api_key
                    break

if not api_key:
    console.print("[red]❌ ANTHROPIC_API_KEY not found[/red]")
    sys.exit(1)

# Connect to Redis
try:
    redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
    redis_client.ping()
except Exception as e:
    console.print(f"[red]❌ Cannot connect to Redis: {e}[/red]")
    sys.exit(1)

from agentcoord.tasks import TaskQueue
from agentcoord.spawner import WorkerSpawner, SpawnMode

# Display CTO header
console.clear()
console.print(Panel.fit(
    "[bold cyan]👔 CTO CODE REVIEW COORDINATOR[/bold cyan]\n"
    "[dim]Comprehensive AgentCoord Codebase Analysis[/dim]\n"
    "[yellow]Leading specialized review teams in parallel[/yellow]",
    border_style="cyan",
    padding=(1, 2)
))

console.print("\n[bold]Phase 1: Review Team Formation[/bold]")
console.print("=" * 80)

# Define specialized review tasks
review_tasks = [
    {
        'title': 'Security Review - Authentication & Authorization',
        'description': '''Conduct comprehensive security review of AgentCoord codebase.

Focus Areas:
1. Authentication mechanisms
   - Check llm.py, agent.py for auth implementation
   - Look for API key handling in spawner.py, examples/llm_worker_agent.py
   - Review Redis authentication if any

2. Authorization & Access Control
   - Check who can create/claim tasks
   - Review worker permissions
   - Look for privilege escalation risks

3. Secret Management
   - Search for hardcoded secrets, API keys
   - Review .env file handling
   - Check if secrets are logged or exposed

4. Input Validation
   - Review task.py for injection risks
   - Check CLI input validation
   - Review Redis data sanitization

5. Dependencies & Vulnerabilities
   - Check requirements.txt for known vulnerabilities
   - Review third-party library usage

Deliverable: Create security_review.md with findings, severity ratings, and fixes.
''',
        'priority': 5,
        'tags': ['security', 'review', 'auth', 'critical']
    },

    {
        'title': 'Architecture Review - Design Patterns & Scalability',
        'description': '''Review AgentCoord architecture for design quality and scalability.

Focus Areas:
1. System Architecture
   - Review CLAUDE.md architectural invariants
   - Check separation of concerns (pure engine vs adapters)
   - Evaluate coordinator/worker pattern implementation

2. Design Patterns
   - Identify patterns used (factory, observer, etc.)
   - Check for anti-patterns
   - Review code organization (cli.py, tasks.py, agent.py)

3. Scalability
   - Can system handle 100+ workers?
   - Redis as bottleneck?
   - Horizontal scaling possibilities

4. Modularity & Extensibility
   - How easy to add new worker types?
   - Plugin architecture for new features?
   - Review spawner.py extensibility

5. State Management
   - Review Redis schema design
   - Check for race conditions in task claiming
   - Evaluate determinism approach

Deliverable: Create architecture_review.md with design assessment and recommendations.
''',
        'priority': 5,
        'tags': ['architecture', 'review', 'design', 'scalability']
    },

    {
        'title': 'Performance Review - Efficiency & Optimization',
        'description': '''Analyze performance bottlenecks and optimization opportunities.

Focus Areas:
1. Redis Performance
   - Review Redis operations in tasks.py, agent.py
   - Check for N+1 queries
   - Evaluate connection pooling

2. Worker Efficiency
   - Review spawner.py worker lifecycle
   - Check polling intervals vs event-driven
   - Analyze LLM API call patterns

3. Code Hotspots
   - Profile task claiming logic
   - Review dashboard.py rendering performance
   - Check CLI command latency

4. Memory Usage
   - Look for memory leaks in long-running workers
   - Review data structure choices
   - Check for unnecessary object retention

5. Concurrency
   - Review thread safety
   - Check for race conditions
   - Evaluate async opportunities

Deliverable: Create performance_review.md with profiling data and optimization plan.
''',
        'priority': 4,
        'tags': ['performance', 'review', 'optimization', 'efficiency']
    },

    {
        'title': 'Code Quality Review - Testing & Documentation',
        'description': '''Assess code quality, test coverage, and documentation.

Focus Areas:
1. Test Coverage
   - Review tests/ directory structure
   - Check unit vs integration test balance
   - Identify untested critical paths
   - Review test quality (not just coverage %)

2. Code Quality
   - Check for code smells
   - Review function length, complexity
   - Look for duplicated code
   - Check type hints usage

3. Documentation
   - Review CLAUDE.md completeness
   - Check docstrings in core modules
   - Evaluate README clarity
   - Review inline comments quality

4. Error Handling
   - Check exception handling patterns
   - Review error messages clarity
   - Look for silent failures

5. Maintainability
   - Assess code readability
   - Check naming conventions
   - Review module coupling

Deliverable: Create quality_review.md with metrics and improvement plan.
''',
        'priority': 4,
        'tags': ['quality', 'review', 'testing', 'documentation']
    },

    {
        'title': 'DevOps Review - Deployment & Operations',
        'description': '''Review operational aspects and deployment readiness.

Focus Areas:
1. Configuration Management
   - Review config.py approach
   - Check environment variable handling
   - Evaluate configuration validation

2. Logging & Monitoring
   - Review logging practices
   - Check for structured logging
   - Evaluate observability

3. Deployment
   - Review setup.py, requirements.txt
   - Check for deployment documentation
   - Evaluate Docker readiness

4. Error Recovery
   - Review worker crash handling
   - Check Redis connection recovery
   - Evaluate graceful degradation

5. Operational Concerns
   - Review backup/restore needs
   - Check for monitoring hooks
   - Evaluate health check endpoints

Deliverable: Create devops_review.md with operational readiness assessment.
''',
        'priority': 3,
        'tags': ['devops', 'review', 'operations', 'deployment']
    },

    {
        'title': 'Integration Review - Cross-Component Analysis',
        'description': '''Review how components integrate and interact.

Focus Areas:
1. Component Interfaces
   - Review API contracts between modules
   - Check for tight coupling
   - Evaluate interface stability

2. Data Flow
   - Map data flow through system
   - Identify bottlenecks
   - Review serialization approach

3. Error Propagation
   - Check how errors flow through layers
   - Review error context preservation
   - Evaluate retry strategies

4. State Consistency
   - Review distributed state management
   - Check for eventual consistency issues
   - Evaluate transaction boundaries

5. Integration Points
   - Review Redis integration
   - Check LLM API integration
   - Evaluate external dependencies

Deliverable: Create integration_review.md with flow diagrams and findings.
''',
        'priority': 3,
        'tags': ['integration', 'review', 'components', 'interfaces']
    }
]

# Create review tasks
task_queue = TaskQueue(redis_client)

console.print("\n📋 Creating specialized review tasks...\n")

created_tasks = []
for task_data in review_tasks:
    task = task_queue.create_task(
        title=task_data['title'],
        description=task_data['description'],
        priority=task_data['priority'],
        tags=task_data['tags']
    )
    created_tasks.append(task)

    # Extract team name
    team_name = task_data['title'].split(' - ')[0]
    console.print(f"  ✅ {team_name}")

console.print(f"\n[bold green]✓ Created {len(created_tasks)} review tasks[/bold green]")

# Display review teams
console.print("\n[bold]Phase 2: Team Assignments[/bold]")
console.print("=" * 80)

teams_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
teams_table.add_column("Team", style="cyan", width=30)
teams_table.add_column("Focus", style="yellow")
teams_table.add_column("Priority", justify="center", width=8)

for task_data in review_tasks:
    team_name = task_data['title'].split(' - ')[0]
    focus = task_data['title'].split(' - ')[1] if ' - ' in task_data['title'] else 'General'
    priority = "⭐" * task_data['priority']
    teams_table.add_row(team_name, focus, priority)

console.print(teams_table)

# Spawn specialized workers
console.print("\n[bold]Phase 3: Worker Deployment[/bold]")
console.print("=" * 80)

spawner = WorkerSpawner(redis_url='redis://localhost:6379')

console.print(f"\n🚀 Spawning 6 specialized review workers...\n")

workers = []
worker_configs = [
    {'name': 'Security-Lead', 'tags': ['security', 'auth', 'critical']},
    {'name': 'Architect-Lead', 'tags': ['architecture', 'design', 'scalability']},
    {'name': 'Performance-Lead', 'tags': ['performance', 'optimization', 'efficiency']},
    {'name': 'Quality-Lead', 'tags': ['quality', 'testing', 'documentation']},
    {'name': 'DevOps-Lead', 'tags': ['devops', 'operations', 'deployment']},
    {'name': 'Integration-Lead', 'tags': ['integration', 'components', 'interfaces']}
]

for config in worker_configs:
    worker = spawner.spawn_worker(
        name=config['name'],
        tags=config['tags'] + ['review'],
        mode=SpawnMode.SUBPROCESS,
        use_llm=True,
        max_tasks=1,  # Each lead handles their specialty
        poll_interval=3
    )
    workers.append(worker)
    console.print(f"  ✅ {config['name']} deployed")

console.print(f"\n[bold green]✓ {len(workers)} review teams active[/bold green]")

# Monitoring
console.print("\n[bold]Phase 4: CTO Monitoring Dashboard[/bold]")
console.print("=" * 80)

console.print("""
[cyan]Review teams are now analyzing the codebase autonomously.[/cyan]

📊 Monitor progress:
   [yellow]agentcoord dashboard[/yellow]        # Live dashboard
   [yellow]agentcoord tasks[/yellow]            # Task status
   [yellow]agentcoord status[/yellow]           # Worker status

📝 Review outputs will be in:
   ./security_review.md
   ./architecture_review.md
   ./performance_review.md
   ./quality_review.md
   ./devops_review.md
   ./integration_review.md

⏱️  Estimated completion: 15-20 minutes
💰 Estimated cost: $2-4 (6 specialized reviews)

[dim]The CTO coordinator has delegated work to specialized teams.
Each team operates autonomously with domain expertise.[/dim]
""")

console.print("\n" + "=" * 80)
console.print("[bold green]🎯 Code review in progress - teams working in parallel![/bold green]")
console.print("=" * 80 + "\n")
