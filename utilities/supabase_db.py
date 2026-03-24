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


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

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


# ─── Friends ──────────────────────────────────────────────────────────────────

def send_friend_request(requester: str, target: str) -> Dict[str, Any]:
    """Send a friend request. Returns {'ok': bool, 'message': str}."""
    if requester == target:
        return {"ok": False, "message": "You can't add yourself."}

    def _do():
        client = _get_client()
        exists = client.table("ol2_users").select("id").eq("username", target).execute()
        if not exists.data:
            return {"ok": False, "message": "User not found."}
        existing = (
            client.table("ol2_friends")
            .select("id, status, requester")
            .or_(f"and(requester.eq.{requester},target.eq.{target}),and(requester.eq.{target},target.eq.{requester})")
            .execute()
        )
        if existing.data:
            row = existing.data[0]
            if row["status"] == "accepted":
                return {"ok": False, "message": "You are already friends."}
            elif row["status"] == "pending":
                if row["requester"] == requester:
                    return {"ok": False, "message": "Friend request already sent."}
                else:
                    client.table("ol2_friends").update({"status": "accepted"}).eq("id", row["id"]).execute()
                    return {"ok": True, "message": f"You are now friends with {target}!", "accepted": True}
        client.table("ol2_friends").insert({"requester": requester, "target": target, "status": "pending"}).execute()
        return {"ok": True, "message": f"Friend request sent to {target}!", "accepted": False}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def respond_friend_request(request_id: str, accept: bool, current_user: str) -> Dict[str, Any]:
    """Accept or reject a pending friend request."""
    def _do():
        client = _get_client()
        row = client.table("ol2_friends").select("id, requester, target, status").eq("id", request_id).execute()
        if not row.data:
            return {"ok": False, "message": "Request not found."}
        r = row.data[0]
        if r["target"] != current_user:
            return {"ok": False, "message": "Not authorized."}
        if r["status"] != "pending":
            return {"ok": False, "message": "Request already handled."}
        if accept:
            client.table("ol2_friends").update({"status": "accepted"}).eq("id", request_id).execute()
            return {"ok": True, "message": f"You are now friends with {r['requester']}!", "friend": r["requester"]}
        else:
            client.table("ol2_friends").delete().eq("id", request_id).execute()
            return {"ok": True, "message": "Request declined.", "friend": r["requester"]}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def remove_friend(user_a: str, user_b: str) -> Dict[str, Any]:
    """Remove a friendship between two users."""
    def _do():
        client = _get_client()
        client.table("ol2_friends").delete().or_(
            f"and(requester.eq.{user_a},target.eq.{user_b}),and(requester.eq.{user_b},target.eq.{user_a})"
        ).execute()
        return {"ok": True, "message": f"Removed {user_b} from friends."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def get_friends(username: str) -> Dict[str, Any]:
    """Get all friends and pending requests for a user."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_friends")
            .select("id, requester, target, status, created_at")
            .or_(f"requester.eq.{username},target.eq.{username}")
            .execute()
        )
        friends: List[Dict] = []
        incoming: List[Dict] = []
        outgoing: List[Dict] = []
        for r in (result.data or []):
            if r["status"] == "accepted":
                other = r["target"] if r["requester"] == username else r["requester"]
                friends.append({"username": other, "id": r["id"]})
            elif r["status"] == "pending":
                if r["requester"] == username:
                    outgoing.append({"username": r["target"], "id": r["id"]})
                else:
                    incoming.append({"username": r["requester"], "id": r["id"]})
        return {"ok": True, "friends": friends, "incoming": incoming, "outgoing": outgoing}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "friends": [], "incoming": [], "outgoing": [], "error": str(e)}


# ─── Private Messages ─────────────────────────────────────────────────────────

def send_dm(sender: str, recipient: str, message: str) -> Dict[str, Any]:
    """Send a private message between two users."""
    message = censor_text(message.strip())
    if not message:
        return {"ok": False, "message": "Message is empty."}
    if len(message) > 500:
        return {"ok": False, "message": "Message too long (max 500 chars)."}

    def _do():
        client = _get_client()
        result = client.table("ol2_dms").insert(
            {"sender": sender, "recipient": recipient, "message": message}
        ).execute()
        return result.data

    try:
        data = _run(_do)
        if data:
            return {"ok": True, "row": data[0]}
        return {"ok": False, "message": "Failed to send."}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def get_dm_conversation(user_a: str, user_b: str, limit: int = 80) -> List[Dict[str, Any]]:
    """Get DM conversation history between two users, oldest first."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_dms")
            .select("id, sender, recipient, message, created_at, read")
            .or_(f"and(sender.eq.{user_a},recipient.eq.{user_b}),and(sender.eq.{user_b},recipient.eq.{user_a})")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []

    try:
        return _run(_do)
    except Exception:
        return []


def mark_dms_read(recipient: str, sender: str) -> None:
    """Mark all DMs from sender to recipient as read."""
    def _do():
        client = _get_client()
        client.table("ol2_dms").update({"read": True}).eq("recipient", recipient).eq("sender", sender).eq("read", False).execute()

    try:
        _run(_do)
    except Exception:
        pass


def get_unread_dm_counts(username: str) -> Dict[str, int]:
    """Return dict of {sender: unread_count} for all unread DMs for username."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_dms")
            .select("sender")
            .eq("recipient", username)
            .eq("read", False)
            .execute()
        )
        counts: Dict[str, int] = {}
        for row in (result.data or []):
            counts[row["sender"]] = counts.get(row["sender"], 0) + 1
        return counts

    try:
        return _run(_do)
    except Exception:
        return {}


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


# ─── Blocks / Blacklist ───────────────────────────────────────────────────────

def block_user(blocker: str, blocked: str) -> Dict[str, Any]:
    """Block a user. Also removes any existing friendship."""
    if blocker == blocked:
        return {"ok": False, "message": "You can't block yourself."}

    def _do():
        client = _get_client()
        exists = client.table("ol2_users").select("id").eq("username", blocked).execute()
        if not exists.data:
            return {"ok": False, "message": "User not found."}
        already = (
            client.table("ol2_blocks")
            .select("id")
            .eq("blocker", blocker)
            .eq("blocked", blocked)
            .execute()
        )
        if not already.data:
            client.table("ol2_blocks").insert({"blocker": blocker, "blocked": blocked}).execute()
        client.table("ol2_friends").delete().or_(
            f"and(requester.eq.{blocker},target.eq.{blocked}),and(requester.eq.{blocked},target.eq.{blocker})"
        ).execute()
        return {"ok": True, "message": f"{blocked} has been blocked."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def unblock_user(blocker: str, blocked: str) -> Dict[str, Any]:
    """Remove a block."""
    def _do():
        client = _get_client()
        client.table("ol2_blocks").delete().eq("blocker", blocker).eq("blocked", blocked).execute()
        return {"ok": True, "message": f"{blocked} has been unblocked."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def is_blocked(sender: str, recipient: str) -> bool:
    """Return True if recipient has blocked sender."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_blocks")
            .select("id")
            .eq("blocker", recipient)
            .eq("blocked", sender)
            .execute()
        )
        return bool(result.data)

    try:
        return _run(_do)
    except Exception:
        return False


def get_blocked_by_me(username: str) -> List[str]:
    """Return list of usernames blocked by username."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_blocks")
            .select("blocked")
            .eq("blocker", username)
            .execute()
        )
        return [r["blocked"] for r in (result.data or [])]

    try:
        return _run(_do)
    except Exception:
        return []


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


# ─── Persistent Character (Phase 1 MMO) ───────────────────────────────────────

def character_autosave(user_id: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist the full structured game state for a logged-in character.
    Uses an upsert on user_id so each account has exactly one live character row.
    Returns {'ok': bool, 'message': str}
    """
    import json as _json

    player = game_state.get("player") or {}
    row = {
        "user_id": user_id,
        "player_name": player.get("name", ""),
        "level": player.get("level", 1),
        "character_class": player.get("class", ""),
        "current_area": game_state.get("current_area", "starting_village"),
        "game_state": _json.dumps(game_state),
    }

    def _do():
        client = _get_client()
        client.table("ol2_characters").upsert(row, on_conflict="user_id").execute()
        return {"ok": True, "message": "Character auto-saved."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Character autosave failed: {e}"}


def character_autoload(user_id: str) -> Dict[str, Any]:
    """
    Load the persistent game state for a logged-in user.
    Returns {'ok': bool, 'message': str, 'data': dict|None}
    """
    import json as _json

    def _do():
        client = _get_client()
        result = (
            client.table("ol2_characters")
            .select("player_name, level, game_state, updated_at")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data

    try:
        rows = _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Character load failed: {e}", "data": None}

    if not rows:
        return {"ok": False, "message": "No persistent character found.", "data": None}

    row = rows[0]
    try:
        raw = row["game_state"]
        if isinstance(raw, str):
            state = _json.loads(raw)
        else:
            state = dict(raw)
        return {
            "ok": True,
            "message": f"Loaded {row['player_name']} (Lv.{row['level']})",
            "data": state,
        }
    except Exception as e:
        return {"ok": False, "message": f"Character load failed: {e}", "data": None}


def character_delete(user_id: str) -> Dict[str, Any]:
    """Delete the persistent character for a user (e.g. when starting a new character)."""
    def _do():
        client = _get_client()
        client.table("ol2_characters").delete().eq("user_id", user_id).execute()
        return {"ok": True, "message": "Character deleted."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Delete failed: {e}"}


def get_all_activities(exclude_user_id: str = None) -> List[Dict[str, Any]]:
    """
    Return a list of {player_name, activity_status, current_area} for all
    characters saved within the last 60 minutes.  Used to show online players'
    current activity in the travel feed.
    """
    import json as _json
    from datetime import datetime, timezone, timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    def _do():
        client = _get_client()
        q = (
            client.table("ol2_characters")
            .select("user_id, player_name, current_area, game_state")
            .gte("updated_at", cutoff)
        )
        if exclude_user_id:
            q = q.neq("user_id", exclude_user_id)
        result = q.execute()
        return result.data or []

    try:
        rows = _run(_do)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        try:
            gs = row.get("game_state") or {}
            if isinstance(gs, str):
                gs = _json.loads(gs)
            player_data = gs.get("player") or {}
            activity = player_data.get("activity_status", "exploring")
        except Exception:
            activity = "exploring"
        out.append({
            "player_name": row.get("player_name", "Unknown"),
            "current_area": row.get("current_area", ""),
            "activity_status": activity,
        })
    return out
