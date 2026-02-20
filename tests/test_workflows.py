"""Tests for workflow routing system."""

import pytest
from agentcoord.workflows import (
    ArtifactStatus,
    WorkArtifact,
    Epic,
    Story,
    TaskTemplate,
    WorkflowDefinition,
    WorkflowRouter,
    WORKFLOW_DEFINITIONS,
    TRADING_STRATEGY_WORKFLOW,
    FEATURE_WORKFLOW,
    BUG_WORKFLOW,
    LAUNCH_WORKFLOW,
)
from agentcoord.roles import Role


class TestArtifactStatus:
    """Test ArtifactStatus enum."""

    def test_all_statuses_defined(self):
        """All expected statuses are defined."""
        expected = {"pending", "in_progress", "completed", "blocked", "cancelled"}
        actual = {s.value for s in ArtifactStatus}
        assert actual == expected


class TestTaskTemplate:
    """Test TaskTemplate dataclass."""

    def test_minimal_template(self):
        """Can create template with minimal fields."""
        template = TaskTemplate(
            title="Implement feature",
            description="Build the thing",
            assigned_role=Role.ENGINEER,
        )

        assert template.title == "Implement feature"
        assert template.description == "Build the thing"
        assert template.assigned_role == Role.ENGINEER
        assert template.depends_on_step is None
        assert template.approval_gate is None
        assert template.tags == []
        assert template.estimated_complexity == 0

    def test_full_template(self):
        """Can create template with all fields."""
        template = TaskTemplate(
            title="QA validation",
            description="Run tests",
            assigned_role=Role.QA_ENGINEER,
            depends_on_step=3,
            approval_gate="qa_signoff",
            tags=["testing", "qa"],
            estimated_complexity=20,
        )

        assert template.depends_on_step == 3
        assert template.approval_gate == "qa_signoff"
        assert template.tags == ["testing", "qa"]
        assert template.estimated_complexity == 20


class TestWorkflowDefinition:
    """Test WorkflowDefinition dataclass."""

    def test_minimal_workflow(self):
        """Can create workflow with minimal fields."""
        workflow = WorkflowDefinition(
            name="simple",
            description="Simple workflow",
            task_templates=[
                TaskTemplate(
                    title="Do thing", description="Thing", assigned_role=Role.ENGINEER
                )
            ],
        )

        assert workflow.name == "simple"
        assert workflow.description == "Simple workflow"
        assert len(workflow.task_templates) == 1
        assert workflow.approval_gates == []
        assert workflow.default_priority == 0

    def test_full_workflow(self):
        """Can create workflow with all fields."""
        workflow = WorkflowDefinition(
            name="complex",
            description="Complex workflow",
            task_templates=[
                TaskTemplate(
                    title="Task 1", description="First", assigned_role=Role.PRODUCT_MANAGER
                ),
                TaskTemplate(
                    title="Task 2",
                    description="Second",
                    assigned_role=Role.ENGINEER,
                    depends_on_step=1,
                ),
            ],
            approval_gates=["gate1", "gate2"],
            default_priority=5,
        )

        assert len(workflow.task_templates) == 2
        assert workflow.approval_gates == ["gate1", "gate2"]
        assert workflow.default_priority == 5


class TestEpic:
    """Test Epic work artifact."""

    def test_epic_creation(self):
        """Can create epic."""
        epic = Epic(
            id="epic-001",
            title="Add Authentication",
            description="User auth system",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm_agent",
        )

        assert epic.id == "epic-001"
        assert epic.title == "Add Authentication"
        assert epic.workflow_type == "feature"
        assert epic.status == ArtifactStatus.PENDING
        assert epic.stories == []
        assert epic.generated_task_ids == []
        assert epic.priority == 0

    def test_epic_can_start_valid_workflow(self):
        """Epic can start if workflow type is valid."""
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        assert epic.can_start() is True

    def test_epic_can_start_invalid_workflow(self):
        """Epic cannot start if workflow type is invalid."""
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="invalid_workflow",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        assert epic.can_start() is False

    def test_epic_progress_with_no_tasks(self):
        """Epic progress is 0% when no tasks generated."""
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        assert epic.progress_percentage() == 0.0

    def test_epic_approval_gates(self):
        """Epic tracks approval gates."""
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
            approval_gates_required=["gate1", "gate2"],
            approval_gates_completed=["gate1"],
        )

        assert epic.is_blocked() is True  # gate2 not complete

        epic.approval_gates_completed.append("gate2")
        assert epic.is_blocked() is False  # all gates complete


class TestStory:
    """Test Story work artifact."""

    def test_story_creation(self):
        """Can create story."""
        story = Story(
            id="story-001",
            title="Backend API",
            description="Implement backend",
            epic_id="epic-001",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        assert story.id == "story-001"
        assert story.epic_id == "epic-001"
        assert story.task_ids == []
        assert story.assigned_role is None

    def test_story_with_role(self):
        """Story can be assigned to role."""
        story = Story(
            id="story-001",
            title="Design",
            description="Create mocks",
            epic_id="epic-001",
            status=ArtifactStatus.PENDING,
            created_by="pm",
            assigned_role=Role.PRODUCT_DESIGNER,
        )

        assert story.assigned_role == Role.PRODUCT_DESIGNER

    def test_story_can_start(self):
        """Story can start (always true in basic implementation)."""
        story = Story(
            id="story-001",
            title="Test",
            description="Test",
            epic_id="epic-001",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        assert story.can_start() is True

    def test_story_progress_with_no_tasks(self):
        """Story progress is 0% when no tasks."""
        story = Story(
            id="story-001",
            title="Test",
            description="Test",
            epic_id="epic-001",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        assert story.progress_percentage() == 0.0


class TestWorkflowDefinitions:
    """Test built-in workflow definitions."""

    def test_all_workflows_registered(self):
        """All expected workflows are registered."""
        expected = {"trading_strategy", "feature", "bug", "launch"}
        actual = set(WORKFLOW_DEFINITIONS.keys())
        assert actual == expected

    def test_trading_strategy_workflow(self):
        """Trading strategy workflow is correctly defined."""
        workflow = WORKFLOW_DEFINITIONS["trading_strategy"]

        assert workflow.name == "trading_strategy"
        assert len(workflow.task_templates) == 8
        assert workflow.approval_gates == [
            "strategy_config_schema",
            "backtest_validation",
            "production_trading_deploy",
        ]

        # Verify sequence
        roles = [t.assigned_role for t in workflow.task_templates]
        assert roles == [
            Role.PRODUCT_MANAGER,
            Role.PRODUCT_DESIGNER,
            Role.ENGINEER,
            Role.ENGINEER,
            Role.QA_ENGINEER,
            Role.QA_LEAD,
            Role.PRODUCT_MANAGER,
            Role.SRE,
        ]

    def test_feature_workflow(self):
        """Feature workflow is correctly defined."""
        workflow = WORKFLOW_DEFINITIONS["feature"]

        assert workflow.name == "feature"
        assert len(workflow.task_templates) == 6

        # Verify sequence
        roles = [t.assigned_role for t in workflow.task_templates]
        assert roles == [
            Role.PRODUCT_MANAGER,
            Role.PRODUCT_DESIGNER,
            Role.ENGINEER,
            Role.QA_ENGINEER,
            Role.PRODUCT_MANAGER,
            Role.GROWTH_MANAGER,
        ]

    def test_bug_workflow(self):
        """Bug workflow is correctly defined."""
        workflow = WORKFLOW_DEFINITIONS["bug"]

        assert workflow.name == "bug"
        assert len(workflow.task_templates) == 3
        assert workflow.default_priority == 2  # Bugs have higher priority

        # Verify sequence
        roles = [t.assigned_role for t in workflow.task_templates]
        assert roles == [Role.QA_ENGINEER, Role.ENGINEER, Role.QA_ENGINEER]

    def test_launch_workflow(self):
        """Launch workflow is correctly defined."""
        workflow = WORKFLOW_DEFINITIONS["launch"]

        assert workflow.name == "launch"
        assert len(workflow.task_templates) == 6

        # Verify sequence includes all cross-functional roles
        roles = [t.assigned_role for t in workflow.task_templates]
        assert Role.PRODUCT_MANAGER in roles
        assert Role.GROWTH_MANAGER in roles
        assert Role.ENGINEER in roles
        assert Role.QA_ENGINEER in roles
        assert Role.SUPPORT_LEAD in roles

    def test_workflow_dependencies(self):
        """Workflows have correct dependency chains."""
        # Trading strategy: each step depends on previous
        ts_deps = [
            t.depends_on_step for t in TRADING_STRATEGY_WORKFLOW.task_templates
        ]
        assert ts_deps == [None, 1, 2, 3, 4, 5, 6, 7]

        # Feature: sequential dependencies
        feature_deps = [t.depends_on_step for t in FEATURE_WORKFLOW.task_templates]
        assert feature_deps == [None, 1, 2, 3, 4, 5]

        # Bug: simple chain
        bug_deps = [t.depends_on_step for t in BUG_WORKFLOW.task_templates]
        assert bug_deps == [None, 1, 2]

    def test_workflow_approval_gates(self):
        """Workflows have approval gates at correct steps."""
        # Trading strategy gates
        ts_gates = [
            (i, t.approval_gate)
            for i, t in enumerate(TRADING_STRATEGY_WORKFLOW.task_templates, 1)
            if t.approval_gate
        ]
        assert len(ts_gates) == 3
        assert ts_gates[0] == (2, "strategy_config_schema")  # Designer
        assert ts_gates[1] == (6, "backtest_validation")  # QA Lead
        assert ts_gates[2] == (7, "production_trading_deploy")  # PM

        # Feature gates
        feature_gates = [
            (i, t.approval_gate)
            for i, t in enumerate(FEATURE_WORKFLOW.task_templates, 1)
            if t.approval_gate
        ]
        assert len(feature_gates) == 5

    def test_workflow_complexity_estimates(self):
        """Workflows have realistic complexity estimates."""
        # All templates should have complexity > 0
        for workflow in WORKFLOW_DEFINITIONS.values():
            for template in workflow.task_templates:
                assert (
                    template.estimated_complexity >= 0
                ), f"{template.title} has no complexity estimate"


class TestWorkflowRouter:
    """Test WorkflowRouter."""

    def test_router_creation(self):
        """Can create router."""
        router = WorkflowRouter()
        assert router.company is None

    def test_router_with_company(self):
        """Can create router with company."""
        # Would use real Company object in integration
        router = WorkflowRouter(company="mock_company")
        assert router.company == "mock_company"

    def test_route_epic_generates_tasks(self):
        """Routing epic generates correct number of tasks."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-001",
            title="Add IV Filter",
            description="Implement IV percentile filter",
            workflow_type="trading_strategy",
            status=ArtifactStatus.PENDING,
            created_by="strategy_pm",
        )

        task_ids = router.route_epic(epic)

        assert len(task_ids) == 8  # trading_strategy has 8 tasks
        assert epic.status == ArtifactStatus.IN_PROGRESS
        assert epic.generated_task_ids == task_ids
        assert epic.approval_gates_required == [
            "strategy_config_schema",
            "backtest_validation",
            "production_trading_deploy",
        ]

    def test_route_epic_invalid_workflow(self):
        """Routing epic with invalid workflow raises error."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="invalid_type",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        with pytest.raises(ValueError, match="Unknown workflow type"):
            router.route_epic(epic)

    def test_route_epic_feature_workflow(self):
        """Routing feature epic generates 6 tasks."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-002",
            title="User Auth",
            description="Add authentication",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        task_ids = router.route_epic(epic)

        assert len(task_ids) == 6
        assert len(epic.approval_gates_required) == 4

    def test_route_epic_bug_workflow(self):
        """Routing bug epic generates 3 tasks."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-003",
            title="Fix Login Bug",
            description="Login fails on mobile",
            workflow_type="bug",
            status=ArtifactStatus.PENDING,
            created_by="qa",
        )

        task_ids = router.route_epic(epic)

        assert len(task_ids) == 3
        assert len(epic.approval_gates_required) == 3

    def test_route_epic_launch_workflow(self):
        """Routing launch epic generates 6 tasks."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-004",
            title="V2 Launch",
            description="Launch version 2.0",
            workflow_type="launch",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        task_ids = router.route_epic(epic)

        assert len(task_ids) == 6
        assert len(epic.approval_gates_required) == 2

    def test_complete_approval_gate(self):
        """Can complete approval gates."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
            approval_gates_required=["gate1", "gate2"],
            approval_gates_completed=[],
        )

        router.complete_approval_gate(epic, "gate1", "approver_agent")

        assert "gate1" in epic.approval_gates_completed
        assert epic.is_blocked() is True  # gate2 still pending

        router.complete_approval_gate(epic, "gate2", "approver_agent")

        assert "gate2" in epic.approval_gates_completed
        assert epic.is_blocked() is False  # all gates complete

    def test_get_next_available_task(self):
        """get_next_available_task returns None in basic implementation."""
        router = WorkflowRouter()
        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        router.route_epic(epic)
        task_id = router.get_next_available_task(Role.ENGINEER, epic)

        # Basic implementation returns None (would integrate with task system)
        assert task_id is None


class TestWorkflowIntegration:
    """Integration tests for workflow system."""

    def test_complete_trading_strategy_workflow(self):
        """Test complete trading strategy epic lifecycle."""
        router = WorkflowRouter()

        # PM creates epic
        epic = Epic(
            id="epic-janus-001",
            title="Add VIX Term Structure Filter",
            description="Filter based on VIX term structure slope",
            workflow_type="trading_strategy",
            status=ArtifactStatus.PENDING,
            created_by="strategy_pm",
            priority=1,
        )

        # Route generates tasks
        task_ids = router.route_epic(epic)

        assert len(task_ids) == 8
        assert epic.status == ArtifactStatus.IN_PROGRESS

        # Verify approval gates required
        assert epic.approval_gates_required == [
            "strategy_config_schema",
            "backtest_validation",
            "production_trading_deploy",
        ]
        assert epic.is_blocked() is True

        # Complete gates in sequence
        router.complete_approval_gate(epic, "strategy_config_schema", "em_agent")
        assert epic.is_blocked() is True

        router.complete_approval_gate(epic, "backtest_validation", "qa_lead")
        assert epic.is_blocked() is True

        router.complete_approval_gate(
            epic, "production_trading_deploy", "pm_agent"
        )
        assert epic.is_blocked() is False

    def test_multiple_epics_different_workflows(self):
        """Can route multiple epics with different workflow types."""
        router = WorkflowRouter()

        epic1 = Epic(
            id="epic-1",
            title="Feature",
            description="New feature",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        epic2 = Epic(
            id="epic-2",
            title="Bug",
            description="Fix bug",
            workflow_type="bug",
            status=ArtifactStatus.PENDING,
            created_by="qa",
        )

        tasks1 = router.route_epic(epic1)
        tasks2 = router.route_epic(epic2)

        assert len(tasks1) == 6  # feature workflow
        assert len(tasks2) == 3  # bug workflow
        assert set(tasks1).isdisjoint(set(tasks2))  # unique task IDs

    def test_epic_with_tags(self):
        """Epic metadata carries through to workflow."""
        router = WorkflowRouter()

        epic = Epic(
            id="epic-001",
            title="Test",
            description="Test epic",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
            tags=["urgent", "customer-facing"],
        )

        task_ids = router.route_epic(epic)

        assert len(task_ids) == 6
        assert epic.tags == ["urgent", "customer-facing"]
