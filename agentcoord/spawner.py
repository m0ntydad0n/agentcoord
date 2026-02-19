"""
Worker spawning and lifecycle management.

Allows coordinator agents to dynamically spawn worker agents
using different backends (subprocess, docker, cloud).
"""

import os
import subprocess
import uuid
import logging
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SpawnMode(str, Enum):
    """Worker spawn modes."""
    SUBPROCESS = "subprocess"
    DOCKER = "docker"
    RAILWAY = "railway"


class WorkerProcess:
    """Represents a spawned worker process."""

    def __init__(self, worker_id: str, name: str, tags: List[str], process, mode: SpawnMode):
        self.worker_id = worker_id
        self.name = name
        self.tags = tags
        self.process = process
        self.mode = mode

    def is_alive(self) -> bool:
        """Check if worker process is still running."""
        if self.mode == SpawnMode.SUBPROCESS:
            return self.process.poll() is None
        elif self.mode == SpawnMode.DOCKER:
            # Check container status
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(self.worker_id)
                return container.status == 'running'
            except:
                return False
        return False

    def terminate(self):
        """Terminate the worker process."""
        if self.mode == SpawnMode.SUBPROCESS:
            self.process.terminate()
            logger.info(f"Terminated subprocess worker {self.name}")
        elif self.mode == SpawnMode.DOCKER:
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(self.worker_id)
                container.stop()
                logger.info(f"Stopped Docker worker {self.name}")
            except Exception as e:
                logger.error(f"Failed to stop Docker worker {self.name}: {e}")


class WorkerSpawner:
    """Manages spawning and lifecycle of worker agents."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.workers: Dict[str, WorkerProcess] = {}

    def spawn_worker(
        self,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        mode: SpawnMode = SpawnMode.SUBPROCESS,
        max_tasks: Optional[int] = None,
        poll_interval: int = 5,
        use_llm: bool = False
    ) -> WorkerProcess:
        """
        Spawn a new worker agent.

        Args:
            name: Worker name (auto-generated if None)
            tags: Task tags this worker should claim
            mode: Spawn mode (subprocess, docker, railway)
            max_tasks: Max tasks before worker stops
            poll_interval: Seconds between task checks

        Returns:
            WorkerProcess object
        """
        worker_id = str(uuid.uuid4())[:8]
        name = name or f"Worker-{worker_id}"
        tags = tags or []

        logger.info(f"Spawning worker {name} with tags {tags} using {mode}")

        if mode == SpawnMode.SUBPROCESS:
            worker_process = self._spawn_subprocess(
                worker_id, name, tags, max_tasks, poll_interval, use_llm
            )
        elif mode == SpawnMode.DOCKER:
            worker_process = self._spawn_docker(
                worker_id, name, tags, max_tasks, poll_interval
            )
        elif mode == SpawnMode.RAILWAY:
            worker_process = self._spawn_railway(
                worker_id, name, tags, max_tasks, poll_interval
            )
        else:
            raise ValueError(f"Unknown spawn mode: {mode}")

        self.workers[worker_id] = worker_process
        return worker_process

    def _spawn_subprocess(
        self,
        worker_id: str,
        name: str,
        tags: List[str],
        max_tasks: Optional[int],
        poll_interval: int,
        use_llm: bool = False
    ) -> WorkerProcess:
        """Spawn worker as subprocess."""
        # Get absolute path to worker script
        import agentcoord
        package_dir = os.path.dirname(os.path.dirname(agentcoord.__file__))

        # Choose worker type
        if use_llm:
            worker_script = os.path.join(package_dir, 'examples', 'llm_worker_agent.py')
        else:
            worker_script = os.path.join(package_dir, 'examples', 'worker_agent.py')

        # Build command
        cmd = [
            'python3',
            worker_script,
            '--name', name,
            '--redis-url', self.redis_url,
            '--poll-interval', str(poll_interval)
        ]

        if tags:
            cmd.extend(['--tags', ','.join(tags)])

        if max_tasks:
            cmd.extend(['--max-tasks', str(max_tasks)])

        # Spawn process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        logger.info(f"Spawned subprocess worker {name} (PID: {process.pid})")

        return WorkerProcess(worker_id, name, tags, process, SpawnMode.SUBPROCESS)

    def _spawn_docker(
        self,
        worker_id: str,
        name: str,
        tags: List[str],
        max_tasks: Optional[int],
        poll_interval: int
    ) -> WorkerProcess:
        """Spawn worker in Docker container."""
        try:
            import docker
            client = docker.from_env()

            # Build command
            cmd = [
                'python3', 'examples/worker_agent.py',
                '--name', name,
                '--redis-url', self.redis_url,
                '--poll-interval', str(poll_interval)
            ]

            if tags:
                cmd.extend(['--tags', ','.join(tags)])

            if max_tasks:
                cmd.extend(['--max-tasks', str(max_tasks)])

            # Run container
            container = client.containers.run(
                'agentcoord-worker',
                command=' '.join(cmd),
                name=f"worker-{worker_id}",
                environment={
                    'REDIS_URL': self.redis_url
                },
                detach=True,
                network_mode='host'  # Access localhost Redis
            )

            logger.info(f"Spawned Docker worker {name} (container: {container.id[:12]})")

            return WorkerProcess(worker_id, name, tags, container, SpawnMode.DOCKER)

        except Exception as e:
            logger.error(f"Failed to spawn Docker worker: {e}")
            raise

    def _spawn_railway(
        self,
        worker_id: str,
        name: str,
        tags: List[str],
        max_tasks: Optional[int],
        poll_interval: int
    ) -> WorkerProcess:
        """Spawn worker on Railway."""
        # Build Railway run command
        cmd = [
            'railway', 'run',
            'python3', 'examples/worker_agent.py',
            '--name', name,
            '--poll-interval', str(poll_interval)
        ]

        if tags:
            cmd.extend(['--tags', ','.join(tags)])

        if max_tasks:
            cmd.extend(['--max-tasks', str(max_tasks)])

        # Spawn via Railway CLI
        process = subprocess.Popen(cmd)

        logger.info(f"Spawned Railway worker {name}")

        return WorkerProcess(worker_id, name, tags, process, SpawnMode.RAILWAY)

    def count_alive_workers(self) -> int:
        """Count workers that are still running."""
        return sum(1 for w in self.workers.values() if w.is_alive())

    def cleanup_dead_workers(self):
        """Remove dead workers from tracking."""
        dead_workers = [
            wid for wid, worker in self.workers.items()
            if not worker.is_alive()
        ]

        for wid in dead_workers:
            logger.info(f"Cleaning up dead worker {self.workers[wid].name}")
            del self.workers[wid]

    def terminate_all(self):
        """Terminate all spawned workers."""
        logger.info(f"Terminating {len(self.workers)} workers...")

        for worker in self.workers.values():
            worker.terminate()

        self.workers.clear()

    def get_worker_stats(self) -> Dict:
        """Get statistics about spawned workers."""
        alive = self.count_alive_workers()
        total = len(self.workers)

        return {
            'total_spawned': total,
            'alive': alive,
            'dead': total - alive,
            'workers': [
                {
                    'id': w.worker_id,
                    'name': w.name,
                    'tags': w.tags,
                    'mode': w.mode.value,
                    'alive': w.is_alive()
                }
                for w in self.workers.values()
            ]
        }
