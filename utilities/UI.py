import os
import re
import time
from typing import Any

_ANSI_ESCAPE = re.compile(r'\033\[[0-9;]*m')


def _is_gui_mode() -> bool:
    """Check whether the GUI is active without a hard import cycle."""
    try:
        from utilities.gui import is_gui_mode
        return is_gui_mode()
    except Exception:
        return False


class Colors:
    """ANSI color codes for terminal output.

    In GUI mode, Colors.wrap() returns plain text so no escape sequences
    appear in the customtkinter message panel.
    """
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GOLD = '\033[93m'
    ORANGE = '\033[38;5;208m'
    PURPLE = '\033[95m'
    DARK_GRAY = '\033[90m'
    LIGHT_GRAY = '\033[37m'
    GRAY = '\033[90m'

    # Rarity colors for items
    COMMON = '\033[37m'
    UNCOMMON = '\033[92m'
    RARE = '\033[94m'
    EPIC = '\033[95m'
    LEGENDARY = '\033[93m'

    @staticmethod
    def _color(code: str) -> str:
        return code

    @classmethod
    def wrap(cls, text: str, color_code: str) -> str:
        if _is_gui_mode():
            return text
        return f"{color_code}{text}{cls.END}"

    @staticmethod
    def strip(text: str) -> str:
        """Remove all ANSI escape sequences from *text*."""
        return _ANSI_ESCAPE.sub('', text)


def clear_screen():
    """Clear the terminal screen (no-op in GUI mode)."""
    if _is_gui_mode():
        return
    time.sleep(1)
    command = 'cls' if os.name == 'nt' else 'clear'
    os.system(command)


def create_progress_bar(current: int,
                        maximum: int,
                        width: int = 20,
                        color: str = Colors.GREEN) -> str:
    """Create a visual progress bar.

    In GUI mode, no ANSI color codes are embedded so the bar renders cleanly
    inside the customtkinter message panel.
    """
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = int((current / maximum) * width)
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = (current / maximum) * 100
    if _is_gui_mode():
        return f"[{filled}{empty}] {percentage:.1f}%"
    return f"[{Colors.wrap(filled, color)}{empty}] {percentage:.1f}%"


def create_separator(char: str = "=", length: int = 60) -> str:
    """Create a visual separator line."""
    return char * length


def create_section_header(title: str, char: str = "=", width: int = 60) -> str:
    """Create a decorative section header.

    Returns a plain-text header in GUI mode.
    """
    padding = (width - len(title) - 2) // 2
    header_text = f"{char * padding} {title} {char * padding}"
    if _is_gui_mode():
        return header_text
    return Colors.wrap(header_text, f"{Colors.CYAN}{Colors.BOLD}")


def display_welcome_screen(lang: Any, game_instance: Any):
    """Removed TUI welcome screen — GUI handles this via WelcomeView."""
    return None


def display_main_menu(lang: Any, player: Any, area_name: str, menu_max: str):
    """Removed TUI main menu — GUI handles this via sidebar navigation."""
    return None
