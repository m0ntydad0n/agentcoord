"""
Agent registration and heartbeat monitoring.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Manages agent registration and heartbeat monitoring."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.heartbeat_stop = threading.Event()

    def register_agent(
        self,
        agent_id: str,
        role: str,
        name: str,
        working_on: str = "",
        session_id: str = ""
    ):
        """Register agent and start heartbeat thread."""
        agent_key = f"agent:{agent_id}"

        self.redis.hset(agent_key, mapping={
            "role": role,
            "name": name,
            "status": "active",
            "working_on": working_on,
            "blocked_by": "",
            "last_commit": "",
            "session_id": session_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        })

        # Add to heartbeats sorted set
        self.redis.zadd("heartbeats", {agent_id: time.time()})

        logger.info(f"Registered agent {agent_id} ({role}: {name})")

        # Start heartbeat thread
        self.start_heartbeat(agent_id)

    def start_heartbeat(self, agent_id: str, interval: int = 30):
        """Start background heartbeat thread."""
        def heartbeat_loop():
            while not self.heartbeat_stop.wait(interval):
                try:
                    self.send_heartbeat(agent_id)
                except Exception as e:
                    logger.error(f"Heartbeat error for {agent_id}: {e}")

        self.heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def send_heartbeat(self, agent_id: str):
        """Send heartbeat update."""
        now = time.time()
        self.redis.zadd("heartbeats", {agent_id: now})
        self.redis.hset(
            f"agent:{agent_id}",
            "last_heartbeat",
            datetime.now(timezone.utc).isoformat()
        )

    def stop_heartbeat(self):
        """Stop heartbeat thread."""
        if self.heartbeat_thread:
            self.heartbeat_stop.set()
            self.heartbeat_thread.join(timeout=5)

    def update_agent_status(self, agent_id: str, **kwargs):
        """Update agent status fields."""
        agent_key = f"agent:{agent_id}"
        if kwargs:
            self.redis.hset(agent_key, mapping=kwargs)

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent details."""
        return self.redis.hgetall(f"agent:{agent_id}") or None

    def list_agents(self) -> Dict[str, Dict]:
        """List all registered agents."""
        agents = {}
        for key in self.redis.keys("agent:*"):
            agent_id = key.split(":", 1)[1]
            agents[agent_id] = self.redis.hgetall(key)
        return agents

    def get_stale_agents(self, threshold_seconds: int = 300) -> Dict[str, Dict]:
        """Find agents with no heartbeat in threshold seconds."""
        cutoff = time.time() - threshold_seconds
        stale_ids = self.redis.zrangebyscore("heartbeats", "-inf", cutoff)

        stale_agents = {}
        for agent_id in stale_ids:
            agent = self.get_agent(agent_id)
            if agent:
                stale_agents[agent_id] = agent

        return stale_agents

    def unregister_agent(self, agent_id: str):
        """Unregister agent and cleanup."""
        self.stop_heartbeat()
        self.redis.delete(f"agent:{agent_id}")
        self.redis.zrem("heartbeats", agent_id)
        logger.info(f"Unregistered agent {agent_id}")
