from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from abc import ABC, abstractmethod
import uuid

from .sub_coordinator import SubCoordinator
from .project_decomposer import ProjectDecomposer
from .budget_allocator import BudgetAllocator
from .progress_aggregator import ProgressAggregator

logger = logging.getLogger(__name__)

class CoordinatorStatus(Enum):
    IDLE = "idle"
    DECOMPOSING = "decomposing"
    ALLOCATING_BUDGET = "allocating_budget"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class ProjectSpec:
    """Project specification with requirements and constraints"""
    id: str
    name: str
    description: str
    requirements: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    deadline: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SubProject:
    """Decomposed sub-project with allocated resources"""
    id: str
    name: str
    description: str
    requirements: Dict[str, Any]
    allocated_budget: float
    estimated_duration: float
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1
    coordinator_id: Optional[str] = None

@dataclass
class MasterProgress:
    """Aggregated progress information"""
    overall_completion: float
    active_sub_projects: int
    completed_sub_projects: int
    failed_sub_projects: int
    total_budget_used: float
    estimated_completion_time: Optional[float]
    status: CoordinatorStatus
    sub_project_progress: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class MasterCoordinator:
    """
    Top-level orchestrator that manages project decomposition,
    budget allocation, and coordination of sub-coordinators.
    """
    
    def __init__(
        self,
        decomposer: ProjectDecomposer,
        budget_allocator: BudgetAllocator,
        progress_aggregator: ProgressAggregator,
        max_concurrent_projects: int = 10,
        default_budget: float = 1000000.0
    ):
        self.id = str(uuid.uuid4())
        self.decomposer = decomposer
        self.budget_allocator = budget_allocator
        self.progress_aggregator = progress_aggregator
        self.max_concurrent_projects = max_concurrent_projects
        self.default_budget = default_budget
        
        # State management
        self.status = CoordinatorStatus.IDLE
        self.current_project: Optional[ProjectSpec] = None
        self.sub_projects: Dict[str, SubProject] = {}
        self.sub_coordinators: Dict[str, SubCoordinator] = {}
        self.total_budget: float = 0.0
        self.used_budget: float = 0.0
        
        # Progress tracking
        self._progress_lock = asyncio.Lock()
        self._execution_tasks: Dict[str, asyncio.Task] = {}
        
    async def execute_project(
        self,
        project: ProjectSpec,
        total_budget: Optional[float] = None
    ) -> MasterProgress:
        """
        Main execution method that orchestrates the entire project lifecycle.
        
        Args:
            project: Project specification to execute
            total_budget: Total budget available for the project
            
        Returns:
            Final progress report
        """
        try:
            self.current_project = project
            self.total_budget = total_budget or self.default_budget
            self.status = CoordinatorStatus.DECOMPOSING
            
            logger.info(f"Starting project execution: {project.name}")
            
            # Step 1: Decompose project into sub-projects
            await self._decompose_project(project)
            
            # Step 2: Allocate budget to sub-projects
            await self._allocate_budget()
            
            # Step 3: Spawn sub-coordinators and execute
            await self._execute_sub_projects()
            
            # Step 4: Monitor and aggregate progress
            final_progress = await self._monitor_execution()
            
            self.status = CoordinatorStatus.COMPLETED
            logger.info(f"Project completed: {project.name}")
            
            return final_progress
            
        except Exception as e:
            self.status = CoordinatorStatus.FAILED
            logger.error(f"Project execution failed: {e}")
            raise
    
    async def _decompose_project(self, project: ProjectSpec) -> None:
        """Decompose project into manageable sub-projects"""
        logger.info("Decomposing project into sub-projects")
        
        decomposed_projects = await self.decomposer.decompose(
            project_spec=project,
            max_sub_projects=self.max_concurrent_projects
        )
        
        for sub_proj_data in decomposed_projects:
            sub_project = SubProject(
                id=str(uuid.uuid4()),
                name=sub_proj_data["name"],
                description=sub_proj_data["description"],
                requirements=sub_proj_data["requirements"],
                allocated_budget=0.0,  # Will be set in budget allocation
                estimated_duration=sub_proj_data.get("estimated_duration", 0.0),
                dependencies=sub_proj_data.get("dependencies", []),
                priority=sub_proj_data.get("priority", 1)
            )
            self.sub_projects[sub_project.id] = sub_project
            
        logger.info(f"Created {len(self.sub_projects)} sub-projects")
    
    async def _allocate_budget(self) -> None:
        """Allocate budget across sub-projects"""
        self.status = CoordinatorStatus.ALLOCATING_BUDGET
        logger.info("Allocating budget to sub-projects")
        
        allocations = await self.budget_allocator.allocate(
            sub_projects=list(self.sub_projects.values()),
            total_budget=self.total_budget
        )
        
        for sub_project_id, allocation in allocations.items():
            if sub_project_id in self.sub_projects:
                self.sub_projects[sub_project_id].allocated_budget = allocation
                
        logger.info("Budget allocation completed")
    
    async def _execute_sub_projects(self) -> None:
        """Spawn sub-coordinators and begin execution"""
        self.status = CoordinatorStatus.EXECUTING
        logger.info("Spawning sub-coordinators")
        
        # Create sub-coordinators for each sub-project
        for sub_project in self.sub_projects.values():
            coordinator = await self._spawn_sub_coordinator(sub_project)
            self.sub_coordinators[sub_project.id] = coordinator
            sub_project.coordinator_id = coordinator.id
            
        # Start execution tasks respecting dependencies
        execution_order = self._calculate_execution_order()
        
        for batch in execution_order:
            tasks = []
            for sub_project_id in batch:
                task = asyncio.create_task(
                    self._execute_sub_project(sub_project_id)
                )
                self._execution_tasks[sub_project_id] = task
                tasks.append(task)
            
            # Wait for current batch to complete before starting next
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _spawn_sub_coordinator(self, sub_project: SubProject) -> SubCoordinator:
        """Create and configure a sub-coordinator for a sub-project"""
        coordinator = SubCoordinator(
            project_spec=sub_project,
            budget=sub_project.allocated_budget,
            parent_coordinator_id=self.id
        )
        
        # Configure coordinator based on sub-project requirements
        await coordinator.initialize()
        
        return coordinator
    
    async def _execute_sub_project(self, sub_project_id: str) -> None:
        """Execute a single sub-project via its coordinator"""
        coordinator = self.sub_coordinators[sub_project_id]
        sub_project = self.sub_projects[sub_project_id]
        
        try:
            logger.info(f"Starting execution of sub-project: {sub_project.name}")
            await coordinator.execute()
            logger.info(f"Completed sub-project: {sub_project.name}")
            
        except Exception as e:
            logger.error(f"Sub-project {sub_project.name} failed: {e}")
            raise
    
    def _calculate_execution_order(self) -> List[List[str]]:
        """Calculate execution order respecting dependencies"""
        # Topological sort to respect dependencies
        visited = set()
        temp_visited = set()
        result = []
        
        def dfs(project_id: str, current_batch: List[str]):
            if project_id in temp_visited:
                raise ValueError(f"Circular dependency detected involving {project_id}")
            if project_id in visited:
                return
                
            temp_visited.add(project_id)
            
            # Process dependencies first
            sub_project = self.sub_projects[project_id]
            for dep_id in sub_project.dependencies:
                if dep_id in self.sub_projects:
                    dfs(dep_id, current_batch)
            
            temp_visited.remove(project_id)
            visited.add(project_id)
            current_batch.append(project_id)
        
        # Group projects that can run in parallel
        remaining = set(self.sub_projects.keys())
        batches = []
        
        while remaining:
            current_batch = []
            for project_id in list(remaining):
                sub_project = self.sub_projects[project_id]
                # Check if all dependencies are satisfied
                if all(dep_id in visited for dep_id in sub_project.dependencies):
                    current_batch.append(project_id)
                    remaining.remove(project_id)
                    visited.add(project_id)
            
            if current_batch:
                batches.append(current_batch)
            elif remaining:
                # Handle remaining items with unsatisfied dependencies
                raise ValueError("Unsatisfiable dependencies detected")
        
        return batches
    
    async def _monitor_execution(self) -> MasterProgress:
        """Monitor execution and aggregate progress from sub-coordinators"""
        logger.info("Monitoring execution progress")
        
        while self.status == CoordinatorStatus.EXECUTING:
            progress = await self.get_progress()
            
            # Check if all sub-projects are complete
            if progress.active_sub_projects == 0:
                break
                
            await asyncio.sleep(1.0)  # Poll interval
        
        return await self.get_progress()
    
    async def get_progress(self) -> MasterProgress:
        """Get current aggregated progress"""
        async with self._progress_lock:
            # Collect progress from all sub-coordinators
            sub_progress = {}
            total_completion = 0.0
            active_count = 0
            completed_count = 0
            failed_count = 0
            
            for sub_project_id, coordinator in self.sub_coordinators.items():
                try:
                    coord_progress = await coordinator.get_progress()
                    sub_progress[sub_project_id] = {
                        "completion": coord_progress.completion_percentage,
                        "status": coord_progress.status.value,
                        "budget_used": coord_progress.budget_used,
                        "estimated_completion": coord_progress.estimated_completion_time
                    }
                    
                    total_completion += coord_progress.completion_percentage
                    
                    if coord_progress.status.value == "active":
                        active_count += 1
                    elif coord_progress.status.value == "completed":
                        completed_count += 1
                    elif coord_progress.status.value == "failed":
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to get progress from coordinator {sub_project_id}: {e}")
            
            # Calculate aggregated metrics
            overall_completion = total_completion / len(self.sub_coordinators) if self.sub_coordinators else 0.0
            total_budget_used = sum(
                prog.get("budget_used", 0) for prog in sub_progress.values()
            )
            
            return MasterProgress(
                overall_completion=overall_completion,
                active_sub_projects=active_count,
                completed_sub_projects=completed_count,
                failed_sub_projects=failed_count,
                total_budget_used=total_budget_used,
                estimated_completion_time=self._estimate_completion_time(sub_progress),
                status=self.status,
                sub_project_progress=sub_progress
            )
    
    def _estimate_completion_time(self, sub_progress: Dict[str, Dict[str, Any]]) -> Optional[float]:
        """Estimate overall completion time based on sub-project estimates"""
        estimates = [
            prog.get("estimated_completion") 
            for prog in sub_progress.values() 
            if prog.get("estimated_completion") is not None
        ]
        
        if not estimates:
            return None
            
        # Return the maximum estimate (critical path)
        return max(estimates)
    
    async def pause_execution(self) -> None:
        """Pause all sub-project execution"""
        if self.status == CoordinatorStatus.EXECUTING:
            self.status = CoordinatorStatus.PAUSED
            
            for coordinator in self.sub_coordinators.values():
                await coordinator.pause()
                
            logger.info("Execution paused")
    
    async def resume_execution(self) -> None:
        """Resume paused execution"""
        if self.status == CoordinatorStatus.PAUSED:
            self.status = CoordinatorStatus.EXECUTING
            
            for coordinator in self.sub_coordinators.values():
                await coordinator.resume()
                
            logger.info("Execution resumed")
    
    async def cancel_execution(self) -> None:
        """Cancel all sub-project execution"""
        logger.info("Canceling execution")
        
        # Cancel all running tasks
        for task in self._execution_tasks.values():
            if not task.done():
                task.cancel()
        
        # Cancel sub-coordinators
        for coordinator in self.sub_coordinators.values():
            await coordinator.cancel()
        
        self.status = CoordinatorStatus.FAILED
        logger.info("Execution canceled")
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        await self.cancel_execution()
        
        for coordinator in self.sub_coordinators.values():
            await coordinator.cleanup()
        
        self.sub_coordinators.clear()
        self.sub_projects.clear()
        self._execution_tasks.clear()