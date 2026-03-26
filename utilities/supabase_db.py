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

def _is_valid_email(email: str) -> bool:
    """Basic email format check."""
    import re
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def register_user(username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
    """
    Register a new user account.
    Email is optional but must be unique and valid if provided.
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

    email_clean: Optional[str] = None
    if email:
        email_clean = email.strip().lower()
        if not _is_valid_email(email_clean):
            return {"ok": False, "message": "Invalid email address."}

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

        if email_clean:
            email_taken = (
                client.table("ol2_users")
                .select("id")
                .eq("email", email_clean)
                .execute()
            )
            if email_taken.data:
                return {"ok": False, "message": "An account with that email already exists."}

        pw_hash, salt = _hash_password(password)
        row: Dict[str, Any] = {"username": username, "pw_hash": pw_hash, "salt": salt}
        if email_clean:
            row["email"] = email_clean
        client.table("ol2_users").insert(row).execute()
        return {"ok": True, "message": f"Account '{username}' created successfully!"}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Registration failed: {e}"}


def login_user(username_or_email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate a user by username or email.
    Returns {'ok': bool, 'message': str, 'user_id': str|None, 'username': str|None}
    """
    identifier = username_or_email.strip().lower()
    by_email = "@" in identifier

    def _do():
        client = _get_client()
        if by_email:
            result = (
                client.table("ol2_users")
                .select("id, username, pw_hash, salt")
                .eq("email", identifier)
                .execute()
            )
        else:
            result = (
                client.table("ol2_users")
                .select("id, username, pw_hash, salt")
                .eq("username", identifier)
                .execute()
            )
        if not result.data:
            return {"ok": False, "message": "Invalid username/email or password.", "user_id": None, "username": None}
        row = result.data[0]
        pw_hash, _ = _hash_password(password, salt=row["salt"])
        if pw_hash != row["pw_hash"]:
            return {"ok": False, "message": "Invalid username/email or password.", "user_id": None, "username": None}
        actual_username = row["username"]
        return {"ok": True, "message": f"Welcome back, {actual_username}!", "user_id": str(row["id"]), "username": actual_username}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Login failed: {e}", "user_id": None, "username": None}


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


# ─── Adventure Groups ─────────────────────────────────────────────────────────

_GROUP_MAX_MEMBERS = 6
_GROUP_XP_CURVE_FACTOR = 1.4


def _group_xp_to_next(level: int) -> int:
    """XP needed to reach the next group level."""
    return int(100 * (_GROUP_XP_CURVE_FACTOR ** (level - 1)))


def create_group(leader: str, name: str, description: str = "") -> Dict[str, Any]:
    """Create a new adventure group. Returns invite_code on success."""
    name = name.strip()
    if not name or len(name) < 2 or len(name) > 32:
        return {"ok": False, "message": "Group name must be 2–32 characters."}
    if contains_profanity(name):
        return {"ok": False, "message": "Group name contains inappropriate language."}

    def _do():
        client = _get_client()
        # Check player is not already in a group
        existing = client.table("ol2_group_members").select("group_id").eq("username", leader).execute()
        if existing.data:
            return {"ok": False, "message": "You are already in a group. Leave it first."}
        # Check group name not taken
        taken = client.table("ol2_groups").select("id").eq("name", name).execute()
        if taken.data:
            return {"ok": False, "message": "A group with that name already exists."}
        invite_code = secrets.token_hex(4).upper()
        group_res = client.table("ol2_groups").insert({
            "name": name,
            "leader": leader,
            "level": 1,
            "xp": 0,
            "xp_to_next": _group_xp_to_next(1),
            "gold_pool": 0,
            "invite_code": invite_code,
            "description": description.strip()[:200],
        }).execute()
        group_id = group_res.data[0]["id"]
        client.table("ol2_group_members").insert({"group_id": group_id, "username": leader, "contribution_xp": 0}).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": leader, "action": f"founded the group \"{name}\"!", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"Group \"{name}\" created!", "invite_code": invite_code, "group_id": group_id}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed to create group: {e}"}


def join_group(username: str, invite_code: str) -> Dict[str, Any]:
    """Join a group by its invite code."""
    invite_code = invite_code.strip().upper()

    def _do():
        client = _get_client()
        existing = client.table("ol2_group_members").select("group_id").eq("username", username).execute()
        if existing.data:
            return {"ok": False, "message": "You are already in a group. Leave it first."}
        group_res = client.table("ol2_groups").select("id, name, leader, level").eq("invite_code", invite_code).execute()
        if not group_res.data:
            return {"ok": False, "message": "Invalid invite code."}
        group = group_res.data[0]
        group_id = group["id"]
        member_count = client.table("ol2_group_members").select("id", count="exact").eq("group_id", group_id).execute()
        if (member_count.count or 0) >= _GROUP_MAX_MEMBERS:
            return {"ok": False, "message": f"Group is full (max {_GROUP_MAX_MEMBERS} members)."}
        client.table("ol2_group_members").insert({"group_id": group_id, "username": username, "contribution_xp": 0}).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": "joined the group!", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"Joined group \"{group['name']}\"!", "group_id": group_id, "group_name": group["name"]}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed to join group: {e}"}


def leave_group(username: str) -> Dict[str, Any]:
    """Leave current group. If leader and other members remain, promotes the next member."""
    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False, "message": "You are not in a group."}
        group_id = mem_res.data[0]["group_id"]
        group_res = client.table("ol2_groups").select("id, name, leader").eq("id", group_id).execute()
        group = group_res.data[0]
        client.table("ol2_group_members").delete().eq("username", username).execute()
        all_members = client.table("ol2_group_members").select("username").eq("group_id", group_id).execute()
        if not all_members.data:
            client.table("ol2_groups").delete().eq("id", group_id).execute()
            return {"ok": True, "message": "You left and the group was disbanded (no members remaining)."}
        if group["leader"] == username:
            new_leader = all_members.data[0]["username"]
            client.table("ol2_groups").update({"leader": new_leader}).eq("id", group_id).execute()
            client.table("ol2_group_log").insert({"group_id": group_id, "username": new_leader, "action": f"became the new leader (previous leader left).", "xp_awarded": 0, "gold_awarded": 0}).execute()
        else:
            client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": "left the group.", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"You left the group \"{group['name']}\"."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed to leave group: {e}"}


def kick_group_member(leader: str, target: str) -> Dict[str, Any]:
    """Leader kicks a member from the group."""
    if leader == target:
        return {"ok": False, "message": "You cannot kick yourself."}

    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id").eq("username", leader).execute()
        if not mem_res.data:
            return {"ok": False, "message": "You are not in a group."}
        group_id = mem_res.data[0]["group_id"]
        group_res = client.table("ol2_groups").select("leader, name").eq("id", group_id).execute()
        if group_res.data[0]["leader"] != leader:
            return {"ok": False, "message": "Only the group leader can kick members."}
        target_res = client.table("ol2_group_members").select("id").eq("group_id", group_id).eq("username", target).execute()
        if not target_res.data:
            return {"ok": False, "message": f"{target} is not in your group."}
        client.table("ol2_group_members").delete().eq("username", target).eq("group_id", group_id).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": target, "action": f"was kicked by the leader.", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"{target} was removed from the group."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def get_user_group(username: str) -> Dict[str, Any]:
    """Return full group info for the user's current group, or None."""
    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id, contribution_xp, joined_at").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False, "group": None}
        group_id = mem_res.data[0]["group_id"]
        group_res = client.table("ol2_groups").select("*").eq("id", group_id).execute()
        if not group_res.data:
            return {"ok": False, "group": None}
        group = group_res.data[0]
        members = client.table("ol2_group_members").select("username, contribution_xp, joined_at").eq("group_id", group_id).execute()
        log = client.table("ol2_group_log").select("username, action, xp_awarded, gold_awarded, created_at").eq("group_id", group_id).order("created_at", desc=True).limit(30).execute()
        return {"ok": True, "group": {**group, "members": members.data or [], "log": log.data or []}}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "group": None}


def contribute_to_group(username: str, xp: int, gold: int, action: str) -> Dict[str, Any]:
    """
    Add XP and gold to the user's group. Handles group leveling.
    Returns {ok, leveled_up, new_level, bonus_xp, bonus_gold}.
    """
    if xp <= 0 and gold <= 0:
        return {"ok": False}

    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id, contribution_xp").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False}
        group_id = mem_res.data[0]["group_id"]
        contrib_xp = mem_res.data[0]["contribution_xp"] + xp
        client.table("ol2_group_members").update({"contribution_xp": contrib_xp}).eq("username", username).eq("group_id", group_id).execute()
        group_res = client.table("ol2_groups").select("level, xp, xp_to_next, gold_pool").eq("id", group_id).execute()
        g = group_res.data[0]
        new_xp = g["xp"] + xp
        new_gold_pool = g["gold_pool"] + gold
        level = g["level"]
        xp_to_next = g["xp_to_next"]
        leveled_up = False
        while new_xp >= xp_to_next:
            new_xp -= xp_to_next
            level += 1
            xp_to_next = _group_xp_to_next(level)
            leveled_up = True
        client.table("ol2_groups").update({"xp": new_xp, "xp_to_next": xp_to_next, "level": level, "gold_pool": new_gold_pool}).eq("id", group_id).execute()
        if xp > 0 or gold > 0:
            client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": action, "xp_awarded": xp, "gold_awarded": gold}).execute()
        bonus_xp = 20 * level if leveled_up else 0
        bonus_gold = 30 * level if leveled_up else 0
        member_usernames: List[str] = []
        if leveled_up:
            mres = client.table("ol2_group_members").select("username").eq("group_id", group_id).execute()
            member_usernames = [m["username"] for m in (mres.data or [])]
            client.table("ol2_group_log").insert({"group_id": group_id, "username": "System", "action": f"Group reached level {level}! All members receive a bonus.", "xp_awarded": bonus_xp, "gold_awarded": bonus_gold}).execute()
        return {"ok": True, "leveled_up": leveled_up, "new_level": level, "group_id": group_id, "bonus_xp": bonus_xp, "bonus_gold": bonus_gold, "members": member_usernames}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False}


def collect_group_gold(username: str) -> Dict[str, Any]:
    """Distribute an equal share of the group gold pool to all members (capped per call)."""
    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False, "message": "You are not in a group."}
        group_id = mem_res.data[0]["group_id"]
        group_res = client.table("ol2_groups").select("gold_pool, leader, name").eq("id", group_id).execute()
        g = group_res.data[0]
        if g["gold_pool"] <= 0:
            return {"ok": False, "message": "The group treasury is empty."}
        member_count = client.table("ol2_group_members").select("id", count="exact").eq("group_id", group_id).execute()
        count = max(1, member_count.count or 1)
        share = g["gold_pool"] // count
        if share < 1:
            return {"ok": False, "message": "Not enough gold to distribute yet."}
        client.table("ol2_groups").update({"gold_pool": 0}).eq("id", group_id).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": f"triggered a treasury distribution ({share} gold per member).", "xp_awarded": 0, "gold_awarded": share}).execute()
        return {"ok": True, "message": f"You collected {share} gold from the group treasury!", "gold": share, "group_id": group_id}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}


def get_group_leaderboard() -> List[Dict[str, Any]]:
    """Return top 10 groups by level, then XP."""
    def _do():
        client = _get_client()
        res = client.table("ol2_groups").select("name, leader, level, xp, xp_to_next, gold_pool").order("level", desc=True).order("xp", desc=True).limit(10).execute()
        rows = res.data or []
        enriched = []
        for i, row in enumerate(rows):
            member_count = client.table("ol2_group_members").select("id", count="exact").eq("group_id", row.get("id", "")).execute() if row.get("id") else None
            enriched.append({**row, "rank": i + 1, "member_count": 0})
        return enriched

    def _do_simple():
        client = _get_client()
        res = client.table("ol2_groups").select("id, name, leader, level, xp, xp_to_next").order("level", desc=True).order("xp", desc=True).limit(10).execute()
        rows = res.data or []
        result = []
        for i, row in enumerate(rows):
            mc = client.table("ol2_group_members").select("username", count="exact").eq("group_id", row["id"]).execute()
            result.append({**row, "rank": i + 1, "member_count": mc.count or 0})
        return result

    try:
        return _run(_do_simple)
    except Exception:
        return []


def get_player_leaderboard() -> List[Dict[str, Any]]:
    """Return top 10 players by level from the ol2_characters table."""
    def _do():
        client = _get_client()
        import json as _json
        res = (
            client.table("ol2_characters")
            .select("player_name, level, current_area, game_state")
            .order("level", desc=True)
            .limit(10)
            .execute()
        )
        result = []
        for i, row in enumerate(res.data or []):
            try:
                gs = row.get("game_state") or {}
                if isinstance(gs, str):
                    gs = _json.loads(gs)
                player_data = gs.get("player") or {}
                character_class = player_data.get("character_class", "Adventurer")
                rank = player_data.get("rank", "")
                experience = player_data.get("experience", 0)
            except Exception:
                character_class = "Adventurer"
                rank = ""
                experience = 0
            result.append({
                "rank": i + 1,
                "player_name": row.get("player_name", "Unknown"),
                "level": row.get("level", 1),
                "character_class": character_class,
                "player_rank": rank,
                "experience": experience,
                "current_area": row.get("current_area", ""),
            })
        return result

    try:
        return _run(_do)
    except Exception:
        return []


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


# ─── Email Management ────────────────────────────────────────────────────────


EMAIL_VERIFICATION_EXPIRY = 86400  # 24 hours


def get_user_email(user_id: str) -> Optional[str]:
    """Return the verified email address for the given user_id, or None."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_users")
            .select("email, email_verified")
            .eq("id", user_id)
            .execute()
        )
        if result.data:
            row = result.data[0]
            if row.get("email_verified") and row.get("email"):
                return row["email"]
        return None

    try:
        return _run(_do)
    except Exception:
        return None


def get_pending_email_verification(user_id: str) -> Optional[str]:
    """Return the pending (unverified) email if there is an active verification request."""
    import datetime

    def _do():
        client = _get_client()
        result = (
            client.table("ol2_email_verifications")
            .select("email, created_at")
            .eq("user_id", user_id)
            .eq("verified", False)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        try:
            created_at = datetime.datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            age = (datetime.datetime.now(datetime.timezone.utc) - created_at).total_seconds()
            if age > EMAIL_VERIFICATION_EXPIRY:
                return None
        except Exception:
            pass
        return row["email"]

    try:
        return _run(_do)
    except Exception:
        return None


def request_email_verification(user_id: str, email: str) -> Dict[str, Any]:
    """
    Create a pending email verification token. Does NOT save the email yet.
    Returns {'ok': bool, 'message': str, 'token': str|None, 'email': str|None}
    """
    email_clean = email.strip().lower()
    if not email_clean:
        return {"ok": False, "message": "Please enter an email address.", "token": None, "email": None}
    if not _is_valid_email(email_clean):
        return {"ok": False, "message": "Invalid email address format.", "token": None, "email": None}

    def _do():
        client = _get_client()
        taken = (
            client.table("ol2_users")
            .select("id")
            .eq("email", email_clean)
            .eq("email_verified", True)
            .neq("id", user_id)
            .execute()
        )
        if taken.data:
            return {"ok": False, "message": "That email is already linked to another account.", "token": None, "email": None}

        token = secrets.token_urlsafe(32)
        client.table("ol2_email_verifications").insert({
            "user_id": user_id,
            "email": email_clean,
            "token": token,
            "verified": False,
        }).execute()
        return {"ok": True, "message": "Verification email sent.", "token": token, "email": email_clean}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Could not create verification: {e}", "token": None, "email": None}


def verify_email_token(token: str) -> Dict[str, Any]:
    """
    Validate an email verification token and save the email as verified on the user's account.
    Returns {'ok': bool, 'message': str, 'user_id': str|None}
    """
    import datetime

    token = token.strip()
    if not token:
        return {"ok": False, "message": "Invalid verification link.", "user_id": None}

    def _do():
        client = _get_client()
        result = (
            client.table("ol2_email_verifications")
            .select("id, user_id, email, created_at, verified")
            .eq("token", token)
            .execute()
        )
        if not result.data:
            return {"ok": False, "message": "Verification link is invalid or has expired.", "user_id": None}

        row = result.data[0]
        if row["verified"]:
            return {"ok": False, "message": "This email has already been verified.", "user_id": None}

        try:
            created_at = datetime.datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            age = (datetime.datetime.now(datetime.timezone.utc) - created_at).total_seconds()
            if age > EMAIL_VERIFICATION_EXPIRY:
                return {"ok": False, "message": "Verification link has expired. Please request a new one.", "user_id": None}
        except Exception:
            pass

        user_id = row["user_id"]
        email = row["email"]

        taken = (
            client.table("ol2_users")
            .select("id")
            .eq("email", email)
            .neq("id", user_id)
            .execute()
        )
        if taken.data:
            return {"ok": False, "message": "That email is already linked to another account.", "user_id": None}

        client.table("ol2_users").update({
            "email": email,
            "email_verified": True,
        }).eq("id", user_id).execute()

        client.table("ol2_email_verifications").update({"verified": True}).eq("id", row["id"]).execute()

        return {"ok": True, "message": "Email verified successfully!", "user_id": user_id}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Verification failed: {e}", "user_id": None}


# ─── Password Reset ───────────────────────────────────────────────────────────

RESET_TOKEN_EXPIRY_SECONDS = 3600  # 1 hour


def create_password_reset_token(email: str) -> Dict[str, Any]:
    """
    Look up a user by email, generate a secure reset token, store it, and
    return {'ok': bool, 'message': str, 'token': str|None, 'email': str|None}.
    Always returns ok=True with a generic message to avoid user-enumeration.
    """
    email_clean = email.strip().lower()
    if not email_clean:
        return {"ok": False, "message": "Please enter your email address.", "token": None, "email": None}

    def _do():
        client = _get_client()
        result = (
            client.table("ol2_users")
            .select("id, email")
            .eq("email", email_clean)
            .execute()
        )
        if not result.data:
            return {"ok": True, "message": "sent", "token": None, "email": None}

        user = result.data[0]
        token = secrets.token_urlsafe(32)
        client.table("ol2_password_resets").insert({
            "user_id": user["id"],
            "token": token,
            "used": False,
        }).execute()
        return {"ok": True, "message": "sent", "token": token, "email": email_clean}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Reset request failed: {e}", "token": None, "email": None}


def reset_password_with_token(token: str, new_password: str) -> Dict[str, Any]:
    """
    Validate a reset token and update the user's password.
    Returns {'ok': bool, 'message': str}
    """
    import datetime

    token = token.strip()
    if not token:
        return {"ok": False, "message": "Invalid reset link."}
    if not new_password or len(new_password) < 6:
        return {"ok": False, "message": "Password must be at least 6 characters."}

    def _do():
        client = _get_client()
        result = (
            client.table("ol2_password_resets")
            .select("id, user_id, created_at, used")
            .eq("token", token)
            .execute()
        )
        if not result.data:
            return {"ok": False, "message": "Reset link is invalid or has expired."}

        row = result.data[0]
        if row["used"]:
            return {"ok": False, "message": "This reset link has already been used."}

        created_at_str = row["created_at"]
        try:
            created_at = datetime.datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            age = (now - created_at).total_seconds()
            if age > RESET_TOKEN_EXPIRY_SECONDS:
                return {"ok": False, "message": "Reset link has expired. Please request a new one."}
        except Exception:
            pass

        pw_hash, salt = _hash_password(new_password)
        client.table("ol2_users").update(
            {"pw_hash": pw_hash, "salt": salt}
        ).eq("id", row["user_id"]).execute()

        client.table("ol2_password_resets").update(
            {"used": True}
        ).eq("id", row["id"]).execute()

        return {"ok": True, "message": "Password updated successfully. You can now sign in."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Password reset failed: {e}"}
