import time
import threading
from agentcoord.client import AgentClient
from agentcoord.spawner import AgentSpawner

def task_handler(task_data):
    """Simple task handler for testing"""
    # Simulate some work
    time.sleep(0.1)
    return {"processed": task_data.get("value", 0) * 2}

def stress_test():
    """Stress test with 20+ workers"""
    print("Starting stress test...")
    
    # Spawn 25 workers
    spawner = AgentSpawner()
    worker_ids = spawner.spawn_workers(25, task_handler, poll_interval=0.5)
    
    time.sleep(2)  # Let workers start up
    
    # Create multiple clients submitting tasks concurrently
    clients = [AgentClient() for _ in range(10)]
    task_ids = []
    
    def submit_tasks(client, start_value):
        """Submit tasks from a client"""
        for i in range(10):
            task_id = client.submit_task({"value": start_value + i}, priority=i)
            task_ids.append(task_id)
    
    # Submit tasks concurrently
    threads = []
    for i, client in enumerate(clients):
        thread = threading.Thread(target=submit_tasks, args=(client, i * 100))
        threads.append(thread)
        thread.start()
    
    # Wait for all submissions to complete
    for thread in threads:
        thread.join()
    
    print(f"Submitted {len(task_ids)} tasks")
    
    # Wait for tasks to complete
    completed = 0
    start_time = time.time()
    
    for task_id in task_ids:
        result = clients[0].get_result(task_id, timeout=30)
        if result:
            completed += 1
    
    end_time = time.time()
    
    print(f"Completed {completed}/{len(task_ids)} tasks in {end_time - start_time:.2f} seconds")
    print(f"Worker stats: {spawner.get_worker_stats()}")
    
    # Cleanup
    spawner.stop_all_workers()
    
    for client in clients:
        client.close()

if __name__ == "__main__":
    stress_test()