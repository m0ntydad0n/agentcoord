# AgentCoord

**Autonomous parallel implementation from a single prompt.**

Multi-agent coordination system that takes one high-level command and handles everything: planning, parallelization, implementation, testing, and validation.

---

## The Simplest Possible Workflow

**1. Write what you want in design docs:**
```markdown
# docs/my_feature.md

Build a class that does X with methods Y and Z.

```python
class MyFeature:
    def method_y(self) -> bool:
        """Does Y."""
        return True
```
```

**2. Run one command:**
```bash
agentcoord build "Implement everything in docs/my_feature.md"
```

**3. Done.**

AgentCoord:
- Reads the design docs
- Plans the implementation with dependencies
- Spawns parallel workers (up to 5 by default)
- Implements everything in optimal order
- Tests as it goes
- Reports results

**No task queues. No coordination files. No multi-step workflows. Just one prompt.**

---

## Real Example

```bash
agentcoord build "Implement the role system and workflow router from docs/"
```

**What happens:**
```
✓ Reads design docs (76KB of specs)
✓ Plans 15 implementation tasks
✓ Organizes into 5 dependency-based waves
✓ Spawns 6 parallel workers
✓ Implements in ~15 minutes (vs 4 hours sequential)

Wave 1: [Role enum, WorkArtifact, TaskTemplate] → parallel
Wave 2: [CustomRole, Agent, Epic, Story, Workflows] → parallel
Wave 3: [ApprovalGate, RoleRegistry, WorkflowRouter] → parallel
Wave 4: [Repositories, Integration] → parallel
Wave 5: [Tests] → validates everything
```

**Result:** Complete role-based access control system with workflow routing, approval gates, and full test coverage.

---

## Installation

```bash
pip install -e .

# Set API key
export ANTHROPIC_API_KEY='your-key'
```

---

## Commands

### `agentcoord build` - Autonomous Parallel Implementation

**Single prompt → Complete implementation**

```bash
agentcoord build "Implement X from docs/design.md"
```

Options:
- `--max-workers N` - Parallel workers (default: 5)
- `--model opus` - Use smarter model (haiku/sonnet/opus)
- `--docs-dir specs` - Different docs folder

### `agentcoord implement` - Single Task Implementation

**For one specific task:**

```bash
agentcoord implement \
  --spec docs/design.md \
  --task "Implement ComponentX" \
  --target-file src/component.py \
  --test-command "pytest tests/"
```

### `agentcoord coordinate` - Research Coordination

**For research/analysis tasks:**

```bash
agentcoord coordinate --request "Research X scenarios and document findings"
```

---

## How to Write Design Specs

**Keep it simple** - show the code you want:

```markdown
# My Feature

Build a class that validates user input.

```python
class Validator:
    """Validates user input.

    Example:
        >>> v = Validator()
        >>> v.is_valid("test@email.com")
        True
    """

    def is_valid(self, input: str) -> bool:
        """Check if input is valid."""
        return "@" in input
```

**File:** `src/validator.py`
**Test:** `pytest tests/test_validator.py`
```

**That's it.** The more complete your code example, the better the implementation.

See `docs/SIMPLE_SPEC.md` for template.

---

## Features

### Autonomous Coordination
- **Dependency Analysis** - Automatically figures out what depends on what
- **Parallel Execution** - Runs independent tasks simultaneously
- **Wave-Based Planning** - Groups tasks into optimal execution waves
- **Real-Time Progress** - Shows what's happening as it happens

### Smart Implementation
- **Reads Design Docs** - Understands specs and generates matching code
- **Type-Safe Code** - Includes type hints, docstrings, examples
- **Tests Included** - Validates each task as it completes
- **Production Ready** - Generates clean, working code

### Flexible Models
- **Haiku** - Fast, cheap, simple tasks ($)
- **Sonnet** - Balanced quality/cost, most tasks ($$)
- **Opus** - Complex reasoning, critical systems ($$$)

---

## Project Structure

```
agentcoord/
├── cli/
│   ├── build.py          # Autonomous parallel implementation
│   ├── implement.py      # Single-task implementation
│   └── coordinate.py     # Research coordination
├── roles.py              # Role-based access control
├── workflows.py          # Workflow routing
├── work_artifacts.py     # Epic/Story/Task models
└── company.py            # Company hierarchy

docs/
├── SIMPLE_SPEC.md        # How to write specs (start here)
├── role_api_design.md    # Example: Complete role system spec
└── workflow_router_design.md  # Example: Workflow router spec
```

---

## Company Model (Advanced)

AgentCoord can model real organizational structures:

- **17 roles** across 5 departments (Product, Engineering, QA, Marketing, Support)
- **50+ capabilities** with inheritance (VPs inherit department capabilities)
- **Workflow types**: `feature`, `bug`, `launch`, `trading_strategy`
- **Approval gates**: Multi-role sign-off for critical operations
- **YAML templates**: Pre-built org structures

```python
from agentcoord.company import Company
from agentcoord.workflows import Epic, WorkflowRouter

# Load company from template
company = Company.from_template("janus_dev")

# Create epic - auto-generates tasks
epic = Epic(
    title="Add IV Percentile Filter",
    workflow_type="trading_strategy",
    created_by="strategy_pm"
)

# Route epic - 8 tasks with dependencies
router = WorkflowRouter(company)
tasks = router.route_epic(epic)

# Tasks assigned by role:
# 1. PM: Define strategy goals
# 2. Designer: Design config schema → requires PM approval
# 3. Engineer: Implement filter → depends on design
# 4. Engineer: Write tests → depends on implementation
# 5. QA: Run backtest → depends on tests
# 6. QA Lead: Validate metrics → requires backtest approval
# 7. PM: Approve for production → requires QA approval
# 8. SRE: Deploy to bot → requires PM approval
```

See `docs/role_capabilities_matrix.md` for complete role system.

---

## Examples

### Build from Design Doc
```bash
agentcoord build "Implement the approval gate system from docs/role_api_design.md"
```

### Implement Single Component
```bash
agentcoord implement \
  --spec docs/my_spec.md \
  --task "Implement UserAuth class" \
  --target-file src/auth.py
```

### Research and Document
```bash
agentcoord coordinate --request "Research database migration strategies and create comparison doc"
```

---

## Why AgentCoord?

**Before:**
```bash
# Write spec
# Break into tasks manually
# Coordinate dependencies yourself
# Spawn workers individually
# Monitor progress across terminals
# Debug failures one by one
# Integrate results manually
```

**After:**
```bash
agentcoord build "Implement X from docs/"
# ☕ Get coffee
# ✅ Review working code
```

**16x faster** through intelligent parallelization.

---

## License

MIT

---

## Contributing

PRs welcome! See `docs/IMPLEMENTATION_WORKFLOW.md` for development guide.

---

## Meta

**AgentCoord used AgentCoord to implement itself.**

The role system, workflow router, and approval gates you see in this repo were built using the `agentcoord build` command from design specifications.

Dogfooding at its finest. 🐕
