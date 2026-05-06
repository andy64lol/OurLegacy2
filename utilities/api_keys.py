"""API key management for Our Legacy 2 JSON API."""

import hashlib
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional

_KEYS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".flask_sessions", "api_keys.json"
)

VALID_SCOPES: Dict[str, str] = {
    "game:read":     "Read game state, player info, inventory, area",
    "game:write":    "Explore, travel, rest, mine",
    "shop:write":    "Buy and sell items",
    "inventory:write": "Equip, unequip, and use items",
    "battle:write":  "Attack, defend, flee, cast spells, use items in battle",
    "profile:read":  "Read public profile and leaderboard data",
    "keys:manage":   "Create, list, and revoke API keys",
    "admin":         "Full access (all scopes)",
}

_DEFAULT_SCOPES = ["game:read", "game:write", "shop:write", "inventory:write", "battle:write"]


def _load() -> Dict[str, Any]:
    try:
        with open(_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"keys": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_KEYS_FILE), exist_ok=True)
    tmp = _KEYS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _KEYS_FILE)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _key_id_from_raw(raw: str) -> str:
    return _hash_key(raw)[:16]


def generate_api_key(
    user_id: str,
    username: str,
    name: str,
    scopes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a new API key. Returns the raw key (shown only once) + metadata."""
    if scopes is None:
        scopes = list(_DEFAULT_SCOPES)
    invalid = set(scopes) - set(VALID_SCOPES.keys())
    if invalid:
        return {"ok": False, "message": f"Invalid scopes: {', '.join(sorted(invalid))}"}
    raw = "ol2_" + secrets.token_hex(24)
    key_id = _key_id_from_raw(raw)
    key_hash = _hash_key(raw)
    data = _load()
    # Enforce per-user key limit
    user_keys = [e for e in data["keys"].values() if e.get("user_id") == user_id and e.get("enabled", True)]
    if len(user_keys) >= 20:
        return {"ok": False, "message": "API key limit reached (20 active keys per user). Revoke some keys first."}
    data["keys"][key_id] = {
        "key_id":     key_id,
        "key_hash":   key_hash,
        "user_id":    user_id,
        "username":   username,
        "name":       name,
        "scopes":     list(scopes),
        "created_at": int(time.time()),
        "last_used":  None,
        "enabled":    True,
    }
    _save(data)
    return {
        "ok":      True,
        "key_id":  key_id,
        "raw_key": raw,
        "scopes":  list(scopes),
        "name":    name,
        "note":    "Save this key — it will not be shown again.",
    }


def validate_api_key(raw: str) -> Optional[Dict[str, Any]]:
    """Validate a raw API key. Returns metadata (without hash) or None."""
    if not raw.startswith("ol2_"):
        return None
    key_id = _key_id_from_raw(raw)
    key_hash = _hash_key(raw)
    data = _load()
    entry = data["keys"].get(key_id)
    if not entry or not entry.get("enabled", True):
        return None
    if entry["key_hash"] != key_hash:
        return None
    entry["last_used"] = int(time.time())
    data["keys"][key_id] = entry
    _save(data)
    return {k: v for k, v in entry.items() if k != "key_hash"}


def list_api_keys(user_id: str) -> List[Dict[str, Any]]:
    """List all enabled keys for a user (no hashes)."""
    data = _load()
    return sorted(
        [
            {k: v for k, v in entry.items() if k != "key_hash"}
            for entry in data["keys"].values()
            if entry.get("user_id") == user_id and entry.get("enabled", True)
        ],
        key=lambda e: e.get("created_at", 0),
        reverse=True,
    )


def revoke_api_key(key_id: str, user_id: str) -> bool:
    """Disable a key by ID. Returns True if found and owned by user_id."""
    data = _load()
    entry = data["keys"].get(key_id)
    if not entry or entry.get("user_id") != user_id:
        return False
    entry["enabled"] = False
    data["keys"][key_id] = entry
    _save(data)
    return True


def has_scope(key_meta: Dict[str, Any], required_scope: str) -> bool:
    """Check if a key has the required scope (admin grants all)."""
    scopes = key_meta.get("scopes", [])
    return "admin" in scopes or required_scope in scopes
