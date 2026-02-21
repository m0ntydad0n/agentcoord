# Workflow Router Design

**Author**: API Designer Agent
**Date**: 2026-02-20
**Status**: Design Specification

## Overview

The WorkflowRouter system provides automated task generation and agent assignment based on predefined workflow types. When a PM or other role creates an Epic with a workflow type (e.g., `trading_strategy`, `feature`, `bug`, `launch`), the router automatically:

1. Generates all required tasks for that workflow
2. Assigns tasks to appropriate agent roles
3. Establishes dependency chains between tasks
4. Tracks progress through the workflow lifecycle

This eliminates manual task creation and ensures consistent workflows across the organization.

---

## Architecture

### Class Hierarchy

```
WorkArtifact (ABC)
├── Epic
├── Story
└── Task
```

**WorkArtifact** is the base abstraction for all work items. It provides common fields and behavior.

**Epic** represents a large body of work (e.g., "Add IV Percentile Filter"). Epics have a `workflow_type` that determines task generation.

**Story** represents a medium-sized deliverable within an Epic. Stories may group related tasks.

**Task** is the atomic unit of work assigned to a single agent. Extends the existing `Task` model from `agentcoord/tasks.py`.

### Integration Points

**Extends existing system:**
- `agentcoord/tasks.py`: Task model with dependencies (already supports `depends_on` field)
- `agentcoord/task_queue.py`: Task creation and claiming (SQLite-backed)
- `task_system/`: In-memory task repository (used for coordination layer)

**New components:**
- `agentcoord/workflow_router.py`: Core routing logic
- `agentcoord/work_artifacts.py`: Epic, Story, WorkArtifact models
- `agentcoord/workflow_definitions.py`: Workflow type configurations

---

## Data Models

### WorkArtifact (Base Class)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class ArtifactStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

@dataclass
class WorkArtifact(ABC):
    """Base class for all work items (Epic, Story, Task)."""

    id: str
    title: str
    description: str
    status: ArtifactStatus
    created_by: str  # agent_id or role name
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @abstractmethod
    def can_start(self) -> bool:
        """Check if this work item can be started."""
        pass

    @abstractmethod
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        pass
```

### Epic

```python
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class Epic(WorkArtifact):
    """
    Large body of work that generates multiple tasks via workflow routing.

    Examples:
    - "Add IV Percentile Filter" (trading_strategy workflow)
    - "User Authentication System" (feature workflow)
    - "Fix Login Bug" (bug workflow)
    """

    workflow_type: str  # "trading_strategy", "feature", "bug", "launch"
    stories: List['Story'] = field(default_factory=list)
    generated_task_ids: List[str] = field(default_factory=list)
    priority: int = 0  # Higher number = higher priority

    # Approval tracking
    approval_gates_required: List[str] = field(default_factory=list)
    approval_gates_completed: List[str] = field(default_factory=list)

    def can_start(self) -> bool:
        """Epic can start if workflow type is valid."""
        return self.workflow_type in WORKFLOW_DEFINITIONS

    def progress_percentage(self) -> float:
        """Calculate percentage based on completed tasks."""
        if not self.generated_task_ids:
            return 0.0

        completed = len([tid for tid in self.generated_task_ids
                        if task_queue.get_task(tid).status == TaskStatus.COMPLETED])
        return (completed / len(self.generated_task_ids)) * 100

    def is_blocked(self) -> bool:
        """Check if any approval gates are blocking progress."""
        return bool(set(self.approval_gates_required) - set(self.approval_gates_completed))
```

### Story

```python
@dataclass
class Story(WorkArtifact):
    """
    Medium-sized work item within an Epic.
    Groups related tasks for better organization.

    Examples:
    - "Design Config Schema" (within "Add IV Percentile Filter" epic)
    - "Backend API Implementation" (within "User Auth" epic)
    """

    epic_id: str
    task_ids: List[str] = field(default_factory=list)
    assigned_role: Optional[str] = None  # Role.PRODUCT_DESIGNER, etc.

    def can_start(self) -> bool:
        """Story can start if Epic is in progress."""
        epic = epic_repository.get(self.epic_id)
        return epic and epic.status == ArtifactStatus.IN_PROGRESS

    def progress_percentage(self) -> float:
        """Calculate percentage based on completed tasks."""
        if not self.task_ids:
            return 0.0

        completed = len([tid for tid in self.task_ids
                        if task_queue.get_task(tid).status == TaskStatus.COMPLETED])
        return (completed / len(self.task_ids)) * 100
```

### TaskTemplate

```python
@dataclass
class TaskTemplate:
    """Template for generating tasks within a workflow."""

    title: str
    description: str
    assigned_role: str  # Role enum value (e.g., "PRODUCT_MANAGER")
    depends_on_step: Optional[int] = None  # Step number this task depends on
    approval_gate: Optional[str] = None  # Approval gate required before claiming
    tags: List[str] = field(default_factory=list)
    estimated_complexity: int = 0  # 0-40 complexity score for planner integration
```

---

## Workflow Definitions

### Workflow Configuration Format

Each workflow type defines a sequence of task templates with dependencies and role assignments.

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class WorkflowDefinition:
    """Defines a complete workflow with tasks and dependencies."""

    name: str  # "trading_strategy", "feature", "bug", "launch"
    description: str
    task_templates: List[TaskTemplate]
    approval_gates: List[str] = field(default_factory=list)
    default_priority: int = 0

# Global registry
WORKFLOW_DEFINITIONS = {
    "trading_strategy": WorkflowDefinition(...),
    "feature": WorkflowDefinition(...),
    "bug": WorkflowDefinition(...),
    "launch": WorkflowDefinition(...),
}
```

### Workflow Type: `trading_strategy`

Based on role_capabilities_matrix.md, a trading strategy workflow follows this sequence:

```python
TRADING_STRATEGY_WORKFLOW = WorkflowDefinition(
    name="trading_strategy",
    description="Develop and deploy a new trading strategy for Janus",
    approval_gates=[
        "strategy_config_schema",  # Designer + EM approve
        "backtest_validation",     # QA_LEAD approves
        "production_trading_deploy" # PM + QA_LEAD + EM approve
    ],
    task_templates=[
        # Step 1: PM defines strategy goals
        TaskTemplate(
            title="Define strategy goals and acceptance criteria",
            description="Create PRD with strategy objectives, risk tolerance, return targets",
            assigned_role="PRODUCT_MANAGER",
            depends_on_step=None,
            tags=["planning", "prd"],
            estimated_complexity=15  # Moderate complexity
        ),

        # Step 2: Designer creates config schema
        TaskTemplate(
            title="Design configuration schema",
            description="Create config schema for strategy parameters",
            assigned_role="PRODUCT_DESIGNER",
            depends_on_step=1,
            approval_gate="strategy_config_schema",
            tags=["design", "schema"],
            estimated_complexity=20
        ),

        # Step 3: Engineer implements filter
        TaskTemplate(
            title="Implement filter logic",
            description="Code the filter implementation with type safety",
            assigned_role="ENGINEER",
            depends_on_step=2,
            tags=["implementation", "filter"],
            estimated_complexity=25
        ),

        # Step 4: Engineer writes tests
        TaskTemplate(
            title="Write unit and integration tests",
            description="Test filter logic with realistic data",
            assigned_role="ENGINEER",
            depends_on_step=3,
            tags=["testing", "implementation"],
            estimated_complexity=20
        ),

        # Step 5: QA runs backtest
        TaskTemplate(
            title="Run backtest with realistic parameters",
            description="Execute backtest over sufficient time period",
            assigned_role="QA_ENGINEER",
            depends_on_step=4,
            tags=["testing", "backtest"],
            estimated_complexity=15
        ),

        # Step 6: QA validates metrics
        TaskTemplate(
            title="Validate backtest metrics",
            description="Verify Sharpe ratio, drawdown, premium capture meet targets",
            assigned_role="QA_LEAD",
            depends_on_step=5,
            approval_gate="backtest_validation",
            tags=["validation", "qa"],
            estimated_complexity=20
        ),

        # Step 7: PM approves for production
        TaskTemplate(
            title="Review and approve strategy for production",
            description="Confirm backtest results align with strategy goals",
            assigned_role="PRODUCT_MANAGER",
            depends_on_step=6,
            approval_gate="production_trading_deploy",
            tags=["approval", "product"],
            estimated_complexity=10
        ),

        # Step 8: SRE deploys to Telegram bot
        TaskTemplate(
            title="Deploy strategy to production Telegram bot",
            description="Deploy configuration and monitor initial performance",
            assigned_role="SRE",
            depends_on_step=7,
            tags=["deployment", "production"],
            estimated_complexity=15
        ),
    ]
)
```

### Workflow Type: `feature`

Standard feature development workflow:

```python
FEATURE_WORKFLOW = WorkflowDefinition(
    name="feature",
    description="Standard feature development workflow",
    approval_gates=[
        "feature_spec",       # PM + EM approve
        "design_mocks",       # PM approves
        "production_deploy",  # EM + QA_LEAD approve
        "public_announcement" # VP_MARKETING approves
    ],
    task_templates=[
        # Step 1: PM creates PRD
        TaskTemplate(
            title="Create product requirements document",
            description="Define feature requirements and acceptance criteria",
            assigned_role="PRODUCT_MANAGER",
            depends_on_step=None,
            approval_gate="feature_spec",
            tags=["planning", "prd"],
            estimated_complexity=15
        ),

        # Step 2: Designer creates mocks
        TaskTemplate(
            title="Create design mocks",
            description="Design user interface and interactions",
            assigned_role="PRODUCT_DESIGNER",
            depends_on_step=1,
            approval_gate="design_mocks",
            tags=["design", "ui"],
            estimated_complexity=20
        ),

        # Step 3: Engineer implements
        TaskTemplate(
            title="Implement feature",
            description="Code the feature according to spec",
            assigned_role="ENGINEER",
            depends_on_step=2,
            tags=["implementation"],
            estimated_complexity=30
        ),

        # Step 4: QA tests
        TaskTemplate(
            title="Test feature",
            description="Execute test plan and verify acceptance criteria",
            assigned_role="QA_ENGINEER",
            depends_on_step=3,
            tags=["testing", "qa"],
            estimated_complexity=20
        ),

        # Step 5: Deploy to production
        TaskTemplate(
            title="Deploy to production",
            description="Deploy feature after approval gates passed",
            assigned_role="SRE",
            depends_on_step=4,
            approval_gate="production_deploy",
            tags=["deployment", "production"],
            estimated_complexity=15
        ),

        # Step 6: Growth launches
        TaskTemplate(
            title="Launch feature to users",
            description="Create launch plan and announce publicly",
            assigned_role="GROWTH_MANAGER",
            depends_on_step=5,
            approval_gate="public_announcement",
            tags=["launch", "marketing"],
            estimated_complexity=15
        ),
    ]
)
```

### Workflow Type: `bug`

Simplified bug fix workflow:

```python
BUG_WORKFLOW = WorkflowDefinition(
    name="bug",
    description="Bug fix and verification workflow",
    approval_gates=["production_deploy"],
    task_templates=[
        # Step 1: QA reproduces bug
        TaskTemplate(
            title="Reproduce and document bug",
            description="Create reproduction steps and capture error logs",
            assigned_role="QA_ENGINEER",
            depends_on_step=None,
            tags=["bug", "reproduction"],
            estimated_complexity=10
        ),

        # Step 2: Engineer fixes bug
        TaskTemplate(
            title="Fix bug and add regression test",
            description="Implement fix with test coverage",
            assigned_role="ENGINEER",
            depends_on_step=1,
            tags=["bug", "fix"],
            estimated_complexity=20
        ),

        # Step 3: QA verifies fix
        TaskTemplate(
            title="Verify bug fix",
            description="Confirm fix resolves issue without regressions",
            assigned_role="QA_ENGINEER",
            depends_on_step=2,
            tags=["verification", "qa"],
            estimated_complexity=10
        ),

        # Step 4: Deploy to production
        TaskTemplate(
            title="Deploy bug fix to production",
            description="Deploy after verification",
            assigned_role="SRE",
            depends_on_step=3,
            approval_gate="production_deploy",
            tags=["deployment", "production"],
            estimated_complexity=10
        ),
    ]
)
```

### Workflow Type: `launch`

Product launch coordination workflow:

```python
LAUNCH_WORKFLOW = WorkflowDefinition(
    name="launch",
    description="Product launch coordination across departments",
    approval_gates=["public_announcement", "production_deploy"],
    task_templates=[
        # Step 1: PM creates launch plan
        TaskTemplate(
            title="Create launch plan",
            description="Define launch timeline and success criteria",
            assigned_role="PRODUCT_MANAGER",
            depends_on_step=None,
            tags=["planning", "launch"],
            estimated_complexity=15
        ),

        # Step 2: Growth creates marketing materials
        TaskTemplate(
            title="Create marketing materials",
            description="Landing page, blog post, social media content",
            assigned_role="GROWTH_MANAGER",
            depends_on_step=1,
            tags=["marketing", "content"],
            estimated_complexity=20
        ),

        # Step 3: Engineer prepares production environment
        TaskTemplate(
            title="Prepare production environment",
            description="Scale infrastructure, configure monitoring",
            assigned_role="SRE",
            depends_on_step=1,
            tags=["infrastructure", "production"],
            estimated_complexity=25
        ),

        # Step 4: QA validates production readiness
        TaskTemplate(
            title="Validate production readiness",
            description="Run smoke tests, verify monitoring",
            assigned_role="QA_ENGINEER",
            depends_on_step=3,
            approval_gate="production_deploy",
            tags=["qa", "validation"],
            estimated_complexity=15
        ),

        # Step 5: Support creates documentation
        TaskTemplate(
            title="Create launch documentation and runbooks",
            description="FAQs, support procedures, escalation paths",
            assigned_role="SUPPORT_LEAD",
            depends_on_step=1,
            tags=["documentation", "support"],
            estimated_complexity=20
        ),

        # Step 6: Growth executes launch
        TaskTemplate(
            title="Execute launch",
            description="Publish marketing materials, monitor metrics",
            assigned_role="GROWTH_MANAGER",
            depends_on_step=[2, 4, 5],  # Depends on multiple tasks
            approval_gate="public_announcement",
            tags=["launch", "marketing"],
            estimated_complexity=15
        ),
    ]
)

# Register all workflows
WORKFLOW_DEFINITIONS = {
    "trading_strategy": TRADING_STRATEGY_WORKFLOW,
    "feature": FEATURE_WORKFLOW,
    "bug": BUG_WORKFLOW,
    "launch": LAUNCH_WORKFLOW,
}
```

---

## WorkflowRouter Implementation

### Core Router Class

```python
from typing import List, Optional, Dict
from agentcoord.tasks import TaskQueue, Task, TaskStatus
from agentcoord.work_artifacts import Epic, Story, WorkArtifact
from agentcoord.workflow_definitions import WORKFLOW_DEFINITIONS, TaskTemplate
import uuid

class WorkflowRouter:
    """
    Routes epics to task generation based on workflow type.
    Automatically creates tasks, assigns roles, and tracks dependencies.
    """

    def __init__(self, task_queue: TaskQueue, epic_repository: 'EpicRepository'):
        self.task_queue = task_queue
        self.epic_repository = epic_repository

    def route_epic(self, epic: Epic) -> List[str]:
        """
        Generate tasks for an epic based on its workflow type.

        Args:
            epic: Epic to route

        Returns:
            List of generated task IDs

        Raises:
            ValueError: If workflow type is invalid
        """
        if epic.workflow_type not in WORKFLOW_DEFINITIONS:
            raise ValueError(f"Unknown workflow type: {epic.workflow_type}")

        workflow = WORKFLOW_DEFINITIONS[epic.workflow_type]
        task_ids = []

        # Store mapping of step number to task ID for dependency resolution
        step_to_task_id = {}

        for step_num, template in enumerate(workflow.task_templates, start=1):
            # Create task from template
            task_id = self._create_task_from_template(
                template=template,
                epic=epic,
                step_num=step_num,
                step_to_task_id=step_to_task_id
            )

            task_ids.append(task_id)
            step_to_task_id[step_num] = task_id

        # Update epic with generated tasks
        epic.generated_task_ids = task_ids
        epic.approval_gates_required = workflow.approval_gates
        epic.status = ArtifactStatus.IN_PROGRESS
        self.epic_repository.update(epic)

        return task_ids

    def _create_task_from_template(
        self,
        template: TaskTemplate,
        epic: Epic,
        step_num: int,
        step_to_task_id: Dict[int, str]
    ) -> str:
        """
        Create a task from a template with dependency resolution.

        Args:
            template: TaskTemplate to instantiate
            epic: Parent epic
            step_num: Step number in workflow
            step_to_task_id: Mapping of step numbers to task IDs

        Returns:
            Created task ID
        """
        # Resolve dependencies
        depends_on = []
        if template.depends_on_step is not None:
            if isinstance(template.depends_on_step, list):
                # Multiple dependencies
                for dep_step in template.depends_on_step:
                    if dep_step in step_to_task_id:
                        depends_on.append(step_to_task_id[dep_step])
            else:
                # Single dependency
                if template.depends_on_step in step_to_task_id:
                    depends_on.append(step_to_task_id[template.depends_on_step])

        # Create task with full context
        description = f"""
{template.description}

**Epic**: {epic.title}
**Workflow**: {epic.workflow_type}
**Step**: {step_num}
**Assigned Role**: {template.assigned_role}
{f"**Approval Gate**: {template.approval_gate}" if template.approval_gate else ""}
"""

        task_id = self.task_queue.create_task(
            title=f"[{epic.title}] {template.title}",
            description=description.strip(),
            depends_on=depends_on
        )

        # Tag task with metadata for assignment
        task = self.task_queue.get_task(task_id)
        task.metadata = {
            'epic_id': epic.id,
            'assigned_role': template.assigned_role,
            'approval_gate': template.approval_gate,
            'workflow_type': epic.workflow_type,
            'step_num': step_num,
            'estimated_complexity': template.estimated_complexity,
            'tags': template.tags,
        }
        self.task_queue.update_task(task_id, metadata=task.metadata)

        return task_id

    def get_next_available_task(self, agent_role: str) -> Optional[Task]:
        """
        Get next available task for an agent based on their role.

        Respects:
        - Task dependencies (only returns unblocked tasks)
        - Role assignments (only returns tasks for agent's role)
        - Approval gates (blocks tasks requiring unapproved gates)

        Args:
            agent_role: Role of claiming agent (e.g., "PRODUCT_MANAGER")

        Returns:
            Next available task or None if no tasks available
        """
        # Get ready tasks (dependencies met, status=PENDING)
        ready_tasks = self.task_queue.get_ready_tasks()

        for task in ready_tasks:
            # Check role match
            if task.metadata.get('assigned_role') != agent_role:
                continue

            # Check approval gate
            if task.metadata.get('approval_gate'):
                epic_id = task.metadata.get('epic_id')
                if epic_id:
                    epic = self.epic_repository.get(epic_id)
                    approval_gate = task.metadata.get('approval_gate')

                    # Task blocked if approval gate not completed
                    if approval_gate not in epic.approval_gates_completed:
                        continue

            # Task is available for claiming
            return task

        return None

    def claim_next_task(self, agent_id: str, agent_role: str) -> Optional[Task]:
        """
        Claim next available task for an agent.

        Args:
            agent_id: Unique agent identifier
            agent_role: Role of agent (e.g., "ENGINEER")

        Returns:
            Claimed task or None if no tasks available
        """
        task = self.get_next_available_task(agent_role)

        if task:
            # Use existing task queue claiming logic
            claimed = self.task_queue.claim_task(agent_id)
            if claimed and claimed.id == task.id:
                return claimed

        return None

    def complete_approval_gate(self, epic_id: str, gate_name: str, approver_role: str):
        """
        Mark an approval gate as completed.

        This unblocks tasks that depend on this gate.

        Args:
            epic_id: Epic containing the approval gate
            gate_name: Name of gate (e.g., "production_trading_deploy")
            approver_role: Role of approving agent

        Raises:
            ValueError: If approver doesn't have authority for this gate
        """
        from agentcoord.roles import RoleCapabilities, ApprovalGate

        # Validate approver has authority
        gate_def = ApprovalGate.GATES.get(gate_name, [])
        if approver_role not in gate_def:
            raise ValueError(
                f"Role {approver_role} cannot approve gate {gate_name}. "
                f"Required roles: {gate_def}"
            )

        # Mark gate as completed
        epic = self.epic_repository.get(epic_id)
        if gate_name not in epic.approval_gates_completed:
            epic.approval_gates_completed.append(gate_name)
            self.epic_repository.update(epic)
```

### Agent Assignment Algorithm

The router assigns tasks based on:

1. **Role matching**: Task's `assigned_role` must match agent's role
2. **Dependency satisfaction**: All `depends_on` tasks must be completed
3. **Approval gate status**: Task's approval gate (if any) must be completed

```python
def claim_algorithm(agent_role: str) -> Optional[Task]:
    """
    Pseudo-code for task claiming algorithm.

    Returns first task matching ALL conditions:
    1. status == PENDING
    2. depends_on tasks all COMPLETED
    3. assigned_role == agent_role
    4. approval_gate (if exists) is completed

    Priority:
    - Higher priority epics first
    - Lower step numbers first (earlier in workflow)
    """
    for epic in epics_sorted_by_priority_desc():
        for task in tasks_sorted_by_step_asc():
            if task.status != PENDING:
                continue
            if not all_dependencies_completed(task):
                continue
            if task.assigned_role != agent_role:
                continue
            if task.approval_gate and not is_gate_completed(epic, task.approval_gate):
                continue

            return task

    return None
```

---

## Task Dependency Tracking

### Dependency Model

Dependencies are tracked at the Task level using the existing `depends_on` field:

```python
@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus
    depends_on: List[str] = None  # List of task IDs
    # ... other fields
```

### Dependency Resolution

When creating tasks from workflow templates:

```python
# Template defines dependency as step number
template = TaskTemplate(
    title="Deploy to production",
    depends_on_step=4,  # Depends on step 4 (testing)
)

# Router resolves to actual task ID
step_to_task_id = {
    1: "task-001",
    2: "task-002",
    3: "task-003",
    4: "task-004",  # Testing task
}

task_id = create_task(
    title="Deploy to production",
    depends_on=["task-004"]  # Resolved dependency
)
```

### Multiple Dependencies

Some tasks depend on multiple previous tasks:

```python
# Template with multiple dependencies
template = TaskTemplate(
    title="Execute launch",
    depends_on_step=[2, 4, 5],  # Depends on marketing, QA, and support
)

# Resolves to multiple task IDs
task_id = create_task(
    title="Execute launch",
    depends_on=["task-002", "task-004", "task-005"]
)
```

### Dependency Graph Visualization

The existing `TaskQueue.get_dependency_graph()` method provides graph structure:

```python
graph = task_queue.get_dependency_graph()

# Returns:
# {
#     "task-001": {
#         "title": "Define strategy goals",
#         "status": "completed",
#         "depends_on": [],
#         "dependents": ["task-002"]
#     },
#     "task-002": {
#         "title": "Design config schema",
#         "status": "pending",
#         "depends_on": ["task-001"],
#         "dependents": ["task-003"]
#     },
#     ...
# }
```

---

## Example Usage Patterns

### Pattern 1: Create Epic and Auto-Generate Tasks

```python
from agentcoord.workflow_router import WorkflowRouter
from agentcoord.work_artifacts import Epic, ArtifactStatus
from agentcoord.tasks import TaskQueue

# Initialize
task_queue = TaskQueue(db_path="company_tasks.db")
epic_repository = EpicRepository()
router = WorkflowRouter(task_queue, epic_repository)

# PM creates epic
epic = Epic(
    id=str(uuid.uuid4()),
    title="Add IV Percentile Filter",
    description="Add new IV percentile filter to Janus strategy",
    status=ArtifactStatus.PENDING,
    workflow_type="trading_strategy",
    created_by="PM-001",
    priority=5
)

epic_repository.create(epic)

# Route epic to generate all tasks
task_ids = router.route_epic(epic)

# Result: 8 tasks created with dependencies
# Task 1: Define strategy goals (PM) - no dependencies
# Task 2: Design config schema (Designer) - depends on Task 1
# Task 3: Implement filter (Engineer) - depends on Task 2
# Task 4: Write tests (Engineer) - depends on Task 3
# Task 5: Run backtest (QA) - depends on Task 4
# Task 6: Validate metrics (QA_LEAD) - depends on Task 5
# Task 7: Approve for production (PM) - depends on Task 6
# Task 8: Deploy to bot (SRE) - depends on Task 7
```

### Pattern 2: Agent Claims Next Task

```python
from agentcoord.agent import Agent

# Agent with role
pm_agent = Agent(
    agent_id="PM-001",
    role="PRODUCT_MANAGER",
    redis_client=redis_client
)

# Agent claims next available task for their role
task = router.claim_next_task(
    agent_id=pm_agent.agent_id,
    agent_role=pm_agent.role
)

if task:
    print(f"Claimed: {task.title}")
    # Work on task...
    task_queue.complete_task(task.id)
else:
    print("No tasks available for PRODUCT_MANAGER role")
```

### Pattern 3: Approval Gate Workflow

```python
# QA_LEAD validates backtest metrics
qa_lead = Agent(agent_id="QA-LEAD-001", role="QA_LEAD")

# Claim validation task
task = router.claim_next_task(qa_lead.agent_id, qa_lead.role)
# Task: "Validate backtest metrics"

# Perform validation...
metrics_valid = validate_sharpe_ratio() and validate_drawdown()

if metrics_valid:
    # Complete task
    task_queue.complete_task(task.id, result="Metrics validated: Sharpe 1.8, DD -12%")

    # Complete approval gate
    router.complete_approval_gate(
        epic_id=task.metadata['epic_id'],
        gate_name="backtest_validation",
        approver_role="QA_LEAD"
    )

    # This unblocks the next task (PM review)
```

### Pattern 4: Multi-Department Coordination

```python
# Multiple agents working on same epic
pm = Agent(agent_id="PM-001", role="PRODUCT_MANAGER")
designer = Agent(agent_id="DESIGNER-001", role="PRODUCT_DESIGNER")
engineer = Agent(agent_id="ENG-001", role="ENGINEER")
qa = Agent(agent_id="QA-001", role="QA_ENGINEER")

# PM claims first task
task1 = router.claim_next_task(pm.agent_id, pm.role)
# Claims: "Define strategy goals"
task_queue.complete_task(task1.id)

# Now designer can claim their task (dependency met)
task2 = router.claim_next_task(designer.agent_id, designer.role)
# Claims: "Design config schema"
task_queue.complete_task(task2.id)

# Designer must get approval gate before engineer can proceed
router.complete_approval_gate(
    epic_id=task2.metadata['epic_id'],
    gate_name="strategy_config_schema",
    approver_role="PRODUCT_DESIGNER"
)

# Now engineer can claim
task3 = router.claim_next_task(engineer.agent_id, engineer.role)
# Claims: "Implement filter logic"
```

### Pattern 5: Epic Progress Tracking

```python
# Check epic progress
epic = epic_repository.get(epic_id)

print(f"Epic: {epic.title}")
print(f"Progress: {epic.progress_percentage():.1f}%")
print(f"Status: {epic.status.value}")

if epic.is_blocked():
    pending_gates = set(epic.approval_gates_required) - set(epic.approval_gates_completed)
    print(f"Blocked on gates: {pending_gates}")

# List remaining tasks
for task_id in epic.generated_task_ids:
    task = task_queue.get_task(task_id)
    if task.status != TaskStatus.COMPLETED:
        print(f"  - {task.title} ({task.status.value})")
```

---

## Integration with Existing Systems

### Task Queue Integration

WorkflowRouter uses the existing `TaskQueue` from `agentcoord/tasks.py`:

```python
# Existing TaskQueue methods used:
task_queue.create_task(title, description, depends_on=[...])
task_queue.get_task(task_id)
task_queue.get_ready_tasks()  # Returns tasks with dependencies met
task_queue.claim_task(agent_id)
task_queue.complete_task(task_id, result)
task_queue.get_dependency_graph()
```

No changes required to existing `TaskQueue` implementation.

### Planner Integration

WorkflowRouter enriches tasks with complexity estimates for the TaskPlanner:

```python
# Task metadata includes complexity for planner
task.metadata = {
    'estimated_complexity': 25,  # From TaskTemplate
    'tags': ['implementation', 'filter'],
}

# TaskPlanner can use this for cost estimation
planner = TaskPlanner()
plan = planner.create_execution_plan(
    tasks=task_queue.get_all_tasks(),
    optimization_mode=OptimizationMode.BALANCED
)

print(f"Estimated cost: ${plan.total_estimated_cost:.2f}")
```

### Company Hierarchy Integration

WorkflowRouter will integrate with the Company model (Task #12):

```python
# Future: Router aware of company structure
router = WorkflowRouter(
    task_queue=task_queue,
    epic_repository=epic_repository,
    company=company  # Company instance with departments/teams
)

# Assign tasks to specific teams
task.metadata['team_id'] = company.get_team_for_role(assigned_role)
```

---

## Testing Strategy

### Unit Tests

```python
# Test workflow definition registration
def test_workflow_registration():
    assert "trading_strategy" in WORKFLOW_DEFINITIONS
    assert "feature" in WORKFLOW_DEFINITIONS

# Test task generation from epic
def test_route_epic_generates_tasks():
    epic = Epic(
        id="epic-1",
        title="Test Epic",
        workflow_type="bug",
        ...
    )

    task_ids = router.route_epic(epic)
    assert len(task_ids) == 4  # Bug workflow has 4 tasks

# Test dependency resolution
def test_dependencies_resolved():
    epic = Epic(workflow_type="trading_strategy", ...)
    task_ids = router.route_epic(epic)

    # Task 2 should depend on Task 1
    task2 = task_queue.get_task(task_ids[1])
    assert task_ids[0] in task2.depends_on

# Test role assignment
def test_agent_claims_correct_role():
    epic = Epic(workflow_type="feature", ...)
    router.route_epic(epic)

    # Designer should only get designer tasks
    task = router.get_next_available_task("PRODUCT_DESIGNER")
    assert task.metadata['assigned_role'] == "PRODUCT_DESIGNER"

# Test approval gate blocking
def test_approval_gate_blocks_task():
    epic = Epic(workflow_type="trading_strategy", ...)
    task_ids = router.route_epic(epic)

    # Complete all dependencies for deployment task
    for i in range(7):
        task_queue.complete_task(task_ids[i])

    # SRE should NOT be able to claim deploy task (gate not approved)
    task = router.get_next_available_task("SRE")
    assert task is None

    # After PM approves gate, SRE can claim
    router.complete_approval_gate(epic.id, "production_trading_deploy", "PRODUCT_MANAGER")
    task = router.get_next_available_task("SRE")
    assert task is not None
```

### Integration Tests

```python
# Test full workflow execution
def test_trading_strategy_workflow_end_to_end():
    epic = Epic(workflow_type="trading_strategy", ...)
    router.route_epic(epic)

    # Simulate agents working through workflow
    roles = [
        "PRODUCT_MANAGER",
        "PRODUCT_DESIGNER",
        "ENGINEER",
        "ENGINEER",
        "QA_ENGINEER",
        "QA_LEAD",
        "PRODUCT_MANAGER",
        "SRE"
    ]

    for role in roles:
        task = router.claim_next_task(f"agent-{role}", role)
        assert task is not None
        task_queue.complete_task(task.id)

        # Handle approval gates
        if task.metadata.get('approval_gate'):
            router.complete_approval_gate(
                epic.id,
                task.metadata['approval_gate'],
                role
            )

    # Epic should be 100% complete
    epic = epic_repository.get(epic.id)
    assert epic.progress_percentage() == 100.0
```

---

## Future Enhancements

1. **Story Support**: Group tasks into stories for better organization
2. **Dynamic Workflows**: Allow custom workflow definitions via config files
3. **Parallel Paths**: Support parallel task execution within workflows
4. **Conditional Steps**: Skip tasks based on runtime conditions
5. **Workflow Templates**: Pre-built templates for common patterns
6. **Progress Visualization**: Gantt chart view of workflow progress
7. **Workflow Analytics**: Track time-to-complete by workflow type
8. **Multi-Epic Coordination**: Dependencies across epics

---

## Files to Create

1. **agentcoord/work_artifacts.py**: Epic, Story, WorkArtifact models
2. **agentcoord/workflow_definitions.py**: Workflow type configurations
3. **agentcoord/workflow_router.py**: WorkflowRouter implementation
4. **agentcoord/epic_repository.py**: CRUD for epics (similar to TaskRepository)
5. **tests/test_workflow_router.py**: Comprehensive test suite

---

## Dependencies

- `agentcoord/tasks.py`: Existing Task model with `depends_on` field
- `agentcoord/task_queue.py`: Existing TaskQueue with SQLite backend
- `agentcoord/roles.py`: (Task #9) Role definitions and capabilities
- `agentcoord/company.py`: (Task #12) Company hierarchy (future integration)

---

## Summary

The WorkflowRouter system provides automated workflow orchestration by:

1. **Defining workflows** as sequences of task templates with roles and dependencies
2. **Routing epics** to generate all required tasks automatically
3. **Assigning tasks** to agents based on role matching and dependency satisfaction
4. **Tracking progress** through approval gates and dependency chains
5. **Integrating** with existing task queue and future company hierarchy

This eliminates manual task creation, ensures consistent workflows, and enables autonomous agent coordination across departments.
