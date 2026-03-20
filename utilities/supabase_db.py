"""
Supabase integration for Our Legacy 2.
Handles user accounts (username + hashed password), cloud saves, and global chat.

All Supabase calls are executed inside gevent's native thread pool (tpool) to
avoid the httpx/asyncio vs gevent event-loop conflict that causes silent hangs
on gunicorn+gevent deployments (e.g. Render).
"""
import os
import hashlib
import base64
import secrets
from typing import Optional, Dict, Any, List

try:
    from gevent import tpool as _tpool
    def _run(fn, *args, **kwargs):
        return _tpool.execute(fn, *args, **kwargs)
except ImportError:
    def _run(fn, *args, **kwargs):
        return fn(*args, **kwargs)

from supabase import create_client, Client
from utilities.save_load import encrypt_save, decrypt_save

try:
    from better_profanity import profanity as _profanity
    _profanity.load_censor_words()
    _PROFANITY_AVAILABLE = True
except Exception:
    _PROFANITY_AVAILABLE = False


def contains_profanity(text: str) -> bool:
    if not _PROFANITY_AVAILABLE:
        return False
    return _profanity.contains_profanity(text)


def censor_text(text: str) -> str:
    if not _PROFANITY_AVAILABLE:
        return text
    return _profanity.censor(text)


SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials not configured.")
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with SHA-256 + salt. Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return h, salt


# ─── Account Management ───────────────────────────────────────────────────────

def register_user(username: str, password: str) -> Dict[str, Any]:
    """
    Register a new user account.
    Returns {'ok': bool, 'message': str}
    """
    username = username.strip().lower()
    if not username or len(username) < 3:
        return {"ok": False, "message": "Username must be at least 3 characters."}
    if len(username) > 20:
        return {"ok": False, "message": "Username must be 20 characters or fewer."}
    if not password or len(password) < 6:
        return {"ok": False, "message": "Password must be at least 6 characters."}
    if contains_profanity(username):
        return {"ok": False, "message": "Username contains inappropriate language."}

    def _do():
        client = _get_client()
        existing = (
            client.table("ol2_users")
            .select("id")
            .eq("username", username)
            .execute()
        )
        if existing.data:
            return {"ok": False, "message": "Username already taken."}
        pw_hash, salt = _hash_password(password)
        client.table("ol2_users").insert(
            {"username": username, "pw_hash": pw_hash, "salt": salt}
        ).execute()
        return {"ok": True, "message": f"Account '{username}' created successfully!"}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Registration failed: {e}"}


def login_user(username: str, password: str) -> Dict[str, Any]:
    """
    Authenticate a user.
    Returns {'ok': bool, 'message': str, 'user_id': str|None}
    """
    username = username.strip().lower()

    def _do():
        client = _get_client()
        result = (
            client.table("ol2_users")
            .select("id, pw_hash, salt")
            .eq("username", username)
            .execute()
        )
        if not result.data:
            return {"ok": False, "message": "Invalid username or password.", "user_id": None}
        row = result.data[0]
        pw_hash, _ = _hash_password(password, salt=row["salt"])
        if pw_hash != row["pw_hash"]:
            return {"ok": False, "message": "Invalid username or password.", "user_id": None}
        return {"ok": True, "message": f"Welcome back, {username}!", "user_id": str(row["id"])}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Login failed: {e}", "user_id": None}


# ─── Cloud Save / Load ────────────────────────────────────────────────────────

def cloud_save(user_id: str, save_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save game state to Supabase as an encrypted blob.
    Each user has one cloud save slot (upsert by user_id).
    Returns {'ok': bool, 'message': str}
    """
    encrypted_bytes = encrypt_save(save_data)
    encoded = base64.b64encode(encrypted_bytes).decode("utf-8")
    player = save_data.get("player", {})
    row = {
        "user_id": user_id,
        "save_blob": encoded,
        "player_name": player.get("name", ""),
        "level": player.get("level", 1),
        "character_class": player.get("class", ""),
        "current_area": save_data.get("current_area", ""),
    }

    def _do():
        client = _get_client()
        client.table("ol2_saves").upsert(row, on_conflict="user_id").execute()
        return {"ok": True, "message": "Game saved to the cloud!"}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Cloud save failed: {e}"}


def cloud_load(user_id: str) -> Dict[str, Any]:
    """
    Load game state from Supabase for the given user.
    Returns {'ok': bool, 'message': str, 'data': dict|None}
    """
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_saves")
            .select("save_blob, player_name, level, updated_at")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data

    try:
        data = _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Cloud load failed: {e}", "data": None}

    if not data:
        return {"ok": False, "message": "No cloud save found.", "data": None}

    try:
        row = data[0]
        raw_bytes = base64.b64decode(row["save_blob"].encode("utf-8"))
        save = decrypt_save(raw_bytes)
        return {
            "ok": True,
            "message": f"Loaded save for {row['player_name']} (Lv.{row['level']})",
            "data": save,
        }
    except Exception as e:
        return {"ok": False, "message": f"Cloud load failed: {e}", "data": None}


def get_cloud_save_meta(user_id: str) -> Optional[Dict[str, Any]]:
    """Return metadata about the user's cloud save, or None if none exists."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_saves")
            .select("player_name, level, character_class, current_area, updated_at")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data

    try:
        data = _run(_do)
        return data[0] if data else None
    except Exception:
        return None


# ─── Global Chat ──────────────────────────────────────────────────────────────

def send_chat_message(username: str, message: str) -> Dict[str, Any]:
    """Store a chat message in Supabase. Returns {'ok': bool, 'row': dict}."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_chat")
            .insert({"username": username, "message": message})
            .execute()
        )
        return result.data

    try:
        data = _run(_do)
        if data:
            return {"ok": True, "row": data[0]}
        return {"ok": False, "row": None}
    except Exception as e:
        return {"ok": False, "row": None, "error": str(e)}


def get_chat_history(limit: int = 60) -> List[Dict[str, Any]]:
    """Return the most recent chat messages, oldest first."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_chat")
            .select("username, message, created_at")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []

    try:
        return _run(_do)
    except Exception:
        return []
