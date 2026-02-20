"""Prometheus metrics for AgentCoord monitoring."""

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest
import time
from contextlib import contextmanager
from typing import Optional
import threading

# Global registry for metrics
REGISTRY = CollectorRegistry()

# Counters
tasks_created = Counter(
    'agentcoord_tasks_created_total',
    'Total number of tasks created',
    ['task_type'],
    registry=REGISTRY
)

tasks_completed = Counter(
    'agentcoord_tasks_completed_total',
    'Total number of tasks completed successfully',
    ['task_type'],
    registry=REGISTRY
)

tasks_failed = Counter(
    'agentcoord_tasks_failed_total',
    'Total number of tasks that failed',
    ['task_type', 'error_type'],
    registry=REGISTRY
)

# Gauges
active_workers = Gauge(
    'agentcoord_active_workers',
    'Current number of active workers',
    ['worker_type'],
    registry=REGISTRY
)

pending_tasks = Gauge(
    'agentcoord_pending_tasks',
    'Current number of pending tasks in queue',
    ['priority'],
    registry=REGISTRY
)

active_locks = Gauge(
    'agentcoord_active_locks',
    'Current number of active coordination locks',
    registry=REGISTRY
)

# Histograms
task_duration_seconds = Histogram(
    'agentcoord_task_duration_seconds',
    'Task execution duration in seconds',
    ['task_type'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf')),
    registry=REGISTRY
)

llm_response_time = Histogram(
    'agentcoord_llm_response_seconds',
    'LLM API response time in seconds',
    ['provider', 'model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, float('inf')),
    registry=REGISTRY
)

class MetricsCollector:
    """Centralized metrics collection and management."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._task_start_times = {}
        
    def record_task_created(self, task_type: str = "default"):
        """Record a new task creation."""
        tasks_created.labels(task_type=task_type).inc()
        
    def record_task_completed(self, task_id: str, task_type: str = "default"):
        """Record successful task completion."""
        tasks_completed.labels(task_type=task_type).inc()
        self._record_task_duration(task_id, task_type)
        
    def record_task_failed(self, task_id: str, task_type: str = "default", error_type: str = "unknown"):
        """Record task failure."""
        tasks_failed.labels(task_type=task_type, error_type=error_type).inc()
        self._record_task_duration(task_id, task_type)
        
    def record_worker_spawned(self, worker_type: str = "default"):
        """Record new worker spawn."""
        active_workers.labels(worker_type=worker_type).inc()
        
    def record_worker_terminated(self, worker_type: str = "default"):
        """Record worker termination."""
        active_workers.labels(worker_type=worker_type).dec()
        
    def set_pending_tasks(self, count: int, priority: str = "normal"):
        """Update pending tasks gauge."""
        pending_tasks.labels(priority=priority).set(count)
        
    def record_lock_acquired(self):
        """Record coordination lock acquisition."""
        active_locks.inc()
        
    def record_lock_released(self):
        """Record coordination lock release."""
        active_locks.dec()
        
    def start_task_timer(self, task_id: str):
        """Start timing a task execution."""
        with self._lock:
            self._task_start_times[task_id] = time.time()
            
    def _record_task_duration(self, task_id: str, task_type: str):
        """Record task duration if timer was started."""
        with self._lock:
            start_time = self._task_start_times.pop(task_id, None)
            if start_time:
                duration = time.time() - start_time
                task_duration_seconds.labels(task_type=task_type).observe(duration)
    
    @contextmanager
    def time_llm_request(self, provider: str, model: str):
        """Context manager to time LLM requests."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            llm_response_time.labels(provider=provider, model=model).observe(duration)
            
    def get_metrics(self) -> bytes:
        """Get current metrics in Prometheus format."""
        return generate_latest(REGISTRY)

# Global metrics collector instance
metrics = MetricsCollector()