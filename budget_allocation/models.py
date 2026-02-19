from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from decimal import Decimal
from datetime import datetime
from enum import Enum
import uuid

class BudgetStatus(Enum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    SUSPENDED = "suspended"

class AlertType(Enum):
    THRESHOLD_WARNING = "threshold_warning"
    THRESHOLD_CRITICAL = "threshold_critical"
    BUDGET_EXHAUSTED = "budget_exhausted"

@dataclass
class BudgetNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    total_budget: Decimal = Decimal('0')
    allocated_budget: Decimal = Decimal('0')
    used_budget: Decimal = Decimal('0')
    parent_id: Optional[str] = None
    children_ids: Set[str] = field(default_factory=set)
    status: BudgetStatus = BudgetStatus.ACTIVE
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def available_budget(self) -> Decimal:
        return self.total_budget - self.used_budget

    @property
    def unallocated_budget(self) -> Decimal:
        return self.total_budget - self.allocated_budget

    @property
    def usage_percentage(self) -> float:
        if self.total_budget == 0:
            return 0.0
        return float(self.used_budget / self.total_budget)

@dataclass
class BudgetTransaction:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    amount: Decimal = Decimal('0')
    description: str = ""
    transaction_type: str = "expense"  # expense, allocation, reallocation
    timestamp: datetime = field(default_factory=datetime.now)
    reference_id: Optional[str] = None

@dataclass
class BudgetAlert:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    alert_type: AlertType = AlertType.THRESHOLD_WARNING
    message: str = ""
    threshold_value: float = 0.0
    current_usage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False