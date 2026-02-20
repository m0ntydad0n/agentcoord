"""Workflow routing system for cross-functional task coordination.

This module provides Epic, Story, Task abstractions and automated workflow routing
based on predefined workflow types (feature, bug, launch, trading_strategy).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
import uuid

from agentcoord.roles import Role


class ArtifactStatus(str, Enum):
    """Status of a work artifact (Epic, Story, Task)."""

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
    metadata: Dict = field(default_factory=dict)

    @abstractmethod
    def can_start(self) -> bool:
        """Check if this work item can be started."""
        pass

    @abstractmethod
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        pass


@dataclass
class TaskTemplate:
    """Template for generating tasks within a workflow."""

    title: str
    description: str
    assigned_role: Role
    depends_on_step: Optional[int] = None
    approval_gate: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    estimated_complexity: int = 0


@dataclass
class WorkflowDefinition:
    """Defines a complete workflow with tasks and dependencies."""

    name: str
    description: str
    task_templates: List[TaskTemplate]
    approval_gates: List[str] = field(default_factory=list)
    default_priority: int = 0


@dataclass
class Epic(WorkArtifact):
    """Large body of work that generates multiple tasks via workflow routing.

    Examples:
    - "Add IV Percentile Filter" (trading_strategy workflow)
    - "User Authentication System" (feature workflow)
    - "Fix Login Bug" (bug workflow)
    """

    workflow_type: str = ""
    stories: List['Story'] = field(default_factory=list)
    generated_task_ids: List[str] = field(default_factory=list)
    priority: int = 0

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

        # This would integrate with actual task system
        # For now, return simple ratio
        return 0.0

    def is_blocked(self) -> bool:
        """Check if any approval gates are blocking progress."""
        return bool(
            set(self.approval_gates_required) - set(self.approval_gates_completed)
        )


@dataclass
class Story(WorkArtifact):
    """Medium-sized work item within an Epic.

    Examples:
    - "Design Config Schema" (within "Add IV Percentile Filter" epic)
    - "Backend API Implementation" (within "User Auth" epic)
    """

    epic_id: str = ""
    task_ids: List[str] = field(default_factory=list)
    assigned_role: Optional[Role] = None

    def can_start(self) -> bool:
        """Story can start if Epic is in progress."""
        # Would integrate with epic repository
        return True

    def progress_percentage(self) -> float:
        """Calculate percentage based on completed tasks."""
        if not self.task_ids:
            return 0.0

        # Would integrate with task system
        return 0.0


# Workflow Definitions

TRADING_STRATEGY_WORKFLOW = WorkflowDefinition(
    name="trading_strategy",
    description="Develop and deploy a new trading strategy for Janus",
    approval_gates=[
        "strategy_config_schema",
        "backtest_validation",
        "production_trading_deploy",
    ],
    default_priority=1,
    task_templates=[
        TaskTemplate(
            title="Define strategy goals and acceptance criteria",
            description="Create PRD with strategy objectives, risk tolerance, return targets",
            assigned_role=Role.PRODUCT_MANAGER,
            depends_on_step=None,
            tags=["planning", "prd"],
            estimated_complexity=15,
        ),
        TaskTemplate(
            title="Design configuration schema",
            description="Create YAML config schema for strategy parameters",
            assigned_role=Role.PRODUCT_DESIGNER,
            depends_on_step=1,
            approval_gate="strategy_config_schema",
            tags=["design", "schema"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Implement filter logic",
            description="Code the filter implementation with type safety and docstrings",
            assigned_role=Role.ENGINEER,
            depends_on_step=2,
            tags=["implementation", "filter"],
            estimated_complexity=25,
        ),
        TaskTemplate(
            title="Write unit and integration tests",
            description="Test filter logic with realistic market data fixtures",
            assigned_role=Role.ENGINEER,
            depends_on_step=3,
            tags=["testing", "implementation"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Run backtest with realistic parameters",
            description="Execute backtest over 12+ months of historical data",
            assigned_role=Role.QA_ENGINEER,
            depends_on_step=4,
            tags=["testing", "backtest"],
            estimated_complexity=15,
        ),
        TaskTemplate(
            title="Validate backtest metrics",
            description="Verify Sharpe ratio, max drawdown, premium capture meet targets",
            assigned_role=Role.QA_LEAD,
            depends_on_step=5,
            approval_gate="backtest_validation",
            tags=["validation", "qa"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Review and approve strategy for production",
            description="Confirm backtest results align with strategy goals and risk tolerance",
            assigned_role=Role.PRODUCT_MANAGER,
            depends_on_step=6,
            approval_gate="production_trading_deploy",
            tags=["approval", "production"],
            estimated_complexity=10,
        ),
        TaskTemplate(
            title="Deploy to Telegram bot",
            description="Deploy strategy to live trading environment with monitoring",
            assigned_role=Role.SRE,
            depends_on_step=7,
            tags=["deployment", "production"],
            estimated_complexity=15,
        ),
    ],
)

FEATURE_WORKFLOW = WorkflowDefinition(
    name="feature",
    description="Standard feature development from PRD to production launch",
    approval_gates=["design_review", "code_review", "qa_signoff", "production_release"],
    default_priority=0,
    task_templates=[
        TaskTemplate(
            title="Write PRD",
            description="Document problem statement, acceptance criteria, success metrics",
            assigned_role=Role.PRODUCT_MANAGER,
            depends_on_step=None,
            approval_gate="design_kickoff",
            tags=["planning", "prd"],
            estimated_complexity=15,
        ),
        TaskTemplate(
            title="Create design mocks",
            description="Design UI/UX mockups, user flows, accessibility considerations",
            assigned_role=Role.PRODUCT_DESIGNER,
            depends_on_step=1,
            approval_gate="design_review",
            tags=["design", "ux"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Implement feature",
            description="Build feature with unit tests (>90% coverage) and documentation",
            assigned_role=Role.ENGINEER,
            depends_on_step=2,
            approval_gate="code_review",
            tags=["implementation"],
            estimated_complexity=30,
        ),
        TaskTemplate(
            title="QA testing",
            description="Execute test plan, regression tests, performance validation",
            assigned_role=Role.QA_ENGINEER,
            depends_on_step=3,
            approval_gate="qa_signoff",
            tags=["testing", "qa"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Approve release",
            description="Review metrics, make go/no-go decision, prepare rollback plan",
            assigned_role=Role.PRODUCT_MANAGER,
            depends_on_step=4,
            approval_gate="production_release",
            tags=["approval", "release"],
            estimated_complexity=10,
        ),
        TaskTemplate(
            title="Launch feature",
            description="Execute launch: marketing content, user docs, support briefing, analytics setup",
            assigned_role=Role.GROWTH_MANAGER,
            depends_on_step=5,
            tags=["launch", "marketing"],
            estimated_complexity=25,
        ),
    ],
)

BUG_WORKFLOW = WorkflowDefinition(
    name="bug",
    description="Rapid bug diagnosis, fix, and verification",
    approval_gates=["triage", "code_review", "qa_verification"],
    default_priority=2,
    task_templates=[
        TaskTemplate(
            title="Reproduce bug",
            description="Create minimal reproduction case, document expected vs actual behavior",
            assigned_role=Role.QA_ENGINEER,
            depends_on_step=None,
            approval_gate="triage",
            tags=["bug", "reproduction"],
            estimated_complexity=10,
        ),
        TaskTemplate(
            title="Fix bug",
            description="Implement fix with regression test (fails before, passes after)",
            assigned_role=Role.ENGINEER,
            depends_on_step=1,
            approval_gate="code_review",
            tags=["bug", "fix"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Verify fix",
            description="Confirm bug no longer reproduces, regression tests pass, no new issues",
            assigned_role=Role.QA_ENGINEER,
            depends_on_step=2,
            approval_gate="qa_verification",
            tags=["verification", "qa"],
            estimated_complexity=10,
        ),
    ],
)

LAUNCH_WORKFLOW = WorkflowDefinition(
    name="launch",
    description="Cross-functional product launch coordination",
    approval_gates=["launch_plan_review", "readiness_check"],
    default_priority=1,
    task_templates=[
        TaskTemplate(
            title="Create launch plan",
            description="Define launch timeline, success metrics, rollback criteria",
            assigned_role=Role.PRODUCT_MANAGER,
            depends_on_step=None,
            approval_gate="launch_plan_review",
            tags=["planning", "launch"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Create marketing content",
            description="Write blog post, release notes, social media content",
            assigned_role=Role.GROWTH_MANAGER,
            depends_on_step=1,
            tags=["marketing", "content"],
            estimated_complexity=25,
        ),
        TaskTemplate(
            title="Implement feature flags",
            description="Add feature flags and gradual rollout controls",
            assigned_role=Role.ENGINEER,
            depends_on_step=1,
            tags=["implementation", "flags"],
            estimated_complexity=15,
        ),
        TaskTemplate(
            title="Regression testing",
            description="Run full regression suite, validate no existing features broken",
            assigned_role=Role.QA_ENGINEER,
            depends_on_step=3,
            tags=["testing", "regression"],
            estimated_complexity=15,
        ),
        TaskTemplate(
            title="Prepare support documentation",
            description="Create FAQs, troubleshooting guides, internal knowledge base",
            assigned_role=Role.SUPPORT_LEAD,
            depends_on_step=1,
            tags=["documentation", "support"],
            estimated_complexity=20,
        ),
        TaskTemplate(
            title="Execute launch",
            description="Enable feature flags, publish content, monitor metrics",
            assigned_role=Role.GROWTH_MANAGER,
            depends_on_step=4,
            approval_gate="readiness_check",
            tags=["launch", "execution"],
            estimated_complexity=15,
        ),
    ],
)

# Global workflow registry
WORKFLOW_DEFINITIONS: Dict[str, WorkflowDefinition] = {
    "trading_strategy": TRADING_STRATEGY_WORKFLOW,
    "feature": FEATURE_WORKFLOW,
    "bug": BUG_WORKFLOW,
    "launch": LAUNCH_WORKFLOW,
}


class WorkflowRouter:
    """Routes epics to appropriate workflow and generates tasks."""

    def __init__(self, company=None):
        """Initialize router with optional company for agent assignment.

        Args:
            company: Company instance for finding available agents by role
        """
        self.company = company

    def route_epic(self, epic: Epic) -> List[str]:
        """Generate tasks for an epic based on its workflow type.

        Args:
            epic: Epic to route

        Returns:
            List of generated task IDs

        Raises:
            ValueError: If workflow type is invalid
        """
        if epic.workflow_type not in WORKFLOW_DEFINITIONS:
            raise ValueError(
                f"Unknown workflow type: {epic.workflow_type}. "
                f"Available: {list(WORKFLOW_DEFINITIONS.keys())}"
            )

        workflow = WORKFLOW_DEFINITIONS[epic.workflow_type]
        task_ids = []
        step_to_task_id = {}

        for step_num, template in enumerate(workflow.task_templates, start=1):
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            step_to_task_id[step_num] = task_id

            # Build task data structure
            # This would integrate with actual task creation system
            task_data = {
                "id": task_id,
                "title": f"{epic.title}: {template.title}",
                "description": template.description,
                "assigned_role": template.assigned_role,
                "tags": template.tags + [epic.workflow_type, f"epic:{epic.id}"],
                "estimated_complexity": template.estimated_complexity,
                "depends_on": [],
                "approval_gate": template.approval_gate,
                "metadata": {
                    "epic_id": epic.id,
                    "workflow_type": epic.workflow_type,
                    "step_number": step_num,
                },
            }

            # Set dependencies
            if template.depends_on_step is not None:
                dependency_task_id = step_to_task_id.get(template.depends_on_step)
                if dependency_task_id:
                    task_data["depends_on"] = [dependency_task_id]

            # Would create actual task here via task system
            # task_queue.create_task(**task_data)

        epic.generated_task_ids = task_ids
        epic.approval_gates_required = workflow.approval_gates
        epic.status = ArtifactStatus.IN_PROGRESS

        return task_ids

    def get_next_available_task(self, agent_role: Role, epic: Epic) -> Optional[str]:
        """Find next available task for a role within an epic.

        Args:
            agent_role: Role to find tasks for
            epic: Epic to search within

        Returns:
            Task ID if available, None otherwise
        """
        # This would integrate with task system to find:
        # - Tasks assigned to agent_role
        # - Not yet claimed
        # - Dependencies satisfied
        # - Not blocked by approval gates

        return None

    def complete_approval_gate(self, epic: Epic, gate_name: str, approver: str):
        """Mark an approval gate as completed.

        Args:
            epic: Epic containing the gate
            gate_name: Name of the gate
            approver: Agent ID or role who approved
        """
        if gate_name in epic.approval_gates_required:
            if gate_name not in epic.approval_gates_completed:
                epic.approval_gates_completed.append(gate_name)
                epic.updated_at = datetime.now().isoformat()
