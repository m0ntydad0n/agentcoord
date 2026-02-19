"""
Demo: Interactive Planning with Cost Estimation.

Shows how the planner analyzes tasks and generates optimized execution plans.
"""

import sys
import os

# Add agentcoord to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agentcoord.planner import TaskPlanner, OptimizationMode, format_plan_summary


def demo_planning():
    """Demonstrate task planning with different optimization modes."""

    # Sample tasks
    tasks = [
        {
            'id': 'task-1',
            'title': 'Add user authentication system',
            'description': 'Implement JWT-based authentication with login/logout endpoints, password hashing, and session management',
            'depends_on': [],
            'tags': ['auth', 'security']
        },
        {
            'id': 'task-2',
            'title': 'Create database migration for users table',
            'description': 'Add users table with email, password_hash, created_at fields. Include indexes.',
            'depends_on': [],
            'tags': ['database', 'migration']
        },
        {
            'id': 'task-3',
            'title': 'Build user profile API endpoints',
            'description': 'CRUD endpoints for user profiles (GET, PUT, DELETE)',
            'depends_on': ['task-1', 'task-2'],
            'tags': ['api']
        },
        {
            'id': 'task-4',
            'title': 'Write unit tests for auth module',
            'description': 'Test coverage for login, logout, token validation, password hashing',
            'depends_on': ['task-1'],
            'tags': ['testing']
        },
        {
            'id': 'task-5',
            'title': 'Add rate limiting to API',
            'description': 'Implement Redis-based rate limiting for API endpoints to prevent abuse',
            'depends_on': ['task-3'],
            'tags': ['api', 'security']
        },
        {
            'id': 'task-6',
            'title': 'Update API documentation',
            'description': 'Document new auth endpoints in OpenAPI spec',
            'depends_on': ['task-1', 'task-3'],
            'tags': ['docs']
        },
    ]

    planner = TaskPlanner()

    print("\n" + "="*70)
    print("AgentCoord Planning Demo: Cost vs Quality Optimization")
    print("="*70)

    print(f"\n📋 Analyzing {len(tasks)} tasks:\n")
    for task in tasks:
        deps = f" (depends on: {', '.join(task['depends_on'])})" if task['depends_on'] else ""
        print(f"  • {task['title']}{deps}")

    # Generate plans with different optimization modes
    modes = [
        (OptimizationMode.COST, "Minimize cost (use smaller models)"),
        (OptimizationMode.BALANCED, "Balance cost and quality"),
        (OptimizationMode.QUALITY, "Maximize quality (use best models)")
    ]

    for mode, description in modes:
        print(f"\n\n{'='*70}")
        print(f"📊 {description.upper()}")
        print(f"{'='*70}")

        plan = planner.create_execution_plan(
            tasks=tasks,
            optimization_mode=mode,
            budget_limit=None,
            max_agents=5
        )

        # Show summary
        print(f"\n💰 Cost Estimate: ${plan.total_estimated_cost:.2f}")
        print(f"⏱️  Time Estimate: ~{plan.total_estimated_duration_minutes} minutes")
        print(f"🤖 Recommended Agents: {plan.recommended_agents}")

        print(f"\n📦 Model Distribution:")
        for model, count in plan.model_distribution.items():
            if count > 0:
                print(f"   {model}: {count} tasks")

        print(f"\n🔀 Parallel Execution:")
        for i, group in enumerate(plan.parallel_groups, 1):
            print(f"   Wave {i}: {len(group)} task{'s' if len(group) != 1 else ''} in parallel")

        print(f"\n📝 Task Assignments:")
        for tc in plan.task_complexities:
            complexity_bar = "█" * (tc.total_complexity // 4) + "░" * (10 - tc.total_complexity // 4)
            print(f"   [{tc.recommended_model.value:20}] {tc.title}")
            print(f"      Complexity: {complexity_bar} {tc.total_complexity}/40")
            print(f"      Cost: ${tc.estimated_cost:.3f} | Time: ~{tc.estimated_duration_minutes} min")

    # Budget constraint demo
    print(f"\n\n{'='*70}")
    print(f"💸 BUDGET CONSTRAINT DEMO")
    print(f"{'='*70}")

    budget_scenarios = [
        (5.00, "Low budget"),
        (10.00, "Medium budget"),
        (20.00, "High budget")
    ]

    for budget, label in budget_scenarios:
        plan = planner.create_execution_plan(
            tasks=tasks,
            optimization_mode=OptimizationMode.BALANCED,
            budget_limit=budget,
            max_agents=5
        )

        status = "✅ WITHIN BUDGET" if plan.within_budget else "❌ OVER BUDGET"
        overage = max(0, plan.total_estimated_cost - budget)

        print(f"\n{label.upper()}: ${budget:.2f} budget")
        print(f"   Estimated: ${plan.total_estimated_cost:.2f} - {status}")
        if not plan.within_budget:
            print(f"   Overage: ${overage:.2f}")

    print("\n" + "="*70)
    print("💡 Demo complete!")
    print("\nNext steps:")
    print("  1. Install: pip install -e .")
    print("  2. Create tasks in Redis")
    print("  3. Run: agentcoord-plan plan")
    print("  4. Watch agents execute your plan!")
    print("="*70 + "\n")


if __name__ == '__main__':
    demo_planning()
