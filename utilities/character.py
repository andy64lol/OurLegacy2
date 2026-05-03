import json
import uuid
from typing import Dict, List, Any, Optional

class Character:

    def __init__(self,
                 name: str,
                 character_class: str,
                 classes_data: Optional[Dict] = None,
                 player_uuid: Optional[str] = None):
        self.name = name
        self.character_class = character_class
        self.uuid = player_uuid or str(uuid.uuid4())

        self.rank = "F tier adventurer"
        self.level = 1
        self.experience = 0
        self.experience_to_next = 100
        self.class_data = {}
        self.level_up_bonuses = {}

        if classes_data and character_class in classes_data:
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
        self.defending = False

        self.equipment: Dict[str, Optional[str]] = {
            "weapon": None,
            "armor": None,
            "offhand": None,
            "accessory_1": None,
            "accessory_2": None,
            "accessory_3": None,
        }

        self.inventory: List[str] = []
        self.gold = 100
        self.companions: List[Dict[str, Any]] = []
        self.active_buffs: List[Dict[str, Any]] = []
        self.bosses_killed: Dict[str, str] = {}

        self.housing_owned: List[str] = []
        self.comfort_points: int = 0
        self.building_slots: Dict[str, Optional[str]] = {}
        self.farm_plots: Dict[str, List] = {"farm_1": [], "farm_2": []}

        self.day = 1
        self.hour = 8.0
        self.current_weather = "sunny"

        self.base_max_hp = self.max_hp
        self.base_max_mp = self.max_mp
        self.base_attack = self.attack
        self.base_defense = self.defense
        self.base_speed = self.speed

        self.active_pet: Optional[str] = None
        self.pets_owned: List[str] = []
        self.pets_data: Dict[str, Any] = self._load_pets_data()
        self._update_rank()

    def _load_pets_data(self) -> Dict[str, Any]:
        try:
            with open('data/pets.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError, KeyError):
            return {}

    def _update_rank(self):
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

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: int) -> int:
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
        damage_taken = max(0, remaining)
        self.hp = max(0, self.hp - damage_taken)
        return damage_taken

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def gain_experience(self, exp: int) -> bool:
        self.experience += exp
        leveled = False
        while self.experience >= self.experience_to_next:
            self.level_up()
            leveled = True
        return leveled

    def level_up(self):
        self.level += 1
        self.experience -= self.experience_to_next
        self.experience_to_next = int(self.experience_to_next * 1.5)
        if self.level_up_bonuses:
            self.base_max_hp += self.level_up_bonuses.get("hp", 0)
            self.base_max_mp += self.level_up_bonuses.get("mp", 0)
            self.base_attack += self.level_up_bonuses.get("attack", 0)
            self.base_defense += self.level_up_bonuses.get("defense", 0)
            self.base_speed += self.level_up_bonuses.get("speed", 0)
            self.max_hp = self.base_max_hp
            self.max_mp = self.base_max_mp
        self.hp = self.max_hp
        self.mp = self.max_mp
        self._update_rank()

    def get_pet_boost(self, stat: str) -> float:
        if not self.active_pet or self.active_pet not in self.pets_data:
            return 0.0
        pet = self.pets_data[self.active_pet]
        boosts = pet.get('boosts', {})
        base_boost = boosts.get(stat, 0.0)
        comfort_multiplier = 1.0 + (self.comfort_points / 1000.0)
        return base_boost * comfort_multiplier

    def get_effective_attack(self) -> int:
        bonus = sum(
            b.get('modifiers', {}).get('attack_bonus', 0)
            for b in self.active_buffs)
        pet_boost = self.get_pet_boost('attack')
        return int((self.attack + bonus) * (1.0 + pet_boost))

    def get_effective_defense(self) -> int:
        bonus = sum(
            b.get('modifiers', {}).get('defense_bonus', 0)
            for b in self.active_buffs)
        pet_boost = self.get_pet_boost('defense')
        base_def = (self.defense + bonus) * (1.0 + pet_boost)
        return int(base_def * 1.5) if self.defending else int(base_def)

    def get_effective_speed(self) -> int:
        bonus = sum(
            b.get('modifiers', {}).get('speed_bonus', 0)
            for b in self.active_buffs)
        pet_boost = self.get_pet_boost('speed')
        return int((self.speed + bonus) * (1.0 + pet_boost))

    def update_stats_from_equipment(
            self,
            items_data: Dict[str, Any],
            companions_data: Optional[Dict[str, Any]] = None):
        self.attack = self.base_attack
        self.defense = self.base_defense
        self.speed = self.base_speed
        self.max_hp = self.base_max_hp
        self.max_mp = self.base_max_mp
        for _slot, item_name in self.equipment.items():
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
        self.active_buffs.append({
            "name": name,
            "duration": duration,
            "modifiers": modifiers
        })

    def tick_buffs(self) -> bool:
        changed = False
        for buff in list(self.active_buffs):
            buff["duration"] -= 1
            if buff["duration"] <= 0:
                self.active_buffs.remove(buff)
                changed = True
        return changed

    def equip(self, item_name: str, items_data: Dict[str, Any]) -> bool:
        if item_name not in self.inventory:
            return False
        item = items_data.get(item_name)
        if not item:
            return False
        slot = item.get("type")
        if slot not in self.equipment:
            return False
        self.unequip(slot, items_data)
        self.equipment[slot] = item_name
        self.inventory.remove(item_name)
        self.update_stats_from_equipment(items_data)
        return True

    def unequip(self, slot: str, items_data: Dict[str, Any]) -> bool:
        if slot not in self.equipment:
            return False
        item_name = self.equipment.get(slot)
        if not item_name:
            return False
        self.equipment[slot] = None
        self.inventory.append(item_name)
        self.update_stats_from_equipment(items_data)
        return True

    def get_stats_dict(self) -> Dict[str, Any]:
        from utilities.stats import get_default_attributes
        return {
            "name": self.name,
            "character_class": self.character_class,
            "uuid": self.uuid,
            "level": self.level,
            "rank": self.rank,
            "experience": self.experience,
            "experience_to_next": self.experience_to_next,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "attack": self.get_effective_attack(),
            "defense": self.get_effective_defense(),
            "speed": self.get_effective_speed(),
            "base_attack": self.base_attack,
            "base_defense": self.base_defense,
            "base_speed": self.base_speed,
            "base_max_hp": self.base_max_hp,
            "base_max_mp": self.base_max_mp,
            "gold": self.gold,
            "inventory": self.inventory,
            "equipment": self.equipment,
            "companions": self.companions,
            "active_buffs": self.active_buffs,
            "housing_owned": self.housing_owned,
            "comfort_points": self.comfort_points,
            "building_slots": self.building_slots,
            "active_pet": self.active_pet,
            "pets_owned": self.pets_owned,
            "day": self.day,
            "hour": self.hour,
            "current_weather": self.current_weather,
            "attributes": get_default_attributes(),
            "attr_spell_power": 0,
            "attr_gold_discount": 0.0,
            "attr_discovery": 0.0,
            "dodge_chance": 0.0,
        }

def build_new_character(name: str, character_class: str,
                        classes_data: Dict[str, Any],
                        items_data: Dict[str, Any]) -> Dict[str, Any]:
    char = Character(name, character_class, classes_data)
    cls_data = classes_data.get(character_class, {})
    starting_items = list(cls_data.get("starting_items", ["Health Potion"]))
    starting_gold = cls_data.get("starting_gold", 100)

    char.inventory = starting_items
    char.gold = starting_gold

    for slot in ("weapon", "armor"):
        for item_name in starting_items:
            if items_data.get(item_name, {}).get("type") == slot:
                if item_name in char.inventory:
                    char.inventory.remove(item_name)
                    char.equipment[slot] = item_name
                break

    char.update_stats_from_equipment(items_data)
    return char.get_stats_dict()

def get_available_classes(
        classes_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for class_name, class_data in classes_data.items():
        result.append({
            "name": class_name,
            "description": class_data.get("description", ""),
            "base_stats": class_data.get("base_stats", {}),
            "starting_items": class_data.get("starting_items", []),
            "starting_gold": class_data.get("starting_gold", 100),
        })
    return result
