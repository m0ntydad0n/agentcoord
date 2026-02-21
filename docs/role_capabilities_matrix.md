# Role Capabilities Matrix

This document defines the capabilities and approval authorities for each role in AgentCoord's company model.

## Roles Taxonomy

AgentCoord models five departments with 15 distinct roles:

- **Product**: VP_PRODUCT, PRODUCT_MANAGER, PRODUCT_DESIGNER, UX_RESEARCHER
- **Engineering**: VP_ENGINEERING, ENGINEERING_MANAGER, SENIOR_ENGINEER, ENGINEER, SRE
- **QA**: QA_LEAD, QA_ENGINEER
- **Marketing**: VP_MARKETING, GROWTH_MANAGER, CONTENT_LEAD
- **Support**: SUPPORT_LEAD, SUPPORT_ENGINEER

---

## Capabilities Matrix

### Product Department

| Role | Capabilities | Description |
|------|-------------|-------------|
| **VP_PRODUCT** | `approve_roadmap`, `prioritize_epics`, `override_pm_decisions`, `allocate_product_resources`, `approve_public_announcement` | Strategic product direction, final say on priorities |
| **PRODUCT_MANAGER** | `create_prd`, `approve_release`, `prioritize_roadmap`, `request_design`, `request_engineering`, `approve_design_mocks`, `define_acceptance_criteria`, `approve_feature_spec`, `approve_trading_strategy_for_production` | Owns feature definition, acceptance criteria, and release decisions |
| **PRODUCT_DESIGNER** | `create_design_mocks`, `create_prototypes`, `create_design_system`, `review_ux`, `design_config_schema` | Visual and interaction design, schema design |
| **UX_RESEARCHER** | `conduct_user_research`, `analyze_user_feedback`, `create_personas`, `run_usability_tests` | User research and validation |

### Engineering Department

| Role | Capabilities | Description |
|------|-------------|-------------|
| **VP_ENGINEERING** | `approve_architecture`, `allocate_eng_resources`, `approve_production_deploy`, `override_em_decisions`, `set_technical_standards` | Technical strategy, architecture decisions, production authority |
| **ENGINEERING_MANAGER** | `assign_tasks`, `approve_architecture`, `deploy_staging`, `review_code`, `approve_merge`, `approve_production_deploy`, `approve_feature_spec` | Team management, code quality, deployment authority |
| **SENIOR_ENGINEER** | `implement_features`, `write_tests`, `review_code`, `approve_merge`, `design_architecture`, `mentor_engineers`, `deploy_staging` | Senior IC, architecture input, mentorship |
| **ENGINEER** | `implement_features`, `write_tests`, `review_code`, `fix_bugs`, `write_documentation`, `implement_filters`, `implement_pricing_logic` | Individual contributor, feature implementation |
| **SRE** | `deploy_staging`, `deploy_production`, `monitor_systems`, `create_alerts`, `manage_infrastructure`, `rollback_deploy`, `deploy_to_telegram_bot` | Operations, deployment, monitoring |

### QA Department

| Role | Capabilities | Description |
|------|-------------|-------------|
| **QA_LEAD** | `approve_release`, `file_bugs`, `create_test_plans`, `approve_production_deploy`, `design_test_strategy`, `approve_backtest_results`, `validate_trading_metrics` | Test strategy, release approval, backtest validation |
| **QA_ENGINEER** | `file_bugs`, `write_test_cases`, `execute_tests`, `verify_fixes`, `run_regression_tests`, `reproduce_bugs`, `run_backtest`, `validate_metrics` | Test execution, bug verification, backtesting |

### Marketing Department

| Role | Capabilities | Description |
|------|-------------|-------------|
| **VP_MARKETING** | `approve_public_announcement`, `allocate_marketing_budget`, `approve_campaigns`, `set_marketing_strategy` | Marketing strategy, public communications authority |
| **GROWTH_MANAGER** | `create_launch_plan`, `run_growth_experiments`, `analyze_metrics`, `manage_campaigns`, `create_content`, `launch_features` | Growth initiatives, launch coordination |
| **CONTENT_LEAD** | `create_content`, `write_documentation`, `manage_blog`, `create_marketing_materials`, `write_release_notes` | Content creation, documentation |

### Support Department

| Role | Capabilities | Description |
|------|-------------|-------------|
| **SUPPORT_LEAD** | `prepare_docs`, `create_runbooks`, `escalate_issues`, `file_bugs`, `approve_support_procedures` | Support strategy, documentation, escalations |
| **SUPPORT_ENGINEER** | `answer_tickets`, `create_faqs`, `reproduce_bugs`, `write_documentation`, `escalate_issues` | Front-line support, documentation |

---

## Approval Gates

Certain operations require approval from specific roles before proceeding. These gates ensure cross-functional alignment and quality.

### Standard Gates

| Gate | Required Approvers | Description | When Required |
|------|-------------------|-------------|---------------|
| **feature_spec** | PRODUCT_MANAGER, ENGINEERING_MANAGER | Feature requirements approved | Before design phase begins |
| **design_mocks** | PRODUCT_MANAGER | Design approved | Before engineering implementation |
| **production_deploy** | ENGINEERING_MANAGER, QA_LEAD | Code quality and testing verified | Before any production deployment |
| **public_announcement** | VP_MARKETING | Marketing copy approved | Before external communications |

### Janus-Specific Gates

For trading strategy development (Janus use case):

| Gate | Required Approvers | Description | When Required |
|------|-------------------|-------------|---------------|
| **production_trading_deploy** | PRODUCT_MANAGER, QA_LEAD, ENGINEERING_MANAGER | Strategy goals, backtest results, and code quality all approved | Before deploying strategy to live trading bot |
| **backtest_validation** | QA_LEAD | Backtest results meet acceptance criteria | Before PM approval for production |
| **strategy_config_schema** | PRODUCT_DESIGNER, ENGINEERING_MANAGER | Schema design approved | Before implementation begins |

**Rationale for Janus Gates:**

Trading strategies have production consequences (real money at risk), so approval gates are strictly enforced:

1. **QA_LEAD** must validate backtest results (Sharpe ratio, drawdown, premium capture, test coverage)
2. **ENGINEERING_MANAGER** must verify code quality (tests pass, no regressions, determinism verified)
3. **PRODUCT_MANAGER** must confirm strategy aligns with goals (risk tolerance, return targets)
4. **SRE** executes deployment only after all three approvals

---

## Role Hierarchies

### Reporting Structure

```
VP_PRODUCT
├── PRODUCT_MANAGER
├── PRODUCT_DESIGNER
└── UX_RESEARCHER

VP_ENGINEERING
├── ENGINEERING_MANAGER
│   ├── SENIOR_ENGINEER
│   └── ENGINEER
└── SRE (may report to VP or EM depending on org)

QA_LEAD
└── QA_ENGINEER

VP_MARKETING
├── GROWTH_MANAGER
└── CONTENT_LEAD

SUPPORT_LEAD
└── SUPPORT_ENGINEER
```

### Capability Inheritance

**VPs inherit all capabilities of their department:**
- VP_PRODUCT can do everything PM/Designer/UX can do
- VP_ENGINEERING can do everything EM/Senior/Engineer/SRE can do
- VP_MARKETING can do everything Growth/Content can do

**Managers inherit all capabilities of their reports:**
- ENGINEERING_MANAGER can do everything SENIOR_ENGINEER and ENGINEER can do
- QA_LEAD can do everything QA_ENGINEER can do
- SUPPORT_LEAD can do everything SUPPORT_ENGINEER can do

**Senior roles inherit capabilities of junior roles:**
- SENIOR_ENGINEER can do everything ENGINEER can do (plus additional architecture/mentorship)

### Override Authority

VPs and managers have **override authority** for decisions within their department:

- **VP_PRODUCT** can override PRODUCT_MANAGER approval decisions
- **VP_ENGINEERING** can override ENGINEERING_MANAGER approval decisions
- **VP_MARKETING** can override GROWTH_MANAGER or CONTENT_LEAD decisions
- **ENGINEERING_MANAGER** can override SENIOR_ENGINEER or ENGINEER decisions
- **QA_LEAD** can override QA_ENGINEER decisions
- **SUPPORT_LEAD** can override SUPPORT_ENGINEER decisions

**Cross-department overrides are not allowed.** VP_ENGINEERING cannot override VP_PRODUCT on feature scope. Conflicts escalate to CEO or designated arbitrator.

---

## Workflow Examples

### Feature Development (Standard)

```
1. PM creates PRD → requires feature_spec gate (PM + EM approve)
2. Designer creates mocks → requires design_mocks gate (PM approves)
3. Engineer implements → no gate, claims task
4. QA tests → no gate, claims task
5. Deploy to production → requires production_deploy gate (EM + QA_LEAD approve)
6. Growth launches → requires public_announcement gate (VP_MARKETING approves)
```

### Trading Strategy Development (Janus)

```
1. PM defines strategy goals → no gate, creates PRD
2. Designer creates config schema → requires strategy_config_schema gate (Designer + EM approve)
3. Engineer implements filter + tests → no gate, claims task
4. QA runs backtest → no gate, claims task
5. QA validates metrics → requires backtest_validation gate (QA_LEAD approves)
6. PM reviews backtest → requires production_trading_deploy gate (PM + QA_LEAD + EM approve)
7. SRE deploys to Telegram bot → gate must be approved before execution
```

**Key difference:** Trading strategies require QA_LEAD approval on backtest results AND PM sign-off on strategy alignment before production deployment.

---

## Workflow Type Definitions

From the roadmap, AgentCoord supports these workflow types:

| Workflow Type | Roles Involved | Description |
|--------------|----------------|-------------|
| **feature** | PM → Designer → Engineer → QA → PM → Growth | Standard feature development |
| **bug** | QA → Engineer → QA | Bug fix and verification |
| **launch** | PM → Growth → Engineer → QA → Support | Product launch coordination |
| **trading_strategy** | PM → Designer → Engineer → QA → PM → SRE | Janus trading strategy (see workflow above) |

---

## Implementation Notes

### Capability Enforcement

```python
class RoleCapabilities:
    """Enforces role-based permissions"""

    PERMISSIONS = {
        Role.PRODUCT_MANAGER: [
            "create_prd",
            "approve_release",
            "prioritize_roadmap",
            "approve_design_mocks",
            "approve_feature_spec",
            "approve_trading_strategy_for_production",
        ],
        Role.ENGINEERING_MANAGER: [
            "assign_tasks",
            "approve_architecture",
            "deploy_staging",
            "review_code",
            "approve_merge",
            "approve_production_deploy",
            "approve_feature_spec",
        ],
        # ... (full mapping for all 15 roles)
    }

    @classmethod
    def can_perform(cls, role: Role, action: str) -> bool:
        """Check if role has permission to perform action"""
        return action in cls.PERMISSIONS.get(role, [])

    @classmethod
    def inherits_from(cls, role: Role) -> list[Role]:
        """Define inheritance relationships"""
        INHERITANCE = {
            Role.VP_PRODUCT: [Role.PRODUCT_MANAGER, Role.PRODUCT_DESIGNER, Role.UX_RESEARCHER],
            Role.VP_ENGINEERING: [Role.ENGINEERING_MANAGER, Role.SENIOR_ENGINEER, Role.ENGINEER, Role.SRE],
            Role.ENGINEERING_MANAGER: [Role.SENIOR_ENGINEER, Role.ENGINEER],
            Role.SENIOR_ENGINEER: [Role.ENGINEER],
            # ... etc
        }
        return INHERITANCE.get(role, [])
```

### Gate Enforcement

```python
class ApprovalGate:
    """Require approval from specific roles before proceeding"""

    GATES = {
        "feature_spec": [Role.PRODUCT_MANAGER, Role.ENGINEERING_MANAGER],
        "design_mocks": [Role.PRODUCT_MANAGER],
        "production_deploy": [Role.ENGINEERING_MANAGER, Role.QA_LEAD],
        "public_announcement": [Role.VP_MARKETING],

        # Janus-specific gates
        "production_trading_deploy": [
            Role.PRODUCT_MANAGER,
            Role.QA_LEAD,
            Role.ENGINEERING_MANAGER
        ],
        "backtest_validation": [Role.QA_LEAD],
        "strategy_config_schema": [Role.PRODUCT_DESIGNER, Role.ENGINEERING_MANAGER],
    }

    def request_approval(self, gate_type: str, context: dict, requestor: Agent):
        """Create approval request for gate"""
        required_approvers = self.GATES[gate_type]

        # VP override: VPs can approve on behalf of their department
        # Example: VP_PRODUCT can approve instead of PRODUCT_MANAGER
        # Example: VP_ENGINEERING can approve instead of ENGINEERING_MANAGER

        approval = ApprovalRequest(
            gate_type=gate_type,
            context=context,
            requestor=requestor,
            required_approvers=required_approvers,
            status="pending"
        )

        return approval
```

---

## Appendix: Full Capability Reference

### Quick Reference by Action Type

**Creation Actions:**
- `create_prd`, `create_design_mocks`, `create_prototypes`, `create_test_plans`, `create_launch_plan`, `create_content`, `create_runbooks`, `create_alerts`, `create_design_system`, `create_personas`, `create_faqs`, `create_marketing_materials`

**Approval Actions:**
- `approve_release`, `approve_roadmap`, `approve_architecture`, `approve_merge`, `approve_production_deploy`, `approve_design_mocks`, `approve_feature_spec`, `approve_trading_strategy_for_production`, `approve_public_announcement`, `approve_backtest_results`, `approve_campaigns`, `approve_support_procedures`

**Implementation Actions:**
- `implement_features`, `implement_filters`, `implement_pricing_logic`, `fix_bugs`, `write_tests`, `write_test_cases`, `write_documentation`

**Review Actions:**
- `review_code`, `review_ux`, `validate_metrics`, `validate_trading_metrics`, `analyze_metrics`, `analyze_user_feedback`

**Deployment Actions:**
- `deploy_staging`, `deploy_production`, `deploy_to_telegram_bot`, `rollback_deploy`

**Testing Actions:**
- `execute_tests`, `run_regression_tests`, `run_backtest`, `verify_fixes`, `reproduce_bugs`, `run_usability_tests`, `run_growth_experiments`

**Communication Actions:**
- `file_bugs`, `escalate_issues`, `answer_tickets`, `launch_features`, `write_release_notes`, `manage_blog`, `manage_campaigns`

**Management Actions:**
- `assign_tasks`, `allocate_product_resources`, `allocate_eng_resources`, `allocate_marketing_budget`, `mentor_engineers`, `prioritize_roadmap`, `prioritize_epics`, `set_technical_standards`, `set_marketing_strategy`, `override_pm_decisions`, `override_em_decisions`

**Monitoring Actions:**
- `monitor_systems`, `manage_infrastructure`

---

## Version History

- **v1.0** (2026-02-20): Initial capabilities matrix based on COMPANY_MODEL_ROADMAP.md
