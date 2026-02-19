"""
MasterCoordinator - Top-level orchestrator for hierarchical coordination.

Breaks large projects into sub-projects and spawns sub-coordinators.
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProjectStatus(str, Enum):
    """Project status in hierarchy."""
    PLANNING = "planning"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class SubProject:
    """A sub-project assigned to a sub-coordinator."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        budget_allocated: float,
        priority: int = 3,
        deadline: Optional[str] = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.budget_allocated = budget_allocated
        self.budget_used = 0.0
        self.priority = priority
        self.deadline = deadline
        self.status = ProjectStatus.PLANNING
        self.assigned_coordinator = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.tasks = []
        self.progress = 0.0


class MasterCoordinator:
    """
    Top-level coordinator that orchestrates multiple sub-coordinators.

    Responsibilities:
    - Break high-level goals into sub-projects
    - Allocate budget across sub-projects
    - Spawn and manage sub-coordinators
    - Monitor overall progress
    - Reallocate resources dynamically
    - Handle escalations
    """

    def __init__(
        self,
        redis_client,
        coordinator_id: Optional[str] = None,
        total_budget: float = 100.0
    ):
        self.redis = redis_client
        self.coordinator_id = coordinator_id or f"master-{uuid.uuid4().hex[:8]}"
        self.total_budget = total_budget
        self.budget_allocated = 0.0
        self.budget_used = 0.0
        self.sub_projects: Dict[str, SubProject] = {}
        self.sub_coordinators: Dict[str, str] = {}  # sub_coordinator_id -> sub_project_id

        # Register as master coordinator
        self._register()

        logger.info(f"MasterCoordinator {self.coordinator_id} initialized with ${total_budget} budget")

    def _register(self):
        """Register in Redis as master coordinator."""
        key = f"coordinator:master:{self.coordinator_id}"
        self.redis.hset(key, mapping={
            'id': self.coordinator_id,
            'type': 'master',
            'total_budget': self.total_budget,
            'budget_allocated': self.budget_allocated,
            'budget_used': self.budget_used,
            'created_at': datetime.now(timezone.utc).isoformat()
        })

        # Add to master set
        self.redis.sadd('coordinators:master', self.coordinator_id)

    def decompose_goal(self, goal: str) -> List[SubProject]:
        """
        Break high-level goal into sub-projects.

        This is where the master uses intelligence to decompose work.
        For now, this is a template - in production, this would use LLM.

        Args:
            goal: High-level project goal

        Returns:
            List of SubProject definitions
        """
        # TODO: Use LLM to intelligently break down goal
        # For now, return template structure

        logger.info(f"Decomposing goal: {goal}")

        # Example decomposition (would be LLM-driven)
        if "web app" in goal.lower():
            return [
                SubProject(
                    id=f"sub-{uuid.uuid4().hex[:8]}",
                    title="Backend API Development",
                    description="Build REST API with authentication and data models",
                    budget_allocated=self.total_budget * 0.4,
                    priority=5
                ),
                SubProject(
                    id=f"sub-{uuid.uuid4().hex[:8]}",
                    title="Frontend UI Development",
                    description="Build responsive UI with React components",
                    budget_allocated=self.total_budget * 0.4,
                    priority=5
                ),
                SubProject(
                    id=f"sub-{uuid.uuid4().hex[:8]}",
                    title="DevOps & Deployment",
                    description="Setup CI/CD, monitoring, and infrastructure",
                    budget_allocated=self.total_budget * 0.2,
                    priority=3
                ),
            ]

        # Default: single sub-project
        return [
            SubProject(
                id=f"sub-{uuid.uuid4().hex[:8]}",
                title=goal,
                description=f"Complete: {goal}",
                budget_allocated=self.total_budget,
                priority=3
            )
        ]

    def allocate_budget(self, sub_projects: List[SubProject]) -> bool:
        """
        Validate and allocate budget across sub-projects.

        Returns:
            True if allocation successful, False if over budget
        """
        total_requested = sum(sp.budget_allocated for sp in sub_projects)

        if total_requested > self.total_budget:
            logger.warning(f"Budget allocation failed: ${total_requested} > ${self.total_budget}")
            return False

        for sp in sub_projects:
            self.sub_projects[sp.id] = sp
            self.budget_allocated += sp.budget_allocated

            # Store in Redis
            self._store_subproject(sp)

        logger.info(f"Allocated ${self.budget_allocated} across {len(sub_projects)} sub-projects")
        return True

    def _store_subproject(self, sub_project: SubProject):
        """Store sub-project in Redis."""
        key = f"subproject:{sub_project.id}"
        self.redis.hset(key, mapping={
            'id': sub_project.id,
            'title': sub_project.title,
            'description': sub_project.description,
            'budget_allocated': sub_project.budget_allocated,
            'budget_used': sub_project.budget_used,
            'priority': sub_project.priority,
            'status': sub_project.status.value,
            'master_coordinator': self.coordinator_id,
            'assigned_coordinator': sub_project.assigned_coordinator or '',
            'created_at': sub_project.created_at,
            'progress': sub_project.progress
        })

        # Link to master
        self.redis.sadd(f"coordinator:master:{self.coordinator_id}:subprojects", sub_project.id)

    def spawn_sub_coordinator(self, sub_project_id: str) -> str:
        """
        Spawn a sub-coordinator for a sub-project.

        Returns:
            Sub-coordinator ID
        """
        if sub_project_id not in self.sub_projects:
            raise ValueError(f"Sub-project {sub_project_id} not found")

        sub_project = self.sub_projects[sub_project_id]

        # Create sub-coordinator ID
        sub_coord_id = f"sub-{uuid.uuid4().hex[:8]}"

        # Store assignment
        self.sub_coordinators[sub_coord_id] = sub_project_id
        sub_project.assigned_coordinator = sub_coord_id
        sub_project.status = ProjectStatus.ASSIGNED

        # Update in Redis
        self._store_subproject(sub_project)

        # Register sub-coordinator
        self.redis.hset(f"coordinator:sub:{sub_coord_id}", mapping={
            'id': sub_coord_id,
            'type': 'sub',
            'master_coordinator': self.coordinator_id,
            'sub_project_id': sub_project_id,
            'budget_allocated': sub_project.budget_allocated,
            'created_at': datetime.now(timezone.utc).isoformat()
        })

        # Link relationships
        self.redis.sadd(f"coordinator:master:{self.coordinator_id}:children", sub_coord_id)
        self.redis.set(f"coordinator:sub:{sub_coord_id}:parent", self.coordinator_id)

        logger.info(f"Spawned sub-coordinator {sub_coord_id} for {sub_project.title}")

        return sub_coord_id

    def get_overall_progress(self) -> float:
        """Calculate overall progress across all sub-projects."""
        if not self.sub_projects:
            return 0.0

        weighted_progress = sum(
            sp.progress * sp.budget_allocated
            for sp in self.sub_projects.values()
        )

        return weighted_progress / self.budget_allocated if self.budget_allocated > 0 else 0.0

    def get_status_report(self) -> Dict:
        """Get comprehensive status report."""
        return {
            'coordinator_id': self.coordinator_id,
            'total_budget': self.total_budget,
            'budget_allocated': self.budget_allocated,
            'budget_used': self.budget_used,
            'budget_remaining': self.total_budget - self.budget_used,
            'overall_progress': self.get_overall_progress(),
            'sub_projects': {
                sp_id: {
                    'title': sp.title,
                    'status': sp.status.value,
                    'progress': sp.progress,
                    'budget_allocated': sp.budget_allocated,
                    'budget_used': sp.budget_used,
                    'assigned_coordinator': sp.assigned_coordinator
                }
                for sp_id, sp in self.sub_projects.items()
            },
            'active_sub_coordinators': len(self.sub_coordinators)
        }
