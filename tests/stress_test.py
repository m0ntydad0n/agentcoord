"""Stress test for agentcoord - simulates multiple concurrent agents."""

import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from agentcoord import CoordinationClient, LockAcquireTimeout
import random
import sys


def agent_worker(agent_id: int, redis_url: str, test_type: str, duration: int = 10):
    """Simulate an agent performing various operations."""
    results = {
        'agent_id': agent_id,
        'locks_acquired': 0,
        'locks_failed': 0,
        'tasks_claimed': 0,
        'decisions_logged': 0,
        'errors': []
    }

    try:
        with CoordinationClient.session(
            redis_url=redis_url,
            role=f"Worker-{agent_id}",
            name=f"Agent-{agent_id}",
            working_on=f"Stress test: {test_type}"
        ) as coord:
            print(f"[Agent {agent_id}] Started in {coord.mode} mode")

            start_time = time.time()

            while time.time() - start_time < duration:
                try:
                    if test_type == 'locks':
                        # Test file locking
                        file_path = f"test_file_{random.randint(1, 5)}.py"
                        try:
                            with coord.lock_file(file_path, intent=f"Agent {agent_id} testing"):
                                results['locks_acquired'] += 1
                                # Simulate work
                                time.sleep(random.uniform(0.1, 0.5))
                        except LockAcquireTimeout:
                            results['locks_failed'] += 1

                    elif test_type == 'tasks':
                        # Test task claiming
                        task = coord.claim_task(tags=['stress-test'])
                        if task:
                            results['tasks_claimed'] += 1
                            time.sleep(random.uniform(0.1, 0.3))

                    elif test_type == 'decisions':
                        # Test decision logging
                        coord.log_decision(
                            decision_type="stress_test",
                            context=f"Agent {agent_id} iteration",
                            reason="Testing concurrent logging"
                        )
                        results['decisions_logged'] += 1
                        time.sleep(random.uniform(0.05, 0.2))

                    elif test_type == 'mixed':
                        # Mixed operations
                        op = random.choice(['lock', 'task', 'decision'])
                        if op == 'lock':
                            try:
                                with coord.lock_file("shared_resource.py", intent="Mixed test"):
                                    results['locks_acquired'] += 1
                                    time.sleep(0.1)
                            except LockAcquireTimeout:
                                results['locks_failed'] += 1
                        elif op == 'task':
                            task = coord.claim_task()
                            if task:
                                results['tasks_claimed'] += 1
                        else:
                            coord.log_decision("test", "mixed", "stress testing")
                            results['decisions_logged'] += 1

                        time.sleep(random.uniform(0.05, 0.15))

                except Exception as e:
                    results['errors'].append(str(e))

            print(f"[Agent {agent_id}] Completed: {results}")

    except Exception as e:
        results['errors'].append(f"Fatal: {str(e)}")
        print(f"[Agent {agent_id}] Failed: {e}")

    return results


def run_stress_test(
    test_name: str,
    test_type: str,
    num_agents: int,
    duration: int,
    redis_url: str,
    use_processes: bool = False
):
    """Run a stress test scenario."""
    print(f"\n{'='*80}")
    print(f"STRESS TEST: {test_name}")
    print(f"Agents: {num_agents} | Duration: {duration}s | Type: {test_type}")
    print(f"Execution: {'Processes' if use_processes else 'Threads'}")
    print(f"{'='*80}\n")

    start_time = time.time()

    if use_processes:
        with ProcessPoolExecutor(max_workers=num_agents) as executor:
            futures = [
                executor.submit(agent_worker, i, redis_url, test_type, duration)
                for i in range(num_agents)
            ]
            results = [f.result() for f in futures]
    else:
        with ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = [
                executor.submit(agent_worker, i, redis_url, test_type, duration)
                for i in range(num_agents)
            ]
            results = [f.result() for f in futures]

    elapsed = time.time() - start_time

    # Aggregate results
    total_locks_acquired = sum(r['locks_acquired'] for r in results)
    total_locks_failed = sum(r['locks_failed'] for r in results)
    total_tasks = sum(r['tasks_claimed'] for r in results)
    total_decisions = sum(r['decisions_logged'] for r in results)
    total_errors = sum(len(r['errors']) for r in results)

    print(f"\n{'='*80}")
    print(f"RESULTS: {test_name}")
    print(f"{'='*80}")
    print(f"Duration: {elapsed:.2f}s")
    print(f"Locks Acquired: {total_locks_acquired}")
    print(f"Locks Failed: {total_locks_failed}")
    if total_locks_acquired + total_locks_failed > 0:
        lock_success_rate = total_locks_acquired / (total_locks_acquired + total_locks_failed) * 100
        print(f"Lock Success Rate: {lock_success_rate:.1f}%")
    print(f"Tasks Claimed: {total_tasks}")
    print(f"Decisions Logged: {total_decisions}")
    print(f"Total Errors: {total_errors}")

    if total_errors > 0:
        print(f"\n⚠️  ERRORS DETECTED:")
        for r in results:
            if r['errors']:
                print(f"  Agent {r['agent_id']}: {r['errors'][:3]}")  # Show first 3 errors

    # Performance metrics
    if test_type == 'locks':
        ops_per_sec = (total_locks_acquired + total_locks_failed) / elapsed
        print(f"\nPerformance: {ops_per_sec:.1f} lock operations/sec")

    print(f"{'='*80}\n")

    return {
        'test_name': test_name,
        'elapsed': elapsed,
        'locks_acquired': total_locks_acquired,
        'locks_failed': total_locks_failed,
        'tasks_claimed': total_tasks,
        'decisions_logged': total_decisions,
        'errors': total_errors
    }


def main():
    """Run all stress tests."""
    redis_url = "redis://localhost:6379"

    print("""
╔══════════════════════════════════════════════════════════════╗
║         AgentCoord Stress Test Suite                        ║
║  Testing concurrent agent operations and race conditions    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Check Redis availability
    try:
        import redis
        client = redis.from_url(redis_url, socket_connect_timeout=1)
        client.ping()
        print("✓ Redis connected\n")
        mode = "Redis"
    except:
        print("⚠️  Redis unavailable - running in file mode\n")
        mode = "File"

    all_results = []

    # Test 1: Light load - File locking
    all_results.append(run_stress_test(
        test_name="Light Load - File Locking",
        test_type="locks",
        num_agents=3,
        duration=5,
        redis_url=redis_url,
        use_processes=False
    ))

    # Test 2: Medium load - File locking
    all_results.append(run_stress_test(
        test_name="Medium Load - File Locking",
        test_type="locks",
        num_agents=10,
        duration=10,
        redis_url=redis_url,
        use_processes=False
    ))

    # Test 3: Heavy load - File locking
    if mode == "Redis":
        all_results.append(run_stress_test(
            test_name="Heavy Load - File Locking",
            test_type="locks",
            num_agents=20,
            duration=15,
            redis_url=redis_url,
            use_processes=True
        ))

    # Test 4: Decision logging stress
    all_results.append(run_stress_test(
        test_name="Decision Logging Stress",
        test_type="decisions",
        num_agents=10,
        duration=10,
        redis_url=redis_url,
        use_processes=False
    ))

    # Test 5: Mixed operations
    all_results.append(run_stress_test(
        test_name="Mixed Operations",
        test_type="mixed",
        num_agents=10,
        duration=15,
        redis_url=redis_url,
        use_processes=False
    ))

    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")

    total_errors = sum(r['errors'] for r in all_results)

    for r in all_results:
        status = "✓ PASS" if r['errors'] == 0 else "✗ FAIL"
        print(f"{status} | {r['test_name']:<40} | {r['elapsed']:.1f}s | {r['errors']} errors")

    print(f"{'='*80}")

    if total_errors == 0:
        print("\n🎉 ALL TESTS PASSED - System is stable under stress!")
    else:
        print(f"\n⚠️  {total_errors} errors detected - review results above")

    print(f"\nMode: {mode}")
    print(f"Total runtime: {sum(r['elapsed'] for r in all_results):.1f}s\n")


if __name__ == '__main__':
    main()
