from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import logging
from .models import BudgetNode, BudgetTransaction, BudgetAlert, BudgetStatus, AlertType

logger = logging.getLogger(__name__)

class BudgetManager:
    def __init__(self):
        self.nodes: Dict[str, BudgetNode] = {}
        self.transactions: List[BudgetTransaction] = []
        self.alerts: List[BudgetAlert] = []
        self.root_node_id: Optional[str] = None

    def create_root_budget(self, name: str, total_budget: Decimal) -> str:
        """Create the root budget node."""
        if self.root_node_id:
            raise ValueError("Root budget already exists")
        
        node = BudgetNode(
            name=name,
            total_budget=total_budget,
            allocated_budget=total_budget
        )
        self.nodes[node.id] = node
        self.root_node_id = node.id
        
        logger.info(f"Created root budget '{name}' with {total_budget}")
        return node.id

    def create_child_budget(
        self, 
        parent_id: str, 
        name: str, 
        allocated_amount: Decimal,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ) -> str:
        """Create a child budget node under a parent."""
        parent = self.nodes.get(parent_id)
        if not parent:
            raise ValueError(f"Parent node {parent_id} not found")
        
        if allocated_amount > parent.unallocated_budget:
            raise ValueError(f"Insufficient budget. Available: {parent.unallocated_budget}")
        
        child = BudgetNode(
            name=name,
            total_budget=allocated_amount,
            allocated_budget=allocated_amount,
            parent_id=parent_id,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )
        
        # Update parent
        parent.children_ids.add(child.id)
        parent.allocated_budget += allocated_amount
        parent.updated_at = datetime.now()
        
        self.nodes[child.id] = child
        
        # Record transaction
        self._record_transaction(
            parent_id, allocated_amount, 
            f"Budget allocation to '{name}'", "allocation"
        )
        
        logger.info(f"Created child budget '{name}' with {allocated_amount} under '{parent.name}'")
        return child.id

    def spend_budget(self, node_id: str, amount: Decimal, description: str = "") -> bool:
        """Record budget expenditure."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        if node.status != BudgetStatus.ACTIVE:
            raise ValueError(f"Budget node is not active: {node.status}")
        
        if amount > node.available_budget:
            raise ValueError(f"Insufficient budget. Available: {node.available_budget}")
        
        # Update node
        node.used_budget += amount
        node.updated_at = datetime.now()
        
        # Check if budget is exhausted
        if node.available_budget <= 0:
            node.status = BudgetStatus.EXHAUSTED
            self._create_alert(node_id, AlertType.BUDGET_EXHAUSTED, 
                            f"Budget for '{node.name}' is exhausted")
        
        # Check thresholds
        self._check_thresholds(node_id)
        
        # Record transaction
        self._record_transaction(node_id, amount, description, "expense")
        
        logger.info(f"Spent {amount} from '{node.name}': {description}")
        return True

    def reallocate_budget(self, from_node_id: str, to_node_id: str, amount: Decimal) -> bool:
        """Reallocate budget between nodes at the same level."""
        from_node = self.nodes.get(from_node_id)
        to_node = self.nodes.get(to_node_id)
        
        if not from_node or not to_node:
            raise ValueError("One or both nodes not found")
        
        if from_node.parent_id != to_node.parent_id:
            raise ValueError("Nodes must have the same parent for reallocation")
        
        if amount > from_node.available_budget:
            raise ValueError(f"Insufficient budget to reallocate. Available: {from_node.available_budget}")
        
        # Update nodes
        from_node.total_budget -= amount
        from_node.allocated_budget -= amount
        from_node.updated_at = datetime.now()
        
        to_node.total_budget += amount
        to_node.allocated_budget += amount
        to_node.updated_at = datetime.now()
        
        # Record transactions
        self._record_transaction(
            from_node_id, amount, 
            f"Reallocated to '{to_node.name}'", "reallocation"
        )
        self._record_transaction(
            to_node_id, -amount, 
            f"Reallocated from '{from_node.name}'", "reallocation"
        )
        
        logger.info(f"Reallocated {amount} from '{from_node.name}' to '{to_node.name}'")
        return True

    def get_budget_hierarchy(self) -> Dict:
        """Get the complete budget hierarchy."""
        if not self.root_node_id:
            return {}
        
        def build_tree(node_id: str) -> Dict:
            node = self.nodes[node_id]
            tree = {
                'node': node,
                'children': []
            }
            
            for child_id in node.children_ids:
                tree['children'].append(build_tree(child_id))
            
            return tree
        
        return build_tree(self.root_node_id)

    def get_budget_report(self, node_id: str) -> Dict:
        """Generate budget report for a node and its children."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        def calculate_totals(node_id: str) -> Tuple[Decimal, Decimal]:
            current = self.nodes[node_id]
            total_budget = current.total_budget
            total_used = current.used_budget
            
            for child_id in current.children_ids:
                child_budget, child_used = calculate_totals(child_id)
                # Don't double count - child budgets are part of parent allocation
            
            return total_budget, total_used
        
        total_budget, total_used = calculate_totals(node_id)
        
        return {
            'node_id': node_id,
            'name': node.name,
            'total_budget': total_budget,
            'used_budget': total_used,
            'available_budget': total_budget - total_used,
            'usage_percentage': float(total_used / total_budget) if total_budget > 0 else 0,
            'status': node.status,
            'children_count': len(node.children_ids),
            'last_updated': node.updated_at
        }

    def get_active_alerts(self) -> List[BudgetAlert]:
        """Get all unacknowledged alerts."""
        return [alert for alert in self.alerts if not alert.acknowledged]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def _check_thresholds(self, node_id: str):
        """Check and create threshold alerts."""
        node = self.nodes[node_id]
        usage_pct = node.usage_percentage
        
        if usage_pct >= node.critical_threshold:
            self._create_alert(
                node_id, AlertType.THRESHOLD_CRITICAL,
                f"Critical: '{node.name}' at {usage_pct:.1%} usage",
                node.critical_threshold, usage_pct
            )
        elif usage_pct >= node.warning_threshold:
            self._create_alert(
                node_id, AlertType.THRESHOLD_WARNING,
                f"Warning: '{node.name}' at {usage_pct:.1%} usage",
                node.warning_threshold, usage_pct
            )

    def _create_alert(
        self, 
        node_id: str, 
        alert_type: AlertType, 
        message: str,
        threshold_value: float = 0.0,
        current_usage: float = 0.0
    ):
        """Create a new alert."""
        alert = BudgetAlert(
            node_id=node_id,
            alert_type=alert_type,
            message=message,
            threshold_value=threshold_value,
            current_usage=current_usage
        )
        self.alerts.append(alert)
        logger.warning(f"Alert created: {message}")

    def _record_transaction(
        self, 
        node_id: str, 
        amount: Decimal, 
        description: str, 
        transaction_type: str
    ):
        """Record a budget transaction."""
        transaction = BudgetTransaction(
            node_id=node_id,
            amount=amount,
            description=description,
            transaction_type=transaction_type
        )
        self.transactions.append(transaction)

    def get_transactions(self, node_id: Optional[str] = None) -> List[BudgetTransaction]:
        """Get transactions, optionally filtered by node."""
        if node_id:
            return [t for t in self.transactions if t.node_id == node_id]
        return self.transactions.copy()