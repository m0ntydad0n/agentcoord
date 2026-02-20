"""Enhanced agent implementation with health monitoring."""
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class AgentRegistry:
    """Simple agent registry for coordination."""

    def __init__(self, redis_client=None):
        """Initialize registry with optional Redis client."""
        self.redis_client = redis_client
        self.agents = {}

    def register(self, agent_id: str, agent_type: str, capabilities: List[str]) -> str:
        """Register an agent."""
        self.agents[agent_id] = {
            "type": agent_type,
            "capabilities": capabilities,
            "registered_at": time.time()
        }

        if self.redis_client:
            key = f"agents:{agent_id}"
            self.redis_client.setex(
                key,
                3600,  # 1 hour TTL
                json.dumps(self.agents[agent_id])
            )

        return agent_id

    def unregister(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]

        if self.redis_client:
            key = f"agents:{agent_id}"
            self.redis_client.delete(key)


class Agent:
    """Enhanced Agent class with health monitoring."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.redis_client = redis_pool_manager.get_client()
        self.health_key = f"agents:{agent_id}:health"
    
    def update_health(self):
        """Update health status in Redis."""
        health_data = health_monitor.get_health_status()
        self.redis_client.setex(
            self.health_key,
            600,  # 10 minutes TTL
            json.dumps(health_data)
        )
    
    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """Get health status for this agent."""
        data = self.redis_client.get(self.health_key)
        if data:
            return json.loads(data)
        return None
    
    def health_check_endpoint(self) -> Dict[str, Any]:
        """Health check endpoint for workers."""
        self.update_health()
        return health_monitor.get_health_status()
    
    def complete_task(self):
        """Mark task as completed and update health."""
        health_monitor.update_task_completed()
        self.update_health()
    
    @classmethod
    def get_all_agents_health(cls) -> Dict[str, Dict[str, Any]]:
        """Get health status for all agents."""
        redis_client = get_redis_client()
        health_data = {}
        
        # Find all agent health keys
        keys = redis_client.keys("agents:*:health")
        
        for key in keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            agent_id = key_str.split(':')[1]
            
            data = redis_client.get(key)
            if data:
                try:
                    health_data[agent_id] = json.loads(data)
                except json.JSONDecodeError:
                    continue
        
        return health_data
    
    @classmethod
    def get_unhealthy_workers(cls, timeout_minutes: int = 5) -> List[str]:
        """Get list of unhealthy worker IDs."""
        health_data = cls.get_all_agents_health()
        unhealthy = []
        
        timeout_seconds = timeout_minutes * 60
        current_time = time.time()
        
        for agent_id, health in health_data.items():
            last_heartbeat = health.get('timestamp', 0)
            if (current_time - last_heartbeat) > timeout_seconds:
                unhealthy.append(agent_id)
        
        return unhealthy