"""
Admin and owner management routes — Flask Blueprint.

All /admin and /api/admin/* endpoints live here.
App-level helpers (GAME_DATA, _is_owner, session state dicts, etc.) are
accessed via a lazy import to avoid circular-import issues at module load time.
"""
import time
from flask import Blueprint, session, jsonify, request, redirect, url_for, render_template

from utilities.supabase_db import (
    admin_ban,
    admin_unban,
    admin_mute,
    admin_unmute,
    admin_add_mod,
    admin_remove_mod,
    admin_get_owner,
    admin_set_owner,
    admin_get_mods,
    admin_list_bans,
    admin_list_mutes,
    admin_warn,
    admin_clear_warns,
)

admin_bp = Blueprint("admin", __name__)


def _h():
    """Lazily return the app module to access shared helpers/state."""
    import app as _app
    return _app


# ── Admin status ─────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/status", methods=["GET"])
def api_admin_status():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    return jsonify(
        {
            "ok": True,
            "is_owner": h._is_owner(caller),
            "owner": admin_get_owner(),
            "admins": admin_get_mods(),
            "banned_users": {r["username"]: r for r in admin_list_bans()},
            "muted_users": {r["username"]: r for r in admin_list_mutes()},
        }
    )


# ── Ban / unban ───────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/ban", methods=["POST"])
def api_admin_ban():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    reason = body.get("reason", "").strip() or "No reason given."
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target.lower() == caller.lower():
        return jsonify({"ok": False, "message": "You cannot ban yourself."}), 400
    if h._is_owner(target) and not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Only the owner can ban the owner."}), 403
    admin_ban(target, reason, caller)
    return jsonify({"ok": True, "message": f"{target} has been banned."})


@admin_bp.route("/api/admin/unban", methods=["POST"])
def api_admin_unban():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_unban(target):
        return jsonify({"ok": False, "message": f"{target} is not banned."}), 404
    return jsonify({"ok": True, "message": f"{target} has been unbanned."})


# ── Mute / unmute ─────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/mute", methods=["POST"])
def api_admin_mute():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    reason = body.get("reason", "").strip() or "No reason given."
    duration_minutes = body.get("duration_minutes")
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target.lower() == caller.lower():
        return jsonify({"ok": False, "message": "You cannot mute yourself."}), 400
    if h._is_owner(target) and not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Only the owner can mute the owner."}), 403
    expires_at = None
    if duration_minutes:
        try:
            expires_at = time.time() + int(duration_minutes) * 60
        except (ValueError, TypeError):
            return jsonify({"ok": False, "message": "Invalid duration."}), 400
    admin_mute(target, expires_at, reason, caller)
    msg = f"{target} has been muted"
    msg += f" for {duration_minutes} minute(s)." if duration_minutes else " permanently."
    return jsonify({"ok": True, "message": msg})


@admin_bp.route("/api/admin/unmute", methods=["POST"])
def api_admin_unmute():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_unmute(target):
        return jsonify({"ok": False, "message": f"{target} is not muted."}), 404
    return jsonify({"ok": True, "message": f"{target} has been unmuted."})


# ── Add / remove admins ───────────────────────────────────────────────────────

@admin_bp.route("/api/admin/add_admin", methods=["POST"])
def api_admin_add_admin():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Only the owner can promote admins."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_add_mod(target):
        return jsonify({"ok": False, "message": f"{target} is already an admin."}), 409
    return jsonify({"ok": True, "message": f"{target} is now an admin."})


@admin_bp.route("/api/admin/remove_admin", methods=["POST"])
def api_admin_remove_admin():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Only the owner can demote admins."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if not admin_remove_mod(target):
        return jsonify({"ok": False, "message": f"{target} is not an admin."}), 404
    return jsonify({"ok": True, "message": f"{target} has been removed from admins."})


# ── Admin console page ────────────────────────────────────────────────────────

@admin_bp.route("/admin")
def admin_console():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return redirect(url_for("index"))
    is_owner = h._is_owner(caller)
    return render_template("admin.html", online_user=caller, is_owner=is_owner)


# ── Items debug page ──────────────────────────────────────────────────────────

@admin_bp.route("/items")
def items_debug():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return redirect(url_for("index"))

    raw: dict = h.GAME_DATA.get("items", {})
    items_list = []
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        entry = {"name": name}
        entry.update(data)
        for field in (
            "texture", "type", "rarity", "weapon_type", "armor_type",
            "description", "effect", "tags", "requirements", "price",
            "attack_bonus", "defense_bonus", "magic_bonus", "crit_chance",
            "aim_accuracy", "parry_chance", "weight", "sharpness",
            "smiting", "value", "min_value", "max_value", "duration",
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
        if r in ["common", "uncommon", "rare", "epic", "legendary"] else 99,
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


# ── Admin data (owner only) ───────────────────────────────────────────────────

@admin_bp.route("/api/admin/data", methods=["GET"])
def api_admin_data():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    return jsonify(
        {
            "ok": True,
            "is_owner": True,
            "owner": admin_get_owner(),
            "mods": admin_get_mods(),
            "bans": admin_list_bans(),
            "mutes": admin_list_mutes(),
            "online_count": len(h._active_sessions),
            "online_users": list(h._username_to_userid.keys()),
        }
    )


# ── Kick ──────────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/kick", methods=["POST"])
def api_admin_kick():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Only the owner can kick players."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip().lower()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target == caller.lower():
        return jsonify({"ok": False, "message": "You cannot kick yourself."}), 400
    uid = h._username_to_userid.get(target)
    if uid:
        h._active_sessions.pop(uid, None)
    h._kicked_usernames.add(target)
    return jsonify({"ok": True, "message": f"{target} has been kicked."})


# ── Warn / clearwarn ─────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/warn", methods=["POST"])
def api_admin_warn_user():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    reason = body.get("reason", "").strip() or "No reason given."
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    count = admin_warn(target, reason)
    return jsonify({"ok": True, "message": f"{target} warned. Total warnings: {count}."})


@admin_bp.route("/api/admin/clearwarn", methods=["POST"])
def api_admin_clearwarn():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_admin_user(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if admin_clear_warns(target):
        return jsonify({"ok": True, "message": f"Warnings cleared for {target}."})
    return jsonify({"ok": False, "message": f"No warnings found for {target}."}), 404


# ── Set owner ─────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/setowner", methods=["POST"])
def api_admin_setowner():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Only the owner can transfer ownership."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("username", "").strip()
    if not target:
        return jsonify({"ok": False, "message": "No username provided."}), 400
    if target.lower() == caller.lower():
        return jsonify({"ok": False, "message": "You are already the owner."}), 400
    admin_set_owner(target)
    return jsonify({"ok": True, "message": f"Ownership transferred to {target}."})


# ── Game / player cheats (owner only) ────────────────────────────────────────

@admin_bp.route("/api/admin/game/stats", methods=["GET"])
def api_game_stats():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character in session. Load a save first."})
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
            "mining_level": h._get_mining_level(player),
            "inventory_count": len(player.get("inventory", [])),
        }
    )


@admin_bp.route("/api/admin/game/give", methods=["POST"])
def api_game_give():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character in session. Load a save first."})
    body = request.get_json(force=True, silent=True) or {}
    kind = body.get("kind", "").lower()
    if kind == "gold":
        amount = int(body.get("amount", 0))
        if amount <= 0:
            return jsonify({"ok": False, "message": "Amount must be positive."})
        player["gold"] = player.get("gold", 0) + amount
        session.modified = True
        return jsonify({"ok": True, "message": f"Gave {amount} gold. Total: {player['gold']}g."})
    elif kind == "xp":
        amount = int(body.get("amount", 0))
        if amount <= 0:
            return jsonify({"ok": False, "message": "Amount must be positive."})
        leveled = h.gain_experience(player, amount)
        session.modified = True
        msg = f"Gave {amount} XP."
        if leveled:
            msg += f" Level up! Now level {player['level']}."
        return jsonify({"ok": True, "message": msg})
    elif kind == "item":
        item_name = body.get("item", "").strip()
        qty = max(1, int(body.get("qty", 1)))
        all_items = h.GAME_DATA.get("items", {})
        matched = next((k for k in all_items if k.lower() == item_name.lower()), None)
        if not matched:
            close = [k for k in all_items if item_name.lower() in k.lower()]
            if close:
                return jsonify({"ok": False, "message": f"Item not found. Did you mean: {', '.join(close[:5])}?"})
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
            {"ok": True, "message": f"Gave {amount} mining XP. Mining level: {h._get_mining_level(player)}."}
        )
    else:
        return jsonify({"ok": False, "message": "kind must be: gold, xp, item, or mining_xp."})


@admin_bp.route("/api/admin/game/set", methods=["POST"])
def api_game_set():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character in session. Load a save first."})
    body = request.get_json(force=True, silent=True) or {}
    kind = body.get("kind", "").lower()
    if kind == "level":
        lvl = int(body.get("value", 1))
        if lvl < 1 or lvl > 999:
            return jsonify({"ok": False, "message": "Level must be 1–999."})
        player["level"] = lvl
        player["rank"] = h.get_rank(lvl)
        player["experience"] = 0
        player["experience_to_next"] = int(100 * (1.5 ** (lvl - 1)))
        session.modified = True
        return jsonify({"ok": True, "message": f"Level set to {lvl} (rank {player['rank']})."})
    elif kind == "stat":
        stat = body.get("stat", "").lower()
        value = int(body.get("value", 0))
        valid_stats = {"hp", "max_hp", "mp", "max_mp", "attack", "defense", "speed", "gold"}
        if stat not in valid_stats:
            return jsonify({"ok": False, "message": f"Stat must be one of: {', '.join(sorted(valid_stats))}."})
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
        player["mining_xp"] = h._mining_xp_for_level(lvl)
        session.modified = True
        return jsonify({"ok": True, "message": f"Mining level set to {lvl}."})
    else:
        return jsonify({"ok": False, "message": "kind must be: level, stat, or mining_level."})


@admin_bp.route("/api/admin/game/heal", methods=["POST"])
def api_game_heal():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character in session. Load a save first."})
    player["hp"] = player.get("max_hp", 100)
    player["mp"] = player.get("max_mp", 50)
    session.modified = True
    return jsonify(
        {"ok": True, "message": f"Fully restored. HP: {player['hp']}/{player['max_hp']}  MP: {player['mp']}/{player['max_mp']}."}
    )


@admin_bp.route("/api/admin/game/remove", methods=["POST"])
def api_game_remove():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character in session. Load a save first."})
    body = request.get_json(force=True, silent=True) or {}
    item_name = body.get("item", "").strip()
    qty = max(1, int(body.get("qty", 1)))
    inv = player.get("inventory", [])
    matched = next((k for k in set(inv) if k.lower() == item_name.lower()), None)
    if not matched:
        return jsonify({"ok": False, "message": f"'{item_name}' not found in inventory."})
    removed = 0
    for _ in range(qty):
        if matched in inv:
            inv.remove(matched)
            removed += 1
        else:
            break
    session.modified = True
    return jsonify({"ok": True, "message": f"Removed {removed}x {matched} from inventory."})


@admin_bp.route("/api/admin/game/inventory", methods=["GET"])
def api_game_inventory():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    player = session.get("player")
    if not player:
        return jsonify({"ok": False, "message": "No active character in session. Load a save first."})
    inv = player.get("inventory", [])
    counts = {}
    for item in inv:
        counts[item] = counts.get(item, 0) + 1
    return jsonify({"ok": True, "inventory": counts, "gold": player.get("gold", 0)})


# ── Teleport ──────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/tp", methods=["POST"])
def api_admin_tp():
    h = _h()
    caller = session.get("online_username", "")
    if not h._is_owner(caller):
        return jsonify({"ok": False, "message": "Forbidden."}), 403
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("target", "self").strip()
    area_key = body.get("area", "").strip().lower().replace(" ", "_")
    if not area_key or area_key not in h.GAME_DATA.get("areas", {}):
        close = [k for k in h.GAME_DATA.get("areas", {}) if area_key in k]
        hint = f" Did you mean: {', '.join(close[:4])}?" if close else ""
        return jsonify({"ok": False, "message": f"Unknown area: '{area_key}'.{hint}"})
    area_name = h.GAME_DATA["areas"][area_key].get("name", area_key)
    if target == "self" or target.lower() == caller.lower():
        session["current_area"] = area_key
        va = session.get("visited_areas", [])
        if area_key not in va:
            va.append(area_key)
            session["visited_areas"] = va
        session.modified = True
        return jsonify({"ok": True, "message": f"Teleported yourself to {area_name}."})
    elif target == "all":
        known = list(set(list(h._chat_online.values()) + list(h._username_to_userid.keys())))
        count = 0
        for uname in known:
            h._pending_tp[uname.lower()] = area_key
            count += 1
        session["current_area"] = area_key
        va = session.get("visited_areas", [])
        if area_key not in va:
            va.append(area_key)
            session["visited_areas"] = va
        session.modified = True
        return jsonify(
            {"ok": True, "message": f"Teleporting everyone ({count} known players) to {area_name}. Takes effect on their next page load."}
        )
    else:
        h._pending_tp[target.lower()] = area_key
        return jsonify(
            {"ok": True, "message": f"Teleport queued for {target} → {area_name}. Takes effect on their next page load."}
        )
