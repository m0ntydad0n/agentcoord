# Workflow Definitions

This document defines all supported workflow types in AgentCoord, their role sequences, dependencies, and approval gates.

Each workflow represents a real-world cross-functional coordination pattern used in software companies.

---

## Workflow Types

### 1. `feature` - Standard Feature Development

**Description:** Full product development cycle from PRD to production launch.

**Participants:**
- Product Manager (PM)
- Product Designer
- Engineering Manager (EM)
- Engineer
- QA Engineer
- Growth Manager

**Sequence:**

```yaml
feature:
  stages:
    - stage: 1_define
      role: PRODUCT_MANAGER
      action: write_prd
      output: Product Requirements Document (PRD)
      deliverables:
        - Problem statement and user impact
        - Acceptance criteria (testable, specific)
        - Success metrics (quantitative)
        - Dependencies and constraints
      approval_gate: design_kickoff
      approvers: [ENGINEERING_MANAGER]

    - stage: 2_design
      role: PRODUCT_DESIGNER
      action: create_mocks
      output: Design artifacts (wireframes, mockups, prototypes)
      deliverables:
        - UI/UX mockups
        - User flows
        - Design system components
        - Accessibility considerations
      depends_on: [1_define]
      approval_gate: design_review
      approvers: [PRODUCT_MANAGER]

    - stage: 3_implement
      role: ENGINEER
      action: implement
      output: Working code with tests
      deliverables:
        - Feature implementation
        - Unit tests (>90% coverage for new code)
        - Integration tests
        - Documentation updates
      depends_on: [2_design]
      approval_gate: code_review
      approvers: [ENGINEERING_MANAGER]

    - stage: 4_qa
      role: QA_ENGINEER
      action: test
      output: Test report and sign-off
      deliverables:
        - Test plan execution results
        - Regression test results
        - Performance validation
        - Bug reports (if any)
      depends_on: [3_implement]
      approval_gate: qa_signoff
      approvers: [QA_LEAD]

    - stage: 5_release_approval
      role: PRODUCT_MANAGER
      action: approve_release
      output: Release decision
      deliverables:
        - Go/no-go decision
        - Release notes draft
        - Rollback plan
      depends_on: [4_qa]
      approval_gate: production_release
      approvers: [VP_PRODUCT, ENGINEERING_MANAGER]

    - stage: 6_launch
      role: GROWTH_MANAGER
      action: launch
      output: Launch execution
      deliverables:
        - Marketing content
        - User documentation
        - Support team briefing
        - Analytics tracking setup
      depends_on: [5_release_approval]

workflow_metadata:
  typical_duration: "2-4 weeks"
  success_criteria:
    - All acceptance criteria met
    - All tests passing
    - No critical bugs in QA
    - Stakeholder approval obtained
```

---

### 2. `bug` - Bug Fix Workflow

**Description:** Rapid bug diagnosis, fix, and verification cycle.

**Participants:**
- QA Engineer
- Engineer
- Engineering Manager

**Sequence:**

```yaml
bug:
  stages:
    - stage: 1_reproduce
      role: QA_ENGINEER
      action: reproduce
      output: Reproduction steps and test case
      deliverables:
        - Minimal reproduction case
        - Expected vs. actual behavior
        - Environment details
        - Severity assessment
      approval_gate: triage
      approvers: [ENGINEERING_MANAGER]

    - stage: 2_fix
      role: ENGINEER
      action: fix
      output: Bug fix with regression test
      deliverables:
        - Code fix (minimal diff)
        - Regression test (fails before fix, passes after)
        - Root cause analysis
        - Related code review
      depends_on: [1_reproduce]
      approval_gate: code_review
      approvers: [ENGINEERING_MANAGER]

    - stage: 3_verify
      role: QA_ENGINEER
      action: verify
      output: Verification report
      deliverables:
        - Bug no longer reproduces
        - Regression tests pass
        - No new issues introduced
        - Deployment readiness
      depends_on: [2_fix]
      approval_gate: qa_verification
      approvers: [QA_LEAD]

workflow_metadata:
  typical_duration: "1-3 days"
  priority_levels:
    critical: "immediate, all hands"
    high: "same day fix target"
    medium: "next sprint"
    low: "backlog"
  success_criteria:
    - Bug no longer reproduces
    - Regression test prevents recurrence
    - No new bugs introduced
```

---

### 3. `launch` - Product Launch Coordination

**Description:** Cross-functional coordination for major product releases or announcements.

**Participants:**
- Product Manager
- Growth Manager
- Engineer
- QA Engineer
- Support Lead

**Sequence:**

```yaml
launch:
  stages:
    - stage: 1_plan
      role: PRODUCT_MANAGER
      action: create_plan
      output: Launch plan document
      deliverables:
        - Launch timeline
        - Success metrics
        - Risk mitigation plan
        - Rollback strategy
      approval_gate: launch_kickoff
      approvers: [VP_PRODUCT, VP_MARKETING]

    - stage: 2_content
      role: GROWTH_MANAGER
      action: create_content
      output: Marketing assets
      deliverables:
        - Announcement blog post
        - Social media content
        - Email campaigns
        - Press materials (if applicable)
      depends_on: [1_plan]
      approval_gate: content_review
      approvers: [VP_MARKETING, PRODUCT_MANAGER]

    - stage: 3_feature_flag
      role: ENGINEER
      action: feature_flag
      output: Deployment configuration
      deliverables:
        - Feature flag implementation
        - Gradual rollout plan
        - Monitoring dashboards
        - Kill switch ready
      depends_on: [1_plan]
      approval_gate: deployment_review
      approvers: [ENGINEERING_MANAGER, SRE]

    - stage: 4_regression_test
      role: QA_ENGINEER
      action: regression_test
      output: Full system validation
      deliverables:
        - Full regression suite execution
        - Performance benchmarks
        - Load testing results
        - Smoke test checklist
      depends_on: [3_feature_flag]
      approval_gate: launch_readiness
      approvers: [QA_LEAD, ENGINEERING_MANAGER]

    - stage: 5_support_docs
      role: SUPPORT_LEAD
      action: prepare_docs
      output: Support materials
      deliverables:
        - User documentation
        - Support team training
        - FAQ document
        - Known issues list
      depends_on: [1_plan, 2_content]
      approval_gate: support_readiness
      approvers: [PRODUCT_MANAGER]

    - stage: 6_go_live
      role: PRODUCT_MANAGER
      action: execute_launch
      output: Launch execution
      deliverables:
        - Feature enabled in production
        - Marketing content published
        - Support team activated
        - Monitoring active
      depends_on: [2_content, 4_regression_test, 5_support_docs]
      approval_gate: launch_authorization
      approvers: [VP_PRODUCT, VP_ENGINEERING]

workflow_metadata:
  typical_duration: "2-6 weeks"
  success_criteria:
    - All stakeholders aligned
    - Rollback plan tested
    - Support team ready
    - Monitoring and alerts configured
    - Launch metrics defined and tracked
```

---

### 4. `trading_strategy` - Janus Trading Strategy Development

**Description:** Specialized workflow for implementing new trading filters or strategies in the Janus options trading engine.

**Context:** Validated against real Janus codebase at `/Users/johnmonty/Desktop/Janus_Engine/janus`.

**Participants:**
- Product Manager (Strategy PM)
- Product Designer (Config Designer)
- Senior Engineer (Filters/Backend)
- QA Engineer (Backtest Engineer)
- Engineering Manager
- SRE (Infrastructure/Deployment)

**Sequence:**

```yaml
trading_strategy:
  stages:
    - stage: 1_define_strategy
      role: PRODUCT_MANAGER
      action: define_strategy_goals
      output: Strategy PRD
      deliverables:
        - Trading hypothesis and rationale
        - Entry/exit rules specification
        - Risk parameters and constraints
        - Acceptance criteria (backtestable)
        - Success metrics (Sharpe, win rate, drawdown)
      approval_gate: strategy_concept
      approvers: [VP_PRODUCT]
      notes: |
        - Must define quantifiable entry/exit conditions
        - Must specify risk constraints (max position size, stop loss, etc.)
        - Must include backtest validation criteria

    - stage: 2_design_config
      role: PRODUCT_DESIGNER
      action: design_config_schema
      output: Configuration schema (YAML)
      deliverables:
        - Parameter schema with types and ranges
        - Default values (conservative)
        - Config validation rules
        - Parameter interdependencies
      depends_on: [1_define_strategy]
      approval_gate: schema_review
      approvers: [PRODUCT_MANAGER, ENGINEERING_MANAGER]
      notes: |
        - Janus uses config.json for strategy parameters
        - All parameters must be deterministic (no runtime randomness)
        - Must integrate with existing EngineConfig structure

    - stage: 3_implement_filter
      role: SENIOR_ENGINEER
      action: implement_filter
      output: Filter implementation in brain/core.py
      deliverables:
        - Filter logic in brain pipeline (stages 4-5)
        - Integration with existing brain stages
        - Deterministic computation (uses DeterministicClock)
        - No external I/O (pure function)
      depends_on: [2_design_config]
      approval_gate: code_review
      approvers: [ENGINEERING_MANAGER]
      notes: |
        - Implementation location: janus/brain/core.py
        - Must follow 12-stage brain pipeline architecture
        - Quality filters go in Stage 4 (apply_quality_filters)
        - Regime filters go in Stage 5 (compute_regime_state)
        - All computations must be deterministic (no wall clock, no randomness)
        - Must use DeterministicClock and DeterministicIdGenerator

    - stage: 4_write_tests
      role: SENIOR_ENGINEER
      action: write_tests
      output: Unit and integration tests
      deliverables:
        - Unit tests for filter logic (>90% coverage)
        - Integration tests with brain pipeline
        - Test fixtures with realistic market data
        - Determinism verification test
      depends_on: [3_implement_filter]
      approval_gate: test_review
      approvers: [ENGINEERING_MANAGER]
      notes: |
        - Test location: tests/test_brain.py
        - Test fixtures: tests/fixtures/*.json
        - Must verify determinism (same inputs → same outputs)
        - Fixtures must use realistic data:
          - Stock prices matching real ranges (VZ ~$40, AAPL ~$200, SPY ~$570)
          - Option premiums $0.50-$5.00 for 30-45 DTE
          - RSI 0-100 scale
          - VIX typical range 12-35
          - Delta ranges: puts -0.15 to -0.50

    - stage: 5_run_backtest
      role: QA_ENGINEER
      action: run_backtest
      output: Backtest execution results
      deliverables:
        - Backtest run (1+ year historical data)
        - Trade log with all entries/exits
        - Performance metrics (Sharpe, Sortino, max DD)
        - Regime analysis (performance by market condition)
      depends_on: [4_write_tests]
      approval_gate: backtest_execution
      approvers: [ENGINEERING_MANAGER]
      notes: |
        - Use janus/backtest.py module
        - Typical backtest period: 2024-01-01 to 2025-01-01 (1 year)
        - Must use realistic historical market data
        - Backtest uses same execute_cycle() as production
        - Output includes equity curve, trade log, closed trades

    - stage: 6_validate_metrics
      role: QA_ENGINEER
      action: validate_metrics
      output: QA sign-off report
      deliverables:
        - Metrics vs. acceptance criteria comparison
        - Win rate and avg win/loss analysis
        - Drawdown analysis
        - Risk-adjusted return validation
        - Comparison vs. baseline strategy
        - No regressions in test suite
      depends_on: [5_run_backtest]
      approval_gate: qa_signoff
      approvers: [QA_LEAD, PRODUCT_MANAGER]
      notes: |
        - Must run full test suite: python3 -m pytest tests/ -v
        - All existing tests must pass (no regressions)
        - Backtest results must meet acceptance criteria from Stage 1
        - Common metrics to validate:
          - Sharpe ratio > baseline
          - Max drawdown < risk tolerance
          - Win rate meets targets
          - Avg premium capture improved

    - stage: 7_approve_production
      role: PRODUCT_MANAGER
      action: approve_for_production
      output: Production deployment decision
      deliverables:
        - Go/no-go decision with rationale
        - Production deployment plan
        - Monitoring and alert configuration
        - Rollback criteria
      depends_on: [6_validate_metrics]
      approval_gate: production_approval
      approvers: [VP_PRODUCT, ENGINEERING_MANAGER, QA_LEAD]
      notes: |
        - Three-way approval required (PM, EM, QA Lead)
        - Must review:
          - Backtest results meet acceptance criteria
          - All tests passing
          - Code reviewed and approved
          - Determinism verified
        - Production consequences: bad code loses real money

    - stage: 8_deploy
      role: SRE
      action: deploy_to_telegram_bot
      output: Live deployment
      deliverables:
        - Updated config.json deployed
        - Telegram bot restarted with new config
        - Monitoring dashboards updated
        - Alert rules configured
        - Deployment verified in production
      depends_on: [7_approve_production]
      approval_gate: deployment_verification
      approvers: [ENGINEERING_MANAGER]
      notes: |
        - Deployment target: janus/bot.py (Telegram bot)
        - Bot uses Schwab adapter for live market data
        - config.json update triggers strategy activation
        - Must verify:
          - Bot restarts successfully
          - Live data fetching works
          - First cycle completes without errors
          - Alerts firing correctly

workflow_metadata:
  typical_duration: "1-2 weeks"
  critical_path:
    - "Stage 5-6 (backtest) is longest: 1-2 days for data collection and analysis"
    - "Stage 3-4 (implementation + tests) depends on filter complexity"
  success_criteria:
    - All tests passing (pytest suite)
    - Backtest meets acceptance criteria
    - Determinism verified (byte-identical outputs)
    - Three-way approval (PM, EM, QA) obtained
    - Live deployment successful
  failure_modes:
    - Backtest shows negative Sharpe or excessive drawdown
    - Determinism violation detected
    - Test suite regressions
    - Live deployment errors

  janus_architecture_notes:
    brain_pipeline: |
      Janus uses a 12-stage deterministic brain pipeline (brain/core.py):
      1. Normalize Inputs
      2. Build Feature Vectors
      3. Build Candidate Underlyings
      4. Apply Quality Filters ← New quality filters go here
      5. Apply Regime Filters ← New regime filters go here
      6. Generate Exit Signals
      7. Construct Candidate Structures
      8. Risk Evaluate Candidates
      9. Rank Candidates
      10. Select Suggestions Under Capital Budget
      11. Generate Decision Artifacts
      12. Populate Run Report Outputs

    determinism_contract: |
      - All code must be deterministic (no wall clock, no randomness, no external I/O)
      - Use DeterministicClock for all time operations
      - Use DeterministicIdGenerator for all identifiers
      - Same inputs → byte-identical outputs (verified via hash comparison)

    testing_architecture: |
      - Unit tests: tests/test_brain.py
      - Integration tests: tests/test_janus_cli.py
      - Backtest harness: janus/backtest.py (orchestration layer, not pure engine)
      - Test fixtures: tests/fixtures/*.json

    deployment_architecture: |
      - Production: janus/bot.py (Telegram bot)
      - Data source: Schwab API via adapters/schwab.py
      - Config: config.json (defines trading universe and risk parameters)
      - Engine: run.py → brain/core.py (pure, deterministic)

    domain_constraints: |
      - Options contract multiplier: 100x (all per-share prices × 100 for dollar amounts)
      - Spread leg pairing: short leg (higher strike) - long leg (lower strike)
      - Credit spreads: natural_credit = short_leg.bid - long_leg.ask (must be positive)
      - P&L computation: cost_basis = abs(avg_price × quantity × 100)
```

---

## Cross-Workflow Patterns

### Approval Gates

All workflows use approval gates to enforce quality and stakeholder alignment.

**Approval Gate Types:**

1. **Concept Approval** - Validates the problem and approach before investment
   - Used in: feature (design_kickoff), trading_strategy (strategy_concept)
   - Approvers: Leadership roles (VP, EM)

2. **Design Review** - Validates design quality and feasibility
   - Used in: feature (design_review), trading_strategy (schema_review)
   - Approvers: PM, EM

3. **Code Review** - Validates implementation quality
   - Used in: feature, bug, trading_strategy
   - Approvers: EM, Senior Eng

4. **QA Sign-off** - Validates correctness and quality
   - Used in: feature, bug, launch, trading_strategy
   - Approvers: QA Lead

5. **Production Approval** - Validates deployment readiness
   - Used in: feature, launch, trading_strategy
   - Approvers: VP-level + EM + QA Lead (high-risk deployments)

**Approval Workflow:**

```yaml
approval_process:
  - Agent completes stage deliverables
  - Agent posts to approval channel with context
  - Approvers review deliverables
  - Approvers post approval/rejection with rationale
  - On rejection: Agent addresses feedback, resubmits
  - On approval: Next stage unblocked
```

### Dependency Management

**Dependency Types:**

1. **Sequential** - Stage B must wait for Stage A to complete
   - Example: `implement` depends_on `create_mocks`

2. **Parallel** - Stages can run concurrently
   - Example: `create_content` and `feature_flag` in launch workflow

3. **Fan-in** - Multiple stages must complete before proceeding
   - Example: `go_live` depends_on [content, regression_test, support_docs]

**Dependency Resolution:**

```yaml
dependency_rules:
  - A stage cannot claim until all `depends_on` stages are completed
  - Completed stages are immutable (cannot re-open)
  - Approval gates block dependent stages until approved
  - Parallel stages can be claimed simultaneously by different agents
```

### Role Responsibilities

**Product Manager:**
- Define requirements and acceptance criteria
- Approve designs and releases
- Make go/no-go decisions
- Own success metrics

**Product Designer:**
- Create user-facing designs
- Define config schemas (for trading strategies)
- Ensure design system consistency

**Engineer / Senior Engineer:**
- Implement features and fixes
- Write tests (unit, integration, regression)
- Maintain code quality and determinism

**QA Engineer / QA Lead:**
- Reproduce bugs
- Execute test plans
- Run backtests (trading strategies)
- Validate metrics and sign off on quality

**Engineering Manager:**
- Approve architecture and code
- Triage bugs
- Approve production deployments
- Manage technical risk

**Growth Manager:**
- Create marketing content
- Execute launches
- Track adoption metrics

**SRE:**
- Deploy to production
- Configure monitoring and alerts
- Maintain infrastructure

**Support Lead:**
- Prepare user documentation
- Train support team
- Create FAQs

---

## Workflow Router Implementation

The `WorkflowRouter` uses these definitions to:

1. **Route Epics** - Map epic type to workflow sequence
2. **Create Tasks** - Generate tasks for each workflow stage
3. **Set Dependencies** - Configure blocking relationships
4. **Assign Approvers** - Route approval requests to correct roles
5. **Track Progress** - Monitor workflow completion

**Example Routing:**

```python
epic = Epic(
    title="Add IV Percentile Filter",
    epic_type="trading_strategy",
    created_by=pm_agent
)

# Router generates 8 tasks in sequence:
tasks = router.route_epic(epic, company)
# → Task 1: define_strategy_goals (PM)
# → Task 2: design_config_schema (Designer) [blocked by Task 1]
# → Task 3: implement_filter (Senior Eng) [blocked by Task 2]
# → ... etc

# Each task includes:
# - role_required (for agent claiming)
# - depends_on (for blocking)
# - approval_gate (for quality control)
# - deliverables (for acceptance criteria)
```

---

## Next Steps

1. Implement `WorkflowRouter` in `agentcoord/workflows.py`
2. Create `ApprovalGate` system in `agentcoord/approvals.py`
3. Add workflow templates to `agentcoord/templates/workflows/`
4. Write integration tests validating each workflow end-to-end
5. Document workflow customization for new domains

---

## References

- **COMPANY_MODEL_ROADMAP.md** - Phase 1 and 2 architecture
- **Janus CLAUDE.md** - Engineering constraints and architecture
- **Janus BRAIN_SPEC.md** - 12-stage brain pipeline specification
- **Janus codebase** - `/Users/johnmonty/Desktop/Janus_Engine/janus`
