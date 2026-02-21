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


def check_file_exists(target_path: Path) -> bool:
    """Check if target file already exists.

    Args:
        target_path: Path to the target file

    Returns:
        True if file exists, False otherwise
    """
    return target_path.exists()


def check_class_exists(file_path: Path, class_name: str) -> bool:
    """Check if a class is already defined in a file.

    Args:
        file_path: Path to Python file to search
        class_name: Name of class to search for

    Returns:
        True if class found, False otherwise
    """
    if not file_path.exists():
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, OSError):
        return False

    import re
    pattern = rf'^class {re.escape(class_name)}[:\(]'
    return bool(re.search(pattern, content, re.MULTILINE))


def apply_modification(target_path: Path, new_code: str, task: dict, workspace_path: Path) -> bool:
    """Apply code modification with conflict detection.

    Args:
        target_path: Path to file
        new_code: Code to add
        task: Task metadata with action type
        workspace_path: Workspace root path

    Returns:
        True if modification applied, False if skipped
    """
    import re

    if task['action'] == 'CREATE':
        if target_path.exists():
            console.print(f"⚠️  File already exists: {target_path}", style="yellow")
            console.print(f"   Skipping {task['title']}")
            return False

        # Safe to create
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            return True
        except Exception as e:
            console.print(f"❌ Error creating file {target_path}: {e}", style="red")
            return False

    elif task['action'] == 'MODIFY':
        if not target_path.exists():
            console.print(f"⚠️  Target file does not exist: {target_path}", style="yellow")
            console.print(f"   Cannot MODIFY non-existent file for {task['title']}")
            return False

        # Extract class names from new code
        class_names = re.findall(r'^class (\w+)[:\(]', new_code, re.MULTILINE)

        # Check for duplicates
        duplicates = []
        for class_name in class_names:
            if check_class_exists(target_path, class_name):
                duplicates.append(class_name)

        if duplicates:
            console.print(f"⚠️  Duplicate classes found: {', '.join(duplicates)}", style="yellow")
            console.print(f"   File: {target_path}")
            console.print(f"   Skipping {task['title']} to avoid conflicts")
            return False

        # Safe to append
        try:
            with open(target_path, 'a', encoding='utf-8') as f:
                f.write('\n\n' + new_code)
            return True
        except Exception as e:
            console.print(f"❌ Error modifying file {target_path}: {e}", style="red")
            return False

    else:
        console.print(f"⚠️  Unknown action type: {task['action']}", style="yellow")
        return False


def get_related_files(target_file: str, workspace_path: Path) -> str:
    """Get context from related files in the same directory.

    Args:
        target_file: Path to target file
        workspace_path: Workspace root path

    Returns:
        String with file listing and class definitions
    """
    target_path = Path(target_file)
    parent_dir = workspace_path / target_path.parent

    if not parent_dir.exists():
        return "No existing files in target directory"

    related = []
    for py_file in parent_dir.glob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            import re
            classes = re.findall(r'^class (\w+)[:\(]', content, re.MULTILINE)
            if classes:
                related.append(f"{py_file.name}: {', '.join(classes)}")
        except Exception:
            continue

    return '\n'.join(related) if related else "No Python files found"


@click.command()
@click.argument('request', required=True)
@click.option('--workspace', default='.', help='Workspace directory')
@click.option('--max-workers', default=5, type=int, help='Maximum parallel workers')
@click.option('--model', default='sonnet', type=click.Choice(['haiku', 'sonnet', 'opus']))
@click.option('--docs-dir', default='docs', help='Directory containing design docs')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def build(request: str, workspace: str, max_workers: int, model: str, docs_dir: str, dry_run: bool):
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

    # Dry-run mode: show what would be done and exit
    if dry_run:
        console.print("\n[bold yellow]DRY RUN MODE[/bold yellow]")
        console.print("Would create/modify the following:\n")

        for task in plan['tasks']:
            action_icon = "📝" if task['action'] == 'CREATE' else "✏️"
            console.print(f"{action_icon} {task['action']}: {task['target_file']}")
            console.print(f"   Task: {task['title']}")

            # Check for conflicts
            target_path = workspace_path / task['target_file']
            if task['action'] == 'CREATE' and check_file_exists(target_path):
                console.print(f"   ⚠️  WARNING: File already exists", style="yellow")

            # Check for duplicate classes if MODIFY
            if task['action'] == 'MODIFY' and target_path.exists():
                import re
                # Try to extract class names from spec
                spec_content = docs_content.get(task.get('spec_file', ''), '')
                class_names = re.findall(r'^class (\w+)[:\(]', spec_content, re.MULTILINE)
                duplicates = [cn for cn in class_names if check_class_exists(target_path, cn)]
                if duplicates:
                    console.print(f"   ⚠️  WARNING: Duplicate classes: {', '.join(duplicates)}", style="yellow")

            console.print()

        console.print("[dim]Run without --dry-run to execute[/dim]")
        return

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
                related_files = get_related_files(task['target_file'], workspace_path)

                impl_prompt = f"""You are implementing a task as part of a larger codebase.

CRITICAL: Before writing code, check if similar functionality already exists.
If you find existing implementations of classes/functions you're about to create, STOP and return:

DUPLICATE_FOUND: <class_name> already exists in <file_path>

Only proceed if you're certain it's new functionality.

TASK: {task['title']}

DESCRIPTION:
{task['description']}

TARGET FILE: {task['target_file']}
ACTION: {task['action']}

SPECIFICATION (from {task['spec_file']}):
{spec_content}

FOCUS ON: {task['spec_section']}

EXISTING CODEBASE CONTEXT:
{related_files}

INSTRUCTIONS:
1. Review the EXISTING CODEBASE CONTEXT above
2. Check if any classes/functions you plan to implement already exist
3. If duplicates found, return "DUPLICATE_FOUND: <details>" and STOP
4. If no duplicates, implement following the specification
5. Include all necessary imports
6. Add type hints and docstrings with examples
7. Handle errors appropriately

OUTPUT FORMAT:
If implementing new code:
```python
# Your complete implementation
```

If duplicate found:
DUPLICATE_FOUND: <class_name> already exists in <file_path>"""

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

        # Apply modification with conflict detection
        target_path = workspace_path / task['target_file']

        if apply_modification(target_path, code, task, workspace_path):
            action_verb = "Created" if task['action'] == 'CREATE' else "Modified"
            console.print(f"  📝 {action_verb} {task['target_file']}")
        else:
            console.print(f"  ⏭️  Skipped {task['target_file']} (conflict detected)")
            continue

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
