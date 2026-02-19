"""
Additional ASCII art and graphics for cyberpunk theme
"""

from cyberpunk_ui import Colors

class ASCIIArt:
    """Collection of cyberpunk ASCII art"""
    
    @staticmethod
    def circuit_pattern() -> str:
        """Electronic circuit pattern"""
        return f"""
{Colors.NEON_GREEN}
    ┌─┬─┐ ╔═══╗ ┌───┬───┐ ╭─╮ ╔═══╗
    │ │ │ ║ ▓ ║ │ ▓ │ ▓ │ │▓│ ║ ▓ ║
    ├─┼─┤ ╚═╤═╝ ├───┼───┤ ╰─╯ ╚═╤═╝
    │ │ │   │   │ ▓ │ ▓ │       │
    └─┴─┘   ╨   └───┴───┘       ╨
{Colors.RESET}"""
    
    @staticmethod
    def cyber_skull() -> str:
        """Cyberpunk skull logo"""
        return f"""
{Colors.NEON_MAGENTA}
        ███████████████████
      ███                 ███
    ███   ███         ███   ███
   ██   ██████       ██████   ██
  ██   ███████       ███████   ██
 ██     █████         █████     ██
 ██                             ██
 ██       ███████████████       ██
 ██     ███             ███     ██
  ██   ███   ███   ███   ███   ██
   ██   ██   ███   ███   ██   ██
    ███   ███████████████   ███
      ███                 ███
        ███████████████████
{Colors.RESET}"""
    
    @staticmethod
    def data_stream() -> str:
        """Flowing data visualization"""
        return f"""
{Colors.NEON_CYAN}
║ 01001000 ║ 01100001 ║ 01100011 ║
╫═══════════╫═══════════╫═══════════╫
║ 01101011 ║ 01100101 ║ 01110010 ║
╫═══════════╫═══════════╫═══════════╫
║ 01110011 ║ 00100000 ║ 01110100 ║
{Colors.RESET}"""
    
    @staticmethod
    def neural_network() -> str:
        """Neural network visualization"""
        return f"""
{Colors.ELECTRIC_BLUE}
    ●───────●───────●
   ╱│╲     ╱│╲     ╱│╲
  ● │ ●   ● │ ●   ● │ ●
   ╲│╱     ╲│╱     ╲│╱
    ●───────●───────●
   ╱│╲     ╱│╲     ╱│╲
  ● │ ●   ● │ ●   ● │ ●
   ╲│╱     ╲│╱     ╲│╱
    ●───────●───────●
{Colors.RESET}"""
    
    @staticmethod
    def warning_banner() -> str:
        """Warning/alert banner"""
        return f"""
{Colors.NEON_YELLOW}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️  WARNING: UNAUTHORIZED ACCESS DETECTED  ⚠️                   ║
║                                                                  ║
║  INITIATING COUNTERMEASURES...                                   ║
║  TRACING CONNECTION...                                           ║
║  DEPLOYING ICE...                                                ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    
    @staticmethod
    def system_monitor() -> str:
        """System monitoring display"""
        return f"""
{Colors.NEON_GREEN}
┌─ SYSTEM MONITOR ──────────────────────────────────────────────┐
│                                                               │
│ CPU: {Colors.NEON_CYAN}████████████░░░░  {Colors.NEON_YELLOW}78%{Colors.NEON_GREEN}                        │
│ RAM: {Colors.NEON_CYAN}██████████████░░  {Colors.NEON_YELLOW}92%{Colors.NEON_GREEN}                        │
│ NET: {Colors.NEON_CYAN}████░░░░░░░░░░░░  {Colors.NEON_YELLOW}23%{Colors.NEON_GREEN}                        │
│ ICE: {Colors.NEON_MAGENTA}██████████████████  {Colors.NEON_YELLOW}ACTIVE{Colors.NEON_GREEN}                   │
│                                                               │
│ PROCESSES: 47 | THREADS: 234 | UPTIME: 15:42:33              │
└───────────────────────────────────────────────────────────────┘
{Colors.RESET}"""