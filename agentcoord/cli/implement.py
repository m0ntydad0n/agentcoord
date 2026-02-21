"""Implement command - coordinate implementation tasks from design specs."""

import click
import sys
import os
import json
from pathlib import Path
from anthropic import Anthropic


@click.command()
@click.option('--spec', required=True, help='Path to design spec file')
@click.option('--task', required=True, help='Specific task from spec to implement')
@click.option('--target-file', required=True, help='File to modify/create')
@click.option('--workspace', default='.', help='Workspace directory')
@click.option('--test-command', default='pytest', help='Command to run tests')
@click.option('--model', default='sonnet', type=click.Choice(['haiku', 'sonnet', 'opus']))
def implement(spec: str, task: str, target_file: str, workspace: str, test_command: str, model: str):
    """
    Coordinate implementation of a specific task from a design specification.

    This command is purpose-built for implementing code from design docs, not research.

    Example:
        agentcoord implement \\
          --spec docs/role_api_design.md \\
          --task "Implement ApprovalGate class (lines 329-460)" \\
          --target-file agentcoord/roles.py \\
          --test-command "pytest tests/test_roles.py -v"
    """
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        click.echo("❌ Error: ANTHROPIC_API_KEY not set", err=True)
        click.echo("   Set it with: export ANTHROPIC_API_KEY='your-key'", err=True)
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Expand paths
    workspace_path = Path(workspace).expanduser().resolve()
    spec_path = (workspace_path / spec).resolve()
    target_path = (workspace_path / target_file).resolve()

    # Validate paths
    if not spec_path.exists():
        click.echo(f"❌ Spec file not found: {spec_path}", err=True)
        sys.exit(1)

    click.echo("\n" + "="*70)
    click.echo("  IMPLEMENTATION COORDINATOR")
    click.echo("="*70 + "\n")
    click.echo(f"📄 Spec: {spec_path.name}")
    click.echo(f"📋 Task: {task}")
    click.echo(f"🎯 Target: {target_path.relative_to(workspace_path)}")
    click.echo(f"🧪 Tests: {test_command}")
    click.echo(f"🤖 Model: {model}\n")

    # Read spec file
    click.echo("📖 Reading specification...")
    with open(spec_path, 'r') as f:
        spec_content = f.read()

    # Read target file if it exists
    target_exists = target_path.exists()
    if target_exists:
        with open(target_path, 'r') as f:
            target_content = f.read()
        click.echo(f"✅ Target file exists ({len(target_content)} bytes)")
    else:
        target_content = ""
        click.echo(f"⚠️  Target file doesn't exist - will create")

    # Create implementation prompt
    click.echo("\n🧠 Creating implementation plan...")

    implementation_prompt = f"""You are an expert software engineer implementing code from a design specification.

TASK: {task}

DESIGN SPECIFICATION:
{spec_content}

CURRENT FILE CONTENT:
{'<File does not exist - will be created>' if not target_exists else target_content}

TARGET FILE: {target_file}

YOUR JOB:
1. Read and understand the design specification thoroughly
2. Implement EXACTLY what's specified - no more, no less
3. Follow the design's:
   - API structure (class names, method signatures)
   - Type hints and docstrings
   - Examples and usage patterns
   - Integration points
4. If the target file exists, add code in the appropriate location
5. Include comprehensive docstrings with examples from the spec
6. Use proper type hints for all parameters and return values

OUTPUT FORMAT:
Provide the complete implementation as a code block with clear insertion instructions.

Format:
```python
# FILE: {target_file}
# ACTION: <CREATE | APPEND | INSERT_AFTER>
# INSERT_AFTER: <If ACTION=INSERT_AFTER, the exact line to insert after>

<complete code to add>
```

IMPORTANT:
- Do NOT include imports that are already in the file
- Do NOT modify existing code unless the spec explicitly requires it
- Follow the exact API from the design spec
- Include all methods, properties, and docstrings from the spec
- Make it production-ready with proper error handling

Begin implementation:"""

    # Select model
    model_map = {
        'haiku': 'claude-haiku-4-5-20251001',
        'sonnet': 'claude-sonnet-4-5-20250929',
        'opus': 'claude-opus-4-6-20250917'
    }

    click.echo(f"🤖 Using {model} model for implementation...")

    response = client.messages.create(
        model=model_map[model],
        max_tokens=8000,
        messages=[{"role": "user", "content": implementation_prompt}]
    )

    response_text = response.content[0].text

    # Extract code block
    import re
    code_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)

    if not code_match:
        click.echo("❌ Failed to extract implementation code", err=True)
        click.echo("\nResponse was:")
        click.echo(response_text)
        sys.exit(1)

    implementation = code_match.group(1)

    # Parse metadata from code
    action = "APPEND"  # Default
    insert_after = None

    for line in implementation.split('\n'):
        if line.startswith('# ACTION:'):
            action = line.split(':', 1)[1].strip()
        elif line.startswith('# INSERT_AFTER:'):
            insert_after = line.split(':', 1)[1].strip()

    # Remove metadata comments
    clean_implementation = '\n'.join([
        line for line in implementation.split('\n')
        if not line.startswith('# FILE:') and
           not line.startswith('# ACTION:') and
           not line.startswith('# INSERT_AFTER:')
    ])

    click.echo(f"\n✅ Implementation generated ({len(clean_implementation)} bytes)")
    click.echo(f"   Action: {action}")
    if insert_after:
        click.echo(f"   Insert after: {insert_after}")

    # Show preview
    click.echo("\n📄 Preview (first 20 lines):")
    click.echo("-" * 70)
    for i, line in enumerate(clean_implementation.split('\n')[:20], 1):
        click.echo(f"{i:3} | {line}")
    click.echo("-" * 70)

    # Confirm before writing
    if click.confirm("\n💾 Write implementation to file?", default=True):
        # Apply implementation
        if action == "CREATE" or not target_exists:
            with open(target_path, 'w') as f:
                f.write(clean_implementation)
            click.echo(f"✅ Created {target_path}")

        elif action == "APPEND":
            with open(target_path, 'a') as f:
                f.write('\n\n' + clean_implementation)
            click.echo(f"✅ Appended to {target_path}")

        elif action == "INSERT_AFTER" and insert_after:
            lines = target_content.split('\n')
            insert_index = None

            for i, line in enumerate(lines):
                if insert_after in line:
                    insert_index = i + 1
                    break

            if insert_index is not None:
                new_lines = lines[:insert_index] + clean_implementation.split('\n') + lines[insert_index:]
                with open(target_path, 'w') as f:
                    f.write('\n'.join(new_lines))
                click.echo(f"✅ Inserted into {target_path} after line {insert_index}")
            else:
                click.echo(f"❌ Could not find insertion point: {insert_after}", err=True)
                sys.exit(1)

        # Run tests
        if click.confirm(f"\n🧪 Run tests? ({test_command})", default=True):
            click.echo(f"\nRunning: {test_command}")
            import subprocess
            result = subprocess.run(
                test_command.split(),
                cwd=workspace_path,
                capture_output=False
            )

            if result.returncode == 0:
                click.echo("\n✅ Tests passed!")
            else:
                click.echo("\n❌ Tests failed")
                sys.exit(1)

        click.echo("\n" + "="*70)
        click.echo("  IMPLEMENTATION COMPLETE")
        click.echo("="*70)
        click.echo(f"\n✅ {task}")
        click.echo(f"📁 {target_path.relative_to(workspace_path)}")
        click.echo(f"\nNext steps:")
        click.echo(f"  1. Review changes: git diff {target_file}")
        click.echo(f"  2. Run full tests: {test_command}")
        click.echo(f"  3. Commit if good: git add {target_file} && git commit")

    else:
        click.echo("\n⚠️  Implementation not written (cancelled)")
        sys.exit(1)
