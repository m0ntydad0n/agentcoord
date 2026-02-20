"""Custom exceptions for AgentCoord."""

class AgentCoordError(Exception):
    """Base exception for AgentCoord."""
    pass

class RedisConnectionError(AgentCoordError):
    """Redis connection or operation failed."""
    pass

class WorkerSpawnError(AgentCoordError):
    """Worker process spawn failed."""
    pass

class WorkerTimeoutError(AgentCoordError):
    """Worker startup timeout."""
    pass

class ValidationError(AgentCoordError):
    """Input validation failed."""
    pass

class APIRateLimitError(AgentCoordError):
    """API rate limit exceeded."""
    pass

class LLMResponseError(AgentCoordError):
    """LLM response parsing or validation failed."""
    pass