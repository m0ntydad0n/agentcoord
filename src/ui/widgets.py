import time
import threading
from typing import Optional
from .progress import ProgressState, progress_tracker

class ProgressBar:
    def __init__(self, width: int = 50, fill_char: str = "█", empty_char: str = "░"):
        self.width = width
        self.fill_char = fill_char
        self.empty_char = empty_char
    
    def render(self, progress: ProgressState) -> str:
        percentage = progress.percentage
        filled_width = int(self.width * percentage / 100)
        empty_width = self.width - filled_width
        
        bar = self.fill_char * filled_width + self.empty_char * empty_width
        
        status_color = self._get_status_color(progress.status)
        percentage_str = f"{percentage:5.1f}%"
        eta_str = f"ETA: {progress.eta_formatted}"
        
        return f"{status_color}[{bar}] {percentage_str} | {eta_str} | {progress.description}\033[0m"
    
    def _get_status_color(self, status: str) -> str:
        colors = {
            "running": "\033[94m",    # Blue
            "completed": "\033[92m",  # Green
            "error": "\033[91m",      # Red
            "paused": "\033[93m"      # Yellow
        }
        return colors.get(status, "\033[0m")

class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, message: str = "Loading..."):
        self.message = message
        self.frame_index = 0
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.pulse_intensity = 0
        self.pulse_direction = 1
    
    def start(self):
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
    
    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)
        print("\r\033[K", end="")  # Clear current line
    
    def _animate(self):
        while self.running:
            # Update pulse effect
            self.pulse_intensity += self.pulse_direction * 0.1
            if self.pulse_intensity >= 1:
                self.pulse_direction = -1
            elif self.pulse_intensity <= 0.3:
                self.pulse_direction = 1
            
            # Create pulsing effect with color intensity
            intensity = int(255 * self.pulse_intensity)
            pulse_color = f"\033[38;2;{intensity};{intensity//2};{intensity//4}m"
            
            frame = self.FRAMES[self.frame_index]
            print(f"\r{pulse_color}{frame} {self.message}\033[0m", end="", flush=True)
            
            self.frame_index = (self.frame_index + 1) % len(self.FRAMES)
            time.sleep(0.1)

class LiveProgressDisplay:
    def __init__(self):
        self.active_tasks = {}
        self.display_thread: Optional[threading.Thread] = None
        self.running = False
        self._lock = threading.RLock()
    
    def add_task(self, task_id: str, description: str = ""):
        with self._lock:
            progress_bar = ProgressBar()
            self.active_tasks[task_id] = {
                'progress_bar': progress_bar,
                'last_update': time.time()
            }
            
            # Add callback to track updates
            progress_tracker.add_callback(task_id, self._on_progress_update)
            
            if not self.running:
                self.start_display()
    
    def _on_progress_update(self, state: ProgressState):
        # This callback is triggered when progress updates
        pass
    
    def start_display(self):
        if self.running:
            return
        
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
    
    def stop_display(self):
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=1)
    
    def _display_loop(self):
        while self.running:
            with self._lock:
                # Clear previous lines
                if self.active_tasks:
                    print(f"\033[{len(self.active_tasks)}A\033[J", end="")
                
                # Display each task
                for task_id, task_data in list(self.active_tasks.items()):
                    progress = progress_tracker.get_progress(task_id)
                    if progress:
                        progress_bar = task_data['progress_bar']
                        line = progress_bar.render(progress)
                        print(line)
                        
                        # Remove completed tasks after a delay
                        if progress.status in ["completed", "error"] and \
                           time.time() - task_data['last_update'] > 2:
                            del self.active_tasks[task_id]
                            progress_tracker.cleanup(task_id)
                    else:
                        # Remove tasks without progress state
                        del self.active_tasks[task_id]
            
            time.sleep(0.1)

# Global display instance
live_display = LiveProgressDisplay()

class PulsingWorkerIndicator:
    def __init__(self, worker_id: str, status: str = "active"):
        self.worker_id = worker_id
        self.status = status
        self.pulse_phase = 0
        self.last_update = time.time()
    
    def update_status(self, status: str):
        self.status = status
        self.last_update = time.time()
    
    def render(self) -> str:
        current_time = time.time()
        self.pulse_phase = (current_time * 2) % (2 * math.pi)  # 2 second cycle
        
        # Calculate pulse intensity
        pulse = (math.sin(self.pulse_phase) + 1) / 2  # 0 to 1
        
        status_colors = {
            "active": (0, 255, 100),
            "idle": (100, 100, 100),
            "busy": (255, 165, 0),
            "error": (255, 0, 0)
        }
        
        base_r, base_g, base_b = status_colors.get(self.status, (100, 100, 100))
        
        # Apply pulse effect
        r = int(base_r * (0.5 + 0.5 * pulse))
        g = int(base_g * (0.5 + 0.5 * pulse))
        b = int(base_b * (0.5 + 0.5 * pulse))
        
        color_code = f"\033[38;2;{r};{g};{b}m"
        
        status_icon = {
            "active": "●",
            "idle": "○",
            "busy": "◐",
            "error": "✗"
        }.get(self.status, "○")
        
        return f"{color_code}{status_icon} Worker-{self.worker_id} ({self.status})\033[0m"

class WorkerStatusDisplay:
    def __init__(self):
        self.workers = {}
        self._lock = threading.RLock()
    
    def add_worker(self, worker_id: str, status: str = "active"):
        with self._lock:
            self.workers[worker_id] = PulsingWorkerIndicator(worker_id, status)
    
    def update_worker(self, worker_id: str, status: str):
        with self._lock:
            if worker_id in self.workers:
                self.workers[worker_id].update_status(status)
    
    def remove_worker(self, worker_id: str):
        with self._lock:
            self.workers.pop(worker_id, None)
    
    def render_all(self) -> str:
        with self._lock:
            if not self.workers:
                return ""
            
            lines = ["Workers:"]
            for worker in self.workers.values():
                lines.append(f"  {worker.render()}")
            
            return "\n".join(lines)

# Global worker display
worker_display = WorkerStatusDisplay()