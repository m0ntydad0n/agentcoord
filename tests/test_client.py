"""Tests for CoordinationClient initialization and basic functionality."""

import pytest
from agentcoord.client import CoordinationClient


def test_client_initializes_with_redis_url():
    """CoordinationClient should initialize with a Redis URL."""
    client = CoordinationClient(redis_url="redis://localhost:6379")

    assert client is not None
    assert client.mode in ["redis", "file"]


def test_client_falls_back_to_file_mode_when_redis_unavailable():
    """CoordinationClient should fall back to file mode when Redis is unreachable."""
    # Use invalid Redis URL to force fallback
    client = CoordinationClient(
        redis_url="redis://localhost:9999",  # Non-existent Redis
        fallback_dir="/tmp/agentcoord_test"
    )

    assert client.mode == "file"
    assert client.fallback_dir == "/tmp/agentcoord_test"


def test_register_agent_sets_agent_id():
    """register_agent should create agent ID and store agent metadata."""
    client = CoordinationClient(
        redis_url="redis://localhost:9999",
        fallback_dir="/tmp/agentcoord_test"
    )

    agent_id = client.register_agent(
        role="CTO",
        name="Claude",
        working_on="Implementing Redis coordination"
    )

    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert len(agent_id) > 0


def test_lock_file_returns_context_manager():
    """lock_file should return a context manager for file locking."""
    client = CoordinationClient(
        redis_url="redis://localhost:9999",
        fallback_dir="/tmp/agentcoord_test"
    )
    client.register_agent(role="CTO", name="Claude")

    lock = client.lock_file("backend/main.py", intent="Add endpoint")

    # Should have __enter__ and __exit__ methods (context manager protocol)
    assert hasattr(lock, '__enter__')
    assert hasattr(lock, '__exit__')


def test_session_context_manager():
    """CoordinationClient.session() should provide clean session management."""
    with CoordinationClient.session(
        redis_url="redis://localhost:9999",
        fallback_dir="/tmp/agentcoord_test",
        role="CTO",
        name="Claude"
    ) as client:
        assert client.agent_id is not None
        assert client.mode == "file"

    # Client should be properly cleaned up after context exit
