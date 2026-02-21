# AgentCoord Implementation Workflow

**End-to-end guide for spec-driven development with `agentcoord implement`**

---

## Quick Start

**1. Write spec using template:**
```bash
cp docs/SPEC_TEMPLATE.md docs/my_feature.md
# Edit docs/my_feature.md
```

**2. Validate spec:**
```bash
# Check against checklist in SPEC_WRITING_GUIDE.md
```

**3. Implement:**
```bash
agentcoord implement \
  --spec docs/my_feature.md \
  --task "Implement FeatureClass from spec" \
  --target-file src/feature.py \
  --test-command "pytest tests/test_feature.py -v"
```

**4. Review and commit:**
```bash
git diff src/feature.py  # Review changes
pytest tests/            # Run tests
git add . && git commit  # Commit if good
```

---

## Complete Workflow

### Phase 1: Design

**Input:** Feature request or task
**Output:** Complete design specification

```bash
# 1. Create spec from template
cp docs/SPEC_TEMPLATE.md docs/new_feature_spec.md

# 2. Fill in all sections:
#    - Overview
#    - Design principles
#    - Core components with complete code examples
#    - Usage examples
#    - API reference
#    - Testing strategy
#    - Integration details

# 3. Validate against checklist
#    See SPEC_WRITING_GUIDE.md section "Spec Quality Checklist"
```

**Quality Gates:**
- [ ] All code examples have valid syntax
- [ ] All methods have type hints
- [ ] All docstrings include runnable examples
- [ ] Integration points clearly defined
- [ ] No TODOs or ambiguous language

---

### Phase 2: Implementation

**Input:** Validated spec
**Output:** Working, tested code

```bash
# Run implement command
agentcoord implement \
  --spec docs/new_feature_spec.md \
  --task "Implement [Component] from spec (lines X-Y)" \
  --target-file path/to/file.py \
  --test-command "pytest tests/test_file.py -v" \
  --model sonnet  # or haiku/opus

# The command will:
# 1. Read spec and target file
# 2. Generate implementation
# 3. Show preview
# 4. Ask for confirmation
# 5. Write code
# 6. Run tests
# 7. Report results
```

**What you get:**
- ✅ Type-safe code matching spec exactly
- ✅ Docstrings with examples
- ✅ Proper integration with existing code
- ✅ Test validation before commit

---

### Phase 3: Validation

**Input:** Generated code
**Output:** Verified implementation

```bash
# 1. Review diff
git diff path/to/file.py

# 2. Check against spec
#    - All classes/methods present?
#    - Signatures match?
#    - Docstrings complete?

# 3. Run tests
pytest tests/ -v

# 4. Manual testing
python3 -c "
from module import NewComponent
obj = NewComponent('test')
print(obj.method())  # Verify works
"

# 5. Lint/type check (optional)
mypy path/to/file.py
flake8 path/to/file.py
```

**Validation Checklist:**
- [ ] All spec requirements implemented
- [ ] Tests pass
- [ ] Code follows project style
- [ ] No regressions in existing tests
- [ ] Examples from spec work when run

---

### Phase 4: Commit

**Input:** Validated code
**Output:** Committed feature

```bash
# 1. Stage changes
git add path/to/file.py tests/test_file.py docs/new_feature_spec.md

# 2. Commit with clear message
git commit -m "Implement [Feature] from spec

- Add [Component] class with methods
- Include comprehensive docstrings
- Add test coverage for [scenarios]
- Design spec: docs/new_feature_spec.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 3. Push (if ready)
git push origin feature-branch
```

---

## Model Selection Guide

Choose the right model for your task:

| Model | Best For | Cost | Speed |
|-------|----------|------|-------|
| **Haiku** | Simple utilities, data structures | $ | ⚡⚡⚡ |
| **Sonnet** | Most features, business logic | $$ | ⚡⚡ |
| **Opus** | Complex algorithms, critical systems | $$$ | ⚡ |

**Default:** Use Sonnet for balanced quality and cost

**Examples:**
- Haiku: Simple dataclass, enum, utility function
- Sonnet: API implementation, workflow logic, integration code
- Opus: Algorithm optimization, security-critical code, complex state machines

---

## Parallel Implementation

For independent tasks, run implements in parallel:

```bash
# Terminal 1
agentcoord implement \
  --spec docs/feature_a.md \
  --task "Implement ComponentA" \
  --target-file src/component_a.py \
  --model sonnet

# Terminal 2 (simultaneously)
agentcoord implement \
  --spec docs/feature_b.md \
  --task "Implement ComponentB" \
  --target-file src/component_b.py \
  --model sonnet

# Both run independently, no conflicts
```

**When to parallelize:**
- ✅ Different target files
- ✅ No shared dependencies
- ✅ Independent test suites

**When to serialize:**
- ❌ Same target file
- ❌ Component B depends on Component A
- ❌ Shared test fixtures

---

## Iterative Refinement

If first implementation needs fixes:

```bash
# 1. Review what was wrong
git diff path/to/file.py

# 2. Update spec with clarifications
#    Add missing details, fix ambiguous sections

# 3. Revert generated code
git checkout path/to/file.py

# 4. Re-run implement with improved spec
agentcoord implement \
  --spec docs/improved_spec.md \
  --task "..." \
  --target-file path/to/file.py

# 5. Compare results
#    Should be better with clearer spec
```

**Common spec improvements:**
- Add more detailed examples
- Clarify integration points
- Specify edge case handling
- Include type hints that were missing
- Remove ambiguous language

---

## Troubleshooting

### Issue: Generated code doesn't match spec

**Solution:**
1. Check if spec has complete code examples
2. Verify type hints are present
3. Add more detailed docstrings
4. Specify exact method signatures

### Issue: Code inserted in wrong location

**Solution:**
1. Spec must specify exact insertion point:
   ```markdown
   **File:** agentcoord/module.py
   **Insert after:** class ExistingClass (line 150)
   ```
2. Include line numbers when possible

### Issue: Missing imports

**Solution:**
1. Add "Required imports" section to spec:
   ```markdown
   **Required imports:**
   ```python
   from typing import List, Dict
   from .existing import ExistingClass
   ```
   ```

### Issue: Tests fail after implementation

**Solution:**
1. Review test expectations in spec
2. Check if edge cases are documented
3. Verify error handling is specified
4. Add test examples to spec

---

## Best Practices

### 1. One Spec Per Component

Don't mix multiple features in one spec:
- ❌ "Implement authentication and database layer"
- ✅ "Implement authentication system"
- ✅ "Implement database layer" (separate spec)

### 2. Spec Before Code

Always write spec first, never after:
- ❌ Write code, then document it
- ✅ Design in spec, then implement

### 3. Runnable Examples

Every spec example should be copy-pasteable:
```python
# ✅ Good - complete, runnable
from module import Component
obj = Component("value")
result = obj.method()

# ❌ Bad - incomplete
obj = Component(...)
result = obj.method()
```

### 4. Explicit Integration

Never assume the LLM knows your codebase:
```markdown
# ✅ Good
Insert after class `ExistingClass` at line 150 in agentcoord/module.py
Imports needed: from .base import BaseClass

# ❌ Bad
Add this somewhere appropriate
```

### 5. Version Control Specs

Commit specs alongside code:
```bash
git add docs/feature_spec.md src/feature.py tests/test_feature.py
git commit -m "Add Feature (spec + implementation + tests)"
```

---

## Metrics & Monitoring

Track your implementation success rate:

```bash
# Count successful first-try implementations
grep "✅ Implementation complete" logs/*.log | wc -l

# Count spec improvements needed
grep "⚠️ Implementation needs revision" logs/*.log | wc -l

# Success rate = successful / total
```

**Target:** >80% first-try success rate with good specs

---

## Example: Complete Workflow

Real example from this project:

```bash
# 1. Design phase
cp docs/SPEC_TEMPLATE.md docs/approval_gate_spec.md
# Edited to include ApprovalGate class design

# 2. Implementation
agentcoord implement \
  --spec docs/role_api_design.md \
  --task "Implement ApprovalGate class (lines 329-460)" \
  --target-file agentcoord/roles.py \
  --test-command "pytest tests/test_roles.py -k approval -v" \
  --model sonnet

# 3. Validation
git diff agentcoord/roles.py  # Reviewed changes
python3 -c "from agentcoord.roles import ApprovalGate; print('✅ Imports work')"
pytest tests/test_roles.py -v  # Tests passed

# 4. Commit
git add agentcoord/roles.py docs/role_api_design.md
git commit -m "Implement ApprovalGate class from spec

- Add ApprovalGate dataclass with approval tracking
- Include can_approve(), approve(), reject() methods
- Add docstrings with examples
- Design spec: docs/role_api_design.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Result:** ✅ Production-ready code in ~15 minutes

---

## Summary

**Workflow:**
1. Design → Write complete spec
2. Implement → Run `agentcoord implement`
3. Validate → Review, test, verify
4. Commit → Add to version control

**Keys to success:**
- Complete specs with runnable examples
- Clear integration points
- Explicit type hints and docstrings
- Quality checklist before implementing

**Benefits:**
- 🚀 Faster development
- ✅ Higher code quality
- 📚 Built-in documentation
- 🔄 Reproducible process

---

## Next Steps

1. **Try it:** Pick a simple feature and follow this workflow
2. **Iterate:** Improve specs based on what works
3. **Scale:** Use for all new development
4. **Share:** Commit good specs for team reuse
