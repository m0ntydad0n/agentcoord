import redis
import json
from typing import Dict, List, Optional, Set
from .schemas import Coordinator, CoordinatorType, TaskStatus

class HierarchyManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    # Coordinator Registry Operations
    def register_coordinator(self, coordinator: Coordinator) -> bool:
        """Register a new coordinator in the hierarchy"""
        pipe = self.redis.pipeline()
        
        # Store coordinator data
        coord_key = f"coordinator:{coordinator.id}"
        coord_data = {
            "id": coordinator.id,
            "type": coordinator.type.value,
            "parent_id": coordinator.parent_id or "",
            "budget_allocated": coordinator.budget_allocated,
            "budget_used": coordinator.budget_used,
            "status": coordinator.status.value,
            "created_at": coordinator.created_at
        }
        pipe.hset(coord_key, mapping=coord_data)
        
        # Add to type-based sets
        pipe.sadd(f"coordinators:{coordinator.type.value}", coordinator.id)
        
        # Update parent-child relationships
        if coordinator.parent_id:
            pipe.sadd(f"children:{coordinator.parent_id}", coordinator.id)
            pipe.set(f"parent:{coordinator.id}", coordinator.parent_id)
            
        # Add to global coordinator set
        pipe.sadd("coordinators:all", coordinator.id)
        
        results = pipe.execute()
        return all(results)
    
    def get_coordinator(self, coord_id: str) -> Optional[Coordinator]:
        """Retrieve coordinator by ID"""
        coord_key = f"coordinator:{coord_id}"
        data = self.redis.hgetall(coord_key)
        
        if not data:
            return None
            
        return Coordinator(
            id=data[b'id'].decode(),
            type=CoordinatorType(data[b'type'].decode()),
            parent_id=data[b'parent_id'].decode() or None,
            budget_allocated=float(data[b'budget_allocated']),
            budget_used=float(data[b'budget_used']),
            status=TaskStatus(data[b'status'].decode()),
            created_at=data[b'created_at'].decode()
        )
    
    # Parent-Child Relationship Operations
    def get_children(self, coord_id: str) -> Set[str]:
        """Get direct children of a coordinator"""
        return {child.decode() for child in self.redis.smembers(f"children:{coord_id}")}
    
    def get_parent(self, coord_id: str) -> Optional[str]:
        """Get parent of a coordinator"""
        parent = self.redis.get(f"parent:{coord_id}")
        return parent.decode() if parent else None
    
    def get_ancestors(self, coord_id: str) -> List[str]:
        """Get all ancestors (parent, grandparent, etc.) of a coordinator"""
        ancestors = []
        current = coord_id
        
        while True:
            parent = self.get_parent(current)
            if not parent:
                break
            ancestors.append(parent)
            current = parent
            
        return ancestors
    
    def get_descendants(self, coord_id: str) -> Set[str]:
        """Get all descendants (children, grandchildren, etc.) of a coordinator"""
        descendants = set()
        to_process = [coord_id]
        
        while to_process:
            current = to_process.pop()
            children = self.get_children(current)
            descendants.update(children)
            to_process.extend(children)
            
        return descendants
    
    # Budget Cascade Operations
    def allocate_budget(self, coord_id: str, amount: float) -> bool:
        """Allocate budget to a coordinator"""
        pipe = self.redis.pipeline()
        
        # Update coordinator's allocated budget
        pipe.hincrbyfloat(f"coordinator:{coord_id}", "budget_allocated", amount)
        
        # Update budget tracking
        pipe.hincrbyfloat(f"budget:allocated:{coord_id}", "total", amount)
        pipe.hincrbyfloat(f"budget:allocated:{coord_id}", "timestamp", 
                         datetime.utcnow().timestamp())
        
        results = pipe.execute()
        return all(results)
    
    def spend_budget(self, coord_id: str, amount: float) -> bool:
        """Record budget spending by a coordinator"""
        coordinator = self.get_coordinator(coord_id)
        if not coordinator:
            return False
            
        # Check if spending exceeds allocation
        if coordinator.budget_used + amount > coordinator.budget_allocated:
            return False
            
        pipe = self.redis.pipeline()
        
        # Update coordinator's used budget
        pipe.hincrbyfloat(f"coordinator:{coord_id}", "budget_used", amount)
        
        # Track spending in time-series
        timestamp = datetime.utcnow().timestamp()
        pipe.zadd(f"budget:spending:{coord_id}", {str(timestamp): amount})
        
        results = pipe.execute()
        return all(results)
    
    def get_budget_rollup(self, coord_id: str) -> Dict[str, float]:
        """Get budget rollup for coordinator and all descendants"""
        descendants = self.get_descendants(coord_id)
        all_coords = descendants.union({coord_id})
        
        total_allocated = 0.0
        total_used = 0.0
        
        for coord in all_coords:
            coordinator = self.get_coordinator(coord)
            if coordinator:
                total_allocated += coordinator.budget_allocated
                total_used += coordinator.budget_used
                
        return {
            "total_allocated": total_allocated,
            "total_used": total_used,
            "remaining": total_allocated - total_used,
            "utilization_rate": total_used / total_allocated if total_allocated > 0 else 0.0
        }
    
    # Progress Roll-up Operations
    def update_status(self, coord_id: str, status: TaskStatus) -> bool:
        """Update coordinator status"""
        return self.redis.hset(f"coordinator:{coord_id}", "status", status.value)
    
    def get_progress_rollup(self, coord_id: str) -> Dict[str, int]:
        """Get progress statistics for coordinator and descendants"""
        descendants = self.get_descendants(coord_id)
        all_coords = descendants.union({coord_id})
        
        status_counts = {status.value: 0 for status in TaskStatus}
        
        for coord in all_coords:
            coordinator = self.get_coordinator(coord)
            if coordinator:
                status_counts[coordinator.status.value] += 1
                
        return status_counts
    
    # Escalation Chain Operations
    def create_escalation_chain(self, coord_id: str, escalation_levels: List[str]) -> bool:
        """Create escalation chain for a coordinator"""
        chain_key = f"escalation:chain:{coord_id}"
        
        # Store escalation chain as ordered list
        pipe = self.redis.pipeline()
        pipe.delete(chain_key)  # Clear existing chain
        
        for level in escalation_levels:
            pipe.rpush(chain_key, level)
            
        # Set expiration (optional - for cleanup)
        pipe.expire(chain_key, timedelta(days=30))
        
        results = pipe.execute()
        return all(results[1:])  # Skip delete result
    
    def get_escalation_chain(self, coord_id: str) -> List[str]:
        """Get escalation chain for a coordinator"""
        chain_key = f"escalation:chain:{coord_id}"
        return [level.decode() for level in self.redis.lrange(chain_key, 0, -1)]
    
    def escalate_issue(self, coord_id: str, issue_data: Dict) -> Optional[str]:
        """Escalate an issue through the chain"""
        chain = self.get_escalation_chain(coord_id)
        if not chain:
            return None
            
        # Get current escalation level
        escalation_key = f"escalation:current:{coord_id}"
        current_level = self.redis.get(escalation_key)
        current_index = 0
        
        if current_level:
            current_level = current_level.decode()
            try:
                current_index = chain.index(current_level) + 1
            except ValueError:
                current_index = 0
                
        # Check if we've reached the end of the chain
        if current_index >= len(chain):
            return None
            
        next_escalation = chain[current_index]
        
        # Record escalation
        escalation_record = {
            "from": coord_id,
            "to": next_escalation,
            "timestamp": datetime.utcnow().isoformat(),
            "issue": json.dumps(issue_data),
            "level": current_index
        }
        
        pipe = self.redis.pipeline()
        
        # Update current escalation level
        pipe.set(escalation_key, next_escalation)
        
        # Add to escalation history
        pipe.lpush(f"escalation:history:{coord_id}", json.dumps(escalation_record))
        
        # Add to target's escalation queue
        pipe.lpush(f"escalation:queue:{next_escalation}", json.dumps(escalation_record))
        
        pipe.execute()
        return next_escalation
    
    def get_escalation_queue(self, coord_id: str) -> List[Dict]:
        """Get pending escalations for a coordinator"""
        queue_key = f"escalation:queue:{coord_id}"
        escalations = self.redis.lrange(queue_key, 0, -1)
        
        return [json.loads(escalation.decode()) for escalation in escalations]
    
    # Query Operations
    def get_coordinators_by_type(self, coord_type: CoordinatorType) -> Set[str]:
        """Get all coordinators of a specific type"""
        return {coord.decode() for coord in self.redis.smembers(f"coordinators:{coord_type.value}")}
    
    def get_hierarchy_tree(self, root_id: str) -> Dict:
        """Get complete hierarchy tree starting from root"""
        def build_tree(coord_id: str) -> Dict:
            coordinator = self.get_coordinator(coord_id)
            if not coordinator:
                return {}
                
            children = self.get_children(coord_id)
            return {
                "coordinator": coordinator,
                "children": [build_tree(child) for child in children]
            }
            
        return build_tree(root_id)