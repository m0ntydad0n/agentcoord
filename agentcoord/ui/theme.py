"""
90s Cyberpunk Terminal Aesthetic for AgentCoord.

Neon colors, ASCII art, retro-futuristic vibes.
Think: WarGames, Hackers, The Matrix.
"""

from rich.console import Console
from rich.theme import Theme
from rich.style import Style

# ============================================================================
# 90S CYBERPUNK COLOR PALETTE
# ============================================================================

CYBERPUNK_THEME = Theme({
    # Primary neon colors
    "neon.green": "bright_green bold",
    "neon.cyan": "bright_cyan bold",
    "neon.magenta": "bright_magenta bold",
    "neon.yellow": "bright_yellow bold",

    # Status colors
    "status.success": "bright_green",
    "status.working": "bright_cyan",
    "status.warning": "bright_yellow",
    "status.error": "bright_red bold",
    "status.pending": "bright_black",

    # Priority colors
    "priority.critical": "bright_red bold blink",
    "priority.high": "bright_red",
    "priority.medium": "bright_yellow",
    "priority.low": "bright_blue",

    # UI elements
    "border": "bright_cyan",
    "header": "bright_magenta bold",
    "title": "bright_green bold",
    "label": "cyan",
    "value": "bright_white",
    "prompt": "bright_yellow",

    # Agent/Task states
    "agent.idle": "bright_black",
    "agent.working": "bright_cyan",
    "agent.done": "bright_green",
    "task.pending": "bright_black",
    "task.claimed": "bright_yellow",
    "task.running": "bright_cyan",
    "task.complete": "bright_green",
    "task.failed": "bright_red",

    # Cost tracking
    "cost.cheap": "bright_green",
    "cost.moderate": "bright_yellow",
    "cost.expensive": "bright_red",

    # Model tiers
    "model.haiku": "bright_green",
    "model.sonnet": "bright_cyan",
    "model.opus": "bright_magenta",
})


# ============================================================================
# ASCII ART
# ============================================================================

LOGO_FULL = r"""
    ___                    __  ______                     __
   /   | ____ ____  ____  / /_/ ____/___  ____  _________/ /
  / /| |/ __ `/ _ \/ __ \/ __/ /   / __ \/ __ \/ ___/ __  /
 / ___ / /_/ /  __/ / / / /_/ /___/ /_/ / /_/ / /  / /_/ /
/_/  |_\__, /\___/_/ /_/\__/\____/\____/\____/_/   \__,_/
      /____/
"""

LOGO_SMALL = r"""
 ▄▀█ █▀▀ █▀▀ █▄░█ ▀█▀ █▀▀ █▀█ █▀█ █▀█ █▀▄
 █▀█ █▄█ ██▄ █░▀█ ░█░ █▄▄ █▄█ █▄█ █▀▄ █▄▀
"""

LOGO_MINIMAL = "[ AGENTCOORD ]"

# Glitch effect characters
GLITCH_CHARS = "░▒▓█▀▄│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌"

# Matrix-style characters
MATRIX_CHARS = "ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ012345789Z:・.\"=*+-<>¦｜╌"

# Box drawing
BOX_SINGLE = {
    'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
    'h': '─', 'v': '│', 't': '┬', 'b': '┴', 'l': '├', 'r': '┤'
}

BOX_DOUBLE = {
    'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
    'h': '═', 'v': '║', 't': '╦', 'b': '╩', 'l': '╠', 'r': '╣'
}

BOX_HEAVY = {
    'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛',
    'h': '━', 'v': '┃', 't': '┳', 'b': '┻', 'l': '┣', 'r': '┫'
}


# ============================================================================
# ICONS & SYMBOLS
# ============================================================================

ICONS = {
    # Status
    'success': '✓',
    'error': '✗',
    'warning': '⚠',
    'info': 'ℹ',

    # Actions
    'play': '▶',
    'pause': '⏸',
    'stop': '⏹',
    'working': '⏳',

    # Entities
    'robot': '🤖',
    'coordinator': '🎯',
    'worker': '👷',
    'task': '📋',
    'agent': '🔧',

    # Progress
    'spinner': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',  # Braille spinner
    'arrow_right': '→',
    'arrow_down': '↓',
    'arrow_up': '↑',

    # Priority
    'critical': '🔴',
    'high': '🟠',
    'medium': '🟡',
    'low': '🔵',

    # Cost
    'dollar': '$',
    'coin': '💰',
    'chart': '📊',

    # Models
    'haiku': '🟢',   # Green - fast & cheap
    'sonnet': '🔵',  # Blue - balanced
    'opus': '🟣',    # Purple - premium
}


# ============================================================================
# PROGRESS BAR STYLES
# ============================================================================

PROGRESS_BARS = {
    'blocks': {
        'complete': '█',
        'incomplete': '░',
        'partial': '▒'
    },
    'arrows': {
        'complete': '▶',
        'incomplete': '▷',
    },
    'dots': {
        'complete': '●',
        'incomplete': '○',
    },
    'squares': {
        'complete': '■',
        'incomplete': '□',
    }
}


# ============================================================================
# BANNER TEMPLATES
# ============================================================================

def get_banner(title: str, subtitle: str = None, width: int = 70) -> str:
    """Generate cyberpunk-style banner."""
    lines = []

    # Top border
    lines.append('╔' + '═' * (width - 2) + '╗')

    # Title (centered)
    title_padded = title.center(width - 4)
    lines.append(f'║ {title_padded} ║')

    # Subtitle if provided
    if subtitle:
        sub_padded = subtitle.center(width - 4)
        lines.append('╠' + '═' * (width - 2) + '╣')
        lines.append(f'║ {sub_padded} ║')

    # Bottom border
    lines.append('╚' + '═' * (width - 2) + '╝')

    return '\n'.join(lines)


def get_section_header(title: str, width: int = 70) -> str:
    """Generate section header with neon styling."""
    left_pad = '━' * 3
    right_pad = '━' * (width - len(title) - len(left_pad) - 2)
    return f"{left_pad} {title} {right_pad}"


def get_status_indicator(status: str) -> str:
    """Get colored status indicator."""
    indicators = {
        'pending': '⏸',
        'claimed': '⏳',
        'working': '▶',
        'complete': '✓',
        'failed': '✗',
        'idle': '○',
        'active': '●',
    }
    return indicators.get(status.lower(), '?')


def get_priority_indicator(priority: int) -> str:
    """Get colored priority indicator (1-5)."""
    if priority >= 5:
        return '🔴'
    elif priority >= 4:
        return '🟠'
    elif priority >= 3:
        return '🟡'
    else:
        return '🔵'


# ============================================================================
# CONSOLE FACTORY
# ============================================================================

def get_console() -> Console:
    """Get configured Rich console with cyberpunk theme."""
    return Console(theme=CYBERPUNK_THEME)


# ============================================================================
# WELCOME MESSAGE
# ============================================================================

WELCOME_MESSAGE = f"""
{LOGO_FULL}

[neon.cyan]Multi-Agent Task Coordination System[/neon.cyan]
[bright_black]Version 0.2.0-alpha | 90s Cyberpunk Edition[/bright_black]

[neon.green]▶ READY TO COORDINATE[/neon.green]
"""
