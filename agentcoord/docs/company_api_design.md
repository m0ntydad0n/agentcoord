# Company Hierarchy API Design

## Overview

The Company Hierarchy API provides a structured organizational model for coordinating multiple LLM agents across departments, teams, and roles. This design supports the Janus use case (backend, infrastructure, QA teams) and generalizes to arbitrary company structures.

## Architecture

### Class Hierarchy

```
Company
├── Department(s)
│   ├── Team(s)
│   │   ├── TeamLead (Agent)
│   │   └── Member(s) (Agent)
│   └── DepartmentHead (Agent)
└── CompanyTemplate (YAML loader)
```

### Core Classes

#### 1. `Company`

Top-level container representing the entire organization.

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from agentcoord.roles import Role
from agentcoord.tasks import Task

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
    departments: Dict[str, 'Department']
    redis_client: Optional[redis.Redis] = None
    template_name: Optional[str] = None

    @classmethod
    def from_template(cls, template_name: str, redis_client: Optional[redis.Redis] = None) -> 'Company':
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

    def get_department(self, name: str) -> Optional['Department']:
        """Get department by name."""
        return self.departments.get(name)

    def find_available_agent(
        self,
        role: Role,
        department: Optional[str] = None,
        team: Optional[str] = None
    ) -> Optional['Agent']:
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

    def get_all_agents(self) -> List['Agent']:
        """Get all agents across all departments."""
        agents = []
        for dept in self.departments.values():
            agents.extend(dept.get_all_agents())
        return agents

    def get_agents_by_role(self, role: Role) -> List['Agent']:
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
```

#### 2. `Department`

Organizational division containing multiple teams.

```python
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
    teams: Dict[str, 'Team']
    head: Optional['Agent'] = None
    company: Optional['Company'] = None

    def get_team(self, name: str) -> Optional['Team']:
        """Get team by name."""
        return self.teams.get(name)

    def find_available_agent(
        self,
        role: Role,
        team: Optional[str] = None
    ) -> Optional['Agent']:
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

    def get_all_agents(self) -> List['Agent']:
        """Get all agents in this department."""
        agents = []
        if self.head:
            agents.append(self.head)
        for team in self.teams.values():
            agents.extend(team.get_all_agents())
        return agents

    def get_available_agents(self, role: Optional[Role] = None) -> List['Agent']:
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
```

#### 3. `Team`

Working group within a department.

```python
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
    lead: Optional['Agent']
    members: List['Agent']
    department: Optional['Department'] = None

    def find_available_agent(self, role: Role) -> Optional['Agent']:
        """
        Find available agent in team with specified role.

        Args:
            role: Required role

        Returns:
            First available agent matching role
        """
        # Check lead first
        if self.lead and self.lead.role == role and self.lead.is_available():
            return self.lead

        # Check members
        for agent in self.members:
            if agent.role == role and agent.is_available():
                return agent

        return None

    def get_all_agents(self) -> List['Agent']:
        """Get all agents in team (lead + members)."""
        agents = []
        if self.lead:
            agents.append(self.lead)
        agents.extend(self.members)
        return agents

    def get_available_agents(self, role: Optional[Role] = None) -> List['Agent']:
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
```

#### 4. `Agent`

Individual agent with role and availability tracking.

```python
from enum import Enum

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
        task.claimed_by = self.id
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
```

#### 5. `CompanyTemplate`

YAML template loader and builder.

```python
import yaml
from pathlib import Path
from typing import Any, Dict

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

    def build(self, redis_client: Optional[redis.Redis] = None) -> Company:
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

        # Build departments
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

        # Build department head if specified
        if 'head' in dept_data:
            head_data = dept_data['head']
            department.head = self._build_agent(
                head_data,
                name=f"{dept_data['name']}-head",
                team=None
            )

        # Build teams
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

        # Build team lead
        if 'lead' in team_data:
            lead_data = team_data['lead']
            team.lead = self._build_agent(
                lead_data,
                name=f"{team.name}-lead",
                team=team
            )

        # Build team members
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
        import uuid

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
```

## YAML Template Schema

### Structure

```yaml
name: "Company Name"                # Required: Company name
template_name: "template_id"        # Optional: Template identifier
departments:                        # Required: List of departments
  - name: "department_name"         # Required: Department name
    head:                           # Optional: Department head
      role: "role_name"             # Required: Role from Role enum
      name: "agent_name"            # Optional: Custom agent name
      id: "agent_id"                # Optional: Custom agent ID
    teams:                          # Required: List of teams
      - name: "team_name"           # Required: Team name
        lead:                       # Optional: Team lead
          role: "role_name"         # Required: Role from Role enum
          name: "agent_name"        # Optional: Custom name
        members:                    # Required: List of team members
          - role: "role_name"       # Required: Role from Role enum
            name: "agent_name"      # Optional: Custom name
            id: "agent_id"          # Optional: Custom ID
```

### Example: Janus Development Template

File: `agentcoord/templates/janus_dev.yaml`

```yaml
name: "Janus Development Team"
template_name: "janus_dev"
departments:
  - name: "engineering"
    head:
      role: "vp_engineering"
      name: "VP Engineering"
    teams:
      - name: "backend"
        lead:
          role: "em"
          name: "Backend EM"
        members:
          - role: "senior_eng"
            name: "Senior Backend Engineer"
          - role: "engineer"
            name: "Backend Engineer 1"
          - role: "engineer"
            name: "Backend Engineer 2"

      - name: "infrastructure"
        lead:
          role: "em"
          name: "Infrastructure EM"
        members:
          - role: "senior_eng"
            name: "Senior DevOps Engineer"
          - role: "engineer"
            name: "Infrastructure Engineer"

      - name: "qa"
        lead:
          role: "qa_lead"
          name: "QA Lead"
        members:
          - role: "qa_engineer"
            name: "QA Engineer 1"
          - role: "qa_engineer"
            name: "QA Engineer 2"
```

### Example: Simple Startup Template

File: `agentcoord/templates/startup_mvp.yaml`

```yaml
name: "Startup MVP Team"
template_name: "startup_mvp"
departments:
  - name: "product"
    teams:
      - name: "fullstack"
        lead:
          role: "em"
          name: "Tech Lead"
        members:
          - role: "engineer"
            name: "Full Stack Developer"
          - role: "qa_engineer"
            name: "QA Engineer"
```

## Example Usage Patterns

### 1. Loading from Template

```python
from agentcoord.company import Company
from agentcoord.roles import Role
import redis

# Without Redis (file-based fallback)
company = Company.from_template("janus_dev")

# With Redis coordination
redis_client = redis.from_url("redis://localhost:6379")
company = Company.from_template("janus_dev", redis_client=redis_client)
```

### 2. Querying Agents

```python
# Get department
eng_dept = company.departments["engineering"]

# Get all available engineers
available_engineers = eng_dept.get_available_agents(role=Role.ENGINEER)

# Get specific team
backend_team = eng_dept.teams["backend"]

# Get team status
print(backend_team.get_status())
```

### 3. Finding Available Agents

```python
# Find any available QA engineer
qa_agent = company.find_available_agent(role=Role.QA_ENGINEER)

# Find QA engineer in specific department
qa_agent = company.find_available_agent(
    role=Role.QA_ENGINEER,
    department="engineering"
)

# Find engineer in specific team
backend_agent = company.find_available_agent(
    role=Role.ENGINEER,
    department="engineering",
    team="backend"
)
```

### 4. Agent Task Assignment

```python
from agentcoord.tasks import Task, TaskQueue

# Create task queue
task_queue = TaskQueue(redis_client)

# Create task
task = task_queue.create_task(
    title="Implement user authentication",
    description="Add JWT-based authentication to API",
    priority=5
)

# Find available agent
agent = company.find_available_agent(role=Role.ENGINEER, team="backend")

if agent:
    # Agent claims task
    if agent.claim_task(task):
        print(f"{agent.name} claimed task: {task.title}")

    # ... agent works on task ...

    # Agent completes task
    completed_task = agent.complete_task(result="Auth implemented successfully")
    task_queue.complete_task(completed_task.id, completed_task.result)
```

### 5. Company-Wide Status

```python
# Get full company status
status = company.get_status()

print(f"Company: {status['name']}")
print(f"Total agents: {status['total_agents']}")

for dept_name, dept_status in status['departments'].items():
    print(f"\nDepartment: {dept_name}")
    print(f"  Available: {dept_status['available_agents']}")

    for team_name, team_status in dept_status['teams'].items():
        print(f"  Team {team_name}: {team_status['available_count']}/{team_status['member_count']} available")
```

### 6. Coordinator Integration

```python
from agentcoord import CoordinationClient

# Coordinator uses company structure
coordinator = CoordinationClient(redis_url="redis://localhost:6379")
company = Company.from_template("janus_dev", redis_client=coordinator.redis_client)

# Coordinator assigns tasks to agents
task = coordinator.create_task("Implement feature X")

# Find best agent for task
agent = company.find_available_agent(role=Role.SENIOR_ENG, department="engineering")

if agent:
    coordinator.assign_task(task.id, agent.id)
    agent.claim_task(task)
```

## Integration Points

### With TaskQueue

Agents claim and complete tasks through the `TaskQueue` interface:

```python
# Agent workflow
agent = company.find_available_agent(role=Role.ENGINEER)
task = task_queue.claim_task(agent.id)

if task:
    agent.claim_task(task)  # Update agent state
    # ... work happens ...
    agent.complete_task(result="Done")
    task_queue.complete_task(task.id, result="Done")
```

### With CoordinationClient

Company hierarchy integrates with existing coordination:

```python
# Coordinator manages company
coordinator = CoordinationClient(redis_url="redis://localhost:6379")
company = Company.from_template("janus_dev", coordinator.redis_client)

# Monitor team health
eng_dept = company.departments["engineering"]
for team in eng_dept.teams.values():
    available = team.get_available_agents()
    if len(available) == 0:
        coordinator.post_thread(
            title=f"Team {team.name} fully utilized",
            message="Consider adding more capacity",
            priority="high"
        )
```

### With Role System

Company uses `Role` enum from role system:

```python
from agentcoord.roles import Role

# Template references roles
agent = Agent(
    id="agent-1",
    name="John",
    role=Role.SENIOR_ENG  # From role system
)

# Query by role
seniors = company.get_agents_by_role(Role.SENIOR_ENG)
```

## File Structure

```
agentcoord/
├── company.py              # Company, Department, Team, Agent classes
├── templates/              # YAML templates directory
│   ├── janus_dev.yaml      # Janus development template
│   ├── startup_mvp.yaml    # Simple startup template
│   └── enterprise.yaml     # Large enterprise template
└── docs/
    └── company_api_design.md  # This document
```

## Next Steps

1. Implement `agentcoord/company.py` with classes defined above
2. Create template YAML files in `agentcoord/templates/`
3. Write comprehensive tests in `tests/test_company.py`
4. Integrate with existing `Role` system
5. Add Redis persistence for agent state
6. Create CLI commands for company management

## Design Rationale

### Why This Structure?

1. **Familiar Mental Model**: Mirrors real-world organizational structures
2. **Flexible Querying**: Find agents by role, department, team, or availability
3. **Template-Based**: Easy to define new organizational structures via YAML
4. **Integration-Ready**: Works with existing TaskQueue and CoordinationClient
5. **Scalable**: Supports small teams and large enterprises

### Alternatives Considered

1. **Flat Agent Pool**: Simpler but loses organizational context
2. **Role-Only Hierarchy**: Doesn't capture team/department boundaries
3. **Graph-Based**: More flexible but harder to reason about

The chosen design balances flexibility with ease of use for the Janus use case while generalizing to other scenarios.
