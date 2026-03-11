from utilities.gui import gui_print
"""
Character and Stats Management for Our Legacy
Centralized Character class and related logic
"""

import json
import uuid
from typing import Dict, List, Any, Optional


class Character:
    """Player character class"""

    def __init__(self,
                 name: str,
                 character_class: str,
                 classes_data: Optional[Dict] = None,
                 player_uuid: Optional[str] = None,
                 lang: Optional[Any] = None):
        self.name = name
        self.character_class = character_class
        self.uuid = player_uuid or str(uuid.uuid4())

        if lang is None:

            class MockLangCharacterAttr:

                def get(self, key, default=None, **kwargs):
                    return key

            self.lang = MockLangCharacterAttr()
        else:
            self.lang = lang

        # Rank system based on level
        self.rank = "F tier adventurer"
        self.level = 1
        self.experience = 0
        self.experience_to_next = 100
        self.class_data = {}
        self.level_up_bonuses = {}

        # Load class data if provided
        if classes_data and character_class in classes_data:
            self.class_data = classes_data[character_class]
            stats = self.class_data.get("base_stats", {})
            self.level_up_bonuses = self.class_data.get("level_up_bonuses", {})
        else:
            # Fallback defaults
            default_stats = {
                "hp": 100,
                "mp": 50,
                "attack": 10,
                "defense": 8,
                "speed": 10
            }
            stats = default_stats

        self.max_hp = stats.get("hp", 100)
        self.hp = self.max_hp
        self.max_mp = stats.get("mp", 50)
        self.mp = self.max_mp
        self.attack = stats.get("attack", 10)
        self.defense = stats.get("defense", 8)
        self.speed = stats.get("speed", 10)
        self.defending = False

        # Equipment slots
        self.equipment: Dict[str, Optional[str]] = {
            "weapon": None,
            "armor": None,
            "offhand": None,
            "accessory_1": None,
            "accessory_2": None,
            "accessory_3": None
        }

        # Legacy compatibility slots
        self.weapon = None
        self.armor = None
        self.offhand = None
        self.accessory = None

        # Inventory and gold
        self.inventory = []
        self.gold = 100
        self.companions: List[Dict[str, Any]] = []
        self.active_buffs: List[Dict[str, Any]] = []
        self.bosses_killed: Dict[str, str] = {}

        # Housing and Building
        self.housing_owned: List[str] = []
        self.comfort_points: int = 0
        self.building_slots: Dict[str, Optional[str]] = {
            "house_1": None,
            "house_2": None,
            "house_3": None,
            "decoration_1": None,
            "decoration_2": None,
            "decoration_3": None,
            "decoration_4": None,
            "decoration_5": None,
            "decoration_6": None,
            "decoration_7": None,
            "decoration_8": None,
            "decoration_9": None,
            "decoration_10": None,
            "fencing_1": None,
            "garden_1": None,
            "garden_2": None,
            "garden_3": None,
            "farm_1": None,
            "farm_2": None,
            "training_place_1": None,
            "training_place_2": None,
            "training_place_3": None,
        }
        self.farm_plots: Dict[str, List[Dict[str, Any]]] = {
            "farm_1": [],
            "farm_2": [],
        }

        # Time and Weather
        self.day = 1
        self.hour = 8.0
        self.max_hours = 24
        self.current_area = "starting_village"
        self.current_weather = "sunny"
        self.weather_data = {}
        self.times_data = {}

        # Stats tracking
        self.base_max_hp = self.max_hp
        self.base_max_mp = self.max_mp
        self.base_attack = self.attack
        self.base_defense = self.defense
        self.base_speed = self.speed

        self.active_pet: Optional[str] = None
        self.pets_owned: List[str] = []
        self.pets_data: Dict[str, Any] = {}
        self._load_pets_data()
        self._sync_equipment_slots()

    def _sync_equipment_slots(self):
        """Sync legacy equipment slots for compatibility"""
        self.weapon = self.equipment.get("weapon")
        self.armor = self.equipment.get("armor")
        self.accessory = self.equipment.get("accessory_1")
        self.offhand = self.equipment.get("offhand")

    def _update_equipment_slots(self):
        """Update legacy equipment slots when equipment dictionary changes"""
        self.weapon = self.equipment.get("weapon")
        self.armor = self.equipment.get("armor")
        self.accessory = self.equipment.get("accessory_1")
        self.offhand = self.equipment.get("offhand")

    def _load_pets_data(self):
        """Load pet data from data/pets.json"""
        try:
            with open('data/pets.json', 'r', encoding='utf-8') as f:
                self.pets_data = json.load(f)
        except Exception:
            self.pets_data = {}

    def get_pet_boost(self, stat: str) -> float:
        """Get the current pet's boost for a given stat, scaled by land comfort."""
        if not self.active_pet or self.active_pet not in self.pets_data:
            return 0.0

        pet = self.pets_data[self.active_pet]
        boosts = pet.get('boosts', {})
        base_boost = boosts.get(stat, 0.0)
        comfort_multiplier = 1.0 + (self.comfort_points / 1000.0)
        return base_boost * comfort_multiplier

    def is_alive(self) -> bool:
        """Check if character is alive"""
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
        """Apply damage to character, return actual damage taken"""
        base_damage = max(1, damage - self.get_effective_defense())
        remaining = base_damage

        for b in list(self.active_buffs):
            mods = b.get('modifiers', {})
            if remaining <= 0:
                break
            if 'absorb_amount' in mods and mods.get('absorb_amount', 0) > 0:
                avail = mods.get('absorb_amount', 0)
                use = min(avail, remaining)
                remaining -= use
                mods['absorb_amount'] = avail - use
                if all((not isinstance(v, (int, float)) or v == 0)
                       for v in mods.values()):
                    try:
                        self.active_buffs.remove(b)
                    except ValueError:
                        pass

        damage_taken = max(0, remaining)
        self.hp = max(0, self.hp - damage_taken)
        return damage_taken

    def heal(self, amount: int):
        """Heal character"""
        self.hp = min(self.max_hp, self.hp + amount)

    def gain_experience(self, exp: int):
        """Gain experience and level up if needed"""
        self.experience += exp
        while self.experience >= self.experience_to_next:
            self.level_up()

    def level_up(self):
        """Level up the character"""
        self.level += 1
        self.experience -= self.experience_to_next
        self.experience_to_next = int(self.experience_to_next * 1.5)

        if self.level_up_bonuses:
            self.max_hp += self.level_up_bonuses.get("hp", 0)
            self.max_mp += self.level_up_bonuses.get("mp", 0)
            self.attack += self.level_up_bonuses.get("attack", 0)
            self.defense += self.level_up_bonuses.get("defense", 0)
            self.speed += self.level_up_bonuses.get("speed", 0)
        self.hp = self.max_hp
        self._update_rank()

    def _update_rank(self):
        """Simple rank tiers based on level"""
        if self.level >= 100:
            self.rank = "SSR tier adventurer"
        elif self.level >= 90:
            self.rank = "SR tier adventurer"
        elif self.level >= 80:
            self.rank = "SSS tier adventurer"
        elif self.level >= 70:
            self.rank = "SS tier adventurer"
        elif self.level >= 50:
            self.rank = "S tier adventurer"
        elif self.level >= 30:
            self.rank = "A tier adventurer"
        elif self.level >= 20:
            self.rank = "B tier adventurer"
        elif self.level >= 15:
            self.rank = "C tier adventurer"
        elif self.level >= 10:
            self.rank = "D tier adventurer"
        elif self.level >= 5:
            self.rank = "E tier adventurer"
        else:
            self.rank = "F tier adventurer"

    def get_time_period(self) -> str:
        """Get current time period"""
        if not self.times_data:
            return "unknown"
        for period, data in self.times_data.items():
            if data['start_hour'] <= self.hour <= data['end_hour']:
                return period
        return "unknown"

    def get_time_description(self, language_manager: Any) -> str:
        """Get translated time description"""
        period = self.get_time_period()
        if period == "unknown":
            return "The passage of time is strange here..."
        period_data = self.times_data.get(period, {})
        return language_manager.get(period_data.get("description", ""))

    def get_weather_description(self, language_manager: Any) -> str:
        """Get translated weather description"""
        weather_info = self.weather_data.get(self.current_weather, {})
        desc_key = weather_info.get("description",
                                    f"weather_{self.current_weather}_desc")
        is_night = self.hour < 6 or self.hour >= 18
        if is_night:
            night_desc_key = f"{desc_key}_night"
            description = language_manager.get(night_desc_key)
            if description != night_desc_key:
                return description
        return language_manager.get(desc_key,
                                    self.current_weather.capitalize())

    def advance_time(self, minutes: float = 10.0):
        """Advance game time"""
        game_minutes = minutes / 2.0
        self.hour += game_minutes / 60.0
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1

    def update_weather(self, area_data: Dict[str, Any]):
        """Update current weather based on area data and probabilities."""
        import random
        weather_chances = area_data.get("weather_chances", {"sunny": 1.0})
        weathers = list(weather_chances.keys())
        weights = list(weather_chances.values())
        if weathers:
            self.current_weather = random.choices(weathers,
                                                  weights=weights,
                                                  k=1)[0]

    def get_effective_attack(self) -> int:
        """Calculate attack with all bonuses"""
        bonus = sum(
            b.get('modifiers', {}).get('attack_bonus', 0)
            for b in self.active_buffs)
        pet_boost = self.get_pet_boost('attack')
        return int((self.attack + bonus) * (1.0 + pet_boost))

    def get_effective_defense(self) -> int:
        """Calculate defense with all bonuses"""
        bonus = sum(
            b.get('modifiers', {}).get('defense_bonus', 0)
            for b in self.active_buffs)
        pet_boost = self.get_pet_boost('defense')
        base_def = (self.defense + bonus) * (1.0 + pet_boost)
        return int(base_def * 1.5) if self.defending else int(base_def)

    def get_effective_speed(self) -> int:
        """Calculate speed with all bonuses"""
        bonus = sum(
            b.get('modifiers', {}).get('speed_bonus', 0)
            for b in self.active_buffs)
        pet_boost = self.get_pet_boost('speed')
        return int((self.speed + bonus) * (1.0 + pet_boost))

    def display_stats(self):
        """Display character stats"""
        from utilities.UI import Colors
        from utilities.battle import create_hp_mp_bar

        gui_print(
            f"\n{Colors.wrap(f'=== {self.name} ({self.character_class}) ===', Colors.CYAN)}"
        )
        gui_print(f"Level: {self.level} ({self.rank})")
        gui_print(f"HP: {create_hp_mp_bar(self.hp, self.max_hp, 20, Colors.RED)}")
        gui_print(f"MP: {create_hp_mp_bar(self.mp, self.max_mp, 20, Colors.BLUE)}")
        gui_print(
            f"EXP: {create_hp_mp_bar(self.experience, self.experience_to_next, 20, Colors.GREEN)}"
        )
        gui_print(f"Gold: {Colors.wrap(str(self.gold), Colors.GOLD)}")
        gui_print(f"Attack: {self.get_effective_attack()} (Base: {self.attack})")
        gui_print(
            f"Defense: {self.get_effective_defense()} (Base: {self.defense})")
        gui_print(f"Speed: {self.get_effective_speed()} (Base: {self.speed})")
        if self.equipment:
            gui_print("\nEquipment:")
            for slot, item in self.equipment.items():
                gui_print(f"  {slot.replace('_', ' ').title()}: {item or 'None'}")

    def update_stats_from_equipment(
            self,
            items_data: Dict[str, Any],
            companions_data: Optional[Dict[str, Any]] = None):
        """Update character stats based on current equipment and companions"""
        self.attack = self.base_attack
        self.defense = self.base_defense
        self.speed = self.base_speed
        self.max_hp = self.base_max_hp
        self.max_mp = self.base_max_mp

        for slot, item_name in self.equipment.items():
            if item_name and item_name in items_data:
                item = items_data[item_name]
                stats = item.get("stats", {})
                self.attack += stats.get("attack", 0)
                self.defense += stats.get("defense", 0)
                self.speed += stats.get("speed", 0)
                self.max_hp += stats.get("hp", 0)
                self.max_mp += stats.get("mp", 0)

        if companions_data and self.companions:
            for companion in self.companions:
                comp_name = companion.get('name') if isinstance(
                    companion, dict) else companion
                comp_data = next((c for c in companions_data.values()
                                  if c.get('name') == comp_name), None)
                if comp_data:
                    self.attack += comp_data.get("attack_bonus", 0)
                    self.defense += comp_data.get("defense_bonus", 0)
                    self.speed += comp_data.get("speed_bonus", 0)

    def apply_buff(self, name: str, duration: int, modifiers: Dict[str, Any]):
        """Apply a buff to the character"""
        self.active_buffs.append({
            "name": name,
            "duration": duration,
            "modifiers": modifiers
        })

    def equip(self, item_name: str, items_data: Dict[str, Any]):
        """Equip an item from inventory"""
        if item_name not in self.inventory:
            return False

        item = items_data.get(item_name)
        if not item:
            return False

        slot = item.get("type")
        if slot not in self.equipment:
            return False

        # Unequip existing if any
        self.unequip(slot, items_data)

        self.equipment[slot] = item_name
        self.inventory.remove(item_name)
        self._update_equipment_slots()
        self.update_stats_from_equipment(items_data)
        return True

    def unequip(self, slot: str, items_data: Dict[str, Any]):
        """Unequip an item from a slot"""
        if slot not in self.equipment:
            return False

        item_name = self.equipment.get(slot)
        if not item_name:
            return False

        self.equipment[slot] = None
        self.inventory.append(item_name)
        self._update_equipment_slots()
        self.update_stats_from_equipment(items_data)
        return True

    def tick_buffs(self) -> bool:
        """Tick active buffs, return True if any expired or changed stats"""
        changed = False
        for buff in list(self.active_buffs):
            buff["duration"] -= 1
            if buff["duration"] <= 0:
                self.active_buffs.remove(buff)
                changed = True
        return changed

    def display_available_classes(self, classes_data: Dict[str, Any],
                                  lang: Any):
        """Display all available character classes from classes.json"""
        from main import Colors
        gui_print(f"\n{lang.get('ui_choose_class', 'Choose your class:')}")

        color_map = [
            Colors.RED, Colors.BLUE, Colors.GREEN, Colors.YELLOW,
            Colors.MAGENTA, Colors.CYAN, Colors.WHITE, Colors.GOLD
        ]

        for i, (class_name, class_data) in enumerate(classes_data.items(), 1):
            color = color_map[(i - 1) % len(color_map)]
            description = class_data.get("description",
                                         "No description available")
            gui_print(f"{color}{i}. {class_name}{Colors.END} - {description}")

    def select_class(self, classes_data: Dict[str, Any], lang: Any) -> str:
        """Allow user to select a class from available options"""
        import difflib
        from main import enable_tab_completion, disable_tab_completion, ask

        class_names = list(classes_data.keys())

        # Try to enable tab-completion for class names (best-effort)
        try:
            enable_tab_completion(class_names)
        except Exception:
            pass

        try:
            while True:
                prompt = f"Enter class choice (1-{len(class_names)}) or name: "
                choice = ask(prompt, allow_empty=False)
                if choice.isdigit():
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(class_names):
                        return class_names[choice_idx]
                    else:
                        gui_print(
                            f"Invalid choice. Please enter a number between 1 and {len(class_names)}."
                        )
                        continue

                # Try to match by name (case-insensitive)
                matches = [
                    cn for cn in class_names if cn.lower() == choice.lower()
                ]
                if matches:
                    return matches[0]

                # Try close matches
                close = difflib.get_close_matches(
                    choice.lower(), [cn.lower() for cn in class_names], n=1)
                if close:
                    # return the real-cased version
                    for cn in class_names:
                        if cn.lower() == close[0]:
                            return cn
                gui_print(
                    "Invalid class name. Try again or use the numeric choice.")
        finally:
            # restore completer
            try:
                disable_tab_completion(None)
            except Exception:
                pass

    def create_character(self, classes_data: Dict[str, Any],
                         items_data: Dict[str, Any], lang: Any):
        """Create a new character"""
        from main import Colors, ask, clear_screen

        gui_print(
            f"{Colors.BOLD}{lang.get('character_creation', 'Character Creation')}{Colors.END}"
        )
        gui_print(lang.get("separator_30", "=" * 30))

        name = ask(lang.get("enter_name", "Enter your name: "))
        if not name:
            name = "Hero"

        # Use dynamic class selection instead of hardcoded options
        self.display_available_classes(classes_data, lang)

        character_class = self.select_class(classes_data, lang)

        # Set character properties
        self.name = name
        self.character_class = character_class

        # Load class data
        if character_class in classes_data:
            self.class_data = classes_data[character_class]
            stats = self.class_data.get("base_stats", {})
            self.level_up_bonuses = self.class_data.get("level_up_bonuses", {})
        else:
            stats = {
                "hp": 100,
                "mp": 50,
                "attack": 10,
                "defense": 8,
                "speed": 10
            }

        self.max_hp = stats.get("hp", 100)
        self.hp = self.max_hp
        self.max_mp = stats.get("mp", 50)
        self.mp = self.max_mp
        self.attack = stats.get("attack", 10)
        self.defense = stats.get("defense", 8)
        self.speed = stats.get("speed", 10)

        # Update base stats
        self.base_max_hp = self.max_hp
        self.base_max_mp = self.max_mp
        self.base_attack = self.attack
        self.base_defense = self.defense
        self.base_speed = self.speed

        gui_print(
            lang.get(
                "welcome_adventurer",
                "Welcome, adventurer {name}! You are a {char_class}.").format(
                    name=name, char_class=character_class))

        # Give starting items based on class data
        self.give_starting_items(character_class, classes_data, items_data,
                                 lang)

        self.display_stats()

    def give_starting_items(self, character_class: str,
                            classes_data: Dict[str, Any],
                            items_data: Dict[str, Any], lang: Any):
        """Grant starting items based on character class from classes.json"""
        if character_class not in classes_data:
            return

        class_info = classes_data[character_class]
        items = class_info.get("starting_items", [])
        starting_gold = class_info.get("starting_gold", 100)

        for item in items:
            self.inventory.append(item)

        self.gold = starting_gold

        if items:
            from main import Colors
            gui_print(
                f"{Colors.YELLOW}You received starting equipment:{Colors.END}")
            for item in items:
                gui_print(f"  - {item}")

        # Auto-equip first weapon and armor if available
        for slot in ("weapon", "armor"):
            for item in items:
                item_type = items_data.get(item, {}).get("type")
                if item_type == slot:
                    self.equip(item, items_data)
                    from main import Colors
                    gui_print(
                        lang.get("equipped_msg",
                                 "Equipped {item}").format(item=item))
                    break
