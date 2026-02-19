import sys
import tty
import termios
from typing import List, Optional, Union, Callable, Any
from dataclasses import dataclass

class InteractivePrompts:
    """Enhanced interactive prompts with rich UI elements"""
    
    def __init__(self):
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m', 
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m'
        }
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def display_header(self, text: str):
        """Display a section header"""
        print(f"\n{self._colorize('=' * 60, 'blue')}")
        print(f"{self._colorize(text.center(60), 'bold')}")
        print(f"{self._colorize('=' * 60, 'blue')}\n")
    
    def display_info(self, text: str):
        """Display info message"""
        print(f"{self._colorize('ℹ', 'blue')} {text}")
    
    def display_success(self, text: str):
        """Display success message"""
        print(f"{self._colorize('✓', 'green')} {self._colorize(text, 'green')}")
    
    def display_error(self, text: str):
        """Display error message"""
        print(f"{self._colorize('✗', 'red')} {self._colorize(text, 'red')}")
    
    def display_warning(self, text: str):
        """Display warning message"""
        print(f"{self._colorize('⚠', 'yellow')} {self._colorize(text, 'yellow')}")
    
    def display_box(self, lines: List[str]):
        """Display text in a box"""
        max_width = max(len(line) for line in lines) + 4
        print(f"{self._colorize('┌' + '─' * (max_width - 2) + '┐', 'cyan')}")
        for line in lines:
            padding = max_width - len(line) - 3
            print(f"{self._colorize('│', 'cyan')} {line}{' ' * padding}{self._colorize('│', 'cyan')}")
        print(f"{self._colorize('└' + '─' * (max_width - 2) + '┘', 'cyan')}")
    
    def text_input(self, prompt: str, default: str = "", required: bool = False) -> str:
        """Get text input with validation"""
        default_text = f" [{default}]" if default else ""
        required_text = " *" if required else ""
        
        while True:
            try:
                response = input(f"{prompt}{default_text}{required_text}: ").strip()
                if not response and default:
                    return default
                if required and not response:
                    self.display_error("This field is required")
                    continue
                return response
            except KeyboardInterrupt:
                raise
    
    def multiline_text_input(self, prompt: str, default: str = "", placeholder: str = "") -> str:
        """Get multiline text input"""
        print(f"{prompt}")
        if placeholder:
            print(f"{self._colorize(placeholder, 'cyan')}")
        if default:
            print(f"Current: {default}")
        
        print("Enter text (press Ctrl+D when finished):")
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        except KeyboardInterrupt:
            raise
        
        result = '\n'.join(lines).strip()
        return result if result else default
    
    def slider_input(self, prompt: str, min_value: int = 1, max_value: int = 5, 
                    default: int = 1, step: int = 1, 
                    show_value: Optional[Callable[[int], str]] = None) -> int:
        """Interactive slider input"""
        current = default
        
        while True:
            # Display slider
            print(f"\n{prompt}")
            slider_width = 40
            position = int(((current - min_value) / (max_value - min_value)) * slider_width)
            
            slider = '─' * position + '●' + '─' * (slider_width - position)
            print(f"│{slider}│")
            print(f"{min_value}{' ' * (slider_width - len(str(min_value)) - len(str(max_value)))}{max_value}")
            
            value_display = show_value(current) if show_value else str(current)
            print(f"Current value: {self._colorize(value_display, 'bold')}")
            print("\nUse ←/→ arrows, +/- keys, or enter number directly")
            print("Press Enter to confirm, 'q' to cancel")
            
            try:
                choice = input("> ").strip().lower()
                
                if choice == 'q':
                    raise KeyboardInterrupt()
                elif choice == '':
                    return current
                elif choice in ['<', 'left', '-']:
                    current = max(min_value, current - step)