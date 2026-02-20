"""Coordinate command - autonomous task decomposition and execution."""

import click
import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic


@click.command()
@click.option('--request', required=True, help='High-level request to coordinate')
@click.option('--workspace', default='~/agentcoord/workspace/coordination', help='Workspace directory')
@click.option('--max-workers', default=20, help='Maximum workers to spawn')
def coordinate(request: str, workspace: str, max_workers: int):
    """
    Autonomous coordinator that breaks down requests into tasks and spawns workers.

    Example:
        agentcoord coordinate --request "Research ZipRecruiter failure scenarios"
    """
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        click.echo("❌ Error: ANTHROPIC_API_KEY not set", err=True)
        click.echo("   Set it with: export ANTHROPIC_API_KEY='your-key'", err=True)
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Expand workspace path
    workspace_path = Path(workspace).expanduser()
    workspace_path.mkdir(parents=True, exist_ok=True)

    click.echo("\n" + "="*70)
    click.echo("  AUTONOMOUS COORDINATOR")
    click.echo("="*70 + "\n")
    click.echo(f"Request: {request}")
    click.echo(f"Workspace: {workspace_path}")
    click.echo(f"Max Workers: {max_workers}\n")

    # Step 1: Decompose request into tasks
    click.echo("🧠 Decomposing request into tasks...")

    decomposition_prompt = f"""You are a project coordinator. Break down this request into specific, executable tasks:

REQUEST: {request}

Your job:
1. Identify 10-20 specific research tasks needed to fulfill this request
2. For each task, provide:
   - Task title (concise)
   - Task description (what needs to be researched/analyzed)
   - Complexity (1-3):
     * 1 = Simple data gathering, fact collection, straightforward research (use Haiku)
     * 2 = Moderate analysis, connecting dots, pattern recognition (use Haiku or Sonnet)
     * 3 = Deep analysis, strategic thinking, complex reasoning, scenario modeling (use Sonnet)

Return ONLY a JSON array of tasks in this format:
[
  {{
    "title": "Task title",
    "description": "Detailed description",
    "complexity": 1
  }},
  ...
]

Be thorough and assign complexity accurately based on cognitive demand."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        messages=[{"role": "user", "content": decomposition_prompt}]
    )

    # Extract task list
    import json
    import re

    response_text = response.content[0].text

    # Extract JSON from response
    json_match = re.search(r'\[[\s\S]*\]', response_text)
    if not json_match:
        click.echo("❌ Failed to decompose request", err=True)
        sys.exit(1)

    tasks = json.loads(json_match.group(0))

    click.echo(f"✅ Decomposed into {len(tasks)} tasks\n")

    # Analyze task complexity distribution
    complexity_counts = {1: 0, 2: 0, 3: 0}
    for task in tasks:
        complexity = task.get('complexity', 2)
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1

    simple_tasks = complexity_counts[1]
    moderate_tasks = complexity_counts[2]
    complex_tasks = complexity_counts[3]

    click.echo(f"Task complexity breakdown:")
    click.echo(f"  🟢 Simple (Haiku):   {simple_tasks} tasks")
    click.echo(f"  🟡 Moderate (Mixed): {moderate_tasks} tasks")
    click.echo(f"  🔴 Complex (Sonnet): {complex_tasks} tasks\n")

    # Step 2: Create tasks in queue with complexity metadata
    from tasks import TaskQueue

    db_path = workspace_path / "tasks.db"
    task_queue = TaskQueue(db_path=str(db_path))

    task_ids = []
    for task_def in tasks:
        complexity = task_def.get('complexity', 2)
        description_with_meta = f"[COMPLEXITY:{complexity}] {task_def['description']}"

        task = task_queue.create_task(
            title=task_def['title'],
            description=description_with_meta
        )
        task_ids.append(task.id)

        complexity_icon = {1: "🟢", 2: "🟡", 3: "🔴"}.get(complexity, "⚪")
        click.echo(f"  {complexity_icon} {task_def['title']}")

    click.echo(f"\n✅ {len(tasks)} tasks created in queue\n")

    # Step 3: Determine optimal worker mix
    # Haiku workers: process simple + moderate tasks (faster, cheaper)
    # Sonnet workers: process complex tasks (deeper reasoning)

    num_haiku = min(max_workers // 2, simple_tasks + moderate_tasks // 2)
    num_sonnet = min(max_workers - num_haiku, complex_tasks + moderate_tasks // 2)

    # Ensure at least 1 of each if we have tasks
    if simple_tasks > 0 and num_haiku == 0:
        num_haiku = 1
    if complex_tasks > 0 and num_sonnet == 0:
        num_sonnet = 1

    # Respect max_workers limit
    total_workers = num_haiku + num_sonnet
    if total_workers > max_workers:
        ratio = max_workers / total_workers
        num_haiku = int(num_haiku * ratio)
        num_sonnet = max_workers - num_haiku

    click.echo(f"🤖 Spawning optimized worker mix:")
    click.echo(f"  🟢 {num_haiku} Haiku workers (fast, cheap)")
    click.echo(f"  🔴 {num_sonnet} Sonnet workers (deep analysis)\n")

    # Step 4: Spawn workers with model assignments
    import subprocess
    import time

    worker_script = Path(__file__).parent.parent.parent / "run_worker.py"

    workers_spawned = 0

    # Spawn Haiku workers
    for i in range(num_haiku):
        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = api_key
        env['MODEL'] = 'haiku'
        env['WORKER_NAME'] = f"HAIKU-{i+1}"

        log_file = workspace_path / f"haiku-worker-{i+1}.log"

        subprocess.Popen(
            [sys.executable, str(worker_script)],
            env=env,
            stdout=open(log_file, 'w'),
            stderr=subprocess.STDOUT,
            cwd=str(workspace_path)
        )

        workers_spawned += 1
        click.echo(f"  🟢 Haiku worker {i+1} spawned")
        time.sleep(0.2)

    # Spawn Sonnet workers
    for i in range(num_sonnet):
        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = api_key
        env['MODEL'] = 'sonnet'
        env['WORKER_NAME'] = f"SONNET-{i+1}"

        log_file = workspace_path / f"sonnet-worker-{i+1}.log"

        subprocess.Popen(
            [sys.executable, str(worker_script)],
            env=env,
            stdout=open(log_file, 'w'),
            stderr=subprocess.STDOUT,
            cwd=str(workspace_path)
        )

        workers_spawned += 1
        click.echo(f"  🔴 Sonnet worker {i+1} spawned")
        time.sleep(0.2)

    click.echo(f"\n{'='*70}")
    click.echo("  COORDINATION COMPLETE - OPTIMIZED EXECUTION")
    click.echo("="*70 + "\n")

    click.echo(f"📋 Tasks: {len(tasks)} total")
    click.echo(f"   🟢 Simple: {simple_tasks} → Haiku")
    click.echo(f"   🟡 Moderate: {moderate_tasks} → Mixed")
    click.echo(f"   🔴 Complex: {complex_tasks} → Sonnet\n")

    click.echo(f"🤖 Workers: {workers_spawned} total")
    click.echo(f"   🟢 Haiku: {num_haiku} workers (50k tokens/min each)")
    click.echo(f"   🔴 Sonnet: {num_sonnet} workers (8k tokens/min each)\n")

    # Calculate expected throughput
    haiku_throughput = num_haiku * 50000 / 2000  # ~25 tasks/min per haiku worker
    sonnet_throughput = num_sonnet * 8000 / 3000  # ~2.6 tasks/min per sonnet worker
    total_throughput = haiku_throughput + sonnet_throughput

    click.echo(f"📊 Expected throughput: ~{total_throughput:.1f} tasks/min")
    click.echo(f"⏱️  Estimated completion: ~{len(tasks)/total_throughput:.1f} minutes\n")

    click.echo(f"Database: {db_path}\n")

    click.echo(f"Monitor progress:")
    click.echo(f"  python3 ~/agentcoord/dashboard.py\n")

    click.echo(f"View logs:")
    click.echo(f"  tail -f {workspace_path}/haiku-*.log")
    click.echo(f"  tail -f {workspace_path}/sonnet-*.log\n")

    click.echo(f"Kill workers:")
    click.echo(f"  pkill -f run_worker.py")
    click.echo()
