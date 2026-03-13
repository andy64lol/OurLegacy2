"""
Attribute System for Our Legacy 2

STR, DEX, INT, CHA, WIS, CON — the six core attributes.
Players start with 5 in each attribute.
Each level grants 3 points to spend.

Attribute effects:
  STR (Strength)      — +2 ATK per point above base
  DEX (Dexterity)     — +1 SPD, +1% dodge per point above base
  INT (Intelligence)  — +3 max MP, +2 spell power per point above base
  CHA (Charisma)      — +1% shop discount per point above base
  WIS (Wisdom)        — +2 max MP, +2% item discovery per point above base
  CON (Constitution)  — +5 max HP, +1 DEF per point above base
"""
from typing import Dict, Any

ATTRIBUTE_NAMES: Dict[str, str] = {
    'str': 'Strength',
    'dex': 'Dexterity',
    'int': 'Intelligence',
    'cha': 'Charisma',
    'wis': 'Wisdom',
    'con': 'Constitution',
}

ATTRIBUTE_DESCRIPTIONS: Dict[str, str] = {
    'str': '+2 ATK per point',
    'dex': '+1 SPD, +1% dodge per point',
    'int': '+3 MP, +2 spell power per point',
    'cha': '+1% shop discount per point',
    'wis': '+2 MP, +2% item discovery per point',
    'con': '+5 HP, +1 DEF per point',
}

BASE_ATTRIBUTE: int = 5
POINTS_PER_LEVEL: int = 3


def get_default_attributes() -> Dict[str, int]:
    return {attr: BASE_ATTRIBUTE for attr in ATTRIBUTE_NAMES}


def ensure_attributes(player: Dict[str, Any]) -> None:
    if 'attributes' not in player:
        player['attributes'] = get_default_attributes()
    else:
        for attr in ATTRIBUTE_NAMES:
            if attr not in player['attributes']:
                player['attributes'][attr] = BASE_ATTRIBUTE


def get_unspent_points(player: Dict[str, Any]) -> int:
    ensure_attributes(player)
    level = player.get('level', 1)
    attrs = player['attributes']
    total_spent = sum(
        attrs.get(a, BASE_ATTRIBUTE) - BASE_ATTRIBUTE
        for a in ATTRIBUTE_NAMES
    )
    total_available = (level - 1) * POINTS_PER_LEVEL
    return max(0, total_available - total_spent)


def spend_attribute_point(player: Dict[str, Any], attr: str) -> Dict[str, Any]:
    if attr not in ATTRIBUTE_NAMES:
        return {'ok': False, 'message': f'Unknown attribute: {attr}'}

    unspent = get_unspent_points(player)
    if unspent <= 0:
        return {'ok': False, 'message': 'No attribute points available.'}

    ensure_attributes(player)
    player['attributes'][attr] = player['attributes'].get(attr, BASE_ATTRIBUTE) + 1
    new_val = player['attributes'][attr]
    delta = new_val - BASE_ATTRIBUTE

    if attr == 'str':
        player['base_attack'] = player.get('base_attack', player.get('attack', 10)) + 2
        player['attack'] = player.get('attack', 10) + 2
    elif attr == 'dex':
        player['base_speed'] = player.get('base_speed', player.get('speed', 10)) + 1
        player['speed'] = player.get('speed', 10) + 1
    elif attr == 'con':
        player['base_defense'] = player.get('base_defense', player.get('defense', 8)) + 1
        player['defense'] = player.get('defense', 8) + 1
        player['max_hp'] = player.get('max_hp', 100) + 5
        player['base_max_hp'] = player.get('base_max_hp', player.get('max_hp', 100))
    elif attr == 'int':
        player['max_mp'] = player.get('max_mp', 50) + 3
        player['base_max_mp'] = player.get('base_max_mp', player.get('max_mp', 50))
        player['attr_spell_power'] = player.get('attr_spell_power', 0) + 2
    elif attr == 'wis':
        player['max_mp'] = player.get('max_mp', 50) + 2
        player['base_max_mp'] = player.get('base_max_mp', player.get('max_mp', 50))
        player['attr_discovery'] = player.get('attr_discovery', 0.0) + 0.02
    elif attr == 'cha':
        player['attr_gold_discount'] = player.get('attr_gold_discount', 0.0) + 0.01

    return {
        'ok': True,
        'message': f'{ATTRIBUTE_NAMES[attr]} increased to {new_val}!'
    }


def get_attribute_summary(player: Dict[str, Any]) -> Dict[str, Any]:
    ensure_attributes(player)
    attrs = player['attributes']
    return {
        'attributes': {
            attr: {
                'name': ATTRIBUTE_NAMES[attr],
                'description': ATTRIBUTE_DESCRIPTIONS[attr],
                'value': attrs.get(attr, BASE_ATTRIBUTE),
            }
            for attr in ATTRIBUTE_NAMES
        },
        'unspent_points': get_unspent_points(player),
    }
