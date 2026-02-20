"""Enhanced coordinator with health monitoring."""
import time
import threading
import logging
from typing import List, Dict, Any

from .agent import Agent
from .health import health_monitor

logger = logging.getLogger(__name__)


class Coordinator:
    """Enhanced coordinator with health monitoring capabilities."""
    
    def __init__(self):
        self.monitoring_active = False
        self.monitor_thread = None
        self.health_check_interval = 60  # seconds
    
    def start_health_monitoring(self):
        """Start health monitoring thread."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Health monitoring started")
    
    def stop_health_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
    
    def _health_monitor_loop(self):
        """Main health monitoring loop."""
        while self.monitoring_active:
            try:
                self.check_worker_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                time.sleep(self.health_check_interval)
    
    def check_worker_health(self):
        """Check health of all workers."""
        unhealthy_workers = Agent.get_unhealthy_workers()
        
        if unhealthy_workers:
            logger.warning(f"Unhealthy workers detected: {unhealthy_workers}")
            self._handle_unhealthy_workers(unhealthy_workers)
    
    def _handle_unhealthy_workers(self, worker_ids: List[str]):
        """Handle unhealthy workers (implement restart logic here)."""
        for worker_id in worker_ids:
            logger.error(f"Worker {worker_id} is unhealthy")
            # TODO: Implement auto-restart logic here
            # This could involve:
            # 1. Removing worker from active pool
            # 2. Reassigning its tasks
            # 3. Starting new worker instance
    
    def get_cluster_health_summary(self) -> Dict[str, Any]:
        """Get overall cluster health summary."""
        all_health = Agent.get_all_agents_health()
        unhealthy = Agent.get_unhealthy_workers()
        
        return {
            'total_workers': len(all_health),
            'healthy_workers': len(all_health) - len(unhealthy),
            'unhealthy_workers': len(unhealthy),
            'unhealthy_worker_ids': unhealthy,
            'timestamp': time.time()
        }