"""Quick test of worker spawning functionality."""

import time
from agentcoord import CoordinationClient
from agentcoord.spawner import WorkerSpawner, SpawnMode

print("="*60)
print("WORKER SPAWNING DEMO")
print("="*60)

# Initialize coordinator
print("\n1️⃣  Initializing coordinator...")
coord = CoordinationClient(redis_url="redis://localhost:6379")
coord.register_agent(role="Coordinator", name="TestCoordinator")
print(f"   ✅ Coordinator started in {coord.mode} mode")

# Initialize spawner
print("\n2️⃣  Initializing worker spawner...")
spawner = WorkerSpawner(redis_url="redis://localhost:6379")
print("   ✅ Spawner ready")

# Spawn a worker
print("\n3️⃣  Spawning worker (subprocess mode)...")
try:
    worker1 = spawner.spawn_worker(
        name="TestWorker-1",
        tags=["test"],
        mode=SpawnMode.SUBPROCESS,
        max_tasks=2
    )
    print(f"   ✅ Spawned: {worker1.name}")
    print(f"   Worker ID: {worker1.worker_id}")
    print(f"   Tags: {worker1.tags}")
    print(f"   Mode: {worker1.mode.value}")
except Exception as e:
    print(f"   ❌ Spawn failed: {e}")
    worker1 = None

# Check if worker is alive
if worker1:
    print("\n4️⃣  Checking worker status...")
    time.sleep(2)
    print(f"   Worker alive: {worker1.is_alive()}")

# Get fleet stats
print("\n5️⃣  Fleet statistics...")
stats = spawner.get_worker_stats()
print(f"   Total spawned: {stats['total_spawned']}")
print(f"   Alive: {stats['alive']}")
print(f"   Dead: {stats['dead']}")

# Spawn another worker
print("\n6️⃣  Spawning second worker...")
try:
    worker2 = spawner.spawn_worker(
        name="TestWorker-2",
        tags=["backend"],
        mode=SpawnMode.SUBPROCESS,
        max_tasks=2
    )
    print(f"   ✅ Spawned: {worker2.name}")
except Exception as e:
    print(f"   ❌ Spawn failed: {e}")
    worker2 = None

# Final stats
print("\n7️⃣  Final fleet status...")
stats = spawner.get_worker_stats()
print(f"   Total spawned: {stats['total_spawned']}")
print(f"   Alive: {stats['alive']}")

for w in stats['workers']:
    status = "✅" if w['alive'] else "❌"
    print(f"   {status} {w['name']} | tags: {w['tags']}")

# Cleanup
print("\n8️⃣  Cleaning up...")
time.sleep(3)
spawner.terminate_all()
coord.shutdown()
print("   ✅ All workers terminated")

print("\n" + "="*60)
print("DEMO COMPLETE")
print("="*60)
print("\nKey takeaways:")
print("  ✓ Coordinator can spawn workers programmatically")
print("  ✓ Workers run as independent subprocesses")
print("  ✓ Fleet can be monitored and managed")
print("  ✓ Workers can be terminated gracefully")
