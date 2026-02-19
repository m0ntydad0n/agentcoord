"""
Git commit tracking and integration.
"""

import json
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class GitIntegration:
    """Tracks git commits in Redis for coordination visibility."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.commits_key = "git:commits"
        self.max_commits = 100  # Keep last 100 commits

    def track_commit(self, commit_hash: str, message: str, author: str, date: str = ""):
        """Track a git commit."""
        commit_data = json.dumps({
            "hash": commit_hash,
            "message": message,
            "author": author,
            "date": date
        })

        # Add to front of list
        self.redis.lpush(self.commits_key, commit_data)

        # Trim to max size
        self.redis.ltrim(self.commits_key, 0, self.max_commits - 1)

        logger.info(f"Tracked commit {commit_hash[:7]}: {message}")

    def get_recent_commits(self, limit: int = 10) -> List[Dict]:
        """Get recent commits."""
        commits_json = self.redis.lrange(self.commits_key, 0, limit - 1)
        return [json.loads(c) for c in commits_json]
