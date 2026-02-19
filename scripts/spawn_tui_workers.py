#!/usr/bin/env python3
"""
Coordinator script to spawn LLM workers for building the interactive TUI.

This time we're building the REAL interactive interface where users can
actually create tasks, manage agents, and control the system.
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

print("🤖 AgentCoord Interactive TUI Build Coordinator")
print("=" * 60)
print("\n📋 10 interactive UX tasks created")
print("🎯 Goal: Build a REAL TUI where users can actually DO things")
print("🚀 Spawning 4 LLM-powered workers...\n")

# Initialize spawner
spawner = WorkerSpawner(redis_url='redis://localhost:6379')

# Spawn 4 LLM workers (more workers for faster completion)
workers = []
for i in range(4):
    worker = spawner.spawn_worker(
        name=f"TUI-Worker-{i+1}",
        tags=['tui', 'ux', 'interaction', 'keyboard', 'forms', 'modal'],
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
print("   agentcoord dashboard      # Live dashboard")
print("\n⏳ Workers will build the interactive TUI")
print("   Estimated time: 20-30 minutes")
print("   Estimated cost: $3-5")
print("\n   Press Ctrl+C to stop coordinator (workers continue)\n")

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

print("\n✨ Interactive TUI build complete!")
print("   Try: agentcoord  # (launches TUI)\n")
