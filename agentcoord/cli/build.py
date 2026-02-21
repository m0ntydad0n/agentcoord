"""Build command - autonomous parallel implementation from a single prompt."""

import click
import sys
import os
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
from anthropic import Anthropic
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.command()
@click.argument('request', required=True)
@click.option('--workspace', default='.', help='Workspace directory')
@click.option('--max-workers', default=5, type=int, help='Maximum parallel workers')
@click.option('--model', default='sonnet', type=click.Choice(['haiku', 'sonnet', 'opus']))
@click.option('--docs-dir', default='docs', help='Directory containing design docs')
def build(request: str, workspace: str, max_workers: int, model: str, docs_dir: str):
    """
    Autonomous parallel implementation from a single high-level prompt.

    Takes one description of what to build and handles everything:
    - Discovers relevant design docs
    - Plans implementation with dependencies
    - Spawns parallel workers
    - Coordinates execution
    - Tests and validates
    - Reports results

    Example:
        agentcoord build "Implement the role system and workflow router from design docs"

    Example:
        agentcoord build "Build everything specified in docs/role_api_design.md"
    """
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("❌ Error: ANTHROPIC_API_KEY not set", style="red")
        console.print("   Set it with: export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Expand paths
    workspace_path = Path(workspace).expanduser().resolve()
    docs_path = workspace_path / docs_dir

    if not docs_path.exists():
        console.print(f"❌ Docs directory not found: {docs_path}", style="red")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold cyan]AGENTCOORD BUILD[/bold cyan]\n\n"
        f"[yellow]Request:[/yellow] {request}\n"
        f"[dim]Workspace: {workspace_path}[/dim]\n"
        f"[dim]Max Workers: {max_workers}[/dim]",
        border_style="cyan"
    ))

    # Step 1: Discover and read design docs
    console.print("\n[bold]Step 1:[/bold] Discovering design documents...")

    design_docs = list(docs_path.glob("*.md"))
    if not design_docs:
        console.print(f"❌ No design docs found in {docs_path}", style="red")
        sys.exit(1)

    console.print(f"Found {len(design_docs)} design documents:")
    for doc in design_docs:
        console.print(f"  📄 {doc.name}")

    # Read all design docs
    docs_content = {}
    for doc in design_docs:
        with open(doc, 'r') as f:
            docs_content[doc.name] = f.read()

    # Step 2: Plan implementation
    console.print("\n[bold]Step 2:[/bold] Creating implementation plan...")

    planning_prompt = f"""You are a senior software architect planning a complex implementation.

USER REQUEST:
{request}

AVAILABLE DESIGN DOCUMENTS:
{chr(10).join(f"- {name}: {len(content)} bytes" for name, content in docs_content.items())}

DESIGN DOCUMENT CONTENTS:
{chr(10).join(f"=== {name} ==={chr(10)}{content}{chr(10)}" for name, content in docs_content.items())}

YOUR JOB:
Analyze the request and design docs, then create a complete implementation plan.

OUTPUT FORMAT (JSON only):
{{
  "summary": "Brief description of what will be built",
  "tasks": [
    {{
      "id": "task-1",
      "title": "Short task title",
      "description": "Complete description of what to implement",
      "spec_file": "which design doc to use",
      "spec_section": "which section/lines of the spec",
      "target_file": "file to create/modify (relative to workspace)",
      "action": "CREATE or MODIFY",
      "dependencies": ["task-2"],
      "test_command": "pytest command to validate",
      "complexity": 1-3 (1=simple/Haiku, 2=moderate/Sonnet, 3=complex/Opus),
      "estimated_minutes": 5-30
    }}
  ],
  "total_estimated_time": "minutes for all tasks",
  "parallelization": {{
    "wave_1": ["task-1", "task-2"],
    "wave_2": ["task-3"],
    "wave_3": ["task-4", "task-5"]
  }}
}}

PLANNING GUIDELINES:
1. Break into atomic tasks (one class/module per task)
2. Identify dependencies (Task B needs Task A complete first)
3. Create parallel waves (tasks with no interdependencies)
4. Assign complexity based on cognitive demand
5. Include test command for each task
6. Specify exact file paths and spec references
7. Order tasks so dependencies come first

IMPORTANT:
- Each task must be independently executable
- Dependencies must be explicit (if Task 3 needs Task 1, say so)
- Test commands must be specific and runnable
- File paths must be precise (e.g., "agentcoord/roles.py")
- Spec references must include section/line numbers

Return ONLY valid JSON, no other text."""

    model_map = {
        'haiku': 'claude-haiku-4-5-20251001',
        'sonnet': 'claude-sonnet-4-5-20250929',
        'opus': 'claude-opus-4-6-20250917'
    }

    console.print(f"[dim]Using {model} model for planning...[/dim]")

    response = client.messages.create(
        model=model_map[model],
        max_tokens=8000,
        messages=[{"role": "user", "content": planning_prompt}]
    )

    # Parse plan
    response_text = response.content[0].text

    # Extract JSON
    import re
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        console.print("❌ Failed to create implementation plan", style="red")
        console.print("\nResponse was:")
        console.print(response_text)
        sys.exit(1)

    try:
        plan = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        console.print(f"❌ Invalid JSON in plan: {e}", style="red")
        console.print(response_text)
        sys.exit(1)

    # Display plan
    console.print("\n[bold green]✓ Implementation plan created[/bold green]")
    console.print(f"\n[bold]{plan['summary']}[/bold]")
    console.print(f"\nTotal tasks: {len(plan['tasks'])}")
    console.print(f"Estimated time: {plan['total_estimated_time']} minutes")
    console.print(f"Parallel waves: {len(plan['parallelization'])} waves")

    # Show tasks
    console.print("\n[bold]Tasks:[/bold]")
    for task in plan['tasks']:
        deps = f" [dim](depends: {', '.join(task['dependencies'])})[/dim]" if task['dependencies'] else ""
        complexity_icon = {1: "🟢", 2: "🟡", 3: "🔴"}.get(task['complexity'], "⚪")
        console.print(f"  {complexity_icon} {task['title']}{deps}")
        console.print(f"     → {task['target_file']}")

    # Confirm before proceeding
    if not click.confirm(f"\n💡 Proceed with implementation? This will spawn up to {max_workers} workers", default=True):
        console.print("\n⚠️  Cancelled by user")
        sys.exit(0)

    # Step 3: Execute implementation in parallel waves
    console.print("\n[bold]Step 3:[/bold] Executing implementation...")

    task_status = {task['id']: 'pending' for task in plan['tasks']}
    task_results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        overall = progress.add_task(
            "[cyan]Overall progress",
            total=len(plan['tasks'])
        )

        # Execute waves sequentially, tasks within waves in parallel
        for wave_name, wave_tasks in plan['parallelization'].items():
            console.print(f"\n[bold blue]→ {wave_name.replace('_', ' ').title()}[/bold blue]")

            # Filter to tasks that exist in this wave
            wave_task_objs = [t for t in plan['tasks'] if t['id'] in wave_tasks]

            if not wave_task_objs:
                continue

            # Spawn workers for all tasks in this wave
            processes = {}
            for task in wave_task_objs:
                console.print(f"  🚀 Starting: {task['title']}")

                # Create implementation prompt
                spec_content = docs_content.get(task['spec_file'], '')

                impl_prompt = f"""Implement this task from the specification.

TASK: {task['title']}

DESCRIPTION:
{task['description']}

SPECIFICATION (from {task['spec_file']}):
{spec_content}

FOCUS ON: {task['spec_section']}

TARGET FILE: {task['target_file']}
ACTION: {task['action']}

OUTPUT:
Provide complete, production-ready code.

If MODIFY: Show the complete section to add
If CREATE: Show the complete file contents

Include:
- All imports needed
- Complete implementation
- Type hints for all parameters
- Docstrings with examples
- Error handling

Begin with:
```python
# ... your implementation
```"""

                # Run implementation in subprocess
                cmd = [
                    sys.executable, '-c',
                    f"""
import os
os.environ['ANTHROPIC_API_KEY'] = '{api_key}'

from anthropic import Anthropic
client = Anthropic()

response = client.messages.create(
    model='{model_map.get('sonnet', 'claude-sonnet-4-5-20250929')}',
    max_tokens=8000,
    messages=[{{"role": "user", "content": '''{impl_prompt}'''}}]
)

print(response.content[0].text)
"""
                ]

                log_file = workspace_path / f"task_{task['id']}.log"
                process = subprocess.Popen(
                    cmd,
                    stdout=open(log_file, 'w'),
                    stderr=subprocess.STDOUT,
                    cwd=workspace_path
                )

                processes[task['id']] = {
                    'process': process,
                    'task': task,
                    'log_file': log_file,
                    'start_time': time.time()
                }

                task_status[task['id']] = 'running'

            # Wait for all tasks in wave to complete
            while processes:
                for task_id in list(processes.keys()):
                    proc_info = processes[task_id]
                    retcode = proc_info['process'].poll()

                    if retcode is not None:
                        # Process completed
                        elapsed = time.time() - proc_info['start_time']

                        # Read output
                        with open(proc_info['log_file'], 'r') as f:
                            output = f.read()

                        if retcode == 0:
                            console.print(f"  ✅ {proc_info['task']['title']} ({elapsed:.1f}s)")
                            task_status[task_id] = 'completed'
                            task_results[task_id] = output
                            progress.advance(overall)
                        else:
                            console.print(f"  ❌ {proc_info['task']['title']} failed", style="red")
                            task_status[task_id] = 'failed'
                            task_results[task_id] = output

                        del processes[task_id]

                time.sleep(0.5)

    # Step 4: Apply implementations and run tests
    console.print("\n[bold]Step 4:[/bold] Applying implementations and testing...")

    for task in plan['tasks']:
        if task_status[task['id']] != 'completed':
            continue

        output = task_results[task['id']]

        # Extract code block
        code_match = re.search(r'```python\n(.*?)\n```', output, re.DOTALL)
        if not code_match:
            console.print(f"⚠️  No code block found for {task['title']}", style="yellow")
            continue

        code = code_match.group(1)

        # Write to target file
        target_path = workspace_path / task['target_file']
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if task['action'] == 'CREATE':
            with open(target_path, 'w') as f:
                f.write(code)
            console.print(f"  📝 Created {task['target_file']}")
        else:  # MODIFY
            with open(target_path, 'a') as f:
                f.write('\n\n' + code)
            console.print(f"  📝 Modified {task['target_file']}")

        # Run tests
        if task.get('test_command'):
            console.print(f"  🧪 Testing: {task['test_command']}")
            test_result = subprocess.run(
                task['test_command'].split(),
                cwd=workspace_path,
                capture_output=True
            )

            if test_result.returncode == 0:
                console.print(f"  ✅ Tests passed")
            else:
                console.print(f"  ❌ Tests failed", style="red")
                console.print(test_result.stdout.decode())
                console.print(test_result.stderr.decode())

    # Final summary
    completed = sum(1 for s in task_status.values() if s == 'completed')
    failed = sum(1 for s in task_status.values() if s == 'failed')

    console.print("\n" + "="*70)
    console.print(Panel.fit(
        f"[bold green]BUILD COMPLETE[/bold green]\n\n"
        f"✅ Completed: {completed}/{len(plan['tasks'])} tasks\n"
        f"{'❌ Failed: ' + str(failed) if failed else ''}",
        border_style="green" if failed == 0 else "yellow"
    ))

    if failed == 0:
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Review changes: git diff")
        console.print("  2. Run full tests: pytest")
        console.print("  3. Commit: git add . && git commit")
    else:
        console.print("\n[yellow]Some tasks failed. Check logs:[/yellow]")
        console.print(f"  ls {workspace_path}/task_*.log")
