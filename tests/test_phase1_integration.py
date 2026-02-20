"""Phase 1 integration test - validates all components working together."""

import pytest
from pathlib import Path
from agentcoord.company import Company, AgentStatus
from agentcoord.roles import Role, RoleCapabilities, ApprovalGate
from agentcoord.channels import ChannelManager, TerminalChannel, FileChannel, MessagePriority
from agentcoord.workflows import (
    Epic,
    ArtifactStatus,
    WorkflowRouter,
    WORKFLOW_DEFINITIONS,
)
from agentcoord.tasks import Task, TaskStatus


class TestPhase1Integration:
    """End-to-end integration test for Phase 1 company model."""

    def test_complete_janus_workflow(self, tmp_path):
        """Test complete Janus trading strategy workflow end-to-end.

        This validates:
        1. Company loading from template
        2. Multi-department organization
        3. Role-based agent assignment
        4. Workflow routing and task generation
        5. Agent claiming and completing tasks
        6. Approval gates
        7. Multi-channel communication
        """

        # ===== 1. SETUP: Load Janus company from template =====
        company = Company.from_template("janus_dev")

        assert company.name == "Janus Development Team"
        assert len(company.departments) == 3  # Product, Engineering, QA

        # Verify departments
        product_dept = company.get_department("product")
        eng_dept = company.get_department("engineering")
        qa_dept = company.get_department("qa")

        assert product_dept is not None
        assert eng_dept is not None
        assert qa_dept is not None

        # Verify teams exist
        strategy_team = product_dept.get_team("strategy")
        backend_team = eng_dept.get_team("backend")
        testing_team = qa_dept.get_team("testing")

        assert strategy_team is not None
        assert backend_team is not None
        assert testing_team is not None

        # Verify agents are available
        all_agents = company.get_all_agents()
        assert len(all_agents) == 9  # Total agents in janus_dev template

        # ===== 2. ROLE CAPABILITIES: Verify role permissions =====

        # PM can approve trading strategies
        assert RoleCapabilities.has_capability(
            Role.PRODUCT_MANAGER, "approve_trading_strategy_for_production"
        )

        # Designer can design schemas
        assert RoleCapabilities.has_capability(
            Role.PRODUCT_DESIGNER, "design_config_schema"
        )

        # Engineer can implement filters
        assert RoleCapabilities.has_capability(Role.ENGINEER, "implement_filters")

        # QA can run backtests
        assert RoleCapabilities.has_capability(Role.QA_ENGINEER, "run_backtest")

        # QA Lead can approve backtest results
        assert RoleCapabilities.has_capability(
            Role.QA_LEAD, "approve_backtest_results"
        )

        # SRE can deploy to Telegram
        assert RoleCapabilities.has_capability(Role.SRE, "deploy_to_telegram_bot")

        # ===== 3. APPROVAL GATES: Verify gate requirements =====

        # Production trading deploy requires PM + QA Lead + EM
        deploy_gate = ApprovalGate.get_required_approvers(
            ApprovalGate.PRODUCTION_TRADING_DEPLOY
        )
        assert Role.PRODUCT_MANAGER in deploy_gate
        assert Role.QA_LEAD in deploy_gate
        assert Role.ENGINEERING_MANAGER in deploy_gate
        assert len(deploy_gate) == 3

        # ===== 4. COMMUNICATION: Setup multi-channel system =====

        channels = ChannelManager()
        channels.add_channel(TerminalChannel(name="console"))
        channels.add_channel(FileChannel(name="logs", log_path=tmp_path / "agentcoord.jsonl"))

        # Broadcast announcement
        results = channels.post(
            channel="engineering",
            content="Phase 1 integration test started",
            from_agent="test_coordinator",
            priority=MessagePriority.HIGH,
        )

        assert len(results) == 2  # Both channels
        assert all(results.values())  # All successful

        # ===== 5. WORKFLOW: Create and route trading strategy epic =====

        # Helper to create Task objects for testing
        def make_task(task_id: str, title: str) -> Task:
            return Task(
                id=task_id,
                title=title,
                description=f"Task for {title}",
                status=TaskStatus.PENDING
            )

        # PM creates epic
        pm_agent = company.find_available_agent(role=Role.PRODUCT_MANAGER)
        assert pm_agent is not None
        assert pm_agent.role == Role.PRODUCT_MANAGER
        assert pm_agent.is_available()

        epic = Epic(
            id="epic-integration-001",
            title="Add IV Percentile Filter",
            description="Filter trades to only enter when IV percentile > 50th",
            workflow_type="trading_strategy",
            status=ArtifactStatus.PENDING,
            created_by=pm_agent.id,
            priority=1,
        )

        # Route epic
        router = WorkflowRouter(company)
        task_ids = router.route_epic(epic)

        assert len(task_ids) == 8  # trading_strategy has 8 tasks
        assert epic.status == ArtifactStatus.IN_PROGRESS
        assert len(epic.approval_gates_required) == 3

        # Verify workflow definition
        workflow = WORKFLOW_DEFINITIONS["trading_strategy"]
        assert workflow.name == "trading_strategy"
        assert len(workflow.task_templates) == 8

        # ===== 6. TASK EXECUTION: Simulate task claiming and completion =====

        # Step 1: PM defines strategy goals (first task)
        task1 = make_task(task_ids[0], "Define strategy goals")
        task1_result = pm_agent.claim_task(task1)
        assert task1_result is True
        assert pm_agent.status == AgentStatus.WORKING

        channels.post(
            channel="product",
            content=f"{pm_agent.name} claimed: Define strategy goals",
            from_agent=pm_agent.id,
            priority=MessagePriority.NORMAL,
        )

        pm_agent.complete_task(result='{"prd": "IV_percentile_strategy_goals.md"}')
        assert pm_agent.is_available()

        # Step 2: Designer creates config schema (second task)
        designer = company.find_available_agent(role=Role.PRODUCT_DESIGNER)
        assert designer is not None

        task2 = make_task(task_ids[1], "Design config schema")
        designer.claim_task(task2)
        designer.complete_task(result='{"schema": "iv_percentile_config.yaml"}')

        # Approval gate: strategy_config_schema
        router.complete_approval_gate(
            epic, "strategy_config_schema", designer.id
        )
        assert "strategy_config_schema" in epic.approval_gates_completed

        # Step 3-4: Engineer implements and tests
        engineer = company.find_available_agent(role=Role.ENGINEER)
        assert engineer is not None

        task3 = make_task(task_ids[2], "Implement filter logic")
        engineer.claim_task(task3)
        engineer.complete_task(result='{"code": "iv_percentile.py"}')

        task4 = make_task(task_ids[3], "Write unit and integration tests")
        engineer.claim_task(task4)
        engineer.complete_task(result='{"tests": "test_iv_percentile.py"}')

        # Step 5-6: QA runs backtest and validates
        qa_eng = company.find_available_agent(role=Role.QA_ENGINEER)
        qa_lead = company.find_available_agent(role=Role.QA_LEAD)

        assert qa_eng is not None
        assert qa_lead is not None

        task5 = make_task(task_ids[4], "Run backtest")
        qa_eng.claim_task(task5)
        qa_eng.complete_task(
            result='{"backtest": "sharpe_1.42_drawdown_-0.15_premium_0.85"}'
        )

        task6 = make_task(task_ids[5], "Validate backtest metrics")
        qa_lead.claim_task(task6)
        qa_lead.complete_task(result='{"validation": "metrics_meet_targets"}')

        # Approval gate: backtest_validation
        router.complete_approval_gate(epic, "backtest_validation", qa_lead.id)
        assert "backtest_validation" in epic.approval_gates_completed

        # Step 7: PM approves for production
        task7 = make_task(task_ids[6], "Review and approve for production")
        pm_agent.claim_task(task7)
        pm_agent.complete_task(result='{"approval": "approved"}')

        # Approval gate: production_trading_deploy (requires PM + QA Lead + EM)
        # In real system, would require all 3 approvers
        router.complete_approval_gate(
            epic, "production_trading_deploy", pm_agent.id
        )

        # Step 8: SRE deploys
        sre = company.find_available_agent(role=Role.SRE)
        assert sre is not None

        task8 = make_task(task_ids[7], "Deploy to Telegram bot")
        sre.claim_task(task8)
        sre.complete_task(result='{"deployment": "telegram_bot_updated"}')

        channels.post(
            channel="engineering",
            content="IV Percentile Filter deployed to production",
            from_agent=sre.id,
            priority=MessagePriority.URGENT,
        )

        # ===== 7. VERIFICATION: All gates complete =====

        assert not epic.is_blocked()  # All approval gates complete
        assert len(epic.approval_gates_completed) == 3

        # ===== 8. MULTI-DEPARTMENT COORDINATION: Verify agent usage =====

        # Verify agents from all departments participated
        departments_used = set()
        for agent in [pm_agent, designer, engineer, qa_eng, qa_lead, sre]:
            if agent.team and agent.team.department:
                departments_used.add(agent.team.department.name)

        assert "product" in departments_used
        assert "engineering" in departments_used
        assert "qa" in departments_used

        # ===== 9. COMMUNICATION: Verify channel logs =====

        # Check file channel wrote logs
        log_file = tmp_path / "agentcoord.jsonl"
        assert log_file.exists()

        log_content = log_file.read_text()
        assert "Phase 1 integration test started" in log_content
        assert "IV Percentile Filter deployed to production" in log_content

    def test_cross_functional_feature_workflow(self):
        """Test feature workflow across Product, Engineering, QA, Marketing."""

        company = Company.from_template("janus_dev")

        # Create feature epic
        epic = Epic(
            id="epic-feature-001",
            title="User Dashboard",
            description="Add user dashboard for strategy monitoring",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        router = WorkflowRouter(company)
        task_ids = router.route_epic(epic)

        # Feature workflow has 6 tasks
        assert len(task_ids) == 6

        # Verify workflow sequence
        workflow = WORKFLOW_DEFINITIONS["feature"]
        roles = [t.assigned_role for t in workflow.task_templates]

        assert roles == [
            Role.PRODUCT_MANAGER,
            Role.PRODUCT_DESIGNER,
            Role.ENGINEER,
            Role.QA_ENGINEER,
            Role.PRODUCT_MANAGER,
            Role.GROWTH_MANAGER,
        ]

        # Verify approval gates
        assert len(epic.approval_gates_required) == 4

    def test_bug_workflow_rapid_cycle(self):
        """Test bug workflow for rapid fix and verification."""

        company = Company.from_template("janus_dev")

        # Create bug epic
        epic = Epic(
            id="epic-bug-001",
            title="Fix pricing calculation",
            description="Contract multiplier missing in P&L",
            workflow_type="bug",
            status=ArtifactStatus.PENDING,
            created_by="qa_eng",
            priority=2,  # Bugs have higher priority
        )

        router = WorkflowRouter(company)
        task_ids = router.route_epic(epic)

        # Bug workflow has 3 tasks
        assert len(task_ids) == 3

        # Verify workflow sequence (QA → Eng → QA)
        workflow = WORKFLOW_DEFINITIONS["bug"]
        roles = [t.assigned_role for t in workflow.task_templates]

        assert roles == [Role.QA_ENGINEER, Role.ENGINEER, Role.QA_ENGINEER]

        # Verify bug workflow has high priority
        assert workflow.default_priority == 2

    def test_multiple_concurrent_epics(self):
        """Test multiple epics running concurrently across departments."""

        company = Company.from_template("janus_dev")
        router = WorkflowRouter(company)

        # Create 3 different epics
        epic1 = Epic(
            id="epic-001",
            title="Trading Strategy",
            description="VIX filter",
            workflow_type="trading_strategy",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        epic2 = Epic(
            id="epic-002",
            title="Feature",
            description="Dashboard",
            workflow_type="feature",
            status=ArtifactStatus.PENDING,
            created_by="pm",
        )

        epic3 = Epic(
            id="epic-003",
            title="Bug",
            description="Fix calculation",
            workflow_type="bug",
            status=ArtifactStatus.PENDING,
            created_by="qa",
        )

        # Route all epics
        tasks1 = router.route_epic(epic1)
        tasks2 = router.route_epic(epic2)
        tasks3 = router.route_epic(epic3)

        # Verify task counts
        assert len(tasks1) == 8  # trading_strategy
        assert len(tasks2) == 6  # feature
        assert len(tasks3) == 3  # bug

        # Verify unique task IDs
        all_tasks = set(tasks1 + tasks2 + tasks3)
        assert len(all_tasks) == 17  # No duplicates

        # Verify all epics are in progress
        assert epic1.status == ArtifactStatus.IN_PROGRESS
        assert epic2.status == ArtifactStatus.IN_PROGRESS
        assert epic3.status == ArtifactStatus.IN_PROGRESS

    def test_agent_availability_tracking(self):
        """Test agent availability changes during task execution."""

        company = Company.from_template("janus_dev")

        # Find available engineer
        engineer = company.find_available_agent(role=Role.ENGINEER)
        assert engineer is not None
        assert engineer.is_available()
        assert engineer.status == AgentStatus.AVAILABLE

        # Claim task
        test_task = Task(
            id="task-001",
            title="Test task",
            description="Testing availability tracking",
            status=TaskStatus.PENDING
        )
        engineer.claim_task(test_task)
        assert not engineer.is_available()
        assert engineer.status == AgentStatus.WORKING
        assert engineer.current_task.id == "task-001"

        # Engineer now unavailable for new tasks
        available_engineers = company.get_agents_by_role(Role.ENGINEER)
        available = [e for e in available_engineers if e.is_available()]
        assert engineer not in available

        # Complete task
        engineer.complete_task(result='{"status": "done"}')
        assert engineer.is_available()
        assert engineer.status == AgentStatus.AVAILABLE
        assert engineer.current_task is None

    def test_hierarchical_status_reporting(self):
        """Test status reporting at all levels of hierarchy."""

        company = Company.from_template("janus_dev")

        # Company-wide status
        company_status = company.get_status()
        assert "departments" in company_status
        assert len(company_status["departments"]) == 3

        # Department status
        eng_dept = company.get_department("engineering")
        dept_status = eng_dept.get_status()
        assert "teams" in dept_status
        assert dept_status["name"] == "engineering"

        # Team status
        backend_team = eng_dept.get_team("backend")
        team_status = backend_team.get_status()
        assert "agents" in team_status
        assert team_status["name"] == "backend"

        # Agent status
        engineer = company.find_available_agent(role=Role.ENGINEER)
        agent_status = engineer.get_status()
        assert "status" in agent_status
        assert agent_status["status"] == "available"
