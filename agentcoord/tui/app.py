import curses
import sys
from typing import Optional

class TUIApp:
    """Main TUI application class."""
    
    def __init__(self):
        self.stdscr: Optional[curses.window] = None
        self.running = False
    
    def run(self):
        """Run the TUI application."""
        try:
            curses.wrapper(self._main)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"TUI Error: {e}", file=sys.stderr)
            raise
    
    def _main(self, stdscr):
        """Main TUI loop."""
        self.stdscr = stdscr
        self.running = True
        
        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        
        # Setup screen
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(1)  # Non-blocking input
        self.stdscr.timeout(100)  # 100ms timeout
        
        while self.running:
            self._draw()
            self._handle_input()
    
    def _draw(self):
        """Draw the TUI interface."""
        if not self.stdscr:
            return
            
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Title bar
        title = "AgentCoord TUI"
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(0, 0, title.center(width))
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(1))
        
        # Main content
        content = [
            "",
            "Welcome to AgentCoord Interactive Interface",
            "",
            "Commands:",
            "  s - Show status",
            "  l - View logs", 
            "  c - Configuration",
            "  h - Help",
            "  q - Quit",
            "",
            "Press a key to continue..."
        ]
        
        start_row = 2
        for i, line in enumerate(content):
            if start_row + i < height - 1:
                self.stdscr.addstr(start_row + i, 2, line)
        
        # Status bar
        status = "Press 'q' to quit | 'h' for help"
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(height - 1, 0, status.ljust(width))
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(2))
        
        self.stdscr.refresh()
    
    def _handle_input(self):
        """Handle user input."""
        if not self.stdscr:
            return
            
        try:
            key = self.stdscr.getch()
        except:
            return
        
        if key == ord('q') or key == ord('Q'):
            self.running = False
        elif key == ord('s') or key == ord('S'):
            self._show_status()
        elif key == ord('l') or key == ord('L'):
            self._show_logs()
        elif key == ord('c') or key == ord('C'):
            self._show_config()
        elif key == ord('h') or key == ord('H'):
            self._show_help()
    
    def _show_status(self):
        """Show system status."""
        # Placeholder for status display
        pass
    
    def _show_logs(self):
        """Show logs viewer."""
        # Placeholder for logs viewer
        pass
    
    def _show_config(self):
        """Show configuration interface."""
        # Placeholder for configuration
        pass
    
    def _show_help(self):
        """Show help dialog."""
        # Placeholder for help display
        pass