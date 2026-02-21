"""Full end-to-end demo: Coordinator creates tasks and spawns workers."""

import time
from agentcoord import CoordinationClient
from agentcoord.spawner import WorkerSpawner, SpawnMode
from agentcoord.tasks import TaskQueue

print("\n" + "="*70)
print(" FULL ORCHESTRATION DEMO: Coordinator + Workers + Tasks")
print("="*70)

# Step 1: Start coordinator
print("\n📋 STEP 1: Initialize Coordinator")
print("-" * 70)
coord = CoordinationClient(redis_url="redis://localhost:6379")
coord.register_agent(role="Coordinator", name="MainCoordinator", working_on="Orchestrating demo")
print(f"✅ Coordinator started in {coord.mode} mode")

# Step 2: Create tasks
print("\n📝 STEP 2: Create Task Queue")
print("-" * 70)

if coord.mode == "redis" and coord.redis_client:
    task_queue = TaskQueue(coord.redis_client)

    tasks_to_create = [
        {"title": "Process user data", "priority": 5, "tags": ["backend"]},
        {"title": "Generate report", "priority": 4, "tags": ["backend"]},
        {"title": "Send notifications", "priority": 3, "tags": ["backend"]},
        {"title": "Update dashboard", "priority": 4, "tags": ["frontend"]},
        {"title": "Cleanup old files", "priority": 2, "tags": ["maintenance"]},
    ]

    for task_def in tasks_to_create:
        task = task_queue.create_task(
            title=task_def["title"],
            description=f"Demo task: {task_def['title']}",
            priority=task_def["priority"],
            tags=task_def["tags"]
        )
        print(f"  📌 Created: {task.title} (priority: {task.priority}, tags: {task.tags})")

    print(f"\n✅ Created {len(tasks_to_create)} tasks")
else:
    print("⚠️  Redis not available - skipping task creation")
    print("  (Tasks require Redis for queue management)")

# Step 3: Spawn workers
print("\n🤖 STEP 3: Spawn Worker Fleet")
print("-" * 70)

spawner = WorkerSpawner(redis_url="redis://localhost:6379")

workers_config = [
    {"name": "BackendWorker-1", "tags": ["backend"], "max_tasks": 2},
    {"name": "BackendWorker-2", "tags": ["backend"], "max_tasks": 2},
    {"name": "FrontendWorker", "tags": ["frontend"], "max_tasks": 1},
    {"name": "GeneralistWorker", "tags": [], "max_tasks": 2},  # Claims any task
]

spawned_workers = []
for config in workers_config:
    try:
        worker = spawner.spawn_worker(
            name=config["name"],
            tags=config["tags"],
            mode=SpawnMode.SUBPROCESS,
            max_tasks=config["max_tasks"]
        )
        spawned_workers.append(worker)
        tags_str = f"tags: {config['tags']}" if config['tags'] else "all tags"
        print(f"  ✅ Spawned: {worker.name} ({tags_str})")
    except Exception as e:
        print(f"  ❌ Failed to spawn {config['name']}: {e}")

print(f"\n✅ Spawned {len(spawned_workers)} workers")

# Step 4: Monitor execution
print("\n👀 STEP 4: Monitor Execution")
print("-" * 70)
print("Workers are now claiming and executing tasks...")
print("(Workers will run for ~10-15 seconds)\n")

for i in range(3):
    time.sleep(3)
    stats = spawner.get_worker_stats()
    alive = stats['alive']
    print(f"  [{i*3:2d}s] Workers alive: {alive}/{stats['total_spawned']}")

    if coord.mode == "redis" and coord.redis_client:
        all_tasks = task_queue.list_tasks()
        completed = sum(1 for t in all_tasks if t.status.value == "completed")
        in_progress = sum(1 for t in all_tasks if t.status.value == "in_progress")
        pending = sum(1 for t in all_tasks if t.status.value == "pending")
        print(f"       Tasks: {completed} completed, {in_progress} in progress, {pending} pending")

# Step 5: View results
print("\n📊 STEP 5: Final Results")
print("-" * 70)

if coord.mode == "redis" and coord.redis_client:
    all_tasks = task_queue.list_tasks()
    completed_tasks = [t for t in all_tasks if t.status.value == "completed"]

    print(f"\nCompleted tasks: {len(completed_tasks)}/{len(all_tasks)}")
    for task in completed_tasks:
        print(f"  ✅ {task.title}")

    # Show incomplete
    incomplete = [t for t in all_tasks if t.status.value != "completed"]
    if incomplete:
        print(f"\nIncomplete tasks: {len(incomplete)}")
        for task in incomplete:
            print(f"  ⏳ {task.title} ({task.status.value})")

# Step 6: Cleanup
print("\n🧹 STEP 6: Cleanup")
print("-" * 70)
time.sleep(2)
spawner.terminate_all()
coord.shutdown()
print("✅ All workers terminated")
print("✅ Coordinator shutdown")

print("\n" + "="*70)
print(" DEMO COMPLETE - Full Orchestration Cycle")
print("="*70)
print("\n✨ Summary:")
print("  • Coordinator created 5 tasks with different priorities and tags")
print("  • Spawned 4 workers with different specializations")
print("  • Workers autonomously claimed and executed tasks")
print("  • System monitored execution in real-time")
print("  • Clean shutdown of entire fleet")
print("\n💡 This demonstrates:")
print("  → Dynamic worker spawning")
print("  → Task-based coordination")
print("  → Heterogeneous worker pools (different tags)")
print("  → Lifecycle management (spawn → execute → terminate)")
print("  → Full orchestrator pattern\n")
