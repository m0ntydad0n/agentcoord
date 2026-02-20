import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # New status for tasks with unmet dependencies

@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus
    agent_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    result: Optional[str] = None
    depends_on: List[str] = None  # New field for task dependencies
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if self.depends_on is None:
            self.depends_on = []

class TaskQueue:
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result TEXT,
                    depends_on TEXT  -- JSON array of task IDs
                )
            ''')
            conn.commit()
    
    def create_task(self, title: str, description: str, depends_on: List[str] = None) -> Task:
        """Create a new task with optional dependencies."""
        task_id = str(uuid.uuid4())
        depends_on = depends_on or []
        
        # Validate dependencies exist
        for dep_id in depends_on:
            if not self.get_task(dep_id):
                raise ValueError(f"Dependency task {dep_id} does not exist")
        
        # Detect circular dependencies
        if self._has_circular_dependency(task_id, depends_on):
            raise ValueError("Circular dependency detected")
        
        # Determine initial status
        status = TaskStatus.BLOCKED if depends_on else TaskStatus.PENDING
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=status,
            depends_on=depends_on
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO tasks (id, title, description, status, agent_id, 
                                 created_at, updated_at, result, depends_on)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id, task.title, task.description, task.status.value,
                task.agent_id, task.created_at, task.updated_at, task.result,
                json.dumps(task.depends_on)
            ))
            conn.commit()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Task(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                status=TaskStatus(row['status']),
                agent_id=row['agent_id'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                result=row['result'],
                depends_on=json.loads(row['depends_on'] or '[]')
            )
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to be claimed (no unmet dependencies)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM tasks WHERE status = ?', (TaskStatus.PENDING.value,))
            rows = cursor.fetchall()
            
            ready_tasks = []
            for row in rows:
                task = Task(
                    id=row['id'],
                    title=row['title'],
                    description=row['description'],
                    status=TaskStatus(row['status']),
                    agent_id=row['agent_id'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    result=row['result'],
                    depends_on=json.loads(row['depends_on'] or '[]')
                )
                
                # Check if all dependencies are completed
                if self._dependencies_completed(task.depends_on):
                    ready_tasks.append(task)
            
            return ready_tasks
    
    def claim_task(self, agent_id: str) -> Optional[Task]:
        """Claim an available task, respecting dependencies."""
        ready_tasks = self.get_ready_tasks()
        
        if not ready_tasks:
            return None
        
        # Claim the first ready task
        task = ready_tasks[0]
        task.status = TaskStatus.CLAIMED
        task.agent_id = agent_id
        task.updated_at = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE tasks SET status = ?, agent_id = ?, updated_at = ?
                WHERE id = ?
            ''', (task.status.value, task.agent_id, task.updated_at, task.id))
            conn.commit()
        
        return task
    
    def complete_task(self, task_id: str, result: str = None) -> bool:
        """Mark a task as completed and check for newly available tasks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            if not cursor.fetchone():
                return False
            
            # Update task status
            conn.execute('''
                UPDATE tasks SET status = ?, result = ?, updated_at = ?
                WHERE id = ?
            ''', (TaskStatus.COMPLETED.value, result, datetime.now().isoformat(), task_id))
            
            # Check for newly available tasks
            self._update_blocked_tasks(conn)
            conn.commit()
            
        return True
    
    def fail_task(self, task_id: str, error: str = None) -> bool:
        """Mark a task as failed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            if not cursor.fetchone():
                return False
            
            conn.execute('''
                UPDATE tasks SET status = ?, result = ?, updated_at = ?
                WHERE id = ?
            ''', (TaskStatus.FAILED.value, error, datetime.now().isoformat(), task_id))
            conn.commit()
            
        return True
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM tasks ORDER BY created_at')
            rows = cursor.fetchall()
            
            return [Task(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                status=TaskStatus(row['status']),
                agent_id=row['agent_id'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                result=row['result'],
                depends_on=json.loads(row['depends_on'] or '[]')
            ) for row in rows]
    
    def get_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """Get the dependency graph for visualization."""
        tasks = self.get_all_tasks()
        graph = {}
        
        for task in tasks:
            graph[task.id] = {
                'title': task.title,
                'status': task.status.value,
                'depends_on': task.depends_on,
                'dependents': []  # Will be populated below
            }
        
        # Add reverse dependencies (dependents)
        for task in tasks:
            for dep_id in task.depends_on:
                if dep_id in graph:
                    graph[dep_id]['dependents'].append(task.id)
        
        return graph
    
    def _dependencies_completed(self, depends_on: List[str]) -> bool:
        """Check if all dependencies are completed."""
        if not depends_on:
            return True
        
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' * len(depends_on))
            cursor = conn.execute(f'''
                SELECT COUNT(*) FROM tasks 
                WHERE id IN ({placeholders}) AND status = ?
            ''', depends_on + [TaskStatus.COMPLETED.value])
            
            completed_count = cursor.fetchone()[0]
            return completed_count == len(depends_on)
    
    def _update_blocked_tasks(self, conn):
        """Update blocked tasks that may now be ready."""
        cursor = conn.execute('SELECT * FROM tasks WHERE status = ?', (TaskStatus.BLOCKED.value,))
        blocked_tasks = cursor.fetchall()
        
        for row in blocked_tasks:
            depends_on = json.loads(row[8] or '[]')  # depends_on column
            if self._dependencies_completed(depends_on):
                conn.execute('''
                    UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
                ''', (TaskStatus.PENDING.value, datetime.now().isoformat(), row[0]))
    
    def _has_circular_dependency(self, task_id: str, depends_on: List[str], visited: set = None) -> bool:
        """Check for circular dependencies using DFS."""
        if visited is None:
            visited = set()
        
        if task_id in visited:
            return True
        
        visited.add(task_id)
        
        for dep_id in depends_on:
            dep_task = self.get_task(dep_id)
            if dep_task and self._has_circular_dependency(dep_id, dep_task.depends_on, visited.copy()):
                return True
        
        return False