import os
import datetime
import hashlib
import base64
import secrets
from typing import Optional, Dict, Any, List

def _run(fn, *args, **kwargs):
    return fn(*args, **kwargs)

from supabase import create_client, Client
from utilities.save_load import encrypt_save, decrypt_save

_profanity: Any = None  # type: ignore[assignment]
_PROFANITY_AVAILABLE = False
try:
    from better_profanity import profanity as _profanity  # type: ignore[assignment]
    _profanity.load_censor_words()
    _PROFANITY_AVAILABLE = True
except Exception:
    pass

def contains_profanity(text: str) -> bool:
    if not _PROFANITY_AVAILABLE or _profanity is None:
        return False
    return bool(_profanity.contains_profanity(text))

def censor_text(text: str) -> str:
    if not _PROFANITY_AVAILABLE or _profanity is None:
        return text
    return str(_profanity.censor(text))

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
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return h, salt

def _is_valid_email(email: str) -> bool:
    import re
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def register_user(username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
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
        pw_hash, _ = _hash_password(password, salt=row["salt"])  # type: ignore[misc]
        if pw_hash != row["pw_hash"]:  # type: ignore[misc]
            return {"ok": False, "message": "Invalid username/email or password.", "user_id": None, "username": None}
        actual_username = row["username"]  # type: ignore[misc]
        return {"ok": True, "message": f"Welcome back, {actual_username}!", "user_id": str(row["id"]), "username": actual_username}  # type: ignore[misc]

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Login failed: {e}", "user_id": None, "username": None}

def cloud_save(user_id: str, save_data: Dict[str, Any]) -> Dict[str, Any]:
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
        raw_bytes = base64.b64decode(row["save_blob"].encode("utf-8"))  # type: ignore[misc]
        save = decrypt_save(raw_bytes)
        return {
            "ok": True,
            "message": f"Loaded save for {row['player_name']} (Lv.{row['level']})",  # type: ignore[misc]
            "data": save,
        }
    except Exception as e:
        return {"ok": False, "message": f"Cloud load failed: {e}", "data": None}

def get_cloud_save_meta(user_id: str) -> Optional[Dict[str, Any]]:
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
        return data[0] if data else None  # type: ignore[misc]
    except Exception:
        return None

def send_friend_request(requester: str, target: str) -> Dict[str, Any]:
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
            if row["status"] == "accepted":  # type: ignore[misc]
                return {"ok": False, "message": "You are already friends."}
            elif row["status"] == "pending":  # type: ignore[misc]
                if row["requester"] == requester:  # type: ignore[misc]
                    return {"ok": False, "message": "Friend request already sent."}
                else:
                    client.table("ol2_friends").update({"status": "accepted"}).eq("id", row["id"]).execute()  # type: ignore[misc]
                    return {"ok": True, "message": f"You are now friends with {target}!", "accepted": True}
        client.table("ol2_friends").insert({"requester": requester, "target": target, "status": "pending"}).execute()
        return {"ok": True, "message": f"Friend request sent to {target}!", "accepted": False}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}

def respond_friend_request(request_id: str, accept: bool, current_user: str) -> Dict[str, Any]:
    def _do():
        client = _get_client()
        row = client.table("ol2_friends").select("id, requester, target, status").eq("id", request_id).execute()
        if not row.data:
            return {"ok": False, "message": "Request not found."}
        r = row.data[0]
        if r["target"] != current_user:  # type: ignore[misc]
            return {"ok": False, "message": "Not authorized."}
        if r["status"] != "pending":  # type: ignore[misc]
            return {"ok": False, "message": "Request already handled."}
        if accept:
            client.table("ol2_friends").update({"status": "accepted"}).eq("id", request_id).execute()
            return {"ok": True, "message": f"You are now friends with {r['requester']}!", "friend": r["requester"]}  # type: ignore[misc]
        else:
            client.table("ol2_friends").delete().eq("id", request_id).execute()
            return {"ok": True, "message": "Request declined.", "friend": r["requester"]}  # type: ignore[misc]

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}

def remove_friend(user_a: str, user_b: str) -> Dict[str, Any]:
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
            if r["status"] == "accepted":  # type: ignore[misc]
                other = r["target"] if r["requester"] == username else r["requester"]  # type: ignore[misc]
                friends.append({"username": other, "id": r["id"]})  # type: ignore[misc]
            elif r["status"] == "pending":  # type: ignore[misc]
                if r["requester"] == username:  # type: ignore[misc]
                    outgoing.append({"username": r["target"], "id": r["id"]})  # type: ignore[misc]
                else:
                    incoming.append({"username": r["requester"], "id": r["id"]})  # type: ignore[misc]
        return {"ok": True, "friends": friends, "incoming": incoming, "outgoing": outgoing}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "friends": [], "incoming": [], "outgoing": [], "error": str(e)}

def send_dm(sender: str, recipient: str, message: str) -> Dict[str, Any]:
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
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return []

def mark_dms_read(recipient: str, sender: str) -> None:
    def _do():
        client = _get_client()
        client.table("ol2_dms").update({"read": True}).eq("recipient", recipient).eq("sender", sender).eq("read", False).execute()

    try:
        _run(_do)
    except Exception:
        pass

def get_unread_dm_counts(username: str) -> Dict[str, int]:
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
            counts[row["sender"]] = counts.get(row["sender"], 0) + 1  # type: ignore[misc]
        return counts

    try:
        return _run(_do)
    except Exception:
        return {}

def send_chat_message(username: str, message: str) -> Dict[str, Any]:
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

def block_user(blocker: str, blocked: str) -> Dict[str, Any]:
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
    def _do():
        client = _get_client()
        client.table("ol2_blocks").delete().eq("blocker", blocker).eq("blocked", blocked).execute()
        return {"ok": True, "message": f"{blocked} has been unblocked."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}

def is_blocked(sender: str, recipient: str) -> bool:
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
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_blocks")
            .select("blocked")
            .eq("blocker", username)
            .execute()
        )
        return [r["blocked"] for r in (result.data or [])]  # type: ignore[misc]

    try:
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return []

def get_chat_history(limit: int = 60) -> List[Dict[str, Any]]:
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
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return []

def clear_chat_history() -> Dict[str, Any]:
    def _do():
        client = _get_client()
        client.table("ol2_chat").delete().gte("created_at", "1970-01-01T00:00:00").execute()
        return {"ok": True}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "error": str(e)}

def character_autosave(user_id: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
    import json as _json

    player = game_state.get("player") or {}
    row = {
        "user_id": user_id,
        "player_name": player.get("name", ""),
        "level": player.get("level", 1),
        "character_class": player.get("class", player.get("character_class", "")),
        "current_area": game_state.get("current_area", "starting_village"),
        # fast-query stat columns (mirrors game_state for leaderboard/display)
        "hp": player.get("hp", 100),
        "gold": player.get("gold", 0),
        "experience": player.get("experience", 0),
        "game_state": _json.dumps(game_state),
    }

    def _do():
        client = _get_client()
        client.table("ol2_characters").upsert(row, on_conflict="user_id").execute()
        return {"ok": True, "message": "Character saved."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Character save failed: {e}"}

def character_autoload(user_id: str) -> Dict[str, Any]:
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
        raw = row["game_state"]  # type: ignore[misc]
        if isinstance(raw, str):
            state = _json.loads(raw)
        else:
            state = dict(raw)  # type: ignore[misc]
        return {
            "ok": True,
            "message": f"Loaded {row['player_name']} (Lv.{row['level']})",  # type: ignore[misc]
            "data": state,
        }
    except Exception as e:
        return {"ok": False, "message": f"Character load failed: {e}", "data": None}

def character_delete(user_id: str) -> Dict[str, Any]:
    def _do():
        client = _get_client()
        client.table("ol2_characters").delete().eq("user_id", user_id).execute()
        return {"ok": True, "message": "Character deleted."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Delete failed: {e}"}

_GROUP_MAX_MEMBERS = 6
_GROUP_XP_CURVE_FACTOR = 1.4

def _group_xp_to_next(level: int) -> int:
    return int(100 * (_GROUP_XP_CURVE_FACTOR ** (level - 1)))

def create_group(leader: str, name: str, description: str = "") -> Dict[str, Any]:
    name = name.strip()
    if not name or len(name) < 2 or len(name) > 32:
        return {"ok": False, "message": "Group name must be 2–32 characters."}
    if contains_profanity(name):
        return {"ok": False, "message": "Group name contains inappropriate language."}

    def _do():
        client = _get_client()
        existing = client.table("ol2_group_members").select("group_id").eq("username", leader).execute()
        if existing.data:
            return {"ok": False, "message": "You are already in a group. Leave it first."}
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
        group_id = group_res.data[0]["id"]  # type: ignore[misc]
        client.table("ol2_group_members").insert({"group_id": group_id, "username": leader, "contribution_xp": 0}).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": leader, "action": f"founded the group \"{name}\"!", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"Group \"{name}\" created!", "invite_code": invite_code, "group_id": group_id}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed to create group: {e}"}

def join_group(username: str, invite_code: str) -> Dict[str, Any]:
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
        group_id = group["id"]  # type: ignore[misc]
        member_count = client.table("ol2_group_members").select("id", count="exact").eq("group_id", group_id).execute()  # type: ignore[misc]
        if (member_count.count or 0) >= _GROUP_MAX_MEMBERS:
            return {"ok": False, "message": f"Group is full (max {_GROUP_MAX_MEMBERS} members)."}
        client.table("ol2_group_members").insert({"group_id": group_id, "username": username, "contribution_xp": 0}).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": "joined the group!", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"Joined group \"{group['name']}\"!", "group_id": group_id, "group_name": group["name"]}  # type: ignore[misc]

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed to join group: {e}"}

def leave_group(username: str) -> Dict[str, Any]:
    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False, "message": "You are not in a group."}
        group_id = mem_res.data[0]["group_id"]  # type: ignore[misc]
        group_res = client.table("ol2_groups").select("id, name, leader").eq("id", group_id).execute()
        group = group_res.data[0]
        client.table("ol2_group_members").delete().eq("username", username).execute()
        all_members = client.table("ol2_group_members").select("username").eq("group_id", group_id).execute()
        if not all_members.data:
            client.table("ol2_groups").delete().eq("id", group_id).execute()
            return {"ok": True, "message": "You left and the group was disbanded (no members remaining)."}
        if group["leader"] == username:  # type: ignore[misc]
            new_leader = all_members.data[0]["username"]  # type: ignore[misc]
            client.table("ol2_groups").update({"leader": new_leader}).eq("id", group_id).execute()
            client.table("ol2_group_log").insert({"group_id": group_id, "username": new_leader, "action": "became the new leader (previous leader left).", "xp_awarded": 0, "gold_awarded": 0}).execute()
        else:
            client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": "left the group.", "xp_awarded": 0, "gold_awarded": 0}).execute()
        return {"ok": True, "message": f"You left the group \"{group['name']}\"."}  # type: ignore[misc]

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed to leave group: {e}"}

def kick_group_member(leader: str, target: str) -> Dict[str, Any]:
    if leader == target:
        return {"ok": False, "message": "You cannot kick yourself."}

    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id").eq("username", leader).execute()
        if not mem_res.data:
            return {"ok": False, "message": "You are not in a group."}
        group_id = mem_res.data[0]["group_id"]  # type: ignore[misc]
        group_res = client.table("ol2_groups").select("leader, name").eq("id", group_id).execute()
        if group_res.data[0]["leader"] != leader:  # type: ignore[misc]
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
    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id, contribution_xp, joined_at").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False, "group": None}
        group_id = mem_res.data[0]["group_id"]  # type: ignore[misc]
        group_res = client.table("ol2_groups").select("*").eq("id", group_id).execute()
        if not group_res.data:
            return {"ok": False, "group": None}
        group = group_res.data[0]
        members = client.table("ol2_group_members").select("username, contribution_xp, joined_at").eq("group_id", group_id).execute()
        log = client.table("ol2_group_log").select("username, action, xp_awarded, gold_awarded, created_at").eq("group_id", group_id).order("created_at", desc=True).limit(30).execute()
        return {"ok": True, "group": {**group, "members": members.data or [], "log": log.data or []}}  # type: ignore[misc]

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "group": None}

def contribute_to_group(username: str, xp: int, gold: int, action: str) -> Dict[str, Any]:
    if xp <= 0 and gold <= 0:
        return {"ok": False}

    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id, contribution_xp").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False}
        group_id = mem_res.data[0]["group_id"]  # type: ignore[misc]
        contrib_xp = mem_res.data[0]["contribution_xp"] + xp  # type: ignore[misc]
        client.table("ol2_group_members").update({"contribution_xp": contrib_xp}).eq("username", username).eq("group_id", group_id).execute()
        group_res = client.table("ol2_groups").select("level, xp, xp_to_next, gold_pool").eq("id", group_id).execute()
        g = group_res.data[0]
        new_xp = g["xp"] + xp  # type: ignore[misc]
        new_gold_pool = g["gold_pool"] + gold  # type: ignore[misc]
        level = g["level"]  # type: ignore[misc]
        xp_to_next = g["xp_to_next"]  # type: ignore[misc]
        leveled_up = False
        while new_xp >= xp_to_next:  # type: ignore[misc]
            new_xp -= xp_to_next  # type: ignore[misc]
            level += 1  # type: ignore[misc]
            xp_to_next = _group_xp_to_next(level)  # type: ignore[misc]
            leveled_up = True
        client.table("ol2_groups").update({"xp": new_xp, "xp_to_next": xp_to_next, "level": level, "gold_pool": new_gold_pool}).eq("id", group_id).execute()
        if xp > 0 or gold > 0:
            client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": action, "xp_awarded": xp, "gold_awarded": gold}).execute()
        bonus_xp = 20 * level if leveled_up else 0  # type: ignore[misc]
        bonus_gold = 30 * level if leveled_up else 0  # type: ignore[misc]
        member_usernames: List[str] = []
        if leveled_up:
            mres = client.table("ol2_group_members").select("username").eq("group_id", group_id).execute()
            member_usernames = [m["username"] for m in (mres.data or [])]  # type: ignore[misc]
            client.table("ol2_group_log").insert({"group_id": group_id, "username": "System", "action": f"Group reached level {level}! All members receive a bonus.", "xp_awarded": bonus_xp, "gold_awarded": bonus_gold}).execute()
        return {"ok": True, "leveled_up": leveled_up, "new_level": level, "group_id": group_id, "bonus_xp": bonus_xp, "bonus_gold": bonus_gold, "members": member_usernames}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False}

def collect_group_gold(username: str) -> Dict[str, Any]:
    def _do():
        client = _get_client()
        mem_res = client.table("ol2_group_members").select("group_id").eq("username", username).execute()
        if not mem_res.data:
            return {"ok": False, "message": "You are not in a group."}
        group_id = mem_res.data[0]["group_id"]  # type: ignore[misc]
        group_res = client.table("ol2_groups").select("gold_pool, leader, name").eq("id", group_id).execute()
        g = group_res.data[0]
        if g["gold_pool"] <= 0:  # type: ignore[misc]
            return {"ok": False, "message": "The group treasury is empty."}
        member_count = client.table("ol2_group_members").select("id", count="exact").eq("group_id", group_id).execute()  # type: ignore[misc]
        count = max(1, member_count.count or 1)
        share = g["gold_pool"] // count  # type: ignore[misc]
        if share < 1:
            return {"ok": False, "message": "Not enough gold to distribute yet."}
        remaining = g["gold_pool"] - share  # type: ignore[misc]
        client.table("ol2_groups").update({"gold_pool": max(0, remaining)}).eq("id", group_id).execute()
        client.table("ol2_group_log").insert({"group_id": group_id, "username": username, "action": f"collected their treasury share ({share} gold).", "xp_awarded": 0, "gold_awarded": share}).execute()
        return {"ok": True, "message": f"You collected {share} gold from the group treasury!", "gold": share, "group_id": group_id}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Failed: {e}"}

def get_group_leaderboard() -> List[Dict[str, Any]]:
    def _do():
        client = _get_client()
        res = client.table("ol2_groups").select("name, leader, level, xp, xp_to_next, gold_pool").order("level", desc=True).order("xp", desc=True).limit(10).execute()
        rows = res.data or []
        enriched = []
        for i, row in enumerate(rows):
            member_count = client.table("ol2_group_members").select("id", count="exact").eq("group_id", row.get("id", "")).execute() if row.get("id") else None  # type: ignore[misc]
            enriched.append({**row, "rank": i + 1, "member_count": 0})  # type: ignore[misc]
        return enriched

    def _do_simple():
        client = _get_client()
        res = client.table("ol2_groups").select("id, name, leader, level, xp, xp_to_next").order("level", desc=True).order("xp", desc=True).limit(10).execute()
        rows = res.data or []
        result = []
        for i, row in enumerate(rows):
            mc = client.table("ol2_group_members").select("username", count="exact").eq("group_id", row["id"]).execute()  # type: ignore[misc]
            result.append({**row, "rank": i + 1, "member_count": mc.count or 0})  # type: ignore[misc]
        return result

    try:
        return _run(_do_simple)
    except Exception:
        return []

def get_player_leaderboard() -> List[Dict[str, Any]]:
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
                gs = row.get("game_state") or {}  # type: ignore[misc]
                if isinstance(gs, str):
                    gs = _json.loads(gs)
                player_data = gs.get("player") or {}  # type: ignore[misc]
                character_class = player_data.get("character_class", "Adventurer")  # type: ignore[misc]
                rank = player_data.get("rank", "")  # type: ignore[misc]
                experience = player_data.get("experience", 0)  # type: ignore[misc]
            except Exception:
                character_class = "Adventurer"
                rank = ""
                experience = 0
            result.append({
                "rank": i + 1,
                "player_name": row.get("player_name", "Unknown"),  # type: ignore[misc]
                "level": row.get("level", 1),  # type: ignore[misc]
                "character_class": character_class,
                "player_rank": rank,
                "experience": experience,
                "current_area": row.get("current_area", ""),  # type: ignore[misc]
            })
        return result

    try:
        return _run(_do)
    except Exception:
        return []

def get_all_activities(exclude_user_id: str = None) -> List[Dict[str, Any]]:  # type: ignore[misc]
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
            gs = row.get("game_state") or {}  # type: ignore[misc]
            if isinstance(gs, str):
                gs = _json.loads(gs)
            player_data = gs.get("player") or {}  # type: ignore[misc]
            activity = player_data.get("activity_status", "exploring")  # type: ignore[misc]
        except Exception:
            activity = "exploring"
        out.append({
            "player_name": row.get("player_name", "Unknown"),  # type: ignore[misc]
            "current_area": row.get("current_area", ""),  # type: ignore[misc]
            "activity_status": activity,
        })
    return out

EMAIL_VERIFICATION_EXPIRY = 86400

def get_user_email(user_id: str) -> Optional[str]:
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
            if row.get("email_verified") and row.get("email"):  # type: ignore[misc]
                return row["email"]  # type: ignore[misc]
        return None

    try:
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return None

def get_pending_email_verification(user_id: str) -> Optional[str]:
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
            created_at = datetime.datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))  # type: ignore[misc]
            age = (datetime.datetime.now(datetime.timezone.utc) - created_at).total_seconds()
            if age > EMAIL_VERIFICATION_EXPIRY:
                return None
        except Exception:
            pass
        return row["email"]  # type: ignore[misc]

    try:
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return None

def request_email_verification(user_id: str, email: str) -> Dict[str, Any]:
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
        if row["verified"]:  # type: ignore[misc]
            return {"ok": False, "message": "This email has already been verified.", "user_id": None}

        try:
            created_at = datetime.datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))  # type: ignore[misc]
            age = (datetime.datetime.now(datetime.timezone.utc) - created_at).total_seconds()
            if age > EMAIL_VERIFICATION_EXPIRY:
                return {"ok": False, "message": "Verification link has expired. Please request a new one.", "user_id": None}
        except Exception:
            pass

        user_id = row["user_id"]  # type: ignore[misc]
        email = row["email"]  # type: ignore[misc]

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

        client.table("ol2_email_verifications").update({"verified": True}).eq("id", row["id"]).execute()  # type: ignore[misc]

        return {"ok": True, "message": "Email verified successfully!", "user_id": user_id}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Verification failed: {e}", "user_id": None}

RESET_TOKEN_EXPIRY_SECONDS = 3600

def create_password_reset_token(email: str) -> Dict[str, Any]:
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
            "user_id": user["id"],  # type: ignore[misc]
            "token": token,
            "used": False,
        }).execute()
        return {"ok": True, "message": "sent", "token": token, "email": email_clean}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Reset request failed: {e}", "token": None, "email": None}

def reset_password_with_token(token: str, new_password: str) -> Dict[str, Any]:
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
        if row["used"]:  # type: ignore[misc]
            return {"ok": False, "message": "This reset link has already been used."}

        created_at_str = row["created_at"]  # type: ignore[misc]
        try:
            created_at = datetime.datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")  # type: ignore[misc]
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
        ).eq("id", row["user_id"]).execute()  # type: ignore[misc]

        client.table("ol2_password_resets").update(
            {"used": True}
        ).eq("id", row["id"]).execute()  # type: ignore[misc]

        return {"ok": True, "message": "Password updated successfully. You can now sign in."}

    try:
        return _run(_do)
    except Exception as e:
        return {"ok": False, "message": f"Password reset failed: {e}"}

_TICK_LOCK_NAME = "world_tick"

def try_acquire_or_renew_world_tick_lock(worker_id: str, ttl_seconds: int = 90) -> bool:
    try:
        client = _get_client()
        now = datetime.datetime.now(datetime.timezone.utc)  # type: ignore[misc]
        expires_at = (now + datetime.timedelta(seconds=ttl_seconds)).isoformat()  # type: ignore[misc]
        now_str = now.isoformat()

        def _do():
            renew_res = (
                client.table("ol2_tick_lock")
                .update({"expires_at": expires_at})
                .eq("lock_name", _TICK_LOCK_NAME)
                .eq("worker_id", worker_id)
                .execute()
            )
            if renew_res.data:
                return True

            client.table("ol2_tick_lock").delete().eq(
                "lock_name", _TICK_LOCK_NAME
            ).lt("expires_at", now_str).execute()

            try:
                ins_res = (
                    client.table("ol2_tick_lock")
                    .insert(
                        {
                            "lock_name": _TICK_LOCK_NAME,
                            "worker_id": worker_id,
                            "expires_at": expires_at,
                        }
                    )
                    .execute()
                )
                return bool(ins_res.data)
            except Exception:
                return False

        return _run(_do)

    except RuntimeError:
        return True
    except Exception:
        return True

def release_world_tick_lock(worker_id: str) -> None:
    try:
        client = _get_client()
        _run(
            lambda: client.table("ol2_tick_lock")
            .delete()
            .eq("lock_name", _TICK_LOCK_NAME)
            .eq("worker_id", worker_id)
            .execute()
        )
    except Exception:
        pass

_ADMIN_OWNER_KEY = "owner"
_ADMIN_OWNER_DEFAULT = "ThePrimordialOne"

def admin_get_owner() -> str:
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_config")
            .select("value")
            .eq("key", _ADMIN_OWNER_KEY)
            .execute()
        )
        if result.data:
            return result.data[0]["value"].lower()  # type: ignore[misc]
        return _ADMIN_OWNER_DEFAULT.lower()
    try:
        return _run(_do)
    except Exception:
        return _ADMIN_OWNER_DEFAULT.lower()

def admin_set_owner(new_owner: str) -> None:
    def _do():
        client = _get_client()
        client.table("ol2_admin_config").upsert(
            {"key": _ADMIN_OWNER_KEY, "value": new_owner.lower()}
        ).execute()
    try:
        _run(_do)
    except Exception:
        pass

def admin_get_mods() -> List[str]:
    def _do():
        client = _get_client()
        result = client.table("ol2_admin_mods").select("username").execute()
        return [r["username"].lower() for r in (result.data or [])]  # type: ignore[misc]
    try:
        return _run(_do)
    except Exception:
        return []

def admin_add_mod(username: str) -> bool:
    uname = username.lower()
    def _do():
        client = _get_client()
        existing = (
            client.table("ol2_admin_mods")
            .select("username")
            .eq("username", uname)
            .execute()
        )
        if existing.data:
            return False
        client.table("ol2_admin_mods").insert({"username": uname}).execute()
        return True
    try:
        return _run(_do)
    except Exception:
        return False

def admin_remove_mod(username: str) -> bool:
    uname = username.lower()
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_mods")
            .delete()
            .eq("username", uname)
            .execute()
        )
        return bool(result.data)
    try:
        return _run(_do)
    except Exception:
        return False

def admin_get_all_mods() -> List[str]:
    owner = admin_get_owner()
    mods = admin_get_mods()
    seen: set = set()
    result: List[str] = []
    for m in ([owner] if owner else []) + mods:
        if m and m not in seen:
            result.append(m)
            seen.add(m)
    return result

def admin_is_banned(username: str) -> bool:
    uname = username.lower()
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_bans")
            .select("username")
            .eq("username", uname)
            .execute()
        )
        return bool(result.data)
    try:
        return _run(_do)
    except Exception:
        return False

def admin_ban(username: str, reason: str, banned_by: str) -> None:
    uname = username.lower()
    def _do():
        client = _get_client()
        client.table("ol2_admin_bans").upsert({
            "username": uname,
            "reason": reason or "No reason given",
            "banned_by": banned_by,
        }).execute()
    try:
        _run(_do)
    except Exception:
        pass

def admin_unban(username: str) -> bool:
    uname = username.lower()
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_bans")
            .delete()
            .eq("username", uname)
            .execute()
        )
        return bool(result.data)
    try:
        return _run(_do)
    except Exception:
        return False

def admin_list_bans() -> List[Dict[str, Any]]:
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_bans")
            .select("username, reason, banned_by, banned_at")
            .execute()
        )
        return result.data or []
    try:
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return []

def admin_is_muted(username: str) -> bool:
    import datetime as _dt
    uname = username.lower()
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_mutes")
            .select("expires_at")
            .eq("username", uname)
            .execute()
        )
        if not result.data:
            return False
        expires_at = result.data[0].get("expires_at")  # type: ignore[misc]
        if expires_at is None:
            return True
        exp = _dt.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))  # type: ignore[misc]
        if _dt.datetime.now(_dt.timezone.utc) > exp:
            client.table("ol2_admin_mutes").delete().eq("username", uname).execute()
            return False
        return True
    try:
        return _run(_do)
    except Exception:
        return False

def admin_mute(username: str, expires_at: Optional[float], reason: str, muted_by: str) -> None:
    import datetime as _dt
    uname = username.lower()
    exp_iso: Optional[str] = None
    if expires_at is not None:
        exp_iso = _dt.datetime.fromtimestamp(expires_at, tz=_dt.timezone.utc).isoformat()
    def _do():
        client = _get_client()
        client.table("ol2_admin_mutes").upsert({
            "username": uname,
            "reason": reason or "No reason given",
            "muted_by": muted_by,
            "expires_at": exp_iso,
        }).execute()
    try:
        _run(_do)
    except Exception:
        pass

def admin_unmute(username: str) -> bool:
    uname = username.lower()
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_mutes")
            .delete()
            .eq("username", uname)
            .execute()
        )
        return bool(result.data)
    try:
        return _run(_do)
    except Exception:
        return False

def admin_list_mutes() -> List[Dict[str, Any]]:
    import datetime as _dt
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_mutes")
            .select("username, reason, muted_by, expires_at")
            .execute()
        )
        now = _dt.datetime.now(_dt.timezone.utc)
        active = []
        for row in (result.data or []):
            exp = row.get("expires_at")  # type: ignore[misc]
            if exp is None:
                active.append(row)
            else:
                exp_dt = _dt.datetime.fromisoformat(exp.replace("Z", "+00:00"))  # type: ignore[misc]
                if exp_dt > now:
                    active.append(row)
        return active
    try:
        return _run(_do)
    except Exception:
        return []

def admin_warn(username: str, reason: str) -> int:
    uname = username.lower()
    def _do():
        client = _get_client()
        client.table("ol2_admin_warns").insert({
            "username": uname,
            "reason": reason or "No reason given",
        }).execute()
        count_res = (
            client.table("ol2_admin_warns")
            .select("id", count="exact")  # type: ignore[misc]
            .eq("username", uname)
            .execute()
        )
        return count_res.count or 1
    try:
        return _run(_do)
    except Exception:
        return 1

def admin_clear_warns(username: str) -> bool:
    uname = username.lower()
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_admin_warns")
            .delete()
            .eq("username", uname)
            .execute()
        )
        return bool(result.data)
    try:
        return _run(_do)
    except Exception:
        return False


# ── MMO Session tracking ──────────────────────────────────────

def session_start(user_id: str, session_token: str,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None) -> None:
    """Record a new session and mark the character as online."""
    def _do():
        client = _get_client()
        # close any stale active sessions for this user
        client.table("ol2_sessions").update({
            "is_active": False,
            "ended_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("user_id", user_id).eq("is_active", True).execute()
        # open new session
        client.table("ol2_sessions").insert({
            "user_id": user_id,
            "session_token": session_token,
            "ip_address": ip_address or "",
            "user_agent": (user_agent or "")[:500],
            "is_active": True,
        }).execute()
        # mark character online and update last_login
        client.table("ol2_characters").update({
            "is_online": True,
            "last_login": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("user_id", user_id).execute()

    try:
        _run(_do)
    except Exception:
        pass


def session_end(user_id: str, session_token: str) -> None:
    """Close session record and mark character offline, updating playtime."""
    def _do():
        client = _get_client()
        now = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now.isoformat()

        # find open session to calculate playtime
        sess_res = (
            client.table("ol2_sessions")
            .select("id, started_at")
            .eq("user_id", user_id)
            .eq("session_token", session_token)
            .eq("is_active", True)
            .execute()
        )
        played_secs = 0
        if sess_res.data:
            row = sess_res.data[0]
            try:
                started = datetime.datetime.fromisoformat(
                    row["started_at"].replace("Z", "+00:00")  # type: ignore[misc]
                )
                played_secs = max(0, int((now - started).total_seconds()))
            except Exception:
                pass
            client.table("ol2_sessions").update({
                "is_active": False,
                "ended_at": now_iso,
            }).eq("id", row["id"]).execute()  # type: ignore[misc]

        # update character: offline + last_logout + accumulated playtime
        char_res = (
            client.table("ol2_characters")
            .select("playtime_seconds")
            .eq("user_id", user_id)
            .execute()
        )
        existing_pt = 0
        if char_res.data:
            existing_pt = char_res.data[0].get("playtime_seconds") or 0  # type: ignore[misc]
        client.table("ol2_characters").update({
            "is_online": False,
            "last_logout": now_iso,
            "playtime_seconds": int(existing_pt) + played_secs,  # type: ignore[arg-type]
        }).eq("user_id", user_id).execute()

    try:
        _run(_do)
    except Exception:
        pass


def session_heartbeat(user_id: str, session_token: str) -> None:
    """Update last_seen_at for an active session (called on autosave heartbeat)."""
    def _do():
        client = _get_client()
        client.table("ol2_sessions").update({
            "last_seen_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("user_id", user_id).eq("session_token", session_token).eq("is_active", True).execute()

    try:
        _run(_do)
    except Exception:
        pass


def get_online_players() -> List[Dict[str, Any]]:
    """Return a lightweight list of currently-online characters."""
    def _do():
        client = _get_client()
        result = (
            client.table("ol2_characters")
            .select("player_name, level, character_class, current_area, last_login")
            .eq("is_online", True)
            .order("last_login", desc=True)
            .limit(100)
            .execute()
        )
        return result.data or []

    try:
        return _run(_do)  # type: ignore[misc]
    except Exception:
        return []
