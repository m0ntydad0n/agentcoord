"""Tests for the task planning module."""

import pytest
from agentcoord.planner import (
    TaskPlanner,
    TaskComplexity,
    ExecutionPlan,
    OptimizationMode,
    ModelTier
)


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            'id': 'task-1',
            'title': 'Add user authentication',
            'description': 'Implement JWT authentication with secure password hashing',
            'depends_on': [],
            'tags': ['auth', 'security']
        },
        {
            'id': 'task-2',
            'title': 'Write unit tests',
            'description': 'Add unit tests for auth module',
            'depends_on': ['task-1'],
            'tags': ['testing']
        },
        {
            'id': 'task-3',
            'title': 'Update documentation',
            'description': 'Document new auth endpoints',
            'depends_on': ['task-1'],
            'tags': ['docs']
        },
    ]


def test_task_complexity_analysis():
    """Test complexity analysis for individual tasks."""
    planner = TaskPlanner()

    # High complexity task
    complex_task = {
        'id': 'task-1',
        'title': 'Refactor database architecture',
        'description': 'Redesign the database schema to optimize query performance across the entire system',
        'depends_on': [],
        'tags': []
    }

    complexity = planner.analyze_task_complexity(complex_task)

    assert isinstance(complexity, TaskComplexity)
    assert complexity.total_complexity > 20
    assert complexity.recommended_model in [ModelTier.SONNET, ModelTier.OPUS]
    assert complexity.estimated_cost > 0
    assert complexity.estimated_tokens > 0


def test_simple_task_analysis():
    """Test that simple tasks get assigned cheaper models."""
    planner = TaskPlanner()

    simple_task = {
        'id': 'task-1',
        'title': 'Fix typo in README',
        'description': 'Update README to fix a typo',
        'depends_on': [],
        'tags': []
    }

    complexity = planner.analyze_task_complexity(simple_task)

    assert complexity.total_complexity < 20
    assert complexity.recommended_model == ModelTier.HAIKU
    assert complexity.estimated_cost < 0.01


def test_execution_plan_creation(sample_tasks):
    """Test creating execution plan from tasks."""
    planner = TaskPlanner()

    plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.BALANCED,
        max_agents=5
    )

    assert isinstance(plan, ExecutionPlan)
    assert plan.total_tasks == len(sample_tasks)
    assert len(plan.task_complexities) == len(sample_tasks)
    assert plan.recommended_agents > 0
    assert plan.total_estimated_cost > 0
    assert plan.total_estimated_tokens > 0


def test_cost_optimization_mode(sample_tasks):
    """Test that cost mode reduces costs."""
    planner = TaskPlanner()

    balanced_plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.BALANCED
    )

    cost_plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.COST
    )

    # Cost mode should be cheaper or equal
    assert cost_plan.total_estimated_cost <= balanced_plan.total_estimated_cost


def test_quality_optimization_mode(sample_tasks):
    """Test that quality mode uses better models."""
    planner = TaskPlanner()

    balanced_plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.BALANCED
    )

    quality_plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.QUALITY
    )

    # Quality mode should use more expensive models
    assert quality_plan.total_estimated_cost >= balanced_plan.total_estimated_cost


def test_budget_constraint(sample_tasks):
    """Test budget constraint checking."""
    planner = TaskPlanner()

    # Plan with tight budget
    plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.BALANCED,
        budget_limit=0.01  # Very low budget
    )

    # Should detect budget exceeded
    assert plan.within_budget is False
    assert plan.budget_limit == 0.01


def test_parallelization_planning():
    """Test that parallel groups respect dependencies."""
    planner = TaskPlanner()

    tasks = [
        {'id': 'task-1', 'title': 'Task 1', 'description': 'First', 'depends_on': [], 'tags': []},
        {'id': 'task-2', 'title': 'Task 2', 'description': 'Second', 'depends_on': [], 'tags': []},
        {'id': 'task-3', 'title': 'Task 3', 'description': 'Third', 'depends_on': ['task-1'], 'tags': []},
        {'id': 'task-4', 'title': 'Task 4', 'description': 'Fourth', 'depends_on': ['task-1', 'task-2'], 'tags': []},
    ]

    plan = planner.create_execution_plan(tasks=tasks)

    # Should have multiple waves
    assert len(plan.parallel_groups) > 1

    # First wave should have independent tasks
    first_wave = set(plan.parallel_groups[0])
    assert 'task-1' in first_wave
    assert 'task-2' in first_wave

    # Later waves should have dependent tasks
    later_waves = set()
    for group in plan.parallel_groups[1:]:
        later_waves.update(group)
    assert 'task-3' in later_waves
    assert 'task-4' in later_waves


def test_model_distribution(sample_tasks):
    """Test model distribution tracking."""
    planner = TaskPlanner()

    plan = planner.create_execution_plan(
        tasks=sample_tasks,
        optimization_mode=OptimizationMode.BALANCED
    )

    # Should have distribution counts
    assert isinstance(plan.model_distribution, dict)
    assert ModelTier.HAIKU.value in plan.model_distribution
    assert ModelTier.SONNET.value in plan.model_distribution
    assert ModelTier.OPUS.value in plan.model_distribution

    # Total should equal number of tasks
    total = sum(plan.model_distribution.values())
    assert total == len(sample_tasks)


def test_agent_count_recommendation(sample_tasks):
    """Test recommended agent count is reasonable."""
    planner = TaskPlanner()

    plan = planner.create_execution_plan(
        tasks=sample_tasks,
        max_agents=10
    )

    # Should recommend at least 1 agent
    assert plan.recommended_agents >= 1

    # Should not exceed max
    assert plan.recommended_agents <= 10

    # Should not exceed number of tasks
    assert plan.recommended_agents <= len(sample_tasks)


def test_complexity_scoring():
    """Test that complexity scoring produces reasonable values."""
    planner = TaskPlanner()

    # Test various task types
    tasks = [
        {'title': 'Fix typo', 'description': 'Update README'},
        {'title': 'Add feature', 'description': 'Implement new API endpoint'},
        {'title': 'Refactor system', 'description': 'Redesign database architecture'},
    ]

    complexities = []
    for task in tasks:
        task['id'] = f"task-{len(complexities)}"
        task['depends_on'] = []
        task['tags'] = []
        c = planner.analyze_task_complexity(task)
        complexities.append(c.total_complexity)

    # Should be in ascending order of complexity
    assert complexities[0] < complexities[1] < complexities[2]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
