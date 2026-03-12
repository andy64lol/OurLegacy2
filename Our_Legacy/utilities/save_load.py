import json
import os
from datetime import datetime
from typing import Dict, Any
from utilities.settings import Colors


class SaveLoadSystem:

    def __init__(self, game_instance):
        self.game = game_instance
        self.player = game_instance.player
        self.lang = game_instance.lang
        self.items_data = game_instance.items_data
        self.classes_data = game_instance.classes_data
        self.companions_data = game_instance.companions_data
        self.missions_data = game_instance.missions_data

    def save_game(self, filename_prefix: str = ""):
        """Save the game with an optional filename prefix."""
        if not self.game.player:
            print(self.lang.get('no_character_save'))
            return

        p = self.game.player
        save_data = {
            "player": {
                "name": p.name,
                "uuid": p.uuid,
                "character_class": p.character_class,
                "level": p.level,
                "experience": p.experience,
                "experience_to_next": p.experience_to_next,
                "max_hp": p.max_hp,
                "hp": p.hp,
                "max_mp": p.max_mp,
                "mp": p.mp,
                "attack": p.attack,
                "defense": p.defense,
                "speed": p.speed,
                "inventory": p.inventory,
                "gold": p.gold,
                "equipment": p.equipment,
                "companions": p.companions,
                "base_stats": {
                    "base_max_hp": p.base_max_hp,
                    "base_max_mp": p.base_max_mp,
                    "base_attack": p.base_attack,
                    "base_defense": p.base_defense,
                    "base_speed": p.base_speed
                },
                "class_data": p.class_data,
                "rank": p.rank,
                "active_buffs": p.active_buffs,
                "housing_owned": getattr(p, 'housing_owned', []),
                "comfort_points": getattr(p, 'comfort_points', 0),
                "building_slots": getattr(p, 'building_slots', {}),
                "farm_plots": getattr(p, 'farm_plots', {}),
                "hour": getattr(p, 'hour', 8),
                "day": getattr(p, 'day', 1),
                "current_weather": getattr(p, 'current_weather', "sunny"),
                "active_pet": getattr(p, 'active_pet', None),
                "pets_owned": getattr(p, 'pets_owned', [])
            },
            "current_area": self.game.current_area,
            "visited_areas": list(self.game.visited_areas),
            "mission_progress": self.game.mission_progress,
            "completed_missions": self.game.completed_missions,
            "achievements": getattr(self.game, 'achievements', []),
            "save_version": "3.1",
            "save_time": datetime.now().isoformat(),
            "bosses_killed": getattr(p, 'bosses_killed', {}),
            "hour": getattr(p, 'hour', 8),
            "day": getattr(p, 'day', 1),
            "current_weather": getattr(p, 'current_weather', "sunny")
        }

        saves_dir = "data/saves"
        os.makedirs(saves_dir, exist_ok=True)
        safe_prefix = (filename_prefix or "").replace('/', '_')

        overwrite_by_uuid = self.game.mod_manager.settings.get(
            "overwrite_save_by_uuid", False)
        if overwrite_by_uuid and not filename_prefix:
            existing_save = None
            for f in os.listdir(saves_dir):
                if f.endswith(
                        '.json'
                ) and f"{p.uuid[:8]}" in f and not f.startswith('err_save'):
                    existing_save = f
                    break
            filename = os.path.join(saves_dir,
                                    existing_save) if existing_save else None
        else:
            filename = None

        if not filename:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{saves_dir}/{safe_prefix}{p.name}_{p.uuid[:8]}_save_{timestamp}_{p.character_class}_{p.level}.json"

        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)
        print(
            self.lang.get("game_saved_success",
                          "Game saved successfully: {filename}").format(
                              filename=filename))

    def load_game(self):
        """Load a saved game."""
        saves_dir = "data/saves"
        if not os.path.exists(saves_dir):
            print(self.lang.get('no_save_files', "No save files found."))
            return

        save_files = [f for f in os.listdir(saves_dir) if f.endswith('.json')]
        if not save_files:
            print(self.lang.get('no_save_files', "No save files found."))
            return

        print(self.lang.get('available_save_files', "Available save files:"))
        for i, save_file in enumerate(save_files, 1):
            print(f"{i}. {save_file.replace('_save.json', '')}")

        choice = self.game.ask(
            self.lang.get(
                "load_save_prompt",
                "Load save (1-{count}) or press Enter to cancel: ").format(
                    count=len(save_files)))
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(save_files):
                filename = os.path.join(saves_dir, save_files[idx])
                try:
                    with open(filename, 'r') as f:
                        save_data = json.load(f)
                    self._load_save_data_internal(save_data)
                except Exception as e:
                    print(
                        self.lang.get(
                            "error_loading_save",
                            "Error loading save file: {error}").format(
                                error=e))

    def _load_save_data_internal(self, save_data: Dict[str, Any]):
        from utilities.character import Character
        save_version = save_data.get("save_version", "1.0")
        player_data = save_data["player"]

        self.game.player = Character(player_data["name"],
                                     player_data["character_class"],
                                     self.game.classes_data,
                                     player_uuid=player_data.get("uuid"))
        p = self.game.player
        p.level = player_data["level"]
        p.experience = player_data["experience"]
        p.experience_to_next = player_data["experience_to_next"]
        p.max_hp = player_data["max_hp"]
        p.hp = player_data["hp"]
        p.max_mp = player_data["max_mp"]
        p.mp = player_data["mp"]
        p.attack = player_data["attack"]
        p.defense = player_data["defense"]
        p.speed = player_data["speed"]
        p.inventory = player_data["inventory"]
        p.gold = player_data["gold"]
        p.rank = player_data.get("rank", p.rank)
        p.active_buffs = player_data.get("active_buffs", p.active_buffs)
        p.companions = player_data.get("companions", [])
        p.housing_owned = player_data.get("housing_owned", [])
        p.comfort_points = player_data.get("comfort_points", 0)
        p.building_slots = player_data.get("building_slots", {})
        p.farm_plots = player_data.get("farm_plots", {
            "farm_1": [],
            "farm_2": []
        })
        p.active_pet = player_data.get("active_pet")
        p.pets_owned = player_data.get("pets_owned", [])
        p.bosses_killed = save_data.get("bosses_killed", {})
        p.hour = save_data.get("hour", player_data.get("hour", 8))
        p.day = save_data.get("day", player_data.get("day", 1))
        p.current_weather = save_data.get(
            "current_weather", player_data.get("current_weather", "sunny"))

        self._load_equipment_data(player_data, save_version)

        self.game.current_area = save_data["current_area"]
        self.game.visited_areas = set(save_data.get("visited_areas", []))
        self.game.mission_progress = save_data.get("mission_progress", {})
        self.game.completed_missions = save_data.get("completed_missions", [])
        self.game.achievements = save_data.get("achievements", [])

        if not self.game.mission_progress and "current_missions" in save_data:
            for mid in save_data["current_missions"]:
                mission = self.game.missions_data.get(mid)
                if mission:
                    mtype = mission.get('type', 'kill')
                    tcount = mission.get('target_count', 1)
                    if mtype == 'collect' and isinstance(tcount, dict):
                        self.game.mission_progress[mid] = {
                            'current_counts': {
                                item: 0
                                for item in tcount.keys()
                            },
                            'target_counts': tcount,
                            'completed': False,
                            'type': mtype
                        }
                    else:
                        self.game.mission_progress[mid] = {
                            'current_count': 0,
                            'target_count': tcount,
                            'completed': False,
                            'type': mtype
                        }

        try:
            p._update_rank()
        except Exception:
            pass
        p.update_stats_from_equipment(self.game.items_data,
                                      self.game.companions_data)
        print(
            self.lang.get(
                "game_loaded_welcome",
                "Game loaded successfully! Welcome back, {player_name}!").
            format(player_name=p.name))
        p.display_stats()

    def _validate_and_fix_equipment(self):
        p = self.game.player
        invalid = []

        for slot in ("weapon", "armor", "accessory"):
            item_name = p.equipment.get(slot)
            if not item_name:
                continue

            if item_name not in self.game.items_data:
                invalid.append((slot, item_name, "Item no longer exists"))
                p.equipment[slot] = None
                continue

            it = self.game.items_data[item_name]
            if it.get("type") != slot:
                invalid.append((slot, item_name, "Item type mismatch"))
                p.equipment[slot] = None
                continue

            reqs = it.get("requirements", {})
            lreq = reqs.get("level", 0)
            creq = reqs.get("class")

            if p.level < lreq:
                invalid.append((slot, item_name, f"Level {lreq} required"))
                p.equipment[slot] = None
            elif creq and creq != p.character_class:
                invalid.append((slot, item_name, f"{creq} class required"))
                p.equipment[slot] = None

        if invalid:
            print(
                f"\n{Colors.YELLOW}{self.lang.get('invalid_items_unequipped', 'Some items were auto-unequipped:')}{Colors.END}"
            )
            for s, n, r in invalid:
                print(f"  - {s.title()}: {n} ({r})")

    def _load_equipment_data(self, player_data: Dict, save_version: str):
        p = self.game.player
        if save_version >= "2.0":
            p.equipment = player_data.get("equipment", {
                "weapon": None,
                "armor": None,
                "accessory": None
            })
            bs = player_data.get("base_stats", {})
            if bs:
                p.base_max_hp = bs.get("base_max_hp", p.base_max_hp)
                p.base_max_mp = bs.get("base_max_mp", p.base_max_mp)
                p.base_attack = bs.get("base_attack", p.base_attack)
                p.base_defense = bs.get("base_defense", p.base_defense)
                p.base_speed = bs.get("base_speed", p.base_speed)
            cd = player_data.get("class_data", {})
            if cd:
                p.class_data = cd
                p.level_up_bonuses = cd.get("level_up_bonuses", {})
        else:
            print(
                f"{Colors.YELLOW}{self.lang.get('legacy_save_warning', 'Loading legacy save. Equipment may not be restored.')}{Colors.END}"
            )
            eq = {"weapon": None, "armor": None, "accessory": None}
            for item in player_data.get("inventory", []):
                it = self.game.items_data.get(item, {})
                itype = it.get("type")
                if itype in eq and not eq[itype]:
                    eq[itype] = item
            p.equipment = eq

        self._validate_and_fix_equipment()
        p.update_stats_from_equipment(self.game.items_data)
