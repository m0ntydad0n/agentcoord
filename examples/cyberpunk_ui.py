"""
Cyberpunk terminal UI components with 90s aesthetic
"""

import random
import time
from typing import List, Optional

class Colors:
    """ANSI color codes for cyberpunk aesthetic"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Neon colors
    NEON_GREEN = '\033[38;5;46m'
    NEON_CYAN = '\033[38;5;51m'
    NEON_MAGENTA = '\033[38;5;201m'
    NEON_YELLOW = '\033[38;5;226m'
    ELECTRIC_BLUE = '\033[38;5;39m'
    
    # Matrix green variants
    MATRIX_GREEN = '\033[38;5;40m'
    DARK_GREEN = '\033[38;5;22m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_DARK_GRAY = '\033[48;5;235m'

class CyberpunkUI:
    """Main cyberpunk UI class"""
    
    def __init__(self):
        self.width = 80
        self.matrix_chars = "ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ01010101"
        
    def agent_coord_logo(self) -> str:
        """ASCII art logo for AgentCoord"""
        logo = f"""
{Colors.NEON_CYAN}{Colors.BOLD}
    ▄▄▄        ▄████  ▓█████  ███▄    █ ▄▄▄█████▓
   ▒████▄     ██▒ ▀█▒ ▓█   ▀  ██ ▀█   █ ▓  ██▒ ▓▒
   ▒██  ▀█▄  ▒██░▄▄▄░ ▒███   ▓██  ▀█ ██▒▒ ▓██░ ▒░
   ░██▄▄▄▄██ ░▓█  ██▓ ▒▓█  ▄ ▓██▒  ▐▌██▒░ ▓██▓ ░ 
    ▓█   ▓██▒░▒▓███▀▒ ░▒████▒▒██░   ▓██░  ▒██▒ ░ 
    ▒▒   ▓▒█░ ░▒   ▒  ░░ ▒░ ░░ ▒░   ▒ ▒   ▒ ░░   
     ▒   ▒▒ ░  ░   ░   ░ ░  ░░ ░░   ░ ▒░    ░    
     ░   ▒   ░ ░   ░     ░      ░   ░ ░   ░      
         ░  ░      ░     ░  ░         ░          

{Colors.NEON_MAGENTA}     ▄████▄   ▒█████   ▒█████   ██▀███  ▓█████▄ 
    ▒██▀ ▀█  ▒██▒  ██▒▒██▒  ██▒▓██ ▒ ██▒▒██▀ ██▌
    ▒▓█    ▄ ▒██░  ██▒▒██░  ██▒▓██ ░▄█ ▒░██   █▌
    ▒▓▓▄ ▄██▒▒██   ██░▒██   ██░▒██▀▀█▄  ░▓█▄   ▌
    ▒ ▓███▀ ░░ ████▓▒░░ ████▓▒░░██▓ ▒██▒░▒████▓ 
    ░ ░▒ ▒  ░░ ▒░▒░▒░ ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░ ▒▒▓  ▒ 
      ░  ▒     ░ ▒ ▒░   ░ ▒ ▒░   ░▒ ░ ▒░ ░ ▒  ▒ 
    ░        ░ ░ ░ ▒  ░ ░ ░ ▒    ░░   ░  ░ ░  ░ 
    ░ ░          ░ ░      ░ ░     ░        ░    
    ░                                   ░      
{Colors.RESET}"""
        return logo
    
    def cyber_border(self, width: Optional[int] = None) -> str:
        """Create cyberpunk-style border"""
        w = width or self.width
        border_chars = "▓▒░█▌▐║═╔╗╚╝"
        
        top = f"{Colors.NEON_GREEN}╔" + "═" * (w-2) + f"╗{Colors.RESET}"
        bottom = f"{Colors.NEON_GREEN}╚" + "═" * (w-2) + f"╝{Colors.RESET}"
        
        return top, bottom
    
    def matrix_rain_line(self, length: int = 40) -> str:
        """Generate a line of matrix-style falling characters"""
        chars = [random.choice(self.matrix_chars) for _ in range(length)]
        colors = [Colors.MATRIX_GREEN, Colors.DARK_GREEN, Colors.NEON_GREEN]
        
        line = ""
        for char in chars:
            color = random.choice(colors)
            line += f"{color}{char}"
        
        return line + Colors.RESET
    
    def glitch_text(self, text: str) -> str:
        """Add glitch effect to text"""
        glitch_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = ""
        
        for char in text:
            if random.random() < 0.1:  # 10% chance to glitch
                result += f"{Colors.NEON_MAGENTA}{random.choice(glitch_chars)}{Colors.RESET}"
            else:
                result += char
                
        return result
    
    def status_panel(self, title: str, content: List[str]) -> str:
        """Create a cyberpunk status panel"""
        top, bottom = self.cyber_border(60)
        
        panel = f"\n{top}\n"
        panel += f"{Colors.NEON_CYAN}║ {Colors.BOLD}{title:^56} {Colors.NEON_CYAN}║{Colors.RESET}\n"
        panel += f"{Colors.NEON_GREEN}║" + "─" * 58 + f"║{Colors.RESET}\n"
        
        for line in content:
            formatted_line = f"{line:<56}"
            panel += f"{Colors.NEON_GREEN}║ {Colors.NEON_YELLOW}{formatted_line} {Colors.NEON_GREEN}║{Colors.RESET}\n"
        
        panel += f"{bottom}\n"
        return panel
    
    def terminal_prompt(self) -> str:
        """Cyberpunk-style terminal prompt"""
        return f"{Colors.NEON_GREEN}[{Colors.NEON_CYAN}AGENT{Colors.NEON_GREEN}@{Colors.NEON_MAGENTA}COORD{Colors.NEON_GREEN}]${Colors.RESET} "
    
    def loading_bar(self, progress: int, width: int = 40, label: str = "LOADING") -> str:
        """Animated loading bar with cyberpunk styling"""
        filled = int(width * progress / 100)
        bar = "█" * filled + "░" * (width - filled)
        
        return f"{Colors.NEON_CYAN}[{Colors.NEON_GREEN}{bar}{Colors.NEON_CYAN}] {Colors.NEON_YELLOW}{progress:3d}% {Colors.NEON_MAGENTA}{label}{Colors.RESET}"

def demo():
    """Demonstrate the cyberpunk UI components"""
    ui = CyberpunkUI()
    
    # Clear screen
    print("\033[2J\033[H")
    
    # Show logo
    print(ui.agent_coord_logo())
    
    # Matrix rain effect
    print(f"\n{Colors.NEON_GREEN}INITIALIZING MATRIX CONNECTION...{Colors.RESET}")
    for _ in range(3):
        print(ui.matrix_rain_line(80))
        time.sleep(0.3)
    
    # Status panel
    status_content = [
        "SYSTEM STATUS: ONLINE",
        "AGENTS CONNECTED: 12",
        "ENCRYPTION: AES-256",
        "LAST SYNC: 2024-01-15 15:30:42",
        "THREAT LEVEL: GREEN"
    ]
    print(ui.status_panel("AGENTCOORD CONTROL PANEL", status_content))
    
    # Loading demonstration
    print(f"\n{Colors.NEON_CYAN}ESTABLISHING SECURE CONNECTION...{Colors.RESET}")
    for i in range(0, 101, 10):
        print(f"\r{ui.loading_bar(i, 50, 'CONNECTING')}", end="", flush=True)
        time.sleep(0.2)
    
    print(f"\n\n{Colors.NEON_GREEN}CONNECTION ESTABLISHED{Colors.RESET}")
    print(ui.terminal_prompt(), end="")

if __name__ == "__main__":
    demo()