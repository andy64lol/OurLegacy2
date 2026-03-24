import sys as _sys

# Patch the standard library with gevent when running directly (python app.py).
# When running under gunicorn, the gevent worker handles patching via post_fork
# (see gunicorn.conf.py). Patching in the gunicorn master process causes the
# "no running event loop" crash when workers are forked.
if "gunicorn" not in _sys.modules:
    from gevent import monkey as _monkey
    _monkey.patch_all()

"""
Our Legacy 2 - Flask Web Interface
Medieval fantasy RPG playable in the browser.
"""

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    make_response,
    send_from_directory,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit as socketio_emit, disconnect as socketio_disconnect
import json
import random
import os
import time as _time_module
import uuid
import urllib.request as _urllib_request
import urllib.error as _urllib_error
from typing import Any

from utilities.dice import Dice
from utilities.stats import (
    ensure_attributes,
    spend_attribute_point,
    get_attribute_summary,
)
from utilities.spellcasting import get_available_spells, cast_spell
from utilities.crafting import (
    get_recipes,
    craft_item,
    check_recipe_craftable,
)
from utilities.dungeons import (
    get_available_dungeons,
    generate_dungeon_rooms,
    process_chest_room,
    process_trap_chest_room,
    process_empty_room,
    process_battle_room,
    process_shrine_room,
    process_ambush_room,
    process_question_room,
    answer_question,
    answer_multi_choice,
    complete_dungeon,
    _pick_multi_choice,
)
from flask_session import Session
from utilities.market import get_market_api
from utilities.save_load import (
    save_game,
    list_saves,
    load_save,
    encrypt_save,
    decrypt_save,
)
from utilities.supabase_db import (
    register_user,
    login_user,
    cloud_save,
    cloud_load,
    get_cloud_save_meta,
    send_chat_message,
    get_chat_history,
    censor_text,
    contains_profanity,
    send_friend_request,
    respond_friend_request,
    remove_friend,
    get_friends,
    send_dm,
    get_dm_conversation,
    mark_dms_read,
    get_unread_dm_counts,
    block_user,
    unblock_user,
    is_blocked,
    get_blocked_by_me,
    character_autosave,
    character_autoload,
    character_delete,
    create_group,
    join_group,
    leave_group,
    kick_group_member,
    get_user_group,
    contribute_to_group,
    collect_group_gold,
    get_group_leaderboard,
    get_player_leaderboard,
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.environ.get("SECRET_KEY", "ol2-default-dev-key-change-in-prod")

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), ".flask_sessions")
app.config["SESSION_PERMANENT"] = False
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent", manage_session=False)

# Online users: {sid: username}  (in-memory, single worker)
_chat_online: dict = {}
_chat_cooldowns: dict = {}  # {username: last_sent_timestamp}
CHAT_COOLDOWN_SECS = 10
CHAT_MAX_LEN = 200

_dm_cooldowns: dict = {}      # {username: last_dm_timestamp}
_fr_cooldowns: dict = {}      # {username: [timestamps]} — friend request rate limiting
DM_COOLDOWN_SECS = 2
DM_MAX_LEN = 500
FR_MAX_PER_MINUTE = 5

# ─── World events feed (online only) ─────────────────────────────────────────
# A rolling log of recent world events visible to online players.
_world_events: list = []
_WORLD_EVENTS_MAX = 40


def push_world_event(text: str) -> None:
    """Append a timestamped event to the global world feed, trimming old ones."""
    import time as _time
    _world_events.append({"t": int(_time.time()), "msg": text})
    if len(_world_events) > _WORLD_EVENTS_MAX:
        del _world_events[: len(_world_events) - _WORLD_EVENTS_MAX]


# ─── In-memory trade state ────────────────────────────────────────────────────
# trade_id → {id, player_a, player_b, offer_a, offer_b, confirmed_a, confirmed_b,
#              status, applied_a, applied_b}
_active_trades: dict = {}
TRADE_MAX_ITEMS = 10
TRADE_MAX_GOLD = 9_999_999
TRADE_TIMEOUT_SECS = 300   # 5 min inactivity → auto-cancel
_bg_started = False


@app.context_processor
def _inject_chat_globals():
    return {"online_username": session.get("online_username")}


# ─── SocketIO Chat Events ──────────────────────────────────────────────────────

@socketio.on("connect")
def _on_chat_connect():
    username = session.get("online_username")
    if not username:
        socketio_disconnect()
        return
    _chat_online[request.sid] = username
    socketio_emit("online_users", sorted(set(_chat_online.values())), broadcast=True)
    history = get_chat_history(60)
    socketio_emit("chat_history", history)


@socketio.on("disconnect")
def _on_chat_disconnect():
    username = _chat_online.pop(request.sid, None)
    socketio_emit("online_users", sorted(set(_chat_online.values())), broadcast=True)
    if username:
        for tid, trade in list(_active_trades.items()):
            if trade["status"] in ("pending", "active") and username in (trade["player_a"], trade["player_b"]):
                other = trade["player_b"] if username == trade["player_a"] else trade["player_a"]
                other_sids = [s for s, u in _chat_online.items() if u == other]
                for s in other_sids:
                    socketio.emit("trade_cancelled", {"message": f"{username} disconnected. Trade cancelled."}, to=s)
                _active_trades.pop(tid, None)


@socketio.on("chat_send")
def _on_chat_send(data):
    username = session.get("online_username")
    if not username:
        socketio_emit("chat_error", {"message": "You must be logged in to chat."})
        return
    raw = str(data.get("message", "")).strip()
    if not raw:
        return
    if len(raw) > CHAT_MAX_LEN:
        socketio_emit("chat_error", {"message": f"Message too long (max {CHAT_MAX_LEN} chars)."})
        return
    now = _time_module.time()
    last = _chat_cooldowns.get(username, 0)
    remaining = int(CHAT_COOLDOWN_SECS - (now - last))
    if remaining > 0:
        socketio_emit("chat_error", {"message": f"Please wait {remaining}s before sending again."})
        return
    censored = censor_text(raw)
    _chat_cooldowns[username] = now
    result = send_chat_message(username, censored)
    if result["ok"]:
        row = result["row"]
        socketio_emit("chat_message", {
            "username": username,
            "message": censored,
            "created_at": row.get("created_at", ""),
        }, broadcast=True)
    else:
        socketio_emit("chat_error", {"message": "Failed to send message. Try again."})


# ─── SocketIO Trade Events ─────────────────────────────────────────────────────

def _get_trade_for_user(trade_id: str, username: str):
    """Return trade dict if trade_id exists and username is a participant."""
    trade = _active_trades.get(trade_id)
    if not trade:
        return None
    if username not in (trade["player_a"], trade["player_b"]):
        return None
    return trade


def _trade_payload(trade: dict, viewer: str) -> dict:
    """Build the trade_update payload for a viewer."""
    other = trade["player_b"] if viewer == trade["player_a"] else trade["player_a"]
    my_offer = trade["offer_a"] if viewer == trade["player_a"] else trade["offer_b"]
    their_offer = trade["offer_b"] if viewer == trade["player_a"] else trade["offer_a"]
    my_confirmed = trade["confirmed_a"] if viewer == trade["player_a"] else trade["confirmed_b"]
    their_confirmed = trade["confirmed_b"] if viewer == trade["player_a"] else trade["confirmed_a"]
    return {
        "trade_id": trade["id"],
        "other": other,
        "my_offer": my_offer,
        "their_offer": their_offer,
        "my_confirmed": my_confirmed,
        "their_confirmed": their_confirmed,
        "status": trade["status"],
    }


def _emit_trade_update(trade: dict):
    """Emit trade_update to both participants."""
    a_sids = [s for s, u in _chat_online.items() if u == trade["player_a"]]
    b_sids = [s for s, u in _chat_online.items() if u == trade["player_b"]]
    for s in a_sids:
        socketio.emit("trade_update", _trade_payload(trade, trade["player_a"]), to=s)
    for s in b_sids:
        socketio.emit("trade_update", _trade_payload(trade, trade["player_b"]), to=s)


@socketio.on("trade_request")
def _on_trade_request(data):
    username = session.get("online_username")
    if not username:
        return
    target = str(data.get("target", "")).strip().lower()
    if not target or target == username:
        socketio_emit("trade_error", {"message": "Invalid trade target."})
        return
    target_sids = [s for s, u in _chat_online.items() if u == target]
    if not target_sids:
        socketio_emit("trade_error", {"message": f"{target} is not online."})
        return
    for t in _active_trades.values():
        if t["status"] in ("pending", "active") and username in (t["player_a"], t["player_b"]):
            socketio_emit("trade_error", {"message": "You already have an active trade."})
            return
        if t["status"] in ("pending", "active") and target in (t["player_a"], t["player_b"]):
            socketio_emit("trade_error", {"message": f"{target} is already in a trade."})
            return
    trade_id = str(uuid.uuid4())[:8]
    _active_trades[trade_id] = {
        "id": trade_id,
        "player_a": username,
        "player_b": target,
        "offer_a": {"items": [], "gold": 0},
        "offer_b": {"items": [], "gold": 0},
        "confirmed_a": False,
        "confirmed_b": False,
        "status": "pending",
        "applied_a": False,
        "applied_b": False,
        "created_at": _time_module.time(),
        "last_activity": _time_module.time(),
    }
    for s in target_sids:
        socketio.emit("trade_invite", {"trade_id": trade_id, "from": username}, to=s)
    socketio_emit("trade_invite_sent", {"trade_id": trade_id, "to": target})


@socketio.on("trade_accept")
def _on_trade_accept(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "pending":
        socketio_emit("trade_error", {"message": "Trade not found or already started."})
        return
    if trade["player_b"] != username:
        socketio_emit("trade_error", {"message": "Only the recipient can accept."})
        return
    trade["status"] = "active"
    trade["last_activity"] = _time_module.time()
    _emit_trade_update(trade)


@socketio.on("trade_decline")
def _on_trade_decline(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    trade = _get_trade_for_user(trade_id, username)
    if not trade:
        return
    other = trade["player_b"] if username == trade["player_a"] else trade["player_a"]
    other_sids = [s for s, u in _chat_online.items() if u == other]
    for s in other_sids:
        socketio.emit("trade_cancelled", {"message": f"{username} declined the trade."}, to=s)
    socketio_emit("trade_cancelled", {"message": "You declined the trade."})
    _active_trades.pop(trade_id, None)


@socketio.on("trade_add_item")
def _on_trade_add_item(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    item_name = str(data.get("item_name", "")).strip()
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "active":
        socketio_emit("trade_error", {"message": "Trade not active."})
        return
    my_offer_key = "offer_a" if username == trade["player_a"] else "offer_b"
    my_confirmed_key = "confirmed_a" if username == trade["player_a"] else "confirmed_b"
    if trade[my_confirmed_key]:
        socketio_emit("trade_error", {"message": "Unconfirm your offer first to make changes."})
        return
    if len(trade[my_offer_key]["items"]) >= TRADE_MAX_ITEMS:
        socketio_emit("trade_error", {"message": f"Maximum {TRADE_MAX_ITEMS} items per trade."})
        return
    player = session.get("player")
    if not player:
        socketio_emit("trade_error", {"message": "No active character."})
        return
    inventory = list(player.get("inventory", []))
    already_offered = list(trade[my_offer_key]["items"])
    for offered in already_offered:
        if offered in inventory:
            inventory.remove(offered)
    if item_name not in inventory:
        socketio_emit("trade_error", {"message": f"You don't have '{item_name}'."})
        return
    trade[my_offer_key]["items"].append(item_name)
    trade["last_activity"] = _time_module.time()
    _emit_trade_update(trade)


@socketio.on("trade_remove_item")
def _on_trade_remove_item(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    item_name = str(data.get("item_name", "")).strip()
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "active":
        return
    my_offer_key = "offer_a" if username == trade["player_a"] else "offer_b"
    my_confirmed_key = "confirmed_a" if username == trade["player_a"] else "confirmed_b"
    if trade[my_confirmed_key]:
        socketio_emit("trade_error", {"message": "Unconfirm your offer first to make changes."})
        return
    items = trade[my_offer_key]["items"]
    if item_name in items:
        items.remove(item_name)
    trade["last_activity"] = _time_module.time()
    _emit_trade_update(trade)


@socketio.on("trade_set_gold")
def _on_trade_set_gold(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    try:
        amount = max(0, min(int(data.get("gold", 0)), TRADE_MAX_GOLD))
    except (ValueError, TypeError):
        amount = 0
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "active":
        return
    my_offer_key = "offer_a" if username == trade["player_a"] else "offer_b"
    my_confirmed_key = "confirmed_a" if username == trade["player_a"] else "confirmed_b"
    if trade[my_confirmed_key]:
        socketio_emit("trade_error", {"message": "Unconfirm your offer first to make changes."})
        return
    player = session.get("player")
    if not player:
        return
    already_offered_items = trade[my_offer_key]["items"]
    if amount > player.get("gold", 0):
        amount = player.get("gold", 0)
    trade[my_offer_key]["gold"] = amount
    trade["last_activity"] = _time_module.time()
    _emit_trade_update(trade)


@socketio.on("trade_confirm")
def _on_trade_confirm(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    confirmed = bool(data.get("confirmed", True))
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "active":
        return
    my_confirmed_key = "confirmed_a" if username == trade["player_a"] else "confirmed_b"
    trade[my_confirmed_key] = confirmed
    trade["last_activity"] = _time_module.time()
    if trade["confirmed_a"] and trade["confirmed_b"]:
        trade["status"] = "approved"
        a_sids = [s for s, u in _chat_online.items() if u == trade["player_a"]]
        b_sids = [s for s, u in _chat_online.items() if u == trade["player_b"]]
        for s in a_sids:
            socketio.emit("trade_approved", {
                "trade_id": trade_id,
                "receive_items": trade["offer_b"]["items"],
                "receive_gold": trade["offer_b"]["gold"],
                "give_items": trade["offer_a"]["items"],
                "give_gold": trade["offer_a"]["gold"],
            }, to=s)
        for s in b_sids:
            socketio.emit("trade_approved", {
                "trade_id": trade_id,
                "receive_items": trade["offer_a"]["items"],
                "receive_gold": trade["offer_a"]["gold"],
                "give_items": trade["offer_b"]["items"],
                "give_gold": trade["offer_b"]["gold"],
            }, to=s)
    else:
        _emit_trade_update(trade)


@socketio.on("trade_cancel")
def _on_trade_cancel(data):
    username = session.get("online_username")
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] not in ("pending", "active"):
        return
    other = trade["player_b"] if username == trade["player_a"] else trade["player_a"]
    other_sids = [s for s, u in _chat_online.items() if u == other]
    for s in other_sids:
        socketio.emit("trade_cancelled", {"message": f"{username} cancelled the trade."}, to=s)
    socketio_emit("trade_cancelled", {"message": "You cancelled the trade."})
    _active_trades.pop(trade_id, None)


# ─── Background World Tick ─────────────────────────────────────────────────────

def _expire_stale_trades():
    """Cancel trades that have been inactive beyond TRADE_TIMEOUT_SECS."""
    now = _time_module.time()
    for tid, trade in list(_active_trades.items()):
        if trade["status"] not in ("pending", "active"):
            continue
        last = trade.get("last_activity", trade.get("created_at", now))
        if now - last > TRADE_TIMEOUT_SECS:
            for p in (trade["player_a"], trade["player_b"]):
                for s, u in list(_chat_online.items()):
                    if u == p:
                        socketio.emit("trade_cancelled", {
                            "message": "Trade expired due to inactivity (5 min timeout)."
                        }, to=s)
            _active_trades.pop(tid, None)


def _world_tick():
    """Background greenlet: fires every 30 s for housekeeping tasks."""
    while True:
        socketio.sleep(30)
        try:
            _expire_stale_trades()
        except Exception:
            pass


@app.before_request
def _ensure_background_tasks():
    global _bg_started
    if not _bg_started:
        _bg_started = True
        socketio.start_background_task(_world_tick)


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "ok": False,
        "message": "Too many attempts. Please wait a moment and try again.",
    }), 429


dice = Dice()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(filename) -> dict[str, Any]:
    try:
        with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError, KeyError):
        return {}


def load_json_list(filename) -> list:
    try:
        with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, ValueError, KeyError):
        return []


GAME_DATA: dict[str, Any] = {
    "classes": load_json("classes.json"),
    "races": load_json("races.json"),
    "areas": load_json("areas.json"),
    "enemies": load_json("enemies.json"),
    "items": load_json("items.json"),
    "missions": load_json("missions.json"),
    "bosses": load_json("bosses.json"),
    "spells": load_json("spells.json"),
    "shops": load_json("shops.json"),
    "companions": load_json("companions.json"),
    "crafting": load_json("crafting.json"),
    "housing": load_json("housing.json"),
    "farming": load_json("farming.json"),
    "pets": load_json("pets.json"),
    "dungeons": load_json("dungeons.json"),
    "weekly_challenges": load_json("weekly_challenges.json").get("challenges", []),
    "weather": load_json("weather.json"),
    "times": load_json("times.json"),
    "dialogues": load_json("dialogues.json"),
    "cutscenes": load_json("cutscenes.json"),
    "books": load_json("books.json"),
    "splash_texts": load_json_list("splash_text.json"),
    "events": load_json("events.json").get("events", []),
    "effects": load_json("effects.json"),
}

GAME_VERSION = "2.5.1"

BUILDING_TYPES = {
    "house": {"label": "House", "slots": 3},
    "decoration": {"label": "Decoration", "slots": 10},
    "fencing": {"label": "Fencing", "slots": 1},
    "garden": {"label": "Garden", "slots": 3},
    "farm": {"label": "Farm", "slots": 2},
    "training_place": {"label": "Training Place", "slots": 3},
}

EQUIPPABLE_TYPES = {"weapon", "armor", "offhand", "accessory"}

# Crafting materials grouped by area difficulty tier
MATERIALS_BY_TIER = {
    1: ["Iron Ore", "Herbs", "Goblin Ears", "Wolf Fangs"],
    2: ["Coal", "Mana Herbs", "Orc Teeth", "Crystal Shards"],
    3: ["Steel Ingot", "Dark Crystals", "Fire Gems", "Venom Sacs"],
    4: ["Gold Nugget", "Spring Water", "Phoenix Feathers", "Dragon Scales"],
    5: ["Dragon Scales", "Phoenix Feathers", "Ancient Relics"],
}

TIME_PERIODS = [
    "Dawn",
    "Morning",
    "Noon",
    "Afternoon",
    "Dusk",
    "Evening",
    "Night",
    "Midnight",
]
TIME_ICONS = {
    "Dawn": "",
    "Morning": "",
    "Noon": "",
    "Afternoon": "",
    "Dusk": "",
    "Evening": "",
    "Night": "",
    "Midnight": "",
}

# Training options at Your Land
TRAINING_OPTIONS = {
    "attack": {"label": "Attack Training", "stat": "attack", "cost": 80, "gain": 1},
    "defense": {"label": "Defense Training", "stat": "defense", "cost": 80, "gain": 1},
    "speed": {"label": "Speed Training", "stat": "speed", "cost": 80, "gain": 1},
    "max_hp": {
        "label": "Endurance Training",
        "stat": "max_hp",
        "cost": 100,
        "gain": 10,
    },
    "max_mp": {
        "label": "Meditation Training",
        "stat": "max_mp",
        "cost": 100,
        "gain": 5,
    },
}

# Boss challenge cooldown in seconds (8 hours)
BOSS_CHALLENGE_COOLDOWN = 8 * 3600


# ─── Helpers ────────────────────────────────────────────────────────────────


def get_player() -> dict[str, Any] | None:
    return session.get("player")


def save_player(player: dict[str, Any]) -> None:
    # Keep visited_areas in sync inside the player dict so it persists with the character
    player["visited_areas"] = list(set(
        player.get("visited_areas", []) + session.get("visited_areas", [])
    ))
    session["player"] = player
    session.modified = True


# ─── Persistent character helpers (Phase 1 MMO) ──────────────────────────────

def _build_game_state() -> dict[str, Any]:
    """Bundle all persistent session data into a dict for Supabase storage."""
    player = session.get("player")
    if not player:
        return {}
    from utilities.stats import ensure_attributes
    ensure_attributes(player)
    return {
        "player": player,
        "current_area": session.get("current_area", "starting_village"),
        "completed_missions": session.get("completed_missions", []),
        "visited_areas": session.get("visited_areas", []),
        "quest_progress": session.get("quest_progress", {}),
        "seen_cutscenes": session.get("seen_cutscenes", []),
        "messages": session.get("messages", [])[-20:],
        "diary": session.get("diary", []),
        "npc_unlocked_quests": session.get("npc_unlocked_quests", []),
        "save_version": "7.1",
    }


def _apply_game_state(data: dict[str, Any]) -> None:
    """Apply a loaded game state dict to the current session."""
    player = data.get("player")
    if not player:
        return
    _ensure_equipment_slots(player)
    player.setdefault("game_ticks", 0)
    player.setdefault("weekly_challenges_progress", {})
    player.setdefault("boss_cooldowns", {})
    player.setdefault("race", "Descendants from another world")
    from utilities.stats import ensure_attributes
    ensure_attributes(player)
    session["player"] = player
    session["current_area"] = data.get("current_area", "starting_village")
    session["completed_missions"] = data.get("completed_missions", [])
    _va_top = data.get("visited_areas", [])
    _va_player = (data.get("player") or {}).get("visited_areas", [])
    session["visited_areas"] = list(set(_va_top + _va_player)) or [session["current_area"]]
    session["quest_progress"] = data.get("quest_progress", {})
    session["seen_cutscenes"] = data.get("seen_cutscenes", [])
    session["messages"] = data.get("messages", [])
    session["diary"] = data.get("diary", [])
    session["npc_unlocked_quests"] = data.get("npc_unlocked_quests", [])
    session.modified = True


def _diary_append(text: str, color: str = "var(--text-light)") -> None:
    """Append an entry to the diary (activity log) without showing it in the message feed."""
    diary = session.get("diary", [])
    diary.append({"text": text, "color": color})
    if len(diary) > 500:
        diary = diary[-500:]
    session["diary"] = diary
    session.modified = True


_AUTOSAVE_DIARY_INTERVAL = 300  # seconds between autosave diary entries


def _autosave() -> None:
    """
    Fire-and-forget autosave to Supabase for logged-in users.
    Silently skips if the user isn't logged in or has no active character.
    Also logs a diary entry at most once every 5 minutes to avoid flooding.
    """
    user_id = session.get("online_user_id")
    if not user_id:
        return
    state = _build_game_state()
    if not state:
        return
    try:
        character_autosave(user_id, state)
    except Exception:
        pass

    # Log to activities (diary) with throttling so it doesn't flood
    now = _time_module.time()
    last_log = session.get("_last_autosave_diary_log", 0)
    if now - last_log >= _AUTOSAVE_DIARY_INTERVAL:
        _diary_append("Progress autosaved.", color="var(--muted)")
        session["_last_autosave_diary_log"] = now
        session.modified = True


def _set_activity(player: dict, status: str) -> None:
    """Store a short activity string on the player dict (persisted in autosave)."""
    player["activity_status"] = status


def _group_contribute(xp_gained: int, gold_gained: int, action: str) -> None:
    """
    Contribute a share of XP/gold to the player's group (if they're in one).
    Silently skips for offline or non-grouped players.
    Broadcasts group_level_up to all online group members on level-up.
    """
    username = session.get("online_username")
    if not username:
        return
    xp_share = max(1, int(xp_gained * 0.10)) if xp_gained > 0 else 0
    gold_share = max(1, int(gold_gained * 0.05)) if gold_gained > 0 else 0
    if xp_share <= 0 and gold_share <= 0:
        return
    try:
        result = contribute_to_group(username, xp_share, gold_share, action)
        if result.get("ok") and result.get("leveled_up"):
            new_level = result["new_level"]
            bonus_xp = result.get("bonus_xp", 0)
            bonus_gold = result.get("bonus_gold", 0)
            members = result.get("members", [])
            payload = {"level": new_level, "bonus_xp": bonus_xp, "bonus_gold": bonus_gold}
            for member in members:
                for sid in [s for s, u in _chat_online.items() if u == member]:
                    socketio.emit("group_level_up", payload, to=sid)
    except Exception:
        pass


def get_messages():
    return session.get("messages", [])


def add_message(text, color="var(--text-light)"):
    msgs = session.get("messages", [])
    msgs.append({"text": text, "color": color})
    if len(msgs) > 80:
        msgs = msgs[-80:]
    session["messages"] = msgs

    diary = session.get("diary", [])
    diary.append({"text": text, "color": color})
    if len(diary) > 500:
        diary = diary[-500:]
    session["diary"] = diary

    session.modified = True


def get_rank(level):
    if level < 5:
        return "F-Tier Adventurer"
    elif level < 10:
        return "E-Tier Adventurer"
    elif level < 15:
        return "D-Tier Adventurer"
    elif level < 20:
        return "C-Tier Adventurer"
    elif level < 30:
        return "B-Tier Adventurer"
    elif level < 40:
        return "A-Tier Adventurer"
    elif level < 50:
        return "S-Tier Adventurer"
    else:
        return "Legendary Hero"


def gain_experience(player, amount):
    player["experience"] += amount
    leveled = False
    while player["experience"] >= player["experience_to_next"]:
        player["experience"] -= player["experience_to_next"]
        player["level"] += 1
        player["experience_to_next"] = int(player["experience_to_next"] * 1.5)
        b = player.get("level_up_bonuses", {})
        player["max_hp"] += b.get("hp", 10)
        player["max_mp"] += b.get("mp", 2)
        player["attack"] += b.get("attack", 2)
        player["defense"] += b.get("defense", 1)
        player["speed"] += b.get("speed", 1)
        player["hp"] = player["max_hp"]
        player["mp"] = player["max_mp"]
        player["rank"] = get_rank(player["level"])
        leveled = True
    if leveled:
        update_level_challenges(player)
    return leveled


# ─── Timed Events ─────────────────────────────────────────────────────────────

import datetime as _dt


def check_and_award_events(player):
    """Check all active events and award unclaimed rewards to the player.

    Returns True if at least one event reward was awarded this call.
    """
    events = GAME_DATA.get("events", [])
    if not events:
        return False

    today_str = _dt.date.today().isoformat()
    claimed = player.setdefault("claimed_events", [])
    awarded_any = False

    for event in events:
        event_id = event.get("id", "")
        if not event_id or event_id in claimed:
            continue

        # ── Date window check ──────────────────────────────────────────────
        if "date" in event:
            if today_str != event["date"]:
                continue
        elif "start" in event and "end" in event:
            if not (event["start"] <= today_str <= event["end"]):
                continue
        else:
            continue

        # ── Condition check ────────────────────────────────────────────────
        condition = event.get("condition", {})
        ctype = condition.get("type", "none")

        if ctype == "boss_kills":
            required = condition.get("count", 1)
            if player.get("total_bosses_defeated", 0) < required:
                continue
        elif ctype == "first_login_on_date":
            pass  # date already matched above; just being present counts
        # ctype == "none" always passes

        # ── Award reward ───────────────────────────────────────────────────
        rtype = event.get("reward_type", "")
        msg = event.get("reward_message", f"You received a reward from the event '{event.get('name', '')}'!")

        if rtype == "item":
            item_name = event.get("reward_item", "")
            if item_name:
                player["inventory"].append(item_name)
        elif rtype == "gold":
            amount = int(event.get("reward_amount", 0))
            player["gold"] = player.get("gold", 0) + amount

        claimed.append(event_id)
        add_message(f"[EVENT] {event.get('name', 'Event')}: {msg}", "var(--gold)")
        awarded_any = True

    return awarded_any


def advance_crops(player):
    crops = player.get("crops", {})
    for _slot_id, crop_info in crops.items():
        if not crop_info.get("ready", False):
            crop_info["turns"] = crop_info.get("turns", 0) + 1
            growth_time = crop_info.get("growth_time", 5)
            if crop_info["turns"] >= growth_time:
                crop_info["ready"] = True


# ─── Time of Day ──────────────────────────────────────────────────────────────


def get_game_time(player=None):
    """Return current time period name based on real London local time."""
    import datetime as _dt2
    import zoneinfo
    london_now = _dt2.datetime.now(_dt2.timezone.utc).astimezone(
        zoneinfo.ZoneInfo("Europe/London")
    )
    hour = london_now.hour
    if 5 <= hour < 7:
        return "Dawn"
    elif 7 <= hour < 10:
        return "Morning"
    elif 10 <= hour < 13:
        return "Noon"
    elif 13 <= hour < 16:
        return "Afternoon"
    elif 16 <= hour < 19:
        return "Dusk"
    elif 19 <= hour < 22:
        return "Evening"
    elif 22 <= hour <= 23:
        return "Night"
    else:
        return "Midnight"


def advance_game_time(player):
    """Increment game ticks by 1."""
    player["game_ticks"] = player.get("game_ticks", 0) + 1


def apply_regen_effects(player):
    """Tick down any active regen effects (e.g. from Grand Feast Platter)."""
    effects = player.get("regen_effects", [])
    if not effects:
        return
    remaining = []
    for eff in effects:
        if eff.get("turns_remaining", 0) <= 0:
            continue
        hp_tick = int(eff.get("hp_per_turn", 0))
        mp_tick = int(eff.get("mp_per_turn", 0))
        if hp_tick:
            player["hp"] = min(player["max_hp"], player["hp"] + hp_tick)
        if mp_tick:
            player["mp"] = min(player["max_mp"], player["mp"] + mp_tick)
        eff["turns_remaining"] -= 1
        if eff["turns_remaining"] > 0:
            remaining.append(eff)
        else:
            add_message(
                f"The {eff.get('source', 'regeneration')} effect has faded.", "var(--text-dim)"
            )
    player["regen_effects"] = remaining


# ─── Weather ──────────────────────────────────────────────────────────────────

# WMO weather interpretation codes → game weather types
_WMO_TO_GAME_WEATHER = {
    0: "sunny", 1: "sunny", 2: "sunny", 3: "sunny",
    45: "rainy", 48: "rainy",
    51: "rainy", 53: "rainy", 55: "rainy",
    56: "rainy", 57: "rainy",
    61: "rainy", 63: "rainy", 65: "rainy",
    66: "rainy", 67: "rainy",
    71: "snowy", 73: "snowy", 75: "snowy", 77: "snowy",
    80: "rainy", 81: "rainy", 82: "rainy",
    85: "snowy", 86: "snowy",
    95: "stormy", 96: "stormy", 99: "stormy",
}

_real_weather_cache: dict = {"weather": "sunny", "fetched_at": 0.0}
_WEATHER_CACHE_TTL = 2 * 3600  # 2 IRL hours = 1 game day


def get_real_weather(area_name: str = "") -> str:
    """Return real London weather from Open-Meteo, cached for 2 hours.
    Underground/subterranean areas always return 'null'."""
    name_lower = area_name.lower()
    if "tomb" in name_lower or "cavern" in name_lower or "underground" in name_lower:
        return "null"

    now = _time_module.time()
    if now - _real_weather_cache["fetched_at"] >= _WEATHER_CACHE_TTL:
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=51.5074&longitude=-0.1278"
                "&current_weather=true"
                "&timezone=Europe%2FLondon"
            )
            with _urllib_request.urlopen(url, timeout=5) as resp:
                payload = json.loads(resp.read().decode())
            wmo_code = int(payload["current_weather"]["weathercode"])
            mapped = _WMO_TO_GAME_WEATHER.get(wmo_code, "sunny")
            _real_weather_cache["weather"] = mapped
            _real_weather_cache["fetched_at"] = now
        except Exception:
            pass  # Keep cached value on failure

    return _real_weather_cache["weather"]


def get_weather_bonuses(weather_key):
    """Return exp and gold bonus multipliers for given weather."""
    weather_def = GAME_DATA["weather"].get(weather_key, {})
    bonuses = weather_def.get("bonuses", {})
    return bonuses.get("exp_bonus", 0.0), bonuses.get("gold_bonus", 0.0)


# ─── Weekly Challenges ────────────────────────────────────────────────────────


def update_weekly_challenge(player, event_type, amount=1):
    """Track weekly challenge progress for the given event type."""
    ch_prog = player.setdefault("weekly_challenges_progress", {})
    for ch in GAME_DATA["weekly_challenges"]:
        ch_id = ch.get("id", "")
        if not ch_id:
            continue
        prog = ch_prog.get(ch_id, {})
        if prog.get("claimed"):
            continue
        if ch.get("type") == event_type:
            entry = ch_prog.setdefault(ch_id, {})
            entry["count"] = entry.get("count", 0) + amount


def update_level_challenges(player):
    """Update level_reach challenges to match current level."""
    ch_prog = player.setdefault("weekly_challenges_progress", {})
    for ch in GAME_DATA["weekly_challenges"]:
        if ch.get("type") == "level_reach":
            ch_id = ch.get("id", "")
            if not ch_id:
                continue
            prog = ch_prog.get(ch_id, {})
            if prog.get("claimed"):
                continue
            entry = ch_prog.setdefault(ch_id, {})
            entry["count"] = max(entry.get("count", 0), player.get("level", 1))


def update_gold_challenges(player):
    """Update gold_reach challenges to match current gold."""
    ch_prog = player.setdefault("weekly_challenges_progress", {})
    for ch in GAME_DATA["weekly_challenges"]:
        if ch.get("type") == "gold_reach":
            ch_id = ch.get("id", "")
            if not ch_id:
                continue
            prog = ch_prog.get(ch_id, {})
            if prog.get("claimed"):
                continue
            entry = ch_prog.setdefault(ch_id, {})
            entry["count"] = max(entry.get("count", 0), player.get("gold", 0))


def build_challenges_display(player):
    """Build challenge display list for template."""
    update_gold_challenges(player)
    ch_prog = player.get("weekly_challenges_progress", {})
    result = []
    for ch in GAME_DATA["weekly_challenges"]:
        ch_id = ch.get("id", "")
        if not ch_id:
            continue
        prog = ch_prog.get(ch_id, {})
        count = prog.get("count", 0)
        target = ch.get("target", 0)
        claimed = prog.get("claimed", False)
        result.append(
            {
                "id": ch_id,
                "name": ch.get("name", ch_id),
                "description": ch.get("description", ""),
                "type": ch.get("type", ""),
                "count": min(count, target),
                "target": target,
                "claimed": claimed,
                "ready": not claimed and count >= target,
                "reward_exp": ch.get("reward_exp", 0),
                "reward_gold": ch.get("reward_gold", 0),
            }
        )
    return result


# ─── Boss Dialogue ────────────────────────────────────────────────────────────


def get_boss_dialogue(boss_key, timing):
    """Return boss dialogue text for 'start' or 'defeat'."""
    return GAME_DATA["dialogues"].get(f"{boss_key}.boss.{timing}", "")


# ─── Boss Battle Mechanics ────────────────────────────────────────────────────


def get_boss_phase(phases, hp_pct):
    """
    Return (phase_index, phase_dict) for the given HP percentage.
    Phases are ordered so that the highest threshold applies first (full health),
    and later phases kick in as HP drops.
    """
    if not phases:
        return 0, {}
    sorted_desc = sorted(phases, key=lambda p: -p.get("hp_threshold", 1.0))
    for i, phase in enumerate(sorted_desc):
        if hp_pct >= phase.get("hp_threshold", 1.0):
            return i, phase
    return len(sorted_desc) - 1, sorted_desc[-1]


def _enemy_take_turn(enemy, player, player_effects, log):
    """Dispatch enemy turn — boss uses full mechanic, regular enemy does plain attack."""
    if enemy.get("is_boss"):
        boss_take_turn(enemy, player, player_effects, log)
    else:
        # Evasion check: player armor evasion_bonus + attr_evasion
        evasion_pct = player.get("attr_evasion", 0) / 100.0
        dodge = player.get("dodge_chance", 0.0) + evasion_pct
        if dodge > 0 and random.random() < dodge:
            log.append(f"You evade the {enemy['name']}'s attack!")
            return
        # Apply physical resistance from armor
        phys_res = player.get("physical_resistance", 0.0)
        e_raw = max(1, enemy["attack"] - player["defense"] + dice.between(-2, 4))
        e_dmg = max(1, int(e_raw * (1.0 - phys_res)))
        if "shield" in player_effects:
            shield_data = player_effects["shield"].get("data", player_effects["shield"])
            absorb = shield_data.get("absorb_amount", 0)
            reduction = min(absorb, e_dmg)
            e_dmg = max(0, e_dmg - reduction)
            if reduction > 0:
                log.append(f"Your shield absorbs {reduction} damage!")
        # Active buff absorb (parry etc.)
        for buff in list(player.get("active_buffs", [])):
            if e_dmg <= 0:
                break
            mods = buff.get("modifiers", {})
            absorb = mods.get("absorb_amount", 0)
            if absorb > 0:
                use = min(absorb, e_dmg)
                e_dmg -= use
                mods["absorb_amount"] = absorb - use
        player["hp"] = max(0, player["hp"] - e_dmg)
        if e_dmg > 0:
            res_note = f" (-{int(phys_res * 100)}% phys res)" if phys_res > 0 else ""
            log.append(f"The {enemy['name']} strikes you for {e_dmg} damage{res_note}.")
        else:
            log.append(f"The {enemy['name']} attacks but your defences hold!")


def boss_take_turn(enemy, player, player_effects, log):
    """
    Resolve the boss's turn: may use a special ability or do a regular attack.
    Handles phase transitions, ability cooldowns, and effect application.
    Modifies enemy/player dicts and log in place.
    Returns dict with keys: used_ability (name or None), phase_changed (bool),
    new_phase_desc (str or None).
    """
    result = {"used_ability": None, "phase_changed": False, "new_phase_desc": None}

    boss_key = enemy.get("key", "")
    boss_data = GAME_DATA["bosses"].get(boss_key, {}) if boss_key else {}
    phases = boss_data.get("phases", [])
    abilities = boss_data.get("special_abilities", [])

    hp_pct = enemy["hp"] / max(1, enemy["max_hp"])
    phase_idx, phase_data = get_boss_phase(phases, hp_pct)

    # Detect phase transition
    prev_phase_idx = enemy.get("_phase_idx", 0)
    if phase_idx != prev_phase_idx and phases:
        enemy["_phase_idx"] = phase_idx
        desc = phase_data.get("description", "")
        result["phase_changed"] = True
        result["new_phase_desc"] = desc
        log.append(f"{enemy['name']} enters a new phase! {desc}")

    # Apply phase multipliers to current combat stats (snapshot every turn)
    if "_base_attack" not in enemy:
        enemy["_base_attack"] = enemy["attack"]
        enemy["_base_defense"] = enemy["defense"]

    atk_mult = phase_data.get("attack_multiplier", 1.0)
    def_mult = phase_data.get("defense_multiplier", 1.0)
    enemy["attack"] = max(1, int(enemy["_base_attack"] * atk_mult))
    enemy["defense"] = max(0, int(enemy["_base_defense"] * def_mult))

    # Tick ability cooldowns
    cooldowns = enemy.get("_ability_cooldowns", {})
    for ab_name in list(cooldowns.keys()):
        if cooldowns[ab_name] > 0:
            cooldowns[ab_name] -= 1
    enemy["_ability_cooldowns"] = cooldowns

    # Determine which abilities are unlocked for this phase
    unlocked = set()
    if phases and phase_data.get("special_abilities_unlocked"):
        unlocked = set(phase_data["special_abilities_unlocked"])
    if not unlocked and abilities:
        unlocked = {ab["name"] for ab in abilities}

    # Filter eligible abilities (off cooldown and unlocked)
    eligible = [
        ab
        for ab in abilities
        if ab["name"] in unlocked and cooldowns.get(ab["name"], 0) == 0
    ]

    used_ability = False
    ability_chance = 0.40 if phase_idx >= 1 else 0.25
    if eligible and random.random() < ability_chance:
        ability = random.choice(eligible)
        ab_name = ability["name"]
        result["used_ability"] = ab_name
        used_ability = True
        cooldowns[ab_name] = ability.get("cooldown", 3)
        enemy["_ability_cooldowns"] = cooldowns

        dmg = ability.get("damage", 0)
        effect = ability.get("effect", "")
        stun_chance = ability.get("stun_chance", 0.0)

        if dmg > 0:
            # Ability damage ignores some defense
            raw = max(1, dmg - player["defense"] // 2 + dice.between(-3, 5))
            if "shield" in player_effects:
                absorb = (
                    player_effects["shield"].get("data", {}).get("absorb_amount", 0)
                )
                red = min(absorb, raw)
                raw = max(0, raw - red)
                if red:
                    log.append(f"Your shield absorbs {red} damage!")
            player["hp"] = max(0, player["hp"] - raw)
            log.append(f"{enemy['name']} uses {ab_name}! You take {raw} damage!")
        else:
            log.append(f"{enemy['name']} uses {ab_name}!")

        if effect == "debuff":
            atk_red = ability.get("attack_reduction", 0)
            def_red = ability.get("defense_reduction", 0)
            if atk_red:
                player["attack"] = max(1, player["attack"] - atk_red)
                log.append(f"  Your attack is reduced by {atk_red}!")
            if def_red:
                player["defense"] = max(0, player["defense"] - def_red)
                log.append(f"  Your defense is reduced by {def_red}!")

        if stun_chance and random.random() < stun_chance:
            log.append("  You are stunned and will lose your next turn!")
            player_effects["stunned"] = {"turns": 1, "data": {}}

        if ability.get("description"):
            log.append(f"  ({ability.get('description', '')})")

    if not used_ability:
        # Regular attack
        e_dmg = max(1, enemy["attack"] - player["defense"] + dice.between(-2, 4))
        if "shield" in player_effects:
            absorb = player_effects["shield"].get("data", {}).get("absorb_amount", 0)
            reduction = min(absorb, e_dmg)
            e_dmg = max(0, e_dmg - reduction)
            if reduction > 0:
                log.append(f"Your shield absorbs {reduction} damage!")
        player["hp"] = max(0, player["hp"] - e_dmg)
        if e_dmg > 0:
            log.append(f"The {enemy['name']} strikes you for {e_dmg} damage.")
        else:
            log.append(f"The {enemy['name']} attacks but your shield holds!")

    return result


# ─── Companion combat helpers ─────────────────────────────────────────────────

_COMPANION_RANK_HP = {
    "common": 400, "uncommon": 700, "rare": 1100,
    "epic": 1800, "legendary": 3000,
}

_COMPANION_RANK_ATK_CAP = {
    "common": 120, "uncommon": 180, "rare": 260,
    "epic": 380, "legendary": 520,
}

_COMPANION_RANK_DEF_CAP = {
    "common": 40, "uncommon": 60, "rare": 90,
    "epic": 130, "legendary": 180,
}


def _get_companion_combat_stats(comp_entry):
    """Derive in-battle combat stats for a companion from game data + stored HP."""
    comp_id = comp_entry.get("id", "")
    comp_data = GAME_DATA["companions"].get(comp_id, {})
    rank = comp_data.get("rank", "common")
    max_hp = _COMPANION_RANK_HP.get(rank, 400)
    atk_cap = _COMPANION_RANK_ATK_CAP.get(rank, 120)
    def_cap = _COMPANION_RANK_DEF_CAP.get(rank, 40)
    atk_bonus = comp_data.get("attack_bonus", 0)
    def_bonus = comp_data.get("defense_bonus", 0)
    crit_bonus = comp_data.get("crit_damage_bonus", 0)
    base_atk = atk_bonus * 8 + 60 + crit_bonus // 5
    base_def = def_bonus * 5 + 12
    return {
        "id": comp_id,
        "name": comp_entry.get("name", comp_data.get("name", "Companion")),
        "hp": comp_entry.get("hp", max_hp),
        "max_hp": comp_entry.get("max_hp", max_hp),
        "attack": min(atk_cap, base_atk),
        "defense": min(def_cap, base_def),
        "action_chance": comp_data.get("action_chance", 0.40),
        "crit_chance": min(0.35, comp_data.get("crit_chance", 0) / 100.0),
    }


def _build_battle_companions(player):
    """Build session battle_companions list from player's hired companions."""
    return [
        _get_companion_combat_stats(c)
        for c in player.get("companions", [])
        if isinstance(c, dict)
    ]


def _companion_take_action(battle_companions, enemy, log):
    """
    Each living companion rolls against their action_chance (40% baseline).
    Returns True if the enemy was killed by a companion this turn.
    """
    for comp in battle_companions:
        if comp["hp"] <= 0:
            continue
        if random.random() > comp.get("action_chance", 0.40):
            continue
        dmg = max(1, comp["attack"] - enemy["defense"] + dice.between(-3, 6))
        comp_crit_rate = 0.08 + comp.get("crit_chance", 0.0)
        if random.random() < comp_crit_rate:
            dmg = int(dmg * 1.75)
            log.append(f"[{comp['name']} lands a critical blow on {enemy['name']} for {dmg}!]")
        else:
            log.append(f"[{comp['name']} attacks {enemy['name']} for {dmg} damage.]")
        enemy["hp"] = max(0, enemy["hp"] - dmg)
        if enemy["hp"] <= 0:
            return True
    return False


def _companion_last_stand(battle_companions, enemy, log):
    """
    Simulate companions fighting solo after the player goes down.
    Returns True if they defeat the enemy before all perishing.
    """
    alive = [c for c in battle_companions if c["hp"] > 0]
    if not alive:
        return False
    log.append("You collapse! Your companions fight on in your name!")
    for _ in range(50):
        for comp in [c for c in alive if c["hp"] > 0]:
            dmg = max(1, comp["attack"] - enemy["defense"] + dice.between(-3, 6))
            log.append(f"[{comp['name']} fights on — {dmg} damage to {enemy['name']}!]")
            enemy["hp"] = max(0, enemy["hp"] - dmg)
            if enemy["hp"] <= 0:
                return True
        alive = [c for c in alive if c["hp"] > 0]
        if not alive:
            return False
        target = alive[0]
        e_dmg = max(1, enemy["attack"] - target["defense"] + dice.between(-2, 4))
        target["hp"] = max(0, target["hp"] - e_dmg)
        log.append(f"The {enemy['name']} strikes {target['name']} for {e_dmg} damage!")
        if target["hp"] <= 0:
            log.append(f"{target['name']} falls!")
        alive = [c for c in alive if c["hp"] > 0]
    return False


def _sync_companion_hp_to_player(player, battle_companions):
    """Write battle HP from session companions back into the player's companion list."""
    hp_map = {c["id"]: c["hp"] for c in battle_companions}
    for comp in player.get("companions", []):
        if isinstance(comp, dict) and comp.get("id") in hp_map:
            comp["hp"] = max(0, hp_map[comp["id"]])


def _restore_companion_hp(player):
    """Restore all companions to full HP after any battle outcome."""
    for comp in player.get("companions", []):
        if isinstance(comp, dict) and "max_hp" in comp:
            comp["hp"] = comp["max_hp"]


def _ensure_companion_hp(player):
    """Migration: assign HP/max_hp to companions hired before this system existed."""
    for comp in player.get("companions", []):
        if not isinstance(comp, dict):
            continue
        if "max_hp" not in comp:
            stats = _get_companion_combat_stats(comp)
            comp["hp"] = stats["max_hp"]
            comp["max_hp"] = stats["max_hp"]


# ─── Cutscenes ────────────────────────────────────────────────────────────────


def trigger_cutscene(cutscene_id):
    """Queue a cutscene to display on next game page load, if not already seen."""
    seen = session.get("seen_cutscenes", [])
    cutscene_def = GAME_DATA["cutscenes"].get(cutscene_id)
    if cutscene_def and not cutscene_def.get("iterable", True) and cutscene_id in seen:
        return
    session["pending_cutscene"] = cutscene_id
    session.modified = True


# ─── Status Effects ────────────────────────────────────────────────────────────


def apply_status_effect(effects_dict, effect_key, turns=None):
    """Add or refresh a status effect. Uses duration from effects.json if turns not specified."""
    effect_def = load_json("effects.json").get(effect_key, {})
    duration = turns or effect_def.get("duration", 3)
    effects_dict[effect_key] = {
        "turns": duration,
        "data": effect_def,
    }


def process_turn_effects(entity, effects_dict, log, entity_label):
    """Process all active status effects for an entity. Returns True if stunned."""
    to_remove = []
    stunned = False
    for eff_key, eff_info in list(effects_dict.items()):
        # Support both old nested-data format and new flat format
        data = eff_info.get("data", eff_info)
        eff_type = data.get("type", "")

        # ── Old nested-format effects ──────────────────────────────────────────
        if eff_type == "damage_over_time":
            dmg = data.get("damage", 5)
            entity["hp"] = max(0, entity["hp"] - dmg)
            log.append(
                f"{entity_label} takes {dmg} {eff_key} damage! ({max(0, eff_info['turns'] - 1)} turns left)"
            )
        elif eff_type == "healing_over_time":
            heal = data.get("heal_amount", 8)
            entity["hp"] = min(entity.get("max_hp", entity["hp"]), entity["hp"] + heal)
            log.append(f"{entity_label} regenerates {heal} HP!")
        elif eff_type == "action_block":
            stunned = True
            log.append(f"{entity_label} is stunned and cannot act!")

        # ── New flat-format proc effects ───────────────────────────────────────
        elif eff_key == "bleed":
            dmg = eff_info.get("damage", 6)
            entity["hp"] = max(0, entity["hp"] - dmg)
            turns_left = max(0, eff_info["turns"] - 1)
            log.append(f"{entity_label} bleeds for {dmg} damage! ({turns_left} turns left)")

        elif eff_key == "daze":
            stunned = True
            log.append(f"{entity_label} is dazed and cannot act this turn!")

        elif eff_key == "weaken":
            # Weaken reduces effective defense — tracked in effect, applied in damage calc
            turns_left = max(0, eff_info["turns"] - 1)
            if turns_left > 0:
                log.append(f"{entity_label}'s defences remain weakened! ({turns_left} turns left)")

        elif eff_key == "shaken":
            turns_left = max(0, eff_info["turns"] - 1)
            if turns_left > 0:
                log.append(f"{entity_label} is still shaken! ({turns_left} turns left)")

        elif eff_key == "armor_crushed":
            turns_left = max(0, eff_info["turns"] - 1)
            if turns_left > 0:
                log.append(f"{entity_label}'s armour remains crushed! ({turns_left} turns left)")

        eff_info["turns"] -= 1
        if eff_info["turns"] <= 0:
            to_remove.append(eff_key)
            if eff_type == "stat_boost":
                # Revert stat boosts from old format
                for stat_key in ("defense_bonus", "attack_bonus", "speed_bonus"):
                    if stat_key in data:
                        stat = stat_key.replace("_bonus", "")
                        entity[stat] = max(1, entity.get(stat, 0) - data[stat_key])

    for k in to_remove:
        effects_dict.pop(k, None)

    return stunned


# ─── Equipment Helpers ───────────────────────────────────────────────────────

STAT_BONUSES = [
    ("attack_bonus", "attack", 1),
    ("defense_bonus", "defense", 1),
    ("speed_bonus", "speed", 1),
    ("hp_bonus", "max_hp", 1),
    ("mp_bonus", "max_mp", 1),
    ("defense_penalty", "defense", -1),
    ("speed_penalty", "speed", -1),
    ("spell_power_bonus", "attr_spell_power", 1),
    # New equipment stats
    ("evasion_bonus", "attr_evasion", 1),
    ("spell_power", "attr_spell_power", 1),
    ("crit_chance", "attr_crit_chance", 1),
]


def apply_item_bonuses(player, item_data, direction=1):
    """Apply (direction=1) or remove (direction=-1) item stat bonuses."""
    for bonus_key, stat_key, sign in STAT_BONUSES:
        val = item_data.get(bonus_key, 0)
        if val:
            player[stat_key] = max(
                0, player.get(stat_key, 0) + int(val) * sign * direction
            )
    hp_bonus = item_data.get("hp_bonus", 0)
    if hp_bonus and direction == 1:
        player["hp"] = min(player["hp"] + hp_bonus, player["max_hp"])
    mp_bonus = item_data.get("mp_bonus", 0)
    if mp_bonus and direction == 1:
        player["mp"] = min(player["mp"] + mp_bonus, player["max_mp"])

    # Elemental resistances (armor only) — clamp to [0, 0.9]
    res_keys = ("physical_resistance", "fire_resistance", "ice_resistance",
                "lightning_resistance", "poison_resistance", "magic_resistance")
    for rk in res_keys:
        val = item_data.get(rk, 0.0)
        if val:
            current = player.get(rk, 0.0)
            player[rk] = max(0.0, min(0.9, current + val * direction))

    # Outlaw tag on bows/daggers: grant dodge_chance bonus
    if item_data.get("type") == "weapon":
        tags = item_data.get("tags", [])
        if "outlaw" in tags:
            dodge_bonus = 0.06
            player["dodge_chance"] = round(
                max(0.0, player.get("dodge_chance", 0.0) + dodge_bonus * direction), 4
            )


def _ensure_equipment_slots(player):
    """Ensure player has all equipment slots including 3 accessory slots."""
    if "equipment" not in player:
        player["equipment"] = {}
    for slot in (
        "weapon",
        "armor",
        "offhand",
        "accessory_1",
        "accessory_2",
        "accessory_3",
    ):
        player["equipment"].setdefault(slot, None)
    # Migrate old single 'accessory' slot
    if "accessory" in player["equipment"]:
        old_val = player["equipment"].pop("accessory")
        if old_val and not player["equipment"].get("accessory_1"):
            player["equipment"]["accessory_1"] = old_val


def equip_item(player, item_name):
    """Equip item from inventory. Returns (success, message)."""
    if item_name not in player.get("inventory", []):
        return False, f"You don't have {item_name}."

    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict):
        return False, f"{item_name} cannot be equipped."

    item_type = item_data.get("type", "")
    if item_type not in EQUIPPABLE_TYPES:
        return False, f"{item_name} is not equippable (type: {item_type})."

    req = item_data.get("requirements", {})
    if req.get("level", 1) > player.get("level", 1):
        return False, f"Requires level {req['level']} to equip."
    if req.get("class") and req["class"] != player.get("class", ""):
        return False, f"Only {req['class']} can equip {item_name}."

    _ensure_equipment_slots(player)
    equipment = player["equipment"]

    # Determine slot
    if item_type == "accessory":
        slot = None
        for i in range(1, 4):
            s = f"accessory_{i}"
            if not equipment.get(s):
                slot = s
                break
        if not slot:
            slot = "accessory_1"  # Replace slot 1 if all full
    else:
        slot = item_type

    # Unequip current item in slot
    current = equipment.get(slot)
    if current:
        cur_data = GAME_DATA["items"].get(current, {})
        if isinstance(cur_data, dict):
            apply_item_bonuses(player, cur_data, direction=-1)
        player["inventory"].append(current)

    # Equip new item
    equipment[slot] = item_name
    player["inventory"].remove(item_name)
    apply_item_bonuses(player, item_data, direction=1)

    bonuses = []
    for bonus_key, stat_key, sign in STAT_BONUSES:
        val = item_data.get(bonus_key, 0)
        if val:
            label = stat_key.replace("max_", "").upper()
            bonuses.append(f"+{int(val) * sign} {label}")
    bonus_str = ", ".join(bonuses) if bonuses else ""
    msg = f"You equip {item_name}."
    if bonus_str:
        msg += f" ({bonus_str})"
    return True, msg


def unequip_item(player, slot):
    """Unequip item from slot. Returns (success, message)."""
    equipment = player.get("equipment", {})
    item_name = equipment.get(slot)
    if not item_name:
        return False, f"Nothing equipped in {slot} slot."

    item_data = GAME_DATA["items"].get(item_name, {})
    if isinstance(item_data, dict):
        apply_item_bonuses(player, item_data, direction=-1)

    equipment[slot] = None
    player["inventory"].append(item_name)
    return True, f"You unequip {item_name}."


def _item_score(item_data):
    """Score an item by total stat contribution (higher = better)."""
    if not isinstance(item_data, dict):
        return 0
    score = 0
    score += item_data.get("attack_bonus", 0) * 2
    score += item_data.get("defense_bonus", 0) * 2
    score += item_data.get("speed_bonus", 0) * 1.5
    score += item_data.get("hp_bonus", 0) * 0.3
    score += item_data.get("mp_bonus", 0) * 0.3
    score += item_data.get("spell_power_bonus", 0) * 1.5
    score -= item_data.get("defense_penalty", 0) * 2
    score -= item_data.get("speed_penalty", 0) * 1.5
    score += item_data.get("sharpness", 0) * 0.8
    score += item_data.get("smiting", 0) * 0.7
    score += item_data.get("fire_attack", 0) * 0.9
    score += item_data.get("ice_attack", 0) * 0.9
    score += item_data.get("lightning_attack", 0) * 0.9
    score += item_data.get("poison_attack", 0) * 0.7
    score += (item_data.get("aim_accuracy", 85) - 85) * 0.3
    return score


def auto_equip_best(player):
    """
    Auto-equip the best items from inventory for each slot.
    Only swaps if the inventory item is better than what is equipped.
    Returns list of messages about what was equipped.
    """
    items_data: dict[str, Any] = GAME_DATA["items"]
    player_level = player.get("level", 1)
    player_class = player.get("class", "")
    _ensure_equipment_slots(player)
    equipment = player["equipment"]

    # Put all currently equipped items back in inventory for fair comparison
    for slot in list(equipment.keys()):
        current = equipment.get(slot)
        if current:
            equipment[slot] = None
            player["inventory"].append(current)
            item_d = items_data.get(current, {})
            if isinstance(item_d, dict):
                apply_item_bonuses(player, item_d, direction=-1)

    # Group inventory items by their equip slot
    slot_candidates: dict[str, list[str]] = {
        "weapon": [],
        "armor": [],
        "offhand": [],
        "accessory": [],
    }
    for item_name in list(player.get("inventory", [])):
        item_data = items_data.get(item_name, {})
        if not isinstance(item_data, dict):
            continue
        item_type = item_data.get("type", "")
        if item_type not in EQUIPPABLE_TYPES:
            continue
        req = item_data.get("requirements", {})
        if req.get("level", 1) > player_level:
            continue
        if req.get("class") and req["class"] != player_class:
            continue
        group = "accessory" if item_type == "accessory" else item_type
        if group in slot_candidates:
            slot_candidates[group].append(item_name)

    messages = []

    # Equip best weapon, armor, offhand
    for slot in ("weapon", "armor", "offhand"):
        candidates = slot_candidates.get(slot, [])
        if not candidates:
            continue
        best = max(candidates, key=lambda n: _item_score(items_data.get(n, {})))
        ok, msg = equip_item(player, best)
        if ok:
            messages.append(msg)

    # Equip best accessories (up to 3)
    acc_candidates = sorted(
        slot_candidates.get("accessory", []),
        key=lambda n: _item_score(items_data.get(n, {})),
        reverse=True,
    )
    for item_name in acc_candidates[:3]:
        ok, msg = equip_item(player, item_name)
        if ok:
            messages.append(msg)

    if not messages:
        messages.append("No better items found to equip.")
    return messages


# Bro comments are unnecessary here

# NO THEY'RE NECESSARY FOR THE TEAM


def get_quest_progress(mission_id):
    return session.get("quest_progress", {}).get(mission_id, {})


def update_quest_kills(enemy_key, enemy_name):
    """Update kill counts for all active kill quests matching this enemy."""
    completed = set(session.get("completed_missions", []))
    missions: dict[str, Any] = GAME_DATA["missions"]
    quest_progress: dict[str, Any] = session.get("quest_progress") or {}
    changed = False

    for mid, mission in missions.items():
        if mid in completed:
            continue
        if mission.get("type") != "kill":
            continue

        target = mission.get("target", "")
        target_count = mission.get("target_count", 1)

        targets_to_check = []
        if isinstance(target_count, dict):
            targets_to_check = list(target_count.keys())
        else:
            targets_to_check = [target]

        for t in targets_to_check:
            t_lower = t.lower().replace(" ", "_")
            e_lower = enemy_key.lower().replace(" ", "_")
            e_name_lower = enemy_name.lower().replace(" ", "_")
            if (
                t_lower == e_lower
                or t_lower in e_lower
                or e_lower in t_lower
                or t_lower == e_name_lower
            ):
                if mid not in quest_progress:
                    quest_progress[mid] = {"kills": {}}
                if "kills" not in quest_progress[mid]:
                    quest_progress[mid]["kills"] = {}
                quest_progress[mid]["kills"][t] = (
                    quest_progress[mid]["kills"].get(t, 0) + 1
                )
                changed = True

    if changed:
        session["quest_progress"] = quest_progress
        session.modified = True


def check_mission_completable(mission_id, player):
    """Check if a mission can be completed right now."""
    mission = GAME_DATA["missions"].get(mission_id, {})
    if not mission:
        return False, "Mission not found."

    completed = set(session.get("completed_missions", []))
    if mission_id in completed:
        return False, "Already completed."

    unlock_level = mission.get("unlock_level", 1)
    if player.get("level", 1) < unlock_level:
        return False, f"Requires level {unlock_level}."

    prereqs = mission.get("prerequisites", [])
    for prereq in prereqs:
        if prereq not in completed:
            prereq_name = GAME_DATA["missions"].get(prereq, {}).get("name", prereq)
            return False, f"Requires: {prereq_name}"

    mission_type = mission.get("type", "")
    target_count = mission.get("target_count", 1)
    target = mission.get("target", "")

    progress = session.get("quest_progress", {}).get(mission_id, {})

    if mission_type == "kill":
        if isinstance(target_count, dict):
            for t, needed in target_count.items():
                have = progress.get("kills", {}).get(t, 0)
                if have < needed:
                    return (
                        False,
                        f"Kill more {t.replace('_', ' ').title()} ({have}/{needed})",
                    )
        else:
            have = progress.get("kills", {}).get(target, 0)
            if have < target_count:
                return (
                    False,
                    f"Kill {target.replace('_', ' ').title()} ({have}/{target_count})",
                )

    elif mission_type == "collect":
        if isinstance(target_count, dict):
            inv_counts: dict[str, int] = {}
            for item in player.get("inventory", []):
                inv_counts[item] = inv_counts.get(item, 0) + 1
            for item_name, needed in target_count.items():
                have = inv_counts.get(item_name, 0)
                if have < needed:
                    return (
                        False,
                        f"Need {needed}x {item_name} in inventory ({have}/{needed})",
                    )
        else:
            inv_counts = {}
            for item in player.get("inventory", []):
                inv_counts[item] = inv_counts.get(item, 0) + 1
            have = inv_counts.get(target, 0)
            if have < target_count:
                return False, f"Need {target} in inventory ({have}/{target_count})"

    return True, "Ready"


def get_mission_progress_display(mission_id, player):
    """Return display info about mission progress."""
    mission = GAME_DATA["missions"].get(mission_id, {})
    if not mission:
        return []

    mission_type = mission.get("type", "")
    target_count = mission.get("target_count", 1)
    target = mission.get("target", "")
    progress = session.get("quest_progress", {}).get(mission_id, {})
    items_display = []

    if mission_type == "kill":
        if isinstance(target_count, dict):
            for t, needed in target_count.items():
                have = progress.get("kills", {}).get(t, 0)
                items_display.append(
                    {"label": t.replace("_", " ").title(), "have": have, "need": needed}
                )
        else:
            have = progress.get("kills", {}).get(target, 0)
            items_display.append(
                {
                    "label": target.replace("_", " ").title(),
                    "have": have,
                    "need": target_count,
                }
            )

    elif mission_type == "collect":
        inv_counts: dict[str, int] = {}
        for item in player.get("inventory", []):
            inv_counts[item] = inv_counts.get(item, 0) + 1
        if isinstance(target_count, dict):
            for item_name, needed in target_count.items():
                have = inv_counts.get(item_name, 0)
                items_display.append({"label": item_name, "have": have, "need": needed})
        else:
            have = inv_counts.get(target, 0)
            items_display.append({"label": target, "have": have, "need": target_count})

    return items_display


@app.route("/game_assets/<path:filename>")
def serve_game_asset(filename):
    return send_from_directory("data/assets", filename)


@app.route("/chat")
def chat_page():
    username = session.get("online_username")
    if not username:
        return redirect(url_for("index"))
    return render_template("chat.html", online_username=username)


@app.route("/")
def index():
    splash_texts = GAME_DATA.get("splash_texts", [])
    splash = random.choice(splash_texts) if splash_texts else ""
    online_user = session.get("online_username")
    online_user_id = session.get("online_user_id")
    cloud_meta = None
    if online_user_id:
        cloud_meta = get_cloud_save_meta(online_user_id)
    return render_template(
        "index.html",
        show_welcome=True,
        splash_text=splash,
        online_user=online_user,
        cloud_meta=cloud_meta,
    )


@app.route("/play")
def play():
    return render_template("play.html")


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "GET":
        return redirect(url_for("game"))
    else:
        name = request.form.get("name", "").strip()
        cls = request.form.get("class", "Warrior")
        race = request.form.get("race", "Human")
        gender = request.form.get("gender", "male")
        if gender not in ("male", "female", "nonbinary"):
            gender = "male"
        background = request.form.get("background", "soldier")
        valid_backgrounds = {
            "soldier",
            "scholar",
            "street_rat",
            "farmer",
            "noble",
            "wanderer",
            "herbalist",
            "sailor",
            "mercenary",
            "acolyte",
            "blacksmith",
        }
        if background not in valid_backgrounds:
            background = "soldier"
        if not name:
            session["create_error"] = "Please enter a character name."
            return redirect(url_for("game"))

        if race not in GAME_DATA["races"]:
            race = "Human"

        cls_data = GAME_DATA["classes"].get(cls, {})
        stats = cls_data.get(
            "base_stats", {"hp": 100, "mp": 50, "attack": 10, "defense": 8, "speed": 10}
        )

        race_data = GAME_DATA["races"].get(race, {})
        race_mods = race_data.get("stat_modifiers", {})

        base_hp = max(10, stats.get("hp", 100) + race_mods.get("hp", 0))
        base_mp = max(0, stats.get("mp", 50) + race_mods.get("mp", 0))
        base_atk = max(1, stats.get("attack", 10) + race_mods.get("attack", 0))
        base_def = max(1, stats.get("defense", 8) + race_mods.get("defense", 0))
        base_spd = max(1, stats.get("speed", 10) + race_mods.get("speed", 0))
        base_gold = max(
            0, cls_data.get("starting_gold", 100) + race_mods.get("gold", 0)
        )

        if gender == "male":
            base_atk += 4
            base_mp += 3
            base_hp += 15
        elif gender == "female":
            base_spd += 3
            base_gold += 25
            base_mp += 5
        elif gender == "nonbinary":
            base_atk += 2
            base_spd += 2
            base_hp += 10

        background_bonuses: dict[str, dict[str, Any]] = {
            "soldier": {"attack": 5, "defense": 5},
            "scholar": {"mp": 8, "spell_power": 2},
            "street_rat": {"speed": 3, "gold": 30},
            "farmer": {"hp": 20, "defense": 2},
            "noble": {"gold": 60, "gold_discount": 0.05},
            "wanderer": {"speed": 2, "exp_bonus": 0.10},
            "herbalist": {"hp": 12, "mp": 5},
            "sailor": {"attack": 3, "speed": 3},
            "mercenary": {"attack": 7},
            "acolyte": {"mp": 10, "spell_power": 1},
            "blacksmith": {"defense": 4, "attack": 2},
        }
        bg: dict[str, Any] = background_bonuses.get(background, {})
        base_atk += bg.get("attack", 0)
        base_def += bg.get("defense", 0)
        base_mp += bg.get("mp", 0)
        base_spd += bg.get("speed", 0)
        base_gold += bg.get("gold", 0)
        base_hp += bg.get("hp", 0)

        player = {
            "name": name,
            "class": cls,
            "race": race,
            "gender": gender,
            "background": background,
            "level": 1,
            "experience": 0,
            "experience_to_next": 100,
            "hp": base_hp,
            "max_hp": base_hp,
            "mp": base_mp,
            "max_mp": base_mp,
            "attack": base_atk,
            "defense": base_def,
            "speed": base_spd,
            "gold": base_gold,
            "inventory": list(cls_data.get("starting_items", ["Health Potion"])),
            "equipment": {
                "weapon": None,
                "armor": None,
                "offhand": None,
                "accessory_1": None,
                "accessory_2": None,
                "accessory_3": None,
            },
            "companions": [],
            "rank": "F-Tier Adventurer",
            "level_up_bonuses": cls_data.get(
                "level_up_bonuses",
                {"hp": 10, "mp": 2, "attack": 2, "defense": 1, "speed": 1},
            ),
            "comfort_points": 0,
            "housing_owned": [],
            "building_slots": {},
            "crops": {},
            "pet": None,
            "explore_count": 0,
            "game_ticks": 0,
            "weekly_challenges_progress": {},
            "boss_cooldowns": {},
        }
        if bg.get("spell_power"):
            player["attr_spell_power"] = (
                player.get("attr_spell_power", 0) + bg["spell_power"]
            )
        if bg.get("gold_discount"):
            player["attr_gold_discount"] = (
                player.get("attr_gold_discount", 0.0) + bg["gold_discount"]
            )
        if bg.get("exp_bonus"):
            player["attr_exp_bonus"] = (
                player.get("attr_exp_bonus", 0.0) + bg["exp_bonus"]
            )
        auto_equip_best(player)
        save_player(player)
        session["messages"] = []
        session["diary"] = []
        session["current_area"] = "starting_village"
        session["completed_missions"] = []
        session["visited_areas"] = ["starting_village"]
        session["quest_progress"] = {}
        session["seen_cutscenes"] = []
        trigger_cutscene("welcome_cutscene")
        add_message(
            f"Welcome, {name} the {race} {cls}! Your legend begins.", "var(--gold)"
        )
        add_message(
            "You stand at the gates of the Starting Village. Adventure awaits.",
            "var(--text-light)",
        )
        _set_activity(player, f"beginning their legend as {cls}")
        _autosave()
        return redirect(url_for("game"))


@app.route("/game")
def game():
    player = get_player()
    if not player:
        user_id = session.get("online_user_id")
        if user_id:
            result = character_autoload(user_id)
            if result["ok"] and result.get("data"):
                _apply_game_state(result["data"])
                player = session.get("player")
    if not player:
        create_error = session.pop("create_error", None)
        session.modified = True
        return render_template(
            "index.html", show_create=True, data=GAME_DATA, create_error=create_error
        )

    # ── Timed events ──────────────────────────────────────────────────────────
    events_awarded = check_and_award_events(player)
    save_player(player)
    if events_awarded:
        _set_activity(player, "claiming an event reward")
        _autosave()

    # ── Battle state: show battle view inline ──────────────.g�───────────────
    _ensure_companion_hp(player)

    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if enemy:
        battle_log = session.get("battle_log", [])
        _items_data = GAME_DATA["items"]
        usable_items = [
            i
            for i in player.get("inventory", [])
            if any(x in i.lower() for x in ["potion", "elixir", "tears", "tonic"])
            or isinstance(_items_data.get(i), dict) and _items_data[i].get("event_item")
        ]
        weapon = player.get("equipment", {}).get("weapon")
        available_spells = get_available_spells(
            weapon, GAME_DATA["items"], GAME_DATA["spells"]
        )
        weapon_data = GAME_DATA["items"].get(weapon, {}) if weapon else {}
        has_magic_weapon = bool(
            weapon and isinstance(weapon_data, dict) and weapon_data.get("magic_weapon")
        )
        player_effects: dict[str, Any] = session.get("battle_player_effects") or {}
        enemy_effects: dict[str, Any] = session.get("battle_enemy_effects") or {}
        boss_dialogue = None
        boss_phase_info = None
        boss_abilities_info = []
        if enemy.get("is_boss"):
            boss_key = enemy.get("key", "")
            boss_dialogue = get_boss_dialogue(boss_key, "start")
            boss_data = GAME_DATA["bosses"].get(boss_key, {})
            phases = boss_data.get("phases", [])
            if phases:
                hp_pct = enemy["hp"] / max(1, enemy["max_hp"])
                phase_idx, phase_data = get_boss_phase(phases, hp_pct)
                total_phases = len(phases)
                boss_phase_info = {
                    "index": phase_idx + 1,
                    "total": total_phases,
                    "description": phase_data.get("description", ""),
                    "attack_multiplier": phase_data.get("attack_multiplier", 1.0),
                }
            abilities = boss_data.get("special_abilities", [])
            cooldowns = enemy.get("_ability_cooldowns", {})
            for ab in abilities:
                boss_abilities_info.append(
                    {
                        "name": ab["name"],
                        "description": ab.get("description", ""),
                        "cooldown_left": cooldowns.get(ab["name"], 0),
                    }
                )
        battle_companions = session.get("battle_companions", [])
        return render_template(
            "index.html",
            in_battle=True,
            player=player,
            enemy=enemy,
            battle_log=battle_log[-14:],
            usable_items=usable_items,
            available_spells=available_spells,
            has_magic_weapon=has_magic_weapon,
            player_effects=player_effects,
            enemy_effects=enemy_effects,
            boss_dialogue=boss_dialogue,
            boss_phase_info=boss_phase_info,
            boss_abilities_info=boss_abilities_info,
            battle_companions=battle_companions,
        )

    _ensure_equipment_slots(player)

    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    area_name = area.get("name", area_key.replace("_", " ").title())

    visited_areas = session.get("visited_areas", [area_key])
    connections = []
    for conn_key in area.get("connections", []):
        conn_area = GAME_DATA["areas"].get(conn_key, {})
        difficulty = conn_area.get("difficulty", 0)
        is_visited = conn_key in visited_areas
        connections.append(
            {
                "key": conn_key,
                # FOW: reveal name and details only for visited areas
                "name": conn_area.get("name", conn_key.replace("_", " ").title()) if is_visited else "???",
                "has_danger": bool(conn_area.get("possible_enemies")) if is_visited else None,
                "visited": is_visited,
                "difficulty": difficulty if is_visited else -1,
            }
        )

    # Shop items
    shop_discount = min(0.50, player.get("attr_gold_discount", 0.0))
    shop_items = []
    shop_name = ""
    for shop_key in area.get("shops", []):
        if shop_key == "pet_shop":
            continue
        shop_data = GAME_DATA["shops"].get(shop_key, {})
        shop_name = shop_data.get("name", "Shop")
        for item_name in shop_data.get("items", []):
            item_data = GAME_DATA["items"].get(item_name, {})
            if not isinstance(item_data, dict):
                continue
            base_price = item_data.get("price", item_data.get("value", 20))
            price = max(1, int(base_price * (1.0 - shop_discount)))
            shop_items.append(
                {
                    "name": item_name,
                    "price": price,
                    "base_price": base_price,
                    "discounted": shop_discount > 0,
                    "rarity": item_data.get("rarity", "common"),
                    "description": item_data.get("description", ""),
                    "type": item_data.get("type", "misc"),
                    "stats": _item_stat_summary(item_data),
                    "can_afford": player["gold"] >= price,
                }
            )

    # Inventory
    inventory_items = []
    counts: dict[str, int] = {}
    for item_name in player.get("inventory", []):
        counts[item_name] = counts.get(item_name, 0) + 1
    for item_name, count in counts.items():
        item_data = GAME_DATA["items"].get(item_name, {})
        if not isinstance(item_data, dict):
            item_data = {}
        sell_price = max(
            1, int(item_data.get("price", item_data.get("value", 10)) * 0.5)
        )
        item_type = item_data.get("type", "")
        is_equippable = item_type in EQUIPPABLE_TYPES
        req = item_data.get("requirements", {})
        level_req = req.get("level", 1)
        class_req = req.get("class", None)
        player_level = player.get("level", 1)
        player_class = player.get("class", "")
        can_equip = True
        equip_block_reason = None
        if is_equippable:
            if player_level < level_req:
                can_equip = False
                equip_block_reason = f"Requires Level {level_req}"
            elif class_req and player_class != class_req:
                can_equip = False
                equip_block_reason = f"{class_req} only"
        req_label = None
        if level_req > 1 or class_req:
            parts = []
            if level_req > 1:
                parts.append(f"Lv.{level_req}")
            if class_req:
                parts.append(class_req)
            req_label = " · ".join(parts)
        _book_key = item_data.get("book_key", "") if item_type == "book" else ""
        inventory_items.append(
            {
                "name": item_name,
                "count": count,
                "rarity": item_data.get("rarity", "common"),
                "description": item_data.get("description", ""),
                "sell_price": sell_price,
                "type": item_type,
                "equippable": is_equippable,
                "can_equip": can_equip,
                "equip_block_reason": equip_block_reason,
                "req_label": req_label,
                "stats": _item_stat_summary(item_data),
                "is_book": item_type == "book",
                "book_key": _book_key,
                "already_read": _book_key in player.get("read_books", []),
            }
        )

    # Equipment info — includes 3 accessory slots
    equipped_details = {}
    for slot, item_name in player.get("equipment", {}).items():
        if item_name:
            item_data = GAME_DATA["items"].get(item_name, {})
            if isinstance(item_data, dict):
                equipped_details[slot] = {
                    "name": item_name,
                    "rarity": item_data.get("rarity", "common"),
                    "description": item_data.get("description", ""),
                    "stats": _item_stat_summary(item_data),
                    "weapon_type": item_data.get("weapon_type", "") if slot == "weapon" else "",
                }

    # Missions
    completed = session.get("completed_missions", [])
    completed_set = set(completed)
    npc_unlocked_quests = set(session.get("npc_unlocked_quests", []))
    available_missions = []
    for mid, mission in GAME_DATA["missions"].items():
        if mid in completed_set:
            continue
        if mission.get("npc_triggered") and mid not in npc_unlocked_quests:
            continue
        unlock_level = mission.get("unlock_level", 1)
        prereqs = mission.get("prerequisites", [])
        prereqs_met = all(p in completed_set for p in prereqs)
        level_ok = player.get("level", 1) >= unlock_level

        progress_items = get_mission_progress_display(mid, player)
        can_complete, status_msg = check_mission_completable(mid, player)

        reward = mission.get("reward", {})
        exp_reward = reward.get("experience", mission.get("experience_reward", 0))
        gold_reward = reward.get("gold", mission.get("gold_reward", 0))
        item_rewards = reward.get("items", [])

        available_missions.append(
            {
                "id": mid,
                "name": mission.get("name", mid),
                "description": mission.get("description", ""),
                "type": mission.get("type", "kill"),
                "exp_reward": exp_reward,
                "gold_reward": gold_reward,
                "item_rewards": item_rewards,
                "unlock_level": unlock_level,
                "prereqs_met": prereqs_met,
                "level_ok": level_ok,
                "eligible": level_ok and prereqs_met,
                "can_complete": can_complete,
                "status_msg": status_msg,
                "progress": progress_items,
                "area": mission.get("area", "any"),
            }
        )

    available_missions.sort(key=lambda m: (not m["eligible"], m["unlock_level"]))

    # Your Land data
    land_data = None
    if area_key == "your_land":
        housing_data: dict[str, Any] = GAME_DATA["housing"]
        farming_data: dict[str, Any] = GAME_DATA["farming"].get("crops", {})
        pets_data: dict[str, Any] = GAME_DATA["pets"]
        owned_set = set(player.get("housing_owned", []))
        building_slots = player.get("building_slots", {})
        crops = player.get("crops", {})

        housing_by_type: dict[str, list[Any]] = {}
        for h_key, h_item in housing_data.items():
            h_type = h_item.get("type", "decoration")
            if h_type not in housing_by_type:
                housing_by_type[h_type] = []
            housing_by_type[h_type].append(
                {
                    "key": h_key,
                    "name": h_item.get("name", h_key),
                    "description": h_item.get("description", ""),
                    "price": h_item.get("price", 100),
                    "comfort": h_item.get("comfort_points", 5),
                    "rarity": h_item.get("rarity", "common"),
                    "owned": h_key in owned_set,
                    "can_afford": player["gold"] >= h_item.get("price", 100),
                }
            )

        placed_by_type: dict[str, list[Any]] = {}
        for slot_id, h_key in building_slots.items():
            if h_key:
                slot_type = slot_id.rsplit("_", 1)[0]
                h_item = housing_data.get(h_key, {})
                if slot_type not in placed_by_type:
                    placed_by_type[slot_type] = []
                placed_by_type[slot_type].append(
                    {
                        "slot_id": slot_id,
                        "key": h_key,
                        "name": h_item.get("name", h_key),
                        "comfort": h_item.get("comfort_points", 0),
                    }
                )

        farm_crops = []
        for i in range(1, 5):
            slot_id = f"farm_{i}"
            crop_info = crops.get(slot_id)
            if crop_info:
                crop_def = farming_data.get(crop_info["crop_key"], {})
                farm_crops.append(
                    {
                        "slot_id": slot_id,
                        "crop_key": crop_info["crop_key"],
                        "name": crop_def.get("name", crop_info["crop_key"]),
                        "ready": crop_info.get("ready", False),
                        "turns": crop_info.get("turns", 0),
                        "growth_time": crop_info.get("growth_time", 5),
                        "sell_price": crop_def.get("sell_price", 15),
                        "harvest_amount": crop_def.get("harvest_amount", 3),
                    }
                )
            else:
                farm_crops.append({"slot_id": slot_id, "crop_key": None})

        pet_data_current = None
        if player.get("pet"):
            pd = pets_data.get(player["pet"], {})
            pet_data_current = {
                "key": player["pet"],
                "name": pd.get("name", player["pet"]),
                "boosts": pd.get("boosts", {}),
            }

        has_training_place = any(
            k.startswith("training_place") and v for k, v in building_slots.items()
        )
        has_garden = any(
            k.startswith("garden") and v for k, v in building_slots.items()
        )

        land_data = {
            "housing_by_type": housing_by_type,
            "placed_by_type": placed_by_type,
            "comfort_points": player.get("comfort_points", 0),
            "building_slots": building_slots,
            "building_types": BUILDING_TYPES,
            "farm_crops": farm_crops,
            "farming_crops": farming_data,
            "pets": {
                k: {
                    "key": k,
                    "name": v.get("name", k),
                    "description": v.get("description", ""),
                    "price": v.get("price", 500),
                    "boosts": v.get("boosts", {}),
                    "can_afford": player["gold"] >= v.get("price", 500),
                }
                for k, v in pets_data.items()
            },
            "current_pet": pet_data_current,
            "owned_housing": owned_set,
            "training_options": TRAINING_OPTIONS,
            "has_training_place": has_training_place,
            "has_garden": has_garden,
        }

    # Companion system
    active_companions = []
    for comp in player.get("companions", []):
        if isinstance(comp, dict):
            comp_id = comp.get("id")
            comp_data = GAME_DATA["companions"].get(comp_id, {})
            rank = comp_data.get("rank", "common")
            max_hp = comp.get("max_hp", _COMPANION_RANK_HP.get(rank, 400))
            cur_hp = comp.get("hp", max_hp)
            hp_pct = int(cur_hp / max_hp * 100) if max_hp > 0 else 100
            active_companions.append(
                {
                    "id": comp_id,
                    "name": comp.get("name", comp_id or ""),
                    "class": comp_data.get("class", ""),
                    "rank": rank,
                    "description": comp_data.get("description", ""),
                    "stat_summary": _companion_stat_summary(comp_data),
                    "hp": cur_hp,
                    "max_hp": max_hp,
                    "hp_pct": hp_pct,
                }
            )

    companions_available = []
    if area_key == "tavern":
        hired_ids = {
            c.get("id") for c in player.get("companions", []) if isinstance(c, dict)
        }
        for comp_id, comp_data in GAME_DATA["companions"].items():
            companions_available.append(
                {
                    "id": comp_id,
                    "name": comp_data.get("name", comp_id),
                    "class": comp_data.get("class", ""),
                    "rank": comp_data.get("rank", "common"),
                    "description": comp_data.get("description", ""),
                    "price": comp_data.get("price", 100),
                    "can_afford": player["gold"] >= comp_data.get("price", 100),
                    "already_hired": comp_id in hired_ids,
                    "stat_summary": _companion_stat_summary(comp_data),
                }
            )

    # Time and weather
    game_time = get_game_time()
    game_time_icon = TIME_ICONS.get(game_time, "")
    area_name_for_weather = GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "")
    current_weather = get_real_weather(area_name_for_weather)
    weather_def = GAME_DATA["weather"].get(current_weather, {})
    weather_display = current_weather.replace("_", " ").title()
    weather_icon = ""
    weather_bonus_exp = int(weather_def.get("bonuses", {}).get("exp_bonus", 0) * 100)
    weather_bonus_gold = int(weather_def.get("bonuses", {}).get("gold_bonus", 0) * 100)

    # Weekly challenges
    challenges_display = build_challenges_display(player)

    # Boss challenges for current area
    available_bosses = []
    now_ts = _time_module.time()
    boss_cooldowns = player.get("boss_cooldowns", {})
    for boss_key in area.get("possible_bosses", []):
        boss_data = GAME_DATA["bosses"].get(boss_key, {})
        if not boss_data:
            continue
        cooldown_until = boss_cooldowns.get(boss_key, 0)
        on_cooldown = now_ts < cooldown_until
        secs_left = max(0, int(cooldown_until - now_ts))
        hours_left = secs_left // 3600
        mins_left = (secs_left % 3600) // 60
        available_bosses.append(
            {
                "key": boss_key,
                "name": boss_data.get("name", boss_key.replace("_", " ").title()),
                "on_cooldown": on_cooldown,
                "cooldown_str": f"{hours_left}h {mins_left}m" if on_cooldown else "",
            }
        )

    # Pending cutscene
    pending_cutscene_id = session.get("pending_cutscene")
    pending_cutscene = None
    if pending_cutscene_id:
        cs = GAME_DATA["cutscenes"].get(pending_cutscene_id)
        if cs:
            pending_cutscene = {
                "id": pending_cutscene_id,
                "content": cs.get("content", {}),
            }

    # Crafting data for inline tab
    crafting_data: dict[str, Any] = GAME_DATA.get("crafting", {})
    raw_recipes = get_recipes(crafting_data)
    crafting_recipes = []
    for recipe in raw_recipes:
        check = check_recipe_craftable(player, recipe)
        crafting_recipes.append(
            {**recipe, "can_craft": check["ok"], "missing": check.get("missing", [])}
        )

    # Events data for inline tab
    def _get_events_display(p):
        today = _dt.date.today()
        today_str = today.isoformat()
        raw_events = GAME_DATA.get("events", [])
        claimed = set(p.get("claimed_events", []))
        boss_kills = p.get("total_bosses_defeated", 0)
        active_evts, upcoming_evts = [], []
        for ev in raw_events:
            eid = ev.get("id", "")
            if "date" in ev:
                s_str = e_str = ev["date"]
            elif "start" in ev and "end" in ev:
                s_str, e_str = ev["start"], ev["end"]
            else:
                continue
            try:
                s_date = _dt.date.fromisoformat(s_str)
                e_date = _dt.date.fromisoformat(e_str)
            except ValueError:
                continue
            is_active = s_date <= today <= e_date
            days_until = (s_date - today).days
            is_upcoming = not is_active and 0 < days_until <= 14
            if today > e_date:
                continue
            condition = ev.get("condition", {})
            ctype = condition.get("type", "none")
            required = condition.get("count") if ctype == "boss_kills" else None
            progress = min(boss_kills, required) if required else None
            is_eligible = (boss_kills >= required) if required else True
            info = {
                "id": eid,
                "name": ev.get("name", ""),
                "description": ev.get("description", ""),
                "start": s_str,
                "end": e_str,
                "reward_type": ev.get("reward_type", ""),
                "reward_item": ev.get("reward_item", ""),
                "reward_amount": ev.get("reward_amount", 0),
                "condition_type": ctype,
                "required": required,
                "progress": progress,
                "is_eligible": is_eligible,
                "is_claimed": eid in claimed,
                "days_remaining": (e_date - today).days + 1 if is_active else None,
                "days_until": days_until if is_upcoming else None,
            }
            if is_active:
                active_evts.append(info)
            elif is_upcoming:
                upcoming_evts.append(info)
        return {"active": active_evts, "upcoming": upcoming_evts}
    events_data = _get_events_display(player)

    # Dungeon data for inline tab
    dungeons_data: dict[str, Any] = GAME_DATA.get("dungeons", {})
    completed_dungeons_set = set(player.get("completed_dungeons", []))
    visited_areas_list = session.get("visited_areas", [area_key])
    dungeon_list = get_available_dungeons(
        dungeons_data, area_key, player.get("level", 1),
        visited_areas=visited_areas_list,
        areas_data=GAME_DATA.get("areas", {}),
    )
    for d in dungeon_list:
        d["completed"] = d.get("id", "") in completed_dungeons_set
    active_dungeon: dict[str, Any] = session.get("active_dungeon") or {}

    ensure_attributes(player)
    attr_summary = get_attribute_summary(player)
    save_player(player)
    return render_template(
        "index.html",
        player=player,
        area=area,
        area_key=area_key,
        area_name=area_name,
        connections=connections,
        shop_items=shop_items,
        shop_name=shop_name,
        inventory_items=inventory_items,
        equipped_details=equipped_details,
        missions=available_missions[:20],
        completed_count=len(completed),
        messages=list(reversed(get_messages()))[:25],
        diary=list(reversed(session.get("diary", []))),
        land_data=land_data,
        active_companions=active_companions,
        companions_available=companions_available,
        game_time=game_time,
        game_time_icon=game_time_icon,
        current_weather=current_weather,
        weather_display=weather_display,
        weather_icon=weather_icon,
        weather_bonus_exp=weather_bonus_exp,
        weather_bonus_gold=weather_bonus_gold,
        challenges=challenges_display,
        available_bosses=available_bosses,
        pending_cutscene=pending_cutscene,
        crafting_recipes=crafting_recipes,
        dungeon_list=dungeon_list,
        active_dungeon=active_dungeon,
        attr_summary=attr_summary,
        read_books=player.get("read_books", []),
        online_user=session.get("online_username"),
        events_data=events_data,
        game_classes=list(GAME_DATA.get("classes", {}).keys()),
        game_races=list(GAME_DATA.get("races", {}).keys()),
        world_events=list(reversed(_world_events[-10:])) if session.get("online_username") else [],
        online_count=len(set(_chat_online.values())),
    )


def _item_stat_summary(item_data):
    if not isinstance(item_data, dict):
        return ""
    parts = []
    itype = item_data.get("type", "")

    # Core stat bonuses/penalties (all equippable types)
    for bonus_key, label in [
        ("attack_bonus", "ATK"),
        ("defense_bonus", "DEF"),
        ("speed_bonus", "SPD"),
        ("hp_bonus", "HP"),
        ("mp_bonus", "MP"),
        ("spell_power_bonus", "SpellPwr"),
        ("spell_power", "SpellPwr"),
        ("defense_penalty", "-DEF"),
        ("speed_penalty", "-SPD"),
    ]:
        val = item_data.get(bonus_key)
        if val:
            sign = "+" if "penalty" not in bonus_key else "-"
            parts.append(f"{sign}{abs(int(val))} {label}")

    # Weapon-specific stats
    if itype == "weapon":
        for bonus_key, label in [
            ("sharpness", "Sharp"),
            ("smiting", "Smite"),
            ("fire_attack", "Fire"),
            ("ice_attack", "Ice"),
            ("lightning_attack", "Lightning"),
            ("poison_attack", "Poison"),
        ]:
            val = item_data.get(bonus_key)
            if val:
                parts.append(f"+{int(val)} {label}")

        # Weapon-type proc attributes
        wtype = item_data.get("weapon_type", "")
        for proc_key, label in [
            ("crit_chance", "Crit"),
            ("bleed_chance", "Bleed"),
            ("stun_chance", "Stun"),
            ("sweep_chance", "Sweep"),
            ("knockback_chance", "Knockback"),
            ("armor_penetration", "ArmorPen"),
            ("armor_crush", "ArmorCrush"),
            ("cleave_chance", "Cleave"),
            ("parry_chance", "Parry"),
            ("backstab_bonus", "Backstab"),
            ("multi_hit_chance", "MultiHit"),
            ("inspire_chance", "Inspire"),
            ("harmony_bonus", "Harmony"),
            ("mana_efficiency", "ManaEff"),
        ]:
            val = item_data.get(proc_key)
            if val:
                parts.append(f"{val}% {label}" if "chance" in proc_key or proc_key == "armor_penetration" or proc_key == "mana_efficiency" else f"+{val} {label}")

    # Armor-specific stats
    elif itype == "armor":
        armor_type = item_data.get("armor_type", "")
        if armor_type:
            parts.append(f"[{armor_type.title()}]")
        eva = item_data.get("evasion_bonus", 0)
        if eva:
            parts.append(f"+{eva}% Evasion")
        for res_key, label in [
            ("physical_resistance", "PhysRes"),
            ("fire_resistance", "FireRes"),
            ("ice_resistance", "IceRes"),
            ("lightning_resistance", "LightRes"),
            ("poison_resistance", "PoisonRes"),
            ("magic_resistance", "MagicRes"),
        ]:
            val = item_data.get(res_key, 0)
            if val:
                parts.append(f"+{int(val * 100)}% {label}")

    # Consumable effects
    elif itype == "consumable":
        effect = item_data.get("effect")
        min_v = item_data.get("min_value", item_data.get("value", 0))
        max_v = item_data.get("max_value", item_data.get("value", 0))
        value = item_data.get("value", 0)
        duration = item_data.get("duration", 0)
        on_use_buff = item_data.get("on_use_buff")

        if effect == "heal":
            if min_v != max_v:
                parts.append(f"Heals {min_v}–{max_v} HP")
            else:
                parts.append(f"Heals {value} HP")
        elif effect == "mp_restore":
            if min_v != max_v:
                parts.append(f"Restores {min_v}–{max_v} MP")
            else:
                parts.append(f"Restores {value} MP")
        elif effect == "full_restore":
            parts.append("Full HP & MP restore")
        elif effect == "defense_boost":
            parts.append(f"+{value} DEF ({duration} turns)")
        elif effect == "attack_boost":
            parts.append(f"+{value} ATK ({duration} turns)")
        elif effect == "speed_boost":
            parts.append(f"+{value} SPD ({duration} turns)")
        elif effect == "grant_exp":
            parts.append(f"+{value} EXP")
        elif effect == "exp_bonus":
            parts.append(f"+{int(value * 100)}% EXP bonus")
        elif effect and effect not in ("birthday_cake", "grand_feast"):
            parts.append(f"Effect: {effect.replace('_', ' ').title()}")

        if on_use_buff:
            parts.append(f"Applies: {on_use_buff.replace('_', ' ').title()}")

    return ", ".join(parts)


def _get_weapon_combat_effects(player, enemy):
    """
    Calculate bonus elemental/special damage from the player's equipped weapon
    against the current enemy, taking enemy tags into account.
    Returns a list of (bonus_dmg, message) tuples.
    """
    equipment = player.get("equipment", {})
    weapon_name = equipment.get("weapon")
    if not weapon_name:
        return []
    weapon = GAME_DATA["items"].get(weapon_name)
    if not isinstance(weapon, dict):
        return []

    enemy_tags = set(enemy.get("tags", []))
    effects = []

    # ── Sharpness: bonus vs humanoid/beast, reduced vs armored/construct ─────
    sharpness = weapon.get("sharpness", 0)
    if sharpness:
        if "humanoid" in enemy_tags or "beast" in enemy_tags:
            bonus = int(sharpness * 1.5)
            effects.append((bonus, f"Your blade bites deep! +{bonus} sharpness damage."))
        elif "armored" in enemy_tags or "construct" in enemy_tags:
            bonus = max(1, int(sharpness * 0.4))
            effects.append((bonus, f"Your blade skips off the armour. +{bonus} damage."))
        else:
            bonus = sharpness
            effects.append((bonus, f"Your weapon's edge adds {bonus} cutting damage."))

    # ── Smiting: bonus vs undead/demon ───────────────────────────────────────
    smiting = weapon.get("smiting", 0)
    if smiting:
        if "undead" in enemy_tags or "demon" in enemy_tags:
            bonus = int(smiting * 2.5)
            effects.append((bonus, f"Holy power surges! +{bonus} smiting damage vs {enemy['name']}!"))
        elif "holy" in enemy_tags:
            bonus = 0
            effects.append((0, f"Smiting has no effect on holy beings."))
        else:
            bonus = smiting
            effects.append((bonus, f"+{bonus} blessed damage."))

    # ── Fire attack ──────────────────────────────────────────────────────────
    fire_atk = weapon.get("fire_attack", 0)
    if fire_atk:
        if "ice" in enemy_tags or "cold" in enemy_tags:
            bonus = int(fire_atk * 2.0)
            effects.append((bonus, f"Fire melts the ice! +{bonus} fire damage!"))
        elif "fire" in enemy_tags:
            bonus = max(0, int(fire_atk * 0.2))
            if bonus:
                effects.append((bonus, f"The flame barely stings. +{bonus} fire damage."))
        else:
            bonus = fire_atk
            effects.append((bonus, f"Your weapon blazes! +{bonus} fire damage."))

    # ── Ice attack ───────────────────────────────────────────────────────────
    ice_atk = weapon.get("ice_attack", 0)
    if ice_atk:
        if "fire" in enemy_tags or "demon" in enemy_tags:
            bonus = int(ice_atk * 2.0)
            effects.append((bonus, f"Frost shatters the flames! +{bonus} ice damage!"))
        elif "ice" in enemy_tags or "cold" in enemy_tags:
            bonus = max(0, int(ice_atk * 0.2))
            if bonus:
                effects.append((bonus, f"The ice barely chills. +{bonus} ice damage."))
        else:
            bonus = ice_atk
            effects.append((bonus, f"Your weapon freezes! +{bonus} ice damage."))

    # ── Lightning attack ─────────────────────────────────────────────────────
    lightning_atk = weapon.get("lightning_attack", 0)
    if lightning_atk:
        if "armored" in enemy_tags or "construct" in enemy_tags:
            bonus = int(lightning_atk * 1.8)
            effects.append((bonus, f"Lightning conducts through armour! +{bonus} lightning damage!"))
        elif "elemental" in enemy_tags and "lightning" in enemy_tags:
            bonus = max(0, int(lightning_atk * 0.2))
            if bonus:
                effects.append((bonus, f"Lightning feeds the elemental. +{bonus} damage."))
        else:
            bonus = lightning_atk
            effects.append((bonus, f"A bolt of lightning! +{bonus} lightning damage."))

    # ── Poison attack ────────────────────────────────────────────────────────
    poison_atk = weapon.get("poison_attack", 0)
    if poison_atk:
        if "construct" in enemy_tags or "undead" in enemy_tags:
            bonus = max(0, int(poison_atk * 0.3))
            if bonus:
                effects.append((bonus, f"The poison has little effect. +{bonus} damage."))
        elif "beast" in enemy_tags or "humanoid" in enemy_tags:
            bonus = int(poison_atk * 1.4)
            effects.append((bonus, f"Venom courses through! +{bonus} poison damage!"))
        else:
            bonus = poison_atk
            effects.append((bonus, f"Poison seeps in. +{bonus} poison damage."))

    return effects


def _get_weapon_on_hit_procs(player, enemy, enemy_effects):
    """
    Roll weapon-type proc chances and apply status effects to the enemy.
    Returns a list of message strings for the battle log.
    Modifies enemy_effects dict in place.
    """
    equipment = player.get("equipment", {})
    weapon_name = equipment.get("weapon")
    if not weapon_name:
        return []
    weapon = GAME_DATA["items"].get(weapon_name)
    if not isinstance(weapon, dict):
        return []

    messages = []
    wtype = weapon.get("weapon_type", "sword")
    tags = weapon.get("tags", [])
    enemy_tags = set(enemy.get("tags", []))

    def _roll(chance_pct):
        return random.random() * 100 < chance_pct

    # ── Bleed (daggers, throwing, sharp weapons) ──────────────────────────────
    bleed_chance = weapon.get("bleed_chance", 0)
    if bleed_chance and _roll(bleed_chance):
        if "construct" not in enemy_tags and "undead" not in enemy_tags:
            stacks = enemy_effects.get("bleed", {}).get("stacks", 0)
            enemy_effects["bleed"] = {"turns": 4, "damage": 6 + stacks * 2, "stacks": min(stacks + 1, 3)}
            messages.append(f"Your blade opens a deep wound! [{enemy.get('name', 'Enemy')} is bleeding]")

    # ── Stun / Daze (maces, warhammers) ──────────────────────────────────────
    stun_chance = weapon.get("stun_chance", 0)
    if stun_chance and _roll(stun_chance):
        if "construct" not in enemy_tags:
            existing = enemy_effects.get("daze", {}).get("turns", 0)
            enemy_effects["daze"] = {"turns": max(1, existing + 1)}
            messages.append(f"Your crushing blow dazes {enemy.get('name', 'the enemy')}! [Dazed — loses next action]")

    # ── Weaken (axes — armor penetration leaves target exposed) ──────────────
    cleave_chance = weapon.get("cleave_chance", 0)
    if cleave_chance and _roll(cleave_chance):
        pen = weapon.get("armor_penetration", 10)
        existing = enemy_effects.get("weaken", {}).get("turns", 0)
        enemy_effects["weaken"] = {"turns": max(existing, 4), "def_reduction": max(enemy_effects.get("weaken", {}).get("def_reduction", 0), int(pen * 0.6))}
        messages.append(f"Your cleaving strike weakens {enemy.get('name', 'the enemy')}'s defences! [-{int(pen * 0.6)} DEF for 4 turns]")

    # ── Knockback / Shaken (greatswords, warhammers) ──────────────────────────
    knockback_chance = weapon.get("knockback_chance", 0)
    if knockback_chance and _roll(knockback_chance):
        enemy_effects["shaken"] = {"turns": 3, "acc_penalty": 20}
        messages.append(f"{enemy.get('name', 'The enemy')} is knocked back and shaken! [-20% accuracy for 3 turns]")

    # ── Sweep damage (greatswords, warhammers — bonus hit) ────────────────────
    sweep_chance = weapon.get("sweep_chance", 0)
    if sweep_chance and _roll(sweep_chance):
        sweep_dmg = max(1, int(player.get("attack", 10) * 0.35))
        enemy["hp"] = max(0, enemy.get("hp", 1) - sweep_dmg)
        messages.append(f"Your sweeping blow strikes again for {sweep_dmg} bonus damage!")

    # ── Multi-hit (throwing weapons) ──────────────────────────────────────────
    multi_hit_chance = weapon.get("multi_hit_chance", 0)
    if multi_hit_chance and _roll(multi_hit_chance):
        hit_dmg = max(1, int(player.get("attack", 10) * 0.25))
        enemy["hp"] = max(0, enemy.get("hp", 1) - hit_dmg)
        messages.append(f"Your second projectile strikes for {hit_dmg} extra damage!")

    # ── Parry (swords — temporary defense buff for player) ────────────────────
    parry_chance = weapon.get("parry_chance", 0)
    if parry_chance and _roll(parry_chance):
        existing_buffs = player.get("active_buffs", [])
        existing_buffs.append({"name": "Parry", "duration": 2, "modifiers": {"defense_bonus": 10, "absorb_amount": 15}})
        player["active_buffs"] = existing_buffs
        messages.append("You deflect the next blow with expert swordsmanship! [Parry: +10 DEF, absorbs 15 dmg for 2 turns]")

    # ── Inspire (bard instruments) ────────────────────────────────────────────
    inspire_chance = weapon.get("inspire_chance", 0)
    if inspire_chance and _roll(inspire_chance):
        inspire_bonus = weapon.get("harmony_bonus", 8)
        existing_buffs = player.get("active_buffs", [])
        existing_buffs.append({"name": "Inspire", "duration": 6, "modifiers": {"attack_bonus": inspire_bonus, "speed_bonus": int(inspire_bonus * 0.5)}})
        player["active_buffs"] = existing_buffs
        messages.append(f"Your melody inspires courage! [+{inspire_bonus} ATK, +{int(inspire_bonus * 0.5)} SPD for 6 turns]")

    # ── Armor Crush (maces — reduces enemy effective defense) ─────────────────
    armor_crush = weapon.get("armor_crush", 0)
    if armor_crush and _roll(20):
        existing = enemy_effects.get("armor_crushed", {}).get("def_reduction", 0)
        enemy_effects["armor_crushed"] = {"turns": 5, "def_reduction": existing + armor_crush}
        messages.append(f"You crush through the armour! [{enemy.get('name', 'Enemy')} defence -{armor_crush} for 5 turns]")

    # ── Backstab (daggers — only if enemy is not yet in combat or is shaken) ──
    backstab_bonus = weapon.get("backstab_bonus", 0)
    if backstab_bonus and ("shaken" in enemy_effects or "daze" in enemy_effects):
        enemy["hp"] = max(0, enemy.get("hp", 1) - backstab_bonus)
        messages.append(f"You exploit the opening for a deadly backstab! +{backstab_bonus} bonus damage!")

    return messages


def _check_weapon_accuracy(player, enemy):
    """
    Returns True if the attack hits, False if it misses.
    Uses weapon aim_accuracy vs enemy speed.
    """
    equipment = player.get("equipment", {})
    weapon_name = equipment.get("weapon")
    if not weapon_name:
        return True
    weapon = GAME_DATA["items"].get(weapon_name)
    if not isinstance(weapon, dict):
        return True
    base_acc = weapon.get("aim_accuracy", 85) / 100.0
    enemy_speed = enemy.get("speed", 10)
    player_speed = player.get("speed", 10)
    dodge_factor = max(0.0, min(0.25, (enemy_speed - player_speed) * 0.015))
    hit_chance = max(0.55, base_acc - dodge_factor)
    return random.random() < hit_chance


def _companion_stat_summary(comp_data):
    if not isinstance(comp_data, dict):
        return ""
    parts = []
    for bonus_key, label in [
        ("attack_bonus", "ATK"),
        ("defense_bonus", "DEF"),
        ("speed_bonus", "SPD"),
        ("hp_bonus", "HP"),
        ("mp_bonus", "MP"),
        ("spell_power_bonus", "SpellPwr"),
        ("crit_chance", "Crit%"),
        ("crit_damage_bonus", "CritDmg%"),
        ("healing_bonus", "HealAura"),
        ("post_battle_heal", "PostHeal"),
    ]:
        val = comp_data.get(bonus_key)
        if val:
            parts.append(f"+{int(val)} {label}")
    return ", ".join(parts)


# ─── Cutscene API ─────────────────────────────────────────────────────────────


@app.route("/api/dismiss_cutscene", methods=["POST"])
def dismiss_cutscene():
    cutscene_id = session.pop("pending_cutscene", None)
    if cutscene_id:
        seen = session.get("seen_cutscenes", [])
        if cutscene_id not in seen:
            seen.append(cutscene_id)
        session["seen_cutscenes"] = seen
        session.modified = True
    return jsonify({"ok": True})


@app.route("/api/spend_attr_point", methods=["POST"])
def api_spend_attr_point():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."})
    ensure_attributes(player)
    data = request.get_json(force=True, silent=True) or {}
    attr = data.get("attr", "")
    result = spend_attribute_point(player, attr)
    if result["ok"]:
        save_player(player)
    attr_summary = get_attribute_summary(player)
    return jsonify(
        {
            "ok": result["ok"],
            "message": result["message"],
            "attr_summary": attr_summary,
            "player_stats": {
                "attack": player.get("attack", 0),
                "defense": player.get("defense", 0),
                "speed": player.get("speed", 0),
                "max_hp": player.get("max_hp", 0),
                "max_mp": player.get("max_mp", 0),
            },
        }
    )


# ─── Exploration ─────────────────────────────────────────────────────────────


@app.route("/action/explore", methods=["POST"])
def action_explore():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    possible_enemies = area.get("possible_enemies", [])
    possible_bosses = area.get("possible_bosses", [])

    player["explore_count"] = player.get("explore_count", 0) + 1
    advance_crops(player)
    advance_game_time(player)
    apply_regen_effects(player)

    current_weather = get_real_weather(area.get("name", ""))

    # Boss encounter: 8% chance if area has bosses
    if possible_bosses and random.random() < 0.08:
        boss_key = random.choice(possible_bosses)
        boss_data = GAME_DATA.get("bosses", {}).get(boss_key, {})
        if boss_data:
            lvl = player["level"]
            scale = 1 + (lvl - 1) * 0.12
            enemy = {
                "key": boss_key,
                "name": boss_data.get("name", boss_key.replace("_", " ").title()),
                "hp": int(boss_data.get("hp", 200) * scale),
                "max_hp": int(boss_data.get("hp", 200) * scale),
                "attack": int(boss_data.get("attack", 20) * scale),
                "defense": int(boss_data.get("defense", 10) * scale),
                "speed": boss_data.get("speed", 12),
                "exp_reward": int(boss_data.get("experience_reward", 200) * scale),
                "gold_reward": int(boss_data.get("gold_reward", 100) * scale),
                "loot_table": boss_data.get("unique_loot", []),
                "is_boss": True,
                "tags": boss_data.get("tags", ["humanoid"]),
            }
            dialogue = get_boss_dialogue(boss_key, "start")
            session["battle_enemy"] = enemy
            session["battle_log"] = [
                f"{enemy['name']} blocks your path! Prepare for a boss battle! (HP: {enemy['hp']})"
            ]
            if dialogue:
                session["battle_log"].append(f'"{dialogue}"')
            session["battle_player_effects"] = {}
            session["battle_enemy_effects"] = {}
            session["battle_companions"] = _build_battle_companions(player)
            _set_activity(player, f"battling {enemy['name']} [Boss]")
            session.modified = True
            save_player(player)
            return redirect(url_for("game"))

    roll = random.random()
    if possible_enemies and roll < 0.55:
        enemy_key = random.choice(possible_enemies)
        enemy_data = GAME_DATA["enemies"].get(enemy_key, {})
        if not isinstance(enemy_data, dict):
            enemy_data = {}
        lvl = player["level"]
        scale = 1 + (lvl - 1) * 0.12
        enemy = {
            "key": enemy_key,
            "name": enemy_data.get("name", enemy_key.replace("_", " ").title()),
            "hp": int(enemy_data.get("hp", 50) * scale),
            "max_hp": int(enemy_data.get("hp", 50) * scale),
            "attack": int(enemy_data.get("attack", 10) * scale),
            "defense": int(enemy_data.get("defense", 5) * scale),
            "speed": enemy_data.get("speed", 10),
            "exp_reward": int(enemy_data.get("experience_reward", 30) * scale),
            "gold_reward": max(
                1, int(enemy_data.get("gold_reward", 10)) + dice.between(-3, 10)
            ),
            "loot_table": enemy_data.get("loot_table", []),
            "tags": enemy_data.get("tags", ["humanoid"]),
        }
        session["battle_enemy"] = enemy
        session["battle_log"] = [
            f"A {enemy['name']} emerges from the shadows! (HP: {enemy['hp']})"
        ]
        session["battle_player_effects"] = {}
        session["battle_enemy_effects"] = {}
        session["battle_companions"] = _build_battle_companions(player)
        _set_activity(player, f"fighting a {enemy['name']}")
        session.modified = True
        save_player(player)
        return redirect(url_for("game"))

    # ── NPC Encounter (20% chance in areas with NPCs, no battle)
    area_npcs = area.get("npcs", [])
    npc_talked = False
    if area_npcs and random.random() < 0.20:
        npc = random.choice(area_npcs)
        npc_name = npc.get("name", "Stranger")
        dialogue = random.choice(npc.get("dialogues", ["..."]))
        add_message(f"You encounter {npc_name}.", "var(--gold)")
        add_message(f'"{dialogue}"', "var(--text-light)")

        # Quest unlock via NPC dialogue
        quest_unlock = npc.get("quest_unlock")
        if quest_unlock:
            completed_missions = session.get("completed_missions", [])
            npc_unlocked = session.get("npc_unlocked_quests", [])
            mission_info = GAME_DATA["missions"].get(quest_unlock, {})
            if (
                quest_unlock not in completed_missions
                and quest_unlock not in npc_unlocked
                and mission_info
            ):
                npc_unlocked.append(quest_unlock)
                session["npc_unlocked_quests"] = npc_unlocked
                mission_name = mission_info.get("name", quest_unlock)
                add_message(
                    f"New quest unlocked: {mission_name}!", "var(--green-bright)"
                )
        npc_talked = True

    # ── Random Explore Events (one event per explore)
    if not npc_talked:
        explore_event_roll = random.random()
        if explore_event_roll < 0.08:
            # Trap!
            dmg = dice.between(5, max(6, player.get("level", 1) * 3))
            player["hp"] = max(1, player["hp"] - dmg)
            add_message(
                f"You trigger a hidden trap! You take {dmg} damage.", "var(--red)"
            )
        elif explore_event_roll < 0.14:
            # Ancient shrine — restore MP
            mp_restore = dice.between(10, 30)
            player["mp"] = min(player["max_mp"], player["mp"] + mp_restore)
            add_message(
                f"You find an ancient shrine and meditate. +{mp_restore} MP restored.",
                "var(--mana-bright,#7eb8f7)",
            )
        elif explore_event_roll < 0.19:
            # Mysterious tome — bonus EXP
            exp_bonus = dice.between(15, 40)
            player["exp"] = player.get("exp", 0) + exp_bonus
            add_message(
                f"You discover a worn tome. Studying it grants you +{exp_bonus} EXP.",
                "var(--gold)",
            )
        elif explore_event_roll < 0.23:
            # Abandoned camp — find multiple items
            finds = random.choice(
                [
                    ["Health Potion"],
                    ["Mana Potion"],
                    ["Health Potion", "Rope"],
                    ["Iron Arrow", "Iron Arrow"],
                ]
            )
            for item in finds:
                player["inventory"].append(item)
            add_message(
                f"You find an abandoned camp with supplies: {', '.join(finds)}.",
                "var(--text-light)",
            )

    # ── Non-combat exploration outcomes
    # 30% chance to find gold (5-20)
    if random.random() < 0.30:
        gold_found = dice.between(5, 20)
        player["gold"] += gold_found
        add_message(
            f"You spot {gold_found} gold coins glinting on the ground.", "var(--gold)"
        )

    # 40% chance to gather crafting materials
    if random.random() < 0.40:
        difficulty = area.get("difficulty", 1)
        tier = max(1, min(difficulty, 5))
        mats = MATERIALS_BY_TIER.get(tier, MATERIALS_BY_TIER[1])
        num = dice.roll_1d(3)
        gathered = random.choices(mats, k=num)
        for mat in gathered:
            player["inventory"].append(mat)
        mat_str = ", ".join(gathered)
        add_message(f"You gather materials: {mat_str}.", "var(--green-bright)")

    # Other exploration outcomes — WIS boosts item find thresholds
    discovery_bonus = player.get("attr_discovery", 0.0)
    roll2 = random.random()
    if roll2 < 0.20:
        heal = dice.between(10, 30)
        player["hp"] = min(player["max_hp"], player["hp"] + heal)
        add_message(
            f"You discover a healing herb and recover {heal} HP.", "var(--green-bright)"
        )
    elif roll2 < min(0.60, 0.35 + discovery_bonus):
        player["inventory"].append("Health Potion")
        add_message(
            "You find a discarded Health Potion on the ground.", "var(--text-light)"
        )
    elif roll2 < 0.50:
        add_message(
            "You explore thoroughly but encounter no danger.", "var(--text-dim)"
        )
    else:
        add_message("The area is quiet. You keep your senses sharp.", "var(--text-dim)")

    save_player(player)
    return redirect(url_for("game"))


@app.route("/action/rest", methods=["POST"])
def action_rest():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})

    if not area.get("can_rest", False):
        add_message("There is nowhere suitable to rest here.", "var(--red)")
        return redirect(url_for("game"))

    cost = area.get("rest_cost", 10)
    if cost > 0 and player["gold"] < cost:
        add_message(f"You need {cost} gold coins to rest here.", "var(--red)")
        return redirect(url_for("game"))

    player["gold"] = player["gold"] - cost
    player["hp"] = player["max_hp"]
    player["mp"] = player["max_mp"]
    advance_crops(player)
    advance_game_time(player)
    apply_regen_effects(player)

    if cost > 0:
        add_message(
            f"You rest for {cost} gold. HP and MP fully restored.",
            "var(--green-bright)",
        )
    else:
        add_message(
            "You rest peacefully on your land. HP and MP restored.",
            "var(--green-bright)",
        )

    area_name = area.get("name", area_key.replace("_", " ").title())
    _set_activity(player, f"resting in {area_name}")
    save_player(player)
    return redirect(url_for("game"))


@app.route("/action/travel", methods=["POST"])
def action_travel():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    dest_key = request.form.get("dest", "")
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})

    if dest_key in area.get("connections", []):
        session["current_area"] = dest_key
        dest_area = GAME_DATA["areas"].get(dest_key, {})
        dest_name = dest_area.get("name", dest_key.replace("_", " ").title())
        visited = session.get("visited_areas", [])
        first_visit = dest_key not in visited
        if first_visit:
            visited.append(dest_key)
            session["visited_areas"] = visited
            # Trigger cutscene if area has one
            cs_id = dest_area.get("first_time_enter_cutscene")
            if cs_id:
                trigger_cutscene(cs_id)
        add_message(f"You travel to {dest_name}.", "var(--wood-light)")
        _set_activity(player, f"wandering {dest_name}")

        # Show up to 3 random online players with their current activity
        my_username = session.get("online_username")
        online_usernames = set(_chat_online.values()) - {my_username}
        if online_usernames:
            try:
                from utilities.supabase_db import get_all_activities
                activities = get_all_activities(exclude_user_id=session.get("online_user_id"))
                # Filter to only currently connected users
                active = [a for a in activities if a["player_name"] in online_usernames]
                random.shuffle(active)
                for entry in active[:3]:
                    name = entry["player_name"]
                    status = entry.get("activity_status", "exploring")
                    add_message(f"You spot {name} — {status}.", "var(--mana-bright)")
            except Exception:
                # Fallback: just show names without activity
                spotted = random.sample(sorted(online_usernames), min(3, len(online_usernames)))
                if len(spotted) == 1:
                    who = spotted[0]
                elif len(spotted) == 2:
                    who = f"{spotted[0]} and {spotted[1]}"
                else:
                    who = f"{spotted[0]}, {spotted[1]}, and {spotted[2]}"
                add_message(f"You spot {who} here.", "var(--mana-bright)")

        session.modified = True
    else:
        add_message("That path is not accessible from here.", "var(--red)")

    save_player(player)
    _autosave()
    return redirect(url_for("game"))


# ─── Manual Boss Challenge ─────────────em�t��──────────────────────────────────────


@app.route("/action/challenge_boss", methods=["POST"])
def action_challenge_boss():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    boss_key = request.form.get("boss_key", "")
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})

    if boss_key not in area.get("possible_bosses", []):
        add_message("That boss is not available in this area.", "var(--red)")
        return redirect(url_for("game"))

    boss_data = GAME_DATA["bosses"].get(boss_key, {})
    if not boss_data:
        add_message("Unknown boss.", "var(--red)")
        return redirect(url_for("game"))

    # Check cooldown
    now_ts = _time_module.time()
    boss_cooldowns = player.get("boss_cooldowns", {})
    cooldown_until = boss_cooldowns.get(boss_key, 0)
    if now_ts < cooldown_until:
        remaining = int(cooldown_until - now_ts)
        h = remaining // 3600
        m = (remaining % 3600) // 60
        add_message(
            f"{boss_data.get('name')} is not ready to fight yet. Cooldown: {h}h {m}m.",
            "var(--red)",
        )
        return redirect(url_for("game"))

    # Set cooldown
    boss_cooldowns[boss_key] = now_ts + BOSS_CHALLENGE_COOLDOWN
    player["boss_cooldowns"] = boss_cooldowns

    lvl = player["level"]
    scale = 1 + (lvl - 1) * 0.12
    enemy = {
        "key": boss_key,
        "name": boss_data.get("name", boss_key.replace("_", " ").title()),
        "hp": int(boss_data.get("hp", 200) * scale),
        "max_hp": int(boss_data.get("hp", 200) * scale),
        "attack": int(boss_data.get("attack", 20) * scale),
        "defense": int(boss_data.get("defense", 10) * scale),
        "speed": boss_data.get("speed", 12),
        "exp_reward": int(boss_data.get("experience_reward", 200) * scale),
        "gold_reward": int(boss_data.get("gold_reward", 100) * scale),
        "loot_table": boss_data.get("unique_loot", []),
        "is_boss": True,
        "tags": boss_data.get("tags", ["humanoid"]),
    }
    dialogue = get_boss_dialogue(boss_key, "start")
    session["battle_enemy"] = enemy
    session["battle_log"] = [
        f"You challenge {enemy['name']}! Prepare yourself! (HP: {enemy['hp']})"
    ]
    if dialogue:
        session["battle_log"].append(f'"{dialogue}"')
    session["battle_player_effects"] = {}
    session["battle_enemy_effects"] = {}
    session["battle_companions"] = _build_battle_companions(player)
    session.modified = True
    save_player(player)
    return redirect(url_for("game"))


@app.route("/action/buy", methods=["POST"])
def action_buy():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    item_name = request.form.get("item", "")
    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict):
        item_data = {}
    base_price = item_data.get("price", item_data.get("value", 20))
    discount = min(0.50, player.get("attr_gold_discount", 0.0))
    price = max(1, int(base_price * (1.0 - discount)))

    if player["gold"] < price:
        add_message(f"You cannot afford {item_name}. Cost: {price} gold.", "var(--red)")
    else:
        player["gold"] -= price
        player["inventory"].append(item_name)
        if discount > 0:
            add_message(
                f"You purchase {item_name} for {price} gold (discount: {int(discount * 100)}%).",
                "var(--gold)",
            )
        else:
            add_message(f"You purchase {item_name} for {price} gold.", "var(--gold)")

    area_name = GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "a shop")
    _set_activity(player, f"shopping in {area_name}")
    save_player(player)
    _autosave()
    return redirect(url_for("game"))


@app.route("/action/sell", methods=["POST"])
def action_sell():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    item_name = request.form.get("item", "")
    if item_name in player["inventory"]:
        item_data = GAME_DATA["items"].get(item_name, {})
        if not isinstance(item_data, dict):
            item_data = {}
        sell_price = max(
            1, int(item_data.get("price", item_data.get("value", 10)) * 0.5)
        )
        player["inventory"].remove(item_name)
        player["gold"] += sell_price
        add_message(f"You sell {item_name} for {sell_price} gold.", "var(--gold)")
    else:
        add_message("You do not have that item.", "var(--red)")

    _set_activity(player, "selling gear at the shop")
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=inventory")


# ─── Companion System ────────────────────────────────────────────────────────


@app.route("/action/hire_companion", methods=["POST"])
def action_hire_companion():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    if session.get("current_area") != "tavern":
        add_message(
            "You must be at The Rusty Tankard to hire companions.", "var(--red)"
        )
        return redirect(url_for("game"))

    comp_id = request.form.get("companion_id", "")
    comp_data = GAME_DATA["companions"].get(comp_id)
    if not comp_data:
        add_message("Unknown companion.", "var(--red)")
        return redirect(url_for("game"))

    companions = player.setdefault("companions", [])
    if len(companions) >= 4:
        add_message("Your party is full (max 4 companions).", "var(--red)")
        return redirect(url_for("game"))

    if any(c.get("id") == comp_id for c in companions if isinstance(c, dict)):
        add_message(
            f"{comp_data.get('name')} is already in your party.", "var(--text-dim)"
        )
        return redirect(url_for("game"))

    base_price = comp_data.get("price", 100)
    discount = min(0.50, player.get("attr_gold_discount", 0.0))
    price = max(1, int(base_price * (1.0 - discount)))
    if player["gold"] < price:
        add_message(
            f"Not enough gold. Need {price}g to hire {comp_data.get('name')}.",
            "var(--red)",
        )
        return redirect(url_for("game"))

    player["gold"] -= price

    for stat_key in ("attack_bonus", "defense_bonus", "speed_bonus"):
        bonus = comp_data.get(stat_key, 0)
        if bonus:
            stat = stat_key.replace("_bonus", "")
            player[stat] = player.get(stat, 0) + bonus
    for stat_key in ("hp_bonus", "mp_bonus"):
        bonus = comp_data.get(stat_key, 0)
        if bonus:
            stat = stat_key.replace("_bonus", "")
            player[stat] = player.get(stat, 0) + bonus
            player[f"max_{stat}"] = player.get(f"max_{stat}", 0) + bonus
    if comp_data.get("spell_power_bonus", 0):
        player["attr_spell_power"] = player.get("attr_spell_power", 0) + comp_data["spell_power_bonus"]
    if comp_data.get("crit_chance", 0):
        player["attr_crit_chance"] = player.get("attr_crit_chance", 0) + comp_data["crit_chance"]
    if comp_data.get("crit_damage_bonus", 0):
        player["attr_crit_damage"] = player.get("attr_crit_damage", 0) + comp_data["crit_damage_bonus"]
    if comp_data.get("healing_bonus", 0):
        player["attr_healing_bonus"] = player.get("attr_healing_bonus", 0) + comp_data["healing_bonus"]
    if comp_data.get("post_battle_heal", 0):
        player["attr_post_battle_heal"] = player.get("attr_post_battle_heal", 0) + comp_data["post_battle_heal"]

    rank = comp_data.get("rank", "common")
    comp_max_hp = _COMPANION_RANK_HP.get(rank, 400)
    companions.append({
        "id": comp_id,
        "name": comp_data.get("name", comp_id),
        "hp": comp_max_hp,
        "max_hp": comp_max_hp,
    })
    add_message(f"{comp_data.get('name')} joins your party!", "var(--gold)")
    save_player(player)
    return redirect(url_for("game"))


@app.route("/action/dismiss_companion", methods=["POST"])
def action_dismiss_companion():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    comp_id = request.form.get("companion_id", "")
    companions = player.get("companions", [])
    to_remove = next(
        (c for c in companions if isinstance(c, dict) and c.get("id") == comp_id), None
    )

    if not to_remove:
        add_message("Companion not found in your party.", "var(--red)")
        return redirect(url_for("game"))

    comp_data = GAME_DATA["companions"].get(comp_id, {})

    for stat_key in ("attack_bonus", "defense_bonus", "speed_bonus"):
        bonus = comp_data.get(stat_key, 0)
        if bonus:
            stat = stat_key.replace("_bonus", "")
            player[stat] = max(0, player.get(stat, 0) - bonus)
    for stat_key in ("hp_bonus", "mp_bonus"):
        bonus = comp_data.get(stat_key, 0)
        if bonus:
            stat = stat_key.replace("_bonus", "")
            player[stat] = max(1, player.get(stat, 0) - bonus)
            player[f"max_{stat}"] = max(1, player.get(f"max_{stat}", 1) - bonus)
    if comp_data.get("spell_power_bonus", 0):
        player["attr_spell_power"] = max(0, player.get("attr_spell_power", 0) - comp_data["spell_power_bonus"])
    if comp_data.get("crit_chance", 0):
        player["attr_crit_chance"] = max(0, player.get("attr_crit_chance", 0) - comp_data["crit_chance"])
    if comp_data.get("crit_damage_bonus", 0):
        player["attr_crit_damage"] = max(0, player.get("attr_crit_damage", 0) - comp_data["crit_damage_bonus"])
    if comp_data.get("healing_bonus", 0):
        player["attr_healing_bonus"] = max(0, player.get("attr_healing_bonus", 0) - comp_data["healing_bonus"])
    if comp_data.get("post_battle_heal", 0):
        player["attr_post_battle_heal"] = max(0, player.get("attr_post_battle_heal", 0) - comp_data["post_battle_heal"])

    companions.remove(to_remove)
    player["companions"] = companions

    name = comp_data.get("name", comp_id)
    add_message(f"{name} has left your party.", "var(--text-dim)")
    save_player(player)
    return redirect(url_for("game"))


@app.route("/action/use_item", methods=["POST"])
def action_use_item():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    item_name = request.form.get("item", "")
    if item_name not in player["inventory"]:
        add_message("You do not have that item.", "var(--red)")
        return redirect(url_for("game"))

    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict):
        item_data = {}
    item_type = item_data.get("type", "")

    if item_type in EQUIPPABLE_TYPES:
        ok, msg = equip_item(player, item_name)
        color = "var(--green-bright)" if ok else "var(--red)"
        add_message(msg, color)
        save_player(player)
        return redirect(url_for("game"))

    lower = item_name.lower()
    if "health" in lower or ("potion" in lower and "mana" not in lower):
        heal = dice.between(40, 70)
        if "large" in lower or "greater" in lower:
            heal = dice.between(70, 130)
        player["hp"] = min(player["max_hp"], player["hp"] + heal)
        player["inventory"].remove(item_name)
        add_message(
            f"You drink the {item_name} and recover {heal} HP.", "var(--green-bright)"
        )
    elif "mana" in lower:
        restore = dice.between(25, 50)
        player["mp"] = min(player["max_mp"], player["mp"] + restore)
        player["inventory"].remove(item_name)
        add_message(
            f"You drink the {item_name} and restore {restore} MP.", "var(--mana-bright)"
        )
    elif "elixir" in lower or "tears" in lower:
        heal = dice.between(50, 100)
        player["hp"] = min(player["max_hp"], player["hp"] + heal)
        player["inventory"].remove(item_name)
        add_message(
            f"You use the {item_name} and feel its power (+{heal} HP).", "var(--gold)"
        )
    elif item_data.get("effect") == "birthday_cake":
        heal_amount = player["max_hp"] - player["hp"]
        mp_amount = player["max_mp"] - player["mp"]
        player["hp"] = player["max_hp"]
        player["mp"] = player["max_mp"]
        exp_bonus = int(item_data.get("exp_bonus", 0))
        leveled = gain_experience(player, exp_bonus) if exp_bonus else False
        player["inventory"].remove(item_name)
        add_message(
            f"You eat a slice of the {item_name}. It is, without exaggeration, the greatest thing you have ever tasted. "
            f"Fully restored (+{heal_amount} HP, +{mp_amount} MP) and granted {exp_bonus:,} EXP in honour of Andrew's birthday. "
            f"Happy Birthday, Primordial One!",
            "var(--gold)",
        )
        if leveled:
            add_message(
                f"The birthday magic carries you to level {player['level']}! Andrew's gift keeps giving.",
                "var(--gold)",
            )
    elif item_data.get("effect") == "grant_exp":
        exp_grant = int(item_data.get("value", 0))
        player["inventory"].remove(item_name)
        leveled = gain_experience(player, exp_grant)
        add_message(
            f"You consume the {item_name}. A torrent of cosmic power surges through you, granting {exp_grant:,} EXP!",
            "var(--gold)",
        )
        if leveled:
            add_message(
                f"You have reached level {player['level']}! The cosmos recognises your ascension.",
                "var(--gold)",
            )
    elif item_data.get("effect") == "grand_feast":
        heal_amount = player["max_hp"] - player["hp"]
        mp_amount = player["max_mp"] - player["mp"]
        player["hp"] = player["max_hp"]
        player["mp"] = player["max_mp"]
        regen_hp = int(item_data.get("regen_hp", 50))
        regen_mp = int(item_data.get("regen_mp", 30))
        regen_turns = int(item_data.get("regen_turns", 10))
        player.setdefault("regen_effects", []).append({
            "hp_per_turn": regen_hp,
            "mp_per_turn": regen_mp,
            "turns_remaining": regen_turns,
            "source": item_name,
        })
        player["inventory"].remove(item_name)
        add_message(
            f"You devour the {item_name} — a divine banquet fit for the gods! Fully restored "
            f"(+{heal_amount} HP, +{mp_amount} MP) and a vigorous feast-glow begins regenerating "
            f"+{regen_hp} HP and +{regen_mp} MP per turn for {regen_turns} turns.",
            "var(--gold)",
        )
    elif item_type == "book":
        return redirect(url_for("action_read_book") + f"?item={item_name}")
    elif item_type == "consumable":
        # Generic effect-driven consumable handling
        effect = item_data.get("effect", "")
        value = item_data.get("value", 0)
        min_v = item_data.get("min_value", value)
        max_v = item_data.get("max_value", value)
        duration = item_data.get("duration", 0)
        on_use_buff = item_data.get("on_use_buff", "")
        consumed = True

        if effect == "heal":
            heal = dice.between(min_v, max_v) if min_v != max_v else value
            player["hp"] = min(player["max_hp"], player["hp"] + heal)
            add_message(f"You use the {item_name} and recover {heal} HP.", "var(--green-bright)")
        elif effect == "mp_restore":
            restore = dice.between(min_v, max_v) if min_v != max_v else value
            player["mp"] = min(player["max_mp"], player["mp"] + restore)
            add_message(f"You use the {item_name} and restore {restore} MP.", "var(--mana-bright)")
        elif effect == "full_restore":
            healed = player["max_hp"] - player["hp"]
            mped = player["max_mp"] - player["mp"]
            player["hp"] = player["max_hp"]
            player["mp"] = player["max_mp"]
            add_message(f"You use the {item_name}. Fully restored! (+{healed} HP, +{mped} MP)", "var(--gold)")
        elif on_use_buff:
            effects_data = GAME_DATA.get("effects", {})
            buff_def = effects_data.get(on_use_buff, {})
            dur = duration or buff_def.get("duration", 5)
            mods = {k: v for k, v in buff_def.items() if k not in ("description", "type", "duration", "tags")}
            player.setdefault("active_buffs", []).append({"name": on_use_buff.replace("_", " ").title(), "duration": dur, "modifiers": mods})
            add_message(f"You use the {item_name}. {buff_def.get('description', 'A buff is applied!')} ({dur} turns)", "var(--green-bright)")
        else:
            consumed = False
            add_message(f"You cannot use {item_name} outside of battle.", "var(--text-dim)")

        if consumed:
            player["inventory"].remove(item_name)
    else:
        add_message(f"You cannot use {item_name} outside of battle.", "var(--text-dim)")

    _set_activity(player, "using a consumable item")
    save_player(player)
    _autosave()
    return redirect(url_for("game"))


@app.route("/action/quick_heal", methods=["POST"])
def action_quick_heal():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    inventory = player.get("inventory", [])
    heal_keywords = ["health", "elixir", "tears", "tonic"]
    potions = [
        i for i in inventory
        if any(x in i.lower() for x in heal_keywords)
        and "mana" not in i.lower()
    ]

    if not potions:
        add_message("You have no healing items to use.", "var(--red)")
        save_player(player)
        return redirect(url_for("game"))

    def potion_priority(name):
        n = name.lower()
        if "large" in n or "greater" in n or "elixir" in n or "tears" in n:
            return 2
        return 1

    best = max(potions, key=potion_priority)
    lower = best.lower()
    if "elixir" in lower or "tears" in lower:
        heal = dice.between(50, 100)
    elif "large" in lower or "greater" in lower:
        heal = dice.between(70, 130)
    else:
        heal = dice.between(40, 70)

    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    player["inventory"].remove(best)
    add_message(f"Quick Heal: used {best} and recovered {heal} HP.", "var(--green-bright)")
    _set_activity(player, "healing up between battles")
    save_player(player)
    _autosave()
    return redirect(url_for("game"))


@app.route("/action/sort_inventory", methods=["POST"])
def action_sort_inventory():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    items_data = GAME_DATA["items"]

    def sort_key(name):
        data = items_data.get(name, {})
        if not isinstance(data, dict):
            return (99, name)
        type_order = {
            "weapon": 0, "armor": 1, "offhand": 2, "accessory": 3,
            "consumable": 4, "book": 5, "material": 6
        }
        t = data.get("type", "misc")
        return (type_order.get(t, 10), name.lower())

    player["inventory"] = sorted(player.get("inventory", []), key=sort_key)
    add_message("Inventory sorted by type.", "var(--text-dim)")
    save_player(player)
    return redirect(url_for("game") + "?tab=character")


@app.route("/action/read_book", methods=["GET", "POST"])
def action_read_book():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    item_name = request.values.get("item", "")
    if item_name not in player.get("inventory", []):
        add_message("You do not have that book.", "var(--red)")
        return redirect(url_for("game"))

    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict) or item_data.get("type") != "book":
        add_message("That item cannot be read.", "var(--red)")
        return redirect(url_for("game"))

    book_key = item_data.get("book_key", "")
    book_meta = GAME_DATA["books"].get(book_key, {})
    book_file = book_meta.get("file", "")

    content = "(The pages of this book are damaged beyond reading.)"
    if book_file:
        try:
            with open(os.path.join(DATA_DIR, book_file), "r", encoding="utf-8") as bf:
                content = bf.read()
        except OSError:
            pass

    read_books = player.setdefault("read_books", [])
    already_read = book_key and book_key in read_books
    if book_key and not already_read:
        read_books.append(book_key)
        add_message(f"You read \"{item_name}\" and add it to your library.", "var(--gold)")

    save_player(player)
    return render_template(
        "book.html",
        book_title=book_meta.get("title", item_name),
        book_author=book_meta.get("author", "Unknown"),
        book_description=book_meta.get("description", ""),
        book_content=content,
        already_read=already_read,
        item_name=item_name,
    )


@app.route("/action/equip", methods=["POST"])
def action_equip():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    item_name = request.form.get("item", "")
    ok, msg = equip_item(player, item_name)
    add_message(msg, "var(--green-bright)" if ok else "var(--red)")
    save_player(player)
    return redirect(url_for("game") + "?tab=inventory")


@app.route("/action/unequip", methods=["POST"])
def action_unequip():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    slot = request.form.get("slot", "")
    ok, msg = unequip_item(player, slot)
    add_message(msg, "var(--text-dim)" if ok else "var(--red)")
    save_player(player)
    return redirect(url_for("game") + "?tab=inventory")


@app.route("/action/auto_equip", methods=["POST"])
def action_auto_equip():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    msgs = auto_equip_best(player)
    for msg in msgs:
        add_message(msg, "var(--green-bright)")
    save_player(player)
    return redirect(url_for("game") + "?tab=inventory")


# ─── Missions ─────────────────────────────────────────────────────────────────


@app.route("/action/complete_mission", methods=["POST"])
def action_complete_mission():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    mission_id = request.form.get("mission_id", "")
    completed = session.get("completed_missions", [])

    if mission_id in completed:
        add_message("That mission is already completed.", "var(--text-dim)")
        return redirect(url_for("game"))

    can_complete, reason = check_mission_completable(mission_id, player)
    if not can_complete:
        add_message(f"Cannot complete mission: {reason}", "var(--red)")
        return redirect(url_for("game"))

    mission = GAME_DATA["missions"].get(mission_id, {})

    # Trigger mission accept cutscene on first ever mission completion
    if not completed:
        trigger_cutscene("mission_accept_tutorial")

    completed.append(mission_id)
    session["completed_missions"] = completed

    reward = mission.get("reward", {})
    exp = reward.get("experience", mission.get("experience_reward", 0))
    gold = reward.get("gold", mission.get("gold_reward", 0))
    item_rewards = reward.get("items", [])

    player["gold"] += gold
    leveled = gain_experience(player, exp)
    _group_contribute(exp, gold, f"completed quest: {mission.get('name', mission_id)}")

    for item in item_rewards:
        player["inventory"].append(item)

    add_message(f"Quest Complete: {mission.get('name', mission_id)}", "var(--gold)")
    add_message(f"Reward: +{exp} EXP, +{gold} gold.", "var(--text-light)")
    if item_rewards:
        add_message(f"Items received: {', '.join(item_rewards)}", "var(--gold-bright)")
    if leveled:
        add_message(
            f"Level Up! You are now level {player['level']}! You gained 3 attribute points (Equipment tab).",
            "var(--gold)",
        )

    # Update weekly challenge
    update_weekly_challenge(player, "mission_count", 1)

    quest_progress: dict[str, Any] = session.get("quest_progress") or {}
    quest_progress.pop(mission_id, None)
    session["quest_progress"] = quest_progress

    _set_activity(player, f"completing quest: {mission.get('name', mission_id)}")
    save_player(player)
    _autosave()
    return redirect(url_for("game"))


# ─── Weekly Challenges ────────────────────────────────────────────────────────


@app.route("/action/claim_challenge", methods=["POST"])
def action_claim_challenge():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    ch_id = request.form.get("challenge_id", "")
    ch_def = next((c for c in GAME_DATA["weekly_challenges"] if c.get("id") == ch_id), None)
    if not ch_def:
        add_message("Unknown challenge.", "var(--red)")
        return redirect(url_for("game") + "#challenges")

    ch_prog = player.setdefault("weekly_challenges_progress", {})
    prog = ch_prog.get(ch_id, {})

    if prog.get("claimed"):
        add_message("Challenge already claimed.", "var(--text-dim)")
        return redirect(url_for("game") + "#challenges")

    count = prog.get("count", 0)
    target = ch_def.get("target", 0)
    if count < target:
        add_message(f"Challenge not yet completed ({count}/{target}).", "var(--red)")
        return redirect(url_for("game") + "#challenges")

    exp = ch_def.get("reward_exp", 0)
    gold = ch_def.get("reward_gold", 0)
    player["gold"] += gold
    leveled = gain_experience(player, exp)
    _group_contribute(exp, gold, f"completed challenge: {ch_def.get('name', ch_id)}")
    ch_prog[ch_id]["claimed"] = True

    add_message(f"Challenge Complete: {ch_def.get('name', ch_id)}!", "var(--gold)")
    add_message(f"Reward: +{exp} EXP, +{gold} gold.", "var(--text-light)")
    if leveled:
        add_message(
            f"Level Up! You are now level {player['level']}! You gained 3 attribute points (Equipment tab).",
            "var(--gold)",
        )

    _set_activity(player, f"claiming challenge: {ch_def.get('name', ch_id)}")
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "#challenges")


# ─── Your Land Routes ────────────────────────────────────────────────────────


@app.route("/action/land/buy_housing", methods=["POST"])
def land_buy_housing():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    h_key = request.form.get("housing_key", "")
    h_data = GAME_DATA["housing"].get(h_key)
    if not h_data:
        add_message("That structure does not exist.", "var(--red)")
        return redirect(url_for("game"))

    base_price = h_data.get("price", 100)
    discount = min(0.50, player.get("attr_gold_discount", 0.0))
    price = max(1, int(base_price * (1.0 - discount)))
    if player["gold"] < price:
        add_message(
            f"Not enough gold. {h_data.get('name', h_key)} costs {price} gold.", "var(--red)"
        )
        save_player(player)
        return redirect(url_for("game"))

    player["gold"] -= price
    owned = player.get("housing_owned", [])
    owned.append(h_key)
    player["housing_owned"] = owned
    add_message(f"You purchase {h_data.get('name', h_key)} for {price} gold.", "var(--gold)")
    _set_activity(player, f"building {h_data.get('name', h_key)} on their land")
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/place_housing", methods=["POST"])
def land_place_housing():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    h_key = request.form.get("housing_key", "")
    slot_id = request.form.get("slot_id", "")

    if h_key not in player.get("housing_owned", []):
        add_message("You do not own that structure.", "var(--red)")
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    h_data = GAME_DATA["housing"].get(h_key, {})
    comfort = h_data.get("comfort_points", 0)
    slots = player.get("building_slots", {})

    if slot_id in slots and slots[slot_id]:
        old_h = GAME_DATA["housing"].get(slots[slot_id], {})
        old_cp = old_h.get("comfort_points", 0)
        player["comfort_points"] = max(0, player.get("comfort_points", 0) - old_cp)

    slots[slot_id] = h_key
    player["building_slots"] = slots
    player["comfort_points"] = player.get("comfort_points", 0) + comfort
    add_message(
        f"You place {h_data.get('name', h_key)} at {slot_id}. +{comfort} comfort",
        "var(--green-bright)",
    )
    save_player(player)
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/remove_housing", methods=["POST"])
def land_remove_housing():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    slot_id = request.form.get("slot_id", "")
    slots = player.get("building_slots", {})

    if slot_id in slots and slots[slot_id]:
        h_key = slots[slot_id]
        h_data = GAME_DATA["housing"].get(h_key, {})
        cp = h_data.get("comfort_points", 0)
        player["comfort_points"] = max(0, player.get("comfort_points", 0) - cp)
        slots[slot_id] = None
        player["building_slots"] = slots
        add_message(
            f"Removed {h_data.get('name', h_key)} from {slot_id}.", "var(--text-dim)"
        )
    else:
        add_message("That slot is already empty.", "var(--text-dim)")

    save_player(player)
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/plant", methods=["POST"])
def land_plant():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    # Require a garden to be built
    building_slots = player.get("building_slots", {})
    has_garden = any(k.startswith("garden") and v for k, v in building_slots.items())
    if not has_garden:
        add_message(
            "You need to build a Garden on your land before you can farm!", "var(--red)"
        )
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    crop_key = request.form.get("crop_key", "")
    slot_id = request.form.get("slot_id", "")
    crops_db = GAME_DATA["farming"].get("crops", {})
    crop_def = crops_db.get(crop_key)

    if not crop_def:
        add_message("Unknown crop.", "var(--red)")
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    crops = player.get("crops", {})
    if crops.get(slot_id, {}).get("crop_key"):
        add_message(
            f"Slot {slot_id} is already occupied. Harvest or clear it first.",
            "var(--red)",
        )
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    crops[slot_id] = {
        "crop_key": crop_key,
        "growth_time": crop_def.get("growth_time", 5),
        "turns": 0,
        "ready": False,
    }
    player["crops"] = crops
    add_message(
        f"You plant {crop_def.get('name', crop_key)} in {slot_id}. Ready in {crop_def.get('growth_time', 5)} turns.",
        "var(--green-bright)",
    )
    save_player(player)
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/harvest", methods=["POST"])
def land_harvest():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    slot_id = request.form.get("slot_id", "")
    crops = player.get("crops", {})
    crop_info = crops.get(slot_id)

    if not crop_info or not crop_info.get("crop_key"):
        add_message("Nothing planted in that slot.", "var(--red)")
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    if not crop_info.get("ready", False):
        turns_left = crop_info.get("growth_time", 5) - crop_info.get("turns", 0)
        add_message(
            f"Crop is not ready yet. About {turns_left} turns remaining.",
            "var(--text-dim)",
        )
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    crops_db = GAME_DATA["farming"].get("crops", {})
    crop_def = crops_db.get(crop_info["crop_key"], {})
    amount = crop_def.get("harvest_amount", 3)
    sell_each = crop_def.get("sell_price", 15)
    gold_earned = amount * sell_each

    player["gold"] += gold_earned
    crops[slot_id] = {}
    player["crops"] = crops
    add_message(
        f"You harvest {amount}x {crop_def.get('name', crop_info['crop_key'])} and earn {gold_earned} gold!",
        "var(--gold)",
    )
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/buy_pet", methods=["POST"])
def land_buy_pet():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    pet_key = request.form.get("pet_key", "")
    pet_data = GAME_DATA["pets"].get(pet_key)

    if not pet_data:
        add_message("Unknown pet.", "var(--red)")
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    price = pet_data.get("price", 500)
    if player["gold"] < price:
        add_message(
            f"Not enough gold. {pet_data.get('name', pet_key)} costs {price} gold.", "var(--red)"
        )
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    if player.get("pet"):
        old_pet = GAME_DATA["pets"].get(player["pet"], {})
        old_price = old_pet.get("price", 500)
        refund = old_price // 2
        player["gold"] += refund
        add_message(
            f"Your old companion ({old_pet.get('name', player['pet'])}) is released. Refund: {refund} gold.",
            "var(--text-dim)",
        )
        for stat, val in old_pet.get("boosts", {}).items():
            if stat in ("attack", "defense", "speed"):
                player[stat] = max(1, player.get(stat, 0) - val)
            elif stat in ("hp", "max_hp"):
                player["max_hp"] = max(1, player.get("max_hp", 0) - val)
            elif stat in ("mp", "max_mp"):
                player["max_mp"] = max(1, player.get("max_mp", 0) - val)

    player["gold"] -= price
    player["pet"] = pet_key
    boosts = pet_data.get("boosts", {})
    for stat, val in boosts.items():
        if stat in ("attack", "defense", "speed"):
            player[stat] = player.get(stat, 0) + val
        elif stat in ("hp", "max_hp"):
            player["max_hp"] = player.get("max_hp", 0) + val
            player["hp"] = min(player["hp"] + val, player["max_hp"])
        elif stat in ("mp", "max_mp"):
            player["max_mp"] = player.get("max_mp", 0) + val
            player["mp"] = min(player["mp"] + val, player["max_mp"])

    add_message(f"You adopt {pet_data.get('name', pet_key)} as your companion!", "var(--gold)")
    if boosts:
        boost_str = ", ".join(
            f"+{v} {k}" for k, v in boosts.items() if isinstance(v, int)
        )
        if boost_str:
            add_message(f"Pet bonus: {boost_str}", "var(--green-bright)")

    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=land")


# ─── Training (Your Land) ─────────────────────────────────────────────────────


@app.route("/action/land/train", methods=["POST"])
def land_train():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    if session.get("current_area") != "your_land":
        add_message("You can only train at Your Land.", "var(--red)")
        return redirect(url_for("game"))

    # Require a training place to be built
    building_slots = player.get("building_slots", {})
    has_training_place = any(
        k.startswith("training_place") and v for k, v in building_slots.items()
    )
    if not has_training_place:
        add_message(
            "You need to build a Training Place on your land first!", "var(--red)"
        )
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    training_key = request.form.get("training_key", "")
    option = TRAINING_OPTIONS.get(training_key)
    if not option:
        add_message("Unknown training option.", "var(--red)")
        return redirect(url_for("game") + "?tab=land")

    cost = option["cost"]
    if player["gold"] < cost:
        add_message(f"Not enough gold. Training costs {cost} gold.", "var(--red)")
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    player["gold"] -= cost
    stat = str(option["stat"])
    gain = option["gain"]
    player[stat] = player.get(stat, 0) + gain
    # If training max_hp, also restore current hp a bit
    if stat == "max_hp":
        player["hp"] = min(player["hp"] + gain, player["max_hp"])
    elif stat == "max_mp":
        player["mp"] = min(player["mp"] + gain, player["max_mp"])

    add_message(
        f"{option['label']} complete! +{gain} {stat.replace('max_', '').upper()} (cost: {cost}g)",
        "var(--green-bright)",
    )
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=land")


# ─── Battle Routes ────────────────────────────────────────────────────────────


@app.route("/battle")
def battle():
    return redirect(url_for("game"))


@app.route("/battle/spell", methods=["POST"])
def battle_spell():
    player = get_player()
    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if not player or not enemy:
        return redirect(url_for("game"))

    spell_name = request.form.get("spell", "")
    spells_data: dict[str, Any] = GAME_DATA["spells"]
    items_data: dict[str, Any] = GAME_DATA["items"]
    weapon = player.get("equipment", {}).get("weapon")
    available_spells = get_available_spells(weapon, items_data, spells_data)
    available_names = [s["name"] for s in available_spells]
    log = session.get("battle_log", [])
    player_effects: dict[str, Any] = session.get("battle_player_effects") or {}
    enemy_effects: dict[str, Any] = session.get("battle_enemy_effects") or {}

    # Process effects at start of turn
    enemy_name = enemy.get("name", "Enemy")
    stunned = process_turn_effects(player, player_effects, log, "You")
    session["battle_player_effects"] = player_effects
    process_turn_effects(enemy, enemy_effects, log, enemy_name)
    session["battle_enemy_effects"] = enemy_effects

    if player["hp"] <= 0:
        return _handle_defeat(player, enemy, log)
    if enemy.get("hp", 1) <= 0:
        return _handle_victory(player, enemy, log)

    if stunned:
        session["battle_log"] = log
        session["battle_enemy"] = enemy
        save_player(player)
        return redirect(url_for("game"))

    if spell_name not in available_names:
        log.append("That spell is unavailable with your current weapon.")
        session["battle_log"] = log
        return redirect(url_for("game"))

    spell_data = spells_data.get(spell_name, {})
    effects_data = spell_data.get("effects_data", {})
    result = cast_spell(player, enemy, spell_name, spell_data, effects_data)

    for msg in result.get("messages", []):
        log.append(msg["text"])

    if not result.get("ok", True):
        session["battle_log"] = log
        save_player(player)
        return redirect(url_for("game"))

    session["battle_enemy"] = enemy

    if enemy.get("hp", 1) <= 0:
        return _handle_victory(player, enemy, log)

    _enemy_take_turn(enemy, player, player_effects, log)

    if player["hp"] <= 0:
        return _handle_defeat(player, enemy, log)

    session["battle_log"] = log
    session["battle_enemy"] = enemy
    session["battle_player_effects"] = player_effects
    session["battle_enemy_effects"] = enemy_effects
    save_player(player)
    return redirect(url_for("game"))


@app.route("/battle/attack", methods=["POST"])
def battle_attack():
    player = get_player()
    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if not player or not enemy:
        return redirect(url_for("game"))

    log = session.get("battle_log", [])
    player_effects: dict[str, Any] = session.get("battle_player_effects") or {}
    enemy_effects: dict[str, Any] = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])

    # Process effects at start of turn
    enemy_name = enemy.get("name", "Enemy")
    stunned = process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(enemy, enemy_effects, log, enemy_name)

    if player["hp"] <= 0:
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        return _handle_defeat(player, enemy, log)
    if enemy.get("hp", 1) <= 0:
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        return _handle_victory(player, enemy, log)

    if not stunned:
        # ── Accuracy check ───────────────────────────────────────────────────
        if not _check_weapon_accuracy(player, enemy):
            log.append(f"You swing at the {enemy_name} but miss!")
        else:
            # Factor in weaken / armor_crushed debuffs on enemy defense
            eff_enemy_def = enemy["defense"]
            weaken_eff = enemy_effects.get("weaken", {})
            if weaken_eff.get("turns", 0) > 0:
                eff_enemy_def = max(0, eff_enemy_def - weaken_eff.get("def_reduction", 0))
            armor_crush_eff = enemy_effects.get("armor_crushed", {})
            if armor_crush_eff.get("turns", 0) > 0:
                eff_enemy_def = max(0, eff_enemy_def - armor_crush_eff.get("def_reduction", 0))

            # Armor penetration ignores a % of remaining defense
            armor_pen_pct = 0
            eq_weapon = GAME_DATA["items"].get(player.get("equipment", {}).get("weapon", ""), {})
            if isinstance(eq_weapon, dict):
                armor_pen_pct = eq_weapon.get("armor_penetration", 0)
            if armor_pen_pct:
                eff_enemy_def = int(eff_enemy_def * (1 - armor_pen_pct / 100.0))

            p_dmg = max(1, player["attack"] - eff_enemy_def + dice.between(-3, 6))
            base_crit_rate = 0.10 + min(0.40, player.get("attr_crit_chance", 0) / 100.0)
            crit = random.random() < base_crit_rate
            if crit:
                crit_mult = 1.6 + player.get("attr_crit_damage", 0) / 100.0
                p_dmg = int(p_dmg * crit_mult)
                log.append(f"CRITICAL STRIKE! You deal {p_dmg} damage to the {enemy_name}!")
            else:
                log.append(f"You attack the {enemy_name} for {p_dmg} damage.")
            enemy["hp"] = max(0, enemy["hp"] - p_dmg)

            # ── Weapon elemental/special effects ─────────────────────────────
            weapon_effects = _get_weapon_combat_effects(player, enemy)
            total_bonus = 0
            for bonus_dmg, bonus_msg in weapon_effects:
                if bonus_dmg > 0:
                    total_bonus += bonus_dmg
                    log.append(bonus_msg)
            if total_bonus > 0:
                enemy["hp"] = max(0, enemy["hp"] - total_bonus)

            # ── On-hit proc effects (bleed, stun, weaken, inspire, etc.) ─────
            proc_msgs = _get_weapon_on_hit_procs(player, enemy, enemy_effects)
            for msg in proc_msgs:
                log.append(msg)

        if enemy["hp"] <= 0:
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            _sync_companion_hp_to_player(player, battle_companions)
            _restore_companion_hp(player)
            return _handle_victory(player, enemy, log)

    _enemy_take_turn(enemy, player, player_effects, log)

    # Companion action
    if enemy["hp"] > 0 and _companion_take_action(battle_companions, enemy, log):
        session["battle_companions"] = battle_companions
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        _sync_companion_hp_to_player(player, battle_companions)
        _restore_companion_hp(player)
        return _handle_victory(player, enemy, log)

    session["battle_companions"] = battle_companions

    if player["hp"] <= 0:
        won = _companion_last_stand(battle_companions, enemy, log)
        session["battle_companions"] = battle_companions
        _sync_companion_hp_to_player(player, battle_companions)
        if won:
            player["hp"] = 1
            log.append("Your companions fought on and saved you! You survive, barely.")
            _restore_companion_hp(player)
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            return _handle_victory(player, enemy, log)
        else:
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            return _handle_defeat(player, enemy, log)

    session["battle_enemy"] = enemy
    session["battle_log"] = log
    session["battle_player_effects"] = player_effects
    session["battle_enemy_effects"] = enemy_effects
    save_player(player)
    return redirect(url_for("game"))


@app.route("/battle/defend", methods=["POST"])
def battle_defend():
    player = get_player()
    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if not player or not enemy:
        return redirect(url_for("game"))

    log = session.get("battle_log", [])
    player_effects: dict[str, Any] = session.get("battle_player_effects") or {}
    enemy_effects: dict[str, Any] = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])

    # Process effects at start of turn
    enemy_name = enemy.get("name", "Enemy")
    process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(enemy, enemy_effects, log, enemy_name)

    if player["hp"] <= 0:
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        return _handle_defeat(player, enemy, log)
    if enemy.get("hp", 1) <= 0:
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        return _handle_victory(player, enemy, log)

    log.append("You brace yourself, raising your guard.")
    real_defense = player["defense"]
    player["defense"] = real_defense * 2
    _enemy_take_turn(enemy, player, player_effects, log)
    player["defense"] = real_defense

    # Companion action
    if enemy["hp"] > 0 and _companion_take_action(battle_companions, enemy, log):
        session["battle_companions"] = battle_companions
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        _sync_companion_hp_to_player(player, battle_companions)
        _restore_companion_hp(player)
        return _handle_victory(player, enemy, log)

    session["battle_companions"] = battle_companions

    if player["hp"] <= 0:
        won = _companion_last_stand(battle_companions, enemy, log)
        session["battle_companions"] = battle_companions
        _sync_companion_hp_to_player(player, battle_companions)
        if won:
            player["hp"] = 1
            log.append("Your companions fought on and saved you! You survive, barely.")
            _restore_companion_hp(player)
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            return _handle_victory(player, enemy, log)
        else:
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            return _handle_defeat(player, enemy, log)

    session["battle_enemy"] = enemy
    session["battle_log"] = log
    session["battle_player_effects"] = player_effects
    session["battle_enemy_effects"] = enemy_effects
    save_player(player)
    return redirect(url_for("game"))


@app.route("/battle/use_item", methods=["POST"])
def battle_use_item():
    player = get_player()
    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if not player or not enemy:
        return redirect(url_for("game"))

    log = session.get("battle_log", [])
    player_effects: dict[str, Any] = session.get("battle_player_effects") or {}
    enemy_effects: dict[str, Any] = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])
    item_name = request.form.get("item", "")

    if item_name not in player["inventory"]:
        log.append("You reach for the item but it is not there.")
    else:
        item_data = GAME_DATA["items"].get(item_name, {})
        if not isinstance(item_data, dict):
            item_data = {}

        effect = item_data.get("effect", "")
        value = item_data.get("value", 0)
        min_v = item_data.get("min_value", value)
        max_v = item_data.get("max_value", value)
        duration = item_data.get("duration", 0)
        on_use_buff = item_data.get("on_use_buff", "")
        used = True

        if effect == "heal":
            heal = dice.between(min_v, max_v) if min_v != max_v else value
            player["hp"] = min(player["max_hp"], player["hp"] + heal)
            log.append(f"You quaff the {item_name}, recovering {heal} HP.")
        elif effect == "mp_restore":
            restore = dice.between(min_v, max_v) if min_v != max_v else value
            player["mp"] = min(player["max_mp"], player["mp"] + restore)
            log.append(f"You drink the {item_name}, restoring {restore} MP.")
        elif effect == "full_restore":
            healed = player["max_hp"] - player["hp"]
            mped = player["max_mp"] - player["mp"]
            player["hp"] = player["max_hp"]
            player["mp"] = player["max_mp"]
            log.append(f"You use the {item_name}. Fully restored! (+{healed} HP, +{mped} MP)")
        elif on_use_buff:
            effects_data = GAME_DATA.get("effects", {})
            buff_def = effects_data.get(on_use_buff, {})
            dur = duration or buff_def.get("duration", 5)
            mods = {k: v for k, v in buff_def.items() if k not in ("description", "type", "duration", "tags")}
            player.setdefault("active_buffs", []).append({"name": on_use_buff.replace("_", " ").title(), "duration": dur, "modifiers": mods})
            log.append(f"You use the {item_name}. {buff_def.get('description', 'A buff is applied!')} ({dur} turns)")
        elif item_data.get("type") == "consumable":
            # Fallback: name-based healing
            lower = item_name.lower()
            if "mana" in lower or "mp" in lower:
                restore = dice.between(25, 50)
                player["mp"] = min(player["max_mp"], player["mp"] + restore)
                log.append(f"You drink the {item_name}, restoring {restore} MP.")
            else:
                heal = dice.between(40, 80)
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                log.append(f"You use the {item_name}, regaining {heal} HP.")
        else:
            used = False
            log.append(f"You cannot use {item_name} in battle.")

        if used:
            player["inventory"].remove(item_name)

        _enemy_take_turn(enemy, player, player_effects, log)

    # Companion action
    if enemy["hp"] > 0 and _companion_take_action(battle_companions, enemy, log):
        session["battle_companions"] = battle_companions
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        _sync_companion_hp_to_player(player, battle_companions)
        _restore_companion_hp(player)
        return _handle_victory(player, enemy, log)

    session["battle_companions"] = battle_companions

    if player["hp"] <= 0:
        won = _companion_last_stand(battle_companions, enemy, log)
        session["battle_companions"] = battle_companions
        _sync_companion_hp_to_player(player, battle_companions)
        if won:
            player["hp"] = 1
            log.append("Your companions fought on and saved you! You survive, barely.")
            _restore_companion_hp(player)
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            return _handle_victory(player, enemy, log)
        else:
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            return _handle_defeat(player, enemy, log)

    session["battle_enemy"] = enemy
    session["battle_log"] = log
    session["battle_player_effects"] = player_effects
    session["battle_enemy_effects"] = enemy_effects
    save_player(player)
    return redirect(url_for("game"))


@app.route("/battle/flee", methods=["POST"])
def battle_flee():
    player = get_player()
    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if not player or not enemy:
        return redirect(url_for("game"))

    log = session.get("battle_log", [])

    if random.random() < 0.55:
        log.append("You break away from combat and escape!")
        add_message(f"You fled from the {enemy['name']}.", "var(--wood-light)")
        session.pop("battle_enemy", None)
        session.pop("battle_player_effects", None)
        session.pop("battle_enemy_effects", None)
        session.pop("battle_companions", None)
        session["battle_log"] = []
        save_player(player)
        return redirect(url_for("game"))
    else:
        e_dmg = max(1, enemy["attack"] - player["defense"] + dice.between(0, 5))
        player["hp"] = max(0, player["hp"] - e_dmg)
        log.append(
            f"You try to flee but the {enemy['name']} cuts you off, dealing {e_dmg} damage!"
        )

    if player["hp"] <= 0:
        return _handle_defeat(player, enemy, log)

    session["battle_enemy"] = enemy
    session["battle_log"] = log
    save_player(player)
    return redirect(url_for("game"))


def _handle_victory(player, enemy, log):
    log.append(f"The {enemy['name']} falls! Victory!")
    exp = enemy.get("exp_reward", enemy.get("experience_reward", 30))
    gold = enemy.get("gold_reward", 10)

    # Apply weather bonuses
    _area_name_bw = GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "")
    current_weather = get_real_weather(_area_name_bw)
    exp_bonus_pct, gold_bonus_pct = get_weather_bonuses(current_weather)
    if exp_bonus_pct > 0:
        bonus_exp = int(exp * exp_bonus_pct)
        exp += bonus_exp
        log.append(f"Weather bonus: +{bonus_exp} EXP ({current_weather.replace('_', ' ').title()})!")
    if gold_bonus_pct > 0:
        bonus_gold = int(gold * gold_bonus_pct)
        gold += bonus_gold
        log.append(f"Weather bonus: +{bonus_gold} gold ({current_weather.replace('_', ' ').title()})!")

    log.append(f"You gain {exp} experience and {gold} gold.")

    player["gold"] += gold
    leveled = gain_experience(player, exp)
    _group_contribute(exp, gold, f"defeated {enemy.get('name', 'an enemy')} in battle")

    loot = enemy.get("loot_table", [])
    loot_item = None
    discovery_bonus = player.get("attr_discovery", 0.0)
    loot_chance = min(0.80, 0.35 + discovery_bonus)
    if loot and random.random() < loot_chance:
        loot_item = random.choice(loot)
        player["inventory"].append(loot_item)
        log.append(f"The enemy drops: {loot_item}.")

    if leveled:
        log.append(f"You have reached level {player['level']}! Your strength grows.")
        add_message(
            f"Level Up! You are now level {player['level']}! You gained 3 attribute points (Equipment tab).",
            "var(--gold)",
        )
        if session.get("online_username"):
            _ln = player.get("name", session.get("online_username", "Someone"))
            push_world_event(f"{_ln} reached level {player['level']}!")

    add_message(
        f"Defeated the {enemy['name']}. +{exp} EXP, +{gold} gold.",
        "var(--green-bright)",
    )
    if loot_item:
        add_message(f"Found: {loot_item}", "var(--gold)")

    # Post-battle companion healing aura
    post_heal = player.get("attr_post_battle_heal", 0)
    if post_heal and post_heal > 0:
        actual = min(post_heal, player["max_hp"] - player["hp"])
        if actual > 0:
            player["hp"] += actual
            log.append(f"Your companion's aura restores {actual} HP after battle.")

    # Update quest kill progress
    enemy_key = enemy.get("key", enemy.get("name", "").lower().replace(" ", "_"))
    enemy_name = enemy.get("name", "")
    update_quest_kills(enemy_key, enemy_name)

    # Update weekly challenges
    update_weekly_challenge(player, "kill_count", 1)
    if enemy.get("is_boss"):
        update_weekly_challenge(player, "boss_kill", 1)
        player["total_bosses_defeated"] = player.get("total_bosses_defeated", 0) + 1
        # Boss defeat dialogue
        boss_key = enemy.get("key", "")
        defeat_dialogue = get_boss_dialogue(boss_key, "defeat")
        if defeat_dialogue:
            log.append(f'"{defeat_dialogue}"')

    # Clear status effects
    session.pop("battle_player_effects", None)
    session.pop("battle_enemy_effects", None)
    session.pop("battle_companions", None)
    session["battle_log"] = log
    session["battle_enemy"] = None
    save_player(player)
    _autosave()

    # World events feed (online players only)
    if session.get("online_username"):
        _pname = player.get("name", session.get("online_username", "Someone"))
        _aname = GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "the wilds")
        if enemy.get("is_boss"):
            push_world_event(f"{_pname} defeated {enemy['name']} in {_aname}!")
        else:
            push_world_event(f"{_pname} slew a {enemy['name']} in {_aname}.")

    # If inside a dungeon, return there instead of showing victory screen
    active_dungeon: dict[str, Any] = session.get("active_dungeon") or {}
    if active_dungeon:
        rooms = active_dungeon.get("rooms", [])
        idx = active_dungeon.get("room_index", 0)
        if idx >= len(rooms):
            return redirect(url_for("dungeon_complete"))
        return redirect(url_for("dungeon_room"))

    return render_template(
        "victory.html",
        player=player,
        enemy=enemy,
        log=log,
        exp=exp,
        gold=gold,
        loot_item=loot_item,
        leveled=leveled,
    )


def _handle_defeat(player, enemy, log):
    log.append("You fall in battle...")

    # If inside a dungeon, restart the dungeon from the beginning
    active_dungeon: dict[str, Any] = session.get("active_dungeon") or {}
    if active_dungeon:
        player["hp"] = max(1, int(player["max_hp"] * 0.40))
        log.append(f"You are dragged out of the dungeon, battered. HP: {player['hp']}")
        add_message(
            f"Defeated by {enemy['name']}! The dungeon resets — try again.",
            "var(--red)",
        )
        add_message("You recover some health at the entrance.", "var(--text-dim)")
        session.pop("battle_player_effects", None)
        session.pop("battle_enemy_effects", None)
        session.pop("battle_companions", None)
        session["battle_log"] = log
        session["battle_enemy"] = None
        # Restart dungeon from room 1
        active_dungeon["room_index"] = 0
        active_dungeon["current_challenge"] = None
        active_dungeon["challenge_answered"] = False
        session["active_dungeon"] = active_dungeon
        save_player(player)
        return redirect(url_for("dungeon_room"))

    player["hp"] = max(1, int(player["max_hp"] * 0.25))
    log.append(f"You awaken later, battered. HP: {player['hp']}")
    add_message(f"You were defeated by the {enemy['name']}.", "var(--red)")
    add_message("You recover with a fraction of your health.", "var(--text-dim)")

    session.pop("battle_player_effects", None)
    session.pop("battle_enemy_effects", None)
    session.pop("battle_companions", None)
    session["battle_log"] = log
    session["battle_enemy"] = None
    save_player(player)
    _autosave()

    return render_template("defeat.html", player=player, enemy=enemy, log=log)


# ─── Save / Load ───────────────────────────────────────────────────────────────


@app.route("/api/save", methods=["POST"])
def api_save():
    player = session.get("player")
    if not player:
        return jsonify({"error": "No active character."}), 400

    ensure_attributes(player)
    save_data = {
        "player": player,
        "current_area": session.get("current_area", "starting_village"),
        "completed_missions": session.get("completed_missions", []),
        "visited_areas": session.get("visited_areas", []),
        "quest_progress": session.get("quest_progress", {}),
        "seen_cutscenes": session.get("seen_cutscenes", []),
        "messages": session.get("messages", [])[-20:],
        "diary": session.get("diary", []),
        "npc_unlocked_quests": session.get("npc_unlocked_quests", []),
        "save_version": "7.1",
        "game_version": GAME_VERSION,
    }

    player_name = (player.get("name") or "save").replace(" ", "_")
    filename = f"our_legacy_{player_name}_lv{player.get('level', 1)}.olsave"
    encrypted = encrypt_save(save_data)
    response = make_response(encrypted)
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@app.route("/api/load", methods=["POST"])
def api_load():
    data = None
    if request.files.get("save_file"):
        raw_bytes = request.files["save_file"].read()
        try:
            data = decrypt_save(raw_bytes)
        except (ValueError, TypeError, OSError) as e:
            return jsonify({"error": str(e)}), 400
    elif request.content_type and "application/octet-stream" in request.content_type:
        raw_bytes = request.data
        try:
            data = decrypt_save(raw_bytes)
        except (ValueError, TypeError, OSError) as e:
            return jsonify({"error": str(e)}), 400
    else:
        data = request.get_json(force=True, silent=True) or {}

    if not data:
        return jsonify({"error": "No save data received."}), 400

    player = data.get("player")
    if not player or not player.get("name"):
        return jsonify({"error": "Invalid save file: missing player data."}), 400

    _ensure_equipment_slots(player)
    # Initialize new fields if missing (backward compatibility)
    player.setdefault("game_ticks", 0)
    player.setdefault("weekly_challenges_progress", {})
    player.setdefault("boss_cooldowns", {})
    player.setdefault("race", "Descendants from another world")
    ensure_attributes(player)

    session["player"] = player
    session["current_area"] = data.get("current_area", "starting_village")
    session["completed_missions"] = data.get("completed_missions", [])
    _va_top = data.get("visited_areas", [])
    _va_player = (data.get("player") or {}).get("visited_areas", [])
    session["visited_areas"] = list(set(_va_top + _va_player)) or [session["current_area"]]
    session["quest_progress"] = data.get("quest_progress", {})
    session["seen_cutscenes"] = data.get("seen_cutscenes", [])
    session["messages"] = data.get("messages", [])
    session["diary"] = data.get("diary", [])
    session["npc_unlocked_quests"] = data.get("npc_unlocked_quests", [])
    session.modified = True
    return jsonify({"ok": True, "player_name": player.get("name")})


# ─── Crafting Routes ──────────────────────────────────────────────────────────


@app.route("/crafting")
def crafting():
    return redirect(url_for("game") + "?tab=crafting")


@app.route("/action/craft", methods=["POST"])
def action_craft():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    recipe_id = request.form.get("recipe_id", "")
    crafting_data: dict[str, Any] = GAME_DATA.get("crafting", {})
    result = craft_item(player, recipe_id, crafting_data)
    color = "var(--green-bright)" if result["ok"] else "var(--red)"
    add_message(result["message"], color)
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=crafting")


# ─── Dungeon Routes ────────────────────────────────────────────────────────────


@app.route("/dungeons")
def dungeons():
    return redirect(url_for("game") + "?tab=dungeons")


@app.route("/action/dungeon/enter", methods=["POST"])
def dungeon_enter():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    dungeon_id = request.form.get("dungeon_id", "")
    dungeons_data: dict[str, Any] = GAME_DATA.get("dungeons", {})
    all_dungeons = dungeons_data.get("dungeons", [])
    dungeon = next((d for d in all_dungeons if d.get("id") == dungeon_id), None)

    if not dungeon:
        add_message("Unknown dungeon.", "var(--red)")
        return redirect(url_for("game") + "?tab=dungeons")

    allowed_areas = dungeon.get("allowed_areas", [])
    current_area_key = session.get("current_area", "starting_village")
    visited = session.get("visited_areas", [])
    if not any(a in visited for a in allowed_areas):
        add_message("You haven't discovered this dungeon yet.", "var(--red)")
        return redirect(url_for("game") + "?tab=dungeons")
    if current_area_key not in allowed_areas:
        area_info = GAME_DATA.get("areas", {}).get(allowed_areas[0], {})
        area_name = area_info.get("name") or allowed_areas[0].replace("_", " ").title()
        add_message(f"You must travel to {area_name} to enter this dungeon.", "var(--red)")
        return redirect(url_for("game") + "?tab=dungeons")

    difficulty = dungeon.get("difficulty", [1, 3])
    min_level = max(1, difficulty[0] * 2)
    if player.get("level", 1) < min_level:
        add_message(
            f"You need to be level {min_level} to enter this dungeon.", "var(--red)"
        )
        return redirect(url_for("game") + "?tab=dungeons")

    rooms = generate_dungeon_rooms(dungeon, dungeons_data)
    session["active_dungeon"] = {
        "dungeon": dungeon,
        "rooms": rooms,
        "room_index": 0,
        "current_challenge": None,
        "challenge_answered": False,
    }
    session.modified = True
    add_message(
        f"You enter {dungeon.get('name', 'the dungeon')}! Steel yourself.",
        "var(--gold)",
    )
    _set_activity(player, f"delving {dungeon.get('name', 'a dungeon')}")
    save_player(player)
    return redirect(url_for("dungeon_room"))


@app.route("/dungeon/room")
def dungeon_room():
    player = get_player()
    active: dict[str, Any] = session.get("active_dungeon") or {}
    if not player or not active:
        return redirect(url_for("game") + "?tab=dungeons")

    rooms = active.get("rooms", [])
    idx = active.get("room_index", 0)
    if idx >= len(rooms):
        return redirect(url_for("dungeon_complete"))

    room: dict[str, Any] = rooms[idx]
    dungeon = active.get("dungeon", {})
    current_challenge = active.get("current_challenge")

    room_type = room.get("type", "empty")
    if room_type in ("question", "multi_choice") and not current_challenge:
        dungeons_data: dict[str, Any] = GAME_DATA.get("dungeons", {})
        if room_type == "question":
            current_challenge = room.get("challenge") or process_question_room(
                dungeons_data
            )
        else:
            current_challenge = room.get("challenge") or _pick_multi_choice(
                dungeons_data
            )
        active["current_challenge"] = current_challenge
        session["active_dungeon"] = active

    return render_template(
        "dungeon_room.html",
        player=player,
        room=room,
        room_num=idx + 1,
        total_rooms=len(rooms),
        dungeon=dungeon,
        current_challenge=current_challenge,
        messages=list(reversed(get_messages()))[:10],
    )


@app.route("/action/dungeon/proceed", methods=["POST"])
def dungeon_proceed():
    player = get_player()
    active: dict[str, Any] = session.get("active_dungeon") or {}
    if not player or not active:
        return redirect(url_for("game") + "?tab=dungeons")

    rooms = active.get("rooms", [])
    idx = active.get("room_index", 0)
    if idx >= len(rooms):
        return redirect(url_for("dungeon_complete"))

    room: dict[str, Any] = rooms[idx]
    room_type = room.get("type", "empty")
    dungeon: dict[str, Any] = active.get("dungeon", {})

    dungeons_data: dict[str, Any] = GAME_DATA.get("dungeons", {})
    items_data: dict[str, Any] = GAME_DATA.get("items", {})
    enemies_data: dict[str, Any] = GAME_DATA.get("enemies", {})
    areas_data: dict[str, Any] = GAME_DATA.get("areas", {})
    area_key = session.get("current_area", "starting_village")

    if room_type == "battle":
        result = process_battle_room(player, room, enemies_data, areas_data, area_key, dungeon=dungeon)
        if result["type"] == "battle":
            enemy = result["enemy"]
            session["battle_enemy"] = enemy
            session["battle_log"] = [
                f"A {enemy.get('name', 'enemy')} confronts you in the dungeon!"
            ]
            session["battle_player_effects"] = {}
            session["battle_enemy_effects"] = {}
            session["battle_companions"] = _build_battle_companions(player)
            active["room_index"] = idx + 1
            active["current_challenge"] = None
            session["active_dungeon"] = active
            save_player(player)
            return redirect(url_for("game"))
        else:
            for msg in result.get("messages", []):
                add_message(msg["text"], msg.get("color", "var(--text-light)"))

    elif room_type == "ambush":
        result = process_ambush_room(player, room, enemies_data, areas_data, area_key, dungeon=dungeon)
        if result["type"] == "ambush":
            enemy = result["enemy"]
            session["battle_enemy"] = enemy
            session["battle_log"] = [
                f"AMBUSH! A powerful {enemy.get('name', 'enemy')} leaps from the shadows!"
            ]
            session["battle_player_effects"] = {}
            session["battle_enemy_effects"] = {}
            session["battle_companions"] = _build_battle_companions(player)
            active["room_index"] = idx + 1
            active["current_challenge"] = None
            session["active_dungeon"] = active
            save_player(player)
            return redirect(url_for("game"))
        else:
            for msg in result.get("messages", []):
                add_message(msg["text"], msg.get("color", "var(--text-light)"))

    elif room_type == "shrine":
        result = process_shrine_room(player)
        for msg in result.get("messages", []):
            add_message(msg["text"], msg.get("color", "var(--text-light)"))

    elif room_type == "chest":
        result = process_chest_room(player, room, dungeons_data, items_data)
        for msg in result.get("messages", []):
            add_message(msg["text"], msg.get("color", "var(--text-light)"))

    elif room_type == "trap_chest":
        roll = dice.roll_1d(20)
        result = process_trap_chest_room(player, room, dungeons_data, items_data, roll)
        for msg in result.get("messages", []):
            add_message(msg["text"], msg.get("color", "var(--text-light)"))

    elif room_type == "boss":
        boss_id = room.get("boss_id", active.get("dungeon", {}).get("boss_id", ""))
        bosses_data: dict[str, Any] = GAME_DATA.get("bosses", {})
        boss_data: dict[str, Any] = bosses_data.get(boss_id, {})
        if boss_data:
            difficulty = room.get("difficulty", 1)
            scale = 0.8 + difficulty * 0.2
            enemy = {
                "key": boss_id,
                "name": boss_data.get("name", boss_id.replace("_", " ").title()),
                "hp": int(boss_data.get("hp", 200) * scale),
                "max_hp": int(boss_data.get("hp", 200) * scale),
                "attack": int(boss_data.get("attack", 20) * scale),
                "defense": int(boss_data.get("defense", 10) * scale),
                "speed": boss_data.get("speed", 12),
                "exp_reward": int(boss_data.get("experience_reward", 200) * scale),
                "gold_reward": int(boss_data.get("gold_reward", 100) * scale),
                "loot_table": boss_data.get("loot_table", []),
                "is_boss": True,
                "tags": boss_data.get("tags", ["humanoid"]),
            }
        else:
            lvl = player.get("level", 1)
            enemy = {
                "key": "dungeon_boss",
                "name": "Dungeon Boss",
                "hp": 200 + lvl * 30,
                "max_hp": 200 + lvl * 30,
                "attack": 20 + lvl * 3,
                "defense": 12 + lvl * 2,
                "speed": 12,
                "exp_reward": 300 + lvl * 50,
                "gold_reward": 100 + lvl * 20,
                "loot_table": [],
                "is_boss": True,
                "tags": ["humanoid"],
            }
        dialogue = get_boss_dialogue(boss_id, "start")
        session["battle_enemy"] = enemy
        session["battle_log"] = [
            f"The guardian {enemy['name']} awakens! This is the final battle!"
        ]
        if dialogue:
            session["battle_log"].append(f'"{dialogue}"')
        session["battle_player_effects"] = {}
        session["battle_enemy_effects"] = {}
        session["battle_companions"] = _build_battle_companions(player)
        active["room_index"] = idx + 1
        active["current_challenge"] = None
        session["active_dungeon"] = active
        save_player(player)
        return redirect(url_for("game"))

    elif room_type == "question":
        add_message("A riddle challenge awaits in the chamber!", "var(--gold)")
        return redirect(url_for("dungeon_room"))

    elif room_type == "multi_choice":
        add_message("A fateful choice confronts you!", "var(--gold)")
        return redirect(url_for("dungeon_room"))

    else:
        result = process_empty_room(room)
        for msg in result.get("messages", []):
            add_message(msg["text"], msg.get("color", "var(--text-light)"))

    active["room_index"] = idx + 1
    active["current_challenge"] = None
    session["active_dungeon"] = active
    save_player(player)

    if active["room_index"] >= len(rooms):
        return redirect(url_for("dungeon_complete"))
    return redirect(url_for("dungeon_room"))


@app.route("/dungeon/answer", methods=["POST"])
def dungeon_answer():
    player = get_player()
    active: dict[str, Any] = session.get("active_dungeon") or {}
    if not player or not active:
        return redirect(url_for("game") + "?tab=dungeons")

    answer_text = request.form.get("answer", "").strip()
    challenge = active.get("current_challenge", {})
    result = answer_question(player, challenge, answer_text)

    for msg in result.get("messages", []):
        add_message(msg["text"], msg.get("color", "var(--text-light)"))

    active["room_index"] = active.get("room_index", 0) + 1
    active["current_challenge"] = None
    session["active_dungeon"] = active
    save_player(player)

    if active["room_index"] >= len(active["rooms"]):
        return redirect(url_for("dungeon_complete"))
    return redirect(url_for("dungeon_room"))


@app.route("/dungeon/choose", methods=["POST"])
def dungeon_choose():
    player = get_player()
    active: dict[str, Any] = session.get("active_dungeon") or {}
    if not player or not active:
        return redirect(url_for("game") + "?tab=dungeons")

    choice_idx = int(request.form.get("choice", 0))
    challenge = active.get("current_challenge", {})
    result = answer_multi_choice(player, challenge, choice_idx)

    for msg in result.get("messages", []):
        add_message(msg["text"], msg.get("color", "var(--text-light)"))

    active["room_index"] = active.get("room_index", 0) + 1
    active["current_challenge"] = None
    session["active_dungeon"] = active
    save_player(player)

    if active["room_index"] >= len(active["rooms"]):
        return redirect(url_for("dungeon_complete"))
    return redirect(url_for("dungeon_room"))


@app.route("/dungeon/complete")
def dungeon_complete():
    player = get_player()
    active: dict[str, Any] = session.get("active_dungeon") or {}
    if not player:
        return redirect(url_for("index"))

    if active:
        dungeon = active.get("dungeon", {})
        result = complete_dungeon(player, dungeon)
        for msg in result.get("messages", []):
            add_message(msg["text"], msg.get("color", "var(--gold)"))
        _group_contribute(result.get("exp", 0), result.get("gold", 0), f"cleared dungeon: {dungeon.get('name', 'a dungeon')}")
        # Mark dungeon as completed in player data
        dungeon_id = dungeon.get("id", "")
        if dungeon_id:
            completed_dungeons = player.setdefault("completed_dungeons", [])
            if dungeon_id not in completed_dungeons:
                completed_dungeons.append(dungeon_id)
        session.pop("active_dungeon", None)
        # Update weekly challenge
        update_weekly_challenge(player, "dungeon_complete", 1)
        save_player(player)
        _autosave()

    return redirect(url_for("game") + "?tab=dungeons")


@app.route("/dungeon/abandon", methods=["POST"])
def dungeon_abandon():
    session.pop("active_dungeon", None)
    add_message("You retreat from the dungeon.", "var(--text-dim)")
    return redirect(url_for("game") + "?tab=dungeons")


@app.route("/market")
def market():
    return redirect(url_for("game") + "?tab=market")


@app.route("/api/market_data")
def api_market_data():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "error": "Not logged in"})
    market_api = get_market_api()
    extra_seed = session.get("market_reroll_count", 0)
    result = market_api.fetch_market_data(extra_seed=extra_seed)
    market_items = []
    cooldown_msg = None
    if result.get("ok") and result.get("data", {}).get("ok"):
        market_items = result["data"].get("items", [])
    elif result.get("cooldown"):
        cooldown_msg = result.get("message", "Market is closed.")
    elif not result.get("ok"):
        cooldown_msg = result.get("message", "Could not reach the market.")
    return jsonify(
        {
            "ok": True,
            "market_items": market_items,
            "cooldown_msg": cooldown_msg,
            "player_gold": player.get("gold", 0),
            "player_level": player.get("level", 1),
            "player_class": player.get("class", ""),
            "reroll_count": extra_seed,
        }
    )


@app.route("/action/market/reset", methods=["POST"])
def market_reset():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    cost = 1000
    if player.get("gold", 0) < cost:
        add_message(f"You need {cost} gold to reroll the Elite Market.", "var(--red)")
    else:
        player["gold"] -= cost
        session["market_reroll_count"] = session.get("market_reroll_count", 0) + 1
        session.modified = True
        save_player(player)
        add_message("The Elite Market stock has been rerolled!", "var(--gold)")
    return redirect(url_for("game") + "?tab=market")


@app.route("/action/market/buy", methods=["POST"])
def market_buy():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    item_name = request.form.get("item_name", "")
    item_price = int(request.form.get("item_price", 0))

    if player["gold"] < item_price:
        add_message(f"Not enough gold. Need {item_price} gold.", "var(--red)")
    else:
        player["gold"] -= item_price
        player["inventory"].append(item_name)
        add_message(
            f"Purchased {item_name} from the Elite Market for {item_price} gold!",
            "var(--gold)",
        )

    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=market")


# ─── Server-side Save / Load ──────────────────────────────────────────────────


@app.route("/api/server_save", methods=["POST"])
def api_server_save():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."})

    result = save_game(
        player=player,
        current_area=session.get("current_area", "starting_village"),
        visited_areas=session.get("visited_areas", []),
        completed_missions=session.get("completed_missions", []),
        npc_unlocked_quests=session.get("npc_unlocked_quests", []),
    )
    return jsonify(result)


@app.route("/api/server_saves", methods=["GET"])
def api_server_saves():
    saves = list_saves()
    return jsonify({"saves": saves})


@app.route("/api/server_load", methods=["POST"])
def api_server_load():
    data = request.get_json(force=True, silent=True) or {}
    filepath = data.get("filepath", "")
    if not filepath:
        return jsonify({"ok": False, "message": "No file path provided."})

    result = load_save(filepath)
    if result.get("ok"):
        session["player"] = result["player"]
        session["current_area"] = result["current_area"]
        session["visited_areas"] = result["visited_areas"]
        session["completed_missions"] = result["completed_missions"]
        session["npc_unlocked_quests"] = result.get("npc_unlocked_quests", [])
        session["messages"] = []
        session.modified = True

    return jsonify({"ok": result.get("ok"), "message": result.get("message", "")})


@app.route("/api/player_stats")
def api_player_stats():
    player = get_player()
    if not player:
        return jsonify({"ok": False})
    return jsonify({"ok": True, "player": player})


@app.route("/new_game")
def new_game():
    session.clear()
    return redirect(url_for("index"))


# ─── Online Account Routes ────────────────────────────────────────────────────


@app.route("/api/online/register", methods=["POST"])
@limiter.limit("5 per hour")
def api_online_register():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    result = register_user(username, password)
    if result["ok"]:
        return jsonify(result), 200
    return jsonify(result), 400


@app.route("/api/online/login", methods=["POST"])
@limiter.limit("10 per minute")
def api_online_login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    result = login_user(username, password)
    if result["ok"]:
        session["online_username"] = username.lower()
        session["online_user_id"] = result["user_id"]
        session.modified = True
        return jsonify({"ok": True, "message": result["message"], "username": username.lower()})
    return jsonify({"ok": False, "message": result["message"]}), 401


@app.route("/api/online/logout", methods=["POST"])
def api_online_logout():
    _autosave()
    game_keys = [
        "player", "current_area", "completed_missions", "visited_areas",
        "quest_progress", "seen_cutscenes", "messages",
        "diary", "npc_unlocked_quests", "battle_enemy", "battle_player_effects",
        "battle_enemy_effects", "active_dungeon", "pending_cutscene",
        "weekly_challenges_progress",
    ]
    for key in game_keys:
        session.pop(key, None)
    session.pop("online_username", None)
    session.pop("online_user_id", None)
    session.modified = True
    return jsonify({"ok": True, "message": "Logged out."})


@app.route("/api/online/cloud_save", methods=["POST"])
def api_cloud_save():
    user_id = session.get("online_user_id")
    if not user_id:
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 400
    ensure_attributes(player)
    save_data = {
        "player": player,
        "current_area": session.get("current_area", "starting_village"),
        "completed_missions": session.get("completed_missions", []),
        "visited_areas": session.get("visited_areas", []),
        "quest_progress": session.get("quest_progress", {}),
        "seen_cutscenes": session.get("seen_cutscenes", []),
        "messages": session.get("messages", [])[-20:],
        "diary": session.get("diary", []),
        "npc_unlocked_quests": session.get("npc_unlocked_quests", []),
        "save_version": "7.1",
        "game_version": GAME_VERSION,
    }
    result = cloud_save(user_id, save_data)
    if result.get("ok"):
        add_message("Game saved to cloud.", color="var(--accent)")
    return jsonify(result), 200 if result["ok"] else 500


@app.route("/api/online/cloud_load", methods=["POST"])
def api_cloud_load():
    user_id = session.get("online_user_id")
    if not user_id:
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    result = cloud_load(user_id)
    if not result["ok"]:
        return jsonify(result), 404

    data = result["data"]
    player = data.get("player")
    if not player or not player.get("name"):
        return jsonify({"ok": False, "message": "Invalid cloud save."}), 400

    _ensure_equipment_slots(player)
    player.setdefault("game_ticks", 0)
    player.setdefault("weekly_challenges_progress", {})
    player.setdefault("boss_cooldowns", {})
    player.setdefault("race", "Descendants from another world")
    ensure_attributes(player)

    session["player"] = player
    session["current_area"] = data.get("current_area", "starting_village")
    session["completed_missions"] = data.get("completed_missions", [])
    _va_top = data.get("visited_areas", [])
    _va_player = (data.get("player") or {}).get("visited_areas", [])
    session["visited_areas"] = list(set(_va_top + _va_player)) or [session["current_area"]]
    session["quest_progress"] = data.get("quest_progress", {})
    session["seen_cutscenes"] = data.get("seen_cutscenes", [])
    session["messages"] = data.get("messages", [])
    session["diary"] = data.get("diary", [])
    session["npc_unlocked_quests"] = data.get("npc_unlocked_quests", [])
    session.modified = True
    return jsonify({"ok": True, "message": result["message"], "player_name": player.get("name")})


@app.route("/api/online/cloud_meta")
def api_cloud_meta():
    user_id = session.get("online_user_id")
    if not user_id:
        return jsonify({"ok": False, "meta": None})
    meta = get_cloud_save_meta(user_id)
    return jsonify({"ok": True, "meta": meta})


@app.route("/api/online/cloud_download")
def api_cloud_download():
    user_id = session.get("online_user_id")
    if not user_id:
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    result = cloud_load(user_id)
    if not result["ok"]:
        return jsonify({"ok": False, "message": result["message"]}), 404
    raw_bytes = encrypt_save(result["data"])
    username = session.get("online_username", "player")
    data = result["data"]
    player = data.get("player", {})
    player_name = (player.get("name") or username).replace(" ", "_")
    filename = f"cloud_{player_name}_lv{player.get('level', 1)}.olsave"
    response = make_response(raw_bytes)
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ─── Friends & DM Routes ──────────────────────────────────────────────────────

@app.route("/friends")
def friends_page():
    username = session.get("online_username")
    if not username:
        return redirect("/")
    return render_template("friends.html", online_username=username)


@app.route("/api/friends", methods=["GET"])
def api_friends():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    result = get_friends(username)
    online = set(_chat_online.values())
    for f in result.get("friends", []):
        f["online"] = f["username"] in online
    unread = get_unread_dm_counts(username)
    for f in result.get("friends", []):
        f["unread"] = unread.get(f["username"], 0)
    return jsonify(result)


@app.route("/api/friends/request", methods=["POST"])
def api_friend_request():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    target = (request.json or {}).get("target", "").strip().lower()
    if not target:
        return jsonify({"ok": False, "message": "No target specified."})
    now = _time_module.time()
    timestamps = _fr_cooldowns.get(username, [])
    timestamps = [t for t in timestamps if now - t < 60]
    if len(timestamps) >= FR_MAX_PER_MINUTE:
        return jsonify({"ok": False, "message": f"Too many requests. Try again in a moment."})
    timestamps.append(now)
    _fr_cooldowns[username] = timestamps
    if is_blocked(username, target):
        return jsonify({"ok": False, "message": "Unable to send request to that user."})
    result = send_friend_request(username, target)
    if result.get("ok"):
        target_sids = [sid for sid, u in _chat_online.items() if u == target]
        for sid in target_sids:
            if result.get("accepted"):
                socketio.emit("friend_accepted", {"from": username}, to=sid)
            else:
                socketio.emit("friend_request", {"from": username}, to=sid)
    return jsonify(result)


@app.route("/api/friends/respond", methods=["POST"])
def api_friend_respond():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    data = request.json or {}
    request_id = data.get("id", "")
    accept = bool(data.get("accept", False))
    result = respond_friend_request(request_id, accept, username)
    if result.get("ok") and accept:
        friend = result.get("friend", "")
        target_sids = [sid for sid, u in _chat_online.items() if u == friend]
        for sid in target_sids:
            socketio.emit("friend_accepted", {"from": username}, to=sid)
    return jsonify(result)


@app.route("/api/friends/remove", methods=["POST"])
def api_friend_remove():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    target = (request.json or {}).get("target", "").strip().lower()
    return jsonify(remove_friend(username, target))


@app.route("/api/dm/<other>", methods=["GET"])
def api_dm_get(other):
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "messages": []})
    other = other.strip().lower()
    mark_dms_read(username, other)
    messages = get_dm_conversation(username, other)
    return jsonify({"ok": True, "messages": messages})


@app.route("/api/dm/send", methods=["POST"])
def api_dm_send():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    data = request.json or {}
    recipient = data.get("recipient", "").strip().lower()
    message = data.get("message", "").strip()
    if not recipient or not message:
        return jsonify({"ok": False, "message": "Missing fields."})
    if len(message) > DM_MAX_LEN:
        return jsonify({"ok": False, "message": f"Message too long (max {DM_MAX_LEN} chars)."})
    now = _time_module.time()
    last_dm = _dm_cooldowns.get(username, 0)
    if now - last_dm < DM_COOLDOWN_SECS:
        wait = int(DM_COOLDOWN_SECS - (now - last_dm)) + 1
        return jsonify({"ok": False, "message": f"Please wait {wait}s before sending another message."})
    _dm_cooldowns[username] = now
    if is_blocked(username, recipient):
        return jsonify({"ok": False, "message": "You cannot message this user."})
    result = send_dm(username, recipient, message)
    if result.get("ok"):
        row = result["row"]
        payload = {
            "id": row.get("id"),
            "sender": username,
            "recipient": recipient,
            "message": row.get("message", message),
            "created_at": row.get("created_at"),
        }
        target_sids = [sid for sid, u in _chat_online.items() if u == recipient]
        for sid in target_sids:
            socketio.emit("dm_message", payload, to=sid)
    return jsonify(result)


@app.route("/api/block", methods=["POST"])
def api_block_user():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    data = request.json or {}
    target = data.get("target", "").strip().lower()
    action = data.get("action", "block")
    if not target:
        return jsonify({"ok": False, "message": "No target specified."})
    if action == "unblock":
        return jsonify(unblock_user(username, target))
    return jsonify(block_user(username, target))


@app.route("/api/block/list", methods=["GET"])
def api_block_list():
    username = session.get("online_username")
    if not username:
        return jsonify({"blocked": []})
    return jsonify({"ok": True, "blocked": get_blocked_by_me(username)})


# ─── Trade REST Routes ────────────────────────────────────────────────────────

@app.route("/api/player/inventory")
def api_player_inventory():
    username = session.get("online_username")
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "inventory": [], "gold": 0, "in_trade": None})
    offered_items: list = []
    offered_gold = 0
    active_trade_id = None
    for tid, trade in _active_trades.items():
        if username and username in (trade["player_a"], trade["player_b"]) and trade["status"] == "active":
            key = "offer_a" if username == trade["player_a"] else "offer_b"
            offered_items = list(trade[key]["items"])
            offered_gold = trade[key]["gold"]
            active_trade_id = tid
            break
    return jsonify({
        "ok": True,
        "inventory": player.get("inventory", []),
        "gold": player.get("gold", 0),
        "offered_items": offered_items,
        "offered_gold": offered_gold,
        "active_trade_id": active_trade_id,
    })


@app.route("/api/trade/apply", methods=["POST"])
def api_trade_apply():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 400
    data = request.json or {}
    trade_id = str(data.get("trade_id", ""))
    trade = _active_trades.get(trade_id)
    if not trade:
        return jsonify({"ok": False, "message": "Trade not found."}), 404
    if trade["status"] != "approved":
        return jsonify({"ok": False, "message": "Trade not approved yet."}), 400
    if username not in (trade["player_a"], trade["player_b"]):
        return jsonify({"ok": False, "message": "Not a participant."}), 403
    is_a = username == trade["player_a"]
    applied_key = "applied_a" if is_a else "applied_b"
    if trade[applied_key]:
        return jsonify({"ok": True, "message": "Already applied."})
    my_offer = trade["offer_a"] if is_a else trade["offer_b"]
    their_offer = trade["offer_b"] if is_a else trade["offer_a"]
    inventory = list(player.get("inventory", []))
    current_gold = player.get("gold", 0)
    give_items = list(my_offer["items"])
    give_gold = int(my_offer["gold"])
    receive_items = list(their_offer["items"])
    receive_gold = int(their_offer["gold"])
    if current_gold < give_gold:
        return jsonify({"ok": False, "message": "Not enough gold."}), 400
    for item in give_items:
        if item not in inventory:
            return jsonify({"ok": False, "message": f"Item '{item}' not found in inventory."}), 400
        inventory.remove(item)
    current_gold -= give_gold
    for item in receive_items:
        inventory.append(item)
    current_gold += receive_gold
    player["inventory"] = inventory
    player["gold"] = current_gold
    session["player"] = player
    session.modified = True
    trade[applied_key] = True
    if trade.get("applied_a") and trade.get("applied_b"):
        _active_trades.pop(trade_id, None)
    return jsonify({
        "ok": True,
        "message": f"Trade complete! Received {len(receive_items)} item(s) and {receive_gold:,} gold.",
        "received_items": receive_items,
        "received_gold": receive_gold,
    })


@app.route("/api/dm/unread", methods=["GET"])
def api_dm_unread():
    username = session.get("online_username")
    if not username:
        return jsonify({})
    return jsonify(get_unread_dm_counts(username))


@app.route("/action/customize_character", methods=["POST"])
def action_customize_character():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."})
    cost = 10000
    if player.get("gold", 0) < cost:
        return jsonify({"ok": False, "message": f"You need {cost:,} gold to change your character."})
    online_user = session.get("online_username")
    data = request.json or {}
    new_name = data.get("name", "").strip()
    new_gender = data.get("gender", "").strip()
    new_race = data.get("race", "").strip()
    new_class = data.get("class", "").strip()
    valid_genders = ["male", "female", "nonbinary"]
    valid_races = list(GAME_DATA.get("races", {}).keys())
    valid_classes = list(GAME_DATA.get("classes", {}).keys())
    changes = []
    if new_name and not online_user:
        if 1 <= len(new_name) <= 20:
            player["name"] = new_name
            changes.append(f"name to {new_name}")
        else:
            return jsonify({"ok": False, "message": "Name must be 1–20 characters."})
    if new_gender and new_gender in valid_genders:
        player["gender"] = new_gender
        changes.append(f"gender to {new_gender}")
    if new_race and new_race in valid_races:
        player["race"] = new_race
        changes.append(f"race to {new_race}")
    if new_class and new_class in valid_classes:
        player["class"] = new_class
        changes.append(f"class to {new_class}")
        equipment = player.get("equipment", {})
        unequipped = []
        for slot, item in equipment.items():
            if item:
                player["inventory"].append(item)
                equipment[slot] = None
                unequipped.append(item)
        player["equipment"] = equipment
        if unequipped:
            add_message(f"All gear unequipped on class change: {', '.join(unequipped)}.", "var(--text-dim)")
    if not changes:
        return jsonify({"ok": False, "message": "No valid changes provided."})
    player["gold"] -= cost
    save_player(player)
    _autosave()
    add_message(f"Character updated ({', '.join(changes)}). -{cost:,} gold.", "var(--gold)")
    return jsonify({"ok": True, "message": f"Character updated: {', '.join(changes)}."})


# ─── Adventure Groups ────────────────────────────────────────────────────────

GROUP_CHAT_COOLDOWN = 5
_group_chat_cooldowns: dict = {}


@socketio.on("group_chat_send")
def on_group_chat_send(data):
    username = session.get("online_username")
    if not username:
        socketio_emit("group_chat_error", {"message": "Not logged in."})
        return
    message = (data.get("message") or "").strip()
    if not message:
        return
    if len(message) > 200:
        socketio_emit("group_chat_error", {"message": "Message too long (max 200 chars)."})
        return
    now = _time_module.time()
    if now - _group_chat_cooldowns.get(username, 0) < GROUP_CHAT_COOLDOWN:
        socketio_emit("group_chat_error", {"message": f"Wait {GROUP_CHAT_COOLDOWN}s between messages."})
        return
    _group_chat_cooldowns[username] = now
    message = censor_text(message)
    group_result = get_user_group(username)
    if not group_result.get("ok") or not group_result.get("group"):
        socketio_emit("group_chat_error", {"message": "You are not in a group."})
        return
    group = group_result["group"]
    members = [m["username"] for m in group.get("members", [])]
    payload = {"username": username, "message": message, "ts": int(now)}
    for member in members:
        for sid in [s for s, u in _chat_online.items() if u == member]:
            socketio.emit("group_chat_message", payload, to=sid)


@app.route("/groups")
def groups_page():
    online_username = session.get("online_username")
    if not online_username:
        return redirect(url_for("index"))
    group_data = None
    try:
        res = get_user_group(online_username)
        if res.get("ok"):
            group_data = res.get("group")
    except Exception:
        pass
    return render_template("groups.html", online_username=online_username, group=group_data)


@app.route("/api/groups/my")
def api_groups_my():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    try:
        res = get_user_group(username)
        return jsonify(res)
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/groups/create", methods=["POST"])
@limiter.limit("5 per hour")
def api_groups_create():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    result = create_group(username, name, description)
    return jsonify(result), 200 if result["ok"] else 400


@app.route("/api/groups/join", methods=["POST"])
@limiter.limit("10 per hour")
def api_groups_join():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    data = request.get_json(force=True, silent=True) or {}
    invite_code = (data.get("invite_code") or "").strip()
    result = join_group(username, invite_code)
    return jsonify(result), 200 if result["ok"] else 400


@app.route("/api/groups/leave", methods=["POST"])
def api_groups_leave():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    result = leave_group(username)
    return jsonify(result), 200 if result["ok"] else 400


@app.route("/api/groups/kick", methods=["POST"])
def api_groups_kick():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    data = request.get_json(force=True, silent=True) or {}
    target = (data.get("target") or "").strip().lower()
    result = kick_group_member(username, target)
    return jsonify(result), 200 if result["ok"] else 400


@app.route("/api/groups/collect_gold", methods=["POST"])
def api_groups_collect_gold():
    username = session.get("online_username")
    if not username:
        return jsonify({"ok": False, "message": "Not logged in."})
    result = collect_group_gold(username)
    if result.get("ok"):
        player = get_player()
        if player:
            gold = result.get("gold", 0)
            player["gold"] = player.get("gold", 0) + gold
            save_player(player)
            _autosave()
            add_message(f"Collected {gold} gold from the group treasury!", "var(--gold)")
    return jsonify(result), 200 if result["ok"] else 400


# ─── Leaderboard ─────────────────────────────────────────────────────────────

@app.route("/leaderboard")
def leaderboard_page():
    online_username = session.get("online_username")
    return render_template("leaderboard.html", online_username=online_username)


@app.route("/api/leaderboard")
def api_leaderboard():
    groups = get_group_leaderboard()
    players = get_player_leaderboard()
    return jsonify({"ok": True, "groups": groups, "players": players})


port = int(os.environ.get("PORT", 5000))
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
