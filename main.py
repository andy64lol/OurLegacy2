"""
Our Legacy - Text-Based CLI Fantasy RPG Game
A comprehensive exploration and grinding-driven RPG experience
"""

import json
import os
import random
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import difflib
import traceback
import io
from utilities.settings import get_setting, set_setting
from utilities.character import Character
from utilities.battle import BattleSystem
from utilities.spellcasting import SpellCastingSystem
from utilities.save_load import SaveLoadSystem
from utilities.market import MarketAPI
from utilities.language import LanguageManager
from utilities.dungeons import DungeonSystem
from utilities.entities import Enemy, Boss
try:
    import readline
except ImportError:
    readline = None
from utilities.UI import Colors, clear_screen, create_progress_bar, create_separator, create_section_header, display_welcome_screen, display_main_menu
from utilities.shop import visit_specific_shop
from utilities.crafting import visit_alchemy
from utilities.building import build_home, build_structures, farm, training
import re as _re
from utilities.gui import gui_print, gui_safe_input, set_gui_mode, set_main_window, is_gui_mode

# Global color toggle
COLORS_ENABLED = True


class GUIPrint:
    """Redirects sys.stdout writes to the GUI message panel, stripping ANSI codes."""

    _ANSI = _re.compile(r'\033\[[0-9;]*[A-Za-z]')

    def __init__(self, window):
        self._window = window
        self._buf = ""

    def write(self, text: str):
        if not text:
            return
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            clean = self._ANSI.sub('', line).rstrip()
            if clean:
                self._window.add_message(clean)

    def flush(self):
        if self._buf.strip():
            clean = self._ANSI.sub('', self._buf).rstrip()
            if clean:
                self._window.add_message(clean)
            self._buf = ""


def loading_indicator(message: str = "Loading"):
    """Display a loading indicator."""
    gui_print(f"\n{Colors.wrap(message, Colors.YELLOW)}", end="", flush=True)
    for i in range(3):
        time.sleep(0.5)
        gui_print(".", end="", flush=True)
    gui_print()


def get_rarity_color(rarity: str) -> str:
    """Get the color for an item rarity."""
    rarity_colors = {
        "common": Colors.COMMON,
        "uncommon": Colors.UNCOMMON,
        "rare": Colors.RARE,
        "epic": Colors.EPIC,
        "legendary": Colors.LEGENDARY
    }
    return rarity_colors.get(rarity.lower(), Colors.WHITE)


def format_item_name(item_name: str, rarity: str = "common") -> str:
    """Format item name with rarity color."""
    color = get_rarity_color(rarity)
    return Colors.wrap(item_name, color)


def ask(prompt: str,
        valid_choices: Optional[List[str]] = None,
        allow_empty: bool = True,
        case_sensitive: bool = False,
        suggest: bool = True,
        lang: Optional[Any] = None) -> str:
    """Prompt the user for input with optional validation and suggestions.

    - `valid_choices`: list of allowed responses (comparison controlled by `case_sensitive`).
    - `allow_empty`: if False, empty input will be rejected.
    - Returns the stripped input string.
    - In GUI mode, returns '' immediately (GUI views handle interaction).
    """
    try:
        from utilities.gui import is_gui_mode
        if is_gui_mode():
            return ''
    except Exception:
        pass

    if lang is None:

        class MockLang:

            def get(self, key, default=None, **kwargs):
                return key

        lang = MockLang()

    while True:
        try:
            response = input(prompt)
        except EOFError:
            response = ''

        resp = response.strip()

        # Normalize for comparison if case-insensitive
        cmp_resp = resp if case_sensitive else resp.lower()
        # Ensure cmp_choices is always a list[str] for safe membership checks
        cmp_choices: List[str] = []
        if valid_choices:
            cmp_choices = [
                c if case_sensitive else c.lower() for c in valid_choices
            ]

        # Empty handling
        if not resp and allow_empty:
            return resp
        if not resp and not allow_empty:
            continue

        # If no validation requested, accept
        if not valid_choices:
            clear_screen()
            return resp

        # Exact match
        if cmp_choices and cmp_resp in cmp_choices:
            clear_screen()
            return resp

        # If suggestions enabled, show closest matches
        if suggest and cmp_choices:
            close = difflib.get_close_matches(cmp_resp,
                                              cmp_choices,
                                              n=3,
                                              cutoff=0.4)
            if close:
                gui_print(
                    lang.get("did_you_mean_msg",
                             "Did you mean one of these? {close}").format(
                                 close=', '.join(close)))
            else:
                gui_print(
                    lang.get(
                        "invalid_input_choices_msg",
                        "Invalid input. Allowed choices: {choices}").format(
                            choices=', '.join(cmp_choices)))
        else:
            # Fallback to showing valid choices if available
            gui_print(
                lang.get("invalid_input_choices_msg",
                         "Invalid input. Allowed choices: {choices}").format(
                             choices=', '.join(cmp_choices or [])))

        # Retry loop


def _make_completer(options: List[str]):
    """Return a simple readline completer for the provided options."""
    if not readline:
        return None

    opts = sorted(options)

    def completer(text, state):
        matches = [o for o in opts if o.startswith(text)]
        try:
            return matches[state]
        except IndexError:
            return None

    return completer


def enable_tab_completion(options: List[str]):
    """Enable tab-completion for a short period (best-effort)."""
    if not readline:
        return None
    completer = _make_completer(options)
    if completer:
        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')
        return completer
    return None


def disable_tab_completion(prev_completer):
    """Restore previous completer (if any)."""
    if not readline:
        return
    readline.set_completer(prev_completer)


# Market API URL and cooldown (set by Game class when game starts)
game_api = None


class Game:
    """Main game class"""

    def __init__(self):
        self.player: Optional[Character] = None
        self.current_area = "starting_village"
        self.visited_areas: set = set()  # Track visited areas for cutscenes
        self.enemies_data: Dict[str, Any] = {}
        self.areas_data: Dict[str, Any] = {}
        self.items_data: Dict[str, Any] = {}
        self.missions_data: Dict[str, Any] = {}
        self.bosses_data: Dict[str, Any] = {}
        self.classes_data: Dict[str, Any] = {}
        self.spells_data: Dict[str, Any] = {}
        self.effects_data: Dict[str, Any] = {}
        self.companions_data: Dict[str, Any] = {}
        self.dialogues_data: Dict[str, Any] = {}
        self.dungeons_data: Dict[str, Any] = {}
        self.cutscenes_data: Dict[str, Any] = {}
        self.mission_progress: Dict[str, Any] = {
        }  # mission_id -> {current_count, target_count, completed, type}
        self.completed_missions: List[str] = []
        self.market_api: Optional[MarketAPI] = None
        self.crafting_data: Dict[str, Any] = {}
        self.weekly_challenges_data: Dict[str, Any] = {}
        self.housing_data: Dict[str, Any] = {}  # Housing items data
        self.shops_data: Dict[str, Any] = {}  # Shop data
        self.farming_data: Dict[str, Any] = {}  # Farming crops and foods data
        self.pets_data: Dict[str, Any] = {}  # Pet data

        # Challenge tracking
        self.challenge_progress: Dict[str, int] = {
        }  # challenge_id -> progress count
        self.completed_challenges: List[str] = []

        # Dungeon state tracking
        self.current_dungeon: Optional[Dict[str, Any]] = None
        self.dungeon_progress: int = 0
        self.dungeon_rooms: List[Dict[str, Any]] = []
        self.dungeon_state: Dict[str, Any] = {}

        # Initialize Language Manager
        self.lang = LanguageManager(get_setting_func=get_setting,
                                    set_setting_func=set_setting)

        # Mod manager removed

        # Initialize Market API with translation support
        self.market_api = MarketAPI(lang=self.lang, colors=Colors)

        # Initialize Dungeon System
        self.dungeon_system = DungeonSystem(self)

        # Load game data
        self.load_game_data()
        self.load_config()

    def load_game_data(self):
        """Load all game data from JSON files and mods"""
        try:
            with open('data/enemies.json', 'r') as f:
                self.enemies_data = json.load(f)
            with open('data/areas.json', 'r') as f:
                self.areas_data = json.load(f)
            with open('data/items.json', 'r') as f:
                self.items_data = json.load(f)
            with open('data/missions.json', 'r') as f:
                self.missions_data = json.load(f)
            with open('data/bosses.json', 'r') as f:
                self.bosses_data = json.load(f)
            with open('data/classes.json', 'r') as f:
                self.classes_data = json.load(f)
            with open('data/spells.json', 'r') as f:
                self.spells_data = json.load(f)
            with open('data/effects.json', 'r') as f:
                self.effects_data = json.load(f)
            # Optional companions data
            try:
                with open('data/companions.json', 'r') as f:
                    self.companions_data = json.load(f)
            except FileNotFoundError:
                self.companions_data = {}

            # Optional crafting data
            try:
                with open('data/crafting.json', 'r') as f:
                    self.crafting_data = json.load(f)
            except FileNotFoundError:
                self.crafting_data = {}

            # Load dialogues data
            try:
                with open('data/dialogues.json', 'r') as f:
                    self.dialogues_data = json.load(f)
            except FileNotFoundError:
                self.dialogues_data = {}

            # Load cutscenes data
            try:
                with open('data/cutscenes.json', 'r') as f:
                    self.cutscenes_data = json.load(f)
            except FileNotFoundError:
                self.cutscenes_data = {}

            # Load weather and times data
            try:
                with open('data/weather.json', 'r') as f:
                    self.weather_data = json.load(f)
                with open('data/times.json', 'r') as f:
                    self.times_data = json.load(f)
            except FileNotFoundError:
                self.weather_data = {}
                self.times_data = {}

            ## Mod data removed
            # Mod data loading removed

            # mod_areas removed
            # self.areas_data.update(mod_areas) removed

            # mod_items removed
            # self.items_data.update(mod_items) removed

            # mod_missions removed
            # self.missions_data.update(mod_missions) removed

            # mod_bosses removed
            # self.bosses_data.update(mod_bosses) removed

            # mod_spells removed

        except FileNotFoundError as e:
            gui_print(f"Error loading game data: {e}")
            gui_print(self.lang.get("ensure_data_files"))
            sys.exit(1)
        except Exception as e:
            gui_print(f"Error loading game data: {e}")
            gui_print(self.lang.get("ensure_data_files"))

        # Load dungeons data
        try:
            with open('data/dungeons.json', 'r') as f:
                self.dungeons_data = json.load(f)
        except FileNotFoundError:
            self.dungeons_data = {}

        # Load weekly challenges data
        try:
            with open('data/weekly_challenges.json', 'r') as f:
                self.weekly_challenges_data = json.load(f)
            # Initialize challenge progress
            for challenge in self.weekly_challenges_data.get('challenges', []):
                self.challenge_progress[challenge['id']] = 0
        except FileNotFoundError:
            self.weekly_challenges_data = {}

        # Load housing data
        try:
            with open('data/housing.json', 'r') as f:
                self.housing_data = json.load(f)
        except FileNotFoundError:
            self.housing_data = {}

        # Load weather data
        try:
            with open('data/weather.json', 'r') as f:
                self.weather_data = json.load(f)
        except FileNotFoundError:
            self.weather_data = {}

        # Load times data
        try:
            with open('data/times.json', 'r') as f:
                self.times_data = json.load(f)
        except FileNotFoundError:
            self.times_data = {}

        # Load shops data
        try:
            with open('data/shops.json', 'r') as f:
                self.shops_data = json.load(f)
        except FileNotFoundError:
            self.shops_data = {}

        # Load farming data
        try:
            with open('data/farming.json', 'r') as f:
                self.farming_data = json.load(f)
        except FileNotFoundError:
            self.farming_data = {}

    def load_config(self):
        """Load configuration - uses hardcoded defaults since config file is removed"""
        # Set global color toggle to True by default
        global COLORS_ENABLED
        COLORS_ENABLED = True

        # Initialize Market API
        self.market_api = MarketAPI(colors=Colors)
        self.battle_system = BattleSystem(self)
        self.spell_casting_system = SpellCastingSystem(self)
        self.save_load_system = SaveLoadSystem(self)

    def ask(self,
            prompt: str,
            valid_choices: Optional[List[str]] = None,
            allow_empty: bool = True,
            case_sensitive: bool = False,
            suggest: bool = True) -> str:
        """Wrapper for the global ask function to allow Game object to use it.
        
        This method delegates to the global ask function defined in main.py.
        """
        return ask(prompt, valid_choices, allow_empty, case_sensitive, suggest,
                   self.lang)

    def update_weather(self):
        """Update current weather based on area data and probabilities."""
        if not self.player:
            return

        area_data = self.areas_data.get(self.player.current_area, {})
        weather_probs = area_data.get("weather_probabilities", {"sunny": 1.0})

        weathers = list(weather_probs.keys())
        probs = list(weather_probs.values())

        new_weather = random.choices(weathers, weights=probs, k=1)[0]
        self.player.current_weather = new_weather

    def play_cutscene(self, cutscene_id: str):
        """Play a cutscene by ID"""
        if cutscene_id not in self.cutscenes_data:
            gui_print(
                self.lang.get("cutscene_not_found_msg").format(
                    cutscene_id=cutscene_id))
            return

        cutscene = self.cutscenes_data[cutscene_id]
        self._play_cutscene_content(cutscene['content'])

    def _play_cutscene_content(self, content: Dict[str, Any]):
        """Recursively play cutscene content"""
        # Display text
        if 'text' in content:
            gui_print(f"\n{Colors.CYAN}{content['text']}{Colors.END}")

        # Wait
        if 'wait' in content:
            wait_time = content['wait']
            for i in range(wait_time):
                gui_print(".", end="", flush=True)
                time.sleep(1)
            gui_print()

        # Handle choices
        if 'choice' in content:
            choices = content['choice']
            if choices:
                gui_print(self.lang.get("nchoose_your_response"))
                choice_keys = list(choices.keys())
                for i, choice_key in enumerate(choice_keys, 1):
                    gui_print(f"{i}. {choice_key}")

                # Allow skipping with Enter
                choice = ask("Your choice (or press Enter to skip): ").strip()
                if choice and choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(choice_keys):
                        selected_choice = choice_keys[idx]
                        next_content = choices[selected_choice]
                        if isinstance(next_content, dict):
                            self._play_cutscene_content(next_content)
                # If no choice or invalid, continue without recursion

    def display_welcome(self) -> str:
        """Display welcome screen and return choice."""
        return display_welcome_screen(self.lang, self)

    def settings_welcome(self):
        """Settings menu available from welcome screen"""
        from utilities.UI import Colors
        while True:
            clear_screen()
            gui_print(self.lang.get("n_settings"))
            gui_print(
                f"\n{Colors.CYAN}{Colors.BOLD}=== {self.lang.get('settings', 'SETTINGS')} ==={Colors.END}"
            )
            gui_print(
                f"{Colors.CYAN}1.{Colors.END} {self.lang.get('language', 'Language')}"
            )
            gui_print(
                f"{Colors.CYAN}2.{Colors.END} {self.lang.get('display_settings', 'Display/Color Settings')}"
            )
            gui_print(
                f"{Colors.CYAN}3.{Colors.END} {self.lang.get('back', 'Back')}")

            choice = ask(f"{Colors.CYAN}Choose an option (1-3): {Colors.END}")

            if choice == "1":
                self.change_language_menu()
            elif choice == "2":
                self.display_settings_menu()
            elif choice == "3" or not choice:
                break
            else:
                gui_print(self.lang.get("invalid_choice"))

    def display_settings_menu(self):
        """Display settings for colors and display options"""
        from utilities.UI import Colors
        global COLORS_ENABLED

        while True:
            clear_screen()
            gui_print(
                f"\n{Colors.CYAN}{Colors.BOLD}=== {self.lang.get('display_settings', 'DISPLAY SETTINGS')} ==={Colors.END}"
            )

            # Color status
            color_status = f"{Colors.GREEN}ON{Colors.END}" if COLORS_ENABLED else f"{Colors.RED}OFF{Colors.END}"
            gui_print(
                f"\n{Colors.CYAN}1.{Colors.END} {self.lang.get('color_output', 'Color Output')}: {color_status}"
            )
            gui_print(
                f"{Colors.CYAN}2.{Colors.END} {self.lang.get('back', 'Back')}")

            choice = ask(f"{Colors.CYAN}Choose an option (1-2): {Colors.END}")

            if choice == "1":
                # Toggle colors
                if COLORS_ENABLED:
                    COLORS_ENABLED = False
                    set_setting('colors_enabled', False)
                    gui_print(f"\n{Colors.YELLOW}Colors disabled.{Colors.END}")
                else:
                    COLORS_ENABLED = True
                    set_setting('colors_enabled', True)
                    gui_print(f"\n{Colors.GREEN}Colors enabled.{Colors.END}")
                time.sleep(1)
            elif choice == "2" or not choice:
                break
            else:
                gui_print(self.lang.get("invalid_choice"))

    def create_character(self):
        """Create a new character and initialize starting state."""
        self.player = Character(name="Hero",
                                character_class="Warrior",
                                classes_data=self.classes_data,
                                lang=self.lang)
        self.player.weather_data = getattr(self, 'weather_data', {})
        self.player.times_data = getattr(self, 'times_data', {})
        self.player.create_character(self.classes_data, self.items_data,
                                     self.lang)
        self.visited_areas.add(self.player.current_area)
        self.update_weather()

    def change_language_menu(self):
        """Menu to change the game language"""
        gui_print(
            f"\n{Colors.CYAN}{Colors.BOLD}=== {self.lang.get('settings', 'SETTINGS')} ==={Colors.END}"
        )
        available = self.lang.config.get("available_languages",
                                         {"en": "English"})

        langs = list(available.items())
        for i, (code, name) in enumerate(langs, 1):
            gui_print(f"{Colors.CYAN}{i}.{Colors.END} {name}")

        gui_print(
            f"{Colors.CYAN}{len(langs) + 1}.{Colors.END} {self.lang.get('back', 'Back')}"
        )

        choice = ask(f"{Colors.CYAN}Choose a language: {Colors.END}")

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(langs):
                self.lang.change_language(langs[idx][0])
            elif idx == len(langs):
                return
        gui_print(create_separator())

    def fight_boss_menu(self):
        """Menu to select and fight a boss in the current area"""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        area_data = self.areas_data.get(self.current_area, {})
        possible_bosses = area_data.get("possible_bosses", [])

        if not possible_bosses:
            gui_print(
                f"There are no bosses in {area_data.get('name', self.current_area)}."
            )
            return

        gui_print(
            f"\n{Colors.RED}{Colors.BOLD}=== BOSSES IN {area_data.get('name', self.current_area).upper()} ==={Colors.END}"
        )
        for i, boss_name in enumerate(possible_bosses, 1):
            boss_data = self.bosses_data.get(boss_name, {})
            status = ""
            if boss_name in self.player.bosses_killed:
                last_killed_str = self.player.bosses_killed[boss_name]
                try:
                    last_killed_dt = datetime.fromisoformat(last_killed_str)
                    diff = datetime.now() - last_killed_dt
                    if diff.total_seconds() < 28800:
                        status = f" {Colors.YELLOW}(Cooldown: {int((28800 - diff.total_seconds()) // 60)}m left){Colors.END}"
                except Exception:
                    pass
            gui_print(f"{i}. {boss_data.get('name', boss_name)}{status}")

        choice = ask(
            f"Choose a boss (1-{len(possible_bosses)}) or Enter to cancel: ")
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(possible_bosses):
                boss_name = possible_bosses[idx]

                # Cooldown check
                if boss_name in self.player.bosses_killed:
                    last_killed_str = self.player.bosses_killed[boss_name]
                    try:
                        last_killed_dt = datetime.fromisoformat(
                            last_killed_str)
                        if (datetime.now() -
                                last_killed_dt).total_seconds() < 28800:
                            gui_print(
                                f"{boss_name} is still recovering. Try again later."
                            )
                            return
                    except Exception:
                        pass

                boss_data = self.bosses_data.get(boss_name)
                if boss_data:
                    boss = Boss(boss_data, self.dialogues_data)
                    gui_print(
                        f"\n{Colors.RED}{Colors.BOLD}Challenge accepted!{Colors.END}"
                    )
                    # Print start dialogue if available
                    start_dialogue = boss.get_dialogue("on_start_battle")
                    if start_dialogue:
                        gui_print(
                            f"\n{Colors.CYAN}{boss.name}:{Colors.END} {start_dialogue}"
                        )
                    self.battle(boss)
            else:
                gui_print(self.lang.get("invalid_choice"))

    def explore(self):
        """Explore the current area"""
        if self.player:
            self.player.advance_time(
                5.0)  # 5 minutes real = 2.5 minutes game time
        if not self.player:
            gui_print(self.lang.get('no_character_created'))
            return

        # Continuous mission check on every action
        self.update_mission_progress('check', '')

        area_data = self.areas_data.get(self.current_area, {})
        area_name = area_data.get("name", "Unknown Area")

        gui_print(self.lang.get("exploring_area_msg").format(area_name=area_name))

        # Random encounter chance
        if random.random() < 0.7:  # 70% chance of encounter
            self.random_encounter()
        else:
            gui_print(self.lang.get("explore_nothing_found"))

            # Small chance to find materials
            if random.random() < 0.4:  # 40% chance to find materials
                self._gather_materials()

            # Small chance to find gold
            if random.random() < 0.3:  # 30% chance to find gold
                found_gold = random.randint(5, 20)
                self.player.gold += found_gold
                gui_print(self.lang.get("found_gold_msg").format(gold=found_gold))

    def random_encounter(self):
        """Handle random encounter with regular enemies"""
        if not self.player:
            return

        area_data = self.areas_data.get(self.current_area, {})
        possible_enemies = area_data.get("possible_enemies", [])

        if not possible_enemies:
            msg = self.lang.get("no_enemies_in_area")
            gui_print(msg.replace("\\n", "\n").replace("\\033", "\033"))
            return

        # Regular enemy encounter
        enemy_name = random.choice(possible_enemies)
        enemy_data = self.enemies_data.get(enemy_name)

        if enemy_data:
            enemy = Enemy(enemy_data)
            msg = f"\nA wild {enemy.name} appears!"
            gui_print(f"\n{Colors.wrap(msg, Colors.RED)}")
            self.battle(enemy)
        else:
            msg = self.lang.get("explore_no_enemies")
            gui_print(msg.replace("\\n", "\n").replace("\\033", "\033"))

    def update_challenge_progress(self, challenge_type: str, value: int = 1):
        """Update challenge progress and check for completions"""
        if not self.player:
            return

        for challenge in self.weekly_challenges_data.get('challenges', []):
            if challenge['id'] in self.completed_challenges:
                continue

            if challenge['type'] == challenge_type:
                self.challenge_progress[challenge['id']] += value

                # Show progress bar
                bar = create_progress_bar(
                    self.challenge_progress[challenge['id']],
                    challenge['target'], 20, Colors.YELLOW)
                gui_print(
                    f"{Colors.CYAN}[Challenge Progress] {challenge.get('name')}: {bar} {self.challenge_progress[challenge['id']]}/{challenge['target']}{Colors.END}"
                )

                # Check if challenge is completed
                if self.challenge_progress[
                        challenge['id']] >= challenge['target']:
                    self.complete_challenge(challenge)

    def complete_challenge(self, challenge: Dict[str, Any]):
        """Complete a challenge and award rewards"""
        if not self.player:
            return

        challenge_id = challenge['id']
        self.completed_challenges.append(challenge_id)

        reward_exp = challenge.get('reward_exp', 0)
        reward_gold = challenge.get('reward_gold', 0)

        self.player.gain_experience(reward_exp)
        self.player.gold += reward_gold

        gui_print(
            f"\n{Colors.CYAN}{Colors.BOLD}✓ Challenge Completed: {challenge['name']}!{Colors.END}"
        )
        gui_print(f"  Reward: {reward_exp} EXP + {reward_gold} Gold")

    def view_challenges(self):
        """Display challenge status to player"""
        if not self.player:
            return

        gui_print(
            f"\n{Colors.CYAN}{Colors.BOLD}=== WEEKLY CHALLENGES ==={Colors.END}"
        )

        for challenge in self.weekly_challenges_data.get('challenges', []):
            challenge_id = challenge['id']
            is_completed = challenge_id in self.completed_challenges
            progress = self.challenge_progress.get(challenge_id, 0)
            target = challenge['target']

            status = "✓" if is_completed else f"{progress}/{target}"
            completed_text = f"{Colors.GREEN}COMPLETED{Colors.END}" if is_completed else status

            gui_print(f"\n{Colors.BOLD}{challenge['name']}{Colors.END}")
            gui_print(f"  {challenge['description']}")
            gui_print(f"  Status: {completed_text}")
            gui_print(
                f"  Reward: {challenge['reward_exp']} EXP + {challenge['reward_gold']} Gold"
            )

    def battle(self, enemy: Enemy):
        self.battle_system.battle(enemy)

    def player_turn(self, enemy: Enemy) -> bool:
        return self.battle_system.player_turn(enemy)

    def companion_action_for(self, companion, enemy: Enemy):
        self.battle_system.companion_action_for(companion, enemy)

    def companions_act(self, enemy: Enemy):
        self.battle_system.companions_act(enemy)

    def enemy_turn(self, enemy: Enemy):
        self.battle_system.enemy_turn(enemy)

    def use_item_in_battle(self):
        """Use item during battle"""
        if not self.player:
            return

        consumables = [
            item for item in self.player.inventory if item in self.items_data
            and self.items_data[item].get("type") == "consumable"
        ]

        if not consumables:
            msg = self.lang.get("no_consumable_items")
            gui_print(msg.replace("\\n", "\n").replace("\\033", "\033"))
            return

        msg = self.lang.get("available_consumables")
        gui_print(msg.replace("\\n", "\n").replace("\\033", "\033"))
        for i, item in enumerate(consumables, 1):
            item_data = self.items_data[item]
            gui_print(
                f"{i}. {item} - {item_data.get('description', 'Unknown effect')}"
            )

        try:
            choice = int(ask("Choose item (1-{}): ".format(
                len(consumables)))) - 1
            if 0 <= choice < len(consumables):
                item = consumables[choice]
                self.use_item(item)
                self.player.inventory.remove(item)
            else:
                gui_print(self.lang.get("invalid_choice"))
        except ValueError:
            gui_print(self.lang.get("invalid_input"))

    def cast_spell(self, enemy, weapon_name: Optional[str] = None):
        """Cast a spell from the player's equipped magic weapon."""
        if not self.player:
            return

        # Use the spell casting system to select and cast a spell
        selected = self.spell_casting_system.select_spell(weapon_name)
        if selected:
            spell_name, spell_data = selected
            self.spell_casting_system.cast_spell(enemy, spell_name, spell_data)

    def use_item(self, item: str):
        """Use an item"""
        if not self.player:
            return

        item_data = self.items_data.get(item, {})
        item_type = item_data.get("type")

        if item_type == "consumable":
            if item_data.get("effect") == "heal":
                heal_amount = item_data.get("value", 0)
                old_hp = self.player.hp
                self.player.heal(heal_amount)
                gui_print(f"Used {item}, healed {self.player.hp - old_hp} HP!")
            elif item_data.get("effect") == "mp_restore":
                mp_amount = item_data.get("value", 0)
                old_mp = self.player.mp
                self.player.mp = min(self.player.max_mp,
                                     self.player.mp + mp_amount)
                gui_print(f"Used {item}, restored {self.player.mp - old_mp} MP!")

    def view_inventory(self):
        """View character inventory"""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        gui_print(self.lang.get("n_inventory"))
        gui_print(f"Gold: {Colors.GOLD}{self.player.gold}{Colors.END}")

        if not self.player.inventory:
            gui_print(self.lang.get('inventory_empty'))
            return

        # Group items by type
        items_by_type = {}
        for item in self.player.inventory:
            item_type = self.items_data.get(item, {}).get("type", "unknown")
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        for item_type, items in items_by_type.items():
            gui_print(f"\n{Colors.CYAN}{item_type.title()}:{Colors.END}")
            for item in items:
                item_data = self.items_data.get(item, {})
                gui_print(f"  - {item}")
                if item_data.get("description"):
                    gui_print(f"    {item_data['description']}")

        # Get consumable items
        consumables = [
            it for it in self.player.inventory
            if self.items_data.get(it, {}).get('type') == 'consumable'
        ]

        # Offer equip/unequip options for equipment items
        equipable = [
            it for it in self.player.inventory
            if self.items_data.get(it, {}).get('type') in ('weapon', 'armor',
                                                           'accessory',
                                                           'offhand')
        ]
        if equipable or consumables:
            gui_print(self.lang.get("equipment_options"))
            if equipable:
                gui_print(self.lang.get("equip_from_inventory"))
                gui_print(self.lang.get("unequip_slot"))
            if consumables:
                gui_print(
                    self.lang.get("use_consumable_option",
                                  "  C. Use a consumable item"))
            choice = ask("Choose option (E/U/C) or press Enter to return: ")
            if choice.lower() == 'e':
                gui_print(self.lang.get("equipable_items"))
                for i, item in enumerate(equipable, 1):
                    gui_print(
                        f"{i}. {item} - {self.items_data.get(item, {}).get('description','')}"
                    )
                sel = ask(
                    f"Choose item to equip (1-{len(equipable)}) or press Enter: "
                )
                if sel and sel.isdigit():
                    idx = int(sel) - 1
                    if 0 <= idx < len(equipable):
                        item_name = equipable[idx]
                        ok = self.player.equip(item_name, self.items_data)
                        if ok:
                            gui_print(f"Equipped {item_name}.")
                        else:
                            gui_print(
                                f"Cannot equip {item_name} (requirements not met)."
                            )
            elif choice.lower() == 'u':
                gui_print(self.lang.get("currently_equipped"))
                for slot in ('weapon', 'armor', 'offhand', 'accessory_1',
                             'accessory_2', 'accessory_3'):
                    gui_print(
                        f"{slot.title()}: {self.player.equipment.get(slot, 'None')}"
                    )
                slot_choice = ask(
                    "Enter slot to unequip (weapon/armor/offhand/accessory_1/accessory_2/accessory_3) or press Enter: "
                )
                valid_slots = ('weapon', 'armor', 'offhand', 'accessory_1',
                               'accessory_2', 'accessory_3')
                if slot_choice in valid_slots:
                    removed = self.player.unequip(slot_choice, self.items_data)
                    if removed:
                        gui_print(f"Unequipped {removed} from {slot_choice}.")
                    else:
                        gui_print(self.lang.get("nothing_to_unequip"))
            elif choice.lower() == 'c' and consumables:
                # Use consumable item
                gui_print(
                    f"\n{self.lang.get('consumable_items_header', 'Consumable items:')}"
                )
                for i, item in enumerate(consumables, 1):
                    item_data = self.items_data.get(item, {})
                    gui_print(f"{i}. {item} - {item_data.get('description', '')}")
                sel = ask(
                    f"Choose item to use (1-{len(consumables)}) or press Enter: "
                )
                if sel and sel.isdigit():
                    idx = int(sel) - 1
                    if 0 <= idx < len(consumables):
                        item_name = consumables[idx]
                        self.use_item(item_name)
                        self.player.inventory.remove(item_name)
                        gui_print(f"Used {item_name}.")

    def view_missions(self):
        """View and manage missions"""
        while True:
            clear_screen()
            gui_print(create_section_header("MISSIONS"))

            # Active Missions
            active_missions = [
                mid for mid in self.mission_progress.keys()
                if not self.mission_progress[mid].get('completed', False)
            ]

            if active_missions:
                gui_print(self.lang.get("n_active_missions"))
                for i, mid in enumerate(active_missions, 1):
                    mission = self.missions_data.get(mid, {})
                    progress = self.mission_progress[mid]

                    if progress['type'] == 'kill':
                        if 'current_counts' in progress:
                            lines = [
                                f"{t}: {progress['current_counts'].get(t,0)}/{c}"
                                for t, c in progress['target_counts'].items()
                            ]
                            status = ", ".join(lines)
                        else:
                            status = f"{progress['current_count']}/{progress['target_count']}"
                    else:
                        if 'current_counts' in progress:
                            lines = [
                                f"{t}: {progress['current_counts'].get(t,0)}/{c}"
                                for t, c in progress['target_counts'].items()
                            ]
                            status = ", ".join(lines)
                        else:
                            status = f"{progress['current_count']}/{progress['target_count']}"

                    gui_print(f"{i}. {mission.get('name')} - {status}")
                    gui_print(
                        f"   {Colors.DARK_GRAY}{mission.get('description')}{Colors.END}"
                    )

                gui_print(f"\n{self.lang.get('options_available_cancel_back')}")
            else:
                gui_print(self.lang.get("no_active_missions"))
                gui_print(f"\n{self.lang.get('options_available_missions_back')}")

            choice = ask("\nChoose an option: ").upper()

            if choice == 'B':
                break
            elif choice == 'A':
                self.available_missions_menu()
            elif choice == 'C' and active_missions:
                idx_str = ask("Enter mission number to cancel: ")
                if idx_str.isdigit():
                    idx = int(idx_str) - 1
                    if 0 <= idx < len(active_missions):
                        m_id = active_missions[idx]
                        m_name = self.missions_data[m_id]['name']
                        confirm = ask(
                            f"Are you sure you want to cancel '{m_name}'? (y/n): "
                        ).lower()
                        if confirm == 'y':
                            del self.mission_progress[m_id]
                            gui_print(f"Mission '{m_name}' cancelled.")
                            time.sleep(1)
                    else:
                        gui_print(self.lang.get("invalid_mission_number"))
                        time.sleep(1)

    def available_missions_menu(self):
        """Menu for viewing and accepting available missions"""
        page = 0
        per_page = 10

        while True:
            clear_screen()
            gui_print(create_section_header("AVAILABLE MISSIONS"))

            available_missions = [
                mid for mid in self.missions_data.keys()
                if mid not in self.mission_progress
                and mid not in self.completed_missions
            ]

            if not available_missions:
                gui_print(self.lang.get("no_new_missions"))
                ask("\nPress Enter to go back...")
                break

            total_pages = (len(available_missions) + per_page - 1) // per_page
            start_idx = page * per_page
            end_idx = min(start_idx + per_page, len(available_missions))
            current_page_missions = available_missions[start_idx:end_idx]

            for i, mission_id in enumerate(current_page_missions, 1):
                mission = self.missions_data.get(mission_id, {})
                gui_print(f"{i}. {Colors.BOLD}{mission.get('name')}{Colors.END}")
                gui_print(f"   {mission.get('description')}")

                # Requirements
                reqs = []
                if mission.get('unlock_level'):
                    level_req = mission.get('unlock_level')
                    has_level = self.player.level >= level_req if self.player else False
                    color = Colors.GREEN if has_level else Colors.RED
                    reqs.append(f"Level {color}{level_req}{Colors.END}")
                if mission.get('prerequisites'):
                    for prereq_id in mission.get('prerequisites'):
                        prereq_name = self.missions_data.get(
                            prereq_id, {}).get('name', prereq_id)
                        color = Colors.GREEN if prereq_id in self.completed_missions else Colors.RED
                        reqs.append(
                            f"Requires: {color}{prereq_name}{Colors.END}")
                if reqs:
                    gui_print(f"   Requirements: {', '.join(reqs)}")

            gui_print(f"\nPage {page + 1}/{total_pages}")
            if total_pages > 1:
                if page > 0:
                    gui_print(f"P. {self.lang.get('ui_previous_page')}")
                if page < total_pages - 1:
                    gui_print(f"N. {self.lang.get('ui_next_page')}")

            if current_page_missions:
                gui_print(f"1-{len(current_page_missions)}. Accept Mission")
            gui_print(f"B. {self.lang.get('back')}")

            choice = ask("\nChoose an option: ").upper()

            if choice == 'B':
                break
            elif choice == 'N' and page < total_pages - 1:
                page += 1
            elif choice == 'P' and page > 0:
                page -= 1
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(current_page_missions):
                    mission_id = current_page_missions[idx]
                    self.accept_mission(mission_id)
                else:
                    gui_print(self.lang.get("invalid_mission_number"))
                    time.sleep(1)

    def accept_mission(self, mission_id: str):
        """Accept a mission"""
        if mission_id not in self.mission_progress:
            mission = self.missions_data.get(mission_id, {})

            # Initialize progress tracking for this mission
            if mission:
                mission_type = mission.get('type', 'kill')
                target_count = mission.get('target_count', 1)

                if mission_type == 'collect' and isinstance(
                        target_count, dict):
                    # For collect missions with multiple items
                    self.mission_progress[mission_id] = {
                        'current_counts': {
                            item: 0
                            for item in target_count.keys()
                        },
                        'target_counts': target_count,
                        'completed': False,
                        'type': mission_type
                    }
                else:
                    # For kill missions or single item collect missions
                    self.mission_progress[mission_id] = {
                        'current_count': 0,
                        'target_count': target_count,
                        'completed': False,
                        'type': mission_type
                    }

                gui_print(f"Mission accepted: {mission.get('name', 'Unknown')}")

                # Check for accept cutscene
                accept_cutscene = mission.get('accept_cutscene')
                if accept_cutscene and accept_cutscene in self.cutscenes_data:
                    self.play_cutscene(accept_cutscene)

                time.sleep(1)
            else:
                gui_print(self.lang.get("mission_data_not_found"))
                time.sleep(1)
        else:
            gui_print(self.lang.get("mission_already_accepted"))
            time.sleep(1)

    def display_player_stats(self):
        """Display current player stats"""
        if self.player:
            self.player.display_stats()
        else:
            gui_print(
                self.lang.get("no_player_to_display",
                              "No player character created yet."))

    def update_mission_progress(self,
                                update_type: str,
                                target: str,
                                count: int = 1):
        """Update mission progress for a specific target"""
        # Always check inventory-based collect missions
        if self.player:
            for mid, progress in self.mission_progress.items():
                if progress.get('completed', False):
                    continue
                mission = self.missions_data.get(mid, {})
                if progress['type'] == 'collect':
                    if 'current_counts' in progress:
                        for item in progress['target_counts'].keys():
                            inv_count = self.player.inventory.count(item)
                            progress['current_counts'][item] = inv_count

                        all_collected = all(
                            progress['current_counts'][item] >=
                            progress['target_counts'][item]
                            for item in progress['target_counts'])
                        if all_collected:
                            self.complete_mission(mid)
                    else:
                        target_item = mission.get('target', '')
                        inv_count = self.player.inventory.count(target_item)
                        progress['current_count'] = inv_count
                        if progress['current_count'] >= progress[
                                'target_count']:
                            self.complete_mission(mid)

        # Standard update logic for kills or specific increments
        for mid, progress in self.mission_progress.items():
            if progress.get('completed', False):
                continue

            mission = self.missions_data.get(mid, {})

            if progress['type'] == 'kill' and update_type == 'kill':
                target_enemy = mission.get('target', '').lower()
                if target_enemy == target.lower():
                    progress['current_count'] += count
                    bar = create_progress_bar(progress['current_count'],
                                              progress['target_count'], 20,
                                              Colors.CYAN)
                    gui_print(
                        f"{Colors.CYAN}[Mission Progress] {mission.get('name')}: {bar} {progress['current_count']}/{progress['target_count']}{Colors.END}"
                    )

                    if progress['current_count'] >= progress['target_count']:
                        self.complete_mission(mid)

            elif progress['type'] == 'collect' and update_type == 'collect':
                # Handle collection missions
                if 'current_counts' in progress:
                    # Multi-item collection
                    if target in progress['current_counts']:
                        progress['current_counts'][target] += count
                        bar = create_progress_bar(
                            progress['current_counts'][target],
                            progress['target_counts'][target], 20, Colors.CYAN)
                        gui_print(
                            f"{Colors.CYAN}[Mission Progress] {mission.get('name')} - {target}: {bar} {progress['current_counts'][target]}/{progress['target_counts'][target]}{Colors.END}"
                        )

                        # Check if all items are collected
                        all_collected = all(
                            progress['current_counts'][item] >=
                            progress['target_counts'][item]
                            for item in progress['target_counts'])
                        if all_collected:
                            self.complete_mission(mid)
                else:
                    # Single item collection
                    target_item = mission.get('target', '')
                    if target_item == target:
                        progress['current_count'] += count
                        bar = create_progress_bar(progress['current_count'],
                                                  progress['target_count'], 20,
                                                  Colors.CYAN)
                        gui_print(
                            f"{Colors.CYAN}[Mission Progress] {mission.get('name')}: {bar} {progress['current_count']}/{progress['target_count']}{Colors.END}"
                        )

                        if progress['current_count'] >= progress[
                                'target_count']:
                            self.complete_mission(mid)

    def complete_mission(self, mission_id: str):
        """Mark a mission as completed and notify player"""
        if mission_id in self.mission_progress:
            self.mission_progress[mission_id]['completed'] = True
            mission = self.missions_data.get(mission_id, {})
            gui_print(
                f"\n{Colors.GOLD}{Colors.BOLD}!!! MISSION COMPLETE: {mission.get('name')} !!!{Colors.END}"
            )
            gui_print(
                f"{Colors.YELLOW}You can now claim your rewards from the menu.{Colors.END}"
            )

            # Check for complete cutscene
            complete_cutscene = mission.get('complete_cutscene')
            if complete_cutscene and complete_cutscene in self.cutscenes_data:
                self.play_cutscene(complete_cutscene)

            time.sleep(2)

    def claim_rewards(self):
        """Claim rewards for completed missions"""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        completed_missions = [
            mid for mid, progress in self.mission_progress.items()
            if progress.get('completed', False)
        ]
        if not completed_missions:
            gui_print(self.lang.get("no_completed_missions"))
            return

        gui_print(self.lang.get("n_claim_rewards"))
        gui_print(self.lang.get("completed_missions_header"))
        for i, mid in enumerate(completed_missions, 1):
            mission = self.missions_data.get(mid, {})
            reward = mission.get('reward', {})
            exp = reward.get('experience', 0)
            gold = reward.get('gold', 0)
            items = reward.get('items', [])
            gui_print(
                f"{i}. {mission.get('name')} - Exp: {exp}, Gold: {gold}, Items: {', '.join(items) if items else 'None'}"
            )

        choice = ask(
            f"Claim rewards for mission (1-{len(completed_missions)}) or press Enter to cancel: "
        )
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(completed_missions):
                mission_id = completed_missions[idx]
                mission = self.missions_data.get(mission_id, {})
                reward = mission.get('reward', {})

                # Apply rewards
                exp = reward.get('experience', 0)
                gold = reward.get('gold', 0)
                items = reward.get('items', [])

                self.player.gain_experience(exp)
                self.player.gold += gold
                for item in items:
                    self.player.inventory.append(item)

                # Remove from progress and add to completed
                del self.mission_progress[mission_id]
                self.completed_missions.append(mission_id)

                gui_print(self.lang.get("nrewards_claimed"))
                gui_print(f"Gained {Colors.MAGENTA}{exp} experience{Colors.END}")
                gui_print(f"Gained {Colors.GOLD}{gold} gold{Colors.END}")
                if items:
                    gui_print(f"Received items: {', '.join(items)}")
            else:
                gui_print(self.lang.get("invalid_choice"))

    def visit_shop(self):
        """Visit the shop - displays items for sale in the current area"""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        area_data = self.areas_data.get(self.current_area, {})
        area_shops = area_data.get("shops", [])

        # Add housing shop if in your_land
        available_shops = list(area_shops)
        if self.current_area == "your_land":
            available_shops.append("housing_shop")

        if not available_shops:
            gui_print(
                f"\n{Colors.RED}There are no shops in {area_data.get('name', self.current_area)}.{Colors.END}"
            )
            return

        # If multiple shops, let player choose
        if len(available_shops) > 1:
            gui_print(
                f"\n{Colors.BOLD}=== SHOPS IN {area_data.get('name', self.current_area).upper()} ==={Colors.END}"
            )
            gui_print(f"Your gold: {Colors.GOLD}{self.player.gold}{Colors.END}\n")
            for i, shop_id in enumerate(available_shops, 1):
                if shop_id == "housing_shop":
                    shop_name = "Housing Shop"
                else:
                    shop_data = self.shops_data.get(shop_id, {})
                    shop_name = shop_data.get(
                        "name",
                        shop_id.replace("_", " ").title())
                gui_print(f"{i}. {shop_name}")

            gui_print(self.lang.get("leave_option"))
            choice = ask("Which shop would you like to visit? ")

            if choice == "0" or not choice.isdigit():
                return

            shop_idx = int(choice) - 1
            if 0 <= shop_idx < len(available_shops):
                selected_shop = available_shops[shop_idx]
            else:
                gui_print(self.lang.get("invalid_choice"))
                return
        else:
            selected_shop = available_shops[0]

        # Now visit the selected shop
        if selected_shop == "housing_shop":
            self._visit_housing_shop_inline()
        else:
            visit_specific_shop(self, selected_shop)

    def _visit_housing_shop_inline(self):
        """Visit the housing shop in your_land to buy housing items"""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        gui_print(self.lang.get("n_housing_shop"))
        gui_print(
            f"{Colors.YELLOW}Welcome to the Housing Shop! Build your dream home with these items.{Colors.END}"
        )
        gui_print(f"\nYour gold: {Colors.GOLD}{self.player.gold}{Colors.END}")
        gui_print(
            f"Comfort Points: {Colors.CYAN}{self.player.comfort_points}{Colors.END}"
        )
        gui_print(
            f"Items owned: {Colors.MAGENTA}{len(self.player.housing_owned)}{Colors.END}"
        )

        # Get all housing items
        housing_items = list(self.housing_data.items())
        if not housing_items:
            gui_print(self.lang.get("no_housing_items_available"))
            return

        page_size = 8
        current_page = 0

        while True:
            start = current_page * page_size
            end = start + page_size
            page_items = housing_items[start:end]

            if not page_items:
                gui_print(self.lang.get("no_more_items"))
                break

            gui_print(
                f"\n{Colors.CYAN}--- Page {current_page + 1} of {(len(housing_items) + page_size - 1) // page_size} ---{Colors.END}"
            )
            for i, (item_id, item_data) in enumerate(page_items, 1):
                name = item_data.get("name", item_id)
                price = item_data.get("price", 0)
                comfort = item_data.get("comfort_points", 0)
                desc = item_data.get("description", "")
                owned = "✓" if item_id in self.player.housing_owned else " "

                # Color price based on affordability
                price_color = Colors.GREEN if self.player.gold >= price else Colors.RED
                # Color owned indicator
                owned_color = Colors.GREEN if owned == "✓" else Colors.RED

                gui_print(
                    f"\n{Colors.CYAN}{i}.{Colors.END} [{owned_color}{owned}{Colors.END}] {Colors.BOLD}{Colors.YELLOW}{name}{Colors.END}"
                )
                gui_print(f"   {desc}")
                gui_print(
                    f"   Price: {price_color}{price} gold{Colors.END} | Comfort: {Colors.CYAN}+{comfort}{Colors.END}"
                )

            gui_print(self.lang.get("noptions_2"))
            gui_print(
                f"{Colors.CYAN}1-{len(page_items)}.{Colors.END} Buy/Add Housing Item"
            )
            if len(housing_items) > page_size:
                gui_print(self.lang.get("n_next_page"))
                gui_print(self.lang.get("p_previous_page"))
            gui_print(self.lang.get("b_furnishview_home"))
            gui_print(self.lang.get("enter_leave_shop"))

            choice = ask("\nChoose action: ").strip().upper()

            if not choice:
                break
            elif choice == 'N' and len(housing_items) > page_size:
                if end < len(housing_items):
                    current_page += 1
            elif choice == 'P' and len(housing_items) > page_size:
                if current_page > 0:
                    current_page -= 1
            elif choice == 'B':
                build_home(self)
            elif choice.isdigit():
                item_idx = int(choice) - 1
                if 0 <= item_idx < len(page_items):
                    item_id, item_data = page_items[item_idx]
                    name = item_data.get("name", item_id)
                    price = item_data.get("price", 0)
                    comfort = item_data.get("comfort_points", 0)

                    # Check if already owned
                    if item_id in self.player.housing_owned:
                        # Option to buy another copy or view details
                        confirm = ask(
                            f"\n{Colors.YELLOW}You already own this. Buy another copy for {Colors.GOLD}{price} gold{Colors.YELLOW}? (y/n): {Colors.END}"
                        ).strip().lower()
                        if confirm != 'y':
                            continue

                    # Check if can afford
                    if self.player.gold >= price:
                        self.player.gold -= price
                        self.player.housing_owned.append(item_id)
                        self.player.comfort_points += comfort
                        gui_print(
                            f"\n{Colors.GREEN}✓ Purchased {Colors.BOLD}{name}{Colors.END}{Colors.GREEN}!{Colors.END}"
                        )
                        gui_print(
                            f"{Colors.CYAN}Comfort points: +{comfort} (Total: {self.player.comfort_points}){Colors.END}"
                        )
                    else:
                        gui_print(
                            f"\n{Colors.RED}✗ Not enough gold! Need {Colors.BOLD}{price}{Colors.END}{Colors.RED}, have {self.player.gold}.{Colors.END}"
                        )
                else:
                    gui_print(self.lang.get("invalid_selection_1"))

    def visit_tavern(self):
        """Visit the tavern to hire companions."""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        gui_print(self.lang.get("n_tavern"))
        gui_print(
            "Welcome to The Rusty Tankard. Here you can hire companions to join your party."
        )
        gui_print(f"Your gold: {Colors.GOLD}{self.player.gold}{Colors.END}")

        companions = list(self.companions_data.items())
        if not companions:
            gui_print(self.lang.get('no_companions_available'))
            return

        page_size = 6
        current_page = 0

        while True:
            start = current_page * page_size
            end = start + page_size
            page_items = companions[start:end]

            gui_print(
                f"\n--- Page {current_page + 1} of {(len(companions) + page_size - 1) // page_size} ---"
            )
            for i, (cid, cdata) in enumerate(page_items, 1):
                price = cdata.get('price', '?')
                desc = cdata.get('description', '')
                gui_print(
                    f"{i}. {cdata.get('name', cid)} - {Colors.GOLD}{price} gold{Colors.END}"
                )
                gui_print(f"   {desc}")

            gui_print(self.lang.get('ui_shortcuts_nav'))
            choice = ask(
                f"\nHire companion (1-{len(page_items)}) or press Enter to leave: "
            )

            if not choice:
                break
            elif choice.lower() == 'n':
                if end < len(companions):
                    current_page += 1
                else:
                    gui_print(self.lang.get('ui_no_more_pages'))
            elif choice.lower() == 'p':
                if current_page > 0:
                    current_page -= 1
                else:
                    gui_print(self.lang.get('ui_already_first_page'))
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(page_items):
                    cid, cdata = page_items[idx]
                    price = cdata.get('price', 0)
                    if self.player.gold >= price:
                        if len(self.player.companions) >= 4:
                            gui_print(
                                "You already have the maximum number of companions (4)."
                            )
                            continue
                        self.player.gold -= price
                        # Create companion data with equipment and level
                        companion_data = {
                            "id": cid,
                            "name": cdata.get('name', cid),
                            "level": 1,
                            "equipment": {
                                "weapon": None,
                                "armor": None,
                                "accessory": None
                            }
                        }
                        self.player.companions.append(companion_data)
                        gui_print(
                            f"Hired {cdata.get('name', cid)} for {price} gold!"
                        )
                        # Recalculate stats with new companion bonus
                        self.player.update_stats_from_equipment(
                            self.items_data, self.companions_data)
                    else:
                        gui_print(self.lang.get('not_enough_gold'))
                else:
                    gui_print(self.lang.get("invalid_choice"))

    def visit_market(self):
        """Visit the Elite Market - browse and buy items from the API at 50% off"""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        if not self.market_api:
            gui_print(self.lang.get('market_api_not_available'))
            return

        gui_print(
            f"\n{Colors.MAGENTA}{Colors.BOLD}=== ELITE MARKET ==={Colors.END}")
        gui_print(self.lang.get('welcome_elite_market'))
        if self.player:
            gui_print(f"\nYour gold: {Colors.GOLD}{self.player.gold}{Colors.END}")

        # Check cooldown
        remaining = self.market_api.get_cooldown_remaining()
        if remaining and remaining.total_seconds() > 0:
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            gui_print(
                f"\n{Colors.YELLOW}Market cooldown: {mins}m {secs}s remaining{Colors.END}"
            )

        # Fetch market data
        market_data = self.market_api.fetch_market_data()
        if not market_data or not market_data.get('ok'):
            gui_print(
                f"\n{Colors.RED}{Colors.BOLD}Market is currently closed!{Colors.END}"
            )
            gui_print(
                f"{Colors.YELLOW}Merchants have travelled to another distant far place!{Colors.END}"
            )
            gui_print(
                f"{Colors.YELLOW}Please wait until the merchants arrive!{Colors.END}"
            )
            return

        items = self.market_api.get_all_items()
        if not items:
            gui_print(self.lang.get('no_items_available_market'))
            return

        # Get filter options from player
        gui_print(self.lang.get("n_browse_items"))
        gui_print(self.lang.get('ui_filters_available'))
        gui_print(self.lang.get('filter_all_items'))
        gui_print(self.lang.get('filter_by_type_desc'))
        gui_print(self.lang.get('filter_by_rarity_desc'))
        gui_print(self.lang.get('filter_by_class_desc'))
        gui_print(self.lang.get('filter_by_max_price_desc'))
        gui_print(f"  R. {self.lang.get('filter_refresh_market')}")

        choice = ask("\nChoose filter (1-5, R) or press Enter to browse all: "
                     ).strip().upper()

        filtered_items = items

        if choice == '1' or not choice:
            pass  # All items
        elif choice == '2':
            gui_print(
                "\nItem types: weapon, armor, consumable, accessory, material, offhand"
            )
            item_type = ask("Enter type: ").strip().lower()
            filtered_items = self.market_api.filter_items(item_type=item_type)
        elif choice == '3':
            gui_print(f"\n{self.lang.get('rarities_list')}")
            rarity = ask("Enter rarity: ").strip().lower()
            filtered_items = self.market_api.filter_items(rarity=rarity)
        elif choice == '4':
            gui_print(f"\n{self.lang.get('classes_list')}")
            class_req = ask("Enter class: ").strip()
            filtered_items = self.market_api.filter_items(class_req=class_req)
        elif choice == '5':
            try:
                max_price = int(ask("Enter max price: ").strip())
                filtered_items = self.market_api.filter_items(
                    max_price=max_price)
            except ValueError:
                gui_print(self.lang.get('invalid_price_showing_all'))
        elif choice == 'R':
            filtered_items = self.market_api.get_all_items()
            # Force refresh
            self.market_api.fetch_market_data(force_refresh=True)
            filtered_items = self.market_api.get_all_items()

        if not filtered_items:
            gui_print(self.lang.get('no_items_match_filters'))
            return

        # Sort by market price by default
        filtered_items = sorted(filtered_items,
                                key=lambda x: x.get('marketPrice', 0))

        # Paginate and display items
        page_size = 8
        current_page = 0

        while True:
            start = current_page * page_size
            end = start + page_size
            page_items = filtered_items[start:end]

            if not page_items:
                gui_print(self.lang.get("no_more_items"))
                break

            gui_print(
                f"\n--- Page {current_page + 1} of {(len(filtered_items) + page_size - 1) // page_size} ---"
            )

            for i, item in enumerate(page_items, 1):
                name = item.get('name', 'Unknown')
                item_type = item.get('type', 'unknown')
                rarity = item.get('rarity', 'common')
                original_price = item.get('originalPrice', 0)
                market_price = item.get('marketPrice', 0)
                desc = item.get('description',
                                '')[:60]  # Truncate long descriptions
                reqs = item.get('requirements')
                class_req = reqs.get('class') if reqs else None
                level_req = reqs.get('level', 1) if reqs else 1

                # Color by rarity
                rarity_color = get_rarity_color(rarity)
                price_color = Colors.GREEN if market_price <= self.player.gold else Colors.RED

                gui_print(f"\n{i}. {rarity_color}{name}{Colors.END} ({item_type})")
                gui_print(f"   {Colors.DARK_GRAY}{desc}{Colors.END}")
                gui_print(
                    f"   {rarity_color}{rarity.title()}{Colors.END} | Level {level_req}"
                    + (f" | {Colors.CYAN}{class_req}{Colors.END}"
                       if class_req else ""))
                gui_print(
                    f"   {price_color}{market_price}{Colors.END} gold (was {original_price})"
                )

            gui_print(self.lang.get("noptions_3"))
            gui_print(f"1-{len(page_items)}. Buy Item")
            if len(filtered_items) > page_size:
                gui_print(f"N. {self.lang.get('ui_next_page')}")
                gui_print(f"P. {self.lang.get('ui_previous_page')}")
            gui_print(f"F. {self.lang.get('ui_filter_items')}")
            gui_print(f"Enter. {self.lang.get('ui_return_to_main_menu')}")

            choice = ask("\nChoose action: ").strip().upper()

            if not choice:
                break
            elif choice == 'N' and len(filtered_items) > page_size:
                if end < len(filtered_items):
                    current_page += 1
            elif choice == 'P' and len(filtered_items) > page_size:
                if current_page > 0:
                    current_page -= 1
            elif choice == 'F':
                # Apply filter
                gui_print(f"\n{self.lang.get('ui_refine_search')}")
                gui_print(self.lang.get('filter_by_type'))
                gui_print(self.lang.get('filter_by_rarity'))
                gui_print(self.lang.get('filter_by_class'))
                gui_print(self.lang.get('filter_by_max_price'))
                sub_choice = ask("Choose filter: ").strip()
                if sub_choice == '1':
                    item_type = ask("Enter type: ").strip().lower()
                    filtered_items = [
                        it for it in filtered_items
                        if it.get('type', '').lower() == item_type
                    ]
                elif sub_choice == '2':
                    rarity = ask("Enter rarity: ").strip().lower()
                    filtered_items = [
                        it for it in filtered_items
                        if it.get('rarity', '').lower() == rarity
                    ]
                elif sub_choice == '3':
                    class_req = ask("Enter class: ").strip()
                    filtered_items = [
                        it for it in filtered_items
                        if (it.get('requirements') or {}
                            ).get('class', '').lower() == class_req.lower()
                    ]
                elif sub_choice == '4':
                    try:
                        max_price = int(ask("Enter max price: ").strip())
                        filtered_items = [
                            it for it in filtered_items
                            if it.get('marketPrice', 0) <= max_price
                        ]
                    except ValueError:
                        pass
                current_page = 0
            elif choice.isdigit():
                item_idx = int(choice) - 1
                if 0 <= item_idx < len(page_items):
                    item = page_items[item_idx]
                    name = item.get('name', '')
                    market_price = item.get('marketPrice', 0)

                    if self.player.gold >= market_price:
                        self.player.gold -= market_price
                        self.player.inventory.append(name)
                        gui_print(
                            f"\n{Colors.GREEN}Purchased {name} for {market_price} gold!{Colors.END}"
                        )
                        self.update_mission_progress('collect', name)
                    else:
                        gui_print(
                            f"\n{Colors.RED}Not enough gold! Need {market_price}, have {self.player.gold}.{Colors.END}"
                        )
                else:
                    gui_print(self.lang.get('invalid_selection'))

    def manage_companions(self):
        """Manage hired companions."""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        while True:
            gui_print(self.lang.get("n_companions"))
            gui_print(f"Active companions: {len(self.player.companions)}/4")

            if not self.player.companions:
                gui_print(
                    "You have no companions yet. Visit the tavern to hire some!"
                )
                return

            # Display active companions
            for i, companion in enumerate(self.player.companions, 1):
                if isinstance(companion, dict):
                    comp_name = companion.get('name')
                    comp_level = companion.get('level', 1)
                else:
                    comp_name = companion
                    comp_level = 1

                # Find companion data to show bonuses
                comp_data = None
                for cid, cdata in self.companions_data.items():
                    if cdata.get('name') == comp_name:
                        comp_data = cdata
                        break

                gui_print(
                    f"\n{i}. {Colors.CYAN}{comp_name}{Colors.END} (Level {comp_level})"
                )
                if comp_data:
                    bonuses = []
                    if comp_data.get('attack_bonus'):
                        bonuses.append(f"+{comp_data.get('attack_bonus')} ATK")
                    if comp_data.get('defense_bonus'):
                        bonuses.append(
                            f"+{comp_data.get('defense_bonus')} DEF")
                    if comp_data.get('speed_bonus'):
                        bonuses.append(f"+{comp_data.get('speed_bonus')} SPD")
                    if comp_data.get('healing_bonus'):
                        bonuses.append(
                            f"+{comp_data.get('healing_bonus')} Healing")
                    if comp_data.get('mp_bonus'):
                        bonuses.append(f"+{comp_data.get('mp_bonus')} MP")

                    if bonuses:
                        gui_print(f"   Bonuses: {', '.join(bonuses)}")
                    gui_print(f"   {comp_data.get('description', '')}")

            gui_print(f"\n{self.lang.get('ui_options')}")
            gui_print(self.lang.get('ui_dismiss_companion'))
            gui_print(self.lang.get('ui_equip_companion'))
            gui_print(self.lang.get('ui_enter_return'))

            choice = ask("Choose action: ").strip().lower()

            if not choice:
                break
            elif choice == 'd':
                # Dismiss companion
                if self.player.companions:
                    try:
                        idx = int(
                            ask(f"Dismiss which companion (1-{len(self.player.companions)})? "
                                )) - 1
                        if 0 <= idx < len(self.player.companions):
                            dismissed = self.player.companions.pop(idx)
                            if isinstance(dismissed, dict):
                                gui_print(
                                    f"{Colors.RED}Dismissed {dismissed.get('name')}.{Colors.END}"
                                )
                            else:
                                gui_print(
                                    f"{Colors.RED}Dismissed {dismissed}.{Colors.END}"
                                )
                            # Recalculate stats after dismissal
                            self.player.update_stats_from_equipment(
                                self.items_data, self.companions_data)
                        else:
                            gui_print(self.lang.get('invalid_selection'))
                    except ValueError:
                        gui_print(self.lang.get('invalid_input'))
            elif choice == 'e':
                # Equip item on companion
                gui_print(self.lang.get('ui_companion_equip_soon'))
                # TODO: Implement companion equipment
            else:
                gui_print(self.lang.get("invalid_choice"))

    def travel(self):
        """Travel to connected areas from the current area."""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        current = self.current_area
        area_data = self.areas_data.get(current, {})
        connections = area_data.get("connections", [])

        gui_print(self.lang.get("n_travel"))
        gui_print(f"Current location: {area_data.get('name', current)}")
        if not connections:
            gui_print(self.lang.get('no_connected_areas'))
            return

        gui_print(self.lang.get('ui_connected_areas'))
        for i, aid in enumerate(connections, 1):
            a = self.areas_data.get(aid, {})
            gui_print(f"{i}. {a.get('name', aid)} - {a.get('description','')}")

        choice = ask(
            f"Travel to (1-{len(connections)}) or press Enter to cancel: ")
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(connections):
                new_area = connections[idx]
                self.current_area = new_area
                self.player.update_weather(new_area)
                gui_print(
                    f"Traveling to {self.areas_data.get(new_area, {}).get('name', new_area)}..."
                )

                # Check for area cutscene
                area_data = self.areas_data.get(new_area, {})
                cutscene_id = area_data.get('first_time_enter_cutscene')
                if cutscene_id and cutscene_id in self.cutscenes_data:
                    cutscene = self.cutscenes_data[cutscene_id]
                    is_iterable = cutscene.get('iterable', False)
                    if is_iterable or new_area not in self.visited_areas:
                        self.play_cutscene(cutscene_id)
                        if not is_iterable:
                            self.visited_areas.add(new_area)

                # small chance encounter on travel
                if random.random() < 0.3:
                    self.random_encounter()

    def rest(self):
        """Rest in a safe area to recover HP and MP for gold."""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        area_data = self.areas_data.get(self.current_area, {})
        area_name = area_data.get("name", "Unknown Area")
        can_rest = area_data.get("can_rest", False)
        rest_cost = area_data.get("rest_cost", 0)

        if not can_rest:
            gui_print(
                f"\n{Colors.RED}You cannot rest in {area_name}. It's too dangerous!{Colors.END}"
            )
            return

        gui_print(
            f"\n{Colors.CYAN}=== REST IN {area_name.upper()} ==={Colors.END}")
        gui_print(f"Rest Cost: {Colors.GOLD}{rest_cost} gold{Colors.END}")
        gui_print(
            f"Current HP: {Colors.RED}{self.player.hp}/{self.player.max_hp}{Colors.END}"
        )
        gui_print(
            f"Current MP: {Colors.BLUE}{self.player.mp}/{self.player.max_mp}{Colors.END}"
        )

        if self.player.gold < rest_cost:
            gui_print(
                f"\n{Colors.RED}You don't have enough gold to rest! Need {rest_cost}, have {self.player.gold}.{Colors.END}"
            )
            return

        choice = ask(f"Rest for {rest_cost} gold? (y/n): ")
        if choice.lower() != 'y':
            gui_print(self.lang.get('decide_not_rest'))
            return

        # Deduct gold and restore HP/MP
        self.player.gold -= rest_cost
        old_hp = self.player.hp
        old_mp = self.player.mp
        self.player.hp = self.player.max_hp
        self.player.mp = self.player.max_mp

        gui_print(
            f"\n{Colors.GREEN}You rest and recover your strength...{Colors.END}"
        )
        gui_print(
            f"HP restored: {old_hp} → {Colors.GREEN}{self.player.hp}{Colors.END}"
        )
        gui_print(
            f"MP restored: {old_mp} → {Colors.GREEN}{self.player.mp}{Colors.END}"
        )
        gui_print(f"Gold remaining: {Colors.GOLD}{self.player.gold}{Colors.END}")

    def pet_shop(self):
        """Menu for buying and managing pets."""
        if not self.player:
            gui_print(self.lang.get("no_character"))
            return

        if not hasattr(self.player, 'pets_owned'):
            self.player.pets_owned = []
        if not hasattr(self.player, 'active_pet'):
            self.player.active_pet = None
        if not hasattr(self.player, 'pets_data'):
            self.player.pets_data = getattr(self, 'pets_data', {})

        while True:
            clear_screen()
            if not self.player:
                break
            gui_print(
                create_section_header(
                    self.lang.get("pet_shop_header", "PET SHOP")))
            gui_print(
                f"{self.lang.get('your_gold', 'Your Gold')}: {Colors.GOLD}{self.player.gold}g{Colors.END}"
            )

            # Using localized pet names if possible, else fallback
            active_pet_name = "None"
            if self.player.active_pet:
                active_pet_name = self.player.pets_data.get(
                    self.player.active_pet, {}).get('name',
                                                    self.player.active_pet)

            gui_print(
                f"Current Pet: {Colors.MAGENTA}{active_pet_name}{Colors.END}\n"
            )

            gui_print(f"{Colors.CYAN}1.{Colors.END} Buy Pet")
            gui_print(f"{Colors.CYAN}2.{Colors.END} Manage Pets")
            gui_print(f"{Colors.CYAN}3.{Colors.END} Back")

            choice = ask("Select an option: ")

            if choice == '1':
                gui_print("\nAvailable Pets:")
                available = []
                for pet_id, pet in self.player.pets_data.items():
                    if pet_id not in self.player.pets_owned:
                        gui_print(
                            f"- {pet['name']} ({pet['price']}g): {pet['description']}"
                        )
                        available.append(pet_id)

                if not available:
                    gui_print("You already own all available pets!")
                    ask("Press Enter to continue...")
                    continue

                pet_input = ask(
                    "\nEnter pet name to buy or press Enter to cancel: "
                ).lower().strip().replace(' ', '_')
                if not pet_input:
                    continue

                if pet_input in self.player.pets_data and pet_input not in self.player.pets_owned:
                    price = self.player.pets_data[pet_input]['price']
                    if self.player.gold >= price:
                        self.player.gold -= price
                        self.player.pets_owned.append(pet_input)
                        gui_print(
                            f"You bought a {self.player.pets_data[pet_input]['name']}!"
                        )
                    else:
                        gui_print("Not enough gold!")
                else:
                    gui_print("Invalid pet or already owned.")
                ask("Press Enter to continue...")

            elif choice == '2':
                if not self.player.pets_owned:
                    gui_print("You don't own any pets yet.")
                    ask("Press Enter to continue...")
                    continue

                gui_print("\nYour Pets:")
                for i, pet_id in enumerate(self.player.pets_owned, 1):
                    pet_name = self.player.pets_data.get(pet_id, {}).get(
                        'name', pet_id)
                    status = "(Active)" if pet_id == self.player.active_pet else ""
                    gui_print(f"{i}. {pet_name} {status}")

                sel = ask(
                    f"Select pet to activate (1-{len(self.player.pets_owned)}) or press Enter: "
                )
                if sel and sel.isdigit():
                    idx = int(sel) - 1
                    if 0 <= idx < len(self.player.pets_owned):
                        self.player.active_pet = self.player.pets_owned[idx]
                        gui_print(
                            f"{self.player.pets_data[self.player.active_pet]['name']} is now active!"
                        )
                        ask("Press Enter to continue...")

            elif choice == '3':
                break

    def save_game(self, filename_prefix: str = ""):
        self.save_load_system.save_game(filename_prefix)

    def load_game(self):
        self.save_load_system.load_game()

    def _load_save_data_internal(self, save_data: Dict[str, Any]):
        self.save_load_system._load_save_data_internal(save_data)

    def _load_equipment_data(self, player_data: Dict, save_version: str):
        self.save_load_system._load_equipment_data(player_data, save_version)

    def _validate_and_fix_equipment(self):
        self.save_load_system._validate_and_fix_equipment()

    def save_on_error(self,
                      exc_info=None,
                      filename_prefix="err_save_unstable_"):
        """Attempt to save the current game state and write a traceback log when an error occurs."""
        try:
            # Build a safe player name for filenames
            pname = (self.player.name if self.player
                     and getattr(self.player, 'name', None) else 'unknown')
            # Try to save using the standard save function with prefix
            try:
                self.save_game(filename_prefix)
            except Exception as se:
                gui_print(f"Error while saving game on error: {se}")

            # Write traceback log
            try:
                saves_dir = "data/saves"
                os.makedirs(saves_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                safe_prefix = (filename_prefix or '').replace('/', '_')
                logname = f"{saves_dir}/{safe_prefix}{pname}_error_{ts}.log"
                if exc_info is None:
                    exc_info = sys.exc_info()
                # exc_info may be a tuple (etype, value, tb) or an exception instance
                # Ensure exc_info is a 3-tuple (etype, value, tb)
                if not (isinstance(exc_info, tuple) and len(exc_info) == 3):
                    exc_info = sys.exc_info()

                et, ev, tbobj = exc_info
                buf = io.StringIO()
                traceback.print_exception(et, ev, tbobj, file=buf)
                tb = buf.getvalue()
                with open(logname, 'w') as lf:
                    lf.write(tb)
                gui_print(f"Error traceback written to: {logname}")
            except Exception as le:
                gui_print(f"Failed to write error log: {le}")
        except Exception as e:
            gui_print(f"Unexpected failure during save_on_error: {e}")

    def quit_game(self):
        """Quit the game"""
        try:
            from utilities.gui import is_gui_mode
            _in_gui = is_gui_mode()
        except Exception:
            _in_gui = False

        gui_print(f"\n{self.lang.get('ui_have_you_saved')}")
        if _in_gui:
            response = ''
        else:
            try:
                response = input(">>> ").strip().lower()
            except EOFError:
                response = ''
        if response == "no":
            clear_screen()
            gui_print(self.lang.get('ui_saving_progress'))
            self.save_game()
            gui_print(self.lang.get('ui_progress_saved'))
        gui_print(self.lang.get('ui_thank_you_playing'))
        gui_print(self.lang.get('ui_legacy_remembered'))
        sys.exit(0)

    def _gather_materials(self):
        """Gather materials based on current area's difficulty and theme."""
        if not self.player:
            return

        area_data = self.areas_data.get(self.current_area, {})
        difficulty = area_data.get('difficulty', 1)

        # Define material pools by difficulty tier
        # Tier 1: Basic materials (difficulty 1-2)
        tier1_materials = [
            "Herb", "Spring Water", "Leather", "Leather Strip", "Hardwood",
            "Stone Block", "Coal", "Iron Ore", "Goblin Ear", "Wolf Fang",
            "Bone Fragment"
        ]

        # Tier 2: Uncommon materials (difficulty 3)
        tier2_materials = [
            "Mana Herb", "Gold Nugget", "Steel Ingot", "Orc Tooth",
            "Serpent Tail", "Crystal Shard", "Venom Sac", "Swamp Scale",
            "Ancient Relic", "Wind Elemental Essence", "Demon Blood"
        ]

        # Tier 3: Rare materials (difficulty 4)
        tier3_materials = [
            "Dark Crystal", "Ice Crystal", "Void Crystal", "Shadow Essence",
            "Fire Essence", "Ice Essence", "Starlight Shard",
            "Eternal Essence", "Poison Crystal", "Lightning Crystal"
        ]

        # Tier 4: Legendary materials (difficulty 5-6)
        tier4_materials = [
            "Dragon Scale", "Dragon Bone", "Phoenix Feather", "Fire Gem",
            "Soul Fragment", "Demon Heart", "Golem Core",
            "Storm Elemental Core", "Zephyr's Scale", "Wind Dragon's Heart",
            "Eternal Feather", "Dragon Heart", "Void Heart"
        ]

        # Select materials based on difficulty
        available_materials = []
        if difficulty <= 2:
            available_materials = tier1_materials.copy()
            if random.random() < 0.3:  # 30% chance for tier 2
                available_materials.extend(tier2_materials)
        elif difficulty == 3:
            available_materials = tier1_materials + tier2_materials
            if random.random() < 0.4:  # 40% chance for tier 3
                available_materials.extend(tier3_materials)
        elif difficulty == 4:
            available_materials = tier2_materials + tier3_materials
            if random.random() < 0.3:  # 30% chance for tier 4
                available_materials.extend(tier4_materials)
        else:  # difficulty 5-6
            available_materials = tier3_materials + tier4_materials
            if random.random() < 0.2:  # 20% chance for tier 2
                available_materials.extend(tier2_materials)

        # Filter to only materials that actually exist in items_data
        valid_materials = [
            m for m in available_materials if m in self.items_data
        ]

        if not valid_materials:
            return

        # Gather 1-3 random materials
        num_materials = random.randint(1, 3)
        gathered = {}

        for _ in range(num_materials):
            material = random.choice(valid_materials)
            quantity = random.randint(1, 3)
            gathered[material] = gathered.get(material, 0) + quantity

        # Add gathered materials to inventory
        found_text = []
        for material, qty in gathered.items():
            for _ in range(qty):
                self.player.inventory.append(material)

            # Get material info for display
            item_data = self.items_data.get(material, {})
            rarity = item_data.get('rarity', 'common')
            color = get_rarity_color(rarity)
            found_text.append(f"{color}{qty}x {material}{Colors.END}")

        # Display gathered materials
        gui_print(self.lang.get("nyou_found_materials"))
        for text in found_text:
            gui_print(f"  - {text}")

        # Update mission progress for collected materials
        for material in gathered.keys():
            self.update_mission_progress('collect', material)

    def run_gui(self):
        """Launch the GUI game window and start the event-driven game loop (Phase 2.3 + 2.4)."""
        from utilities.gui import (
            GameWindow, WelcomeView, CharacterCreationView, SettingsView,
            ExploreView, CharacterView, InventoryView, MissionsView, ShopView,
            TavernView, MarketView, DungeonsView, HousingView, FarmView,
            TrainingView, TravelView, BossView, CompanionsView, ChallengesView,
            set_main_window, set_gui_mode,
        )

        window = GameWindow(title="Our Legacy", width=1200, height=800)
        window.game = self
        set_main_window(window)
        set_gui_mode(True)

        # Redirect stdout → GUI message panel (Phase 2.1)
        _orig_stdout = sys.stdout
        sys.stdout = GUIPrint(window)

        # Instantiate all views
        views: Dict[str, Any] = {
            "welcome":           WelcomeView(window, self),
            "create_character":  CharacterCreationView(window, self),
            "character":         CharacterView(window, self),
            "inventory":         InventoryView(window, self),
            "explore":           ExploreView(window, self),
            "missions":          MissionsView(window, self),
            "shop":              ShopView(window, self),
            "tavern":            TavernView(window, self),
            "market":            MarketView(window, self),
            "dungeons":          DungeonsView(window, self),
            "housing":           HousingView(window, self),
            "farm":              FarmView(window, self),
            "training":          TrainingView(window, self),
            "travel":            TravelView(window, self),
            "boss":              BossView(window, self),
            "companions":        CompanionsView(window, self),
            "challenges":        ChallengesView(window, self),
            "settings":          SettingsView(window, self),
        }

        def _refresh_status():
            if self.player:
                window.update_status(self.player)
                window.show_land_buttons(self.current_area == "your_land")

        def menu_callback(action: str):
            """Route sidebar nav actions to the matching view (Phase 2.4)."""
            view_map = {
                "explore":    "explore",
                "character":  "character",
                "travel":     "travel",
                "inventory":  "inventory",
                "missions":   "missions",
                "boss":       "boss",
                "tavern":     "tavern",
                "shop":       "shop",
                "market":     "market",
                "dungeons":   "dungeons",
                "companions": "companions",
                "challenges": "challenges",
                "settings":   "settings",
                "furnish_home": "housing",
                "farm":       "farm",
                "training":   "training",
            }

            if action in view_map:
                if not self.player and action not in ("settings",):
                    window.add_message("Create or load a character first.")
                    views["welcome"].show()
                    return
                views[view_map[action]].show()

            elif action == "alchemy":
                if self.player:
                    visit_alchemy(self)
                    _refresh_status()

            elif action == "rest":
                if self.player:
                    cost = max(5, self.player.level * 2)
                    if self.player.gold >= cost:
                        self.player.gold -= cost
                        self.player.hp = self.player.max_hp
                        self.player.mp = self.player.max_mp
                        window.add_message(
                            f"You rest. Spent {cost} gold. HP and MP restored.",
                            "#00cc00")
                        _refresh_status()
                    else:
                        window.add_message(
                            f"Need {cost} gold to rest. You have {self.player.gold}.",
                            "#cc0000")

            elif action == "pet_shop":
                if self.player:
                    self.pet_shop()
                    _refresh_status()

            elif action == "build":
                if self.player:
                    build_structures(self)
                    _refresh_status()

            elif action == "save":
                self.save_load_system.save_game()

            elif action == "load":
                self.save_load_system.load_game()
                if self.player:
                    _refresh_status()
                    views["character"].show()

            elif action == "claim":
                self.claim_rewards()
                _refresh_status()

            elif action == "quit":
                sys.stdout = _orig_stdout
                set_gui_mode(False)
                window.destroy()

        window.menu_callback = menu_callback

        # Wire the WelcomeView buttons to use GUI-specific character creation
        welcome_view = views["welcome"]
        welcome_view.on_new_game = lambda: (
            views["create_character"].show()
        )
        welcome_view.on_load_game = lambda: (
            self.save_load_system.load_game() or _refresh_status() or
            views["character"].show() if self.player else views["welcome"].show()
        )

        # Show the welcome screen and start the GUI event loop
        views["welcome"].show()
        window.mainloop()

        # Restore stdout after window closes
        sys.stdout = _orig_stdout
        set_gui_mode(False)


def main():
    """Main entry point — launches the GUI."""
    game = Game()
    game.run_gui()


if __name__ == "__main__":
    main()
