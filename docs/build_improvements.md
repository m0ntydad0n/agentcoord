# Build Command Improvements

Fix critical issues discovered during dogfooding attempt.

## Problem Summary

The `agentcoord build` command executed wave-based parallelization perfectly but had integration issues:
- Created duplicate files when classes already existed
- MODIFY action blindly appended instead of intelligently merging
- No checks for existing implementations
- Overwrote core codebase files

## Fix 1: Duplicate Detection

Add pre-flight checks before creating files or modifying code.

```python
def check_file_exists(target_path: Path) -> bool:
    """Check if target file already exists.

    Returns:
        True if file exists, False otherwise
    """
    return target_path.exists()

def check_class_exists(file_path: Path, class_name: str) -> bool:
    """Check if a class is already defined in a file.

    Args:
        file_path: Path to Python file
        class_name: Name of class to search for

    Returns:
        True if class found, False otherwise

    Example:
        >>> check_class_exists(Path("agent.py"), "Agent")
        True
    """
    if not file_path.exists():
        return False

    with open(file_path, 'r') as f:
        content = f.read()

    import re
    pattern = rf'^class {class_name}[:\(]'
    return bool(re.search(pattern, content, re.MULTILINE))
```

**File:** `agentcoord/cli/build.py` (add after imports, before build function)

## Fix 2: Smart MODIFY Action

Replace blind append with intelligent merge strategy.

```python
def apply_modification(target_path: Path, new_code: str, task: dict) -> bool:
    """Apply code modification with conflict detection.

    Strategy:
    1. Check if target file exists
    2. If CREATE action and file exists -> warn and skip
    3. If MODIFY action -> check for duplicate classes
    4. If duplicate found -> ask user for resolution
    5. Only append if safe

    Args:
        target_path: Path to file
        new_code: Code to add
        task: Task metadata with action type

    Returns:
        True if modification applied, False if skipped
    """
    if task['action'] == 'CREATE':
        if target_path.exists():
            console.print(f"⚠️  File already exists: {target_path}", style="yellow")
            console.print(f"   Skipping {task['title']}")
            return False

        # Safe to create
        with open(target_path, 'w') as f:
            f.write(new_code)
        return True

    elif task['action'] == 'MODIFY':
        # Extract class names from new code
        import re
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
        with open(target_path, 'a') as f:
            f.write('\n\n' + new_code)
        return True
```

**File:** `agentcoord/cli/build.py` (replace existing code application logic in Step 4)

## Fix 3: Dry-Run Mode

Add `--dry-run` flag to preview what would be done.

```python
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def build(request: str, workspace: str, max_workers: int, model: str, docs_dir: str, dry_run: bool):
    """Build command with dry-run support."""

    # ... existing planning code ...

    if dry_run:
        console.print("\n[bold yellow]DRY RUN MODE[/bold yellow]")
        console.print("Would create/modify the following:\n")

        for task in plan['tasks']:
            action_icon = "📝" if task['action'] == 'CREATE' else "✏️"
            console.print(f"{action_icon} {task['action']}: {task['target_file']}")
            console.print(f"   Task: {task['title']}")

            # Check for conflicts
            target_path = workspace_path / task['target_file']
            if task['action'] == 'CREATE' and target_path.exists():
                console.print(f"   ⚠️  WARNING: File already exists", style="yellow")

            console.print()

        console.print("[dim]Run without --dry-run to execute[/dim]")
        return

    # ... rest of execution ...
```

**File:** `agentcoord/cli/build.py` (add option, add dry-run check after planning)

## Fix 4: Codebase-Aware Prompts

Improve implementation prompts to check existing code first.

```python
# In the implementation prompt (Step 3), add:

impl_prompt = f\"\"\"You are implementing a task as part of a larger codebase.

CRITICAL: Before writing code, check if similar functionality already exists in the codebase.
If you find existing implementations of the classes/functions you're about to create, STOP and return:

DUPLICATE_FOUND: <class_name> already exists in <file_path>

Only proceed with implementation if you're certain it's new functionality.

TASK: {task['title']}

DESCRIPTION:
{task['description']}

TARGET FILE: {task['target_file']}
ACTION: {task['action']}

SPECIFICATION:
{spec_content}

EXISTING CODEBASE CONTEXT:
{get_related_files(task['target_file'])}

OUTPUT FORMAT:
If implementing new code:
```python
# Your implementation
```

If duplicate found:
DUPLICATE_FOUND: <details>
\"\"\"
```

**File:** `agentcoord/cli/build.py` (enhance implementation prompt in Step 3)

Add helper to find related files:

```python
def get_related_files(target_file: str) -> str:
    """Get context from related files in the same directory.

    Args:
        target_file: Path to target file

    Returns:
        String with file listing and class definitions
    """
    from pathlib import Path

    target_path = Path(target_file)
    parent_dir = target_path.parent

    if not parent_dir.exists():
        return "No existing files in target directory"

    related = []
    for py_file in parent_dir.glob("*.py"):
        # Read and extract class definitions
        with open(py_file, 'r') as f:
            content = f.read()

        import re
        classes = re.findall(r'^class (\w+)[:\(]', content, re.MULTILINE)
        if classes:
            related.append(f"{py_file.name}: {', '.join(classes)}")

    return '\n'.join(related) if related else "No Python files found"
```

**File:** `agentcoord/cli/build.py` (add before build function)

## Testing

After implementing:

```bash
# Test dry-run
agentcoord build --dry-run "Implement test feature from docs/test_spec.md"

# Test duplicate detection
# (Try to re-implement something that exists)
agentcoord build "Implement Role enum from docs/role_api_design.md"
# Should detect and skip

# Test real implementation
agentcoord build "Add logging middleware to CLI commands"
# Should work without conflicts
```

## Files Modified

- `agentcoord/cli/build.py` - All improvements
- Tests: `tests/test_build_command.py` (create new test file)

## Success Criteria

- ✅ `--dry-run` shows preview without executing
- ✅ Duplicate files are detected and skipped
- ✅ Duplicate classes are detected and skipped
- ✅ Workers check existing codebase before implementing
- ✅ No more accidental overwrites of core files
