# AgentCoord: Company Model Implementation Roadmap

## Vision
Model a real company's coordination patterns - not just engineering, but Product, Design, QA, Marketing, SRE, etc. - with cross-functional workflows that mirror how actual teams collaborate.

## Design Principles

1. **Easy to use** - `agentcoord init` → working org in <60 seconds
2. **Platform-agnostic** - Works out of box (terminal/TUI), Slack is optional
3. **Real workflows** - Feature development, launches, incidents mirror actual companies
4. **No external dependencies** - Core works without Slack/Discord/etc
5. **Extensible** - Easy to add new roles, departments, integrations

---

## Architecture

### Core Abstractions

```python
# Role hierarchy
Company
├── Department (Product, Engineering, Marketing, etc.)
│   ├── Team (Backend, Frontend, Growth, etc.)
│   │   └── Agent (Individual contributors)

# Communication (platform-agnostic)
Channel (abstract)
├── TerminalChannel (default, always works)
├── DashboardChannel (Rich TUI, always works)
├── FileChannel (logs, always works)
└── SlackChannel (optional, opt-in)

# Work artifacts
Epic (large initiative)
├── Story (user-facing feature)
│   └── Task (implementation work)

# Approval gates
ApprovalRequest
├── Approvers (by role: PM, EM, QA, etc.)
└── Status (pending, approved, rejected)
```

---

## Phase 1: Multi-Department Foundation

**Goal:** Support all company roles, not just engineering

### 1.1 Role System
```python
class Role(Enum):
    # Product
    VP_PRODUCT = "vp_product"
    PRODUCT_MANAGER = "pm"
    PRODUCT_DESIGNER = "designer"
    UX_RESEARCHER = "ux_researcher"

    # Engineering
    VP_ENGINEERING = "vp_eng"
    ENGINEERING_MANAGER = "em"
    SENIOR_ENGINEER = "senior_eng"
    ENGINEER = "engineer"
    SRE = "sre"

    # QA
    QA_LEAD = "qa_lead"
    QA_ENGINEER = "qa_eng"

    # Marketing
    VP_MARKETING = "vp_marketing"
    GROWTH_MANAGER = "growth"
    CONTENT_LEAD = "content"

    # Support
    SUPPORT_LEAD = "support_lead"
    SUPPORT_ENGINEER = "support_eng"

class RoleCapabilities:
    """Defines what each role can do"""
    PERMISSIONS = {
        Role.PRODUCT_MANAGER: [
            "create_prd",
            "approve_release",
            "prioritize_roadmap"
        ],
        Role.ENGINEERING_MANAGER: [
            "assign_tasks",
            "approve_architecture",
            "deploy_staging"
        ],
        Role.QA_LEAD: [
            "approve_release",
            "file_bugs",
            "create_test_plans"
        ],
        # ... etc
    }
```

**Files to create:**
- `agentcoord/roles.py` - Role definitions and capabilities
- `agentcoord/departments.py` - Department structure
- `tests/test_roles.py` - Role permission tests

---

### 1.2 Department Hierarchies

```python
class Department:
    """A department within the company"""
    def __init__(self, name: str, vp: Agent):
        self.name = name
        self.vp = vp
        self.teams: list[Team] = []
        self.agents: list[Agent] = []

    def add_team(self, team: Team):
        self.teams.append(team)

    def get_available_agents(self, role: Role = None):
        """Find available agents, optionally filtered by role"""
        agents = [a for a in self.agents if a.is_available()]
        if role:
            agents = [a for a in agents if a.role == role]
        return agents

class Team:
    """A team within a department (e.g., Backend team in Engineering)"""
    def __init__(self, name: str, lead: Agent, department: Department):
        self.name = name
        self.lead = lead
        self.department = department
        self.members: list[Agent] = [lead]

    def add_member(self, agent: Agent):
        self.members.append(agent)
        agent.team = self

class Company:
    """Top-level company organization"""
    def __init__(self, name: str):
        self.name = name
        self.departments: dict[str, Department] = {}

    @classmethod
    def create_from_template(cls, template: str):
        """Create company from template (startup, scaleup, etc.)"""
        # Load template and create departments/teams/agents
        pass
```

**Files to create:**
- `agentcoord/company.py` - Company, Department, Team classes
- `agentcoord/templates/` - Org templates (startup, scaleup, etc.)
- `tests/test_company.py` - Org structure tests

---

### 1.3 Communication Channel Abstraction

```python
class CommunicationChannel(ABC):
    """Abstract base for all communication channels"""

    @abstractmethod
    def post(self, channel: str, message: str, priority: str = "normal", **kwargs):
        """Post message to channel"""
        pass

    @abstractmethod
    def dm(self, from_agent: str, to_agent: str, message: str):
        """Direct message between agents"""
        pass

    @abstractmethod
    def create_thread(self, channel: str, title: str, message: str):
        """Create threaded conversation"""
        pass

class TerminalChannel(CommunicationChannel):
    """Default: prints to terminal (always available)"""
    def post(self, channel: str, message: str, priority: str = "normal", **kwargs):
        color = "red" if priority == "urgent" else "white"
        console.print(f"[{channel}] {message}", style=color)

class DashboardChannel(CommunicationChannel):
    """Rich TUI dashboard (always available)"""
    def __init__(self, dashboard: Dashboard):
        self.dashboard = dashboard

    def post(self, channel: str, message: str, **kwargs):
        self.dashboard.add_message(channel, message)

class FileChannel(CommunicationChannel):
    """File-based logs (always available)"""
    def post(self, channel: str, message: str, **kwargs):
        log_file = Path(f"channels/{channel}.log")
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} {message}\n")

class SlackChannel(CommunicationChannel):
    """Slack integration (optional, requires slack_sdk)"""
    def __init__(self, token: str, channel_map: dict):
        try:
            from slack_sdk import WebClient
            self.client = WebClient(token=token)
            self.channel_map = channel_map
        except ImportError:
            raise RuntimeError("Install slack_sdk: pip install agentcoord[slack]")

    def post(self, channel: str, message: str, **kwargs):
        slack_channel = self.channel_map.get(channel, channel)
        self.client.chat_postMessage(channel=slack_channel, text=message, **kwargs)

class ChannelManager:
    """Manages multiple channel adapters"""
    def __init__(self):
        self.adapters: list[CommunicationChannel] = [
            TerminalChannel(),  # Always enabled
            FileChannel(),      # Always enabled
        ]

    def add_adapter(self, adapter: CommunicationChannel):
        self.adapters.append(adapter)

    def post(self, channel: str, message: str, adapters: list[str] = None, **kwargs):
        """Post to all adapters (or subset if specified)"""
        for adapter in self.adapters:
            if adapters is None or adapter.__class__.__name__ in adapters:
                adapter.post(channel, message, **kwargs)
```

**Files to create:**
- `agentcoord/channels.py` - Channel abstraction + built-in adapters
- `agentcoord/integrations/slack.py` - Slack adapter (optional)
- `tests/test_channels.py` - Channel tests

---

### 1.4 Cross-Functional Task Routing

```python
class WorkArtifact:
    """Base class for all work items"""
    def __init__(self, title: str, created_by: Agent):
        self.id = str(uuid.uuid4())
        self.title = title
        self.created_by = created_by
        self.created_at = datetime.now()
        self.status = "open"

class Epic(WorkArtifact):
    """Large initiative that spans multiple teams/departments"""
    def __init__(self, title: str, created_by: Agent, departments: list[str]):
        super().__init__(title, created_by)
        self.departments = departments  # Which departments involved
        self.stories: list[Story] = []

class Story(WorkArtifact):
    """User-facing feature or capability"""
    def __init__(self, title: str, created_by: Agent, epic: Epic, assigned_to: Team):
        super().__init__(title, created_by)
        self.epic = epic
        self.assigned_to = assigned_to
        self.tasks: list[Task] = []

class Task(WorkArtifact):
    """Specific implementation work"""
    def __init__(self, title: str, created_by: Agent, story: Story,
                 assigned_to: Agent, role_required: Role):
        super().__init__(title, created_by)
        self.story = story
        self.assigned_to = assigned_to
        self.role_required = role_required  # PM, Eng, QA, etc.

class WorkflowRouter:
    """Routes work artifacts to appropriate teams/roles"""

    # Define workflow for each epic type
    WORKFLOWS = {
        "feature": [
            (Role.PRODUCT_MANAGER, "write_prd"),
            (Role.PRODUCT_DESIGNER, "create_mocks"),
            (Role.ENGINEER, "implement"),
            (Role.QA_ENGINEER, "test"),
            (Role.PRODUCT_MANAGER, "approve_release"),
            (Role.GROWTH_MANAGER, "launch"),
        ],
        "bug": [
            (Role.QA_ENGINEER, "reproduce"),
            (Role.ENGINEER, "fix"),
            (Role.QA_ENGINEER, "verify"),
        ],
        "launch": [
            (Role.PRODUCT_MANAGER, "create_plan"),
            (Role.GROWTH_MANAGER, "create_content"),
            (Role.ENGINEER, "feature_flag"),
            (Role.QA_ENGINEER, "regression_test"),
            (Role.SUPPORT_LEAD, "prepare_docs"),
        ],
        "trading_strategy": [  # Janus-specific workflow
            (Role.PRODUCT_MANAGER, "define_strategy_goals"),
            (Role.PRODUCT_DESIGNER, "design_config_schema"),
            (Role.ENGINEER, "implement_filter"),
            (Role.ENGINEER, "write_tests"),
            (Role.QA_ENGINEER, "run_backtest"),
            (Role.QA_ENGINEER, "validate_metrics"),
            (Role.PRODUCT_MANAGER, "approve_for_production"),
            (Role.SRE, "deploy_to_telegram_bot"),
        ],
    }

    def route_epic(self, epic: Epic, workflow_type: str, company: Company):
        """Create tasks following workflow pattern"""
        workflow = self.WORKFLOWS[workflow_type]

        for i, (role, action) in enumerate(workflow):
            # Find team/department with this role
            team = company.find_team_with_role(role)

            # Create task
            task = Task(
                title=f"{epic.title}: {action}",
                created_by=epic.created_by,
                story=epic.stories[0],  # Simplified
                assigned_to=team.get_available_agent(role),
                role_required=role
            )

            # Set dependencies (task i blocks task i+1)
            if i > 0:
                task.blocked_by = [workflow[i-1]]
```

**Files to create:**
- `agentcoord/workflows.py` - Epic, Story, Task, WorkflowRouter
- `agentcoord/routing.py` - Cross-functional routing logic
- `tests/test_workflows.py` - Workflow tests

---

## Phase 2: Core Workflows (Week 2)

### 2.1 Feature Development Cycle

```python
class FeatureDevelopmentWorkflow:
    """PM → Design → Eng → QA → Launch"""

    def initiate(self, pm: Agent, title: str, description: str):
        # PM creates PRD
        prd = pm.create_document(
            type="prd",
            title=title,
            content=description
        )

        # Auto-assign to design
        design_task = Task.create(
            title=f"Design: {title}",
            role_required=Role.PRODUCT_DESIGNER,
            blocked_by=None
        )

        # Design creates mocks (blocks engineering)
        # Engineering implements (blocks QA)
        # QA validates (blocks launch)
        # PM approves launch
```

### 2.2 Approval Gates

```python
class ApprovalGate:
    """Require approval from specific roles before proceeding"""

    GATES = {
        "feature_spec": [Role.PRODUCT_MANAGER, Role.ENGINEERING_MANAGER],
        "design_mocks": [Role.PRODUCT_MANAGER],
        "production_deploy": [Role.ENGINEERING_MANAGER, Role.QA_LEAD],
        "public_announcement": [Role.VP_MARKETING],
    }

    def request_approval(self, gate_type: str, context: dict, requestor: Agent):
        required_approvers = self.GATES[gate_type]

        # Create approval request
        approval = ApprovalRequest(
            gate_type=gate_type,
            context=context,
            requestor=requestor,
            required_approvers=required_approvers
        )

        # Notify approvers via channels
        for role in required_approvers:
            self.notify_approver(role, approval)

        return approval
```

---

## Phase 3: Templates & Onboarding (Week 3)

### 3.1 Company Templates

**Startup (Seed)**
```yaml
name: "Seed Stage Startup"
departments:
  - name: product
    vp: null
    teams:
      - name: product
        lead: {role: pm}
        members: [{role: designer}]

  - name: engineering
    vp: null
    teams:
      - name: engineering
        lead: {role: em}
        members: [{role: senior_eng}, {role: engineer}, {role: engineer}]

  - name: marketing
    vp: null
    teams:
      - name: growth
        lead: {role: growth}
        members: []
```

### 3.2 CLI Wizard

```bash
$ agentcoord init

Welcome to AgentCoord!

? Company name: Acme Inc
? Template: [Startup (Seed), Startup (Series A), Scaleup, Custom]
> Startup (Seed)

Creating your organization...
✓ Created Product department (1 PM, 1 Designer)
✓ Created Engineering department (1 EM, 3 Engineers)
✓ Created Marketing department (1 Growth)
✓ Started communication channels
✓ Dashboard ready

Your company is ready! Launch dashboard:
  agentcoord dashboard

Or submit your first epic:
  agentcoord epic create "Build user authentication"
```

---

## Phase 4: Dogfooding with Janus (Week 4)

### Use AgentCoord to coordinate Janus trading engine development

AgentCoord will manage feature development for Janus (options trading engine at ~/Desktop/Janus_Engine/janus). This validates the full cross-functional workflow with a real production system.

**Example Epic: Implement IV Percentile Filter for Janus**

```bash
# Create company modeling the Janus development team
agentcoord init --template startup

# Configure Janus as the product
agentcoord config set project_path ~/Desktop/Janus_Engine/janus

# Submit epic for new trading filter
agentcoord epic create "Add IV Percentile Filter" \
  --type feature \
  --priority high \
  --description "Filter trades to only enter when IV percentile > 50th to ensure adequate volatility premium"

# Watch agents work
agentcoord dashboard

# Agents automatically coordinate:
# 1. PM writes PRD with acceptance criteria (IV percentile calculation, backtestable)
# 2. Design creates strategy parameter config schema
# 3. Engineering implements:
#    - src/filters/iv_percentile.py
#    - Integration with existing strategy engine
#    - Unit tests for percentile calculation
# 4. QA runs backtests:
#    - Validates IV percentile calculations against historical data
#    - Confirms filter reduces entry count appropriately
#    - Runs full test suite (pytest)
# 5. PM reviews backtest results and approves for production
# 6. Engineering deploys to live Telegram bot
```

**Real Multi-Department Workflow:**

```python
# PM Agent creates PRD
prd = {
    "title": "IV Percentile Filter",
    "acceptance_criteria": [
        "Calculate IV percentile using 252-day rolling window",
        "Only enter trades when IV > 50th percentile",
        "Backtest shows improved premium capture vs current strategy",
        "Parameter configurable via strategy YAML"
    ],
    "success_metrics": [
        "Avg premium per trade increases by 15%+",
        "All existing tests pass",
        "New tests achieve >90% coverage"
    ]
}

# Design Agent creates schema
config_schema = {
    "iv_percentile_threshold": {
        "type": "float",
        "default": 0.50,
        "range": [0.0, 1.0],
        "description": "Minimum IV percentile to enter trade"
    }
}

# Engineering Agent implements
class IVPercentileFilter(Filter):
    def evaluate(self, chain: OptionChain, config: dict) -> bool:
        """Filter trades by IV percentile."""
        iv = chain.get_current_iv()
        percentile = self._calculate_percentile(chain.symbol, iv)
        return percentile >= config["iv_percentile_threshold"]

# QA Agent runs validation
backtest_results = backtester.run(
    strategy="iv_percentile_filter",
    start="2024-01-01",
    end="2025-01-01",
    params={"iv_percentile_threshold": 0.50}
)

# QA validates:
assert backtest_results.total_trades < baseline.total_trades  # Filtered correctly
assert backtest_results.avg_premium > baseline.avg_premium    # Better premium
assert pytest.run("tests/") == "ALL PASS"                     # No regressions
```

**Why Janus is the Perfect Dogfooding Example:**

1. **Real cross-functional workflow**: PM defines strategy goals, Design creates config schema, Eng implements, QA backtests with actual market data
2. **Approval gates matter**: Can't deploy to live trading without QA sign-off on backtest results
3. **Multiple teams**: Backend (filters, pricing), Infrastructure (Telegram bot, Schwab API), QA (backtesting)
4. **Production consequences**: Bad code loses real money, tests quality gates rigorously
5. **Existing codebase**: 9,628 lines, 50+ tests, established patterns to follow

---

## File Structure

```
agentcoord/
├── roles.py              # Role definitions & capabilities
├── departments.py        # Department structure
├── company.py           # Company, Team classes
├── channels.py          # Communication abstraction
├── workflows.py         # Epic, Story, Task
├── routing.py           # Cross-functional routing
├── approvals.py         # Approval gate system
├── templates/           # Org templates
│   ├── seed.yaml
│   ├── series_a.yaml
│   └── scaleup.yaml
├── integrations/
│   ├── slack.py         # Optional Slack adapter
│   └── discord.py       # Optional Discord adapter
└── cli/
    ├── init.py          # agentcoord init
    └── epic.py          # agentcoord epic

tests/
├── test_roles.py
├── test_company.py
├── test_channels.py
├── test_workflows.py
└── test_integration.py
```

---

## Success Criteria

**Week 1:**
- [ ] Multi-role system implemented (PM, Design, Eng, QA, Marketing, SRE)
- [ ] Department/team hierarchy working
- [ ] Communication channels (terminal, file) working
- [ ] Can create company with multiple departments

**Week 2:**
- [ ] Feature development workflow (PM → Design → Eng → QA)
- [ ] Approval gates functional
- [ ] Cross-department task routing works
- [ ] Agents can claim tasks by role

**Week 3:**
- [ ] `agentcoord init` wizard working
- [ ] 3 templates available (seed, series A, scaleup)
- [ ] CLI commands functional
- [ ] Documentation complete

**Week 4:**
- [ ] Use AgentCoord to build a feature in AgentCoord
- [ ] Slack adapter working (optional)
- [ ] Demo video recorded
- [ ] Published to PyPI

---

## Next Steps

1. Create role system (`agentcoord/roles.py`)
2. Build department hierarchy (`agentcoord/company.py`)
3. Implement channel abstraction (`agentcoord/channels.py`)
4. Test multi-department coordination using Janus

---

## Janus Integration Plan

**Phase 1: Foundation (Use Janus for validation)**

After implementing roles, departments, and channels, validate by creating a company template for the Janus development team:

```yaml
# agentcoord/templates/janus_dev.yaml
name: "Janus Trading Engine Team"
project_path: "~/Desktop/Janus_Engine/janus"

departments:
  - name: product
    teams:
      - name: strategy
        lead: {role: pm, name: "strategy_pm"}
        members: [{role: designer, name: "config_designer"}]

  - name: engineering
    teams:
      - name: backend
        lead: {role: em, name: "backend_em"}
        members: [
          {role: senior_eng, name: "filters_eng"},
          {role: engineer, name: "pricing_eng"}
        ]
      - name: infrastructure
        lead: {role: sre, name: "devops_lead"}
        members: [{role: sre, name: "telegram_eng"}]

  - name: qa
    teams:
      - name: testing
        lead: {role: qa_lead, name: "qa_lead"}
        members: [{role: qa_eng, name: "backtest_eng"}]
```

**Phase 2: First Epic (Validate workflows)**

```bash
# After Phase 1 is complete, run first real epic:
agentcoord init --template janus_dev
agentcoord epic create "Implement VIX Term Structure Filter" \
  --type trading_strategy \
  --priority high

# Agents coordinate:
# - PM defines entry/exit rules based on VIX term structure
# - Design creates YAML schema for VIX threshold params
# - Engineering implements VixTermStructureFilter class
# - Engineering writes pytest tests with realistic fixtures
# - QA runs backtest (2024-01-01 to 2025-01-01)
# - QA validates: fewer trades, higher avg premium
# - PM reviews metrics, approves for production
# - SRE deploys to live Telegram bot
```

**Phase 3: Approval Gates (Validate cross-role coordination)**

```python
# Before deploying any Janus strategy to production:
approval = ApprovalGate.request_approval(
    gate_type="production_trading_deploy",
    context={
        "strategy": "vix_term_structure",
        "backtest_sharpe": 1.42,
        "backtest_max_drawdown": -0.15,
        "test_coverage": 0.94
    },
    requestor=sre_agent
)

# Requires sign-off from:
# - QA Lead (backtest results acceptable)
# - Engineering Manager (code reviewed, tests pass)
# - Product Manager (aligns with strategy goals)

# Only after all 3 approve → deploy to live bot
```

**Success Criteria:**

- [ ] Can create Janus company from template
- [ ] Agents claim tasks by role (PM, Eng, QA, SRE)
- [ ] PM agent writes strategy PRD
- [ ] Eng agent implements filter + tests
- [ ] QA agent runs backtest and validates results
- [ ] Approval gate blocks production deploy until all approvers sign off
- [ ] Terminal/file channels show real-time agent coordination
- [ ] Full audit trail of who did what

---

Ready to start with Phase 1.1: Role System?
