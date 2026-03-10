"""
Mod Management for Our Legacy
Centralized mod handler
"""

import json
import os
from typing import Dict, List, Any
from utilities.settings import DEFAULT_SETTINGS

class ModManager:
    """Manages mod loading and data merging"""

    def __init__(self, lang=None):
        self.mods_dir = "mods"
        self.mods: Dict[str, Dict[str, Any]] = {}
        self.enabled_mods: List[str] = []
        self.settings_file = "data/mod_settings.json"
        self.settings = DEFAULT_SETTINGS.copy()
        
        if lang is None:
            class MockLang:
                def get(self, key, default=None, **kwargs):
                    return key
            self.lang = MockLang()
        else:
            self.lang = lang
            
        self.load_settings()
        self.discover_mods()

    def load_settings(self):
        """Load mod settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError):
            self.settings = DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """Save mod settings to file"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            print(f"Error saving mod settings: {e}")

    def discover_mods(self):
        """Discover all mods in the mods directory"""
        self.mods = {}
        if not os.path.exists(self.mods_dir):
            return

        for entry in os.listdir(self.mods_dir):
            mod_path = os.path.join(self.mods_dir, entry)
            if os.path.isdir(mod_path):
                mod_json_path = os.path.join(mod_path, "mod.json")
                if os.path.exists(mod_json_path):
                    try:
                        with open(mod_json_path, 'r', encoding='utf-8') as f:
                            mod_data = json.load(f)
                            mod_data['mod_path'] = mod_path
                            mod_data['folder_name'] = entry
                            self.mods[entry] = mod_data
                    except (json.JSONDecodeError, IOError):
                        print(self.lang.get("mod_load_error", "Error loading mod {entry}").format(entry=entry))

    def get_enabled_mods(self) -> List[str]:
        """Get list of enabled mod folder names"""
        if not self.settings.get("mods_enabled", True):
            return []

        disabled = set(self.settings.get("disabled_mods", []))
        return [name for name in self.mods.keys() if name not in disabled]

    def load_mod_data(self, data_type: str) -> Dict[str, Any]:
        """Load and merge data from all enabled mods for a specific data type"""
        merged_data = {}

        for mod_name in self.get_enabled_mods():
            mod = self.mods.get(mod_name)
            if not mod:
                continue

            mod_path = mod.get('mod_path', '')
            file_path = os.path.join(mod_path, data_type)

            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        mod_data = json.load(f)
                        for key, value in mod_data.items():
                            new_key = f"{mod_name}_{key}" if key in merged_data else key
                            merged_data[new_key] = value
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load {data_type} from mod {mod_name}: {e}")

        if data_type == "pets.json":
            mod_pets = self.load_mod_data("pets.json")
            merged_data.update(mod_pets)

        return merged_data

    def get_mod_list(self) -> List[Dict[str, Any]]:
        """Get list of all mods with their metadata and status"""
        mods_list = []
        enabled = self.get_enabled_mods()

        for name, mod in self.mods.items():
            mods_list.append({
                'folder_name': name,
                'name': mod.get('name', name),
                'description': mod.get('description', ''),
                'author': mod.get('author', 'Unknown'),
                'version': mod.get('version', '1.0'),
                'enabled': name in enabled and self.settings.get("mods_enabled", True),
                'mod_path': mod.get('mod_path', '')
            })

        return mods_list

    def toggle_mod(self, folder_name: str):
        """Toggle a mod's enabled state"""
        disabled = set(self.settings.get("disabled_mods", []))

        if folder_name in disabled:
            disabled.remove(folder_name)
            print(self.lang.get("mod_enabled_msg", "Mod enabled: {folder_name}").format(folder_name=folder_name))
        else:
            disabled.add(folder_name)
            print(self.lang.get("mod_disabled_msg", "Mod disabled: {folder_name}").format(folder_name=folder_name))

        self.settings["disabled_mods"] = list(disabled)
        self.save_settings()

    def toggle_mods_system(self):
        """Toggle the entire mods system on/off"""
        self.settings["mods_enabled"] = not self.settings.get("mods_enabled", True)
        status = "enabled" if self.settings["mods_enabled"] else "disabled"
        print(self.lang.get("mod_system_status_msg", "Mod system {status}!").format(status=status))
        self.save_settings()
        return self.settings["mods_enabled"]
