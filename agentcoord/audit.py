"""
Decision audit logging using Redis Streams.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class AuditLog:
    """Append-only audit log for decisions."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.stream_key = "audit:decisions"

    def log_decision(
        self,
        agent_id: str,
        decision_type: str,
        context: str,
        reason: str
    ):
        """Log a decision to the audit stream."""
        entry = {
            "agent_id": agent_id,
            "decision_type": decision_type,
            "context": context,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Add to stream (auto-generates ID)
        self.redis.xadd(self.stream_key, entry)
        logger.info(f"Logged decision: {decision_type} by {agent_id}")

    def get_recent_decisions(self, count: int = 100) -> List[Dict]:
        """Retrieve recent decisions from the log."""
        entries = self.redis.xrevrange(self.stream_key, count=count)
        decisions = []
        for entry_id, data in entries:
            decisions.append({
                "id": entry_id,
                **data
            })
        return decisions

    def get_decisions_by_agent(self, agent_id: str, count: int = 100) -> List[Dict]:
        """Get decisions made by a specific agent."""
        all_decisions = self.get_recent_decisions(count=count)
        return [d for d in all_decisions if d.get("agent_id") == agent_id]
