"""Quick test of Alpha MVP functionality."""

import redis
from agentcoord.tasks import TaskQueue
from agentcoord.planner import TaskPlanner, OptimizationMode, format_plan_summary

# Connect to Redis
redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
redis_client.ping()

# Clear existing tasks
redis_client.flushdb()
print("✅ Redis cleared")

# Create sample tasks
task_queue = TaskQueue(redis_client)

tasks_to_create = [
    {
        'title': 'Implement user authentication system',
        'description': 'Add JWT-based auth with login/logout, password hashing, and session management',
        'priority': 5,
        'tags': ['auth', 'security']
    },
    {
        'title': 'Create database schema for users',
        'description': 'Design and implement users table with proper indexes',
        'priority': 4,
        'tags': ['database']
    },
    {
        'title': 'Build user profile API endpoints',
        'description': 'CRUD endpoints for user profile management',
        'priority': 3,
        'tags': ['api']
    },
    {
        'title': 'Add rate limiting to API',
        'description': 'Implement Redis-based rate limiting to prevent abuse',
        'priority': 3,
        'tags': ['api', 'security']
    },
]

print(f"\n📋 Creating {len(tasks_to_create)} sample tasks...")
created_tasks = []
for task_data in tasks_to_create:
    task = task_queue.create_task(**task_data)
    created_tasks.append(task)
    print(f"   ✅ {task.title}")

print(f"\n✅ Created {len(created_tasks)} tasks in Redis")

# Get pending tasks
pending = task_queue.list_pending_tasks()
print(f"\n📊 Pending tasks: {len(pending)}")

# Create execution plan
print("\n🧠 Generating execution plans...\n")

planner = TaskPlanner()
tasks_dict = [
    {
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'depends_on': t.depends_on or [],
        'tags': t.tags or []
    }
    for t in pending
]

# Test all three optimization modes
modes = [
    (OptimizationMode.COST, "💰 Cost Optimization"),
    (OptimizationMode.BALANCED, "⚖️  Balanced Optimization"),
    (OptimizationMode.QUALITY, "🏆 Quality Optimization")
]

for mode, label in modes:
    plan = planner.create_execution_plan(
        tasks=tasks_dict,
        optimization_mode=mode,
        max_agents=5
    )

    print(f"{label}:")
    print(f"   Cost: ${plan.total_estimated_cost:.2f}")
    print(f"   Time: ~{plan.total_estimated_duration_minutes} min")
    print(f"   Agents: {plan.recommended_agents}")
    print(f"   Models: {sum(1 for m,c in plan.model_distribution.items() if c > 0)} different tiers")
    print()

print("=" * 60)
print("✅ Alpha MVP Test Complete!")
print("=" * 60)
print("\nNow try the interactive CLI:")
print("   agentcoord-plan plan")
print("   agentcoord-plan estimate")
print()
print("Or view the tasks:")
print("   agentcoord tasks")
print()
