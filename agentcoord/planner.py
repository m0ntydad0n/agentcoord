"""
Interactive Planning Module for AgentCoord.

Analyzes tasks, estimates costs, and generates execution plans
with user preferences for cost/quality optimization.
"""

import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OptimizationMode(str, Enum):
    """User preference for planning optimization."""
    COST = "cost"  # Minimize cost, use smaller models
    QUALITY = "quality"  # Maximize quality, use best models
    BALANCED = "balanced"  # Balance cost and quality


class ModelTier(str, Enum):
    """LLM model tiers for task assignment."""
    HAIKU = "claude-haiku-4.5"  # Fast, cheap, simple tasks
    SONNET = "claude-sonnet-4.5"  # Balanced, most tasks
    OPUS = "claude-opus-4.6"  # Best quality, complex tasks


@dataclass
class TaskComplexity:
    """Complexity analysis for a task."""
    task_id: str
    title: str
    description: str

    # Complexity scores (0-10)
    reasoning_depth: int  # How much reasoning required
    file_count: int  # Estimated files to modify
    dependency_complexity: int  # How complex are dependencies
    risk_level: int  # Risk of breaking things

    # Derived metrics
    total_complexity: int  # Sum of scores
    recommended_model: ModelTier
    estimated_tokens: int
    estimated_cost: float
    estimated_duration_minutes: int

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['recommended_model'] = self.recommended_model.value
        return d


@dataclass
class ExecutionPlan:
    """A complete execution plan for multi-agent coordination."""
    plan_id: str
    optimization_mode: OptimizationMode

    # Task analysis
    total_tasks: int
    task_complexities: List[TaskComplexity]

    # Resource planning
    recommended_agents: int
    model_distribution: Dict[str, int]  # ModelTier -> count

    # Cost estimates
    total_estimated_tokens: int
    total_estimated_cost: float
    total_estimated_duration_minutes: int

    # Budget constraints
    budget_limit: Optional[float] = None
    within_budget: bool = True

    # Parallelization
    parallel_groups: List[List[str]] = None  # Groups of task IDs that can run in parallel

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['optimization_mode'] = self.optimization_mode.value
        d['task_complexities'] = [tc.to_dict() for tc in self.task_complexities]
        return d


class TaskPlanner:
    """
    Analyzes tasks and generates optimized execution plans.

    Uses heuristics and cost models to recommend:
    - Number of agents to spawn
    - Which model to use for each task
    - Parallel execution groups
    - Total cost and time estimates
    """

    # Model pricing (per 1M tokens, rough estimates)
    MODEL_PRICING = {
        ModelTier.HAIKU: 0.25,  # $0.25 per 1M tokens
        ModelTier.SONNET: 3.00,  # $3.00 per 1M tokens
        ModelTier.OPUS: 15.00,  # $15.00 per 1M tokens
    }

    # Average tokens per task by complexity
    TOKENS_BY_COMPLEXITY = {
        "simple": 5000,      # 0-15 complexity
        "moderate": 20000,   # 16-30 complexity
        "complex": 50000,    # 31+ complexity
    }

    def __init__(self):
        """Initialize task planner."""
        pass

    def analyze_task_complexity(self, task: Dict) -> TaskComplexity:
        """
        Analyze a single task to determine complexity.

        Args:
            task: Task dictionary with title, description, etc.

        Returns:
            TaskComplexity analysis
        """
        title = task.get('title', '')
        description = task.get('description', '')
        tags = task.get('tags', [])

        # Heuristic scoring (0-10 each)
        reasoning_depth = self._score_reasoning_depth(title, description)
        file_count = self._estimate_file_count(title, description)
        dependency_complexity = self._score_dependencies(task.get('depends_on', []))
        risk_level = self._score_risk(title, description, tags)

        total_complexity = reasoning_depth + file_count + dependency_complexity + risk_level

        # Recommend model based on total complexity
        if total_complexity <= 15:
            recommended_model = ModelTier.HAIKU
            category = "simple"
        elif total_complexity <= 30:
            recommended_model = ModelTier.SONNET
            category = "moderate"
        else:
            recommended_model = ModelTier.OPUS
            category = "complex"

        # Estimate tokens and cost
        estimated_tokens = self.TOKENS_BY_COMPLEXITY[category]
        estimated_cost = (estimated_tokens / 1_000_000) * self.MODEL_PRICING[recommended_model]

        # Estimate duration (rough: 1 minute per 1000 tokens)
        estimated_duration_minutes = max(5, estimated_tokens // 1000)

        return TaskComplexity(
            task_id=task.get('id', 'unknown'),
            title=title,
            description=description,
            reasoning_depth=reasoning_depth,
            file_count=file_count,
            dependency_complexity=dependency_complexity,
            risk_level=risk_level,
            total_complexity=total_complexity,
            recommended_model=recommended_model,
            estimated_tokens=estimated_tokens,
            estimated_cost=estimated_cost,
            estimated_duration_minutes=estimated_duration_minutes
        )

    def _score_reasoning_depth(self, title: str, description: str) -> int:
        """Score how much reasoning is required (0-10)."""
        text = f"{title} {description}".lower()

        # Keywords indicating complex reasoning
        high_reasoning = ['architecture', 'design', 'algorithm', 'optimize', 'refactor', 'analyze']
        medium_reasoning = ['implement', 'integrate', 'modify', 'update', 'enhance']
        low_reasoning = ['add', 'fix', 'update', 'change', 'document']

        if any(kw in text for kw in high_reasoning):
            return 8
        elif any(kw in text for kw in medium_reasoning):
            return 5
        elif any(kw in text for kw in low_reasoning):
            return 2
        return 3

    def _estimate_file_count(self, title: str, description: str) -> int:
        """Estimate number of files to modify (0-10)."""
        text = f"{title} {description}".lower()

        # Keywords indicating file scope
        if any(kw in text for kw in ['system', 'framework', 'architecture', 'refactor']):
            return 8  # Multiple files
        elif any(kw in text for kw in ['module', 'component', 'feature']):
            return 5  # A few files
        elif any(kw in text for kw in ['function', 'method', 'class']):
            return 2  # Single file
        return 3

    def _score_dependencies(self, depends_on: List[str]) -> int:
        """Score dependency complexity (0-10)."""
        dep_count = len(depends_on) if depends_on else 0
        return min(10, dep_count * 3)

    def _score_risk(self, title: str, description: str, tags: List[str]) -> int:
        """Score risk level (0-10)."""
        text = f"{title} {description}".lower()

        high_risk = ['database', 'migration', 'security', 'auth', 'payment', 'production']
        medium_risk = ['api', 'integration', 'deployment']

        if any(kw in text for kw in high_risk):
            return 8
        elif any(kw in text for kw in medium_risk):
            return 5
        return 2

    def create_execution_plan(
        self,
        tasks: List[Dict],
        optimization_mode: OptimizationMode = OptimizationMode.BALANCED,
        budget_limit: Optional[float] = None,
        max_agents: int = 10
    ) -> ExecutionPlan:
        """
        Create optimized execution plan for tasks.

        Args:
            tasks: List of task dictionaries
            optimization_mode: User preference for cost/quality
            budget_limit: Optional budget limit in dollars
            max_agents: Maximum agents to spawn

        Returns:
            ExecutionPlan with recommendations
        """
        # Analyze each task
        complexities = [self.analyze_task_complexity(task) for task in tasks]

        # Apply optimization mode adjustments
        if optimization_mode == OptimizationMode.COST:
            # Downgrade models where possible
            for tc in complexities:
                if tc.recommended_model == ModelTier.OPUS:
                    tc.recommended_model = ModelTier.SONNET
                elif tc.recommended_model == ModelTier.SONNET and tc.total_complexity < 20:
                    tc.recommended_model = ModelTier.HAIKU
                # Recalculate cost
                tc.estimated_cost = (tc.estimated_tokens / 1_000_000) * self.MODEL_PRICING[tc.recommended_model]

        elif optimization_mode == OptimizationMode.QUALITY:
            # Upgrade models where it helps
            for tc in complexities:
                if tc.recommended_model == ModelTier.HAIKU and tc.total_complexity > 10:
                    tc.recommended_model = ModelTier.SONNET
                elif tc.recommended_model == ModelTier.SONNET and tc.total_complexity > 25:
                    tc.recommended_model = ModelTier.OPUS
                # Recalculate cost
                tc.estimated_cost = (tc.estimated_tokens / 1_000_000) * self.MODEL_PRICING[tc.recommended_model]

        # Calculate totals
        total_tokens = sum(tc.estimated_tokens for tc in complexities)
        total_cost = sum(tc.estimated_cost for tc in complexities)

        # Determine parallelization groups
        parallel_groups = self._plan_parallelization(tasks, complexities)

        # Calculate duration (parallel groups run concurrently)
        total_duration = sum(
            max(complexities[i].estimated_duration_minutes for i in range(len(tasks)) if tasks[i]['id'] in group)
            for group in parallel_groups
        )

        # Determine optimal agent count
        # Simple heuristic: 2 tasks per agent, but respect parallel groups
        recommended_agents = min(
            max_agents,
            max(len(parallel_groups[0]) if parallel_groups else 1, (len(tasks) + 1) // 2)
        )

        # Model distribution
        model_distribution = {
            ModelTier.HAIKU.value: sum(1 for tc in complexities if tc.recommended_model == ModelTier.HAIKU),
            ModelTier.SONNET.value: sum(1 for tc in complexities if tc.recommended_model == ModelTier.SONNET),
            ModelTier.OPUS.value: sum(1 for tc in complexities if tc.recommended_model == ModelTier.OPUS),
        }

        # Budget check
        within_budget = True
        if budget_limit is not None and total_cost > budget_limit:
            within_budget = False
            logger.warning(f"Plan exceeds budget: ${total_cost:.2f} > ${budget_limit:.2f}")

        plan_id = f"plan-{len(tasks)}-tasks"

        return ExecutionPlan(
            plan_id=plan_id,
            optimization_mode=optimization_mode,
            total_tasks=len(tasks),
            task_complexities=complexities,
            recommended_agents=recommended_agents,
            model_distribution=model_distribution,
            total_estimated_tokens=total_tokens,
            total_estimated_cost=total_cost,
            total_estimated_duration_minutes=total_duration,
            budget_limit=budget_limit,
            within_budget=within_budget,
            parallel_groups=parallel_groups
        )

    def _plan_parallelization(self, tasks: List[Dict], complexities: List[TaskComplexity]) -> List[List[str]]:
        """
        Plan parallel execution groups based on dependencies.

        Returns:
            List of groups, where each group contains task IDs that can run in parallel
        """
        # Build dependency graph
        task_deps = {task['id']: set(task.get('depends_on', [])) for task in tasks}
        task_ids = [task['id'] for task in tasks]

        # Topological sort into levels (simple version)
        groups = []
        remaining = set(task_ids)

        while remaining:
            # Find tasks with no unmet dependencies
            ready = {
                tid for tid in remaining
                if not (task_deps[tid] & remaining)  # No dependencies in remaining
            }

            if not ready:
                # Circular dependency or error, just add all remaining
                groups.append(list(remaining))
                break

            groups.append(list(ready))
            remaining -= ready

        return groups if groups else [[tid] for tid in task_ids]


def format_plan_summary(plan: ExecutionPlan) -> str:
    """Format execution plan as human-readable summary."""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"EXECUTION PLAN: {plan.plan_id}")
    lines.append(f"{'='*60}\n")

    lines.append(f"Optimization Mode: {plan.optimization_mode.value.upper()}")
    lines.append(f"Total Tasks: {plan.total_tasks}")
    lines.append(f"Recommended Agents: {plan.recommended_agents}\n")

    lines.append(f"Cost Estimate: ${plan.total_estimated_cost:.2f}")
    lines.append(f"Time Estimate: ~{plan.total_estimated_duration_minutes} minutes")
    lines.append(f"Token Estimate: {plan.total_estimated_tokens:,}\n")

    if plan.budget_limit:
        status = "✅ WITHIN BUDGET" if plan.within_budget else "❌ OVER BUDGET"
        lines.append(f"Budget: ${plan.budget_limit:.2f} - {status}\n")

    lines.append(f"Model Distribution:")
    for model, count in plan.model_distribution.items():
        if count > 0:
            lines.append(f"  {model}: {count} tasks")

    lines.append(f"\nParallel Execution Groups:")
    for i, group in enumerate(plan.parallel_groups or [], 1):
        lines.append(f"  Wave {i}: {len(group)} tasks can run in parallel")

    lines.append(f"\nTask Breakdown:")
    for tc in plan.task_complexities:
        lines.append(f"  [{tc.recommended_model.value}] {tc.title}")
        lines.append(f"      Complexity: {tc.total_complexity}/40 | Cost: ${tc.estimated_cost:.3f} | Time: ~{tc.estimated_duration_minutes}min")

    lines.append(f"\n{'='*60}\n")

    return '\n'.join(lines)
