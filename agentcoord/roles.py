"""Role-based access control (RBAC) for AgentCoord.

This module defines roles, capabilities, and permission checking for multi-department
company coordination.
"""

from enum import Enum
from typing import FrozenSet, Set, Dict, Optional
from dataclasses import dataclass


class Role(str, Enum):
    """Agent roles across all company departments."""

    # Product Department
    VP_PRODUCT = "vp_product"
    PRODUCT_MANAGER = "pm"
    PRODUCT_DESIGNER = "designer"
    UX_RESEARCHER = "ux_researcher"

    # Engineering Department
    VP_ENGINEERING = "vp_eng"
    ENGINEERING_MANAGER = "em"
    SENIOR_ENGINEER = "senior_eng"
    ENGINEER = "engineer"
    SRE = "sre"

    # QA Department
    QA_LEAD = "qa_lead"
    QA_ENGINEER = "qa_eng"

    # Marketing Department
    VP_MARKETING = "vp_marketing"
    GROWTH_MANAGER = "growth"
    CONTENT_LEAD = "content"

    # Support Department
    SUPPORT_LEAD = "support_lead"
    SUPPORT_ENGINEER = "support_eng"

    @property
    def capabilities(self) -> FrozenSet[str]:
        """Get capabilities for this role."""
        return RoleCapabilities.get_capabilities(self)

    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """Parse role from string, case-insensitive."""
        try:
            return cls(role_str.lower())
        except ValueError:
            raise ValueError(
                f"Unknown role: {role_str}. Available roles: {[r.value for r in cls]}"
            )


class Capability:
    """Capability constants for permission checking."""

    # Product capabilities
    CREATE_PRD = "create_prd"
    APPROVE_RELEASE = "approve_release"
    APPROVE_ROADMAP = "approve_roadmap"
    PRIORITIZE_ROADMAP = "prioritize_roadmap"
    PRIORITIZE_EPICS = "prioritize_epics"
    APPROVE_DESIGN_MOCKS = "approve_design_mocks"
    APPROVE_FEATURE_SPEC = "approve_feature_spec"
    DEFINE_ACCEPTANCE_CRITERIA = "define_acceptance_criteria"
    REQUEST_DESIGN = "request_design"
    REQUEST_ENGINEERING = "request_engineering"
    APPROVE_TRADING_STRATEGY_FOR_PRODUCTION = "approve_trading_strategy_for_production"
    CREATE_DESIGN_MOCKS = "create_design_mocks"
    CREATE_PROTOTYPES = "create_prototypes"
    CREATE_DESIGN_SYSTEM = "create_design_system"
    REVIEW_UX = "review_ux"
    DESIGN_CONFIG_SCHEMA = "design_config_schema"
    CONDUCT_USER_RESEARCH = "conduct_user_research"
    ANALYZE_USER_FEEDBACK = "analyze_user_feedback"
    CREATE_PERSONAS = "create_personas"
    RUN_USABILITY_TESTS = "run_usability_tests"

    # Engineering capabilities
    APPROVE_ARCHITECTURE = "approve_architecture"
    APPROVE_PRODUCTION_DEPLOY = "approve_production_deploy"
    ASSIGN_TASKS = "assign_tasks"
    DEPLOY_STAGING = "deploy_staging"
    DEPLOY_PRODUCTION = "deploy_production"
    REVIEW_CODE = "review_code"
    APPROVE_MERGE = "approve_merge"
    IMPLEMENT_FEATURES = "implement_features"
    IMPLEMENT_FILTERS = "implement_filters"
    IMPLEMENT_PRICING_LOGIC = "implement_pricing_logic"
    WRITE_TESTS = "write_tests"
    FIX_BUGS = "fix_bugs"
    WRITE_DOCUMENTATION = "write_documentation"
    DESIGN_ARCHITECTURE = "design_architecture"
    MENTOR_ENGINEERS = "mentor_engineers"
    MONITOR_SYSTEMS = "monitor_systems"
    CREATE_ALERTS = "create_alerts"
    MANAGE_INFRASTRUCTURE = "manage_infrastructure"
    ROLLBACK_DEPLOY = "rollback_deploy"
    DEPLOY_TO_TELEGRAM_BOT = "deploy_to_telegram_bot"

    # QA capabilities
    FILE_BUGS = "file_bugs"
    CREATE_TEST_PLANS = "create_test_plans"
    DESIGN_TEST_STRATEGY = "design_test_strategy"
    APPROVE_BACKTEST_RESULTS = "approve_backtest_results"
    VALIDATE_TRADING_METRICS = "validate_trading_metrics"
    WRITE_TEST_CASES = "write_test_cases"
    EXECUTE_TESTS = "execute_tests"
    VERIFY_FIXES = "verify_fixes"
    RUN_REGRESSION_TESTS = "run_regression_tests"
    REPRODUCE_BUGS = "reproduce_bugs"
    RUN_BACKTEST = "run_backtest"
    VALIDATE_METRICS = "validate_metrics"

    # Marketing capabilities
    APPROVE_PUBLIC_ANNOUNCEMENT = "approve_public_announcement"
    CREATE_LAUNCH_PLAN = "create_launch_plan"
    RUN_GROWTH_EXPERIMENTS = "run_growth_experiments"
    ANALYZE_METRICS = "analyze_metrics"
    MANAGE_CAMPAIGNS = "manage_campaigns"
    CREATE_CONTENT = "create_content"
    LAUNCH_FEATURES = "launch_features"
    MANAGE_BLOG = "manage_blog"
    CREATE_MARKETING_MATERIALS = "create_marketing_materials"
    WRITE_RELEASE_NOTES = "write_release_notes"

    # Support capabilities
    PREPARE_DOCS = "prepare_docs"
    CREATE_RUNBOOKS = "create_runbooks"
    ESCALATE_ISSUES = "escalate_issues"
    APPROVE_SUPPORT_PROCEDURES = "approve_support_procedures"
    ANSWER_TICKETS = "answer_tickets"
    CREATE_FAQS = "create_faqs"

    # Management capabilities
    OVERRIDE_PM_DECISIONS = "override_pm_decisions"
    OVERRIDE_EM_DECISIONS = "override_em_decisions"
    ALLOCATE_PRODUCT_RESOURCES = "allocate_product_resources"
    ALLOCATE_ENG_RESOURCES = "allocate_eng_resources"
    ALLOCATE_MARKETING_BUDGET = "allocate_marketing_budget"
    SET_TECHNICAL_STANDARDS = "set_technical_standards"
    SET_MARKETING_STRATEGY = "set_marketing_strategy"
    APPROVE_CAMPAIGNS = "approve_campaigns"


class RoleCapabilities:
    """Maps roles to their capabilities and provides permission checking."""

    PERMISSIONS: Dict[Role, FrozenSet[str]] = {
        # Product Department
        Role.VP_PRODUCT: frozenset([
            Capability.APPROVE_ROADMAP,
            Capability.PRIORITIZE_EPICS,
            Capability.OVERRIDE_PM_DECISIONS,
            Capability.ALLOCATE_PRODUCT_RESOURCES,
            Capability.APPROVE_PUBLIC_ANNOUNCEMENT,
            Capability.CREATE_PRD,
            Capability.APPROVE_RELEASE,
            Capability.PRIORITIZE_ROADMAP,
            Capability.APPROVE_DESIGN_MOCKS,
            Capability.APPROVE_FEATURE_SPEC,
            Capability.APPROVE_TRADING_STRATEGY_FOR_PRODUCTION,
            Capability.CREATE_DESIGN_MOCKS,
            Capability.CREATE_PROTOTYPES,
            Capability.REVIEW_UX,
            Capability.CONDUCT_USER_RESEARCH,
        ]),
        Role.PRODUCT_MANAGER: frozenset([
            Capability.CREATE_PRD,
            Capability.APPROVE_RELEASE,
            Capability.PRIORITIZE_ROADMAP,
            Capability.APPROVE_DESIGN_MOCKS,
            Capability.APPROVE_FEATURE_SPEC,
            Capability.DEFINE_ACCEPTANCE_CRITERIA,
            Capability.REQUEST_DESIGN,
            Capability.REQUEST_ENGINEERING,
            Capability.APPROVE_TRADING_STRATEGY_FOR_PRODUCTION,
        ]),
        Role.PRODUCT_DESIGNER: frozenset([
            Capability.CREATE_DESIGN_MOCKS,
            Capability.CREATE_PROTOTYPES,
            Capability.CREATE_DESIGN_SYSTEM,
            Capability.REVIEW_UX,
            Capability.DESIGN_CONFIG_SCHEMA,
        ]),
        Role.UX_RESEARCHER: frozenset([
            Capability.CONDUCT_USER_RESEARCH,
            Capability.ANALYZE_USER_FEEDBACK,
            Capability.CREATE_PERSONAS,
            Capability.RUN_USABILITY_TESTS,
        ]),
        # Engineering Department
        Role.VP_ENGINEERING: frozenset([
            Capability.APPROVE_ARCHITECTURE,
            Capability.ALLOCATE_ENG_RESOURCES,
            Capability.APPROVE_PRODUCTION_DEPLOY,
            Capability.OVERRIDE_EM_DECISIONS,
            Capability.SET_TECHNICAL_STANDARDS,
            Capability.ASSIGN_TASKS,
            Capability.DEPLOY_STAGING,
            Capability.REVIEW_CODE,
            Capability.APPROVE_MERGE,
            Capability.IMPLEMENT_FEATURES,
            Capability.WRITE_TESTS,
            Capability.DESIGN_ARCHITECTURE,
            Capability.DEPLOY_PRODUCTION,
        ]),
        Role.ENGINEERING_MANAGER: frozenset([
            Capability.ASSIGN_TASKS,
            Capability.APPROVE_ARCHITECTURE,
            Capability.DEPLOY_STAGING,
            Capability.REVIEW_CODE,
            Capability.APPROVE_MERGE,
            Capability.APPROVE_PRODUCTION_DEPLOY,
            Capability.APPROVE_FEATURE_SPEC,
            Capability.IMPLEMENT_FEATURES,
            Capability.WRITE_TESTS,
            Capability.DESIGN_ARCHITECTURE,
            Capability.MENTOR_ENGINEERS,
        ]),
        Role.SENIOR_ENGINEER: frozenset([
            Capability.IMPLEMENT_FEATURES,
            Capability.WRITE_TESTS,
            Capability.REVIEW_CODE,
            Capability.APPROVE_MERGE,
            Capability.DESIGN_ARCHITECTURE,
            Capability.MENTOR_ENGINEERS,
            Capability.DEPLOY_STAGING,
            Capability.IMPLEMENT_FILTERS,
            Capability.IMPLEMENT_PRICING_LOGIC,
            Capability.FIX_BUGS,
            Capability.WRITE_DOCUMENTATION,
        ]),
        Role.ENGINEER: frozenset([
            Capability.IMPLEMENT_FEATURES,
            Capability.WRITE_TESTS,
            Capability.REVIEW_CODE,
            Capability.FIX_BUGS,
            Capability.WRITE_DOCUMENTATION,
            Capability.IMPLEMENT_FILTERS,
            Capability.IMPLEMENT_PRICING_LOGIC,
        ]),
        Role.SRE: frozenset([
            Capability.DEPLOY_STAGING,
            Capability.DEPLOY_PRODUCTION,
            Capability.MONITOR_SYSTEMS,
            Capability.CREATE_ALERTS,
            Capability.MANAGE_INFRASTRUCTURE,
            Capability.ROLLBACK_DEPLOY,
            Capability.DEPLOY_TO_TELEGRAM_BOT,
        ]),
        # QA Department
        Role.QA_LEAD: frozenset([
            Capability.APPROVE_RELEASE,
            Capability.FILE_BUGS,
            Capability.CREATE_TEST_PLANS,
            Capability.APPROVE_PRODUCTION_DEPLOY,
            Capability.DESIGN_TEST_STRATEGY,
            Capability.APPROVE_BACKTEST_RESULTS,
            Capability.VALIDATE_TRADING_METRICS,
            Capability.WRITE_TEST_CASES,
            Capability.EXECUTE_TESTS,
            Capability.VERIFY_FIXES,
            Capability.RUN_REGRESSION_TESTS,
            Capability.REPRODUCE_BUGS,
            Capability.RUN_BACKTEST,
            Capability.VALIDATE_METRICS,
        ]),
        Role.QA_ENGINEER: frozenset([
            Capability.FILE_BUGS,
            Capability.WRITE_TEST_CASES,
            Capability.EXECUTE_TESTS,
            Capability.VERIFY_FIXES,
            Capability.RUN_REGRESSION_TESTS,
            Capability.REPRODUCE_BUGS,
            Capability.RUN_BACKTEST,
            Capability.VALIDATE_METRICS,
        ]),
        # Marketing Department
        Role.VP_MARKETING: frozenset([
            Capability.APPROVE_PUBLIC_ANNOUNCEMENT,
            Capability.ALLOCATE_MARKETING_BUDGET,
            Capability.APPROVE_CAMPAIGNS,
            Capability.SET_MARKETING_STRATEGY,
            Capability.CREATE_LAUNCH_PLAN,
            Capability.RUN_GROWTH_EXPERIMENTS,
            Capability.ANALYZE_METRICS,
            Capability.MANAGE_CAMPAIGNS,
            Capability.CREATE_CONTENT,
        ]),
        Role.GROWTH_MANAGER: frozenset([
            Capability.CREATE_LAUNCH_PLAN,
            Capability.RUN_GROWTH_EXPERIMENTS,
            Capability.ANALYZE_METRICS,
            Capability.MANAGE_CAMPAIGNS,
            Capability.CREATE_CONTENT,
            Capability.LAUNCH_FEATURES,
        ]),
        Role.CONTENT_LEAD: frozenset([
            Capability.CREATE_CONTENT,
            Capability.WRITE_DOCUMENTATION,
            Capability.MANAGE_BLOG,
            Capability.CREATE_MARKETING_MATERIALS,
            Capability.WRITE_RELEASE_NOTES,
        ]),
        # Support Department
        Role.SUPPORT_LEAD: frozenset([
            Capability.PREPARE_DOCS,
            Capability.CREATE_RUNBOOKS,
            Capability.ESCALATE_ISSUES,
            Capability.FILE_BUGS,
            Capability.APPROVE_SUPPORT_PROCEDURES,
            Capability.ANSWER_TICKETS,
            Capability.CREATE_FAQS,
            Capability.WRITE_DOCUMENTATION,
            Capability.REPRODUCE_BUGS,
        ]),
        Role.SUPPORT_ENGINEER: frozenset([
            Capability.ANSWER_TICKETS,
            Capability.CREATE_FAQS,
            Capability.REPRODUCE_BUGS,
            Capability.WRITE_DOCUMENTATION,
            Capability.ESCALATE_ISSUES,
        ]),
    }

    @classmethod
    def get_capabilities(cls, role: Role) -> FrozenSet[str]:
        """Get all capabilities for a role."""
        return cls.PERMISSIONS.get(role, frozenset())

    @classmethod
    def has_capability(cls, role: Role, capability: str) -> bool:
        """Check if role has a specific capability."""
        return capability in cls.PERMISSIONS.get(role, frozenset())

    @classmethod
    def inherits_from(cls, role: Role) -> Set[Role]:
        """Get roles this role inherits capabilities from."""
        INHERITANCE = {
            Role.VP_PRODUCT: {
                Role.PRODUCT_MANAGER,
                Role.PRODUCT_DESIGNER,
                Role.UX_RESEARCHER,
            },
            Role.VP_ENGINEERING: {
                Role.ENGINEERING_MANAGER,
                Role.SENIOR_ENGINEER,
                Role.ENGINEER,
                Role.SRE,
            },
            Role.ENGINEERING_MANAGER: {Role.SENIOR_ENGINEER, Role.ENGINEER},
            Role.SENIOR_ENGINEER: {Role.ENGINEER},
            Role.VP_MARKETING: {Role.GROWTH_MANAGER, Role.CONTENT_LEAD},
            Role.QA_LEAD: {Role.QA_ENGINEER},
            Role.SUPPORT_LEAD: {Role.SUPPORT_ENGINEER},
        }
        return INHERITANCE.get(role, set())

    @classmethod
    def can_override(cls, role: Role, target_role: Role) -> bool:
        """Check if role can override decisions by target_role."""
        # VPs can override their department
        overrides = {
            Role.VP_PRODUCT: {Role.PRODUCT_MANAGER, Role.PRODUCT_DESIGNER, Role.UX_RESEARCHER},
            Role.VP_ENGINEERING: {Role.ENGINEERING_MANAGER, Role.SENIOR_ENGINEER, Role.ENGINEER, Role.SRE},
            Role.VP_MARKETING: {Role.GROWTH_MANAGER, Role.CONTENT_LEAD},
            Role.ENGINEERING_MANAGER: {Role.SENIOR_ENGINEER, Role.ENGINEER},
            Role.QA_LEAD: {Role.QA_ENGINEER},
            Role.SUPPORT_LEAD: {Role.SUPPORT_ENGINEER},
        }
        return target_role in overrides.get(role, set())


@dataclass(frozen=True)
class CustomRole:
    """Custom role with user-defined capabilities."""

    name: str
    capabilities: FrozenSet[str]

    def __str__(self) -> str:
        return self.name

    def has_capability(self, capability: str) -> bool:
        """Check if role has a specific capability."""
        return capability in self.capabilities


class ApprovalGate:
    """Approval gate configuration."""

    # Standard approval gates
    FEATURE_SPEC = "feature_spec"
    DESIGN_MOCKS = "design_mocks"
    PRODUCTION_DEPLOY = "production_deploy"
    PUBLIC_ANNOUNCEMENT = "public_announcement"

    # Janus-specific gates
    PRODUCTION_TRADING_DEPLOY = "production_trading_deploy"
    BACKTEST_VALIDATION = "backtest_validation"
    STRATEGY_CONFIG_SCHEMA = "strategy_config_schema"

    GATES: Dict[str, Set[Role]] = {
        FEATURE_SPEC: {Role.PRODUCT_MANAGER, Role.ENGINEERING_MANAGER},
        DESIGN_MOCKS: {Role.PRODUCT_MANAGER},
        PRODUCTION_DEPLOY: {Role.ENGINEERING_MANAGER, Role.QA_LEAD},
        PUBLIC_ANNOUNCEMENT: {Role.VP_MARKETING},
        # Janus-specific
        PRODUCTION_TRADING_DEPLOY: {
            Role.PRODUCT_MANAGER,
            Role.QA_LEAD,
            Role.ENGINEERING_MANAGER,
        },
        BACKTEST_VALIDATION: {Role.QA_LEAD},
        STRATEGY_CONFIG_SCHEMA: {Role.PRODUCT_DESIGNER, Role.ENGINEERING_MANAGER},
    }

    @classmethod
    def get_required_approvers(cls, gate_type: str) -> Set[Role]:
        """Get roles required to approve a gate."""
        return cls.GATES.get(gate_type, set())

    @classmethod
    def can_approve(cls, gate_type: str, role: Role) -> bool:
        """Check if role can approve this gate type."""
        required = cls.GATES.get(gate_type, set())
        return role in required


class PermissionDenied(Exception):
    """Raised when agent lacks required permission."""
    pass
