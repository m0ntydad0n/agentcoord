"""Tests for role-based access control system."""

import pytest
from agentcoord.roles import (
    Role,
    Capability,
    RoleCapabilities,
    CustomRole,
    ApprovalGate,
    PermissionDenied,
)


class TestRole:
    """Test Role enum and role definitions."""

    def test_all_roles_defined(self):
        """All expected roles are defined."""
        expected_roles = {
            # Product
            "vp_product",
            "pm",
            "designer",
            "ux_researcher",
            # Engineering
            "vp_eng",
            "em",
            "senior_eng",
            "engineer",
            "sre",
            # QA
            "qa_lead",
            "qa_eng",
            # Marketing
            "vp_marketing",
            "growth",
            "content",
            # Support
            "support_lead",
            "support_eng",
        }
        actual_roles = {r.value for r in Role}
        assert actual_roles == expected_roles

    def test_role_from_string(self):
        """Role can be parsed from string."""
        assert Role.from_string("pm") == Role.PRODUCT_MANAGER
        assert Role.from_string("engineer") == Role.ENGINEER
        assert Role.from_string("qa_lead") == Role.QA_LEAD

    def test_role_from_string_case_insensitive(self):
        """Role parsing is case-insensitive."""
        assert Role.from_string("PM") == Role.PRODUCT_MANAGER
        assert Role.from_string("Engineer") == Role.ENGINEER

    def test_invalid_role_raises(self):
        """Invalid role string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown role"):
            Role.from_string("invalid_role")

    def test_role_capabilities_property(self):
        """Role.capabilities returns frozenset of capabilities."""
        caps = Role.PRODUCT_MANAGER.capabilities
        assert isinstance(caps, frozenset)
        assert Capability.CREATE_PRD in caps
        assert Capability.APPROVE_RELEASE in caps


class TestCapability:
    """Test Capability constants."""

    def test_capability_constants_defined(self):
        """Key capabilities are defined."""
        # Sample check
        assert hasattr(Capability, "CREATE_PRD")
        assert hasattr(Capability, "IMPLEMENT_FEATURES")
        assert hasattr(Capability, "APPROVE_RELEASE")
        assert hasattr(Capability, "RUN_BACKTEST")

    def test_capability_values_are_strings(self):
        """All capability constants are strings."""
        assert isinstance(Capability.CREATE_PRD, str)
        assert isinstance(Capability.DEPLOY_PRODUCTION, str)


class TestRoleCapabilities:
    """Test role-to-capability mapping."""

    def test_product_manager_capabilities(self):
        """PM has expected capabilities."""
        pm_caps = RoleCapabilities.get_capabilities(Role.PRODUCT_MANAGER)

        assert Capability.CREATE_PRD in pm_caps
        assert Capability.APPROVE_RELEASE in pm_caps
        assert Capability.PRIORITIZE_ROADMAP in pm_caps
        assert Capability.APPROVE_DESIGN_MOCKS in pm_caps
        assert Capability.APPROVE_FEATURE_SPEC in pm_caps
        assert Capability.APPROVE_TRADING_STRATEGY_FOR_PRODUCTION in pm_caps

    def test_engineer_capabilities(self):
        """Engineer has expected capabilities."""
        eng_caps = RoleCapabilities.get_capabilities(Role.ENGINEER)

        assert Capability.IMPLEMENT_FEATURES in eng_caps
        assert Capability.WRITE_TESTS in eng_caps
        assert Capability.REVIEW_CODE in eng_caps
        assert Capability.FIX_BUGS in eng_caps

        # Should NOT have approval powers
        assert Capability.APPROVE_PRODUCTION_DEPLOY not in eng_caps
        assert Capability.APPROVE_MERGE not in eng_caps

    def test_qa_lead_capabilities(self):
        """QA Lead has approval and testing capabilities."""
        qa_caps = RoleCapabilities.get_capabilities(Role.QA_LEAD)

        assert Capability.APPROVE_RELEASE in qa_caps
        assert Capability.APPROVE_PRODUCTION_DEPLOY in qa_caps
        assert Capability.APPROVE_BACKTEST_RESULTS in qa_caps
        assert Capability.VALIDATE_TRADING_METRICS in qa_caps
        assert Capability.RUN_BACKTEST in qa_caps

    def test_sre_capabilities(self):
        """SRE has deployment capabilities."""
        sre_caps = RoleCapabilities.get_capabilities(Role.SRE)

        assert Capability.DEPLOY_STAGING in sre_caps
        assert Capability.DEPLOY_PRODUCTION in sre_caps
        assert Capability.DEPLOY_TO_TELEGRAM_BOT in sre_caps
        assert Capability.MONITOR_SYSTEMS in sre_caps
        assert Capability.ROLLBACK_DEPLOY in sre_caps

    def test_vp_product_inherits_department_capabilities(self):
        """VP Product has all product department capabilities."""
        vp_caps = RoleCapabilities.get_capabilities(Role.VP_PRODUCT)

        # Has PM capabilities
        assert Capability.CREATE_PRD in vp_caps
        assert Capability.APPROVE_RELEASE in vp_caps

        # Has Designer capabilities
        assert Capability.CREATE_DESIGN_MOCKS in vp_caps
        assert Capability.REVIEW_UX in vp_caps

        # Has override powers
        assert Capability.OVERRIDE_PM_DECISIONS in vp_caps

    def test_vp_engineering_inherits_department_capabilities(self):
        """VP Engineering has all engineering capabilities."""
        vp_eng_caps = RoleCapabilities.get_capabilities(Role.VP_ENGINEERING)

        # Has EM capabilities
        assert Capability.ASSIGN_TASKS in vp_eng_caps
        assert Capability.APPROVE_PRODUCTION_DEPLOY in vp_eng_caps

        # Has engineer capabilities
        assert Capability.IMPLEMENT_FEATURES in vp_eng_caps
        assert Capability.WRITE_TESTS in vp_eng_caps

        # Has override powers
        assert Capability.OVERRIDE_EM_DECISIONS in vp_eng_caps

    def test_has_capability_check(self):
        """has_capability correctly checks role permissions."""
        assert RoleCapabilities.has_capability(Role.PRODUCT_MANAGER, Capability.CREATE_PRD)
        assert RoleCapabilities.has_capability(Role.ENGINEER, Capability.IMPLEMENT_FEATURES)
        assert not RoleCapabilities.has_capability(Role.ENGINEER, Capability.APPROVE_RELEASE)

    def test_role_inheritance(self):
        """Role inheritance relationships defined."""
        # VP_PRODUCT inherits from PM, Designer, UX
        vp_prod_inherits = RoleCapabilities.inherits_from(Role.VP_PRODUCT)
        assert Role.PRODUCT_MANAGER in vp_prod_inherits
        assert Role.PRODUCT_DESIGNER in vp_prod_inherits
        assert Role.UX_RESEARCHER in vp_prod_inherits

        # EM inherits from Senior Eng and Eng
        em_inherits = RoleCapabilities.inherits_from(Role.ENGINEERING_MANAGER)
        assert Role.SENIOR_ENGINEER in em_inherits
        assert Role.ENGINEER in em_inherits

        # Senior Eng inherits from Eng
        senior_inherits = RoleCapabilities.inherits_from(Role.SENIOR_ENGINEER)
        assert Role.ENGINEER in senior_inherits

    def test_can_override_decisions(self):
        """Override authority is correctly defined."""
        # VP_PRODUCT can override PM
        assert RoleCapabilities.can_override(Role.VP_PRODUCT, Role.PRODUCT_MANAGER)
        assert RoleCapabilities.can_override(Role.VP_PRODUCT, Role.PRODUCT_DESIGNER)

        # VP_ENGINEERING can override EM
        assert RoleCapabilities.can_override(Role.VP_ENGINEERING, Role.ENGINEERING_MANAGER)
        assert RoleCapabilities.can_override(Role.VP_ENGINEERING, Role.ENGINEER)

        # EM can override engineers
        assert RoleCapabilities.can_override(Role.ENGINEERING_MANAGER, Role.SENIOR_ENGINEER)
        assert RoleCapabilities.can_override(Role.ENGINEERING_MANAGER, Role.ENGINEER)

        # Cross-department overrides not allowed
        assert not RoleCapabilities.can_override(Role.VP_ENGINEERING, Role.PRODUCT_MANAGER)
        assert not RoleCapabilities.can_override(Role.VP_PRODUCT, Role.ENGINEERING_MANAGER)

        # Peers cannot override each other
        assert not RoleCapabilities.can_override(Role.ENGINEER, Role.ENGINEER)
        assert not RoleCapabilities.can_override(Role.PRODUCT_MANAGER, Role.PRODUCT_DESIGNER)


class TestCustomRole:
    """Test custom role creation."""

    def test_custom_role_creation(self):
        """Custom roles can be created."""
        analyst = CustomRole(
            name="ANALYST", capabilities=frozenset(["read_metrics", "create_reports"])
        )

        assert analyst.name == "ANALYST"
        assert "read_metrics" in analyst.capabilities
        assert "create_reports" in analyst.capabilities

    def test_custom_role_has_capability(self):
        """Custom roles can check capabilities."""
        analyst = CustomRole(
            name="ANALYST", capabilities=frozenset(["read_metrics", "create_reports"])
        )

        assert analyst.has_capability("read_metrics")
        assert analyst.has_capability("create_reports")
        assert not analyst.has_capability("deploy_production")

    def test_custom_role_immutable(self):
        """Custom roles are immutable."""
        analyst = CustomRole(
            name="ANALYST", capabilities=frozenset(["read_metrics"])
        )

        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.10+
            analyst.name = "NEW_NAME"


class TestApprovalGate:
    """Test approval gate configuration."""

    def test_standard_gates_defined(self):
        """Standard approval gates are defined."""
        assert ApprovalGate.FEATURE_SPEC == "feature_spec"
        assert ApprovalGate.DESIGN_MOCKS == "design_mocks"
        assert ApprovalGate.PRODUCTION_DEPLOY == "production_deploy"
        assert ApprovalGate.PUBLIC_ANNOUNCEMENT == "public_announcement"

    def test_janus_gates_defined(self):
        """Janus-specific gates are defined."""
        assert ApprovalGate.PRODUCTION_TRADING_DEPLOY == "production_trading_deploy"
        assert ApprovalGate.BACKTEST_VALIDATION == "backtest_validation"
        assert ApprovalGate.STRATEGY_CONFIG_SCHEMA == "strategy_config_schema"

    def test_feature_spec_gate(self):
        """Feature spec gate requires PM + EM."""
        required = ApprovalGate.get_required_approvers(ApprovalGate.FEATURE_SPEC)

        assert Role.PRODUCT_MANAGER in required
        assert Role.ENGINEERING_MANAGER in required
        assert len(required) == 2

    def test_production_deploy_gate(self):
        """Production deploy gate requires EM + QA Lead."""
        required = ApprovalGate.get_required_approvers(ApprovalGate.PRODUCTION_DEPLOY)

        assert Role.ENGINEERING_MANAGER in required
        assert Role.QA_LEAD in required
        assert len(required) == 2

    def test_production_trading_deploy_gate(self):
        """Trading deploy gate requires PM + QA Lead + EM."""
        required = ApprovalGate.get_required_approvers(
            ApprovalGate.PRODUCTION_TRADING_DEPLOY
        )

        assert Role.PRODUCT_MANAGER in required
        assert Role.QA_LEAD in required
        assert Role.ENGINEERING_MANAGER in required
        assert len(required) == 3

    def test_backtest_validation_gate(self):
        """Backtest validation requires QA Lead only."""
        required = ApprovalGate.get_required_approvers(ApprovalGate.BACKTEST_VALIDATION)

        assert Role.QA_LEAD in required
        assert len(required) == 1

    def test_can_approve_gate(self):
        """can_approve checks role authorization."""
        # PM can approve feature spec
        assert ApprovalGate.can_approve(ApprovalGate.FEATURE_SPEC, Role.PRODUCT_MANAGER)
        assert ApprovalGate.can_approve(ApprovalGate.FEATURE_SPEC, Role.ENGINEERING_MANAGER)

        # Engineer cannot approve feature spec
        assert not ApprovalGate.can_approve(ApprovalGate.FEATURE_SPEC, Role.ENGINEER)

        # QA Lead can approve production deploy
        assert ApprovalGate.can_approve(ApprovalGate.PRODUCTION_DEPLOY, Role.QA_LEAD)

        # VP Marketing can approve public announcement
        assert ApprovalGate.can_approve(
            ApprovalGate.PUBLIC_ANNOUNCEMENT, Role.VP_MARKETING
        )

    def test_invalid_gate_type(self):
        """Invalid gate type returns empty set."""
        required = ApprovalGate.get_required_approvers("invalid_gate")
        assert required == set()


class TestPermissionDenied:
    """Test PermissionDenied exception."""

    def test_exception_can_be_raised(self):
        """PermissionDenied is a valid exception."""
        with pytest.raises(PermissionDenied):
            raise PermissionDenied("Test permission denied")

    def test_exception_message(self):
        """Exception message is preserved."""
        try:
            raise PermissionDenied("Agent lacks capability: deploy_production")
        except PermissionDenied as e:
            assert "deploy_production" in str(e)


class TestJanusWorkflow:
    """Integration test for Janus trading strategy workflow."""

    def test_janus_roles_have_trading_capabilities(self):
        """Janus-relevant roles have trading-specific capabilities."""
        # PM can approve trading strategies
        pm_caps = RoleCapabilities.get_capabilities(Role.PRODUCT_MANAGER)
        assert Capability.APPROVE_TRADING_STRATEGY_FOR_PRODUCTION in pm_caps

        # Designer can design config schemas
        designer_caps = RoleCapabilities.get_capabilities(Role.PRODUCT_DESIGNER)
        assert Capability.DESIGN_CONFIG_SCHEMA in designer_caps

        # Engineer can implement filters
        eng_caps = RoleCapabilities.get_capabilities(Role.ENGINEER)
        assert Capability.IMPLEMENT_FILTERS in eng_caps
        assert Capability.IMPLEMENT_PRICING_LOGIC in eng_caps

        # QA can run backtests and validate metrics
        qa_caps = RoleCapabilities.get_capabilities(Role.QA_ENGINEER)
        assert Capability.RUN_BACKTEST in qa_caps
        assert Capability.VALIDATE_METRICS in qa_caps

        # QA Lead can approve backtest results
        qa_lead_caps = RoleCapabilities.get_capabilities(Role.QA_LEAD)
        assert Capability.APPROVE_BACKTEST_RESULTS in qa_lead_caps
        assert Capability.VALIDATE_TRADING_METRICS in qa_lead_caps

        # SRE can deploy to Telegram bot
        sre_caps = RoleCapabilities.get_capabilities(Role.SRE)
        assert Capability.DEPLOY_TO_TELEGRAM_BOT in sre_caps

    def test_janus_approval_gates(self):
        """Janus workflow has correct approval gates."""
        # Strategy config schema requires Designer + EM
        schema_gate = ApprovalGate.get_required_approvers(
            ApprovalGate.STRATEGY_CONFIG_SCHEMA
        )
        assert Role.PRODUCT_DESIGNER in schema_gate
        assert Role.ENGINEERING_MANAGER in schema_gate

        # Backtest validation requires QA Lead
        backtest_gate = ApprovalGate.get_required_approvers(
            ApprovalGate.BACKTEST_VALIDATION
        )
        assert Role.QA_LEAD in backtest_gate

        # Production trading deploy requires PM + QA Lead + EM
        deploy_gate = ApprovalGate.get_required_approvers(
            ApprovalGate.PRODUCTION_TRADING_DEPLOY
        )
        assert Role.PRODUCT_MANAGER in deploy_gate
        assert Role.QA_LEAD in deploy_gate
        assert Role.ENGINEERING_MANAGER in deploy_gate
