import json
import os
from typing import Dict, Any, Optional

class LanguageManager:
    """Manages language loading and translation"""

    def __init__(self, get_setting_func=None, set_setting_func=None):
        self.config: Dict[str, Any] = {}
        self.translations: Dict[str, str] = {}
        self.get_setting = get_setting_func
        self.set_setting = set_setting_func
        
        # Get language from settings, fallback to 'en'
        if self.get_setting:
            self.current_language = self.get_setting("language", "en")
        else:
            self.current_language = "en"
            
        self.load_config()
        self.load_translations()

    def load_config(self):
        """Load language configuration"""
        try:
            with open('data/languages/config.json', 'r') as f:
                self.config = json.load(f)
                # Ensure current_language matches settings
                if self.get_setting:
                    self.current_language = self.get_setting(
                        "language", self.config.get('default_language', 'en'))
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback defaults
            self.config = {
                "default_language": "en",
                "available_languages": {
                    "en": "English",
                    "es": "Español",
                    "zh_simp": "简体中文"
                },
                "fallback_language": "en",
                "overwrite_save_files": True
            }

    def change_language(self, lang_code: str):
        """Change current language and save to settings"""
        if lang_code in self.config.get("available_languages", {}):
            self.current_language = lang_code
            if self.set_setting:
                self.set_setting("language", lang_code)
            self.load_translations()
            return True
        return False

    def load_translations(self):
        """Load translation strings for current language"""
        try:
            lang_file = f'data/languages/{self.current_language}.json'
            with open(lang_file, 'r') as f:
                self.translations = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to English if current language fails
            if self.current_language != 'en':
                try:
                    with open('data/languages/en.json', 'r') as f:
                        self.translations = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    self.translations = {}

    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Get translated string with robust formatting and escape handling"""
        # Get translation, fallback to default or key if not found
        text = self.translations.get(key,
                                     default if default is not None else key)

        # Handle literal escape sequences found in JSON files
        text = text.replace("\\n", "\n").replace("\\033", "\033").replace(
            "\\x1b", "\x1b").replace("\\r", "\r")

        if kwargs:
            try:
                # Ensure all values in kwargs are strings for .format() if they are numbers
                formatted_kwargs = {k: str(v) for k, v in kwargs.items()}
                text = text.format(**formatted_kwargs)
            except (KeyError, ValueError, IndexError):
                # Fallback for missing placeholders in translation strings
                if key == "current_location" and "area" in kwargs and "{area}" not in text:
                    text = f"{text} {kwargs['area']}"
                elif key == "welcome_adventurer" and "name" in kwargs and "{name}" not in text:
                    text = f"{text} {kwargs['name']}"

        return text

    def should_overwrite_saves(self) -> bool:
        """Check if save files should be overwritten"""
        return self.config.get('overwrite_save_files', True)
