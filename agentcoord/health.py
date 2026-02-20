"""Health monitoring system for agents."""
import time
import psutil
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import redis

from .redis_pool import redis_pool_manager


class HealthMonitor:
    """Manages health monitoring for agents."""

    def __init__(self):
        self.redis_client = redis_pool_manager.get_client()
        self.start_time = time.time()
        self.tasks_completed = 0
        self.last_task_time = None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of this agent."""
        try:
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
        except ImportError:
            memory_info = None
            cpu_percent = None
        
        status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'uptime': time.time() - self.start_time,
            'tasks_completed': self.tasks_completed,
            'last_task_timestamp': self.last_task_time,
        }
        
        if memory_info:
            status['memory_usage'] = {
                'percent': memory_info.percent,
                'used': memory_info.used,
                'available': memory_info.available
            }
        
        if cpu_percent is not None:
            status['cpu_percent'] = cpu_percent
        
        return status
    
    def update_task_completed(self):
        """Update task completion counter."""
        self.tasks_completed += 1
        self.last_task_time = time.time()
    
    def is_worker_healthy(self, health_data: Dict[str, Any], timeout_minutes: int = 5) -> bool:
        """Check if a worker is healthy based on health data."""
        if not health_data:
            return False
        
        last_heartbeat = health_data.get('timestamp', 0)
        timeout_seconds = timeout_minutes * 60
        
        return (time.time() - last_heartbeat) < timeout_seconds


health_monitor = HealthMonitor()