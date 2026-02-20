import json
import time
import signal
import sys
from typing import Any, Dict, Callable, Optional
import redis
from .redis_pool import redis_pool_manager

class AgentWorker:
    def __init__(self, worker_id: Optional[str] = None, task_handler: Optional[Callable] = None):
        self.worker_id = worker_id or f"worker_{int(time.time())}"
        self.redis_client = redis_pool_manager.get_client()
        self.task_queue = "agent_tasks"
        self.result_prefix = "agent_result:"
        self.task_handler = task_handler or self._default_task_handler
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"Worker {self.worker_id} received signal {signum}, shutting down...")
        self.running = False
    
    def _default_task_handler(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Default task handler - override in subclasses"""
        return {"status": "completed", "result": f"Processed by {self.worker_id}"}
    
    def _update_task_status(self, task_id: str, status: str):
        """Update task status in Redis"""
        status_key = f"agent_status:{task_id}"
        self.redis_client.setex(status_key, 3600, status)  # Expire after 1 hour
    
    def _publish_result(self, task_id: str, result: Dict[str, Any]):
        """Publish task result"""
        result_key = f"{self.result_prefix}{task_id}"
        result_data = {
            "task_id": task_id,
            "worker_id": self.worker_id,
            "result": result,
            "completed_at": time.time()
        }
        self.redis_client.lpush(result_key, json.dumps(result_data))
        self.redis_client.expire(result_key, 3600)  # Expire after 1 hour
    
    def process_task(self, task: Dict[str, Any]) -> bool:
        """Process a single task"""
        task_id = task["id"]
        
        try:
            self._update_task_status(task_id, "processing")
            
            # Process the task
            result = self.task_handler(task["data"])
            
            # Publish result
            self._publish_result(task_id, result)
            self._update_task_status(task_id, "completed")
            
            print(f"Worker {self.worker_id} completed task {task_id}")
            return True
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "worker_id": self.worker_id
            }
            self._publish_result(task_id, error_result)
            self._update_task_status(task_id, "error")
            print(f"Worker {self.worker_id} error processing task {task_id}: {e}")
            return False
    
    def start(self, poll_interval: int = 1):
        """Start processing tasks"""
        self.running = True
        print(f"Worker {self.worker_id} started")
        
        while self.running:
            try:
                # Get highest priority task (ZREVRANGE with LIMIT)
                tasks = self.redis_client.zrevrange(self.task_queue, 0, 0, withscores=True)
                
                if tasks:
                    task_data, score = tasks[0]
                    task = json.loads(task_data)
                    
                    # Remove task from queue atomically
                    removed = self.redis_client.zrem(self.task_queue, task_data)
                    
                    if removed:
                        self.process_task(task)
                    else:
                        # Task was already taken by another worker
                        continue
                else:
                    # No tasks available, wait
                    time.sleep(poll_interval)
                    
            except redis.RedisError as e:
                print(f"Redis error in worker {self.worker_id}: {e}")
                time.sleep(poll_interval * 2)
            except Exception as e:
                print(f"Unexpected error in worker {self.worker_id}: {e}")
                time.sleep(poll_interval)
        
        print(f"Worker {self.worker_id} stopped")
    
    def stop(self):
        """Stop the worker"""
        self.running = False
    
    def close(self):
        """Close worker connection"""
        pass