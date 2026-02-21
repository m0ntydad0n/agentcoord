# Role and Capability Management API Design

**Author**: API Designer
**Date**: 2026-02-20
**Status**: Design Specification

## Overview

This document specifies the Python API for role-based access control (RBAC) and capability management in AgentCoord. The API enables agents to check permissions, enforce approval gates based on roles, and extend the system with custom roles and capabilities.

## Design Principles

1. **Type-safe**: Use enums for built-in roles and capabilities to catch errors at development time
2. **Extensible**: Support custom roles and capabilities without modifying core code
3. **Composable**: Capabilities can be combined and checked independently
4. **Explicit**: Permission checks are clear and readable in code
5. **Auditable**: All permission checks and role assignments are logged to audit trail

## Core Components

### 1. Role Enum

Built-in roles with predefined capabilities.

```python
from enum import Enum
from typing import Set, FrozenSet

class Role(str, Enum):
    """Built-in agent roles with predefined capabilities."""

    # Leadership roles
    CTO = "cto"
    EM = "engineering_manager"
    TECH_LEAD = "tech_lead"

    # Specialist roles
    ENGINEER = "engineer"
    QA_LEAD = "qa_lead"
    REVIEWER = "reviewer"

    # Operational roles
    WORKER = "worker"
    OBSERVER = "observer"

    @property
    def capabilities(self) -> FrozenSet[str]:
        """Get capabilities for this role."""
        return ROLE_CAPABILITIES.get(self, frozenset())

    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """Parse role from string, case-insensitive."""
        try:
            return cls(role_str.lower())
        except ValueError:
            raise ValueError(f"Unknown role: {role_str}. Use Role.create() for custom roles.")

    @staticmethod
    def create(name: str, capabilities: Set[str]) -> "CustomRole":
        """Create a custom role with specific capabilities.

        Args:
            name: Role name (e.g., "ANALYST", "DEVOPS")
            capabilities: Set of capability strings

        Returns:
            CustomRole instance

        Example:
            analyst = Role.create("ANALYST", {"read_metrics", "create_reports"})
        """
        return CustomRole(name=name.upper(), capabilities=frozenset(capabilities))
```

### 2. Capability Definitions

Capability constants for type-safe permission checks.

```python
class Capability:
    """Built-in capability constants."""

    # Approval capabilities
    APPROVE_RELEASE = "approve_release"
    APPROVE_DEPLOY = "approve_deploy"
    APPROVE_ARCHITECTURE = "approve_architecture"
    APPROVE_COMMIT = "approve_commit"

    # Action capabilities
    CREATE_TASK = "create_task"
    CLAIM_TASK = "claim_task"
    ESCALATE_TASK = "escalate_task"
    DELETE_TASK = "delete_task"

    # File capabilities
    LOCK_FILE = "lock_file"
    EDIT_FILE = "edit_file"
    DELETE_FILE = "delete_file"

    # Board capabilities
    POST_THREAD = "post_thread"
    ARCHIVE_THREAD = "archive_thread"
    PIN_THREAD = "pin_thread"

    # Audit capabilities
    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_AUDIT_LOG = "export_audit_log"

    # Configuration capabilities
    MODIFY_CONFIG = "modify_config"
    DEPLOY_PRODUCTION = "deploy_production"

    # Administrative capabilities
    CREATE_ROLE = "create_role"
    ASSIGN_ROLE = "assign_role"
    MANAGE_AGENTS = "manage_agents"


# Role to capability mapping
ROLE_CAPABILITIES: Dict[Role, FrozenSet[str]] = {
    Role.CTO: frozenset([
        Capability.APPROVE_RELEASE,
        Capability.APPROVE_DEPLOY,
        Capability.APPROVE_ARCHITECTURE,
        Capability.APPROVE_COMMIT,
        Capability.CREATE_TASK,
        Capability.CLAIM_TASK,
        Capability.ESCALATE_TASK,
        Capability.DELETE_TASK,
        Capability.LOCK_FILE,
        Capability.EDIT_FILE,
        Capability.POST_THREAD,
        Capability.ARCHIVE_THREAD,
        Capability.PIN_THREAD,
        Capability.VIEW_AUDIT_LOG,
        Capability.EXPORT_AUDIT_LOG,
        Capability.MODIFY_CONFIG,
        Capability.DEPLOY_PRODUCTION,
        Capability.CREATE_ROLE,
        Capability.ASSIGN_ROLE,
        Capability.MANAGE_AGENTS,
    ]),

    Role.EM: frozenset([
        Capability.APPROVE_RELEASE,
        Capability.APPROVE_DEPLOY,
        Capability.CREATE_TASK,
        Capability.CLAIM_TASK,
        Capability.ESCALATE_TASK,
        Capability.LOCK_FILE,
        Capability.EDIT_FILE,
        Capability.POST_THREAD,
        Capability.PIN_THREAD,
        Capability.VIEW_AUDIT_LOG,
        Capability.ASSIGN_ROLE,
    ]),

    Role.TECH_LEAD: frozenset([
        Capability.APPROVE_ARCHITECTURE,
        Capability.APPROVE_COMMIT,
        Capability.CREATE_TASK,
        Capability.CLAIM_TASK,
        Capability.ESCALATE_TASK,
        Capability.LOCK_FILE,
        Capability.EDIT_FILE,
        Capability.POST_THREAD,
        Capability.VIEW_AUDIT_LOG,
    ]),

    Role.QA_LEAD: frozenset([
        Capability.APPROVE_RELEASE,
        Capability.CREATE_TASK,
        Capability.CLAIM_TASK,
        Capability.POST_THREAD,
        Capability.VIEW_AUDIT_LOG,
    ]),

    Role.ENGINEER: frozenset([
        Capability.CREATE_TASK,
        Capability.CLAIM_TASK,
        Capability.LOCK_FILE,
        Capability.EDIT_FILE,
        Capability.POST_THREAD,
    ]),

    Role.REVIEWER: frozenset([
        Capability.APPROVE_COMMIT,
        Capability.CLAIM_TASK,
        Capability.POST_THREAD,
        Capability.VIEW_AUDIT_LOG,
    ]),

    Role.WORKER: frozenset([
        Capability.CLAIM_TASK,
        Capability.LOCK_FILE,
        Capability.EDIT_FILE,
        Capability.POST_THREAD,
    ]),

    Role.OBSERVER: frozenset([
        Capability.VIEW_AUDIT_LOG,
    ]),
}
```

### 3. CustomRole Class

For defining custom roles beyond built-in ones.

```python
from dataclasses import dataclass

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
```

### 4. Agent Class Extensions

Add role and capability management to agents.

```python
from typing import Union

RoleType = Union[Role, CustomRole]

class Agent:
    """Enhanced Agent with role-based access control."""

    def __init__(self, agent_id: str, role: RoleType):
        self.agent_id = agent_id
        self.role = role
        self._custom_capabilities: Set[str] = set()

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability.

        Args:
            capability: Capability string to check

        Returns:
            True if agent has the capability, False otherwise

        Example:
            if agent.has_capability(Capability.APPROVE_RELEASE):
                gate.approve(agent)
        """
        # Check role capabilities
        if isinstance(self.role, Role):
            role_caps = self.role.capabilities
        else:
            role_caps = self.role.capabilities

        # Check custom capabilities
        return capability in role_caps or capability in self._custom_capabilities

    def grant_capability(self, capability: str):
        """Grant an additional capability to this agent.

        Args:
            capability: Capability to grant

        Note:
            Only agents with Capability.ASSIGN_ROLE can call this.
            Logs to audit trail.
        """
        self._custom_capabilities.add(capability)
        # Log to audit trail
        if hasattr(self, 'audit_log'):
            self.audit_log.log(
                agent_id=self.agent_id,
                action="grant_capability",
                details={"capability": capability}
            )

    def revoke_capability(self, capability: str):
        """Revoke a custom capability from this agent.

        Args:
            capability: Capability to revoke
        """
        self._custom_capabilities.discard(capability)
        # Log to audit trail
        if hasattr(self, 'audit_log'):
            self.audit_log.log(
                agent_id=self.agent_id,
                action="revoke_capability",
                details={"capability": capability}
            )

    def get_all_capabilities(self) -> Set[str]:
        """Get all capabilities (role + custom)."""
        if isinstance(self.role, Role):
            role_caps = set(self.role.capabilities)
        else:
            role_caps = set(self.role.capabilities)
        return role_caps | self._custom_capabilities

    def require_capability(self, capability: str):
        """Raise PermissionDenied if agent lacks capability.

        Args:
            capability: Required capability

        Raises:
            PermissionDenied: If agent lacks the capability

        Example:
            agent.require_capability(Capability.DEPLOY_PRODUCTION)
            # ... perform deployment ...
        """
        if not self.has_capability(capability):
            raise PermissionDenied(
                f"Agent {self.agent_id} ({self.role}) lacks capability: {capability}"
            )
```

### 5. ApprovalGate Class

Enhanced approval gates with role-based validation.

```python
from typing import List, Set
from dataclasses import dataclass, field

@dataclass
class ApprovalGate:
    """Approval gate requiring specific roles or capabilities."""

    gate_id: str
    action_type: str  # "production_deploy", "release", "architecture_change"
    description: str

    # Role-based requirements
    required_roles: Set[RoleType] = field(default_factory=set)
    required_capabilities: Set[str] = field(default_factory=set)

    # Approval tracking
    approvals: List[str] = field(default_factory=list)  # agent_ids
    rejections: List[str] = field(default_factory=list)  # agent_ids

    # Configuration
    min_approvals: int = 1
    allow_self_approval: bool = False

    def requires_approval_from(self, roles: List[RoleType]) -> "ApprovalGate":
        """Specify which roles can approve this gate.

        Args:
            roles: List of Role or CustomRole instances

        Returns:
            Self for chaining

        Example:
            gate = ApprovalGate("production_deploy")
            gate.requires_approval_from([Role.EM, Role.QA_LEAD])
        """
        self.required_roles = set(roles)
        return self

    def requires_capability(self, capability: str) -> "ApprovalGate":
        """Require approvers to have a specific capability.

        Args:
            capability: Required capability string

        Returns:
            Self for chaining

        Example:
            gate.requires_capability(Capability.APPROVE_RELEASE)
        """
        self.required_capabilities.add(capability)
        return self

    def can_approve(self, agent: Agent) -> bool:
        """Check if agent can approve this gate.

        Args:
            agent: Agent to check

        Returns:
            True if agent has required role/capabilities
        """
        # Check if already approved/rejected
        if agent.agent_id in self.approvals or agent.agent_id in self.rejections:
            return False

        # Check role match
        role_match = not self.required_roles or agent.role in self.required_roles

        # Check capabilities
        capability_match = all(
            agent.has_capability(cap) for cap in self.required_capabilities
        )

        return role_match and capability_match

    def approve(self, agent: Agent):
        """Approve gate with this agent.

        Args:
            agent: Approving agent

        Raises:
            PermissionDenied: If agent cannot approve
        """
        if not self.can_approve(agent):
            raise PermissionDenied(
                f"Agent {agent.agent_id} ({agent.role}) cannot approve {self.action_type}"
            )

        self.approvals.append(agent.agent_id)

        # Log to audit
        if hasattr(agent, 'audit_log'):
            agent.audit_log.log(
                agent_id=agent.agent_id,
                action="approve_gate",
                details={
                    "gate_id": self.gate_id,
                    "action_type": self.action_type,
                    "description": self.description
                }
            )

    def reject(self, agent: Agent):
        """Reject gate with this agent."""
        if not self.can_approve(agent):
            raise PermissionDenied(
                f"Agent {agent.agent_id} ({agent.role}) cannot reject {self.action_type}"
            )

        self.rejections.append(agent.agent_id)

    def is_approved(self) -> bool:
        """Check if gate has sufficient approvals."""
        return len(self.approvals) >= self.min_approvals and len(self.rejections) == 0

    def is_rejected(self) -> bool:
        """Check if gate has been rejected."""
        return len(self.rejections) > 0


class PermissionDenied(Exception):
    """Raised when agent lacks required permission."""
    pass
```

### 6. RoleRegistry

Manage custom roles across the system.

```python
class RoleRegistry:
    """Registry for custom roles."""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self._custom_roles: Dict[str, CustomRole] = {}

    def register_role(self, role: CustomRole):
        """Register a custom role.

        Args:
            role: CustomRole to register
        """
        self._custom_roles[role.name] = role

        if self.redis_client:
            key = f"roles:custom:{role.name}"
            self.redis_client.hset(key, mapping={
                "name": role.name,
                "capabilities": json.dumps(list(role.capabilities))
            })

    def get_role(self, name: str) -> Optional[CustomRole]:
        """Retrieve a custom role by name."""
        # Check memory cache
        if name in self._custom_roles:
            return self._custom_roles[name]

        # Check Redis
        if self.redis_client:
            key = f"roles:custom:{name}"
            data = self.redis_client.hgetall(key)
            if data:
                capabilities = json.loads(data["capabilities"])
                role = CustomRole(name=name, capabilities=frozenset(capabilities))
                self._custom_roles[name] = role
                return role

        return None

    def list_custom_roles(self) -> List[CustomRole]:
        """List all registered custom roles."""
        if self.redis_client:
            # Sync from Redis
            for key in self.redis_client.keys("roles:custom:*"):
                name = key.split(":")[-1]
                if name not in self._custom_roles:
                    self.get_role(name)

        return list(self._custom_roles.values())
```

## Usage Examples

### Example 1: Basic Permission Check

```python
from agentcoord import Role, Capability, Agent, PermissionDenied

# Create agents with different roles
engineer = Agent("alice", Role.ENGINEER)
tech_lead = Agent("bob", Role.TECH_LEAD)
cto = Agent("carol", Role.CTO)

# Check capabilities
if engineer.has_capability(Capability.EDIT_FILE):
    # Edit file
    pass

if tech_lead.has_capability(Capability.APPROVE_ARCHITECTURE):
    # Can review architecture proposals
    pass

# Require capability (raises if missing)
try:
    engineer.require_capability(Capability.APPROVE_RELEASE)
except PermissionDenied as e:
    print(f"Permission denied: {e}")
```

### Example 2: Approval Gates

```python
from agentcoord import ApprovalGate, Role

# Create approval gate for production deployment
gate = ApprovalGate(
    gate_id="deploy-v2.1.0",
    action_type="production_deploy",
    description="Deploy version 2.1.0 to production"
)

# Require both EM and QA Lead approval
gate.requires_approval_from([Role.EM, Role.QA_LEAD])
gate.min_approvals = 2

# Agents attempt to approve
em_agent = Agent("alice", Role.EM)
qa_agent = Agent("bob", Role.QA_LEAD)
engineer_agent = Agent("charlie", Role.ENGINEER)

# EM approves
if gate.can_approve(em_agent):
    gate.approve(em_agent)

# QA Lead approves
if gate.can_approve(qa_agent):
    gate.approve(qa_agent)

# Engineer cannot approve
try:
    gate.approve(engineer_agent)
except PermissionDenied:
    print("Engineer cannot approve production deploys")

# Check if approved
if gate.is_approved():
    print("Deployment approved - proceeding")
```

### Example 3: Capability-Based Gates

```python
# Require specific capability instead of role
gate = ApprovalGate("release-v1.0", "release", "Release v1.0")
gate.requires_capability(Capability.APPROVE_RELEASE)
gate.min_approvals = 1

# Any agent with approve_release capability can approve
# (CTO, EM, or QA_LEAD in default config)
if agent.has_capability(Capability.APPROVE_RELEASE):
    gate.approve(agent)
```

### Example 4: Custom Roles

```python
from agentcoord import Role, CustomRole, RoleRegistry

# Create custom role for data analysts
analyst_role = Role.create("ANALYST", {
    "read_metrics",
    "create_reports",
    Capability.VIEW_AUDIT_LOG,
    Capability.POST_THREAD
})

# Register the custom role
registry = RoleRegistry(redis_client)
registry.register_role(analyst_role)

# Create agent with custom role
analyst = Agent("data-analyst-1", analyst_role)

# Check custom capabilities
if analyst.has_capability("read_metrics"):
    # Access metrics
    pass

# Retrieve custom role later
retrieved_role = registry.get_role("ANALYST")
```

### Example 5: Dynamic Capability Grants

```python
# Grant temporary capability to an agent
worker = Agent("worker-1", Role.WORKER)

# Worker normally can't approve
assert not worker.has_capability(Capability.APPROVE_COMMIT)

# CTO grants review capability temporarily
cto = Agent("cto", Role.CTO)
cto.require_capability(Capability.ASSIGN_ROLE)  # Verify permission
worker.grant_capability(Capability.APPROVE_COMMIT)

# Now worker can approve commits
assert worker.has_capability(Capability.APPROVE_COMMIT)

# Revoke after use
worker.revoke_capability(Capability.APPROVE_COMMIT)
```

### Example 6: Integration with CoordinationClient

```python
from agentcoord import CoordinationClient, Role

# Create client with role
with CoordinationClient.session(
    redis_url="redis://localhost:6379",
    role="TECH_LEAD",
    name="Bob"
) as coord:
    # Client automatically creates agent with role
    agent = coord.agent_registry.get_agent(coord.agent_id)

    # Check permission before action
    if agent.has_capability(Capability.APPROVE_ARCHITECTURE):
        # Approve architecture change
        approval_workflow = coord.approval_workflow
        approval_workflow.approve(approval_id, agent.agent_id)
```

### Example 7: Multi-Role Approval

```python
# Require approval from multiple different roles
gate = ApprovalGate(
    gate_id="critical-change",
    action_type="architecture_change",
    description="Rewrite authentication system"
)

# Need both tech lead AND EM
gate.requires_approval_from([Role.TECH_LEAD, Role.EM])
gate.min_approvals = 2

tech_lead_1 = Agent("alice", Role.TECH_LEAD)
tech_lead_2 = Agent("bob", Role.TECH_LEAD)
em = Agent("carol", Role.EM)

# Two tech leads can't satisfy requirement
gate.approve(tech_lead_1)
gate.approve(tech_lead_2)
assert not gate.is_approved()  # Still need EM

# EM approves - now satisfied
gate.approve(em)
assert gate.is_approved()
```

## Extension Patterns

### Adding New Capabilities

```python
# 1. Define capability constant
class Capability:
    # ... existing ...
    EMERGENCY_OVERRIDE = "emergency_override"

# 2. Add to role mapping
ROLE_CAPABILITIES[Role.CTO] = ROLE_CAPABILITIES[Role.CTO] | {
    Capability.EMERGENCY_OVERRIDE
}

# 3. Use in code
if agent.has_capability(Capability.EMERGENCY_OVERRIDE):
    # Bypass normal approval flow
    pass
```

### Creating Role Hierarchies

```python
# Define role with inherited capabilities
class ExtendedRole(CustomRole):
    """Custom role that inherits from a base role."""

    def __init__(self, name: str, base_role: Role, additional_caps: Set[str]):
        combined = set(base_role.capabilities) | additional_caps
        super().__init__(name=name, capabilities=frozenset(combined))

# Senior engineer has all engineer capabilities + more
senior_engineer = ExtendedRole(
    "SENIOR_ENGINEER",
    base_role=Role.ENGINEER,
    additional_caps={Capability.APPROVE_COMMIT, "mentor_junior"}
)
```

### Domain-Specific Capabilities

```python
# Define domain-specific capabilities for your project
class TradingCapability:
    """Trading system specific capabilities."""
    EXECUTE_TRADE = "execute_trade"
    CANCEL_ORDER = "cancel_order"
    VIEW_POSITIONS = "view_positions"
    MODIFY_STRATEGY = "modify_strategy"

# Create trader role
trader_role = Role.create("TRADER", {
    TradingCapability.EXECUTE_TRADE,
    TradingCapability.VIEW_POSITIONS,
    Capability.VIEW_AUDIT_LOG
})

# Risk manager can cancel but not execute
risk_manager = Role.create("RISK_MANAGER", {
    TradingCapability.CANCEL_ORDER,
    TradingCapability.VIEW_POSITIONS,
    Capability.VIEW_AUDIT_LOG,
    Capability.EXPORT_AUDIT_LOG
})
```

## Redis Storage Schema

### Agent Role Storage

```
Key: agents:{agent_id}:role
Type: Hash
Fields:
  - role_type: "builtin" | "custom"
  - role_name: "engineer" | "ANALYST"
  - custom_capabilities: JSON list of additional capabilities
```

### Custom Role Registry

```
Key: roles:custom:{role_name}
Type: Hash
Fields:
  - name: role name
  - capabilities: JSON list of capability strings
  - created_at: ISO timestamp
  - created_by: agent_id who created role
```

### Permission Audit Trail

```
Key: audit:permissions:{agent_id}
Type: Stream
Entries:
  - action: "grant_capability" | "revoke_capability" | "approve_gate"
  - timestamp: ISO timestamp
  - details: JSON with specifics
```

## Type Definitions

```python
from typing import Protocol, Union

class HasRole(Protocol):
    """Protocol for objects with a role."""
    role: RoleType

    def has_capability(self, capability: str) -> bool:
        ...

class HasCapabilities(Protocol):
    """Protocol for objects with capabilities."""

    def has_capability(self, capability: str) -> bool:
        ...

    def get_all_capabilities(self) -> Set[str]:
        ...

# Type aliases
RoleType = Union[Role, CustomRole]
CapabilitySet = FrozenSet[str]
```

## Testing Helpers

```python
# Test utilities for mocking roles and capabilities

class MockAgent:
    """Test agent with configurable capabilities."""

    def __init__(self, agent_id: str, capabilities: Set[str]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.role = "mock"

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities

def create_test_agent(capabilities: List[str]) -> MockAgent:
    """Create test agent with specific capabilities."""
    return MockAgent("test-agent", set(capabilities))

# Usage in tests
def test_approval_gate():
    approver = create_test_agent([Capability.APPROVE_RELEASE])
    gate = ApprovalGate("test", "release", "Test release")
    gate.requires_capability(Capability.APPROVE_RELEASE)

    assert gate.can_approve(approver)
    gate.approve(approver)
    assert gate.is_approved()
```

## Migration Path

For existing AgentCoord deployments:

1. **Phase 1**: Add role field to agent registration (default to Role.WORKER for backward compatibility)
2. **Phase 2**: Add permission checks around critical operations (deployments, approvals)
3. **Phase 3**: Migrate existing agents to appropriate roles based on their usage patterns
4. **Phase 4**: Enforce permission checks (change warnings to errors)

```python
# Backward compatible registration
def register_agent(self, agent_id: str, agent_type: str, capabilities: List[str], role: Optional[RoleType] = None):
    """Register agent with optional role."""
    # Default to WORKER for backward compatibility
    if role is None:
        role = Role.WORKER

    # ... existing registration logic ...
```

## Security Considerations

1. **Capability Escalation**: Only agents with `ASSIGN_ROLE` capability can grant capabilities
2. **Audit Trail**: All permission grants, revocations, and approvals are logged
3. **Immutable Roles**: Built-in role capabilities are frozen and cannot be modified at runtime
4. **Approval Validation**: Gates verify both role AND capability before accepting approvals
5. **Self-Approval**: Can be disabled per gate to prevent agents from approving their own actions

## Performance Notes

- Role capability lookups are O(1) using frozenset membership checks
- Custom capabilities stored in memory cache with Redis backup
- Permission checks happen locally without Redis roundtrips
- Audit logging is asynchronous to avoid blocking operations

## Summary

This API provides:
- **Type-safe role definitions** using enums for built-in roles
- **Flexible capability system** with both predefined and custom capabilities
- **Composable approval gates** that validate against roles and capabilities
- **Extensibility** through custom roles and dynamic capability grants
- **Auditability** with full logging of permission-related actions
- **Performance** through local caching and efficient data structures

The design balances safety (type checking, permission validation) with flexibility (custom roles, dynamic grants) while maintaining a clean, readable API.
