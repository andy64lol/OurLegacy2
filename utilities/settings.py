from utilities.gui import gui_print
"""
Settings Management for Our Legacy
Centralized configuration and settings handler
Extracted from main.py and enhanced
"""

import json
import os
from typing import Dict, List, Any, Optional

# Default settings - originally from main.py
DEFAULT_SETTINGS = {
    "mods_enabled": True,
    "disabled_mods": [],
    "overwrite_save_by_uuid": False,
    "language": "en"
}


class SettingsManager:
    """Manages game settings and configuration"""
    
    def __init__(self, settings_file: str = "data/mod_settings.json"):
        self.settings_file = settings_file
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError, OSError) as e:
            gui_print(f"Warning: Could not load settings: {e}")
            self.settings = DEFAULT_SETTINGS.copy()
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except (IOError, OSError) as e:
            gui_print(f"Error saving settings: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Set a setting value"""
        self.settings[key] = value
        return self.save_settings()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = DEFAULT_SETTINGS.copy()
        return self.save_settings()
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self.settings.copy()
    
    def update_multiple(self, settings_dict: Dict[str, Any]) -> bool:
        """Update multiple settings at once"""
        self.settings.update(settings_dict)
        return self.save_settings()


from utilities.UI import Colors

# Global settings manager instance
_settings_manager = None

def get_settings_manager() -> SettingsManager:
    """Get or create the global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager

def get_setting(key: str, default=None):
    """Convenience function to get a setting"""
    return get_settings_manager().get(key, default)

def set_setting(key: str, value: Any) -> bool:
    """Convenience function to set a setting"""
    return get_settings_manager().set(key, value)
