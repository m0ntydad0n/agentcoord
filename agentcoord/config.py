import os
from typing import Optional

class Config:
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_MAX_CONNECTIONS: int = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    REDIS_SOCKET_CONNECT_TIMEOUT: int = int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5'))
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv('REDIS_SOCKET_TIMEOUT', '5'))
    REDIS_RETRY_ON_TIMEOUT: bool = os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true'

config = Config()