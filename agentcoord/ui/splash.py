"""Cyberpunk splash screen implementation."""

import os
import sys
import time
import random
import threading
from pathlib import Path
from typing import Optional

from .theme import LOGO_ASCII_SMALL, MATRIX_CHARS, Colors


class MatrixRain:
    """Matrix rain effect for splash screen."""
    
    def __init__(self, width: int = 80, height: int = 10):
        self.width = width
        self.height = height
        self.drops = [0] * width
        self.running = False
        
    def start(self, duration: float = 0.5):
        """Start matrix rain effect."""
        self.running = True
        start_time = time.time()
        
        # Hide cursor
        print('\033[?25l', end='')
        
        try:
            while self.running and (time.time() - start_time) < duration:
                self._draw_frame()
                time.sleep(0.05)
        finally:
            # Show cursor
            print('\033[?25h', end='')
            # Clear screen area
            for _ in range(self.height + 1):
                print('\033[1A\033[2K', end='')
    
    def stop(self):
        """Stop matrix rain effect.""" 
        self.running = False
        
    def _draw_frame(self):
        """Draw single frame of matrix rain."""
        # Move cursor to start
        print('\033[s', end='')
        
        for y in range(self.height):
            line = ""
            for x in range(self.width):
                if y == self.drops[x]:
                    # Bright green character at drop point
                    char = random.choice(MATRIX_CHARS)
                    line += f"{Colors.GREEN}{Colors.BOLD}{char}{Colors.RESET}"
                elif y == self.drops[x] - 1:
                    # Medium green character above drop
                    char = random.choice(MATRIX_CHARS)
                    line += f"{Colors.GREEN}{char}{Colors.RESET}"
                elif y < self.drops[x] and y >= self.drops[x] - 3:
                    # Dim green characters in tail
                    char = random.choice(MATRIX_CHARS)
                    line += f"{Colors.GREEN}{Colors.DIM}{char}{Colors.RESET}"
                else:
                    line += " "
            
            print(line)
            
        # Update drop positions
        for i in range(len(self.drops)):
            if random.random() > 0.95:  # Random reset
                self.drops[i] = 0
            else:
                self.drops[i] += 1
                
        # Reset cursor
        print('\033[u', end='')


def get_system_status() -> dict:
    """Get system status information."""
    try:
        # Try to import and check Redis connection
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        redis_status = f"{Colors.GREEN}●{Colors.RESET} Connected"
        
        # Get counts from Redis
        agent_count = len(r.keys('agent:*')) if r else 0
        task_count = len(r.keys('task:*')) if r else 0
        
    except Exception:
        redis_status = f"{Colors.RED}●{Colors.RESET} Disconnected"
        agent_count = 0
        task_count = 0
    
    return {
        'redis_status': redis_status,
        'agent_count': agent_count,
        'task_count': task_count
    }


def show_splash_screen():
    """Display the cyberpunk splash screen."""
    # Clear screen
    os.system('clear' if os.name == 'posix' else 'cls')
    
    # Matrix rain effect
    print(f"{Colors.GREEN}Initializing neural network...{Colors.RESET}")
    rain = MatrixRain(width=60, height=8)
    rain.start(duration=0.5)
    
    # Show logo
    print(f"{Colors.CYAN}{LOGO_ASCII_SMALL}{Colors.RESET}")
    
    # Get system status
    status = get_system_status()
    
    # Status line
    print(f"{Colors.WHITE}┌─ SYSTEM STATUS {Colors.DIM}{'─' * 47}{Colors.RESET}")
    print(f"{Colors.WHITE}│{Colors.RESET} Redis: {status['redis_status']} | "
          f"Agents: {Colors.CYAN}{status['agent_count']}{Colors.RESET} | "
          f"Tasks: {Colors.YELLOW}{status['task_count']}{Colors.RESET}")
    print(f"{Colors.WHITE}└{'─' * 63}{Colors.RESET}")
    print()


def should_show_splash() -> bool:
    """Check if splash screen should be shown."""
    # Check environment variable
    if os.getenv('AGENTCOORD_NO_SPLASH'):
        return False
        
    # Check session marker file
    marker_file = Path.home() / '.agentcoord' / 'session_splash'
    
    if marker_file.exists():
        # Check if marker is from current session (same PID parent)
        try:
            with open(marker_file, 'r') as f:
                stored_ppid = f.read().strip()
            if stored_ppid == str(os.getppid()):
                return False
        except (IOError, ValueError):
            pass
    
    return True


def mark_splash_shown():
    """Mark that splash screen has been shown for this session."""
    marker_dir = Path.home() / '.agentcoord'
    marker_dir.mkdir(exist_ok=True)
    
    marker_file = marker_dir / 'session_splash'
    try:
        with open(marker_file, 'w') as f:
            f.write(str(os.getppid()))
    except IOError:
        pass  # Ignore if we can't write the marker