import sys
import threading
import time
from contextlib import contextmanager
from .widgets import Spinner, live_display, worker_display
from .progress import progress_tracker

class ConsoleManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._active_spinners = {}
        self._console_height = 0
        self._last_output_lines = 0
    
    @contextmanager
    def spinner(self, message: str = "Processing..."):
        spinner_id = id(threading.current_thread())
        spinner = Spinner(message)
        
        with self._lock:
            self._active_spinners[spinner_id] = spinner
        
        try:
            spinner.start()
            yield spinner
        finally:
            spinner.stop()
            with self._lock:
                self._active_spinners.pop(spinner_id, None)
    
    @contextmanager
    def progress_task(self, task_id: str, total: int, description: str = ""):
        """Context manager for progress tracking"""
        progress_tracker.create_progress(task_id, total, description)
        live_display.add_task(task_id, description)
        
        try:
            yield progress_tracker.get_progress(task_id)
        finally:
            progress_tracker.complete_progress(task_id)
    
    def update_progress(self, task_id: str, current: int, description: str = None):
        progress_tracker.update_progress(task_id, current, description)
    
    def increment_progress(self, task_id: str, amount: int = 1, description: str = None):
        progress_tracker.increment_progress(task_id, amount, description)
    
    def print_status(self, message: str, level: str = "info"):
        """Print status message with appropriate formatting"""
        colors = {
            "info": "\033[94m",     # Blue
            "success": "\033[92m",  # Green
            "warning": "\033[93m",  # Yellow
            "error": "\033[91m",    # Red
        }
        
        color = colors.get(level, "\033[0m")
        timestamp = time.strftime("%H:%M:%S")
        
        with self._lock:
            print(f"{color}[{timestamp}] {message}\033[0m")
    
    def clear_screen(self):
        print("\033[2J\033[H", end="")
    
    def move_cursor_up(self, lines: int):
        print(f"\033[{lines}A", end="")
    
    def clear_lines(self, lines: int):
        for _ in range(lines):
            print("\033[K\033[1A\033[K")
    
    def show_worker_status(self):
        """Display current worker status"""
        status = worker_display