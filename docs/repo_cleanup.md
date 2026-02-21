# Repository Cleanup - Organize Root Directory

Move loose files from root into proper subdirectories.

## Current Problem

Root directory has 20+ loose Python files that should be organized:
- Demo files scattered everywhere
- Test files not in tests/
- Utility scripts mixed with core code

## Desired Structure

```
agentcoord/
├── examples/           # All demo_*.py files
├── scripts/           # Utility scripts
├── tests/             # All test_*.py files
└── (clean root)       # Only essential files
```

## Tasks

### Task 1: Move Demo Files to examples/

Move these files to `examples/`:
- demo.py
- demo_dashboard.py
- demo_llm_budget.py
- demo_ui.py
- test_full_demo.py
- example_usage.py

Create `.gitkeep` file in examples/ to ensure directory exists.

**File:** Create `examples/.gitkeep`
**Test:** `ls examples/*.py | wc -l` should show 6 files

### Task 2: Move Utility Scripts to scripts/

Move these to `scripts/`:
- create_task.py (if not in use)
- run_worker.py
- worker_stats_analysis.py
- detailed_worker_stats.py
- usability_improvements_coordinator.py
- interactive_prompts.py

**File:** Verify `scripts/` directory structure
**Test:** `ls scripts/*.py | wc -l` should include these files

### Task 3: Move Test Files to tests/

Move these to `tests/`:
- test_alpha_mvp.py
- test_rich_ui.py
- test_spawning.py

**File:** Move to `tests/`
**Test:** `pytest tests/test_*.py --collect-only` should find them

### Task 4: Clean Obsolete Files

Identify files that might be obsolete:
- ascii_art.py (if not imported anywhere)
- cyberpunk_ui.py (if replaced by newer UI)
- dashboard.py (if dashboard moved to agentcoord/dashboard.py)
- main.py (if not entry point)

Check imports and either move to appropriate directory or add to .gitignore.

**File:** `.gitignore` updates
**Test:** `git status` should show clean root

## Success Criteria

✅ Root directory only contains:
- README.md
- setup.py
- requirements.txt
- docker-compose.yml
- .gitignore
- Key markdown files

✅ All demo files in `examples/`
✅ All scripts in `scripts/`
✅ All tests in `tests/`
✅ No broken imports
