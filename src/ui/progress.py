import time
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math

@dataclass
class ProgressState:
    current: int = 0
    total: int = 100
    start_time: float = field(default_factory=time.time)
    description: str = ""
    status: str = "running"  # running, completed, error, paused
    
    @property
    def percentage(self) -> float:
        return (self.current / max(self.total, 1)) * 100
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    @property
    def eta(self) -> Optional[float]:
        if self.current == 0:
            return None
        rate = self.current / self.elapsed_time
        remaining = self.total - self.current
        return remaining / rate if rate > 0 else None
    
    @property
    def eta_formatted(self) -> str:
        eta = self.eta
        if eta is None:
            return "Unknown"
        return str(timedelta(seconds=int(eta)))

class ProgressTracker:
    def __init__(self):
        self._states: Dict[str, ProgressState] = {}
        self._callbacks: Dict[str, list] = {}
        self._lock = threading.RLock()
    
    def create_progress(self, task_id: str, total: int, description: str = "") -> ProgressState:
        with self._lock:
            state = ProgressState(total=total, description=description)
            self._states[task_id] = state
            self._callbacks[task_id] = []
            return state
    
    def update_progress(self, task_id: str, current: int, description: str = None):
        with self._lock:
            if task_id not in self._states:
                return
            
            state = self._states[task_id]
            state.current = min(current, state.total)
            
            if description:
                state.description = description
            
            if state.current >= state.total:
                state.status = "completed"
            
            # Notify callbacks
            for callback in self._callbacks.get(task_id, []):
                try:
                    callback(state)
                except Exception:
                    pass
    
    def increment_progress(self, task_id: str, amount: int = 1, description: str = None):
        with self._lock:
            if task_id not in self._states:
                return
            state = self._states[task_id]
            self.update_progress(task_id, state.current + amount, description)
    
    def get_progress(self, task_id: str) -> Optional[ProgressState]:
        return self._states.get(task_id)
    
    def complete_progress(self, task_id: str):
        with self._lock:
            if task_id in self._states:
                state = self._states[task_id]
                state.current = state.total
                state.status = "completed"
                self._notify_callbacks(task_id)
    
    def error_progress(self, task_id: str, error_msg: str = ""):
        with self._lock:
            if task_id in self._states:
                state = self._states[task_id]
                state.status = "error"
                state.description = error_msg or state.description
                self._notify_callbacks(task_id)
    
    def add_callback(self, task_id: str, callback: Callable[[ProgressState], None]):
        with self._lock:
            if task_id not in self._callbacks:
                self._callbacks[task_id] = []
            self._callbacks[task_id].append(callback)
    
    def _notify_callbacks(self, task_id: str):
        state = self._states.get(task_id)
        if not state:
            return
        
        for callback in self._callbacks.get(task_id, []):
            try:
                callback(state)
            except Exception:
                pass
    
    def cleanup(self, task_id: str):
        with self._lock:
            self._states.pop(task_id, None)
            self._callbacks.pop(task_id, None)

# Global progress tracker instance
progress_tracker = ProgressTracker()