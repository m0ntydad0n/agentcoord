import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

class TaskStorage:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.db_path = self.storage_path / "tasks.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    tags TEXT,
                    data TEXT,
                    created_at TEXT,
                    claimed_by TEXT,
                    claimed_at TEXT,
                    completed_at TEXT,
                    error TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS locks (
                    resource TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL
                )
            ''')
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                task = dict(row)
                task['tags'] = json.loads(task['tags']) if task['tags'] else []
                task['data'] = json.loads(task['data']) if task['data'] else {}
                return task
        return None
    
    def get_stale_tasks(self, threshold: datetime) -> List[Dict[str, Any]]:
        """Get tasks older than threshold that haven't been claimed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE created_at < ? AND claimed_by IS NULL",
                (threshold.isoformat(),)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def remove_task(self, task_id: str):
        """Remove a task from storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    
    def get_orphaned_locks(self) -> List[Dict[str, Any]]:
        """Get locks that don't have corresponding active workers"""
        # This would need to cross-reference with worker storage
        # For now, return locks older than 1 hour
        threshold = datetime.now() - tim