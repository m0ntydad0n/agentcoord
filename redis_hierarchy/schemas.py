from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import redis
from datetime import datetime, timedelta

class CoordinatorType(Enum):
    MASTER = "master"
    SUB = "sub" 
    WORKER = "worker"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Coordinator:
    id: str
    type: CoordinatorType
    parent_id: Optional[str] = None
    budget_allocated: float = 0.0
    budget_used: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()