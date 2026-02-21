# Simple Spec Format

**For 90% of implementation tasks, you only need this:**

---

## Minimal Spec Template

```markdown
# What to Build

[1-2 sentences describing what you're implementing]

## The Code

```python
# Show exactly what you want with complete code

class MyClass:
    """What it does.

    Example:
        >>> obj = MyClass("test")
        >>> obj.method()
        True
    """

    def method(self) -> bool:
        """What this method does.

        Example:
            >>> obj.method()
            True
        """
        return True
```

## Where It Goes

- **File**: `path/to/file.py`
- **After**: `class ExistingClass` or line 150

## How to Test

```bash
pytest tests/test_file.py -v
```

Done.
```

---

## Real Example

Here's what actually worked for ApprovalGate:

```markdown
# Approval Gate for Multi-Role Sign-off

Need a class that tracks approvals from different roles.

## The Code

```python
@dataclass
class ApprovalGate:
    """Approval gate requiring specific roles.

    Example:
        >>> gate = ApprovalGate("deploy", "production_deploy", "Deploy v2")
        >>> gate.requires_approval_from([Role.EM, Role.QA_LEAD])
        >>> gate.approve(em_agent)
        >>> gate.is_approved()
        False  # Need QA too
    """

    gate_id: str
    action_type: str
    description: str

    required_roles: Set[Role] = field(default_factory=set)
    approvals: List[str] = field(default_factory=list)
    rejections: List[str] = field(default_factory=list)
    min_approvals: int = 1

    def requires_approval_from(self, roles: List[Role]) -> "ApprovalGate":
        """Set required roles."""
        self.required_roles = set(roles)
        return self

    def can_approve(self, agent) -> bool:
        """Check if agent can approve."""
        return agent.role in self.required_roles

    def approve(self, agent):
        """Approve with this agent."""
        if not self.can_approve(agent):
            raise PermissionDenied(f"Can't approve")
        self.approvals.append(agent.agent_id)

    def is_approved(self) -> bool:
        """Check if approved."""
        return len(self.approvals) >= self.min_approvals
```

## Where

- **File**: `agentcoord/roles.py`
- **After**: `class PermissionDenied`

## Test

```bash
pytest tests/test_roles.py -v
```
```

---

## That's It

**3 essential pieces:**

1. **The Code** - Show exactly what you want (complete, working syntax)
2. **Where It Goes** - File + insertion point
3. **How to Test** - Command to run

**Everything else is optional.**

---

## Quick Rules

✅ **Do:**
- Include complete code with type hints
- Show 1-2 usage examples in docstrings
- Specify exact file and location

❌ **Don't:**
- Write essays about design principles
- Create complex documentation
- Use TODOs or pseudocode

---

## When You Need More

Only add extra sections if:

- **Multiple components** → Add a component per section
- **Complex integration** → Show dependency graph
- **Edge cases** → Add more examples
- **Breaking changes** → Add migration notes

But start simple. Most tasks only need the minimal template.

---

## Command Format

```bash
agentcoord implement \
  --spec docs/my_simple_spec.md \
  --task "Implement MyClass from spec" \
  --target-file src/file.py \
  --test-command "pytest tests/test_file.py"
```

Done.
