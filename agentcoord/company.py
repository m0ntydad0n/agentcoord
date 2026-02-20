"""Company organizational hierarchy for AgentCoord.

This module provides a structured organizational model for coordinating multiple LLM agents
across departments, teams, and roles.
"""

import uuid
import yaml
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from agentcoord.roles import Role
from agentcoord.tasks import Task, TaskStatus

try:
    import redis
except ImportError:
    redis = None


class AgentStatus(Enum):
    """Agent availability status."""
    AVAILABLE = "available"
    WORKING = "working"
    BLOCKED = "blocked"
    OFFLINE = "offline"


@dataclass
class Agent:
    """
    Represents an individual agent in the organization.

    Attributes:
        id: Unique agent identifier
        name: Agent display name
        role: Agent's role (from Role enum)
        status: Current availability status
        current_task: Currently assigned task (if any)
        team: Parent team reference
    """
    id: str
    name: str
    role: Role
    status: AgentStatus = AgentStatus.AVAILABLE
    current_task: Optional[Task] = None
    team: Optional['Team'] = None

    def is_available(self) -> bool:
        """Check if agent is available for work."""
        return self.status == AgentStatus.AVAILABLE and self.current_task is None

    def claim_task(self, task: Task) -> bool:
        """
        Claim a task for this agent.

        Args:
            task: Task to claim

        Returns:
            True if successfully claimed, False if agent unavailable
        """
        if not self.is_available():
            return False

        self.current_task = task
        self.status = AgentStatus.WORKING
        task.agent_id = self.id
        return True

    def complete_task(self, result: Optional[str] = None) -> Optional[Task]:
        """
        Mark current task as complete and return to available.

        Args:
            result: Optional task result

        Returns:
            Completed task, or None if no task assigned
        """
        if not self.current_task:
            return None

        task = self.current_task
        task.status = TaskStatus.COMPLETED
        task.result = result

        self.current_task = None
        self.status = AgentStatus.AVAILABLE

        return task

    def get_status(self) -> Dict:
        """Get agent status summary."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role.value,
            'status': self.status.value,
            'current_task': self.current_task.id if self.current_task else None,
            'team': self.team.name if self.team else None
        }


@dataclass
class Team:
    """
    Represents a team within a department.

    Attributes:
        name: Team name
        lead: Team lead agent
        members: List of team member agents
        department: Parent department reference
    """
    name: str
    lead: Optional[Agent]
    members: List[Agent]
    department: Optional['Department'] = None

    def find_available_agent(self, role: Role) -> Optional[Agent]:
        """
        Find available agent in team with specified role.

        Args:
            role: Required role

        Returns:
            First available agent matching role
        """
        if self.lead and self.lead.role == role and self.lead.is_available():
            return self.lead

        for agent in self.members:
            if agent.role == role and agent.is_available():
                return agent

        return None

    def get_all_agents(self) -> List[Agent]:
        """Get all agents in team (lead + members)."""
        agents = []
        if self.lead:
            agents.append(self.lead)
        agents.extend(self.members)
        return agents

    def get_available_agents(self, role: Optional[Role] = None) -> List[Agent]:
        """
        Get available agents in team.

        Args:
            role: Optional role filter

        Returns:
            List of available agents
        """
        agents = [
            agent for agent in self.get_all_agents()
            if agent.is_available() and (not role or agent.role == role)
        ]
        return agents

    def get_status(self) -> Dict:
        """Get team status summary."""
        return {
            'name': self.name,
            'lead': self.lead.name if self.lead else None,
            'member_count': len(self.members),
            'available_count': len(self.get_available_agents()),
            'agents': [
                agent.get_status() for agent in self.get_all_agents()
            ]
        }


@dataclass
class Department:
    """
    Represents a department within the company.

    Attributes:
        name: Department name
        teams: Dict mapping team name to Team instance
        head: Optional department head agent
        company: Parent company reference
    """
    name: str
    teams: Dict[str, Team]
    head: Optional[Agent] = None
    company: Optional['Company'] = None

    def get_team(self, name: str) -> Optional[Team]:
        """Get team by name."""
        return self.teams.get(name)

    def find_available_agent(
        self,
        role: Role,
        team: Optional[str] = None
    ) -> Optional[Agent]:
        """
        Find available agent in this department.

        Args:
            role: Required role
            team: Optional team filter

        Returns:
            First available agent matching criteria
        """
        for team_name, team_obj in self.teams.items():
            if team and team_name != team:
                continue

            agent = team_obj.find_available_agent(role)
            if agent:
                return agent

        return None

    def get_all_agents(self) -> List[Agent]:
        """Get all agents in this department."""
        agents = []
        if self.head:
            agents.append(self.head)
        for team in self.teams.values():
            agents.extend(team.get_all_agents())
        return agents

    def get_available_agents(self, role: Optional[Role] = None) -> List[Agent]:
        """
        Get all available agents in department.

        Args:
            role: Optional role filter

        Returns:
            List of available agents
        """
        agents = [
            agent for team in self.teams.values()
            for agent in team.get_available_agents(role)
        ]
        return agents

    def get_status(self) -> Dict:
        """Get department status summary."""
        return {
            'name': self.name,
            'head': self.head.name if self.head else None,
            'teams': {
                name: team.get_status()
                for name, team in self.teams.items()
            },
            'total_agents': len(self.get_all_agents()),
            'available_agents': len(self.get_available_agents())
        }


@dataclass
class Company:
    """
    Represents an organization with departments and teams.

    Attributes:
        name: Company name
        departments: Dict mapping department name to Department instance
        redis_client: Optional Redis client for distributed coordination
        template_name: Name of YAML template used to create company
    """
    name: str
    departments: Dict[str, Department]
    redis_client: Optional['redis.Redis'] = None
    template_name: Optional[str] = None

    @classmethod
    def from_template(cls, template_name: str, redis_client: Optional['redis.Redis'] = None) -> 'Company':
        """
        Load company structure from YAML template.

        Args:
            template_name: Name of template file (without .yaml extension)
            redis_client: Optional Redis client for coordination

        Returns:
            Fully initialized Company instance

        Example:
            company = Company.from_template("janus_dev")
        """
        template = CompanyTemplate.load(template_name)
        return template.build(redis_client)

    def get_department(self, name: str) -> Optional[Department]:
        """Get department by name."""
        return self.departments.get(name)

    def find_available_agent(
        self,
        role: Role,
        department: Optional[str] = None,
        team: Optional[str] = None
    ) -> Optional[Agent]:
        """
        Find an available agent matching criteria.

        Args:
            role: Required role for agent
            department: Optional department filter
            team: Optional team filter

        Returns:
            First available agent matching criteria, or None

        Example:
            agent = company.find_available_agent(
                role=Role.QA_ENGINEER,
                department="engineering"
            )
        """
        for dept_name, dept in self.departments.items():
            if department and dept_name != department:
                continue

            agent = dept.find_available_agent(role, team)
            if agent:
                return agent

        return None

    def get_all_agents(self) -> List[Agent]:
        """Get all agents across all departments."""
        agents = []
        for dept in self.departments.values():
            agents.extend(dept.get_all_agents())
        return agents

    def get_agents_by_role(self, role: Role) -> List[Agent]:
        """Get all agents with specified role."""
        return [agent for agent in self.get_all_agents() if agent.role == role]

    def get_status(self) -> Dict:
        """
        Get company-wide status report.

        Returns:
            Dict with department summaries, agent counts, task statistics
        """
        return {
            'name': self.name,
            'departments': {
                name: dept.get_status()
                for name, dept in self.departments.items()
            },
            'total_agents': len(self.get_all_agents()),
            'agents_by_role': {
                role.value: len(self.get_agents_by_role(role))
                for role in Role
            }
        }


class CompanyTemplate:
    """
    Loads and builds company structures from YAML templates.
    """

    TEMPLATE_DIR = Path(__file__).parent / "templates"

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize template from parsed YAML data.

        Args:
            data: Parsed YAML template data
        """
        self.data = data

    @classmethod
    def load(cls, template_name: str) -> 'CompanyTemplate':
        """
        Load template from YAML file.

        Args:
            template_name: Template name (without .yaml extension)

        Returns:
            CompanyTemplate instance

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = cls.TEMPLATE_DIR / f"{template_name}.yaml"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path) as f:
            data = yaml.safe_load(f)

        return cls(data)

    def build(self, redis_client: Optional['redis.Redis'] = None) -> Company:
        """
        Build Company instance from template.

        Args:
            redis_client: Optional Redis client for coordination

        Returns:
            Fully initialized Company
        """
        company = Company(
            name=self.data['name'],
            departments={},
            redis_client=redis_client,
            template_name=self.data.get('template_name')
        )

        for dept_data in self.data.get('departments', []):
            department = self._build_department(dept_data, company)
            company.departments[department.name] = department

        return company

    def _build_department(self, dept_data: Dict, company: Company) -> Department:
        """Build Department from template data."""
        department = Department(
            name=dept_data['name'],
            teams={},
            company=company
        )

        if 'head' in dept_data:
            head_data = dept_data['head']
            department.head = self._build_agent(
                head_data,
                name=f"{dept_data['name']}-head",
                team=None
            )

        for team_data in dept_data.get('teams', []):
            team = self._build_team(team_data, department)
            department.teams[team.name] = team

        return department

    def _build_team(self, team_data: Dict, department: Department) -> Team:
        """Build Team from template data."""
        team = Team(
            name=team_data['name'],
            lead=None,
            members=[],
            department=department
        )

        if 'lead' in team_data:
            lead_data = team_data['lead']
            team.lead = self._build_agent(
                lead_data,
                name=f"{team.name}-lead",
                team=team
            )

        for member_data in team_data.get('members', []):
            agent = self._build_agent(member_data, team=team)
            team.members.append(agent)

        return team

    def _build_agent(
        self,
        agent_data: Dict,
        team: Optional[Team] = None,
        name: Optional[str] = None
    ) -> Agent:
        """Build Agent from template data."""
        role = Role(agent_data['role'])
        agent_id = agent_data.get('id', str(uuid.uuid4()))
        agent_name = name or agent_data.get('name', f"{role.value}-{agent_id[:8]}")

        return Agent(
            id=agent_id,
            name=agent_name,
            role=role,
            status=AgentStatus.AVAILABLE,
            team=team
        )
