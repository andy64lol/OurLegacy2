import os
from typing import Any


class Colors:
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
        return f"{color_code}{text}{cls.END}"


def create_progress_bar(current: int, maximum: int, width: int = 20, color: str = Colors.GREEN) -> str:
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = int((current / maximum) * width)
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = (current / maximum) * 100
    return f"[{Colors.wrap(filled, color)}{empty}] {percentage:.1f}%"


def create_separator(char: str = "=", length: int = 60) -> str:
    return char * length


def create_section_header(title: str, char: str = "=", width: int = 60) -> str:
    padding = (width - len(title) - 2) // 2
    header_text = f"{char * padding} {title} {char * padding}"
    return Colors.wrap(header_text, f"{Colors.CYAN}{Colors.BOLD}")


def get_rarity_color(rarity: str) -> str:
    mapping = {
        "common": Colors.COMMON,
        "uncommon": Colors.UNCOMMON,
        "rare": Colors.RARE,
        "epic": Colors.EPIC,
        "legendary": Colors.LEGENDARY,
    }
    return mapping.get((rarity or "common").lower(), Colors.WHITE)
