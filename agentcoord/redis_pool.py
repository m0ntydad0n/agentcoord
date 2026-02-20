import redis
from typing import Optional
from .config import config

class RedisPoolManager:
    _instance: Optional['RedisPoolManager'] = None
    _pool: Optional[redis.ConnectionPool] = None
    
    def __new__(cls) -> 'RedisPoolManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_pool(self) -> redis.ConnectionPool:
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_MAX_CONNECTIONS,
                socket_connect_timeout=config.REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=config.REDIS_SOCKET_TIMEOUT,
                retry_on_timeout=config.REDIS_RETRY_ON_TIMEOUT,
                decode_responses=True
            )
        return self._pool
    
    def get_client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.get_pool())
    
    def close_pool(self) -> None:
        if self._pool:
            self._pool.disconnect()
            self._pool = None

# Global instance for easy access
redis_pool_manager = RedisPoolManager()