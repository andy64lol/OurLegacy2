import os
import time
from typing import Any


class Colors:
    """ANSI color codes for terminal output"""
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
        return f"{color_code}{text}{cls.END}"


def clear_screen():
    """Clear the terminal screen."""
    time.sleep(1)
    command = 'cls' if os.name == 'nt' else 'clear'
    os.system(command)


def create_progress_bar(current: int,
                        maximum: int,
                        width: int = 20,
                        color: str = Colors.GREEN) -> str:
    """Create a visual progress bar."""
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = int((current / maximum) * width)
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = (current / maximum) * 100
    return f"[{Colors.wrap(filled, color)}{empty}] {percentage:.1f}%"


def create_separator(char: str = "=", length: int = 60) -> str:
    """Create a visual separator line."""
    return char * length


def create_section_header(title: str, char: str = "=", width: int = 60) -> str:
    """Create a decorative section header."""
    padding = (width - len(title) - 2) // 2
    header_text = f"{char * padding} {title} {char * padding}"
    return Colors.wrap(header_text, f"{Colors.CYAN}{Colors.BOLD}")


def display_welcome_screen(lang: Any, game_instance: Any):
    """Display welcome screen and handle menu."""
    from main import ask
    while True:
        clear_screen()
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("=" * 60)
        print(f"             {lang.get('game_title_display')}")
        print(f"       {lang.get('game_subtitle_display')}")
        print("=" * 60)
        print(f"{Colors.END}")
        print(lang.get("welcome_message"))
        print(
            "Choose your path wisely, for every decision shapes your destiny.\n"
        )
        print(
            f"{Colors.BOLD}{Colors.CYAN}=== {lang.get('main_menu')} ==={Colors.END}"
        )
        print(f"{Colors.CYAN}1.{Colors.END} {lang.get('new_game')}")
        print(f"{Colors.CYAN}2.{Colors.END} {lang.get('load_game')}")
        print(f"{Colors.CYAN}3.{Colors.END} {lang.get('settings')}")
        print(f"{Colors.CYAN}4.{Colors.END} {lang.get('mods')}")
        print(f"{Colors.CYAN}5.{Colors.END} {lang.get('quit')}\n")

        choice = ask(f"{Colors.CYAN}Choose an option (1-5): {Colors.END}")
        if choice == "1":
            return "new_game"
        if choice == "2":
            return "load_game"
        if choice == "3":
            game_instance.settings_welcome()
        if choice == "4":
            game_instance.mods_welcome()
        if choice == "5":
            print(lang.get("thank_exit"))
            clear_screen()
            import sys
            sys.exit(0)


def display_main_menu(lang: Any, player: Any, area_name: str, menu_max: str):
    """Display the main game menu options."""
    from utilities.battle import create_hp_mp_bar
    print(f"\n{Colors.BOLD}=== {lang.get('main_menu')} ==={Colors.END}")
    print(lang.get("current_location", area=area_name))

    # Time and weather
    display_hour = int(player.hour)
    display_minute = int((player.hour - display_hour) * 60)
    time_str = lang.get("current_time",
                        hour=f"{display_hour:02d}:{display_minute:02d}")
    day_str = lang.get("current_day", day=str(player.day))
    weather_desc = player.get_weather_description(lang)
    print(f"{Colors.YELLOW}{time_str} | {day_str}{Colors.END}")
    print(f"{Colors.CYAN}{weather_desc}{Colors.END}")

    print(f"{Colors.CYAN}1.{Colors.END} {lang.get('explore')}")
    print(f"{Colors.CYAN}2.{Colors.END} {lang.get('view_character')}")
    print(f"{Colors.CYAN}3.{Colors.END} {lang.get('travel')}")
    print(f"{Colors.CYAN}4.{Colors.END} {lang.get('inventory')}")
    print(f"{Colors.CYAN}5.{Colors.END} {lang.get('missions')}")
    print(f"{Colors.CYAN}6.{Colors.END} {lang.get('fight_boss')}")
    print(f"{Colors.CYAN}7.{Colors.END} {lang.get('tavern')}")
    print(f"{Colors.CYAN}8.{Colors.END} {lang.get('shop')}")
    print(f"{Colors.CYAN}9.{Colors.END} {lang.get('alchemy')}")
    print(f"{Colors.CYAN}10.{Colors.END} {lang.get('elite_market')}")
    print(f"{Colors.CYAN}11.{Colors.END} {lang.get('rest')}")
    print(f"{Colors.CYAN}12.{Colors.END} {lang.get('companions')}")
    print(f"{Colors.CYAN}13.{Colors.END} {lang.get('dungeons')}")
    print(f"{Colors.CYAN}14.{Colors.END} {lang.get('challenges')}")

    if player.current_area == "your_land":
        print(
            f"{Colors.CYAN}15.{Colors.END} {lang.get('pet_shop', 'Pet Shop')}")
    print(f"{Colors.CYAN}16.{Colors.END} {lang.get('settings', 'Settings')}")

    if player.current_area == "your_land":
        print(
            f"{Colors.YELLOW}17.{Colors.END} {lang.get('furnish_home', 'Furnish Home')}"
        )
        print(
            f"{Colors.YELLOW}18.{Colors.END} {lang.get('build_structures', 'Build Structures')}"
        )
        print(f"{Colors.YELLOW}19.{Colors.END} {lang.get('farm', 'Farm')}")
        print(
            f"{Colors.YELLOW}20.{Colors.END} {lang.get('training', 'Training')}"
        )
        print(f"{Colors.CYAN}21.{Colors.END} {lang.get('save_game')}")
        print(f"{Colors.CYAN}22.{Colors.END} {lang.get('load_game')}")
        print(f"{Colors.CYAN}23.{Colors.END} {lang.get('claim_rewards')}")
        print(f"{Colors.CYAN}24.{Colors.END} {lang.get('quit')}")
    else:
        print(f"{Colors.CYAN}17.{Colors.END} {lang.get('save_game')}")
        print(f"{Colors.CYAN}18.{Colors.END} {lang.get('load_game')}")
        print(f"{Colors.CYAN}19.{Colors.END} {lang.get('claim_rewards')}")
        print(f"{Colors.CYAN}20.{Colors.END} {lang.get('quit')}")
