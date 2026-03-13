"""
Spell Casting System for Our Legacy 2 - Flask Edition
Stateless functions that operate on player dicts.
"""

import random
from typing import Dict, List, Any, Optional
from utilities.dice import Dice


def get_available_spells(
    weapon_name: Optional[str], items_data: Dict[str, Any], spells_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Return list of spells available for the given weapon."""
    if not weapon_name:
        return []
    weapon = items_data.get(weapon_name, {})
    if not weapon.get("magic_weapon"):
        return []
    spells = []
    for sname, sdata in spells_data.items():
        if weapon_name in sdata.get("allowed_weapons", []):
            spells.append(
                {
                    "name": sname,
                    "mp_cost": sdata.get("mp_cost", 0),
                    "type": sdata.get("type", "damage"),
                    "power": sdata.get("power", 0),
                    "description": sdata.get("description", ""),
                    "effects": sdata.get("effects", []),
                }
            )
    return spells


def can_cast_spell(
    player: Dict[str, Any], spell_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Check if the player can cast a spell."""
    cost = spell_data.get("mp_cost", 0)
    if player.get("mp", 0) < cost:
        return {
            "ok": False,
            "message": f"Not enough MP! Need {cost}, have {player.get('mp', 0)}.",
        }
    return {"ok": True}


def cast_spell(
    player: Dict[str, Any],
    enemy_dict: Dict[str, Any],
    spell_name: str,
    spell_data: Dict[str, Any],
    effects_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Cast a spell. Modifies player dict in place (MP cost).
    Returns a result dict with messages and outcome data.
    """
    messages = []
    cost = spell_data.get("mp_cost", 0)
    check = can_cast_spell(player, spell_data)
    if not check["ok"]:
        return {
            "ok": False,
            "message": check["message"],
            "messages": [{"text": check["message"], "color": "var(--red)"}],
        }

    player["mp"] = player.get("mp", 0) - cost
    spell_type = spell_data.get("type")
    result = {
        "ok": True,
        "spell_name": spell_name,
        "spell_type": spell_type,
        "messages": messages,
    }
    dice = Dice()

    if spell_type == "damage":
        power = spell_data.get("power", 0)
        spell_power_bonus = player.get("attr_spell_power", 0)
        base_damage = power + (player.get("attack", 10) // 2) + spell_power_bonus
        roll = dice.roll_1d(20)

        if roll == 1:
            messages.append(
                {"text": "Critical miss! The spell fizzles!", "color": "var(--red)"}
            )
        elif roll == 20:
            messages.append(
                {
                    "text": "Critical hit! The spell surges with power!",
                    "color": "var(--gold)",
                }
            )

        damage = int(base_damage * roll / 10)
        enemy_defense = enemy_dict.get("defense", 2)
        actual = max(1, damage - enemy_defense)
        enemy_dict["hp"] = max(0, enemy_dict.get("hp", 0) - actual)

        messages.append(
            {
                "text": f"You cast {spell_name} for {actual} damage!",
                "color": "var(--blue)",
            }
        )
        result["damage"] = actual
        result["enemy_hp"] = enemy_dict["hp"]
        result["enemy_alive"] = enemy_dict["hp"] > 0

        for effect_name in spell_data.get("effects", []):
            effect = effects_data.get(effect_name, {})
            etype = effect.get("type", "")
            if etype == "damage_over_time":
                messages.append(
                    {
                        "text": f"{enemy_dict.get('name', 'Enemy')} is burning!",
                        "color": "var(--red)",
                    }
                )
            elif etype == "stun" and random.random() < effect.get("chance", 0.5):
                messages.append(
                    {
                        "text": f"{enemy_dict.get('name', 'Enemy')} is stunned!",
                        "color": "var(--yellow)",
                    }
                )

    elif spell_type == "heal":
        heal_amount = spell_data.get("power", 0)
        old_hp = player.get("hp", 0)
        player["hp"] = min(player.get("max_hp", 100), old_hp + heal_amount)
        healed = player["hp"] - old_hp
        messages.append(
            {
                "text": f"You cast {spell_name} and healed {healed} HP!",
                "color": "var(--green-bright)",
            }
        )
        result["healed"] = healed

    elif spell_type == "buff":
        power = spell_data.get("power", 0)
        for effect_name in spell_data.get("effects", []):
            effect = effects_data.get(effect_name, {})
            modifiers = {}
            for k, v in effect.items():
                if isinstance(v, (int, float)) and (
                    k.endswith("_bonus") or k in ("absorb_amount",)
                ):
                    modifiers[k] = int(v)
            duration = int(effect.get("duration", max(3, power or 3)))
            player.setdefault("active_buffs", []).append(
                {"name": effect_name, "duration": duration, "modifiers": modifiers}
            )
            mod_str = (
                ", ".join(f"+{v} {k}" for k, v in modifiers.items())
                if modifiers
                else effect.get("type", "")
            )
            messages.append(
                {
                    "text": f"Buff applied: {effect_name} ({mod_str}) for {duration} turns!",
                    "color": "var(--green-bright)",
                }
            )
        result["buffs_applied"] = len(spell_data.get("effects", []))

    elif spell_type == "debuff":
        for effect_name in spell_data.get("effects", []):
            effect = effects_data.get(effect_name, {})
            etype = effect.get("type", "")
            if etype == "action_block" and random.random() < effect.get("chance", 0.5):
                messages.append(
                    {
                        "text": f"{enemy_dict.get('name', 'Enemy')} is stunned!",
                        "color": "var(--yellow)",
                    }
                )
            elif etype == "speed_reduction":
                messages.append(
                    {
                        "text": f"{enemy_dict.get('name', 'Enemy')} is slowed!",
                        "color": "var(--yellow)",
                    }
                )
        result["debuffs_applied"] = len(spell_data.get("effects", []))

    else:
        player["mp"] = player.get("mp", 0) + cost
        return {
            "ok": False,
            "message": f"Unknown spell type: {spell_type}",
            "messages": [{"text": "Unknown spell type!", "color": "var(--red)"}],
        }

    return result
