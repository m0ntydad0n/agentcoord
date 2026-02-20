"""Worker process spawner with robust error handling."""

import logging
import os
import psutil
import signal
import subprocess
import time
from typing import Dict, List, Optional, Set
import threading

from .exceptions import WorkerSpawnError, WorkerTimeoutError

logger = logging.getLogger(__name__)

class WorkerProcess:
    """Represents a spawned worker process."""
    
    def __init__(self, process: subprocess.Popen, worker_id: str, command: List[str]):
        self.process = process
        self.worker_id = worker_id
        self.command = command
        self.spawn_time = time.time()
        self.last_health_check = None

    @property
    def pid(self) -> int:
        """Get process ID."""
        return self.process.pid

    @property
    def is_alive(self) -> bool:
        """Check if process is still running."""
        return self.process.poll() is None

    def terminate(self, timeout: int = 10) -> bool:
        """Terminate process gracefully."""
        if not self.is_alive:
            return True

        try:
            # Try graceful termination first
            self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=timeout)
                logger.info(f"Worker {self.worker_id} terminated gracefully")
                return True
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination fails
                logger.warning(f"Worker {self.worker_id} didn't terminate gracefully, force killing")
                self.process.kill()
                self.process.wait(timeout=5)
                return True
                
        except Exception as e:
            logger.error(f"Error terminating worker {self.worker_id}: {e}")
            return False

class WorkerSpawner:
    """Spawns and manages worker processes with error handling."""
    
    def __init__(
        self,
        max_workers: int = 4,
        startup_timeout: int = 30,
        health_check_interval: int = 60,
        max_memory_mb: int = 1024,
        max_cpu_percent: float = 80.0
    ):
        self.max_workers = max_workers
        self.startup_timeout = startup_timeout
        self.health_check_interval = health_check_interval
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        
        self.workers: Dict[str, WorkerProcess] = {}
        self.zombie_pids: Set[int] = set()
        self._shutdown_event = threading.Event()
        self._health_check_thread = None
        
        # Start health check thread
        self._start_health_monitor()

    def _start_health_monitor(self) -> None:
        """Start background health monitoring thread."""
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("Health monitoring thread started")

    def _health_check_loop(self) -> None:
        """Background health monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                self._cleanup_zombies()
                self._check_worker_health()
                
                # Wait for next check or shutdown
                self._shutdown_event.wait(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                time.sleep(5)  # Brief pause before retrying

    def _cleanup_zombies(self) -> None:
        """Clean up zombie processes."""
        zombies_to_remove = set()
        
        for pid in self.zombie_pids:
            try:
                # Check if process still exists
                if not psutil.pid_exists(pid):
                    zombies_to_remove.add(pid)
                    continue
                    
                proc = psutil.Process(pid)
                if proc.status() == psutil.STATUS_ZOMBIE:
                    logger.warning(f"Cleaning up zombie process {pid}")
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        pass
                    zombies_to_remove.add(pid)
                    
            except psutil.NoSuchProcess:
                zombies_to_remove.add(pid)
            except Exception as e:
                logger.error(f"Error cleaning zombie process {pid}: {e}")

        self.zombie_pids -= zombies_to_remove

    def _check_worker_health(self) -> None:
        """Check health of running workers."""
        workers_to_restart = []
        
        for worker_id, worker in list(self.workers.items()):
            try:
                if not worker.is_alive:
                    logger.warning(f"Worker {worker_id} is no longer alive")
                    workers_to_restart.append(worker_id)
                    continue

                # Check resource usage
                try:
                    proc = psutil.Process(worker.pid)
                    memory_mb = proc.memory_info().rss / 1024 / 1024
                    cpu_percent = proc.cpu_percent()

                    if memory_mb > self.max_memory_mb:
                        logger.warning(
                            f"Worker {worker_id} using too much memory: "
                            f"{memory_mb:.1f}MB > {self.max_memory_mb}MB"
                        )
                        workers_to_restart.append(worker_id)
                        
                    elif cpu_percent > self.max_cpu_percent:
                        logger.warning(
                            f"Worker {worker_id} using too much CPU: "
                            f"{cpu_percent:.1f}% > {self.max_cpu_percent}%"
                        )
                        # Log but don't restart for CPU (might be temporary spike)

                except psutil.NoSuchProcess:
                    logger.warning(f"Worker {worker_id} process no longer exists")
                    workers_to_restart.append(worker_id)
                    
            except Exception as e:
                logger.error(f"Error checking worker {worker_id} health: {e}")

        # Restart unhealthy workers
        for worker_id in workers_to_restart:
            self._restart_worker(worker_id)

    def _restart_worker(self, worker_id: str) -> None:
        """Restart a specific worker."""
        try:
            worker = self.workers.get(worker