#!/usr/bin/env python3
"""
Coordinator script to spawn LLM workers for UI integration tasks.
"""

import os
import sys
import time
from agentcoord.spawner import WorkerSpawner, SpawnMode

# Get API key
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    # Try Janus Engine .env
    janus_env = os.path.expanduser('~/Desktop/Janus_Engine/.env')
    if os.path.exists(janus_env):
        with open(janus_env) as f:
            for line in f:
                if line.startswith('ANTHROPIC_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    os.environ['ANTHROPIC_API_KEY'] = api_key
                    break

if not api_key:
    print("❌ ANTHROPIC_API_KEY not found")
    print("   Set it in environment or ~/Desktop/Janus_Engine/.env")
    sys.exit(1)

print("🤖 AgentCoord UI Integration Coordinator")
print("=" * 60)
print("\n📋 8 UI integration tasks created")
print("🚀 Spawning 3 LLM-powered workers...\n")

# Initialize spawner
spawner = WorkerSpawner(redis_url='redis://localhost:6379')

# Spawn 3 LLM workers
workers = []
for i in range(3):
    worker = spawner.spawn_worker(
        name=f"UI-Worker-{i+1}",
        tags=['ui', 'cli', 'integration', 'bugfix', 'dashboard'],
        mode=SpawnMode.SUBPROCESS,
        max_tasks=3,  # Each worker handles up to 3 tasks
        poll_interval=5,
        use_llm=True
    )
    workers.append(worker)
    print(f"  ✅ Spawned {worker.name}")

print(f"\n✅ {len(workers)} LLM workers active")
print("\n📊 Monitor progress:")
print("   agentcoord tasks          # View task queue")
print("   agentcoord status         # View agent status")
print("   agentcoord dashboard      # Live dashboard (after CLI updated)")
print("\n⏳ Workers will auto-complete tasks and stop when done")
print("   Press Ctrl+C to stop this coordinator (workers continue)\n")

try:
    # Monitor workers
    while True:
        alive = spawner.count_alive_workers()
        if alive == 0:
            print("\n✅ All workers finished!")
            break

        print(f"\r⚡ {alive} workers still running...", end='', flush=True)
        time.sleep(5)

except KeyboardInterrupt:
    print("\n\n⚠️  Coordinator stopped (workers continue in background)")
    print(f"   {spawner.count_alive_workers()} workers still active\n")

finally:
    # Cleanup dead workers
    spawner.cleanup_dead_workers()

print("\n✨ UI integration complete!")
print("   Try: agentcoord dashboard\n")
