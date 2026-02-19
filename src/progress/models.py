from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class NodeType(Enum):
    WORKER = "worker"
    SUB_COORDINATOR = "sub_coordinator" 
    MASTER = "master"

class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class ProgressReport:
    node_id: str
    node_type: NodeType
    status: Status
    progress_percentage: float
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_completion: Optional[datetime] = None
    throughput: Optional[float] = None  # units per second

@dataclass  
class AggregatedProgress:
    node_id: str
    total_progress: float
    weighted_progress: float
    child_count: int
    completed_children: int
    failed_children: int
    bottlenecks: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)