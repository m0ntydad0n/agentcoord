"""Tests for company organizational hierarchy."""

import pytest
import tempfile
import yaml
from pathlib import Path
from agentcoord.company import (
    Agent,
    AgentStatus,
    Team,
    Department,
    Company,
    CompanyTemplate,
)
from agentcoord.roles import Role
from agentcoord.tasks import Task, TaskStatus


class TestAgentStatus:
    """Test AgentStatus enum."""

    def test_all_statuses_defined(self):
        """All expected agent statuses are defined."""
        expected_statuses = {"available", "working", "blocked", "offline"}
        actual_statuses = {status.value for status in AgentStatus}
        assert actual_statuses == expected_statuses


class TestAgent:
    """Test Agent class functionality."""

    def test_agent_creation(self):
        """Agent can be created with basic attributes."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
        )

        assert agent.id == "agent-001"
        assert agent.name == "Alice"
        assert agent.role == Role.ENGINEER
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.current_task is None
        assert agent.team is None

    def test_agent_is_available_when_created(self):
        """New agent is available by default."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
        )

        assert agent.is_available()

    def test_agent_is_available_checks_status_and_task(self):
        """is_available requires AVAILABLE status and no task."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
            status=AgentStatus.AVAILABLE,
        )

        # Available with correct status and no task
        assert agent.is_available()

        # Not available when working
        agent.status = AgentStatus.WORKING
        assert not agent.is_available()

        # Not available even if status is correct but has a task
        agent.status = AgentStatus.AVAILABLE
        agent.current_task = Task(
            id="task-001",
            title="Test Task",
            description="Test",
            status=TaskStatus.CLAIMED,
        )
        assert not agent.is_available()

    def test_agent_claim_task_success(self):
        """Agent can claim a task when available."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
        )
        task = Task(
            id="task-001",
            title="Implement feature",
            description="Add new feature X",
            status=TaskStatus.PENDING,
        )

        result = agent.claim_task(task)

        assert result is True
        assert agent.status == AgentStatus.WORKING
        assert agent.current_task == task
        assert task.agent_id == "agent-001"

    def test_agent_claim_task_fails_when_unavailable(self):
        """Agent cannot claim task when already working."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
            status=AgentStatus.WORKING,
        )
        task = Task(
            id="task-001",
            title="Implement feature",
            description="Add new feature X",
            status=TaskStatus.PENDING,
        )

        result = agent.claim_task(task)

        assert result is False
        assert agent.current_task is None
        assert task.agent_id is None

    def test_agent_complete_task(self):
        """Agent can complete task and return to available."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
        )
        task = Task(
            id="task-001",
            title="Implement feature",
            description="Add new feature X",
            status=TaskStatus.PENDING,
        )

        # Claim task
        agent.claim_task(task)
        assert agent.status == AgentStatus.WORKING

        # Complete task
        completed_task = agent.complete_task(result="Feature implemented successfully")

        assert completed_task == task
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "Feature implemented successfully"
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.current_task is None

    def test_agent_complete_task_without_current_task(self):
        """Completing task without current task returns None."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
        )

        completed_task = agent.complete_task(result="Nothing to complete")

        assert completed_task is None
        assert agent.status == AgentStatus.AVAILABLE

    def test_agent_get_status(self):
        """Agent can return status summary."""
        team = Team(name="Backend", lead=None, members=[])
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
            team=team,
        )

        status = agent.get_status()

        assert status["id"] == "agent-001"
        assert status["name"] == "Alice"
        assert status["role"] == "engineer"
        assert status["status"] == "available"
        assert status["current_task"] is None
        assert status["team"] == "Backend"

    def test_agent_get_status_with_task(self):
        """Agent status includes current task when working."""
        agent = Agent(
            id="agent-001",
            name="Alice",
            role=Role.ENGINEER,
        )
        task = Task(
            id="task-001",
            title="Implement feature",
            description="Add new feature X",
            status=TaskStatus.PENDING,
        )
        agent.claim_task(task)

        status = agent.get_status()

        assert status["status"] == "working"
        assert status["current_task"] == "task-001"


class TestTeam:
    """Test Team class functionality."""

    def test_team_creation(self):
        """Team can be created with lead and members."""
        lead = Agent(id="lead-001", name="Bob", role=Role.SENIOR_ENGINEER)
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(id="eng-002", name="Charlie", role=Role.ENGINEER)

        team = Team(
            name="Backend",
            lead=lead,
            members=[member1, member2],
        )

        assert team.name == "Backend"
        assert team.lead == lead
        assert len(team.members) == 2
        assert member1 in team.members
        assert member2 in team.members

    def test_team_get_all_agents(self):
        """get_all_agents returns lead and all members."""
        lead = Agent(id="lead-001", name="Bob", role=Role.SENIOR_ENGINEER)
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(id="eng-002", name="Charlie", role=Role.ENGINEER)

        team = Team(
            name="Backend",
            lead=lead,
            members=[member1, member2],
        )

        all_agents = team.get_all_agents()

        assert len(all_agents) == 3
        assert lead in all_agents
        assert member1 in all_agents
        assert member2 in all_agents

    def test_team_get_all_agents_without_lead(self):
        """get_all_agents works when team has no lead."""
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(id="eng-002", name="Charlie", role=Role.ENGINEER)

        team = Team(
            name="Backend",
            lead=None,
            members=[member1, member2],
        )

        all_agents = team.get_all_agents()

        assert len(all_agents) == 2
        assert member1 in all_agents
        assert member2 in all_agents

    def test_team_find_available_agent_by_role(self):
        """find_available_agent finds first available agent with role."""
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(id="eng-002", name="Charlie", role=Role.ENGINEER)
        member3 = Agent(id="qa-001", name="Dana", role=Role.QA_ENGINEER)

        team = Team(
            name="Backend",
            lead=None,
            members=[member1, member2, member3],
        )

        # Find engineer
        found_agent = team.find_available_agent(Role.ENGINEER)
        assert found_agent == member1

        # Find QA engineer
        found_agent = team.find_available_agent(Role.QA_ENGINEER)
        assert found_agent == member3

    def test_team_find_available_agent_checks_lead_first(self):
        """find_available_agent checks lead before members."""
        lead = Agent(id="lead-001", name="Bob", role=Role.SENIOR_ENGINEER)
        member = Agent(id="eng-001", name="Alice", role=Role.SENIOR_ENGINEER)

        team = Team(
            name="Backend",
            lead=lead,
            members=[member],
        )

        found_agent = team.find_available_agent(Role.SENIOR_ENGINEER)
        assert found_agent == lead

    def test_team_find_available_agent_skips_unavailable(self):
        """find_available_agent skips agents that are working."""
        member1 = Agent(
            id="eng-001",
            name="Alice",
            role=Role.ENGINEER,
            status=AgentStatus.WORKING,
        )
        member2 = Agent(id="eng-002", name="Charlie", role=Role.ENGINEER)

        team = Team(
            name="Backend",
            lead=None,
            members=[member1, member2],
        )

        found_agent = team.find_available_agent(Role.ENGINEER)
        assert found_agent == member2

    def test_team_find_available_agent_returns_none_when_not_found(self):
        """find_available_agent returns None when no match found."""
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)

        team = Team(
            name="Backend",
            lead=None,
            members=[member1],
        )

        found_agent = team.find_available_agent(Role.QA_ENGINEER)
        assert found_agent is None

    def test_team_get_available_agents_no_filter(self):
        """get_available_agents returns all available agents."""
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(
            id="eng-002",
            name="Charlie",
            role=Role.ENGINEER,
            status=AgentStatus.WORKING,
        )
        member3 = Agent(id="qa-001", name="Dana", role=Role.QA_ENGINEER)

        team = Team(
            name="Backend",
            lead=None,
            members=[member1, member2, member3],
        )

        available = team.get_available_agents()

        assert len(available) == 2
        assert member1 in available
        assert member3 in available
        assert member2 not in available

    def test_team_get_available_agents_with_role_filter(self):
        """get_available_agents can filter by role."""
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(id="eng-002", name="Charlie", role=Role.ENGINEER)
        member3 = Agent(id="qa-001", name="Dana", role=Role.QA_ENGINEER)

        team = Team(
            name="Backend",
            lead=None,
            members=[member1, member2, member3],
        )

        available_engineers = team.get_available_agents(role=Role.ENGINEER)

        assert len(available_engineers) == 2
        assert member1 in available_engineers
        assert member2 in available_engineers
        assert member3 not in available_engineers

    def test_team_get_status(self):
        """Team can return status summary."""
        lead = Agent(id="lead-001", name="Bob", role=Role.SENIOR_ENGINEER)
        member1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        member2 = Agent(
            id="eng-002",
            name="Charlie",
            role=Role.ENGINEER,
            status=AgentStatus.WORKING,
        )

        team = Team(
            name="Backend",
            lead=lead,
            members=[member1, member2],
        )

        status = team.get_status()

        assert status["name"] == "Backend"
        assert status["lead"] == "Bob"
        assert status["member_count"] == 2
        assert status["available_count"] == 2  # Lead + 1 available member
        assert len(status["agents"]) == 3


class TestDepartment:
    """Test Department class functionality."""

    def test_department_creation(self):
        """Department can be created with teams."""
        team1 = Team(name="Backend", lead=None, members=[])
        team2 = Team(name="Frontend", lead=None, members=[])

        dept = Department(
            name="Engineering",
            teams={"backend": team1, "frontend": team2},
        )

        assert dept.name == "Engineering"
        assert len(dept.teams) == 2
        assert dept.teams["backend"] == team1
        assert dept.teams["frontend"] == team2

    def test_department_get_team(self):
        """Department can retrieve team by name."""
        team1 = Team(name="Backend", lead=None, members=[])
        team2 = Team(name="Frontend", lead=None, members=[])

        dept = Department(
            name="Engineering",
            teams={"backend": team1, "frontend": team2},
        )

        assert dept.get_team("backend") == team1
        assert dept.get_team("frontend") == team2
        assert dept.get_team("nonexistent") is None

    def test_department_find_available_agent_across_teams(self):
        """Department finds agents across all teams."""
        backend_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        frontend_agent = Agent(id="eng-002", name="Bob", role=Role.ENGINEER)

        backend_team = Team(name="Backend", lead=None, members=[backend_agent])
        frontend_team = Team(name="Frontend", lead=None, members=[frontend_agent])

        dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "frontend": frontend_team},
        )

        found_agent = dept.find_available_agent(Role.ENGINEER)
        assert found_agent in [backend_agent, frontend_agent]

    def test_department_find_available_agent_with_team_filter(self):
        """Department can filter agent search by team."""
        backend_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        frontend_agent = Agent(id="eng-002", name="Bob", role=Role.ENGINEER)

        backend_team = Team(name="Backend", lead=None, members=[backend_agent])
        frontend_team = Team(name="Frontend", lead=None, members=[frontend_agent])

        dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "frontend": frontend_team},
        )

        found_agent = dept.find_available_agent(Role.ENGINEER, team="frontend")
        assert found_agent == frontend_agent

    def test_department_get_all_agents(self):
        """Department returns all agents from all teams."""
        backend_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        frontend_agent = Agent(id="eng-002", name="Bob", role=Role.ENGINEER)
        dept_head = Agent(id="head-001", name="Charlie", role=Role.VP_ENGINEERING)

        backend_team = Team(name="Backend", lead=None, members=[backend_agent])
        frontend_team = Team(name="Frontend", lead=None, members=[frontend_agent])

        dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "frontend": frontend_team},
            head=dept_head,
        )

        all_agents = dept.get_all_agents()

        assert len(all_agents) == 3
        assert backend_agent in all_agents
        assert frontend_agent in all_agents
        assert dept_head in all_agents

    def test_department_get_available_agents(self):
        """Department returns available agents from all teams."""
        available_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        working_agent = Agent(
            id="eng-002",
            name="Bob",
            role=Role.ENGINEER,
            status=AgentStatus.WORKING,
        )

        backend_team = Team(name="Backend", lead=None, members=[available_agent])
        frontend_team = Team(name="Frontend", lead=None, members=[working_agent])

        dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "frontend": frontend_team},
        )

        available = dept.get_available_agents()

        assert len(available) == 1
        assert available_agent in available
        assert working_agent not in available

    def test_department_get_available_agents_with_role_filter(self):
        """Department can filter available agents by role."""
        engineer = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        qa = Agent(id="qa-001", name="Bob", role=Role.QA_ENGINEER)

        backend_team = Team(name="Backend", lead=None, members=[engineer])
        qa_team = Team(name="QA", lead=None, members=[qa])

        dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "qa": qa_team},
        )

        available_engineers = dept.get_available_agents(role=Role.ENGINEER)

        assert len(available_engineers) == 1
        assert engineer in available_engineers
        assert qa not in available_engineers

    def test_department_get_status(self):
        """Department can return status summary."""
        engineer = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        backend_team = Team(name="Backend", lead=None, members=[engineer])

        dept = Department(
            name="Engineering",
            teams={"backend": backend_team},
        )

        status = dept.get_status()

        assert status["name"] == "Engineering"
        assert status["head"] is None
        assert "backend" in status["teams"]
        assert status["total_agents"] == 1
        assert status["available_agents"] == 1


class TestCompany:
    """Test Company class functionality."""

    def test_company_creation(self):
        """Company can be created with departments."""
        dept1 = Department(name="Engineering", teams={})
        dept2 = Department(name="Product", teams={})

        company = Company(
            name="Acme Corp",
            departments={"engineering": dept1, "product": dept2},
        )

        assert company.name == "Acme Corp"
        assert len(company.departments) == 2
        assert company.departments["engineering"] == dept1
        assert company.departments["product"] == dept2

    def test_company_get_department(self):
        """Company can retrieve department by name."""
        dept1 = Department(name="Engineering", teams={})
        dept2 = Department(name="Product", teams={})

        company = Company(
            name="Acme Corp",
            departments={"engineering": dept1, "product": dept2},
        )

        assert company.get_department("engineering") == dept1
        assert company.get_department("product") == dept2
        assert company.get_department("nonexistent") is None

    def test_company_find_available_agent_across_departments(self):
        """Company finds agents across all departments."""
        eng_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        pm_agent = Agent(id="pm-001", name="Bob", role=Role.PRODUCT_MANAGER)

        eng_team = Team(name="Backend", lead=None, members=[eng_agent])
        pm_team = Team(name="Product", lead=None, members=[pm_agent])

        eng_dept = Department(name="Engineering", teams={"backend": eng_team})
        product_dept = Department(name="Product", teams={"product": pm_team})

        company = Company(
            name="Acme Corp",
            departments={"engineering": eng_dept, "product": product_dept},
        )

        # Find engineer
        found_agent = company.find_available_agent(Role.ENGINEER)
        assert found_agent == eng_agent

        # Find PM
        found_agent = company.find_available_agent(Role.PRODUCT_MANAGER)
        assert found_agent == pm_agent

    def test_company_find_available_agent_with_department_filter(self):
        """Company can filter agent search by department."""
        eng_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        eng_team = Team(name="Backend", lead=None, members=[eng_agent])
        eng_dept = Department(name="Engineering", teams={"backend": eng_team})

        pm_agent = Agent(id="pm-001", name="Bob", role=Role.PRODUCT_MANAGER)
        pm_team = Team(name="Product", lead=None, members=[pm_agent])
        product_dept = Department(name="Product", teams={"product": pm_team})

        company = Company(
            name="Acme Corp",
            departments={"engineering": eng_dept, "product": product_dept},
        )

        found_agent = company.find_available_agent(
            Role.ENGINEER, department="engineering"
        )
        assert found_agent == eng_agent

    def test_company_find_available_agent_with_team_filter(self):
        """Company can filter agent search by department and team."""
        backend_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        frontend_agent = Agent(id="eng-002", name="Bob", role=Role.ENGINEER)

        backend_team = Team(name="Backend", lead=None, members=[backend_agent])
        frontend_team = Team(name="Frontend", lead=None, members=[frontend_agent])

        eng_dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "frontend": frontend_team},
        )

        company = Company(
            name="Acme Corp",
            departments={"engineering": eng_dept},
        )

        found_agent = company.find_available_agent(
            Role.ENGINEER, department="engineering", team="frontend"
        )
        assert found_agent == frontend_agent

    def test_company_get_all_agents(self):
        """Company returns all agents across all departments."""
        eng_agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        pm_agent = Agent(id="pm-001", name="Bob", role=Role.PRODUCT_MANAGER)

        eng_team = Team(name="Backend", lead=None, members=[eng_agent])
        pm_team = Team(name="Product", lead=None, members=[pm_agent])

        eng_dept = Department(name="Engineering", teams={"backend": eng_team})
        product_dept = Department(name="Product", teams={"product": pm_team})

        company = Company(
            name="Acme Corp",
            departments={"engineering": eng_dept, "product": product_dept},
        )

        all_agents = company.get_all_agents()

        assert len(all_agents) == 2
        assert eng_agent in all_agents
        assert pm_agent in all_agents

    def test_company_get_agents_by_role(self):
        """Company can filter agents by role."""
        eng1 = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        eng2 = Agent(id="eng-002", name="Bob", role=Role.ENGINEER)
        pm = Agent(id="pm-001", name="Charlie", role=Role.PRODUCT_MANAGER)

        backend_team = Team(name="Backend", lead=None, members=[eng1])
        frontend_team = Team(name="Frontend", lead=None, members=[eng2])
        pm_team = Team(name="Product", lead=None, members=[pm])

        eng_dept = Department(
            name="Engineering",
            teams={"backend": backend_team, "frontend": frontend_team},
        )
        product_dept = Department(name="Product", teams={"product": pm_team})

        company = Company(
            name="Acme Corp",
            departments={"engineering": eng_dept, "product": product_dept},
        )

        engineers = company.get_agents_by_role(Role.ENGINEER)
        pms = company.get_agents_by_role(Role.PRODUCT_MANAGER)

        assert len(engineers) == 2
        assert eng1 in engineers
        assert eng2 in engineers
        assert len(pms) == 1
        assert pm in pms

    def test_company_get_status(self):
        """Company can return comprehensive status summary."""
        eng = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        pm = Agent(id="pm-001", name="Bob", role=Role.PRODUCT_MANAGER)

        eng_team = Team(name="Backend", lead=None, members=[eng])
        pm_team = Team(name="Product", lead=None, members=[pm])

        eng_dept = Department(name="Engineering", teams={"backend": eng_team})
        product_dept = Department(name="Product", teams={"product": pm_team})

        company = Company(
            name="Acme Corp",
            departments={"engineering": eng_dept, "product": product_dept},
        )

        status = company.get_status()

        assert status["name"] == "Acme Corp"
        assert "engineering" in status["departments"]
        assert "product" in status["departments"]
        assert status["total_agents"] == 2
        assert "agents_by_role" in status
        assert status["agents_by_role"]["engineer"] == 1
        assert status["agents_by_role"]["pm"] == 1


class TestCompanyTemplate:
    """Test CompanyTemplate loading and building."""

    def test_template_load_missing_file(self):
        """Loading non-existent template raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Template not found"):
            CompanyTemplate.load("nonexistent_template")

    def test_template_build_minimal(self):
        """Template can build minimal company structure."""
        template_data = {
            "name": "Test Corp",
            "departments": [],
        }

        template = CompanyTemplate(template_data)
        company = template.build()

        assert company.name == "Test Corp"
        assert len(company.departments) == 0

    def test_template_build_with_agents(self):
        """Template builds company with departments, teams, and agents."""
        template_data = {
            "name": "Test Corp",
            "departments": [
                {
                    "name": "Engineering",
                    "teams": [
                        {
                            "name": "Backend",
                            "lead": {"role": "senior_eng"},
                            "members": [
                                {"role": "engineer", "name": "Alice"},
                                {"role": "engineer", "name": "Bob"},
                            ],
                        }
                    ],
                }
            ],
        }

        template = CompanyTemplate(template_data)
        company = template.build()

        assert company.name == "Test Corp"
        assert "Engineering" in company.departments

        eng_dept = company.departments["Engineering"]
        assert "Backend" in eng_dept.teams

        backend_team = eng_dept.teams["Backend"]
        assert backend_team.lead is not None
        assert backend_team.lead.role == Role.SENIOR_ENGINEER
        assert len(backend_team.members) == 2
        assert backend_team.members[0].name == "Alice"
        assert backend_team.members[1].name == "Bob"

    def test_template_build_with_department_head(self):
        """Template can create department head."""
        template_data = {
            "name": "Test Corp",
            "departments": [
                {
                    "name": "Engineering",
                    "head": {"role": "vp_eng"},
                    "teams": [],
                }
            ],
        }

        template = CompanyTemplate(template_data)
        company = template.build()

        eng_dept = company.departments["Engineering"]
        assert eng_dept.head is not None
        assert eng_dept.head.role == Role.VP_ENGINEERING
        assert eng_dept.head.name == "Engineering-head"

    def test_template_sets_hierarchical_relationships(self):
        """Template properly sets parent references."""
        template_data = {
            "name": "Test Corp",
            "departments": [
                {
                    "name": "Engineering",
                    "teams": [
                        {
                            "name": "Backend",
                            "members": [{"role": "engineer", "name": "Alice"}],
                        }
                    ],
                }
            ],
        }

        template = CompanyTemplate(template_data)
        company = template.build()

        eng_dept = company.departments["Engineering"]
        backend_team = eng_dept.teams["Backend"]
        agent = backend_team.members[0]

        # Check parent references
        assert eng_dept.company == company
        assert backend_team.department == eng_dept
        assert agent.team == backend_team

    def test_template_from_yaml_file(self):
        """Template can be loaded from YAML file."""
        # Create temporary YAML file
        template_data = {
            "name": "YAML Corp",
            "departments": [
                {
                    "name": "Engineering",
                    "teams": [
                        {
                            "name": "Backend",
                            "members": [{"role": "engineer"}],
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily override template directory
            original_dir = CompanyTemplate.TEMPLATE_DIR
            CompanyTemplate.TEMPLATE_DIR = Path(tmpdir)

            # Write template file
            template_path = Path(tmpdir) / "test_template.yaml"
            with open(template_path, "w") as f:
                yaml.dump(template_data, f)

            try:
                # Load and build
                template = CompanyTemplate.load("test_template")
                company = template.build()

                assert company.name == "YAML Corp"
                assert "Engineering" in company.departments
            finally:
                # Restore original directory
                CompanyTemplate.TEMPLATE_DIR = original_dir

    def test_company_from_template_classmethod(self):
        """Company.from_template is a convenience method."""
        template_data = {
            "name": "Template Corp",
            "template_name": "test_template",
            "departments": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = CompanyTemplate.TEMPLATE_DIR
            CompanyTemplate.TEMPLATE_DIR = Path(tmpdir)

            template_path = Path(tmpdir) / "test_template.yaml"
            with open(template_path, "w") as f:
                yaml.dump(template_data, f)

            try:
                company = Company.from_template("test_template")

                assert company.name == "Template Corp"
                assert company.template_name == "test_template"
            finally:
                CompanyTemplate.TEMPLATE_DIR = original_dir


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_agent_workflow_full_cycle(self):
        """Test complete workflow: find agent, claim task, complete task."""
        # Setup company
        agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        team = Team(name="Backend", lead=None, members=[agent])
        dept = Department(name="Engineering", teams={"backend": team})
        company = Company(name="Acme Corp", departments={"engineering": dept})

        # Find available agent
        found_agent = company.find_available_agent(Role.ENGINEER)
        assert found_agent is not None
        assert found_agent.is_available()

        # Claim task
        task = Task(
            id="task-001",
            title="Implement API",
            description="Create REST API",
            status=TaskStatus.PENDING,
        )
        success = found_agent.claim_task(task)
        assert success is True

        # Verify agent is now unavailable
        still_available = company.find_available_agent(Role.ENGINEER)
        assert still_available is None

        # Complete task
        completed = found_agent.complete_task(result="API implemented")
        assert completed.status == TaskStatus.COMPLETED

        # Agent is available again
        available_again = company.find_available_agent(Role.ENGINEER)
        assert available_again == found_agent

    def test_multi_department_agent_coordination(self):
        """Test finding agents across multiple departments."""
        # Engineering department
        eng = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        eng_team = Team(name="Backend", lead=None, members=[eng])
        eng_dept = Department(name="Engineering", teams={"backend": eng_team})

        # QA department
        qa = Agent(id="qa-001", name="Bob", role=Role.QA_ENGINEER)
        qa_team = Team(name="QA", lead=None, members=[qa])
        qa_dept = Department(name="QA", teams={"qa": qa_team})

        # Product department
        pm = Agent(id="pm-001", name="Charlie", role=Role.PRODUCT_MANAGER)
        pm_team = Team(name="Product", lead=None, members=[pm])
        product_dept = Department(name="Product", teams={"product": pm_team})

        company = Company(
            name="Acme Corp",
            departments={
                "engineering": eng_dept,
                "qa": qa_dept,
                "product": product_dept,
            },
        )

        # Find each type of agent
        found_eng = company.find_available_agent(Role.ENGINEER)
        found_qa = company.find_available_agent(Role.QA_ENGINEER)
        found_pm = company.find_available_agent(Role.PRODUCT_MANAGER)

        assert found_eng == eng
        assert found_qa == qa
        assert found_pm == pm

        # Verify total count
        assert len(company.get_all_agents()) == 3

    def test_hierarchical_status_reporting(self):
        """Test status reporting at all hierarchy levels."""
        agent = Agent(id="eng-001", name="Alice", role=Role.ENGINEER)
        team = Team(name="Backend", lead=None, members=[agent])
        agent.team = team  # Set parent reference
        dept = Department(name="Engineering", teams={"backend": team})
        company = Company(name="Acme Corp", departments={"engineering": dept})
        dept.company = company  # Set parent reference

        # Agent status
        agent_status = agent.get_status()
        assert agent_status["name"] == "Alice"
        assert agent_status["team"] == "Backend"

        # Team status
        team_status = team.get_status()
        assert team_status["name"] == "Backend"
        assert team_status["available_count"] == 1
        assert len(team_status["agents"]) == 1

        # Department status
        dept_status = dept.get_status()
        assert dept_status["name"] == "Engineering"
        assert dept_status["total_agents"] == 1
        assert "backend" in dept_status["teams"]

        # Company status
        company_status = company.get_status()
        assert company_status["name"] == "Acme Corp"
        assert company_status["total_agents"] == 1
        assert "engineering" in company_status["departments"]
