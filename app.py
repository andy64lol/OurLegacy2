import sys
import warnings

warnings.filterwarnings("ignore", message="urllib3")
warnings.filterwarnings("ignore", message="chardet")

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
import socketio as _socketio_module
import asyncio as _asyncio
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
    clear_chat_history,
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
    create_password_reset_token,
    reset_password_with_token,
    get_user_email,
    get_pending_email_verification,
    request_email_verification,
    verify_email_token,
    try_acquire_or_renew_world_tick_lock,
    release_world_tick_lock,
    admin_get_owner,
    admin_set_owner,
    admin_get_mods,
    admin_add_mod,
    admin_remove_mod,
    admin_get_all_mods,
    admin_is_banned,
    admin_ban,
    admin_unban,
    admin_list_bans,
    admin_is_muted,
    admin_mute,
    admin_unmute,
    admin_list_mutes,
    admin_warn,
    admin_clear_warns,
)
from utilities.email_sender import (
    send_email as _send_email,
    is_configured as _email_configured,
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.environ.get("SECRET_KEY") or os.environ.get(
    "SESSION_SECRET", "ol2-default-dev-key-change-in-prod"
)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(
    os.path.dirname(__file__), ".flask_sessions"
)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)


@app.after_request
def apply_cors_and_iframe_headers(response):
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With"
    )
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers.pop("Content-Security-Policy", None)
    return response


@app.route("/", methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path=""):
    response = make_response()
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With"
    )
    response.headers["X-Frame-Options"] = "ALLOWALL"
    return response, 204


sio = _socketio_module.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

_asyncio_loop: _asyncio.AbstractEventLoop | None = None
_username_player: dict = {}


def _emit_sync(event: str, data, **kwargs) -> None:
    if _asyncio_loop is not None and not _asyncio_loop.is_closed():
        _asyncio.run_coroutine_threadsafe(
            sio.emit(event, data, **kwargs), _asyncio_loop
        )


def _load_session_for_socket(environ: dict) -> dict:
    from http.cookies import SimpleCookie
    import cachelib.file as _clf

    cookie_str = environ.get("HTTP_COOKIE", "")
    if not cookie_str:
        return {}
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_str)
    except Exception:
        return {}
    session_key = app.config.get("SESSION_COOKIE_NAME", "session")
    if session_key not in cookie:
        return {}
    session_id = cookie[session_key].value
    cache = _clf.FileSystemCache(
        cache_dir=app.config["SESSION_FILE_DIR"], threshold=500, mode=0o600
    )
    try:
        data = cache.get("session:" + session_id)
        return dict(data) if isinstance(data, dict) else {}
    except Exception:
        return {}


_chat_online: dict = {}
_server_announcements: list = []
_chat_cooldowns: dict = {}
_chat_recent_msgs: dict = {}
_chat_last_content: dict = {}
_SPAM_WINDOW_SECS = 12
_SPAM_MAX_MSGS = 5

_active_sessions: dict = {}
_session_last_activity: dict = {}
_kicked_usernames: set = set()
_username_to_userid: dict = {}
_pending_tp: dict = {}
CHAT_COOLDOWN_SECS = 10
CHAT_MAX_LEN = 200

_dm_cooldowns: dict = {}
_fr_cooldowns: dict = {}
DM_COOLDOWN_SECS = 2
DM_MAX_LEN = 500
FR_MAX_PER_MINUTE = 5

_world_events: list = []
_WORLD_EVENTS_MAX = 40


def push_world_event(text: str) -> None:
    import time as _time

    _world_events.append({"t": int(_time.time()), "msg": text})
    if len(_world_events) > _WORLD_EVENTS_MAX:
        del _world_events[: len(_world_events) - _WORLD_EVENTS_MAX]


from threading import RLock as _RLock

_activity_counts: dict = {
    "battles": 0,
    "boss_kills": 0,
    "deaths": 0,
    "quests": 0,
    "dungeons": 0,
    "challenges": 0,
}
_activity_lock = _RLock()


def _is_owner(username: str) -> bool:
    return bool(username) and username.lower() == admin_get_owner()


def _is_admin_user(username: str) -> bool:
    if not username:
        return False
    uname = username.lower()
    return uname == admin_get_owner() or uname in admin_get_mods()


def _is_banned(username: str) -> bool:
    return admin_is_banned(username)


def _is_muted(username: str) -> bool:
    return admin_is_muted(username)


def _get_all_mods() -> list:
    return admin_get_all_mods()


def _warn_user_in_admins(username: str, reason: str) -> int:
    return admin_warn(username, reason)


async def _broadcast_system(message: str, to_sid=None) -> None:
    payload = {
        "username": "SYSTEM",
        "message": message,
        "created_at": _time_module.strftime(
            "%Y-%m-%dT%H:%M:%SZ", _time_module.gmtime()
        ),
        "is_system": True,
    }
    if to_sid:
        await sio.emit("chat_message", payload, to=to_sid)
    else:
        await sio.emit("chat_message", payload)


async def _handle_mod_command(sid: str, username: str, raw: str) -> bool:
    if not raw.startswith("/"):
        return False

    parts = raw.split(None, 2)
    cmd = parts[0].lower()
    is_admin = _is_admin_user(username)

    if cmd == "/help":
        lines = ["Available commands: /me <action>  /mods  /help"]
        lines.append("Admin commands are now in the console at /admin")
        for line in lines:
            await _broadcast_system(line, to_sid=sid)
        return True

    if cmd == "/mods":
        mods = _get_all_mods()
        owner_name = admin_get_owner()
        mods_str = (
            ", ".join(
                (f"{m} [Owner]" if m.lower() == owner_name else f"{m} [Mod]")
                for m in mods
            )
            or "No moderators listed."
        )
        await _broadcast_system(f"Moderators: {mods_str}", to_sid=sid)
        return True

    if cmd == "/me":
        action = " ".join(parts[1:]) if len(parts) > 1 else ""
        if not action:
            await sio.emit("chat_error", {"message": "Usage: /me <action>"}, to=sid)
            return True
        emote = f"* {username} {action}"
        result = await _asyncio.get_event_loop().run_in_executor(
            None, send_chat_message, username, emote
        )
        if result["ok"]:
            row = result["row"]
            await sio.emit(
                "chat_message",
                {
                    "username": username,
                    "message": emote,
                    "created_at": row.get("created_at", ""),
                    "is_mod": is_admin,
                    "is_emote": True,
                },
            )
        return True

    await sio.emit(
        "chat_error",
        {
            "message": f"Commands have moved to the console (/admin). Chat commands: /me /mods /help"
        },
        to=sid,
    )
    return True


def _record_activity(category: str, amount: int = 1) -> None:
    with _activity_lock:
        if category in _activity_counts:
            _activity_counts[category] += amount


_area_presence: dict = {}


def _update_area_presence(username: str, area: str, text: str) -> None:
    import time as _time2

    if username:
        _area_presence[username] = {"area": area, "text": text, "t": _time2.time()}


import re as _re

_NARRATIVE_PATTERNS = [
    (r"^battling (.+?) \[Boss\]$", lambda m: f"facing the fearsome {m.group(1)}"),
    (r"^fighting a (.+)$", lambda m: f"locked in combat with a {m.group(1)}"),
    (r"^wandering (.+)$", lambda m: f"wandering the roads of {m.group(1)}"),
    (r"^resting in (.+)$", lambda m: f"taking shelter in {m.group(1)}"),
    (r"^shopping in (.+)$", lambda m: f"browsing the market in {m.group(1)}"),
    (r"^selling gear", lambda m: "selling hard-won gear at the market"),
    (r"^using a consumable", lambda m: "tending to their wounds"),
    (r"^healing up", lambda m: "recovering strength between battles"),
    (r"^completing quest: (.+)$", lambda m: f'pursuing the quest "{m.group(1)}"'),
    (
        r"^claiming challenge: (.+)$",
        lambda m: f'claiming their reward for "{m.group(1)}"',
    ),
    (r"^delving (.+)$", lambda m: f"delving deep into {m.group(1)}"),
    (r"^building (.+) on their land$", lambda m: f"hard at work building {m.group(1)}"),
    (
        r"^beginning their legend as (.+)$",
        lambda m: f"taking their first steps as a {m.group(1)}",
    ),
    (r"^claiming an event reward$", lambda m: "claiming a rare event reward"),
]


def _narrativize(status: str) -> str:
    for pattern, fmt in _NARRATIVE_PATTERNS:
        m = _re.match(pattern, status.strip(), _re.IGNORECASE)
        if m:
            return fmt(m)
    return status.strip()


def _narrative_when(ago_secs: int) -> str:
    if ago_secs < 30:
        return "moments ago"
    elif ago_secs < 90:
        return "just a moment past"
    elif ago_secs < 150:
        return "a minute past"
    elif ago_secs < 3600:
        return f"{ago_secs // 60} minutes past"
    elif ago_secs < 7200:
        return "an hour past"
    else:
        return f"{ago_secs // 3600} hours past"


def _clear_area_presence(username: str) -> None:
    _area_presence.pop(username, None)


_active_trades: dict = {}
TRADE_MAX_ITEMS = 10
TRADE_MAX_GOLD = 9_999_999
TRADE_TIMEOUT_SECS = 300
_bg_started = False

import uuid as _uuid_mod

_WORLD_TICK_WORKER_ID: str = _uuid_mod.uuid4().hex


@app.context_processor
def _inject_chat_globals():
    return {"online_username": session.get("online_username")}


@sio.on("connect")
async def _on_chat_connect(sid, environ, auth=None):
    global _asyncio_loop, _bg_started
    sess = await _asyncio.get_event_loop().run_in_executor(
        None, _load_session_for_socket, environ
    )
    username = sess.get("online_username")
    if not username:
        await sio.disconnect(sid)
        return
    if _is_banned(username):
        await sio.emit("chat_error", {"message": "You are banned from chat."}, to=sid)
        await sio.disconnect(sid)
        return
    _asyncio_loop = _asyncio.get_event_loop()
    if not _bg_started:
        _bg_started = True
        _asyncio.create_task(_world_tick())
    _chat_online[sid] = username
    await sio.emit("online_users", sorted(set(_chat_online.values())))
    mods = _get_all_mods()
    await sio.emit("mod_list", [m.lower() for m in mods], to=sid)
    owner_name = admin_get_owner()
    await sio.emit("owner_name", owner_name, to=sid)
    await sio.emit(
        "user_flags",
        {
            "is_mod": _is_admin_user(username),
            "is_owner": _is_owner(username),
        },
        to=sid,
    )
    history = await _asyncio.get_event_loop().run_in_executor(
        None, get_chat_history, 60
    )
    await sio.emit("chat_history", history, to=sid)


@sio.on("disconnect")
async def _on_chat_disconnect(sid):
    username = _chat_online.pop(sid, None)
    await sio.emit("online_users", sorted(set(_chat_online.values())))
    if username:
        _clear_area_presence(username)
        for tid, trade in list(_active_trades.items()):
            if trade["status"] in ("pending", "active") and username in (
                trade["player_a"],
                trade["player_b"],
            ):
                other = (
                    trade["player_b"]
                    if username == trade["player_a"]
                    else trade["player_a"]
                )
                other_sids = [s for s, u in _chat_online.items() if u == other]
                for s in other_sids:
                    await sio.emit(
                        "trade_cancelled",
                        {"message": f"{username} disconnected. Trade cancelled."},
                        to=s,
                    )
                _active_trades.pop(tid, None)


@sio.on("chat_send")
async def _on_chat_send(sid, data):
    username = _chat_online.get(sid)
    if not username:
        await sio.emit(
            "chat_error", {"message": "You must be logged in to chat."}, to=sid
        )
        return

    if _is_banned(username):
        await sio.emit("chat_error", {"message": "You are banned from chat."}, to=sid)
        await sio.disconnect(sid)
        return

    raw = str(data.get("message", "")).strip()
    if not raw:
        return

    if raw.startswith("/"):
        handled = await _handle_mod_command(sid, username, raw)
        if handled:
            return

    if _is_muted(username):
        await sio.emit(
            "chat_error", {"message": "You are muted and cannot send messages."}, to=sid
        )
        return

    if len(raw) > CHAT_MAX_LEN:
        await sio.emit(
            "chat_error",
            {"message": f"Message too long (max {CHAT_MAX_LEN} chars)."},
            to=sid,
        )
        return

    now = _time_module.time()

    last_content = _chat_last_content.get(username, "")
    if raw.lower() == last_content.lower():
        await sio.emit(
            "chat_error",
            {"message": "Please don't send the same message twice."},
            to=sid,
        )
        return

    recent = _chat_recent_msgs.get(username, [])
    recent = [t for t in recent if now - t < _SPAM_WINDOW_SECS]
    if len(recent) >= _SPAM_MAX_MSGS:
        admin_mute(username, now + 5 * 60, "auto-muted for flooding", "SYSTEM")
        await sio.emit(
            "chat_error",
            {"message": "You have been auto-muted for 5 minutes for flooding."},
            to=sid,
        )
        return
    recent.append(now)
    _chat_recent_msgs[username] = recent

    last_ts = _chat_cooldowns.get(username, 0)
    remaining = int(CHAT_COOLDOWN_SECS - (now - last_ts))
    if remaining > 0:
        await sio.emit(
            "chat_error",
            {"message": f"Please wait {remaining}s before sending again."},
            to=sid,
        )
        return

    censored = censor_text(raw)
    _chat_last_content[username] = raw
    _chat_cooldowns[username] = now

    result = await _asyncio.get_event_loop().run_in_executor(
        None, send_chat_message, username, censored
    )
    if result["ok"]:
        row = result["row"]
        await sio.emit(
            "chat_message",
            {
                "username": username,
                "message": censored,
                "created_at": row.get("created_at", ""),
                "is_mod": _is_admin_user(username),
            },
        )
    else:
        await sio.emit(
            "chat_error", {"message": "Failed to send message. Try again."}, to=sid
        )


def _get_trade_for_user(trade_id: str, username: str):
    trade = _active_trades.get(trade_id)
    if not trade:
        return None
    if username not in (trade["player_a"], trade["player_b"]):
        return None
    return trade


def _trade_payload(trade: dict, viewer: str) -> dict:
    other = trade["player_b"] if viewer == trade["player_a"] else trade["player_a"]
    my_offer = trade["offer_a"] if viewer == trade["player_a"] else trade["offer_b"]
    their_offer = trade["offer_b"] if viewer == trade["player_a"] else trade["offer_a"]
    my_confirmed = (
        trade["confirmed_a"] if viewer == trade["player_a"] else trade["confirmed_b"]
    )
    their_confirmed = (
        trade["confirmed_b"] if viewer == trade["player_a"] else trade["confirmed_a"]
    )
    return {
        "trade_id": trade["id"],
        "other": other,
        "my_offer": my_offer,
        "their_offer": their_offer,
        "my_confirmed": my_confirmed,
        "their_confirmed": their_confirmed,
        "status": trade["status"],
    }


async def _emit_trade_update(trade: dict):
    a_sids = [s for s, u in _chat_online.items() if u == trade["player_a"]]
    b_sids = [s for s, u in _chat_online.items() if u == trade["player_b"]]
    for s in a_sids:
        await sio.emit("trade_update", _trade_payload(trade, trade["player_a"]), to=s)
    for s in b_sids:
        await sio.emit("trade_update", _trade_payload(trade, trade["player_b"]), to=s)


@sio.on("trade_request")
async def _on_trade_request(sid, data):
    username = _chat_online.get(sid)
    if not username:
        return
    target = str(data.get("target", "")).strip().lower()
    if not target or target == username:
        await sio.emit("trade_error", {"message": "Invalid trade target."}, to=sid)
        return
    target_sids = [s for s, u in _chat_online.items() if u == target]
    if not target_sids:
        await sio.emit("trade_error", {"message": f"{target} is not online."}, to=sid)
        return
    for t in _active_trades.values():
        if t["status"] in ("pending", "active") and username in (
            t["player_a"],
            t["player_b"],
        ):
            await sio.emit(
                "trade_error", {"message": "You already have an active trade."}, to=sid
            )
            return
        if t["status"] in ("pending", "active") and target in (
            t["player_a"],
            t["player_b"],
        ):
            await sio.emit(
                "trade_error",
                {"message": f"{target} is already in a trade."},
                to=sid,
            )
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
        await sio.emit("trade_invite", {"trade_id": trade_id, "from": username}, to=s)
    await sio.emit("trade_invite_sent", {"trade_id": trade_id, "to": target}, to=sid)


@sio.on("trade_accept")
async def _on_trade_accept(sid, data):
    username = _chat_online.get(sid)
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "pending":
        await sio.emit(
            "trade_error",
            {"message": "Trade not found or already started."},
            to=sid,
        )
        return
    if trade["player_b"] != username:
        await sio.emit(
            "trade_error", {"message": "Only the recipient can accept."}, to=sid
        )
        return
    trade["status"] = "active"
    trade["last_activity"] = _time_module.time()
    await _emit_trade_update(trade)


@sio.on("trade_decline")
async def _on_trade_decline(sid, data):
    username = _chat_online.get(sid)
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    trade = _get_trade_for_user(trade_id, username)
    if not trade:
        return
    other = trade["player_b"] if username == trade["player_a"] else trade["player_a"]
    other_sids = [s for s, u in _chat_online.items() if u == other]
    for s in other_sids:
        await sio.emit(
            "trade_cancelled", {"message": f"{username} declined the trade."}, to=s
        )
    await sio.emit("trade_cancelled", {"message": "You declined the trade."}, to=sid)
    _active_trades.pop(trade_id, None)


@sio.on("trade_add_item")
async def _on_trade_add_item(sid, data):
    username = _chat_online.get(sid)
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    item_name = str(data.get("item_name", "")).strip()
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] != "active":
        await sio.emit("trade_error", {"message": "Trade not active."}, to=sid)
        return
    my_offer_key = "offer_a" if username == trade["player_a"] else "offer_b"
    my_confirmed_key = "confirmed_a" if username == trade["player_a"] else "confirmed_b"
    if trade[my_confirmed_key]:
        await sio.emit(
            "trade_error",
            {"message": "Unconfirm your offer first to make changes."},
            to=sid,
        )
        return
    if len(trade[my_offer_key]["items"]) >= TRADE_MAX_ITEMS:
        await sio.emit(
            "trade_error",
            {"message": f"Maximum {TRADE_MAX_ITEMS} items per trade."},
            to=sid,
        )
        return
    player = _username_player.get(username)
    if not player:
        await sio.emit("trade_error", {"message": "No active character."}, to=sid)
        return
    inventory = list(player.get("inventory", []))
    already_offered = list(trade[my_offer_key]["items"])
    for offered in already_offered:
        if offered in inventory:
            inventory.remove(offered)
    if item_name not in inventory:
        await sio.emit(
            "trade_error", {"message": f"You don't have '{item_name}'."}, to=sid
        )
        return
    trade[my_offer_key]["items"].append(item_name)
    trade["last_activity"] = _time_module.time()
    await _emit_trade_update(trade)


@sio.on("trade_remove_item")
async def _on_trade_remove_item(sid, data):
    username = _chat_online.get(sid)
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
        await sio.emit(
            "trade_error",
            {"message": "Unconfirm your offer first to make changes."},
            to=sid,
        )
        return
    items = trade[my_offer_key]["items"]
    if item_name in items:
        items.remove(item_name)
    trade["last_activity"] = _time_module.time()
    await _emit_trade_update(trade)


@sio.on("trade_set_gold")
async def _on_trade_set_gold(sid, data):
    username = _chat_online.get(sid)
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
        await sio.emit(
            "trade_error",
            {"message": "Unconfirm your offer first to make changes."},
            to=sid,
        )
        return
    player = _username_player.get(username)
    if not player:
        return
    if amount > player.get("gold", 0):
        amount = player.get("gold", 0)
    trade[my_offer_key]["gold"] = amount
    trade["last_activity"] = _time_module.time()
    await _emit_trade_update(trade)


@sio.on("trade_confirm")
async def _on_trade_confirm(sid, data):
    username = _chat_online.get(sid)
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
            await sio.emit(
                "trade_approved",
                {
                    "trade_id": trade_id,
                    "receive_items": trade["offer_b"]["items"],
                    "receive_gold": trade["offer_b"]["gold"],
                    "give_items": trade["offer_a"]["items"],
                    "give_gold": trade["offer_a"]["gold"],
                },
                to=s,
            )
        for s in b_sids:
            await sio.emit(
                "trade_approved",
                {
                    "trade_id": trade_id,
                    "receive_items": trade["offer_a"]["items"],
                    "receive_gold": trade["offer_a"]["gold"],
                    "give_items": trade["offer_b"]["items"],
                    "give_gold": trade["offer_b"]["gold"],
                },
                to=s,
            )
    else:
        await _emit_trade_update(trade)


@sio.on("trade_cancel")
async def _on_trade_cancel(sid, data):
    username = _chat_online.get(sid)
    if not username:
        return
    trade_id = str(data.get("trade_id", ""))
    trade = _get_trade_for_user(trade_id, username)
    if not trade or trade["status"] not in ("pending", "active"):
        return
    other = trade["player_b"] if username == trade["player_a"] else trade["player_a"]
    other_sids = [s for s, u in _chat_online.items() if u == other]
    for s in other_sids:
        await sio.emit(
            "trade_cancelled", {"message": f"{username} cancelled the trade."}, to=s
        )
    await sio.emit("trade_cancelled", {"message": "You cancelled the trade."}, to=sid)
    _active_trades.pop(trade_id, None)


async def _expire_stale_trades():
    now = _time_module.time()
    for tid, trade in list(_active_trades.items()):
        if trade["status"] not in ("pending", "active"):
            continue
        last = trade.get("last_activity", trade.get("created_at", now))
        if now - last > TRADE_TIMEOUT_SECS:
            for p in (trade["player_a"], trade["player_b"]):
                for s, u in list(_chat_online.items()):
                    if u == p:
                        await sio.emit(
                            "trade_cancelled",
                            {
                                "message": "Trade expired due to inactivity (5 min timeout)."
                            },
                            to=s,
                        )
            _active_trades.pop(tid, None)


def _tick_world_events() -> None:
    with _activity_lock:
        counts = dict(_activity_counts)
        for k in _activity_counts:
            _activity_counts[k] = 0

    battles = counts["battles"]
    boss_kills = counts["boss_kills"]
    deaths = counts["deaths"]
    quests = counts["quests"]
    dungeons = counts["dungeons"]
    challenges = counts["challenges"]

    if sum(counts.values()) == 0:
        return

    messages: list[str] = []

    if boss_kills:
        messages.append(
            random.choice(
                [
                    "Legends are written this day. A fell power has been vanquished.",
                    "The realm trembles — a great evil has been brought low by bold hands.",
                    "Word spreads of a mighty foe slain. Bards scramble to record the tale.",
                    "Darkness retreats as a terrible beast falls before the brave.",
                ]
            )
        )

    if deaths >= 3:
        messages.append(
            random.choice(
                [
                    "The darkness claims its toll. Many brave souls have fallen this hour.",
                    "The roads run red — adventurers fall to horrors unseen and unforgiving.",
                    "Grim tidings from all corners: the monsters grow relentless.",
                    "Death walks the land. Even the boldest blades are not enough today.",
                ]
            )
        )
    elif deaths >= 1 and not boss_kills:
        messages.append(
            random.choice(
                [
                    "A brave adventurer has fallen. The realm mourns.",
                    "Death walks the land today. Stay sharp, wanderer.",
                    "Another soul lost to the wilds. The darkness grows bolder.",
                ]
            )
        )

    deeds = quests + dungeons + challenges
    if deeds >= 3:
        messages.append(
            random.choice(
                [
                    "A wave of heroism sweeps the realm — quests fulfilled, dungeons breached, challenges met.",
                    "The chronicles grow thick with deeds of valour. This is an hour of heroes.",
                    "Word of great accomplishments fills every tavern. The realm rings with legend.",
                ]
            )
        )
    elif quests:
        messages.append(
            random.choice(
                [
                    "Acts of heroism ripple across the realm. The people take heart.",
                    "Word spreads of great deeds — quests fulfilled, wrongs set right.",
                    "The notice boards grow light as bold adventurers answer every call.",
                ]
            )
        )
    elif dungeons:
        messages.append(
            random.choice(
                [
                    "Ancient depths have been breached. Secrets long buried see the light.",
                    "Dungeon delvers return triumphant, laden with hard-won spoils.",
                    "The dark places of the world yield to those bold enough to enter.",
                ]
            )
        )
    elif challenges:
        messages.append(
            random.choice(
                [
                    "Champions rise to the call — the realm's greatest trials are met.",
                    "The proving grounds ring with victory. Bold adventurers claim their honours.",
                ]
            )
        )

    if not messages and battles >= 5:
        messages.append(
            random.choice(
                [
                    "Blood is spilled across the realm. Warriors clash with darkness on every road.",
                    "The monsters grow bold — combat echoes from every corner of the land.",
                    "A fearsome tide of beasts assails the realm. Adventurers hold the line.",
                    "Steel rings and spells crack. This day belongs to the fighters.",
                ]
            )
        )

    for msg in messages[:2]:
        push_world_event(msg)


def _prune_area_presence() -> None:
    import time as _tp

    cutoff = _tp.time() - 900
    online_set = set(_chat_online.values())
    stale = [
        u for u, e in _area_presence.items() if e["t"] < cutoff or u not in online_set
    ]
    for u in stale:
        _area_presence.pop(u, None)


async def _world_tick():
    while True:
        await _asyncio.sleep(30)

        try:
            acquired = await _asyncio.get_event_loop().run_in_executor(
                None,
                try_acquire_or_renew_world_tick_lock,
                _WORLD_TICK_WORKER_ID,
                90,
            )
            if not acquired:
                continue
        except Exception:
            pass

        try:
            await _expire_stale_trades()
        except Exception:
            pass
        try:
            _tick_world_events()
        except Exception:
            pass
        try:
            _prune_area_presence()
        except Exception:
            pass


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(
        {
            "ok": False,
            "message": "Too many attempts. Please wait a moment and try again.",
        }
    ), 429


dice = Dice()

_BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(_BASE_DIR, "game_data")
_CONTENT_DIR = os.path.join(DATA_DIR, "content")
_WORLD_DIR = os.path.join(DATA_DIR, "world")
_UI_DIR = os.path.join(DATA_DIR, "ui")


def _load_json_from(path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError, KeyError):
        return {}


def _load_json_list_from(path) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, ValueError, KeyError):
        return []


def load_json(filename) -> dict[str, Any]:
    for d in (_CONTENT_DIR, _WORLD_DIR, _UI_DIR, DATA_DIR):
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return _load_json_from(p)
    return {}


def load_json_list(filename) -> list:
    for d in (_CONTENT_DIR, _WORLD_DIR, _UI_DIR, DATA_DIR):
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return _load_json_list_from(p)
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
    "splash_texts": load_json_list("splash_text.json"),
    "events": load_json("events.json").get("events", []),
    "effects": load_json("effects.json"),
}

GAME_VERSION = "2.7.2"

_PICKAXE_TIERS: dict[str, int] = {
    "Wooden Pickaxe": 1,
    "Iron Pickaxe": 2,
    "Steel Pickaxe": 3,
    "Mithril Pickaxe": 4,
}
_PICKAXE_TIER_NAMES: dict[int, str] = {v: k for k, v in _PICKAXE_TIERS.items()}
_ORE_REQUIREMENTS: dict[str, dict[str, int]] = {
    "Coal": {"pickaxe_tier": 1, "mining_level": 1},
    "Copper Ore": {"pickaxe_tier": 1, "mining_level": 1},
    "Iron Ore": {"pickaxe_tier": 1, "mining_level": 1},
    "Silver Ore": {"pickaxe_tier": 2, "mining_level": 5},
    "Gold Ore": {"pickaxe_tier": 2, "mining_level": 8},
    "Darkstone": {"pickaxe_tier": 2, "mining_level": 8},
    "Mithril Ore": {"pickaxe_tier": 3, "mining_level": 12},
    "Sunstone Crystal": {"pickaxe_tier": 3, "mining_level": 12},
    "Adamantine Ore": {"pickaxe_tier": 4, "mining_level": 16},
    "Shadowite Crystal": {"pickaxe_tier": 4, "mining_level": 20},
}
_MINING_XP_PER_RARITY: dict[str, int] = {
    "junk": 5,
    "common": 10,
    "uncommon": 30,
    "rare": 75,
    "legendary": 200,
}


def _get_mining_level(player: dict) -> int:
    import math as _m

    xp = max(0, player.get("mining_xp", 0))
    return min(25, int(_m.sqrt(xp / 50)) + 1)


def _mining_xp_for_level(level: int) -> int:
    return max(0, (level - 1) ** 2 * 50)


BUILDING_TYPES = {
    "house": {"label": "House", "slots": 3},
    "decoration": {"label": "Decoration", "slots": 10},
    "fencing": {"label": "Fencing", "slots": 1},
    "garden": {"label": "Garden", "slots": 3},
    "farming": {"label": "Farming", "slots": 2},
    "training_place": {"label": "Training Place", "slots": 3},
    "storage": {"label": "Storage", "slots": 2},
    "crafting": {"label": "Crafting", "slots": 2},
}

BUILDING_TILE_SIZES: dict[str, tuple[int, int]] = {
    "small_tent": (3, 3),
    "large_tent": (4, 4),
    "small_hut": (3, 4),
    "stone_wall_medium_house": (4, 5),
    "large_stone_house": (6, 8),
    "elven_treehouse": (3, 4),
    "large_house_with_tower": (5, 7),
    "stone_castle_with_golden_dragon_statues_and_marbled_floors": (9, 12),
    "makeshift_campfire": (2, 2),
    "stone_bench": (3, 2),
    "tribal_statue": (2, 3),
    "garden_with_fountain": (4, 4),
    "dragon_statue": (2, 3),
    "grand_stone_tower": (2, 4),
    "dragon_nest": (4, 4),
    "wooden_fence_border": (5, 2),
    "golden_gates_with_marble_walls": (4, 3),
    "small_garden": (3, 3),
    "enchanted_garden": (5, 4),
    "small_farm": (4, 3),
    "large_farm": (7, 5),
    "storage_shed": (3, 4),
    "basic_training_dummy": (3, 4),
    "advanced_gymnasium": (6, 8),
    "dwarven_forge": (3, 4),
}

EQUIPPABLE_TYPES = {"weapon", "armor", "offhand", "accessory"}

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

BOSS_CHALLENGE_COOLDOWN = 8 * 3600


def get_player() -> dict[str, Any] | None:
    return session.get("player")


def save_player(player: dict[str, Any]) -> None:
    player["visited_areas"] = list(
        set(player.get("visited_areas", []) + session.get("visited_areas", []))
    )
    session["player"] = player
    session.modified = True


def _build_game_state() -> dict[str, Any]:
    player = session.get("player")
    if not player:
        return {}
    from utilities.stats import ensure_attributes

    ensure_attributes(player)
    user_id = session.get("online_user_id")
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
        "signed_in": bool(user_id and user_id in _active_sessions),
        "save_version": "7.1",
    }


def _apply_game_state(data: dict[str, Any]) -> None:
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
    session["visited_areas"] = list(set(_va_top + _va_player)) or [
        session["current_area"]
    ]
    session["quest_progress"] = data.get("quest_progress", {})
    session["seen_cutscenes"] = data.get("seen_cutscenes", [])
    session["messages"] = data.get("messages", [])
    session["diary"] = data.get("diary", [])
    session["npc_unlocked_quests"] = data.get("npc_unlocked_quests", [])
    raw_slots = data.get("_save_slots")
    if isinstance(raw_slots, list):
        session["_save_slots"] = raw_slots
    session.modified = True


def _diary_append(text: str, color: str = "var(--text-light)") -> None:
    diary = session.get("diary", [])
    diary.append({"text": text, "color": color})
    if len(diary) > 500:
        diary = diary[-500:]
    session["diary"] = diary
    session.modified = True


_AUTOSAVE_DIARY_INTERVAL = 300


def _effective_mob_level(player_level: int) -> int:
    if player_level >= 10:
        return max(1, player_level // 10)
    return player_level


def _is_session_valid() -> bool:
    user_id = session.get("online_user_id")
    if not user_id:
        return True
    token = session.get("session_token")
    if not token:
        return False
    username = session.get("online_username", "")
    if username and username.lower() in _kicked_usernames:
        _kicked_usernames.discard(username.lower())
        _active_sessions.pop(user_id, None)
        return False
    if user_id in _active_sessions and _active_sessions[user_id] != token:
        return False
    if user_id not in _active_sessions:
        _active_sessions[user_id] = token
    _session_last_activity[user_id] = _time_module.time()
    return True


def _update_save_slot(slot: int, label: str, state: dict) -> None:
    slots = session.get("_save_slots") or [None] * 5
    if not isinstance(slots, list):
        slots = [None] * 5
    slots: list[Any] = (list(slots) + [None] * 5)[:5]
    player = state.get("player", {})
    snapshot = {k: v for k, v in state.items() if k != "_save_slots"}
    slots[slot - 1] = {
        "slot": slot,
        "label": label,
        "saved_at": _time_module.strftime("%Y-%m-%d %H:%M", _time_module.gmtime())
        + " UTC",
        "level": player.get("level", 1),
        "area": state.get("current_area", ""),
        "character_class": player.get("class", ""),
        "player_name": player.get("name", ""),
        "snapshot": snapshot,
    }
    session["_save_slots"] = slots
    session.modified = True


def _autosave() -> None:
    state = _build_game_state()
    if not state:
        return

    _update_save_slot(1, "Auto Save", state)

    user_id = session.get("online_user_id")
    if user_id:
        username = session.get("online_username")
        if username:
            _username_player[username] = state.get("player", {})
        state["_save_slots"] = session.get("_save_slots", [None] * 5)
        try:
            character_autosave(user_id, state)
        except Exception:
            pass

    now = _time_module.time()
    last_log = session.get("_last_autosave_diary_log", 0)
    if now - last_log >= _AUTOSAVE_DIARY_INTERVAL:
        _diary_append("Progress autosaved.", color="var(--muted)")
        session["_last_autosave_diary_log"] = now
        session.modified = True


def _set_activity(player: dict, status: str) -> None:
    player["activity_status"] = status
    username = session.get("online_username")
    area = session.get("current_area", "")
    if username and area:
        _update_area_presence(username, area, status)


def _group_contribute(xp_gained: int, gold_gained: int, action: str) -> None:
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
            payload = {
                "level": new_level,
                "bonus_xp": bonus_xp,
                "bonus_gold": bonus_gold,
            }
            for member in members:
                for sid in [s for s, u in _chat_online.items() if u == member]:
                    _emit_sync("group_level_up", payload, to=sid)
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


import datetime as _dt


def check_and_award_events(player):
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

        if "date" in event:
            if today_str != event["date"]:
                continue
        elif "start" in event and "end" in event:
            if not (event["start"] <= today_str <= event["end"]):
                continue
        else:
            continue

        condition = event.get("condition", {})
        ctype = condition.get("type", "none")

        if ctype == "boss_kills":
            required = condition.get("count", 1)
            if player.get("total_bosses_defeated", 0) < required:
                continue
        elif ctype == "first_login_on_date":
            pass

        rtype = event.get("reward_type", "")
        msg = event.get(
            "reward_message",
            f"You received a reward from the event '{event.get('name', '')}'!",
        )

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


def get_game_time(player=None):
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
    player["game_ticks"] = player.get("game_ticks", 0) + 1


def apply_regen_effects(player):
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
                f"The {eff.get('source', 'regeneration')} effect has faded.",
                "var(--text-dim)",
            )
    player["regen_effects"] = remaining


_WMO_TO_GAME_WEATHER = {
    0: "sunny",
    1: "sunny",
    2: "sunny",
    3: "sunny",
    45: "rainy",
    48: "rainy",
    51: "rainy",
    53: "rainy",
    55: "rainy",
    56: "rainy",
    57: "rainy",
    61: "rainy",
    63: "rainy",
    65: "rainy",
    66: "rainy",
    67: "rainy",
    71: "snowy",
    73: "snowy",
    75: "snowy",
    77: "snowy",
    80: "rainy",
    81: "rainy",
    82: "rainy",
    85: "snowy",
    86: "snowy",
    95: "stormy",
    96: "stormy",
    99: "stormy",
}

_real_weather_cache: dict = {"weather": "sunny", "fetched_at": 0.0}
_WEATHER_CACHE_TTL = 2 * 3600


def get_real_weather(area_name: str = "") -> str:
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
            pass

    return _real_weather_cache["weather"]


def get_weather_bonuses(weather_key):
    weather_def = GAME_DATA["weather"].get(weather_key, {})
    bonuses = weather_def.get("bonuses", {})
    return bonuses.get("exp_bonus", 0.0), bonuses.get("gold_bonus", 0.0)


def update_weekly_challenge(player, event_type, amount=1):
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


def get_boss_dialogue(boss_key, timing):
    return GAME_DATA["dialogues"].get(f"{boss_key}.boss.{timing}", "")


def get_boss_phase(phases, hp_pct):
    if not phases:
        return 0, {}
    sorted_desc = sorted(phases, key=lambda p: -p.get("hp_threshold", 1.0))
    for i, phase in enumerate(sorted_desc):
        if hp_pct >= phase.get("hp_threshold", 1.0):
            return i, phase
    return len(sorted_desc) - 1, sorted_desc[-1]


def _enemy_take_turn(enemy, player, player_effects, log, battle_companions=None):
    if enemy.get("is_boss"):
        boss_take_turn(enemy, player, player_effects, log)
        return

    living_companions = [c for c in (battle_companions or []) if c.get("hp", 0) > 0]
    targets = ["player"] + [c["id"] for c in living_companions]
    chosen = random.choice(targets)

    if chosen != "player" and living_companions:
        comp = next((c for c in living_companions if c["id"] == chosen), None)
        if comp:
            c_dmg = max(1, enemy["attack"] - comp["defense"] + dice.between(-2, 4))
            comp["hp"] = max(0, comp["hp"] - c_dmg)
            if comp["hp"] == 0:
                log.append(
                    f"The {enemy['name']} strikes {comp['name']} for {c_dmg} damage — "
                    f"{comp['name']} has fallen!"
                )
            else:
                log.append(
                    f"The {enemy['name']} attacks {comp['name']} for {c_dmg} damage! "
                    f"({comp['hp']}/{comp['max_hp']} HP remaining)"
                )
            return

    evasion_pct = player.get("attr_evasion", 0) / 100.0
    dodge = player.get("dodge_chance", 0.0) + evasion_pct
    if dodge > 0 and random.random() < dodge:
        log.append(f"You evade the {enemy['name']}'s attack!")
        return
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
    result = {"used_ability": None, "phase_changed": False, "new_phase_desc": None}

    boss_key = enemy.get("key", "")
    boss_data = GAME_DATA["bosses"].get(boss_key, {}) if boss_key else {}
    phases = boss_data.get("phases", [])
    abilities = boss_data.get("special_abilities", [])

    hp_pct = enemy["hp"] / max(1, enemy["max_hp"])
    phase_idx, phase_data = get_boss_phase(phases, hp_pct)

    prev_phase_idx = enemy.get("_phase_idx", 0)
    if phase_idx != prev_phase_idx and phases:
        enemy["_phase_idx"] = phase_idx
        desc = phase_data.get("description", "")
        result["phase_changed"] = True
        result["new_phase_desc"] = desc
        log.append(f"{enemy['name']} enters a new phase! {desc}")

    if "_base_attack" not in enemy:
        enemy["_base_attack"] = enemy["attack"]
        enemy["_base_defense"] = enemy["defense"]

    raw_atk_mult = phase_data.get("attack_multiplier", 1.0)
    raw_def_mult = phase_data.get("defense_multiplier", 1.0)
    atk_mult = 1.0 + (raw_atk_mult - 1.0) * 0.5
    def_mult = 1.0 + (raw_def_mult - 1.0) * 0.5
    enemy["attack"] = max(1, int(enemy["_base_attack"] * atk_mult))
    enemy["defense"] = max(0, int(enemy["_base_defense"] * def_mult))

    cooldowns = enemy.get("_ability_cooldowns", {})
    for ab_name in list(cooldowns.keys()):
        if cooldowns[ab_name] > 0:
            cooldowns[ab_name] -= 1
    enemy["_ability_cooldowns"] = cooldowns

    unlocked = set()
    if phases and phase_data.get("special_abilities_unlocked"):
        unlocked = set(phase_data["special_abilities_unlocked"])
    if not unlocked and abilities:
        unlocked = {ab["name"] for ab in abilities}

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
            raw = max(
                1, int((dmg - player["defense"] // 2 + dice.between(-3, 5)) * 0.8)
            )
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


_COMPANION_RANK_HP = {
    "common": 4000,
    "uncommon": 7500,
    "rare": 13000,
    "epic": 20000,
    "legendary": 32000,
}

_COMPANION_RANK_ATK_CAP = {
    "common": 800,
    "uncommon": 1400,
    "rare": 2200,
    "epic": 3200,
    "legendary": 5000,
}

_COMPANION_RANK_DEF_CAP = {
    "common": 280,
    "uncommon": 480,
    "rare": 720,
    "epic": 1050,
    "legendary": 1600,
}


def _get_companion_combat_stats(comp_entry):
    comp_id = comp_entry.get("id", "")
    comp_data = GAME_DATA["companions"].get(comp_id, {})
    rank = comp_data.get("rank", "common")
    max_hp = _COMPANION_RANK_HP.get(rank, 400)
    atk_cap = _COMPANION_RANK_ATK_CAP.get(rank, 120)
    def_cap = _COMPANION_RANK_DEF_CAP.get(rank, 40)
    atk_bonus = comp_data.get("attack_bonus", 0)
    def_bonus = comp_data.get("defense_bonus", 0)
    crit_bonus = comp_data.get("crit_damage_bonus", 0)
    base_atk = atk_bonus * 40 + 500 + crit_bonus // 2
    base_def = def_bonus * 28 + 180
    return {
        "id": comp_id,
        "name": comp_entry.get("name", comp_data.get("name", "Companion")),
        "hp": comp_entry.get("hp", max_hp),
        "max_hp": comp_entry.get("max_hp", max_hp),
        "attack": min(atk_cap, base_atk),
        "defense": min(def_cap, base_def),
        "action_chance": min(0.95, comp_data.get("action_chance", 0.82)),
        "crit_chance": min(0.60, comp_data.get("crit_chance", 0) / 100.0 + 0.12),
        "fallen": comp_entry.get("fallen", False),
    }


def _build_battle_companions(player):
    return [
        _get_companion_combat_stats(c)
        for c in player.get("companions", [])
        if isinstance(c, dict) and not c.get("fallen", False)
    ]


def _companion_take_action(battle_companions, enemy, log):
    for comp in battle_companions:
        if comp["hp"] <= 0:
            continue
        if random.random() > comp.get("action_chance", 0.40):
            continue
        dmg = max(1, comp["attack"] - enemy["defense"] + dice.between(-3, 6))
        comp_crit_rate = 0.20 + comp.get("crit_chance", 0.0)
        if random.random() < comp_crit_rate:
            dmg = int(dmg * 3.5)
            log.append(
                f"[{comp['name']} lands a critical blow on {enemy['name']} for {dmg}!]"
            )
        else:
            log.append(f"[{comp['name']} attacks {enemy['name']} for {dmg} damage.]")
        enemy["hp"] = max(0, enemy["hp"] - dmg)
        if enemy["hp"] <= 0:
            return True
    return False


def _companion_last_stand(battle_companions, enemy, log):
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
    hp_map = {c["id"]: c["hp"] for c in battle_companions}
    for comp in player.get("companions", []):
        if isinstance(comp, dict) and comp.get("id") in hp_map:
            new_hp = max(0, hp_map[comp["id"]])
            comp["hp"] = new_hp
            if new_hp <= 0:
                comp["fallen"] = True


def _restore_companion_hp(player):
    for comp in player.get("companions", []):
        if (
            isinstance(comp, dict)
            and "max_hp" in comp
            and not comp.get("fallen", False)
        ):
            comp["hp"] = comp["max_hp"]


def _revive_companions(player):
    revived = []
    for comp in player.get("companions", []):
        if isinstance(comp, dict) and comp.get("fallen", False):
            comp["fallen"] = False
            stats = _get_companion_combat_stats(comp)
            comp["hp"] = stats["max_hp"]
            comp["max_hp"] = stats["max_hp"]
            revived.append(comp.get("name", "Companion"))
    return revived


def _ensure_companion_hp(player):
    for comp in player.get("companions", []):
        if not isinstance(comp, dict):
            continue
        stats = _get_companion_combat_stats(comp)
        new_max = stats["max_hp"]
        if "max_hp" not in comp:
            comp["hp"] = new_max
            comp["max_hp"] = new_max
        elif comp.get("max_hp", 0) < new_max and not comp.get("fallen", False):
            comp["max_hp"] = new_max
            comp["hp"] = new_max


def trigger_cutscene(cutscene_id):
    seen = session.get("seen_cutscenes", [])
    cutscene_def = GAME_DATA["cutscenes"].get(cutscene_id)
    if cutscene_def and not cutscene_def.get("iterable", True) and cutscene_id in seen:
        return
    session["pending_cutscene"] = cutscene_id
    session.modified = True


def apply_status_effect(effects_dict, effect_key, turns=None):
    effect_def = load_json("effects.json").get(effect_key, {})
    duration = turns or effect_def.get("duration", 3)
    effects_dict[effect_key] = {
        "turns": duration,
        "data": effect_def,
    }


def process_turn_effects(
    entity, effects_dict, log, entity_label, is_enemy=False, player_level=1
):
    to_remove = []
    stunned = False
    for eff_key, eff_info in list(effects_dict.items()):
        data = eff_info.get("data", eff_info)
        eff_type = data.get("type", "")

        if eff_type == "damage_over_time":
            dmg = data.get("damage", 5)
            entity["hp"] = max(0, entity["hp"] - dmg)
            log.append(
                f"{entity_label} takes {dmg} {eff_key} damage! ({max(0, eff_info['turns'] - 1)} turns left)"
            )
        elif eff_type == "healing_over_time":
            heal_base = data.get("heal_amount", 8)
            if is_enemy:
                scale = max(0.25, 1.0 - player_level * 0.03)
                heal = max(1, int(heal_base * scale))
            else:
                heal = heal_base
            entity["hp"] = min(entity.get("max_hp", entity["hp"]), entity["hp"] + heal)
            log.append(f"{entity_label} regenerates {heal} HP!")
        elif eff_type == "action_block":
            stunned = True
            log.append(f"{entity_label} is stunned and cannot act!")

        elif eff_key == "bleed":
            dmg = eff_info.get("damage", 6)
            entity["hp"] = max(0, entity["hp"] - dmg)
            turns_left = max(0, eff_info["turns"] - 1)
            log.append(
                f"{entity_label} bleeds for {dmg} damage! ({turns_left} turns left)"
            )

        elif eff_key == "daze":
            stunned = True
            log.append(f"{entity_label} is dazed and cannot act this turn!")

        elif eff_key == "weaken":
            turns_left = max(0, eff_info["turns"] - 1)
            if turns_left > 0:
                log.append(
                    f"{entity_label}'s defences remain weakened! ({turns_left} turns left)"
                )

        elif eff_key == "shaken":
            turns_left = max(0, eff_info["turns"] - 1)
            if turns_left > 0:
                log.append(f"{entity_label} is still shaken! ({turns_left} turns left)")

        elif eff_key == "armor_crushed":
            turns_left = max(0, eff_info["turns"] - 1)
            if turns_left > 0:
                log.append(
                    f"{entity_label}'s armour remains crushed! ({turns_left} turns left)"
                )

        eff_info["turns"] -= 1
        if eff_info["turns"] <= 0:
            to_remove.append(eff_key)
            if eff_type == "stat_boost":
                for stat_key in ("defense_bonus", "attack_bonus", "speed_bonus"):
                    if stat_key in data:
                        stat = stat_key.replace("_bonus", "")
                        entity[stat] = max(1, entity.get(stat, 0) - data[stat_key])

    for k in to_remove:
        effects_dict.pop(k, None)

    return stunned


STAT_BONUSES = [
    ("attack_bonus", "attack", 1),
    ("defense_bonus", "defense", 1),
    ("speed_bonus", "speed", 1),
    ("hp_bonus", "max_hp", 1),
    ("mp_bonus", "max_mp", 1),
    ("defense_penalty", "defense", -1),
    ("speed_penalty", "speed", -1),
    ("spell_power_bonus", "attr_spell_power", 1),
    ("evasion_bonus", "attr_evasion", 1),
    ("spell_power", "attr_spell_power", 1),
    ("crit_chance", "attr_crit_chance", 1),
]


def apply_item_bonuses(player, item_data, direction=1):
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

    res_keys = (
        "physical_resistance",
        "fire_resistance",
        "ice_resistance",
        "lightning_resistance",
        "poison_resistance",
        "magic_resistance",
    )
    for rk in res_keys:
        val = item_data.get(rk, 0.0)
        if val:
            current = player.get(rk, 0.0)
            player[rk] = max(0.0, min(0.9, current + val * direction))

    if item_data.get("type") == "weapon":
        tags = item_data.get("tags", [])
        if "outlaw" in tags:
            dodge_bonus = 0.06
            player["dodge_chance"] = round(
                max(0.0, player.get("dodge_chance", 0.0) + dodge_bonus * direction), 4
            )


def _ensure_equipment_slots(player):
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
    if "accessory" in player["equipment"]:
        old_val = player["equipment"].pop("accessory")
        if old_val and not player["equipment"].get("accessory_1"):
            player["equipment"]["accessory_1"] = old_val


def equip_item(player, item_name):
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

    if item_type == "accessory":
        slot = None
        for i in range(1, 4):
            s = f"accessory_{i}"
            if not equipment.get(s):
                slot = s
                break
        if not slot:
            slot = "accessory_1"
    else:
        slot = item_type

    current = equipment.get(slot)
    if current:
        cur_data = GAME_DATA["items"].get(current, {})
        if isinstance(cur_data, dict):
            apply_item_bonuses(player, cur_data, direction=-1)
        player["inventory"].append(current)

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
    items_data: dict[str, Any] = GAME_DATA["items"]
    player_level = player.get("level", 1)
    player_class = player.get("class", "")
    _ensure_equipment_slots(player)
    equipment = player["equipment"]

    for slot in list(equipment.keys()):
        current = equipment.get(slot)
        if current:
            equipment[slot] = None
            player["inventory"].append(current)
            item_d = items_data.get(current, {})
            if isinstance(item_d, dict):
                apply_item_bonuses(player, item_d, direction=-1)

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

    for slot in ("weapon", "armor", "offhand"):
        candidates = slot_candidates.get(slot, [])
        if not candidates:
            continue
        best = max(candidates, key=lambda n: _item_score(items_data.get(n, {})))
        ok, msg = equip_item(player, best)
        if ok:
            messages.append(msg)

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


def get_quest_progress(mission_id):
    return session.get("quest_progress", {}).get(mission_id, {})


def update_quest_kills(enemy_key, enemy_name):
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
    return send_from_directory("game_data/assets", filename)


@app.route("/ping")
def health_ping():
    from flask import jsonify as _jsonify

    return _jsonify({"status": "ok"}), 200


@app.route("/api/announcements")
def api_announcements():
    from flask import jsonify as _jsonify

    return _jsonify(
        {"announcements": [{"ts": ts, "text": t} for ts, t in _server_announcements]}
    ), 200


@app.route("/chat")
def chat_page():
    username = session.get("online_username")
    if not username:
        return redirect(url_for("index"))
    return render_template("chat.html", online_username=username)


@app.route("/chat_widget")
def chat_widget_page():
    username = session.get("online_username")
    if not username:
        return ("Unauthorized", 401)
    return render_template("chat_widget.html", online_username=username)


@app.route("/")
def index():
    if not os.path.exists("sacred_text_hahahhahahahahahahaah.txt"):
        return render_template("sacred_text_gone.html")
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
        online_count=len(_active_sessions),
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
            "stored_items": [],
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


def _build_land_data(player: dict) -> dict:
    """Build the land_data dict for 'your_land' area."""
    housing_data: dict[str, Any] = GAME_DATA["housing"]
    farming_data: dict[str, Any] = GAME_DATA["farming"].get("crops", {})
    pets_data: dict[str, Any] = GAME_DATA["pets"]
    owned_set = set(player.get("housing_owned", []))
    building_slots = player.get("building_slots", {})
    crops = player.get("crops", {})

    housing_by_type: dict[str, list] = {}
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

    placed_by_type: dict[str, list] = {}
    building_positions_raw = player.get("building_positions", {})
    placed_buildings_map: list = []
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
            pos = building_positions_raw.get(slot_id, {})
            placed_buildings_map.append(
                {
                    "slot_id": slot_id,
                    "key": h_key,
                    "name": h_item.get("name", h_key),
                    "type": h_item.get("type", "decoration"),
                    "x": pos.get("x", -1),
                    "y": pos.get("y", -1),
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
    has_garden = any(k.startswith("garden") and v for k, v in building_slots.items())
    has_house = any(k.startswith("house") and v for k, v in building_slots.items())
    has_storage = any(k.startswith("storage") and v for k, v in building_slots.items())
    has_crafting = any(
        k.startswith("crafting") and v for k, v in building_slots.items()
    )
    has_farming = any(k.startswith("farming") and v for k, v in building_slots.items())
    storage_capacity = (
        sum(1 for k, v in building_slots.items() if k.startswith("storage") and v) * 10
    )

    inventory_counts: dict[str, int] = {}
    for item in player.get("inventory", []):
        inventory_counts[item] = inventory_counts.get(item, 0) + 1

    all_recipes = GAME_DATA.get("crafting", {}).get("recipes", {})
    crafting_recipes = []
    for r_key, recipe in all_recipes.items():
        materials = recipe.get("materials", {})
        can_craft = all(
            inventory_counts.get(mat, 0) >= qty for mat, qty in materials.items()
        )
        crafting_recipes.append(
            {
                "key": r_key,
                "name": recipe.get("name", r_key),
                "description": recipe.get("description", ""),
                "category": recipe.get("category", ""),
                "output": recipe.get("output", {}),
                "materials": materials,
                "rarity": recipe.get("rarity", "common"),
                "can_craft": can_craft,
                "have": {mat: inventory_counts.get(mat, 0) for mat in materials},
            }
        )

    return {
        "housing_by_type": housing_by_type,
        "placed_by_type": placed_by_type,
        "placed_buildings_map": placed_buildings_map,
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
        "has_house": has_house,
        "has_storage": has_storage,
        "has_crafting": has_crafting,
        "has_farming": has_farming,
        "stored_items": player.get("stored_items", []),
        "storage_capacity": storage_capacity,
        "crafting_recipes": crafting_recipes,
    }


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
            "index.html",
            show_create=True,
            data=GAME_DATA,
            create_error=create_error,
            world_events=list(reversed(_world_events[-8:])),
        )

    username_key = (session.get("online_username") or "").lower()
    if username_key and username_key in _pending_tp:
        tp_dest = _pending_tp.pop(username_key)
        if tp_dest in GAME_DATA.get("areas", {}):
            session["current_area"] = tp_dest
            va = session.get("visited_areas", [])
            if tp_dest not in va:
                va.append(tp_dest)
                session["visited_areas"] = va
            tp_area_name = GAME_DATA["areas"][tp_dest].get("name", tp_dest)
            add_message(f"You have been teleported to {tp_area_name}.", "var(--gold)")
        session.modified = True

    _game_user_id = session.get("online_user_id")
    _user_has_email = True
    _user_email_pending = None
    if _game_user_id:
        _user_has_email = bool(get_user_email(_game_user_id))
        if not _user_has_email:
            _user_email_pending = get_pending_email_verification(_game_user_id)

    events_awarded = check_and_award_events(player)
    save_player(player)
    if events_awarded:
        _set_activity(player, "claiming an event reward")
        _autosave()

    _ensure_companion_hp(player)

    enemy: dict[str, Any] = session.get("battle_enemy") or {}
    if enemy:
        battle_log = session.get("battle_log", [])
        _items_data = GAME_DATA["items"]
        usable_items = [
            i
            for i in player.get("inventory", [])
            if any(x in i.lower() for x in ["potion", "elixir", "tears", "tonic"])
            or isinstance(_items_data.get(i), dict)
            and _items_data[i].get("event_item")
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
            online_user=session.get("online_username"),
            user_has_email=_user_has_email,
            user_email_pending=_user_email_pending,
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
                "name": conn_area.get("name", conn_key.replace("_", " ").title())
                if is_visited
                else "???",
                "has_danger": bool(conn_area.get("possible_enemies"))
                if is_visited
                else None,
                "visited": is_visited,
                "difficulty": difficulty if is_visited else -1,
            }
        )

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
            }
        )

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
                    "weapon_type": item_data.get("weapon_type", "")
                    if slot == "weapon"
                    else "",
                }

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
        building_positions_raw = player.get("building_positions", {})
        placed_buildings_map: list[Any] = []
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
                pos = building_positions_raw.get(slot_id, {})
                placed_buildings_map.append(
                    {
                        "slot_id": slot_id,
                        "key": h_key,
                        "name": h_item.get("name", h_key),
                        "type": h_item.get("type", "decoration"),
                        "x": pos.get("x", -1),
                        "y": pos.get("y", -1),
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
        has_house = any(k.startswith("house") and v for k, v in building_slots.items())
        has_storage = any(
            k.startswith("storage") and v for k, v in building_slots.items()
        )
        has_crafting = any(
            k.startswith("crafting") and v for k, v in building_slots.items()
        )
        has_farming = any(
            k.startswith("farming") and v for k, v in building_slots.items()
        )

        storage_capacity = (
            sum(1 for k, v in building_slots.items() if k.startswith("storage") and v)
            * 10
        )

        inventory_counts: dict[str, int] = {}
        for item in player.get("inventory", []):
            inventory_counts[item] = inventory_counts.get(item, 0) + 1

        all_recipes = GAME_DATA.get("crafting", {}).get("recipes", {})
        crafting_recipes = []
        for r_key, recipe in all_recipes.items():
            materials = recipe.get("materials", {})
            can_craft = all(
                inventory_counts.get(mat, 0) >= qty for mat, qty in materials.items()
            )
            crafting_recipes.append(
                {
                    "key": r_key,
                    "name": recipe.get("name", r_key),
                    "description": recipe.get("description", ""),
                    "category": recipe.get("category", ""),
                    "output": recipe.get("output", {}),
                    "materials": materials,
                    "rarity": recipe.get("rarity", "common"),
                    "can_craft": can_craft,
                    "have": {mat: inventory_counts.get(mat, 0) for mat in materials},
                }
            )

        land_data = {
            "housing_by_type": housing_by_type,
            "placed_by_type": placed_by_type,
            "placed_buildings_map": placed_buildings_map,
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
            "has_house": has_house,
            "has_storage": has_storage,
            "has_crafting": has_crafting,
            "has_farming": has_farming,
            "stored_items": player.get("stored_items", []),
            "storage_capacity": storage_capacity,
            "crafting_recipes": crafting_recipes,
        }

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
                    "fallen": comp.get("fallen", False),
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

    game_time = get_game_time()
    game_time_icon = TIME_ICONS.get(game_time, "")
    area_name_for_weather = (
        GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "")
    )
    current_weather = get_real_weather(area_name_for_weather)
    weather_def = GAME_DATA["weather"].get(current_weather, {})
    weather_display = current_weather.replace("_", " ").title()
    weather_icon = ""
    weather_bonus_exp = int(weather_def.get("bonuses", {}).get("exp_bonus", 0) * 100)
    weather_bonus_gold = int(weather_def.get("bonuses", {}).get("gold_bonus", 0) * 100)

    challenges_display = build_challenges_display(player)

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

    mine_data = None
    mine_pool = area.get("mine_pool", [])
    if mine_pool:
        player_inv = player.get("inventory", [])
        best_pickaxe_tier = max(
            (_PICKAXE_TIERS.get(i, 0) for i in player_inv), default=0
        )
        best_pickaxe_name = next(
            (
                i
                for i in reversed(player_inv)
                if _PICKAXE_TIERS.get(i, 0) == best_pickaxe_tier
            ),
            None,
        )
        mining_lvl = _get_mining_level(player)
        mining_xp_total = player.get("mining_xp", 0)
        cur_lvl_xp = _mining_xp_for_level(mining_lvl)
        next_lvl_xp = _mining_xp_for_level(mining_lvl + 1)
        xp_span = max(1, next_lvl_xp - cur_lvl_xp)
        xp_progress = mining_xp_total - cur_lvl_xp
        xp_pct = min(100, int(xp_progress / xp_span * 100)) if mining_lvl < 25 else 100

        mine_items = []
        for ore_name, req in _ORE_REQUIREMENTS.items():
            ore_item = GAME_DATA["items"].get(ore_name, {})
            if not isinstance(ore_item, dict):
                continue
            accessible = (
                best_pickaxe_tier >= req["pickaxe_tier"]
                and mining_lvl >= req["mining_level"]
            )
            if not accessible:
                if best_pickaxe_tier < req["pickaxe_tier"]:
                    blocked_by = f"Needs {_PICKAXE_TIER_NAMES.get(req['pickaxe_tier'], 'better pickaxe')}"
                else:
                    blocked_by = f"Mining Lv.{req['mining_level']}"
            else:
                blocked_by = None
            mine_items.append(
                {
                    "name": ore_name,
                    "rarity": ore_item.get("rarity", "common"),
                    "description": ore_item.get("description", ""),
                    "price": ore_item.get("price", 5),
                    "accessible": accessible,
                    "blocked_by": blocked_by,
                }
            )
        if mine_items:
            mine_data = {
                "pool": mine_items,
                "mining_level": mining_lvl,
                "mining_xp": mining_xp_total,
                "xp_progress": xp_progress,
                "xp_needed": xp_span,
                "xp_pct": xp_pct,
                "has_pickaxe": best_pickaxe_tier > 0,
                "best_pickaxe": best_pickaxe_name,
                "best_tier": best_pickaxe_tier,
            }

    pending_cutscene_id = session.get("pending_cutscene")
    pending_cutscene = None
    if pending_cutscene_id:
        cs = GAME_DATA["cutscenes"].get(pending_cutscene_id)
        if cs:
            pending_cutscene = {
                "id": pending_cutscene_id,
                "content": cs.get("content", {}),
            }

    crafting_data: dict[str, Any] = GAME_DATA.get("crafting", {})
    raw_recipes = get_recipes(crafting_data)
    crafting_recipes = []
    for recipe in raw_recipes:
        check = check_recipe_craftable(player, recipe)
        crafting_recipes.append(
            {**recipe, "can_craft": check["ok"], "missing": check.get("missing", [])}
        )

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

    dungeons_data: dict[str, Any] = GAME_DATA.get("dungeons", {})
    completed_dungeons_set = set(player.get("completed_dungeons", []))
    visited_areas_list = session.get("visited_areas", [area_key])
    dungeon_list = get_available_dungeons(
        dungeons_data,
        area_key,
        player.get("level", 1),
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
        areas_data=GAME_DATA.get("areas", {}),
        visited_areas=visited_areas,
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
        mine_data=mine_data,
        online_user=session.get("online_username"),
        events_data=events_data,
        game_classes=list(GAME_DATA.get("classes", {}).keys()),
        game_races=list(GAME_DATA.get("races", {}).keys()),
        world_events=list(reversed(_world_events[-10:]))
        if session.get("online_username")
        else [],
        online_count=len(set(_chat_online.values())),
        user_has_email=_user_has_email,
        user_email_pending=_user_email_pending,
    )


def _item_stat_summary(item_data):
    if not isinstance(item_data, dict):
        return ""
    parts = []
    itype = item_data.get("type", "")

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
                parts.append(
                    f"{val}% {label}"
                    if "chance" in proc_key
                    or proc_key == "armor_penetration"
                    or proc_key == "mana_efficiency"
                    else f"+{val} {label}"
                )

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
    equipment = player.get("equipment", {})
    weapon_name = equipment.get("weapon")
    if not weapon_name:
        return []
    weapon = GAME_DATA["items"].get(weapon_name)
    if not isinstance(weapon, dict):
        return []

    enemy_tags = set(enemy.get("tags", []))
    effects = []

    sharpness = weapon.get("sharpness", 0)
    if sharpness:
        if "humanoid" in enemy_tags or "beast" in enemy_tags:
            bonus = int(sharpness * 1.5)
            effects.append(
                (bonus, f"Your blade bites deep! +{bonus} sharpness damage.")
            )
        elif "armored" in enemy_tags or "construct" in enemy_tags:
            bonus = max(1, int(sharpness * 0.4))
            effects.append(
                (bonus, f"Your blade skips off the armour. +{bonus} damage.")
            )
        else:
            bonus = sharpness
            effects.append((bonus, f"Your weapon's edge adds {bonus} cutting damage."))

    smiting = weapon.get("smiting", 0)
    if smiting:
        if "undead" in enemy_tags or "demon" in enemy_tags:
            bonus = int(smiting * 2.5)
            effects.append(
                (
                    bonus,
                    f"Holy power surges! +{bonus} smiting damage vs {enemy['name']}!",
                )
            )
        elif "holy" in enemy_tags:
            bonus = 0
            effects.append((0, f"Smiting has no effect on holy beings."))
        else:
            bonus = smiting
            effects.append((bonus, f"+{bonus} blessed damage."))

    fire_atk = weapon.get("fire_attack", 0)
    if fire_atk:
        if "ice" in enemy_tags or "cold" in enemy_tags:
            bonus = int(fire_atk * 2.0)
            effects.append((bonus, f"Fire melts the ice! +{bonus} fire damage!"))
        elif "fire" in enemy_tags:
            bonus = max(0, int(fire_atk * 0.2))
            if bonus:
                effects.append(
                    (bonus, f"The flame barely stings. +{bonus} fire damage.")
                )
        else:
            bonus = fire_atk
            effects.append((bonus, f"Your weapon blazes! +{bonus} fire damage."))

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

    lightning_atk = weapon.get("lightning_attack", 0)
    if lightning_atk:
        if "armored" in enemy_tags or "construct" in enemy_tags:
            bonus = int(lightning_atk * 1.8)
            effects.append(
                (
                    bonus,
                    f"Lightning conducts through armour! +{bonus} lightning damage!",
                )
            )
        elif "elemental" in enemy_tags and "lightning" in enemy_tags:
            bonus = max(0, int(lightning_atk * 0.2))
            if bonus:
                effects.append(
                    (bonus, f"Lightning feeds the elemental. +{bonus} damage.")
                )
        else:
            bonus = lightning_atk
            effects.append((bonus, f"A bolt of lightning! +{bonus} lightning damage."))

    poison_atk = weapon.get("poison_attack", 0)
    if poison_atk:
        if "construct" in enemy_tags or "undead" in enemy_tags:
            bonus = max(0, int(poison_atk * 0.3))
            if bonus:
                effects.append(
                    (bonus, f"The poison has little effect. +{bonus} damage.")
                )
        elif "beast" in enemy_tags or "humanoid" in enemy_tags:
            bonus = int(poison_atk * 1.4)
            effects.append((bonus, f"Venom courses through! +{bonus} poison damage!"))
        else:
            bonus = poison_atk
            effects.append((bonus, f"Poison seeps in. +{bonus} poison damage."))

    return effects


def _get_weapon_on_hit_procs(player, enemy, enemy_effects):
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

    bleed_chance = weapon.get("bleed_chance", 0)
    if bleed_chance and _roll(bleed_chance):
        if "construct" not in enemy_tags and "undead" not in enemy_tags:
            stacks = enemy_effects.get("bleed", {}).get("stacks", 0)
            enemy_effects["bleed"] = {
                "turns": 4,
                "damage": 6 + stacks * 2,
                "stacks": min(stacks + 1, 3),
            }
            messages.append(
                f"Your blade opens a deep wound! [{enemy.get('name', 'Enemy')} is bleeding]"
            )

    stun_chance = weapon.get("stun_chance", 0)
    if stun_chance and _roll(stun_chance):
        if "construct" not in enemy_tags:
            existing = enemy_effects.get("daze", {}).get("turns", 0)
            enemy_effects["daze"] = {"turns": max(1, existing + 1)}
            messages.append(
                f"Your crushing blow dazes {enemy.get('name', 'the enemy')}! [Dazed — loses next action]"
            )

    cleave_chance = weapon.get("cleave_chance", 0)
    if cleave_chance and _roll(cleave_chance):
        pen = weapon.get("armor_penetration", 10)
        existing = enemy_effects.get("weaken", {}).get("turns", 0)
        enemy_effects["weaken"] = {
            "turns": max(existing, 4),
            "def_reduction": max(
                enemy_effects.get("weaken", {}).get("def_reduction", 0), int(pen * 0.6)
            ),
        }
        messages.append(
            f"Your cleaving strike weakens {enemy.get('name', 'the enemy')}'s defences! [-{int(pen * 0.6)} DEF for 4 turns]"
        )

    knockback_chance = weapon.get("knockback_chance", 0)
    if knockback_chance and _roll(knockback_chance):
        enemy_effects["shaken"] = {"turns": 3, "acc_penalty": 20}
        messages.append(
            f"{enemy.get('name', 'The enemy')} is knocked back and shaken! [-20% accuracy for 3 turns]"
        )

    sweep_chance = weapon.get("sweep_chance", 0)
    if sweep_chance and _roll(sweep_chance):
        sweep_dmg = max(1, int(player.get("attack", 10) * 0.35))
        enemy["hp"] = max(0, enemy.get("hp", 1) - sweep_dmg)
        messages.append(
            f"Your sweeping blow strikes again for {sweep_dmg} bonus damage!"
        )

    multi_hit_chance = weapon.get("multi_hit_chance", 0)
    if multi_hit_chance and _roll(multi_hit_chance):
        hit_dmg = max(1, int(player.get("attack", 10) * 0.25))
        enemy["hp"] = max(0, enemy.get("hp", 1) - hit_dmg)
        messages.append(f"Your second projectile strikes for {hit_dmg} extra damage!")

    parry_chance = weapon.get("parry_chance", 0)
    if parry_chance and _roll(parry_chance):
        existing_buffs = player.get("active_buffs", [])
        existing_buffs.append(
            {
                "name": "Parry",
                "duration": 2,
                "modifiers": {"defense_bonus": 10, "absorb_amount": 15},
            }
        )
        player["active_buffs"] = existing_buffs
        messages.append(
            "You deflect the next blow with expert swordsmanship! [Parry: +10 DEF, absorbs 15 dmg for 2 turns]"
        )

    inspire_chance = weapon.get("inspire_chance", 0)
    if inspire_chance and _roll(inspire_chance):
        inspire_bonus = weapon.get("harmony_bonus", 8)
        existing_buffs = player.get("active_buffs", [])
        existing_buffs.append(
            {
                "name": "Inspire",
                "duration": 6,
                "modifiers": {
                    "attack_bonus": inspire_bonus,
                    "speed_bonus": int(inspire_bonus * 0.5),
                },
            }
        )
        player["active_buffs"] = existing_buffs
        messages.append(
            f"Your melody inspires courage! [+{inspire_bonus} ATK, +{int(inspire_bonus * 0.5)} SPD for 6 turns]"
        )

    armor_crush = weapon.get("armor_crush", 0)
    if armor_crush and _roll(20):
        existing = enemy_effects.get("armor_crushed", {}).get("def_reduction", 0)
        enemy_effects["armor_crushed"] = {
            "turns": 5,
            "def_reduction": existing + armor_crush,
        }
        messages.append(
            f"You crush through the armour! [{enemy.get('name', 'Enemy')} defence -{armor_crush} for 5 turns]"
        )

    backstab_bonus = weapon.get("backstab_bonus", 0)
    if backstab_bonus and ("shaken" in enemy_effects or "daze" in enemy_effects):
        enemy["hp"] = max(0, enemy.get("hp", 1) - backstab_bonus)
        messages.append(
            f"You exploit the opening for a deadly backstab! +{backstab_bonus} bonus damage!"
        )

    return messages


def _check_weapon_accuracy(player, enemy):
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
    count = int(data.get("count", 1))
    result = spend_attribute_point(player, attr, count)
    if result["ok"]:
        save_player(player)
        _autosave()
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

    if possible_bosses and random.random() < 0.08:
        boss_key = random.choice(possible_bosses)
        boss_data = GAME_DATA.get("bosses", {}).get(boss_key, {})
        if boss_data:
            lvl = _effective_mob_level(player["level"])
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
        lvl = _effective_mob_level(player["level"])
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

    area_npcs = area.get("npcs", [])
    npc_talked = False
    if area_npcs and random.random() < 0.20:
        npc = random.choice(area_npcs)
        npc_name = npc.get("name", "Stranger")
        dialogue = random.choice(npc.get("dialogues", ["..."]))
        add_message(f"You encounter {npc_name}.", "var(--gold)")
        add_message(f'"{dialogue}"', "var(--text-light)")

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

    if not npc_talked:
        explore_event_roll = random.random()
        if explore_event_roll < 0.08:
            dmg = dice.between(5, max(6, player.get("level", 1) * 3))
            player["hp"] = max(1, player["hp"] - dmg)
            add_message(
                f"You trigger a hidden trap! You take {dmg} damage.", "var(--red)"
            )
        elif explore_event_roll < 0.14:
            mp_restore = dice.between(10, 30)
            player["mp"] = min(player["max_mp"], player["mp"] + mp_restore)
            add_message(
                f"You find an ancient shrine and meditate. +{mp_restore} MP restored.",
                "var(--mana-bright,#7eb8f7)",
            )
        elif explore_event_roll < 0.19:
            exp_bonus = dice.between(15, 40)
            player["exp"] = player.get("exp", 0) + exp_bonus
            add_message(
                f"You discover a worn tome. Studying it grants you +{exp_bonus} EXP.",
                "var(--gold)",
            )
        elif explore_event_roll < 0.23:
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

    if random.random() < 0.30:
        gold_found = dice.between(5, 20)
        player["gold"] += gold_found
        add_message(
            f"You spot {gold_found} gold coins glinting on the ground.", "var(--gold)"
        )

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
    _autosave()
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

    revived = _revive_companions(player)

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

    if revived:
        names = ", ".join(revived)
        add_message(
            f"Your fallen companions have recovered: {names}!",
            "var(--gold)",
        )

    area_name = area.get("name", area_key.replace("_", " ").title())
    _set_activity(player, f"resting in {area_name}")
    save_player(player)
    _autosave()
    return redirect(url_for("game"))


@app.route("/action/mine", methods=["POST"])
def action_mine():
    import random as _rand

    player = get_player()
    if not player:
        return redirect(url_for("index"))

    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    mine_pool = area.get("mine_pool", [])

    if not mine_pool:
        add_message("There are no mines in this area.", "var(--red)")
        return redirect(url_for("game"))

    inventory = player.get("inventory", [])
    best_tier = max((_PICKAXE_TIERS.get(i, 0) for i in inventory), default=0)
    best_pickaxe = next(
        (i for i in reversed(inventory) if _PICKAXE_TIERS.get(i, 0) == best_tier),
        None,
    )

    if best_tier == 0:
        add_message(
            "You need a pickaxe to mine. Buy a Wooden Pickaxe from a shop (20g).",
            "var(--red)",
        )
        return redirect(url_for("game"))

    mining_lvl = _get_mining_level(player)
    accessible: list[str] = []
    for ore_name, req in _ORE_REQUIREMENTS.items():
        if best_tier >= req["pickaxe_tier"] and mining_lvl >= req["mining_level"]:
            accessible.append(ore_name)

    if not accessible:
        add_message(
            "You need a better pickaxe or higher Mining Level to find ore here.",
            "var(--text-dim)",
        )
        return redirect(url_for("game"))

    str_val = int(player.get("attributes", {}).get("str", 0))
    success_chance = min(0.95, 0.65 + str_val * 0.005)

    advance_game_time(player)

    if _rand.random() > success_chance:
        add_message(
            "You swing your pickaxe but find nothing this time.",
            "var(--text-dim)",
        )
        save_player(player)
        _autosave()
        return redirect(url_for("game"))

    _rw = {"junk": 80, "common": 60, "uncommon": 30, "rare": 8, "legendary": 2}
    pool_names: list[str] = []
    pool_weights: list[int] = []
    for ore_name in accessible:
        od = GAME_DATA["items"].get(ore_name, {})
        if isinstance(od, dict):
            pool_names.append(ore_name)
            pool_weights.append(_rw.get(od.get("rarity", "common"), 30))

    ore_name = _rand.choices(pool_names, weights=pool_weights, k=1)[0]
    amount = _rand.choices([1, 2, 3], weights=[60, 30, 10], k=1)[0]
    for _ in range(amount):
        player["inventory"].append(ore_name)

    ore_data = GAME_DATA["items"].get(ore_name, {})
    rarity = (
        ore_data.get("rarity", "common") if isinstance(ore_data, dict) else "common"
    )

    xp_gain = _MINING_XP_PER_RARITY.get(rarity, 10) * amount
    old_level = _get_mining_level(player)
    player["mining_xp"] = player.get("mining_xp", 0) + xp_gain
    new_level = _get_mining_level(player)

    _rc = {
        "junk": "var(--text-dim)",
        "common": "var(--text-light)",
        "uncommon": "var(--green-bright)",
        "rare": "var(--mana-bright)",
        "legendary": "var(--gold)",
    }
    color = _rc.get(rarity, "var(--text-light)")
    qty_str = f" &times;{amount}" if amount > 1 else ""
    add_message(f"You mined {ore_name}{qty_str}! (+{xp_gain} Mining XP)", color)

    if new_level > old_level:
        add_message(
            f"Mining Level Up! You are now Mining Level {new_level}!",
            "var(--gold)",
        )

    area_name = area.get("name", area_key.replace("_", " ").title())
    _set_activity(player, f"mining in {area_name}")
    save_player(player)
    _autosave()
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
            cs_id = dest_area.get("first_time_enter_cutscene")
            if cs_id:
                trigger_cutscene(cs_id)
        add_message(f"You travel to {dest_name}.", "var(--wood-light)")
        _set_activity(player, f"wandering {dest_name}")

        my_username = session.get("online_username")
        online_set = set(_chat_online.values()) - {my_username}
        import time as _tv

        cutoff = _tv.time() - 900
        here = [
            (u, e["text"])
            for u, e in _area_presence.items()
            if u in online_set and e["area"] == dest_key and e["t"] >= cutoff
        ]
        random.shuffle(here)
        for uname, status in here[:3]:
            add_message(
                f"You notice {uname} here — {_narrativize(status)}.",
                "var(--mana-bright)",
            )

        session.modified = True
    else:
        add_message("That path is not accessible from here.", "var(--red)")

    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?autosaved=1")


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

    boss_cooldowns[boss_key] = now_ts + BOSS_CHALLENGE_COOLDOWN
    player["boss_cooldowns"] = boss_cooldowns

    lvl = _effective_mob_level(player["level"])
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

    area_name = (
        GAME_DATA["areas"]
        .get(session.get("current_area", ""), {})
        .get("name", "a shop")
    )
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
        player["attr_spell_power"] = (
            player.get("attr_spell_power", 0) + comp_data["spell_power_bonus"]
        )
    if comp_data.get("crit_chance", 0):
        player["attr_crit_chance"] = (
            player.get("attr_crit_chance", 0) + comp_data["crit_chance"]
        )
    if comp_data.get("crit_damage_bonus", 0):
        player["attr_crit_damage"] = (
            player.get("attr_crit_damage", 0) + comp_data["crit_damage_bonus"]
        )
    if comp_data.get("healing_bonus", 0):
        player["attr_healing_bonus"] = (
            player.get("attr_healing_bonus", 0) + comp_data["healing_bonus"]
        )
    if comp_data.get("post_battle_heal", 0):
        player["attr_post_battle_heal"] = (
            player.get("attr_post_battle_heal", 0) + comp_data["post_battle_heal"]
        )

    rank = comp_data.get("rank", "common")
    comp_max_hp = _COMPANION_RANK_HP.get(rank, 400)
    companions.append(
        {
            "id": comp_id,
            "name": comp_data.get("name", comp_id),
            "hp": comp_max_hp,
            "max_hp": comp_max_hp,
        }
    )
    add_message(f"{comp_data.get('name')} joins your party!", "var(--gold)")
    save_player(player)
    _autosave()
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
        player["attr_spell_power"] = max(
            0, player.get("attr_spell_power", 0) - comp_data["spell_power_bonus"]
        )
    if comp_data.get("crit_chance", 0):
        player["attr_crit_chance"] = max(
            0, player.get("attr_crit_chance", 0) - comp_data["crit_chance"]
        )
    if comp_data.get("crit_damage_bonus", 0):
        player["attr_crit_damage"] = max(
            0, player.get("attr_crit_damage", 0) - comp_data["crit_damage_bonus"]
        )
    if comp_data.get("healing_bonus", 0):
        player["attr_healing_bonus"] = max(
            0, player.get("attr_healing_bonus", 0) - comp_data["healing_bonus"]
        )
    if comp_data.get("post_battle_heal", 0):
        player["attr_post_battle_heal"] = max(
            0, player.get("attr_post_battle_heal", 0) - comp_data["post_battle_heal"]
        )

    companions.remove(to_remove)
    player["companions"] = companions

    name = comp_data.get("name", comp_id)
    add_message(f"{name} has left your party.", "var(--text-dim)")
    save_player(player)
    _autosave()
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
        player.setdefault("regen_effects", []).append(
            {
                "hp_per_turn": regen_hp,
                "mp_per_turn": regen_mp,
                "turns_remaining": regen_turns,
                "source": item_name,
            }
        )
        player["inventory"].remove(item_name)
        add_message(
            f"You devour the {item_name} — a divine banquet fit for the gods! Fully restored "
            f"(+{heal_amount} HP, +{mp_amount} MP) and a vigorous feast-glow begins regenerating "
            f"+{regen_hp} HP and +{regen_mp} MP per turn for {regen_turns} turns.",
            "var(--gold)",
        )
    elif item_type == "consumable":
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
            add_message(
                f"You use the {item_name} and recover {heal} HP.", "var(--green-bright)"
            )
        elif effect == "mp_restore":
            restore = dice.between(min_v, max_v) if min_v != max_v else value
            player["mp"] = min(player["max_mp"], player["mp"] + restore)
            add_message(
                f"You use the {item_name} and restore {restore} MP.",
                "var(--mana-bright)",
            )
        elif effect == "full_restore":
            healed = player["max_hp"] - player["hp"]
            mped = player["max_mp"] - player["mp"]
            player["hp"] = player["max_hp"]
            player["mp"] = player["max_mp"]
            add_message(
                f"You use the {item_name}. Fully restored! (+{healed} HP, +{mped} MP)",
                "var(--gold)",
            )
        elif on_use_buff:
            effects_data = GAME_DATA.get("effects", {})
            buff_def = effects_data.get(on_use_buff, {})
            dur = duration or buff_def.get("duration", 5)
            mods = {
                k: v
                for k, v in buff_def.items()
                if k not in ("description", "type", "duration", "tags")
            }
            player.setdefault("active_buffs", []).append(
                {
                    "name": on_use_buff.replace("_", " ").title(),
                    "duration": dur,
                    "modifiers": mods,
                }
            )
            add_message(
                f"You use the {item_name}. {buff_def.get('description', 'A buff is applied!')} ({dur} turns)",
                "var(--green-bright)",
            )
        else:
            consumed = False
            add_message(
                f"You cannot use {item_name} outside of battle.", "var(--text-dim)"
            )

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
        i
        for i in inventory
        if any(x in i.lower() for x in heal_keywords) and "mana" not in i.lower()
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
    add_message(
        f"Quick Heal: used {best} and recovered {heal} HP.", "var(--green-bright)"
    )
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
            "weapon": 0,
            "armor": 1,
            "offhand": 2,
            "accessory": 3,
            "consumable": 4,
            "material": 6,
        }
        t = data.get("type", "misc")
        return (type_order.get(t, 10), name.lower())

    player["inventory"] = sorted(player.get("inventory", []), key=sort_key)
    add_message("Inventory sorted by type.", "var(--text-dim)")
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=character")


@app.route("/action/equip", methods=["POST"])
def action_equip():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    item_name = request.form.get("item", "")
    ok, msg = equip_item(player, item_name)
    add_message(msg, "var(--green-bright)" if ok else "var(--red)")
    save_player(player)
    _autosave()
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
    _autosave()
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
    _autosave()
    return redirect(url_for("game") + "?tab=inventory")


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
    _record_activity("quests")

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

    update_weekly_challenge(player, "mission_count", 1)

    quest_progress: dict[str, Any] = session.get("quest_progress") or {}
    quest_progress.pop(mission_id, None)
    session["quest_progress"] = quest_progress

    _set_activity(player, f"completing quest: {mission.get('name', mission_id)}")
    save_player(player)
    _autosave()
    return redirect(url_for("game"))


@app.route("/action/claim_challenge", methods=["POST"])
def action_claim_challenge():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    ch_id = request.form.get("challenge_id", "")
    ch_def = next(
        (c for c in GAME_DATA["weekly_challenges"] if c.get("id") == ch_id), None
    )
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
    _record_activity("challenges")
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
            f"Not enough gold. {h_data.get('name', h_key)} costs {price} gold.",
            "var(--red)",
        )
        save_player(player)
        return redirect(url_for("game"))

    player["gold"] -= price
    owned = player.get("housing_owned", [])
    owned.append(h_key)
    player["housing_owned"] = owned
    add_message(
        f"You purchase {h_data.get('name', h_key)} for {price} gold.", "var(--gold)"
    )
    _set_activity(player, f"building {h_data.get('name', h_key)} on their land")
    save_player(player)
    _autosave()
    return_to = request.form.get("return_to", "")
    return redirect(
        url_for("land_shop_page")
        if return_to == "land_shop"
        else url_for("game") + "?tab=land"
    )


@app.route("/action/land/place_housing", methods=["POST"])
def land_place_housing():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    h_key = request.form.get("housing_key", "")
    tile_x_str = request.form.get("tile_x", "")
    tile_y_str = request.form.get("tile_y", "")
    return_to = request.form.get("return_to", "")
    redirect_url = (
        url_for("land_map_page")
        if return_to == "land_map"
        else url_for("game") + "?tab=land"
    )

    if h_key not in player.get("housing_owned", []):
        add_message("You do not own that structure.", "var(--red)")
        save_player(player)
        return redirect(redirect_url)

    h_data = GAME_DATA["housing"].get(h_key, {})
    if not h_data:
        add_message("That structure does not exist.", "var(--red)")
        return redirect(redirect_url)

    h_type = h_data.get("type", "decoration")
    comfort = h_data.get("comfort_points", 0)
    slots = player.get("building_slots", {})
    positions = player.get("building_positions", {})

    type_info = BUILDING_TYPES.get(h_type, {"slots": 1, "label": h_type})
    max_slots = type_info["slots"]
    slot_id = None
    for i in range(1, int(max_slots) + 1):
        candidate = f"{h_type}_{i}"
        if not slots.get(candidate):
            slot_id = candidate
            break

    if slot_id is None:
        add_message(
            f"No more {type_info.get('label', h_type)} slots available. Remove one first.",
            "var(--red)",
        )
        save_player(player)
        return redirect(redirect_url)

    _TILE_COLS = 60
    _TILE_ROWS = 50
    _BLOCKED_ROWS = 5

    if tile_x_str != "" and tile_y_str != "":
        try:
            tile_x = int(tile_x_str)
            tile_y = int(tile_y_str)
        except ValueError:
            add_message("Invalid placement position.", "var(--red)")
            save_player(player)
            return redirect(redirect_url)
        if (
            tile_x < 0
            or tile_x >= _TILE_COLS
            or tile_y < _BLOCKED_ROWS
            or tile_y >= _TILE_ROWS
        ):
            add_message(
                "Cannot place there — out of bounds or in blocked zone.", "var(--red)"
            )
            save_player(player)
            return redirect(redirect_url)

        tw, th = BUILDING_TILE_SIZES.get(h_key, (3, 3))
        for exist_slot, exist_pos in positions.items():
            if exist_slot == slot_id:
                continue
            exist_key = slots.get(exist_slot)
            if not exist_key:
                continue
            ex, ey = exist_pos.get("x", -1), exist_pos.get("y", -1)
            if ex < 0 or ey < 0:
                continue
            etw, eth = BUILDING_TILE_SIZES.get(exist_key, (3, 3))
            if (
                tile_x < ex + etw
                and tile_x + tw > ex
                and tile_y < ey + eth
                and tile_y + th > ey
            ):
                add_message(
                    "Cannot place here — overlaps with an existing building.",
                    "var(--red)",
                )
                save_player(player)
                return redirect(redirect_url)

        positions[slot_id] = {"x": tile_x, "y": tile_y}
        player["building_positions"] = positions

    slots[slot_id] = h_key
    player["building_slots"] = slots
    player["comfort_points"] = player.get("comfort_points", 0) + comfort
    add_message(
        f"You place {h_data.get('name', h_key)}. +{comfort} comfort",
        "var(--green-bright)",
    )
    save_player(player)
    _autosave()
    return redirect(redirect_url)


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
        positions = player.get("building_positions", {})
        positions.pop(slot_id, None)
        player["building_positions"] = positions
        add_message(
            f"Removed {h_data.get('name', h_key)} from your land.", "var(--text-dim)"
        )
    else:
        add_message("That slot is already empty.", "var(--text-dim)")

    save_player(player)
    _autosave()
    return_to = request.form.get("return_to", "")
    return redirect(
        url_for("land_map_page")
        if return_to == "land_map"
        else url_for("game") + "?tab=land"
    )


@app.route("/action/land/plant", methods=["POST"])
def land_plant():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

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
    _autosave()
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

    building_slots = player.get("building_slots", {})
    has_farming = any(k.startswith("farming") and v for k, v in building_slots.items())
    farming_bonus_msg = ""
    if has_farming:
        bonus = int(gold_earned * 0.5)
        gold_earned += bonus
        farming_bonus_msg = f" (+{bonus}g farming bonus)"

    player["gold"] += gold_earned
    crops[slot_id] = {}
    player["crops"] = crops
    add_message(
        f"You harvest {amount}x {crop_def.get('name', crop_info['crop_key'])} and earn {gold_earned} gold!{farming_bonus_msg}",
        "var(--gold)",
    )
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/rest", methods=["POST"])
def land_rest():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    building_slots = player.get("building_slots", {})
    has_house = any(k.startswith("house") and v for k, v in building_slots.items())
    if not has_house:
        add_message("You need a house on your land to rest here.", "var(--red)")
        return redirect(url_for("game") + "?tab=land")

    hp = player.get("hp", 1)
    max_hp = player.get("max_hp", 100)
    mp = player.get("mp", 0)
    max_mp = player.get("max_mp", 50)

    if hp >= max_hp and mp >= max_mp:
        add_message("You are already at full health and mana.", "var(--text-dim)")
        save_player(player)
        return redirect(url_for("game") + "?tab=land")

    comfort = player.get("comfort_points", 0)
    hp_restore = max(10, comfort * 2)
    mp_restore = max(5, comfort)

    old_hp, old_mp = hp, mp
    player["hp"] = min(max_hp, hp + hp_restore)
    player["mp"] = min(max_mp, mp + mp_restore)
    gained_hp = player["hp"] - old_hp
    gained_mp = player["mp"] - old_mp

    add_message(
        f"You rest at home and recover +{gained_hp} HP, +{gained_mp} MP.",
        "var(--green-bright)",
    )
    save_player(player)
    _autosave()
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/store_item", methods=["POST"])
def land_store_item():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    building_slots = player.get("building_slots", {})
    has_storage = any(k.startswith("storage") and v for k, v in building_slots.items())
    if not has_storage:
        add_message("You need a storage building on your land first.", "var(--red)")
        return redirect(url_for("game") + "?tab=land")

    item_name = request.form.get("item_name", "")
    inventory = player.get("inventory", [])
    if item_name not in inventory:
        add_message(f"{item_name} is not in your inventory.", "var(--red)")
        return redirect(url_for("game") + "?tab=land")

    storage_count = sum(
        1 for k, v in building_slots.items() if k.startswith("storage") and v
    )
    capacity = storage_count * 10
    stored = player.get("stored_items", [])
    if len(stored) >= capacity:
        add_message(
            f"Storage is full ({capacity} items max). Build more storage to expand.",
            "var(--red)",
        )
        return redirect(url_for("game") + "?tab=land")

    inventory.remove(item_name)
    player["inventory"] = inventory
    stored.append(item_name)
    player["stored_items"] = stored
    add_message(f"Stored {item_name} in your storage.", "var(--text-dim)")
    save_player(player)
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/retrieve_item", methods=["POST"])
def land_retrieve_item():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    item_name = request.form.get("item_name", "")
    stored = player.get("stored_items", [])
    if item_name not in stored:
        add_message(f"{item_name} is not in your storage.", "var(--red)")
        return redirect(url_for("game") + "?tab=land")

    stored.remove(item_name)
    player["stored_items"] = stored
    player.setdefault("inventory", []).append(item_name)
    add_message(f"Retrieved {item_name} from storage.", "var(--green-bright)")
    save_player(player)
    return redirect(url_for("game") + "?tab=land")


@app.route("/action/land/craft", methods=["POST"])
def land_craft():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    building_slots = player.get("building_slots", {})
    has_crafting = any(
        k.startswith("crafting") and v for k, v in building_slots.items()
    )
    if not has_crafting:
        add_message(
            "You need a crafting building (like the Dwarven Forge) on your land first.",
            "var(--red)",
        )
        return redirect(url_for("game") + "?tab=land")

    recipe_key = request.form.get("recipe_key", "")
    recipe = GAME_DATA.get("crafting", {}).get("recipes", {}).get(recipe_key)
    if not recipe:
        add_message("Unknown recipe.", "var(--red)")
        return redirect(url_for("game") + "?tab=land")

    inventory = player.get("inventory", [])
    inv_counts: dict[str, int] = {}
    for item in inventory:
        inv_counts[item] = inv_counts.get(item, 0) + 1

    materials = recipe.get("materials", {})
    for mat, qty in materials.items():
        if inv_counts.get(mat, 0) < qty:
            add_message(f"Not enough materials: need {qty}x {mat}.", "var(--red)")
            return redirect(url_for("game") + "?tab=land")

    for mat, qty in materials.items():
        for _ in range(qty):
            inventory.remove(mat)

    output = recipe.get("output", {})
    for out_item, out_qty in output.items():
        for _ in range(out_qty):
            inventory.append(out_item)

    player["inventory"] = inventory
    out_str = ", ".join(f"{q}x {n}" for n, q in output.items())
    add_message(f"You craft {out_str}!", "var(--green-bright)")
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
            f"Not enough gold. {pet_data.get('name', pet_key)} costs {price} gold.",
            "var(--red)",
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

    add_message(
        f"You adopt {pet_data.get('name', pet_key)} as your companion!", "var(--gold)"
    )
    if boosts:
        boost_str = ", ".join(
            f"+{v} {k}" for k, v in boosts.items() if isinstance(v, int)
        )
        if boost_str:
            add_message(f"Pet bonus: {boost_str}", "var(--green-bright)")

    save_player(player)
    _autosave()
    return_to = request.form.get("return_to", "")
    return redirect(
        url_for("land_pets_page")
        if return_to == "land_pets"
        else url_for("game") + "?tab=land"
    )


@app.route("/action/land/train", methods=["POST"])
def land_train():
    player = get_player()
    if not player:
        return redirect(url_for("index"))

    if session.get("current_area") != "your_land":
        add_message("You can only train at Your Land.", "var(--red)")
        return redirect(url_for("game"))

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
    battle_companions = session.get("battle_companions", [])

    enemy_name = enemy.get("name", "Enemy")
    stunned = process_turn_effects(player, player_effects, log, "You")
    session["battle_player_effects"] = player_effects
    process_turn_effects(
        enemy,
        enemy_effects,
        log,
        enemy_name,
        is_enemy=True,
        player_level=player.get("level", 1),
    )
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
        _sync_companion_hp_to_player(player, battle_companions)
        _restore_companion_hp(player)
        return _handle_victory(player, enemy, log)

    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)

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
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
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

    enemy_name = enemy.get("name", "Enemy")
    stunned = process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(
        enemy,
        enemy_effects,
        log,
        enemy_name,
        is_enemy=True,
        player_level=player.get("level", 1),
    )

    if player["hp"] <= 0:
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        return _handle_defeat(player, enemy, log)
    if enemy.get("hp", 1) <= 0:
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"] = enemy_effects
        return _handle_victory(player, enemy, log)

    if not stunned:
        if not _check_weapon_accuracy(player, enemy):
            log.append(f"You swing at the {enemy_name} but miss!")
        else:
            eff_enemy_def = enemy["defense"]
            weaken_eff = enemy_effects.get("weaken", {})
            if weaken_eff.get("turns", 0) > 0:
                eff_enemy_def = max(
                    0, eff_enemy_def - weaken_eff.get("def_reduction", 0)
                )
            armor_crush_eff = enemy_effects.get("armor_crushed", {})
            if armor_crush_eff.get("turns", 0) > 0:
                eff_enemy_def = max(
                    0, eff_enemy_def - armor_crush_eff.get("def_reduction", 0)
                )

            armor_pen_pct = 0
            eq_weapon = GAME_DATA["items"].get(
                player.get("equipment", {}).get("weapon", ""), {}
            )
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
                log.append(
                    f"CRITICAL STRIKE! You deal {p_dmg} damage to the {enemy_name}!"
                )
            else:
                log.append(f"You attack the {enemy_name} for {p_dmg} damage.")
            enemy["hp"] = max(0, enemy["hp"] - p_dmg)

            weapon_effects = _get_weapon_combat_effects(player, enemy)
            total_bonus = 0
            for bonus_dmg, bonus_msg in weapon_effects:
                if bonus_dmg > 0:
                    total_bonus += bonus_dmg
                    log.append(bonus_msg)
            if total_bonus > 0:
                enemy["hp"] = max(0, enemy["hp"] - total_bonus)

            proc_msgs = _get_weapon_on_hit_procs(player, enemy, enemy_effects)
            for msg in proc_msgs:
                log.append(msg)

        if enemy["hp"] <= 0:
            session["battle_player_effects"] = player_effects
            session["battle_enemy_effects"] = enemy_effects
            _sync_companion_hp_to_player(player, battle_companions)
            _restore_companion_hp(player)
            return _handle_victory(player, enemy, log)

    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)

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
    _autosave()
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

    enemy_name = enemy.get("name", "Enemy")
    process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(
        enemy,
        enemy_effects,
        log,
        enemy_name,
        is_enemy=True,
        player_level=player.get("level", 1),
    )

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
    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)
    player["defense"] = real_defense

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
    _autosave()
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
            log.append(
                f"You use the {item_name}. Fully restored! (+{healed} HP, +{mped} MP)"
            )
        elif on_use_buff:
            effects_data = GAME_DATA.get("effects", {})
            buff_def = effects_data.get(on_use_buff, {})
            dur = duration or buff_def.get("duration", 5)
            mods = {
                k: v
                for k, v in buff_def.items()
                if k not in ("description", "type", "duration", "tags")
            }
            player.setdefault("active_buffs", []).append(
                {
                    "name": on_use_buff.replace("_", " ").title(),
                    "duration": dur,
                    "modifiers": mods,
                }
            )
            log.append(
                f"You use the {item_name}. {buff_def.get('description', 'A buff is applied!')} ({dur} turns)"
            )
        elif item_data.get("type") == "consumable":
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

        _enemy_take_turn(enemy, player, player_effects, log, battle_companions)

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
    _autosave()
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
        _autosave()
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
    _autosave()
    return redirect(url_for("game"))


def _handle_victory(player, enemy, log):
    log.append(f"The {enemy['name']} falls! Victory!")
    exp = enemy.get("exp_reward", enemy.get("experience_reward", 30))
    gold = enemy.get("gold_reward", 10)

    _area_name_bw = (
        GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "")
    )
    current_weather = get_real_weather(_area_name_bw)
    exp_bonus_pct, gold_bonus_pct = get_weather_bonuses(current_weather)
    if exp_bonus_pct > 0:
        bonus_exp = int(exp * exp_bonus_pct)
        exp += bonus_exp
        log.append(
            f"Weather bonus: +{bonus_exp} EXP ({current_weather.replace('_', ' ').title()})!"
        )
    if gold_bonus_pct > 0:
        bonus_gold = int(gold * gold_bonus_pct)
        gold += bonus_gold
        log.append(
            f"Weather bonus: +{bonus_gold} gold ({current_weather.replace('_', ' ').title()})!"
        )

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

    post_heal = player.get("attr_post_battle_heal", 0)
    if post_heal and post_heal > 0:
        actual = min(post_heal, player["max_hp"] - player["hp"])
        if actual > 0:
            player["hp"] += actual
            log.append(f"Your companion's aura restores {actual} HP after battle.")

    enemy_key = enemy.get("key", enemy.get("name", "").lower().replace(" ", "_"))
    enemy_name = enemy.get("name", "")
    update_quest_kills(enemy_key, enemy_name)

    update_weekly_challenge(player, "kill_count", 1)
    _record_activity("boss_kills" if enemy.get("is_boss") else "battles")
    if enemy.get("is_boss"):
        update_weekly_challenge(player, "boss_kill", 1)
        player["total_bosses_defeated"] = player.get("total_bosses_defeated", 0) + 1
        boss_key = enemy.get("key", "")
        defeat_dialogue = get_boss_dialogue(boss_key, "defeat")
        if defeat_dialogue:
            log.append(f'"{defeat_dialogue}"')

    session.pop("battle_player_effects", None)
    session.pop("battle_enemy_effects", None)
    session.pop("battle_companions", None)
    session["battle_log"] = log
    session["battle_enemy"] = None
    save_player(player)
    _autosave()

    if session.get("online_username"):
        _pname = player.get("name", session.get("online_username", "Someone"))
        _aname = (
            GAME_DATA["areas"]
            .get(session.get("current_area", ""), {})
            .get("name", "the wilds")
        )
        if enemy.get("is_boss"):
            push_world_event(f"{_pname} defeated {enemy['name']} in {_aname}!")
        else:
            push_world_event(f"{_pname} slew a {enemy['name']} in {_aname}.")

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
        active_dungeon["room_index"] = 0
        active_dungeon["current_challenge"] = None
        active_dungeon["challenge_answered"] = False
        session["active_dungeon"] = active_dungeon
        save_player(player)
        return redirect(url_for("dungeon_room"))

    player["hp"] = max(1, int(player["max_hp"] * 0.25))
    log.append(f"You awaken later, battered. HP: {player['hp']}")
    _record_activity("deaths")
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
    session["visited_areas"] = list(set(_va_top + _va_player)) or [
        session["current_area"]
    ]
    session["quest_progress"] = data.get("quest_progress", {})
    session["seen_cutscenes"] = data.get("seen_cutscenes", [])
    session["messages"] = data.get("messages", [])
    session["diary"] = data.get("diary", [])
    session["npc_unlocked_quests"] = data.get("npc_unlocked_quests", [])
    session.modified = True
    return jsonify({"ok": True, "player_name": player.get("name")})


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
        add_message(
            f"You must travel to {area_name} to enter this dungeon.", "var(--red)"
        )
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
        result = process_battle_room(
            player, room, enemies_data, areas_data, area_key, dungeon=dungeon
        )
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
        result = process_ambush_room(
            player, room, enemies_data, areas_data, area_key, dungeon=dungeon
        )
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
        _group_contribute(
            result.get("exp", 0),
            result.get("gold", 0),
            f"cleared dungeon: {dungeon.get('name', 'a dungeon')}",
        )
        _record_activity("dungeons")
        dungeon_id = dungeon.get("id", "")
        if dungeon_id:
            completed_dungeons = player.setdefault("completed_dungeons", [])
            if dungeon_id not in completed_dungeons:
                completed_dungeons.append(dungeon_id)
        session.pop("active_dungeon", None)
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


@app.route("/api/online/register", methods=["POST"])
@limiter.limit("5 per hour")
def api_online_register():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip() or None
    result = register_user(username, password, email=email)
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
        user_id = result["user_id"]
        actual_username = result.get("username") or username.lower()
        if _is_banned(actual_username):
            return jsonify(
                {"ok": False, "message": "Your account has been banned."}
            ), 403
        other_active = [uid for uid in _active_sessions if uid != user_id]
        if len(other_active) >= 100:
            return jsonify(
                {
                    "ok": False,
                    "server_full": True,
                    "message": "The server is full (100 players max). Please try again later.",
                }
            ), 503
        session_token = str(uuid.uuid4())
        _active_sessions[user_id] = session_token
        _session_last_activity[user_id] = _time_module.time()
        _username_to_userid[actual_username.lower()] = user_id
        session["online_username"] = actual_username
        session["online_user_id"] = user_id
        session["session_token"] = session_token
        session.modified = True
        return jsonify(
            {"ok": True, "message": result["message"], "username": actual_username}
        )
    return jsonify({"ok": False, "message": result["message"]}), 401


@app.route("/api/online/logout", methods=["POST"])
def api_online_logout():
    user_id = session.get("online_user_id")
    if user_id and _active_sessions.get(user_id) == session.get("session_token"):
        _active_sessions.pop(user_id, None)
        _session_last_activity.pop(user_id, None)
    _autosave()
    game_keys = [
        "player",
        "current_area",
        "completed_missions",
        "visited_areas",
        "quest_progress",
        "seen_cutscenes",
        "messages",
        "diary",
        "npc_unlocked_quests",
        "battle_enemy",
        "battle_player_effects",
        "battle_enemy_effects",
        "active_dungeon",
        "pending_cutscene",
        "weekly_challenges_progress",
    ]
    for key in game_keys:
        session.pop(key, None)
    session.pop("online_username", None)
    session.pop("online_user_id", None)
    session.pop("session_token", None)
    session.modified = True
    return jsonify({"ok": True, "message": "Logged out."})


@app.route("/api/session/check", methods=["GET"])
def api_session_check():
    if not _is_session_valid():
        return jsonify({"valid": False}), 200
    return jsonify({"valid": True}), 200


@app.route("/api/online/autosave", methods=["POST"])
def api_online_autosave():
    if not _is_session_valid():
        return jsonify({"ok": False}), 401
    _autosave()
    return jsonify({"ok": True})


@app.route("/api/saves/list", methods=["GET"])
def api_saves_list():
    slots = session.get("_save_slots") or [None] * 5
    if not isinstance(slots, list):
        slots = [None] * 5
    slots: list[Any] = (list(slots) + [None] * 5)[:5]
    result = []
    for i, s in enumerate(slots):
        if s is None or not isinstance(s, dict):
            result.append({"slot": i + 1, "empty": True})
        else:
            result.append(
                {
                    "slot": i + 1,
                    "empty": False,
                    "label": s.get("label", ""),
                    "saved_at": s.get("saved_at", ""),
                    "level": s.get("level", 1),
                    "area": s.get("area", ""),
                    "character_class": s.get("character_class", ""),
                    "player_name": s.get("player_name", ""),
                }
            )
    return jsonify({"ok": True, "slots": result})


@app.route("/api/saves/write", methods=["POST"])
def api_saves_write():
    if not _is_session_valid():
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        slot = int(data.get("slot", 0))
    except (TypeError, ValueError):
        slot = 0
    if slot < 2 or slot > 5:
        return jsonify(
            {"ok": False, "message": "Slot must be 2–5 (slot 1 is auto-save)."}
        ), 400
    label = str(data.get("label", f"Save {slot}")).strip()[:32] or f"Save {slot}"
    state = _build_game_state()
    if not state:
        return jsonify({"ok": False, "message": "No active character."}), 400
    _update_save_slot(slot, label, state)
    state["_save_slots"] = session.get("_save_slots", [None] * 5)
    try:
        user_id = session.get("online_user_id")
        if user_id:
            character_autosave(user_id, state)
    except Exception:
        pass
    return jsonify({"ok": True, "message": f"Saved to slot {slot}!"})


@app.route("/api/saves/restore", methods=["POST"])
def api_saves_restore():
    if not _is_session_valid():
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        slot = int(data.get("slot", 0))
    except (TypeError, ValueError):
        slot = 0
    if slot < 1 or slot > 5:
        return jsonify({"ok": False, "message": "Invalid slot number."}), 400
    slots = session.get("_save_slots") or []
    if not isinstance(slots, list) or len(slots) < slot:
        return jsonify({"ok": False, "message": "That slot is empty."}), 404
    slot_data = slots[slot - 1]
    if (
        not slot_data
        or not isinstance(slot_data, dict)
        or not slot_data.get("snapshot")
    ):
        return jsonify({"ok": False, "message": "That slot is empty."}), 404
    snapshot = slot_data["snapshot"]
    current_slots = slots
    _apply_game_state(snapshot)
    session["_save_slots"] = current_slots
    session.modified = True
    return jsonify(
        {"ok": True, "message": f"Restored from slot {slot}!", "reload": True}
    )


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
    session["visited_areas"] = list(set(_va_top + _va_player)) or [
        session["current_area"]
    ]
    session["quest_progress"] = data.get("quest_progress", {})
    session["seen_cutscenes"] = data.get("seen_cutscenes", [])
    session["messages"] = data.get("messages", [])
    session["diary"] = data.get("diary", [])
    session["npc_unlocked_quests"] = data.get("npc_unlocked_quests", [])
    session.modified = True
    return jsonify(
        {"ok": True, "message": result["message"], "player_name": player.get("name")}
    )


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
        return jsonify(
            {"ok": False, "message": f"Too many requests. Try again in a moment."}
        )
    timestamps.append(now)
    _fr_cooldowns[username] = timestamps
    if is_blocked(username, target):
        return jsonify({"ok": False, "message": "Unable to send request to that user."})
    result = send_friend_request(username, target)
    if result.get("ok"):
        target_sids = [sid for sid, u in _chat_online.items() if u == target]
        for sid in target_sids:
            if result.get("accepted"):
                _emit_sync("friend_accepted", {"from": username}, to=sid)
            else:
                _emit_sync("friend_request", {"from": username}, to=sid)
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
            _emit_sync("friend_accepted", {"from": username}, to=sid)
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
        return jsonify(
            {"ok": False, "message": f"Message too long (max {DM_MAX_LEN} chars)."}
        )
    now = _time_module.time()
    last_dm = _dm_cooldowns.get(username, 0)
    if now - last_dm < DM_COOLDOWN_SECS:
        wait = int(DM_COOLDOWN_SECS - (now - last_dm)) + 1
        return jsonify(
            {
                "ok": False,
                "message": f"Please wait {wait}s before sending another message.",
            }
        )
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
            _emit_sync("dm_message", payload, to=sid)
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
        if (
            username
            and username in (trade["player_a"], trade["player_b"])
            and trade["status"] == "active"
        ):
            key = "offer_a" if username == trade["player_a"] else "offer_b"
            offered_items = list(trade[key]["items"])
            offered_gold = trade[key]["gold"]
            active_trade_id = tid
            break
    return jsonify(
        {
            "ok": True,
            "inventory": player.get("inventory", []),
            "gold": player.get("gold", 0),
            "offered_items": offered_items,
            "offered_gold": offered_gold,
            "active_trade_id": active_trade_id,
        }
    )


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
            return jsonify(
                {"ok": False, "message": f"Item '{item}' not found in inventory."}
            ), 400
        inventory.remove(item)
    current_gold -= give_gold
    for item in receive_items:
        inventory.append(item)
    current_gold += receive_gold
    player["inventory"] = inventory
    player["gold"] = current_gold
    session["player"] = player
    session.modified = True
    _autosave()
    trade[applied_key] = True
    if trade.get("applied_a") and trade.get("applied_b"):
        _active_trades.pop(trade_id, None)
    return jsonify(
        {
            "ok": True,
            "message": f"Trade complete! Received {len(receive_items)} item(s) and {receive_gold:,} gold.",
            "received_items": receive_items,
            "received_gold": receive_gold,
        }
    )


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
        return jsonify(
            {
                "ok": False,
                "message": f"You need {cost:,} gold to change your character.",
            }
        )
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
            add_message(
                f"All gear unequipped on class change: {', '.join(unequipped)}.",
                "var(--text-dim)",
            )
    if not changes:
        return jsonify({"ok": False, "message": "No valid changes provided."})
    player["gold"] -= cost
    save_player(player)
    _autosave()
    add_message(
        f"Character updated ({', '.join(changes)}). -{cost:,} gold.", "var(--gold)"
    )
    return jsonify({"ok": True, "message": f"Character updated: {', '.join(changes)}."})


GROUP_CHAT_COOLDOWN = 5
_group_chat_cooldowns: dict = {}


@sio.on("group_chat_send")
async def on_group_chat_send(sid, data):
    username = _chat_online.get(sid)
    if not username:
        await sio.emit("group_chat_error", {"message": "Not logged in."}, to=sid)
        return
    message = (data.get("message") or "").strip()
    if not message:
        return
    if len(message) > 200:
        await sio.emit(
            "group_chat_error",
            {"message": "Message too long (max 200 chars)."},
            to=sid,
        )
        return
    now = _time_module.time()
    if now - _group_chat_cooldowns.get(username, 0) < GROUP_CHAT_COOLDOWN:
        await sio.emit(
            "group_chat_error",
            {"message": f"Wait {GROUP_CHAT_COOLDOWN}s between messages."},
            to=sid,
        )
        return
    _group_chat_cooldowns[username] = now
    message = censor_text(message)
    group_result = await _asyncio.get_event_loop().run_in_executor(
        None, get_user_group, username
    )
    if not group_result.get("ok") or not group_result.get("group"):
        await sio.emit(
            "group_chat_error", {"message": "You are not in a group."}, to=sid
        )
        return
    group = group_result["group"]
    members = [m["username"] for m in group.get("members", [])]
    payload = {"username": username, "message": message, "ts": int(now)}
    for member in members:
        for s in [s for s, u in _chat_online.items() if u == member]:
            await sio.emit("group_chat_message", payload, to=s)


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
    return render_template(
        "groups.html", online_username=online_username, group=group_data
    )


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
            add_message(
                f"Collected {gold} gold from the group treasury!", "var(--gold)"
            )
    return jsonify(result), 200 if result["ok"] else 400


@app.route("/api/area_activity")
def api_area_activity():
    import time as _ta

    username = session.get("online_username")
    area = session.get("current_area", "")
    if not username or not area:
        return jsonify({"ok": False, "players": []})

    now = _ta.time()
    cutoff = now - 900
    online_set = set(_chat_online.values())

    results = []
    for uname, entry in list(_area_presence.items()):
        if uname == username:
            continue
        if uname not in online_set:
            continue
        if entry["area"] != area:
            continue
        if entry["t"] < cutoff:
            continue
        ago = int(now - entry["t"])
        results.append(
            {
                "username": uname,
                "narrative": _narrativize(entry["text"]),
                "when": _narrative_when(ago),
            }
        )

    results.sort(key=lambda x: x["when"])
    return jsonify({"ok": True, "area": area, "players": results})


@app.route("/leaderboard")
def leaderboard_page():
    online_username = session.get("online_username")
    return render_template("leaderboard.html", online_username=online_username)


@app.route("/api/leaderboard")
def api_leaderboard():
    groups = get_group_leaderboard()
    players = get_player_leaderboard()
    return jsonify({"ok": True, "groups": groups, "players": players})


@app.route("/api/online/set_email", methods=["POST"])
@limiter.limit("5 per hour")
def api_online_set_email():
    user_id = session.get("online_user_id")
    if not user_id:
        return jsonify({"ok": False, "message": "Not logged in."}), 401
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip()
    result = request_email_verification(user_id, email)
    if not result["ok"]:
        return jsonify(result), 400

    if result["token"] and result["email"]:
        base_url = request.host_url.rstrip("/")
        verify_url = f"{base_url}/verify-email?token={result['token']}"
        html_body = f"""
<html><body style="background:#0a0618;color:#e8deff;font-family:sans-serif;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:rgba(18,12,38,0.98);border:1px solid rgba(180,130,255,0.4);border-radius:14px;padding:32px;">
    <h2 style="color:#b87fff;margin-top:0;">Our Legacy 2 — Verify Your Email</h2>
    <p>Hello, Adventurer!</p>
    <p>Please confirm this email address is yours by clicking the button below. The link expires in <strong>24 hours</strong>.</p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{verify_url}" style="background:linear-gradient(135deg,#6030c0,#3a1a80);color:#fff;text-decoration:none;padding:13px 28px;border-radius:8px;font-size:15px;font-weight:bold;letter-spacing:0.05em;">Verify My Email</a>
    </div>
    <p style="font-size:12px;color:#888;">If you did not request this, you can safely ignore it.</p>
    <p style="font-size:12px;color:#888;">Link: <a href="{verify_url}" style="color:#b87fff;">{verify_url}</a></p>
  </div>
</body></html>
"""
        text_body = (
            f"Our Legacy 2 — Verify Your Email\n\n"
            f"Click the link below to verify your email (expires in 24 hours):\n{verify_url}\n\n"
            f"If you did not request this, ignore this email."
        )
        _send_email(
            to=result["email"],
            subject="Our Legacy 2 — Verify Your Email",
            body_html=html_body,
            body_text=text_body,
        )

    return jsonify(
        {
            "ok": True,
            "message": f"Verification email sent to {result['email']}. Check your inbox and click the link to confirm.",
        }
    )


@app.route("/verify-email")
def verify_email_page():
    token = request.args.get("token", "").strip()
    if not token:
        return render_template("verify_email.html", token=None, result=None)
    result = verify_email_token(token)
    if result["ok"] and result.get("user_id"):
        verified_user_id = result["user_id"]
        if session.get("online_user_id") == verified_user_id:
            _autosave()
    return render_template("verify_email.html", token=token, result=result)


@app.route("/api/online/forgot-password", methods=["POST"])
@limiter.limit("3 per hour")
def api_forgot_password():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify(
            {"ok": False, "message": "Please enter your email address."}
        ), 400

    result = create_password_reset_token(email)
    if not result["ok"]:
        return jsonify({"ok": False, "message": result["message"]}), 500

    if result["token"] and result["email"]:
        if not _email_configured():
            app.logger.error(
                "Password reset: email service not configured (RESEND_API / RESEND_EMAIL missing)."
            )
            return jsonify(
                {
                    "ok": False,
                    "message": "Email service is not configured. Please contact the administrator.",
                }
            ), 503

        base_url = request.host_url.rstrip("/")
        reset_url = f"{base_url}/reset-password?token={result['token']}"
        html_body = f"""
<html><body style="background:#0a0618;color:#e8deff;font-family:sans-serif;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:rgba(18,12,38,0.98);border:1px solid rgba(180,130,255,0.4);border-radius:14px;padding:32px;">
    <h2 style="color:#b87fff;margin-top:0;">Our Legacy 2 — Password Reset</h2>
    <p>Hello, Adventurer!</p>
    <p>We received a request to reset the password for your account. Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.</p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{reset_url}" style="background:linear-gradient(135deg,#6030c0,#3a1a80);color:#fff;text-decoration:none;padding:13px 28px;border-radius:8px;font-size:15px;font-weight:bold;letter-spacing:0.05em;">Reset My Password</a>
    </div>
    <p style="font-size:12px;color:#888;">If you did not request a password reset, you can safely ignore this email. Your password will not change.</p>
    <p style="font-size:12px;color:#888;">Link: <a href="{reset_url}" style="color:#b87fff;">{reset_url}</a></p>
  </div>
</body></html>
"""
        text_body = (
            f"Our Legacy 2 — Password Reset\n\n"
            f"Click the link below to reset your password (expires in 1 hour):\n{reset_url}\n\n"
            f"If you did not request this, ignore this email."
        )
        email_result = _send_email(
            to=result["email"],
            subject="Our Legacy 2 — Password Reset",
            body_html=html_body,
            body_text=text_body,
        )
        if not email_result.get("ok"):
            app.logger.error(
                "Password reset email failed for %s: %s",
                result["email"],
                email_result.get("message"),
            )
            return jsonify(
                {
                    "ok": False,
                    "message": "Could not send reset email. Please try again later or contact support.",
                }
            ), 503

    return jsonify(
        {
            "ok": True,
            "message": "If that email is registered, you'll receive a reset link shortly.",
        }
    )


@app.route("/reset-password")
def reset_password_page():
    token = request.args.get("token", "").strip()
    return render_template("reset_password.html", token=token)


@app.route("/api/online/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def api_reset_password():
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("token", "").strip()
    new_password = data.get("password", "")
    confirm_password = data.get("confirm", "")
    if not token:
        return jsonify({"ok": False, "message": "Invalid reset link."}), 400
    if not new_password or len(new_password) < 6:
        return jsonify(
            {"ok": False, "message": "Password must be at least 6 characters."}
        ), 400
    if new_password != confirm_password:
        return jsonify({"ok": False, "message": "Passwords do not match."}), 400
    result = reset_password_with_token(token, new_password)
    if result["ok"]:
        return jsonify(result), 200
    return jsonify(result), 400


def _require_admin():
    return (
        session.get("online_username")
        if _is_admin_user(session.get("online_username", ""))
        else None
    )


@app.route("/api/admin/status", methods=["GET"])
def api_admin_status():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    return jsonify(
        {
            "ok": True,
            "is_owner": _is_owner(caller),
            "owner": admin_get_owner(),
            "admins": admin_get_mods(),
            "banned_users": {r["username"]: r for r in admin_list_bans()},
            "muted_users": {r["username"]: r for r in admin_list_mutes()},
        }
    )


@app.route("/api/admin/ban", methods=["POST"])
def api_admin_ban():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    reason = body.get("reason", "").strip() or "No reason given."
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target.lower() == caller.lower():
        return jsonify({"ok": False, "message": "You cannot ban yourself."}), 400
    if _is_owner(target) and not _is_owner(caller):
        return jsonify(
            {"ok": False, "message": "Only the owner can ban the owner."}
        ), 403
    admin_ban(target, reason, caller)
    return jsonify({"ok": True, "message": f"{target} has been banned."})


@app.route("/api/admin/unban", methods=["POST"])
def api_admin_unban():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_unban(target):
        return jsonify({"ok": False, "message": f"{target} is not banned."}), 404
    return jsonify({"ok": True, "message": f"{target} has been unbanned."})


@app.route("/api/admin/mute", methods=["POST"])
def api_admin_mute():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    reason = body.get("reason", "").strip() or "No reason given."
    duration_minutes = body.get("duration_minutes")
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target.lower() == caller.lower():
        return jsonify({"ok": False, "message": "You cannot mute yourself."}), 400
    if _is_owner(target) and not _is_owner(caller):
        return jsonify(
            {"ok": False, "message": "Only the owner can mute the owner."}
        ), 403
    expires_at = None
    if duration_minutes:
        try:
            expires_at = _time_module.time() + int(duration_minutes) * 60
        except (ValueError, TypeError):
            return jsonify({"ok": False, "message": "Invalid duration."}), 400
    admin_mute(target, expires_at, reason, caller)
    msg = f"{target} has been muted"
    msg += (
        f" for {duration_minutes} minute(s)." if duration_minutes else " permanently."
    )
    return jsonify({"ok": True, "message": msg})


@app.route("/api/admin/unmute", methods=["POST"])
def api_admin_unmute():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_unmute(target):
        return jsonify({"ok": False, "message": f"{target} is not muted."}), 404
    return jsonify({"ok": True, "message": f"{target} has been unmuted."})


@app.route("/api/admin/add_admin", methods=["POST"])
def api_admin_add_admin():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify(
            {"ok": False, "message": "Only the owner can promote admins."}
        ), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_add_mod(target):
        return jsonify({"ok": False, "message": f"{target} is already an admin."}), 409
    return jsonify({"ok": True, "message": f"{target} is now an admin."})


@app.route("/api/admin/remove_admin", methods=["POST"])
def api_admin_remove_admin():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify(
            {"ok": False, "message": "Only the owner can demote admins."}
        ), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_remove_mod(target):
        return jsonify({"ok": False, "message": f"{target} is not an admin."}), 404
    return jsonify({"ok": True, "message": f"{target} has been removed from admins."})


@app.route("/admin")
def admin_console():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return redirect(url_for("index"))
    is_owner = _is_owner(caller)
    return render_template("admin.html", online_user=caller, is_owner=is_owner)


@app.route("/items")
def items_debug():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return redirect(url_for("index"))

    raw: dict = GAME_DATA.get("items", {})

    items_list = []
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        entry = {"name": name}
        entry.update(data)
        for field in (
            "texture",
            "type",
            "rarity",
            "weapon_type",
            "armor_type",
            "description",
            "effect",
            "tags",
            "requirements",
            "price",
            "attack_bonus",
            "defense_bonus",
            "magic_bonus",
            "crit_chance",
            "aim_accuracy",
            "parry_chance",
            "weight",
            "sharpness",
            "smiting",
            "value",
            "min_value",
            "max_value",
            "duration",
        ):
            entry.setdefault(field, None)
        entry["tags"] = entry["tags"] or []
        entry["requirements"] = entry["requirements"] or {}
        items_list.append(entry)

    items_list.sort(key=lambda x: (x.get("type") or "", x["name"]))

    total = len(items_list)
    with_texture = sum(1 for i in items_list if i.get("texture"))
    without_texture = total - with_texture

    all_types = sorted({i.get("type") or "unknown" for i in items_list})
    all_rarities = sorted(
        {i.get("rarity") or "common" for i in items_list},
        key=lambda r: ["common", "uncommon", "rare", "epic", "legendary"].index(r)
        if r in ["common", "uncommon", "rare", "epic", "legendary"]
        else 99,
    )

    type_counts = {}
    for i in items_list:
        t = i.get("type") or "unknown"
        type_counts[t] = type_counts.get(t, 0) + 1

    return render_template(
        "items.html",
        items=items_list,
        total=total,
        with_texture=with_texture,
        without_texture=without_texture,
        type_list=all_types,
        rarity_list=all_rarities,
        type_counts=type_counts,
    )


@app.route("/api/admin/data", methods=["GET"])
def api_admin_data():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    return jsonify(
        {
            "ok": True,
            "is_owner": True,
            "owner": admin_get_owner(),
            "mods": admin_get_mods(),
            "bans": admin_list_bans(),
            "mutes": admin_list_mutes(),
            "online_count": len(_active_sessions),
            "online_users": list(_username_to_userid.keys()),
        }
    )


@app.route("/api/admin/kick", methods=["POST"])
def api_admin_kick():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify(
            {"ok": False, "message": "Only the owner can kick players."}
        ), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip().lower()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target == caller.lower():
        return jsonify({"ok": False, "message": "You cannot kick yourself."}), 400
    uid = _username_to_userid.get(target)
    if uid:
        _active_sessions.pop(uid, None)
    _kicked_usernames.add(target)
    return jsonify({"ok": True, "message": f"{target} has been kicked."})


@app.route("/api/admin/warn", methods=["POST"])
def api_admin_warn_user():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    reason = body.get("reason", "").strip() or "No reason given."
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    count = admin_warn(target, reason)
    return jsonify(
        {"ok": True, "message": f"{target} warned. Total warnings: {count}."}
    )


@app.route("/api/admin/clearwarn", methods=["POST"])
def api_admin_clearwarn():
    caller = session.get("online_username", "")
    if not _is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if admin_clear_warns(target):
        return jsonify({"ok": True, "message": f"Warnings cleared for {target}."})
    return jsonify({"ok": False, "message": f"No warnings found for {target}."}), 404


@app.route("/api/admin/setowner", methods=["POST"])
def api_admin_setowner():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify(
            {"ok": False, "message": "Only the owner can transfer ownership."}
        ), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target.lower() == caller.lower():
        return jsonify({"ok": False, "message": "You are already the owner."}), 400
    admin_set_owner(target)
    return jsonify({"ok": True, "message": f"Ownership transferred to {target}."})


@app.route("/api/admin/game/stats", methods=["GET"])
def api_game_stats():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify(
            {
                "ok": False,
                "message": "No active character in session. Load a save first.",
            }
        )
    return jsonify(
        {
            "ok": True,
            "name": player.get("name", "?"),
            "class": player.get("class", "?"),
            "level": player.get("level", 1),
            "rank": player.get("rank", "F"),
            "experience": player.get("experience", 0),
            "experience_to_next": player.get("experience_to_next", 100),
            "hp": player.get("hp", 0),
            "max_hp": player.get("max_hp", 0),
            "mp": player.get("mp", 0),
            "max_mp": player.get("max_mp", 0),
            "attack": player.get("attack", 0),
            "defense": player.get("defense", 0),
            "speed": player.get("speed", 0),
            "gold": player.get("gold", 0),
            "mining_xp": player.get("mining_xp", 0),
            "mining_level": _get_mining_level(player),
            "inventory_count": len(player.get("inventory", [])),
        }
    )


@app.route("/api/admin/game/give", methods=["POST"])
def api_game_give():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify(
            {
                "ok": False,
                "message": "No active character in session. Load a save first.",
            }
        )
    body = request.get_json(force=True, silent=True) or {}
    kind = body.get("kind", "").lower()
    if kind == "gold":
        amount = int(body.get("amount", 0))
        if amount <= 0:
            return jsonify({"ok": False, "message": "Amount must be positive."})
        player["gold"] = player.get("gold", 0) + amount
        session.modified = True
        return jsonify(
            {"ok": True, "message": f"Gave {amount} gold. Total: {player['gold']}g."}
        )
    elif kind == "xp":
        amount = int(body.get("amount", 0))
        if amount <= 0:
            return jsonify({"ok": False, "message": "Amount must be positive."})
        leveled = gain_experience(player, amount)
        session.modified = True
        msg = f"Gave {amount} XP."
        if leveled:
            msg += f" Level up! Now level {player['level']}."
        return jsonify({"ok": True, "message": msg})
    elif kind == "item":
        item_name = body.get("item", "").strip()
        qty = max(1, int(body.get("qty", 1)))
        all_items = GAME_DATA.get("items", {})
        matched = next((k for k in all_items if k.lower() == item_name.lower()), None)
        if not matched:
            close = [k for k in all_items if item_name.lower() in k.lower()]
            if close:
                return jsonify(
                    {
                        "ok": False,
                        "message": f"Item not found. Did you mean: {', '.join(close[:5])}?",
                    }
                )
            return jsonify({"ok": False, "message": f"Item '{item_name}' not found."})
        inv = player.setdefault("inventory", [])
        for _ in range(qty):
            inv.append(matched)
        session.modified = True
        return jsonify({"ok": True, "message": f"Added {qty}x {matched} to inventory."})
    elif kind == "mining_xp":
        amount = int(body.get("amount", 0))
        if amount <= 0:
            return jsonify({"ok": False, "message": "Amount must be positive."})
        player["mining_xp"] = player.get("mining_xp", 0) + amount
        session.modified = True
        return jsonify(
            {
                "ok": True,
                "message": f"Gave {amount} mining XP. Mining level: {_get_mining_level(player)}.",
            }
        )
    else:
        return jsonify(
            {"ok": False, "message": "kind must be: gold, xp, item, or mining_xp."}
        )


@app.route("/api/admin/game/set", methods=["POST"])
def api_game_set():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify(
            {
                "ok": False,
                "message": "No active character in session. Load a save first.",
            }
        )
    body = request.get_json(force=True, silent=True) or {}
    kind = body.get("kind", "").lower()
    if kind == "level":
        lvl = int(body.get("value", 1))
        if lvl < 1 or lvl > 999:
            return jsonify({"ok": False, "message": "Level must be 1–999."})
        player["level"] = lvl
        player["rank"] = get_rank(lvl)
        player["experience"] = 0
        player["experience_to_next"] = int(100 * (1.5 ** (lvl - 1)))
        session.modified = True
        return jsonify(
            {"ok": True, "message": f"Level set to {lvl} (rank {player['rank']})."}
        )
    elif kind == "stat":
        stat = body.get("stat", "").lower()
        value = int(body.get("value", 0))
        valid_stats = {
            "hp",
            "max_hp",
            "mp",
            "max_mp",
            "attack",
            "defense",
            "speed",
            "gold",
        }
        if stat not in valid_stats:
            return jsonify(
                {
                    "ok": False,
                    "message": f"Stat must be one of: {', '.join(sorted(valid_stats))}.",
                }
            )
        if value < 0:
            return jsonify({"ok": False, "message": "Value cannot be negative."})
        player[stat] = value
        if stat == "max_hp":
            player["hp"] = min(player["hp"], value)
        if stat == "max_mp":
            player["mp"] = min(player["mp"], value)
        session.modified = True
        return jsonify({"ok": True, "message": f"{stat} set to {value}."})
    elif kind == "mining_level":
        lvl = int(body.get("value", 1))
        if lvl < 1 or lvl > 25:
            return jsonify({"ok": False, "message": "Mining level must be 1–25."})
        player["mining_xp"] = _mining_xp_for_level(lvl)
        session.modified = True
        return jsonify({"ok": True, "message": f"Mining level set to {lvl}."})
    else:
        return jsonify(
            {"ok": False, "message": "kind must be: level, stat, or mining_level."}
        )


@app.route("/api/admin/game/heal", methods=["POST"])
def api_game_heal():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify(
            {
                "ok": False,
                "message": "No active character in session. Load a save first.",
            }
        )
    player["hp"] = player.get("max_hp", 100)
    player["mp"] = player.get("max_mp", 50)
    session.modified = True
    return jsonify(
        {
            "ok": True,
            "message": f"Fully restored. HP: {player['hp']}/{player['max_hp']}  MP: {player['mp']}/{player['max_mp']}.",
        }
    )


@app.route("/api/admin/game/remove", methods=["POST"])
def api_game_remove():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify(
            {
                "ok": False,
                "message": "No active character in session. Load a save first.",
            }
        )
    body = request.get_json(force=True, silent=True) or {}
    item_name = body.get("item", "").strip()
    qty = max(1, int(body.get("qty", 1)))
    inv = player.get("inventory", [])
    matched = next((k for k in set(inv) if k.lower() == item_name.lower()), None)
    if not matched:
        return jsonify(
            {"ok": False, "message": f"'{item_name}' not found in inventory."}
        )
    removed = 0
    for _ in range(qty):
        if matched in inv:
            inv.remove(matched)
            removed += 1
        else:
            break
    session.modified = True
    return jsonify(
        {"ok": True, "message": f"Removed {removed}x {matched} from inventory."}
    )


@app.route("/api/admin/game/inventory", methods=["GET"])
def api_game_inventory():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify(
            {
                "ok": False,
                "message": "No active character in session. Load a save first.",
            }
        )
    inv = player.get("inventory", [])
    counts = {}
    for item in inv:
        counts[item] = counts.get(item, 0) + 1
    return jsonify({"ok": True, "inventory": counts, "gold": player.get("gold", 0)})


@app.route("/api/admin/tp", methods=["POST"])
def api_admin_tp():
    caller = session.get("online_username", "")
    if not _is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("target", "self").strip()
    area_key = body.get("area", "").strip().lower().replace(" ", "_")
    if not area_key or area_key not in GAME_DATA.get("areas", {}):
        close = [k for k in GAME_DATA.get("areas", {}) if area_key in k]
        hint = f" Did you mean: {', '.join(close[:4])}?" if close else ""
        return jsonify({"ok": False, "message": f"Unknown area: '{area_key}'.{hint}"})
    area_name = GAME_DATA["areas"][area_key].get("name", area_key)
    if target == "self" or target.lower() == caller.lower():
        session["current_area"] = area_key
        va = session.get("visited_areas", [])
        if area_key not in va:
            va.append(area_key)
            session["visited_areas"] = va
        session.modified = True
        return jsonify({"ok": True, "message": f"Teleported yourself to {area_name}."})
    elif target == "all":
        known = list(
            set(list(_chat_online.values()) + list(_username_to_userid.keys()))
        )
        count = 0
        for uname in known:
            _pending_tp[uname.lower()] = area_key
            count += 1
        session["current_area"] = area_key
        va = session.get("visited_areas", [])
        if area_key not in va:
            va.append(area_key)
            session["visited_areas"] = va
        session.modified = True
        return jsonify(
            {
                "ok": True,
                "message": f"Teleporting everyone ({count} known players) to {area_name}. Takes effect on their next page load.",
            }
        )
    else:
        _pending_tp[target.lower()] = area_key
        return jsonify(
            {
                "ok": True,
                "message": f"Teleport queued for {target} → {area_name}. Takes effect on their next page load.",
            }
        )


from asgiref.wsgi import WsgiToAsgi as _WsgiToAsgi


async def _on_startup():
    global _asyncio_loop, _bg_started
    _asyncio_loop = _asyncio.get_running_loop()
    from concurrent.futures import ThreadPoolExecutor

    _asyncio_loop.set_default_executor(ThreadPoolExecutor(max_workers=20))
    if not _bg_started:
        _bg_started = True
        _asyncio.create_task(_world_tick())


asgi_app = _socketio_module.ASGIApp(
    sio,
    other_asgi_app=_WsgiToAsgi(app),
    on_startup=_on_startup,
)


@app.route("/land/map")
def land_map_page():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    if session.get("current_area") != "your_land":
        return redirect(url_for("game") + "?tab=land")
    land_data = _build_land_data(player)
    return render_template(
        "land_map.html",
        player=player,
        land_data=land_data,
        online_username=session.get("online_username"),
    )


@app.route("/land/shop")
def land_shop_page():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    if session.get("current_area") != "your_land":
        return redirect(url_for("game") + "?tab=land")
    land_data = _build_land_data(player)
    return render_template(
        "land_shop.html",
        player=player,
        land_data=land_data,
        online_username=session.get("online_username"),
    )


@app.route("/land/pets")
def land_pets_page():
    player = get_player()
    if not player:
        return redirect(url_for("index"))
    if session.get("current_area") != "your_land":
        return redirect(url_for("game") + "?tab=land")
    land_data = _build_land_data(player)
    return render_template(
        "land_pets.html",
        player=player,
        land_data=land_data,
        online_username=session.get("online_username"),
    )


@app.route("/api/login", methods=["POST"])
@limiter.limit("10 per minute")
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify(
            {"ok": False, "message": "Username and password are required."}
        ), 400
    result = login_user(username, password)
    if not result["ok"]:
        return jsonify({"ok": False, "message": result["message"]}), 401
    user_id = result["user_id"]
    actual_username = result.get("username") or username.lower()
    if _is_banned(actual_username):
        return jsonify({"ok": False, "message": "Your account has been banned."}), 403
    other_active = [uid for uid in _active_sessions if uid != user_id]
    if len(other_active) >= 100:
        return jsonify(
            {
                "ok": False,
                "server_full": True,
                "message": "The server is full. Please try again later.",
            }
        ), 503
    session_token = str(uuid.uuid4())
    _active_sessions[user_id] = session_token
    _session_last_activity[user_id] = _time_module.time()
    _username_to_userid[actual_username.lower()] = user_id
    session["online_username"] = actual_username
    session["online_user_id"] = user_id
    session["session_token"] = session_token
    session.modified = True
    return jsonify(
        {
            "ok": True,
            "message": result["message"],
            "user_id": user_id,
            "username": actual_username,
            "session_token": session_token,
        }
    )


@app.route("/api/online/profile", methods=["POST"])
@limiter.limit("20 per minute")
def api_online_profile():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify(
            {"ok": False, "message": "Username and password are required."}
        ), 400
    result = login_user(username, password)
    if not result["ok"]:
        return jsonify({"ok": False, "message": result["message"]}), 401
    if _is_banned(result.get("username") or username):
        return jsonify({"ok": False, "message": "Your account has been banned."}), 403
    user_id = result["user_id"]
    actual_username = result.get("username") or username.lower()
    email = get_user_email(user_id)
    pending_email = get_pending_email_verification(user_id)
    if pending_email and not email:
        return jsonify(
            {
                "ok": False,
                "message": "Your email address has not been verified yet. Please check your inbox and confirm before accessing your profile.",
                "email_pending": pending_email,
            }
        ), 403
    player = get_player()
    profile = {
        "user_id": user_id,
        "username": actual_username,
        "email": email,
        "email_verified": email is not None,
        "email_pending": pending_email,
    }
    if player and session.get("online_user_id") == user_id:
        profile["character"] = {
            "name": player.get("name"),
            "race": player.get("race"),
            "char_class": player.get("char_class"),
            "level": player.get("level"),
            "xp": player.get("xp"),
            "gold": player.get("gold"),
            "current_area": session.get("current_area"),
        }
    return jsonify({"ok": True, "profile": profile})


# ═══════════════════════════════════════════════════════════════
# JSON Game APIs
# ═══════════════════════════════════════════════════════════════

def _api_player_summary(player):
    return {
        "name":         player.get("name"),
        "level":        player.get("level"),
        "hp":           player.get("hp"),
        "max_hp":       player.get("max_hp"),
        "mp":           player.get("mp"),
        "max_mp":       player.get("max_mp"),
        "attack":       player.get("attack"),
        "defense":      player.get("defense"),
        "speed":        player.get("speed"),
        "gold":         player.get("gold"),
        "xp":           player.get("xp"),
        "race":         player.get("race"),
        "char_class":   player.get("char_class"),
        "current_area": session.get("current_area"),
        "in_battle":    bool(session.get("battle_enemy")),
        "equipment":    player.get("equipment", {}),
        "attributes":   player.get("attributes", {}),
    }

def _api_battle_summary():
    enemy = session.get("battle_enemy") or {}
    return {
        "enemy_name":    enemy.get("name"),
        "enemy_hp":      enemy.get("hp"),
        "enemy_max_hp":  enemy.get("max_hp"),
        "enemy_attack":  enemy.get("attack"),
        "enemy_defense": enemy.get("defense"),
        "is_boss":       enemy.get("is_boss", False),
        "log":           (session.get("battle_log") or [])[-10:],
    }

def _api_battle_outcome(player, enemy, log):
    """Determine and handle battle outcome; returns a JSON response."""
    if enemy.get("hp", 1) <= 0:
        log.append(f"The {enemy['name']} falls! Victory!")
        exp = enemy.get("exp_reward", enemy.get("experience_reward", 30))
        gold_gain = enemy.get("gold_reward", 10)
        _area_name_bw = GAME_DATA["areas"].get(session.get("current_area", ""), {}).get("name", "")
        current_weather = get_real_weather(_area_name_bw)
        exp_bonus_pct, gold_bonus_pct = get_weather_bonuses(current_weather)
        if exp_bonus_pct > 0:
            exp += int(exp * exp_bonus_pct)
        if gold_bonus_pct > 0:
            gold_gain += int(gold_gain * gold_bonus_pct)
        player["gold"] += gold_gain
        leveled = gain_experience(player, exp)
        _group_contribute(exp, gold_gain, f"defeated {enemy.get('name','an enemy')} in battle")
        loot_item = None
        loot = enemy.get("loot_table", [])
        if loot and random.random() < min(0.80, 0.35 + player.get("attr_discovery", 0.0)):
            loot_item = random.choice(loot)
            player["inventory"].append(loot_item)
            log.append(f"The enemy drops: {loot_item}.")
        if leveled:
            log.append(f"You reached level {player['level']}!")
        enemy_key = enemy.get("key", enemy.get("name", "").lower().replace(" ", "_"))
        update_quest_kills(enemy_key, enemy.get("name", ""))
        update_weekly_challenge(player, "kill_count", 1)
        _record_activity("boss_kills" if enemy.get("is_boss") else "battles")
        if enemy.get("is_boss"):
            update_weekly_challenge(player, "boss_kill", 1)
            player["total_bosses_defeated"] = player.get("total_bosses_defeated", 0) + 1
        session.pop("battle_player_effects", None)
        session.pop("battle_enemy_effects", None)
        session.pop("battle_companions", None)
        session["battle_log"] = log
        session["battle_enemy"] = None
        save_player(player)
        _autosave()
        return jsonify({
            "ok": True, "outcome": "victory",
            "log": log[-10:], "exp_gained": exp, "gold_gained": gold_gain,
            "loot_item": loot_item, "leveled_up": leveled,
            "player": _api_player_summary(player),
            "message": f"You defeated the {enemy['name']}! +{exp} EXP, +{gold_gain} gold.",
        })
    if player["hp"] <= 0:
        log.append("You fall in battle...")
        player["hp"] = max(1, int(player["max_hp"] * 0.25))
        log.append(f"You awaken battered. HP: {player['hp']}")
        _record_activity("deaths")
        session.pop("battle_player_effects", None)
        session.pop("battle_enemy_effects", None)
        session.pop("battle_companions", None)
        session["battle_log"] = log
        session["battle_enemy"] = None
        save_player(player)
        _autosave()
        return jsonify({
            "ok": True, "outcome": "defeat",
            "log": log[-10:],
            "player": _api_player_summary(player),
            "message": f"You were defeated by the {enemy['name']}.",
        })
    session["battle_enemy"] = enemy
    session["battle_log"] = log
    save_player(player)
    _autosave()
    return jsonify({
        "ok": True, "outcome": "ongoing",
        "log": log[-10:],
        "player": _api_player_summary(player),
        "battle": _api_battle_summary(),
    })

# ── GET /api/game/state ─────────────────────────────────────────────────────────
@app.route("/api/game/state", methods=["GET"])
def api_game_state():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    in_battle = bool(session.get("battle_enemy"))
    state = {
        "ok": True,
        "player": _api_player_summary(player),
        "inventory": player.get("inventory", []),
        "messages": (session.get("messages") or [])[-20:],
        "area": {
            "key":         area_key,
            "name":        area.get("name", area_key.replace("_", " ").title()),
            "description": area.get("description", ""),
            "connections": area.get("connections", []),
            "can_rest":    area.get("can_rest", False),
            "rest_cost":   area.get("rest_cost", 0),
            "has_shop":    bool(area.get("shop")),
            "has_mine":    bool(area.get("mine")),
            "difficulty":  area.get("difficulty", 1),
        },
        "in_battle": in_battle,
    }
    if in_battle:
        state["battle"] = _api_battle_summary()
    return jsonify(state)

# ── GET /api/battle/state ───────────────────────────────────────────────────────
@app.route("/api/battle/state", methods=["GET"])
def api_battle_state():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    enemy = session.get("battle_enemy")
    if not enemy:
        return jsonify({"ok": False, "in_battle": False, "message": "Not in battle."})
    return jsonify({
        "ok": True, "in_battle": True,
        "player": _api_player_summary(player),
        "battle": _api_battle_summary(),
    })

# ── POST /api/action/explore ────────────────────────────────────────────────────
@app.route("/api/action/explore", methods=["POST"])
@limiter.limit("30 per minute")
def api_action_explore():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    if session.get("battle_enemy"):
        return jsonify({"ok": False, "message": "You are in battle."}), 409
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    possible_enemies = area.get("possible_enemies", [])
    possible_bosses  = area.get("possible_bosses", [])
    player["explore_count"] = player.get("explore_count", 0) + 1
    advance_crops(player); advance_game_time(player); apply_regen_effects(player)
    if possible_bosses and random.random() < 0.08:
        boss_key = random.choice(possible_bosses)
        boss_data = GAME_DATA.get("bosses", {}).get(boss_key, {})
        if boss_data:
            lvl = _effective_mob_level(player["level"]); scale = 1 + (lvl - 1) * 0.12
            enemy = {
                "key": boss_key,
                "name": boss_data.get("name", boss_key.replace("_", " ").title()),
                "hp": int(boss_data.get("hp", 200) * scale), "max_hp": int(boss_data.get("hp", 200) * scale),
                "attack": int(boss_data.get("attack", 20) * scale), "defense": int(boss_data.get("defense", 10) * scale),
                "speed": boss_data.get("speed", 12), "exp_reward": int(boss_data.get("experience_reward", 200) * scale),
                "gold_reward": int(boss_data.get("gold_reward", 100) * scale),
                "loot_table": boss_data.get("unique_loot", []), "is_boss": True,
                "tags": boss_data.get("tags", ["humanoid"]),
            }
            session["battle_enemy"] = enemy
            session["battle_log"] = [f"{enemy['name']} blocks your path! Boss battle! (HP: {enemy['hp']})"]
            session["battle_player_effects"] = {}; session["battle_enemy_effects"] = {}
            session["battle_companions"] = _build_battle_companions(player)
            session.modified = True; save_player(player)
            return jsonify({"ok": True, "outcome": "battle_started", "battle": _api_battle_summary(), "player": _api_player_summary(player)})
    if possible_enemies and random.random() < 0.55:
        enemy_key = random.choice(possible_enemies)
        enemy_data = GAME_DATA["enemies"].get(enemy_key, {})
        if isinstance(enemy_data, dict) and enemy_data:
            lvl = _effective_mob_level(player["level"]); scale = 1 + (lvl - 1) * 0.12
            enemy = {
                "key": enemy_key,
                "name": enemy_data.get("name", enemy_key.replace("_", " ").title()),
                "hp": int(enemy_data.get("hp", 50) * scale), "max_hp": int(enemy_data.get("hp", 50) * scale),
                "attack": int(enemy_data.get("attack", 10) * scale), "defense": int(enemy_data.get("defense", 5) * scale),
                "speed": enemy_data.get("speed", 10), "exp_reward": int(enemy_data.get("experience_reward", 30) * scale),
                "gold_reward": max(1, int(enemy_data.get("gold_reward", 10)) + dice.between(-3, 10)),
                "loot_table": enemy_data.get("loot_table", []), "tags": enemy_data.get("tags", ["humanoid"]),
            }
            session["battle_enemy"] = enemy
            session["battle_log"] = [f"A {enemy['name']} emerges! (HP: {enemy['hp']})"]
            session["battle_player_effects"] = {}; session["battle_enemy_effects"] = {}
            session["battle_companions"] = _build_battle_companions(player)
            session.modified = True; save_player(player)
            return jsonify({"ok": True, "outcome": "battle_started", "battle": _api_battle_summary(), "player": _api_player_summary(player)})
    events = []
    roll = random.random()
    if roll < 0.08:
        dmg = dice.between(5, max(6, player.get("level", 1) * 3))
        player["hp"] = max(1, player["hp"] - dmg); events.append(f"Trap! You take {dmg} damage.")
    elif roll < 0.14:
        mp_r = dice.between(10, 30); player["mp"] = min(player["max_mp"], player["mp"] + mp_r)
        events.append(f"Ancient shrine: +{mp_r} MP.")
    elif roll < 0.19:
        xp_b = dice.between(15, 40); gain_experience(player, xp_b); events.append(f"Worn tome: +{xp_b} EXP.")
    elif roll < 0.23:
        finds = random.choice([["Health Potion"], ["Mana Potion"], ["Health Potion", "Rope"]])
        for i in finds: player["inventory"].append(i)
        events.append(f"Supplies found: {', '.join(finds)}.")
    if random.random() < 0.30:
        g = dice.between(5, 20); player["gold"] += g; events.append(f"+{g} gold.")
    if random.random() < 0.40:
        tier = max(1, min(area.get("difficulty", 1), 5))
        mats = MATERIALS_BY_TIER.get(tier, MATERIALS_BY_TIER[1])
        gathered = random.choices(mats, k=dice.roll_1d(3))
        for m in gathered: player["inventory"].append(m)
        events.append(f"Materials: {', '.join(gathered)}.")
    roll2 = random.random()
    if roll2 < 0.20:
        h = dice.between(10, 30); player["hp"] = min(player["max_hp"], player["hp"] + h); events.append(f"Healing herb: +{h} HP.")
    elif roll2 < min(0.60, 0.35 + player.get("attr_discovery", 0.0)):
        player["inventory"].append("Health Potion"); events.append("Found a Health Potion.")
    save_player(player); _autosave()
    return jsonify({
        "ok": True, "outcome": "explored",
        "events": events, "player": _api_player_summary(player),
        "message": " ".join(events) if events else "You explore the area but find nothing notable.",
    })

# ── POST /api/action/travel ─────────────────────────────────────────────────────
@app.route("/api/action/travel", methods=["POST"])
@limiter.limit("30 per minute")
def api_action_travel():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    if session.get("battle_enemy"):
        return jsonify({"ok": False, "message": "You are in battle."}), 409
    data = request.get_json(force=True, silent=True) or {}
    dest_key = data.get("dest", "").strip()
    if not dest_key:
        return jsonify({"ok": False, "message": "Destination required (dest)."}), 400
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    if dest_key not in area.get("connections", []):
        return jsonify({"ok": False, "message": "That destination is not reachable from here."}), 400
    session["current_area"] = dest_key
    dest_area = GAME_DATA["areas"].get(dest_key, {})
    dest_name = dest_area.get("name", dest_key.replace("_", " ").title())
    visited = session.get("visited_areas", [])
    first_visit = dest_key not in visited
    if first_visit:
        visited.append(dest_key); session["visited_areas"] = visited
    _set_activity(player, f"wandering {dest_name}")
    session.modified = True; save_player(player); _autosave()
    return jsonify({
        "ok": True, "message": f"You travel to {dest_name}.",
        "area_key": dest_key, "area_name": dest_name, "first_visit": first_visit,
        "player": _api_player_summary(player),
    })

# ── POST /api/action/rest ───────────────────────────────────────────────────────
@app.route("/api/action/rest", methods=["POST"])
@limiter.limit("20 per minute")
def api_action_rest():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    if session.get("battle_enemy"):
        return jsonify({"ok": False, "message": "You are in battle."}), 409
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    if not area.get("can_rest", False):
        return jsonify({"ok": False, "message": "There is nowhere to rest here."}), 400
    cost = area.get("rest_cost", 0)
    if cost > 0 and player["gold"] < cost:
        return jsonify({"ok": False, "message": f"You need {cost} gold to rest here."}), 400
    player["gold"] -= cost
    player["hp"] = player["max_hp"]; player["mp"] = player["max_mp"]
    advance_crops(player); advance_game_time(player); apply_regen_effects(player)
    _revive_companions(player)
    save_player(player); _autosave()
    return jsonify({
        "ok": True,
        "message": f"You rest{f' for {cost} gold' if cost else ''}. HP and MP fully restored.",
        "player": _api_player_summary(player),
    })

# ── POST /api/action/mine ───────────────────────────────────────────────────────
@app.route("/api/action/mine", methods=["POST"])
@limiter.limit("30 per minute")
def api_action_mine():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    if session.get("battle_enemy"):
        return jsonify({"ok": False, "message": "You are in battle."}), 409
    area_key = session.get("current_area", "starting_village")
    area = GAME_DATA["areas"].get(area_key, {})
    if not area.get("mine"):
        return jsonify({"ok": False, "message": "There is no mine here."}), 400
    has_pickaxe = any("pickaxe" in i.lower() for i in player.get("inventory", []) + [player.get("equipment", {}).get("weapon", "")])
    if not has_pickaxe:
        return jsonify({"ok": False, "message": "You need a pickaxe to mine."}), 400
    str_bonus = player.get("attributes", {}).get("str", 0) * 0.5
    success_chance = min(0.95, 0.55 + str_bonus / 100)
    if random.random() > success_chance:
        save_player(player)
        return jsonify({"ok": True, "message": "You swing your pickaxe but find nothing useful.", "found": None, "player": _api_player_summary(player)})
    mine_data = area.get("mine", {})
    ore_pool = mine_data.get("ore_pool", ["Iron Ore"])
    ore = random.choice(ore_pool)
    player["inventory"].append(ore)
    mining_xp = random.randint(8, 20)
    player["mining_xp"] = player.get("mining_xp", 0) + mining_xp
    save_player(player); _autosave()
    return jsonify({"ok": True, "message": f"You mine {ore}. (+{mining_xp} mining XP)", "found": ore, "player": _api_player_summary(player)})

# ── POST /api/action/buy ────────────────────────────────────────────────────────
@app.route("/api/action/buy", methods=["POST"])
@limiter.limit("60 per minute")
def api_action_buy():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    data = request.get_json(force=True, silent=True) or {}
    item_name = data.get("item", "").strip()
    if not item_name:
        return jsonify({"ok": False, "message": "Item name required."}), 400
    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict):
        item_data = {}
    base_price = item_data.get("price", item_data.get("value", 20))
    discount = min(0.50, player.get("attr_gold_discount", 0.0))
    price = max(1, int(base_price * (1.0 - discount)))
    if player["gold"] < price:
        return jsonify({"ok": False, "message": f"Not enough gold. Need {price}g, have {player['gold']}g."}), 400
    player["gold"] -= price
    player["inventory"].append(item_name)
    save_player(player); _autosave()
    return jsonify({"ok": True, "message": f"Bought {item_name} for {price}g.", "item": item_name, "price": price, "player": _api_player_summary(player)})

# ── POST /api/action/sell ───────────────────────────────────────────────────────
@app.route("/api/action/sell", methods=["POST"])
@limiter.limit("60 per minute")
def api_action_sell():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    data = request.get_json(force=True, silent=True) or {}
    item_name = data.get("item", "").strip()
    if not item_name:
        return jsonify({"ok": False, "message": "Item name required."}), 400
    if item_name not in player.get("inventory", []):
        return jsonify({"ok": False, "message": f"You don't have {item_name}."}), 400
    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict):
        item_data = {}
    sell_price = max(1, int(item_data.get("price", item_data.get("value", 5)) * 0.5))
    player["inventory"].remove(item_name)
    player["gold"] += sell_price
    save_player(player); _autosave()
    return jsonify({"ok": True, "message": f"Sold {item_name} for {sell_price}g.", "item": item_name, "gold_received": sell_price, "player": _api_player_summary(player)})

# ── POST /api/action/equip ──────────────────────────────────────────────────────
@app.route("/api/action/equip", methods=["POST"])
@limiter.limit("60 per minute")
def api_action_equip():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    data = request.get_json(force=True, silent=True) or {}
    item_name = data.get("item", "").strip()
    if not item_name:
        return jsonify({"ok": False, "message": "Item name required."}), 400
    ok, msg = equip_item(player, item_name)
    save_player(player); _autosave()
    return jsonify({"ok": ok, "message": msg, "player": _api_player_summary(player)}), (200 if ok else 400)

# ── POST /api/action/unequip ────────────────────────────────────────────────────
@app.route("/api/action/unequip", methods=["POST"])
@limiter.limit("60 per minute")
def api_action_unequip():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    data = request.get_json(force=True, silent=True) or {}
    slot = data.get("slot", "").strip()
    if not slot:
        return jsonify({"ok": False, "message": "Slot required (weapon, armor, accessory, etc.)."}), 400
    ok, msg = unequip_item(player, slot)
    save_player(player); _autosave()
    return jsonify({"ok": ok, "message": msg, "player": _api_player_summary(player)}), (200 if ok else 400)

# ── POST /api/action/use_item ───────────────────────────────────────────────────
@app.route("/api/action/use_item", methods=["POST"])
@limiter.limit("60 per minute")
def api_action_use_item():
    player = get_player()
    if not player:
        return jsonify({"ok": False, "message": "No active character."}), 401
    data = request.get_json(force=True, silent=True) or {}
    item_name = data.get("item", "").strip()
    if not item_name:
        return jsonify({"ok": False, "message": "Item name required."}), 400
    if item_name not in player.get("inventory", []):
        return jsonify({"ok": False, "message": f"You don't have {item_name}."}), 400
    item_data = GAME_DATA["items"].get(item_name, {})
    if not isinstance(item_data, dict): item_data = {}
    lower = item_name.lower()
    msg = ""
    if "health" in lower or ("potion" in lower and "mana" not in lower):
        heal = dice.between(70, 130) if ("large" in lower or "greater" in lower) else dice.between(40, 70)
        player["hp"] = min(player["max_hp"], player["hp"] + heal)
        player["inventory"].remove(item_name)
        msg = f"You use {item_name}: +{heal} HP."
    elif "mana" in lower:
        r = dice.between(25, 50); player["mp"] = min(player["max_mp"], player["mp"] + r)
        player["inventory"].remove(item_name); msg = f"You use {item_name}: +{r} MP."
    elif "elixir" in lower or "tears" in lower:
        heal = dice.between(50, 100); player["hp"] = min(player["max_hp"], player["hp"] + heal)
        player["inventory"].remove(item_name); msg = f"You use {item_name}: +{heal} HP."
    else:
        return jsonify({"ok": False, "message": f"{item_name} cannot be used directly."}), 400
    save_player(player); _autosave()
    return jsonify({"ok": True, "message": msg, "player": _api_player_summary(player)})

# ── POST /api/battle/attack ─────────────────────────────────────────────────────
@app.route("/api/battle/attack", methods=["POST"])
@limiter.limit("60 per minute")
def api_battle_attack():
    player = get_player()
    enemy = session.get("battle_enemy") or {}
    if not player or not enemy:
        return jsonify({"ok": False, "message": "Not in battle."}), 400
    log = session.get("battle_log", [])
    player_effects = session.get("battle_player_effects") or {}
    enemy_effects  = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])
    enemy_name = enemy.get("name", "Enemy")
    stunned = process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(enemy, enemy_effects, log, enemy_name, is_enemy=True, player_level=player.get("level", 1))
    session["battle_player_effects"] = player_effects
    session["battle_enemy_effects"]  = enemy_effects
    if player["hp"] <= 0 or enemy.get("hp", 1) <= 0:
        return _api_battle_outcome(player, enemy, log)
    if not stunned:
        if not _check_weapon_accuracy(player, enemy):
            log.append(f"You swing at the {enemy_name} but miss!")
        else:
            eff_def = enemy["defense"]
            if enemy_effects.get("weaken", {}).get("turns", 0) > 0:
                eff_def = max(0, eff_def - enemy_effects["weaken"].get("def_reduction", 0))
            if enemy_effects.get("armor_crushed", {}).get("turns", 0) > 0:
                eff_def = max(0, eff_def - enemy_effects["armor_crushed"].get("def_reduction", 0))
            eq_weapon = GAME_DATA["items"].get(player.get("equipment", {}).get("weapon", ""), {})
            armor_pen = eq_weapon.get("armor_penetration", 0) if isinstance(eq_weapon, dict) else 0
            if armor_pen: eff_def = int(eff_def * (1 - armor_pen / 100.0))
            p_dmg = max(1, player["attack"] - eff_def + dice.between(-3, 6))
            crit_rate = 0.10 + min(0.40, player.get("attr_crit_chance", 0) / 100.0)
            if random.random() < crit_rate:
                p_dmg = int(p_dmg * (1.6 + player.get("attr_crit_damage", 0) / 100.0))
                log.append(f"CRITICAL STRIKE! You deal {p_dmg} damage to the {enemy_name}!")
            else:
                log.append(f"You attack the {enemy_name} for {p_dmg} damage.")
            enemy["hp"] = max(0, enemy["hp"] - p_dmg)
            for bonus_dmg, bonus_msg in _get_weapon_combat_effects(player, enemy):
                if bonus_dmg > 0: enemy["hp"] = max(0, enemy["hp"] - bonus_dmg); log.append(bonus_msg)
            for msg in _get_weapon_on_hit_procs(player, enemy, enemy_effects): log.append(msg)
    if enemy["hp"] <= 0:
        _sync_companion_hp_to_player(player, battle_companions); _restore_companion_hp(player)
        return _api_battle_outcome(player, enemy, log)
    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)
    if enemy["hp"] > 0 and _companion_take_action(battle_companions, enemy, log):
        _sync_companion_hp_to_player(player, battle_companions); _restore_companion_hp(player)
        session["battle_companions"] = battle_companions
        return _api_battle_outcome(player, enemy, log)
    session["battle_companions"] = battle_companions
    if player["hp"] <= 0:
        won = _companion_last_stand(battle_companions, enemy, log)
        _sync_companion_hp_to_player(player, battle_companions)
        if won:
            player["hp"] = 1; _restore_companion_hp(player)
            log.append("Your companions fought on and saved you!")
        session["battle_player_effects"] = player_effects
        session["battle_enemy_effects"]  = enemy_effects
        return _api_battle_outcome(player, enemy, log)
    session["battle_enemy"] = enemy; session["battle_log"] = log
    session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
    save_player(player); _autosave()
    return jsonify({"ok": True, "outcome": "ongoing", "log": log[-10:], "player": _api_player_summary(player), "battle": _api_battle_summary()})

# ── POST /api/battle/defend ─────────────────────────────────────────────────────
@app.route("/api/battle/defend", methods=["POST"])
@limiter.limit("60 per minute")
def api_battle_defend():
    player = get_player()
    enemy = session.get("battle_enemy") or {}
    if not player or not enemy:
        return jsonify({"ok": False, "message": "Not in battle."}), 400
    log = session.get("battle_log", [])
    player_effects = session.get("battle_player_effects") or {}
    enemy_effects  = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])
    enemy_name = enemy.get("name", "Enemy")
    process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(enemy, enemy_effects, log, enemy_name, is_enemy=True, player_level=player.get("level", 1))
    if player["hp"] <= 0 or enemy.get("hp", 1) <= 0:
        return _api_battle_outcome(player, enemy, log)
    log.append("You brace yourself, raising your guard.")
    real_def = player["defense"]; player["defense"] = real_def * 2
    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)
    player["defense"] = real_def
    if enemy["hp"] > 0 and _companion_take_action(battle_companions, enemy, log):
        _sync_companion_hp_to_player(player, battle_companions); _restore_companion_hp(player)
        session["battle_companions"] = battle_companions
        return _api_battle_outcome(player, enemy, log)
    session["battle_companions"] = battle_companions
    if player["hp"] <= 0:
        won = _companion_last_stand(battle_companions, enemy, log)
        _sync_companion_hp_to_player(player, battle_companions)
        if won:
            player["hp"] = 1; _restore_companion_hp(player); log.append("Your companions saved you!")
        session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
        return _api_battle_outcome(player, enemy, log)
    session["battle_enemy"] = enemy; session["battle_log"] = log
    session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
    save_player(player); _autosave()
    return jsonify({"ok": True, "outcome": "ongoing", "log": log[-10:], "player": _api_player_summary(player), "battle": _api_battle_summary()})

# ── POST /api/battle/flee ───────────────────────────────────────────────────────
@app.route("/api/battle/flee", methods=["POST"])
@limiter.limit("30 per minute")
def api_battle_flee():
    player = get_player()
    enemy = session.get("battle_enemy") or {}
    if not player or not enemy:
        return jsonify({"ok": False, "message": "Not in battle."}), 400
    log = session.get("battle_log", [])
    if random.random() < 0.55:
        log.append("You break away and escape!")
        session.pop("battle_enemy", None); session.pop("battle_player_effects", None)
        session.pop("battle_enemy_effects", None); session.pop("battle_companions", None)
        session["battle_log"] = []
        save_player(player); _autosave()
        return jsonify({"ok": True, "outcome": "fled", "message": f"You fled from the {enemy.get('name','enemy')}.", "player": _api_player_summary(player)})
    e_dmg = max(1, enemy["attack"] - player["defense"] + dice.between(0, 5))
    player["hp"] = max(0, player["hp"] - e_dmg)
    log.append(f"Flee failed! The {enemy.get('name','enemy')} deals {e_dmg} damage!")
    if player["hp"] <= 0:
        return _api_battle_outcome(player, enemy, log)
    session["battle_enemy"] = enemy; session["battle_log"] = log
    save_player(player); _autosave()
    return jsonify({"ok": True, "outcome": "ongoing", "log": log[-10:], "player": _api_player_summary(player), "battle": _api_battle_summary()})

# ── POST /api/battle/spell ──────────────────────────────────────────────────────
@app.route("/api/battle/spell", methods=["POST"])
@limiter.limit("60 per minute")
def api_battle_spell():
    player = get_player()
    enemy = session.get("battle_enemy") or {}
    if not player or not enemy:
        return jsonify({"ok": False, "message": "Not in battle."}), 400
    data = request.get_json(force=True, silent=True) or {}
    spell_name = data.get("spell", "").strip()
    if not spell_name:
        return jsonify({"ok": False, "message": "Spell name required."}), 400
    spells_data = GAME_DATA["spells"]; items_data = GAME_DATA["items"]
    weapon = player.get("equipment", {}).get("weapon")
    available = [s["name"] for s in get_available_spells(weapon, items_data, spells_data)]
    if spell_name not in available:
        return jsonify({"ok": False, "message": "That spell is not available with your current weapon."}), 400
    log = session.get("battle_log", [])
    player_effects = session.get("battle_player_effects") or {}
    enemy_effects  = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])
    enemy_name = enemy.get("name", "Enemy")
    stunned = process_turn_effects(player, player_effects, log, "You")
    process_turn_effects(enemy, enemy_effects, log, enemy_name, is_enemy=True, player_level=player.get("level", 1))
    session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
    if player["hp"] <= 0 or enemy.get("hp", 1) <= 0:
        return _api_battle_outcome(player, enemy, log)
    if stunned:
        session["battle_log"] = log; session["battle_enemy"] = enemy; save_player(player)
        return jsonify({"ok": True, "outcome": "ongoing", "log": log[-10:], "player": _api_player_summary(player), "battle": _api_battle_summary()})
    spell_data = spells_data.get(spell_name, {})
    result = cast_spell(player, enemy, spell_name, spell_data, spell_data.get("effects_data", {}))
    for m in result.get("messages", []): log.append(m["text"])
    session["battle_enemy"] = enemy
    if enemy.get("hp", 1) <= 0:
        _sync_companion_hp_to_player(player, battle_companions); _restore_companion_hp(player)
        return _api_battle_outcome(player, enemy, log)
    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)
    if enemy["hp"] > 0 and _companion_take_action(battle_companions, enemy, log):
        _sync_companion_hp_to_player(player, battle_companions); _restore_companion_hp(player)
        session["battle_companions"] = battle_companions
        return _api_battle_outcome(player, enemy, log)
    session["battle_companions"] = battle_companions
    if player["hp"] <= 0:
        won = _companion_last_stand(battle_companions, enemy, log)
        _sync_companion_hp_to_player(player, battle_companions)
        if won:
            player["hp"] = 1; _restore_companion_hp(player); log.append("Companions saved you!")
        session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
        return _api_battle_outcome(player, enemy, log)
    session["battle_log"] = log; session["battle_enemy"] = enemy
    session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
    save_player(player); _autosave()
    return jsonify({"ok": True, "outcome": "ongoing", "log": log[-10:], "player": _api_player_summary(player), "battle": _api_battle_summary()})

# ── POST /api/battle/use_item ───────────────────────────────────────────────────
@app.route("/api/battle/use_item", methods=["POST"])
@limiter.limit("60 per minute")
def api_battle_use_item():
    player = get_player()
    enemy = session.get("battle_enemy") or {}
    if not player or not enemy:
        return jsonify({"ok": False, "message": "Not in battle."}), 400
    data = request.get_json(force=True, silent=True) or {}
    item_name = data.get("item", "").strip()
    if not item_name:
        return jsonify({"ok": False, "message": "Item name required."}), 400
    if item_name not in player.get("inventory", []):
        return jsonify({"ok": False, "message": f"You don't have {item_name}."}), 400
    log = session.get("battle_log", [])
    player_effects = session.get("battle_player_effects") or {}
    enemy_effects  = session.get("battle_enemy_effects") or {}
    battle_companions = session.get("battle_companions", [])
    lower = item_name.lower()
    used = False
    if "health" in lower or ("potion" in lower and "mana" not in lower):
        heal = dice.between(70, 130) if ("large" in lower or "greater" in lower) else dice.between(40, 70)
        player["hp"] = min(player["max_hp"], player["hp"] + heal)
        player["inventory"].remove(item_name); log.append(f"You use {item_name}: +{heal} HP."); used = True
    elif "mana" in lower:
        r = dice.between(25, 50); player["mp"] = min(player["max_mp"], player["mp"] + r)
        player["inventory"].remove(item_name); log.append(f"You use {item_name}: +{r} MP."); used = True
    if not used:
        return jsonify({"ok": False, "message": f"{item_name} cannot be used in battle."}), 400
    enemy_name = enemy.get("name", "Enemy")
    _enemy_take_turn(enemy, player, player_effects, log, battle_companions)
    if player["hp"] <= 0 or enemy.get("hp", 1) <= 0:
        session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
        return _api_battle_outcome(player, enemy, log)
    session["battle_enemy"] = enemy; session["battle_log"] = log
    session["battle_player_effects"] = player_effects; session["battle_enemy_effects"] = enemy_effects
    save_player(player); _autosave()
    return jsonify({"ok": True, "outcome": "ongoing", "log": log[-10:], "player": _api_player_summary(player), "battle": _api_battle_summary()})

port = int(os.environ.get("PORT", 5000))
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(asgi_app, host="0.0.0.0", port=port)
