"""
Save/Load System for Our Legacy 2 - Flask Edition
Functions for serializing/deserializing game state (Flask session dicts).
Supports encrypted pickle saves (download/upload) and server-side JSON saves.
"""
import json
import os
import pickle
import hashlib
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional

from cryptography.fernet import Fernet, InvalidToken

SAVES_DIR = "data/saves"
SAVE_VERSION = "3.2"

SAVE_MAGIC = b'OL2S'
SALT_SIZE = 16
APP_SAVE_SECRET = "our_legacy_2_eternal_save_secret_v5"

# ─── Encrypted Pickle Helpers ─────────────────────────────────────────────────


def _derive_key(salt: bytes) -> bytes:
    """Derive a Fernet key from a salt using SHA-256."""
    raw = hashlib.sha256(salt + APP_SAVE_SECRET.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_save(save_data: Dict[str, Any]) -> bytes:
    """
    Serialize and encrypt save_data.
    Returns binary: MAGIC(4) + SALT(16) + fernet_token(variable).
    """
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(salt)
    f = Fernet(key)
    pickled = pickle.dumps(save_data, protocol=4)
    token = f.encrypt(pickled)
    return SAVE_MAGIC + salt + token


def decrypt_save(data: bytes) -> Dict[str, Any]:
    """
    Decrypt and deserialize encrypted save bytes.
    Returns save_data dict.
    Raises ValueError on bad format or decryption failure.
    """
    if not data.startswith(SAVE_MAGIC):
        raise ValueError("Not a valid Our Legacy 2 save file.")
    payload = data[len(SAVE_MAGIC):]
    if len(payload) < SALT_SIZE:
        raise ValueError("Save file is too short or corrupted.")
    salt = payload[:SALT_SIZE]
    token = payload[SALT_SIZE:]
    key = _derive_key(salt)
    f = Fernet(key)
    try:
        pickled = f.decrypt(token)
    except InvalidToken:
        raise ValueError("Save file is corrupted or was modified.")
    return pickle.loads(pickled)


# ─── Server-Side JSON Helpers (legacy) ───────────────────────────────────────


def build_save_data(player: Dict[str, Any],
                    current_area: str,
                    visited_areas: List[str],
                    completed_missions: List[str],
                    achievements: Optional[List] = None) -> Dict[str, Any]:
    """Build a save data dict from current game state."""
    return {
        "player": player,
        "current_area": current_area,
        "visited_areas": list(visited_areas),
        "completed_missions": completed_missions,
        "achievements": achievements or [],
        "save_version": SAVE_VERSION,
        "save_time": datetime.now().isoformat(),
    }


def save_game(player: Dict[str, Any],
              current_area: str,
              visited_areas: List[str],
              completed_missions: List[str],
              achievements: Optional[List] = None,
              filename_prefix: str = "") -> Dict[str, Any]:
    """
    Save game to a JSON file.
    Returns {'ok': bool, 'message': str, 'filename': str}
    """
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        save_data = build_save_data(player, current_area, visited_areas,
                                    completed_missions, achievements)

        name = player.get('name', 'unknown').replace('/', '_')
        pid = player.get('uuid', 'xxxx')[:8]
        cls = player.get('class', player.get('character_class', 'unknown'))
        level = player.get('level', 1)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_prefix = (filename_prefix or "").replace('/', '_')
        filename = f"{SAVES_DIR}/{safe_prefix}{name}_{pid}_save_{timestamp}_{cls}_{level}.json"

        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)

        return {
            'ok': True,
            'message': f'Game saved: {os.path.basename(filename)}',
            'filename': filename
        }
    except Exception as e:
        return {
            'ok': False,
            'message': f'Error saving game: {e}',
            'filename': ''
        }


def list_saves() -> List[Dict[str, Any]]:
    """Return list of available save files with metadata."""
    if not os.path.exists(SAVES_DIR):
        return []

    saves = []
    for fname in sorted(os.listdir(SAVES_DIR)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(SAVES_DIR, fname)
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            player = data.get('player', {})
            saves.append({
                'filename':
                fname,
                'filepath':
                fpath,
                'player_name':
                player.get('name', '?'),
                'character_class':
                player.get('class', player.get('character_class', '?')),
                'level':
                player.get('level', 1),
                'save_time':
                data.get('save_time', ''),
                'save_version':
                data.get('save_version', '?'),
                'current_area':
                data.get('current_area', ''),
            })
        except Exception:
            continue
    return saves


def load_save(filepath: str) -> Dict[str, Any]:
    """
    Load a save file. Returns:
    {'ok': bool, 'message': str, 'player': dict, 'current_area': str,
     'visited_areas': list, 'completed_missions': list, 'achievements': list}
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        player = data.get('player', {})
        current_area = data.get('current_area', 'starting_village')
        visited_areas = data.get('visited_areas', [current_area])
        completed_missions = data.get('completed_missions', [])
        achievements = data.get('achievements', [])

        if not player or not player.get('name'):
            return {
                'ok': False,
                'message': 'Invalid save file: missing player data.'
            }

        return {
            'ok': True,
            'message': f'Welcome back, {player.get("name")}!',
            'player': player,
            'current_area': current_area,
            'visited_areas': visited_areas,
            'completed_missions': completed_missions,
            'achievements': achievements,
        }
    except FileNotFoundError:
        return {'ok': False, 'message': 'Save file not found.'}
    except Exception as e:
        return {'ok': False, 'message': f'Error loading save: {e}'}


def load_save_by_index(index: int) -> Dict[str, Any]:
    """Load a save file by its list index."""
    saves = list_saves()
    if not saves or not (0 <= index < len(saves)):
        return {'ok': False, 'message': 'Invalid save file selection.'}
    return load_save(saves[index]['filepath'])


def delete_save(filepath: str) -> Dict[str, Any]:
    """Delete a save file."""
    try:
        os.remove(filepath)
        return {'ok': True, 'message': 'Save file deleted.'}
    except Exception as e:
        return {'ok': False, 'message': f'Error deleting save: {e}'}
