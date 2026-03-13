"""
Battle System for Our Legacy 2 - Flask Edition
Stateless battle functions that return result dicts.
"""
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from utilities.dice import Dice
from utilities.entities import Enemy, Boss


def create_hp_mp_bar(current: int,
                     maximum: int,
                     width: int = 15,
                     color: Optional[str] = None) -> str:
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = max(0, min(width, int((current / maximum) * width)))
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    return f"[{filled}{empty}] {current}/{maximum}"


def create_boss_hp_bar(current: int, maximum: int, width: int = 40) -> str:
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = max(0, min(width, int((current / maximum) * width)))
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = (current / maximum) * 100
    return f"BOSS HP [{filled}{empty}] {percentage:.1f}% ({current}/{maximum})"


def get_effective_attack(player: Dict[str, Any]) -> int:
    base = player.get('attack', 10)
    buff_bonus = sum(
        b.get('modifiers', {}).get('attack_bonus', 0)
        for b in player.get('active_buffs', []))
    return base + buff_bonus


def get_effective_defense(player: Dict[str, Any]) -> int:
    base = player.get('defense', 8)
    buff_bonus = sum(
        b.get('modifiers', {}).get('defense_bonus', 0)
        for b in player.get('active_buffs', []))
    total = base + buff_bonus
    if player.get('defending'):
        total = int(total * 1.5)
    return total


def get_effective_speed(player: Dict[str, Any]) -> int:
    base = player.get('speed', 10)
    buff_bonus = sum(
        b.get('modifiers', {}).get('speed_bonus', 0)
        for b in player.get('active_buffs', []))
    return base + buff_bonus


def player_take_damage(player: Dict[str, Any], raw_damage: int) -> int:
    """Apply damage to player dict. Returns actual damage taken."""
    defense = get_effective_defense(player)
    damage = max(1, raw_damage - defense)
    remaining = damage
    for b in list(player.get('active_buffs', [])):
        mods = b.get('modifiers', {})
        if remaining <= 0:
            break
        if mods.get('absorb_amount', 0) > 0:
            avail = mods['absorb_amount']
            use = min(avail, remaining)
            remaining -= use
            mods['absorb_amount'] = avail - use
    taken = max(0, remaining)
    player['hp'] = max(0, player.get('hp', 0) - taken)
    return taken


def tick_buffs(player: Dict[str, Any]) -> bool:
    """Tick player buffs. Returns True if any expired."""
    changed = False
    buffs = player.get('active_buffs', [])
    remaining = []
    for buff in buffs:
        buff['duration'] -= 1
        if buff['duration'] > 0:
            remaining.append(buff)
        else:
            changed = True
    player['active_buffs'] = remaining
    return changed


def battle_round_player_attack(player: Dict[str, Any], enemy_dict: Dict[str,
                                                                        Any],
                               items_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the player's attack portion of a battle round.
    Returns a result dict with messages, damage dealt, etc.
    """
    dice = Dice()
    messages = []
    result = {
        "action": "attack",
        "messages": messages,
        "enemy_alive": True,
        "player_alive": True
    }

    atk = get_effective_attack(player)
    roll = dice.roll_1d(20)

    if roll == 1:
        messages.append({
            "text": "Critical miss! Your weapon slips!",
            "color": "var(--red)"
        })
    elif roll == 20:
        messages.append({
            "text": "Critical hit! A perfect strike!",
            "color": "var(--gold)"
        })

    damage = int(atk * roll / 10)
    enemy = Enemy(enemy_dict)
    enemy.hp = enemy_dict.get('hp', enemy.max_hp)
    actual = enemy.take_damage(damage)
    enemy_dict['hp'] = enemy.hp

    messages.append({
        "text": f"You attack for {actual} damage! (Rolled {roll}/20)",
        "color": "var(--green-bright)"
    })
    result["damage_dealt"] = actual
    result["enemy_alive"] = enemy.is_alive()
    result["enemy_hp"] = enemy.hp

    if not enemy.is_alive():
        messages.append({
            "text": f"You defeated {enemy_dict.get('name', 'the enemy')}!",
            "color": "var(--gold)"
        })

    return result


def battle_round_player_defend(player: Dict[str, Any]) -> Dict[str, Any]:
    """Player chooses to defend."""
    player['defending'] = True
    return {
        "action":
        "defend",
        "messages": [{
            "text": "You take a defensive stance, reducing incoming damage!",
            "color": "var(--blue)"
        }],
        "enemy_alive":
        True,
        "player_alive":
        True,
    }


def battle_round_player_flee(player: Dict[str, Any],
                             enemy_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Player attempts to flee."""
    p_speed = get_effective_speed(player)
    e_speed = enemy_dict.get('speed', 5)
    flee_chance = 0.7 if p_speed > e_speed else 0.4
    fled = random.random() < flee_chance
    msg = "You successfully fled the battle!" if fled else "Failed to flee! The enemy blocks your path."
    color = "var(--yellow)" if fled else "var(--red)"
    return {
        "action": "flee",
        "fled": fled,
        "messages": [{
            "text": msg,
            "color": color
        }],
        "enemy_alive": True,
        "player_alive": True,
    }


def battle_round_enemy_attack(player: Dict[str, Any],
                              enemy_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Enemy attacks the player. Modifies player dict in place."""
    dice = Dice()
    messages = []

    e_name = enemy_dict.get('name', 'The enemy')
    e_atk = enemy_dict.get('attack', 5)
    roll = dice.roll_1d(max(1, player.get('level', 1)))
    raw_damage = int(e_atk * roll / 10)

    was_defending = player.get('defending', False)
    if was_defending:
        raw_damage = raw_damage // 2
        player['defending'] = False

    actual = player_take_damage(player, raw_damage)
    messages.append({
        "text": f"{e_name} attacks you for {actual} damage!",
        "color": "var(--red)"
    })

    if was_defending:
        messages.append({
            "text": "Your defensive stance reduced the damage!",
            "color": "var(--blue)"
        })

    player_alive = player.get('hp', 0) > 0
    if not player_alive:
        messages.append({
            "text": "You have been defeated...",
            "color": "var(--red)"
        })

    return {
        "action": "enemy_attack",
        "damage_taken": actual,
        "messages": messages,
        "enemy_alive": True,
        "player_alive": player_alive,
    }


def collect_battle_rewards(player: Dict[str, Any], enemy_dict: Dict[str, Any],
                           items_data: Dict[str, Any]) -> Dict[str, Any]:
    """Collect rewards after defeating an enemy. Modifies player dict in place."""
    messages = []
    e_name = enemy_dict.get('name', 'the enemy')
    exp_reward = enemy_dict.get('experience_reward',
                                enemy_dict.get('exp_reward', 20))
    gold_reward = enemy_dict.get('gold_reward', 10)

    weather = player.get('current_weather', 'sunny')
    if weather == "sunny":
        exp_reward = int(exp_reward * 1.1)
        messages.append({
            "text": "Sunny weather bonus: +10% EXP!",
            "color": "var(--gold)"
        })
    elif weather == "stormy":
        gold_reward = int(gold_reward * 1.2)
        messages.append({
            "text": "Stormy weather bonus: +20% Gold!",
            "color": "var(--blue)"
        })

    old_level = player.get('level', 1)
    player['experience'] = player.get('experience', 0) + exp_reward
    leveled_up = False
    while player['experience'] >= player.get('experience_to_next', 100):
        player['experience'] -= player['experience_to_next']
        player['level'] = player.get('level', 1) + 1
        player['experience_to_next'] = int(
            player.get('experience_to_next', 100) * 1.5)
        bonuses = player.get('level_up_bonuses', {})
        player['max_hp'] = player.get('max_hp', 100) + bonuses.get('hp', 10)
        player['max_mp'] = player.get('max_mp', 50) + bonuses.get('mp', 2)
        player['attack'] = player.get('attack', 10) + bonuses.get('attack', 2)
        player['defense'] = player.get('defense', 8) + bonuses.get(
            'defense', 1)
        player['speed'] = player.get('speed', 10) + bonuses.get('speed', 1)
        player['hp'] = player['max_hp']
        player['mp'] = player['max_mp']
        leveled_up = True

    player['gold'] = player.get('gold', 0) + gold_reward
    messages.append({
        "text":
        f"Defeated {e_name}! Gained {exp_reward} EXP and {gold_reward} gold.",
        "color": "var(--gold)"
    })

    if leveled_up:
        messages.append({
            "text": f"Level up! You are now level {player['level']}!",
            "color": "var(--gold)"
        })

    loot_gained = None
    loot_table = enemy_dict.get('loot_table', enemy_dict.get('drops', []))
    if loot_table and random.random() < 0.5:
        loot = random.choice(loot_table)
        player.setdefault('inventory', []).append(loot)
        loot_gained = loot
        messages.append({
            "text": f"Loot acquired: {loot}!",
            "color": "var(--yellow)"
        })

    return {
        "messages": messages,
        "exp_reward": exp_reward,
        "gold_reward": gold_reward,
        "leveled_up": leveled_up,
        "new_level": player.get('level', 1),
        "loot": loot_gained,
    }


def handle_player_defeat(player: Dict[str, Any]) -> Dict[str, Any]:
    """Handle player being defeated. Modifies player dict and returns to starting village."""
    player['hp'] = player.get('max_hp', 100) // 2
    player['mp'] = player.get('max_mp', 50) // 2
    return {
        "messages": [
            {
                "text": "You were defeated in battle...",
                "color": "var(--red)"
            },
            {
                "text":
                "You wake up at the Starting Village, weakened but alive.",
                "color": "var(--yellow)"
            },
        ],
        "respawn_area":
        "starting_village",
    }


def build_enemy_from_area(
        area_key: str, enemies_data: Dict[str, Any],
        areas_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pick a random enemy from the current area."""
    area = areas_data.get(area_key, {})
    possible = area.get('possible_enemies', [])
    if not possible:
        possible = [k for k in enemies_data.keys()][:5]
    if not possible:
        return None
    enemy_key = random.choice(possible)
    enemy_data = enemies_data.get(enemy_key)
    if not enemy_data:
        return None
    return dict(enemy_data)


def get_spells_for_weapon(
        weapon_name: Optional[str], items_data: Dict[str, Any],
        spells_data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """Return list of (spell_name, spell_data) available for the given weapon."""
    if not weapon_name:
        return []
    weapon = items_data.get(weapon_name, {})
    if not weapon.get('magic_weapon'):
        return []
    return [(sname, sdata) for sname, sdata in spells_data.items()
            if weapon_name in sdata.get('allowed_weapons', [])]
