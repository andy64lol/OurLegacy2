"""
Our Legacy 2 - Flask Web Interface
Medieval fantasy RPG playable in the browser.
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
from cryptography.fernet import Fernet
import pickle
import base64
import json
import random
import os

from utilities.UI import Colors, get_rarity_color, create_progress_bar
from utilities.dice import Dice
from utilities.entities import Enemy, Boss
from utilities.character import build_new_character, get_available_classes
from utilities.battle import (
    battle_round_player_attack, battle_round_enemy_attack,
    battle_round_player_flee, battle_round_player_defend,
    collect_battle_rewards, handle_player_defeat, get_spells_for_weapon,
)
from utilities.shop import get_shop_items, buy_item, sell_item
from utilities.spellcasting import get_available_spells, cast_spell, can_cast_spell
from utilities.crafting import get_recipes, craft_item, check_recipe_craftable, get_recipe_categories
from utilities.building import (
    get_building_status, place_housing_item, remove_housing_item_slot,
    plant_crop, harvest_crop,
)
from utilities.dungeons import (
    get_available_dungeons, generate_dungeon_rooms,
    process_chest_room, process_trap_chest_room, process_empty_room, process_battle_room,
    process_question_room, answer_question, answer_multi_choice, complete_dungeon,
    _pick_multi_choice,
)
from utilities.market import get_market_api
from utilities.save_load import save_game, list_saves, load_save

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def load_json(filename):
    try:
        with open(os.path.join(DATA_DIR, filename), 'r') as f:
            return json.load(f)
    except Exception:
        return {}


GAME_DATA = {
    'classes': load_json('classes.json'),
    'areas': load_json('areas.json'),
    'enemies': load_json('enemies.json'),
    'items': load_json('items.json'),
    'missions': load_json('missions.json'),
    'bosses': load_json('bosses.json'),
    'spells': load_json('spells.json'),
    'shops': load_json('shops.json'),
    'companions': load_json('companions.json'),
    'crafting': load_json('crafting.json'),
    'housing': load_json('housing.json'),
    'farming': load_json('farming.json'),
    'pets': load_json('pets.json'),
    'dungeons': load_json('dungeons.json'),
}

BUILDING_TYPES = {
    'house': {'label': 'House', 'slots': 3},
    'decoration': {'label': 'Decoration', 'slots': 10},
    'fencing': {'label': 'Fencing', 'slots': 1},
    'garden': {'label': 'Garden', 'slots': 3},
    'farm': {'label': 'Farm', 'slots': 2},
    'training_place': {'label': 'Training Place', 'slots': 3},
}

EQUIPPABLE_TYPES = {'weapon', 'armor', 'offhand', 'accessory'}


# ─── Helpers ────────────────────────────────────────────────────────────────


def get_player():
    return session.get('player')


def save_player(player):
    session['player'] = player
    session.modified = True


def get_messages():
    return session.get('messages', [])


def add_message(text, color='var(--text-light)'):
    msgs = session.get('messages', [])
    msgs.append({'text': text, 'color': color})
    if len(msgs) > 80:
        msgs = msgs[-80:]
    session['messages'] = msgs
    session.modified = True


def get_rank(level):
    if level < 5:
        return 'F-Tier Adventurer'
    elif level < 10:
        return 'E-Tier Adventurer'
    elif level < 15:
        return 'D-Tier Adventurer'
    elif level < 20:
        return 'C-Tier Adventurer'
    elif level < 30:
        return 'B-Tier Adventurer'
    elif level < 40:
        return 'A-Tier Adventurer'
    elif level < 50:
        return 'S-Tier Adventurer'
    else:
        return 'Legendary Hero'


def gain_experience(player, amount):
    player['experience'] += amount
    leveled = False
    while player['experience'] >= player['experience_to_next']:
        player['experience'] -= player['experience_to_next']
        player['level'] += 1
        player['experience_to_next'] = int(player['experience_to_next'] * 1.5)
        b = player.get('level_up_bonuses', {})
        player['max_hp'] += b.get('hp', 10)
        player['max_mp'] += b.get('mp', 2)
        player['attack'] += b.get('attack', 2)
        player['defense'] += b.get('defense', 1)
        player['speed'] += b.get('speed', 1)
        player['hp'] = player['max_hp']
        player['mp'] = player['max_mp']
        player['rank'] = get_rank(player['level'])
        leveled = True
    return leveled


def advance_crops(player):
    crops = player.get('crops', {})
    for slot_id, crop_info in crops.items():
        if not crop_info.get('ready', False):
            crop_info['turns'] = crop_info.get('turns', 0) + 1
            growth_time = crop_info.get('growth_time', 5)
            if crop_info['turns'] >= growth_time:
                crop_info['ready'] = True


# ─── Equipment Helpers ───────────────────────────────────────────────────────

STAT_BONUSES = [
    ('attack_bonus', 'attack', 1),
    ('defense_bonus', 'defense', 1),
    ('speed_bonus', 'speed', 1),
    ('hp_bonus', 'max_hp', 1),
    ('mp_bonus', 'max_mp', 1),
    ('defense_penalty', 'defense', -1),
    ('speed_penalty', 'speed', -1),
]


def apply_item_bonuses(player, item_data, direction=1):
    """Apply (direction=1) or remove (direction=-1) item stat bonuses."""
    for bonus_key, stat_key, sign in STAT_BONUSES:
        val = item_data.get(bonus_key, 0)
        if val:
            player[stat_key] = max(1, player.get(stat_key, 0) + int(val) * sign * direction)
    # hp_bonus also raises current hp when equipping
    hp_bonus = item_data.get('hp_bonus', 0)
    if hp_bonus and direction == 1:
        player['hp'] = min(player['hp'] + hp_bonus, player['max_hp'])
    mp_bonus = item_data.get('mp_bonus', 0)
    if mp_bonus and direction == 1:
        player['mp'] = min(player['mp'] + mp_bonus, player['max_mp'])


def equip_item(player, item_name):
    """Equip item from inventory. Returns (success, message)."""
    if item_name not in player.get('inventory', []):
        return False, f"You don't have {item_name}."

    item_data = GAME_DATA['items'].get(item_name, {})
    if not isinstance(item_data, dict):
        return False, f"{item_name} cannot be equipped."

    item_type = item_data.get('type', '')
    if item_type not in EQUIPPABLE_TYPES:
        return False, f"{item_name} is not equippable (type: {item_type})."

    req = item_data.get('requirements', {})
    if req.get('level', 1) > player.get('level', 1):
        return False, f"Requires level {req['level']} to equip."
    if req.get('class') and req['class'] != player.get('class', ''):
        return False, f"Only {req['class']} can equip {item_name}."

    equipment = player.setdefault('equipment', {})
    slot = item_type  # weapon/armor/offhand/accessory

    # Unequip current item in slot
    current = equipment.get(slot)
    if current:
        cur_data = GAME_DATA['items'].get(current, {})
        if isinstance(cur_data, dict):
            apply_item_bonuses(player, cur_data, direction=-1)
        player['inventory'].append(current)

    # Equip new item
    equipment[slot] = item_name
    player['inventory'].remove(item_name)
    apply_item_bonuses(player, item_data, direction=1)

    bonuses = []
    for bonus_key, stat_key, sign in STAT_BONUSES:
        val = item_data.get(bonus_key, 0)
        if val:
            label = stat_key.replace('max_', '').upper()
            bonuses.append(f'+{int(val) * sign} {label}')
    bonus_str = ', '.join(bonuses) if bonuses else ''
    msg = f'You equip {item_name}.'
    if bonus_str:
        msg += f' ({bonus_str})'
    return True, msg


def unequip_item(player, slot):
    """Unequip item from slot. Returns (success, message)."""
    equipment = player.get('equipment', {})
    item_name = equipment.get(slot)
    if not item_name:
        return False, f'Nothing equipped in {slot} slot.'

    item_data = GAME_DATA['items'].get(item_name, {})
    if isinstance(item_data, dict):
        apply_item_bonuses(player, item_data, direction=-1)

    equipment[slot] = None
    player['inventory'].append(item_name)
    return True, f'You unequip {item_name}.'


# ─── Quest Helpers ───────────────────────────────────────────────────────────


def get_quest_progress(mission_id):
    return session.get('quest_progress', {}).get(mission_id, {})


def update_quest_kills(enemy_key, enemy_name):
    """Update kill counts for all active kill quests matching this enemy."""
    completed = set(session.get('completed_missions', []))
    missions = GAME_DATA['missions']
    quest_progress = session.get('quest_progress', {})
    changed = False

    for mid, mission in missions.items():
        if mid in completed:
            continue
        if mission.get('type') != 'kill':
            continue

        target = mission.get('target', '')
        target_count = mission.get('target_count', 1)

        targets_to_check = []
        if isinstance(target_count, dict):
            targets_to_check = list(target_count.keys())
        else:
            targets_to_check = [target]

        for t in targets_to_check:
            t_lower = t.lower().replace(' ', '_')
            e_lower = enemy_key.lower().replace(' ', '_')
            e_name_lower = enemy_name.lower().replace(' ', '_')
            if t_lower == e_lower or t_lower in e_lower or e_lower in t_lower or t_lower == e_name_lower:
                if mid not in quest_progress:
                    quest_progress[mid] = {'kills': {}}
                if 'kills' not in quest_progress[mid]:
                    quest_progress[mid]['kills'] = {}
                quest_progress[mid]['kills'][t] = quest_progress[mid]['kills'].get(t, 0) + 1
                changed = True

    if changed:
        session['quest_progress'] = quest_progress
        session.modified = True


def check_mission_completable(mission_id, player):
    """Check if a mission can be completed right now."""
    mission = GAME_DATA['missions'].get(mission_id, {})
    if not mission:
        return False, 'Mission not found.'

    completed = set(session.get('completed_missions', []))
    if mission_id in completed:
        return False, 'Already completed.'

    # Level requirement
    unlock_level = mission.get('unlock_level', 1)
    if player.get('level', 1) < unlock_level:
        return False, f'Requires level {unlock_level}.'

    # Prerequisites
    prereqs = mission.get('prerequisites', [])
    for prereq in prereqs:
        if prereq not in completed:
            prereq_name = GAME_DATA['missions'].get(prereq, {}).get('name', prereq)
            return False, f'Requires: {prereq_name}'

    mission_type = mission.get('type', '')
    target_count = mission.get('target_count', 1)
    target = mission.get('target', '')

    progress = session.get('quest_progress', {}).get(mission_id, {})

    if mission_type == 'kill':
        if isinstance(target_count, dict):
            for t, needed in target_count.items():
                have = progress.get('kills', {}).get(t, 0)
                if have < needed:
                    return False, f'Kill more {t.replace("_", " ").title()} ({have}/{needed})'
        else:
            have = progress.get('kills', {}).get(target, 0)
            if have < target_count:
                return False, f'Kill {target.replace("_", " ").title()} ({have}/{target_count})'

    elif mission_type == 'collect':
        if isinstance(target_count, dict):
            inv_counts = {}
            for item in player.get('inventory', []):
                inv_counts[item] = inv_counts.get(item, 0) + 1
            for item_name, needed in target_count.items():
                have = inv_counts.get(item_name, 0)
                if have < needed:
                    return False, f'Need {needed}x {item_name} in inventory ({have}/{needed})'
        else:
            inv_counts = {}
            for item in player.get('inventory', []):
                inv_counts[item] = inv_counts.get(item, 0) + 1
            have = inv_counts.get(target, 0)
            if have < target_count:
                return False, f'Need {target} in inventory ({have}/{target_count})'

    return True, 'Ready'


def get_mission_progress_display(mission_id, player):
    """Return display info about mission progress."""
    mission = GAME_DATA['missions'].get(mission_id, {})
    if not mission:
        return []

    mission_type = mission.get('type', '')
    target_count = mission.get('target_count', 1)
    target = mission.get('target', '')
    progress = session.get('quest_progress', {}).get(mission_id, {})
    items_display = []

    if mission_type == 'kill':
        if isinstance(target_count, dict):
            for t, needed in target_count.items():
                have = progress.get('kills', {}).get(t, 0)
                items_display.append({'label': t.replace('_', ' ').title(), 'have': have, 'need': needed})
        else:
            have = progress.get('kills', {}).get(target, 0)
            items_display.append({'label': target.replace('_', ' ').title(), 'have': have, 'need': target_count})

    elif mission_type == 'collect':
        inv_counts = {}
        for item in player.get('inventory', []):
            inv_counts[item] = inv_counts.get(item, 0) + 1
        if isinstance(target_count, dict):
            for item_name, needed in target_count.items():
                have = inv_counts.get(item_name, 0)
                items_display.append({'label': item_name, 'have': have, 'need': needed})
        else:
            have = inv_counts.get(target, 0)
            items_display.append({'label': target, 'have': have, 'need': target_count})

    return items_display


# ─── Routes ─────────────────────────────────────────────────────────────────


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        cls = request.form.get('class', 'Warrior')
        if not name:
            return render_template('create.html', data=GAME_DATA, error='Please enter a character name.')

        cls_data = GAME_DATA['classes'].get(cls, {})
        stats = cls_data.get('base_stats', {
            'hp': 100, 'mp': 50, 'attack': 10, 'defense': 8, 'speed': 10
        })

        player = {
            'name': name,
            'class': cls,
            'level': 1,
            'experience': 0,
            'experience_to_next': 100,
            'hp': stats['hp'],
            'max_hp': stats['hp'],
            'mp': stats['mp'],
            'max_mp': stats['mp'],
            'attack': stats['attack'],
            'defense': stats['defense'],
            'speed': stats['speed'],
            'gold': cls_data.get('starting_gold', 100),
            'inventory': list(cls_data.get('starting_items', ['Health Potion'])),
            'equipment': {'weapon': None, 'armor': None, 'offhand': None, 'accessory': None},
            'companions': [],
            'rank': 'F-Tier Adventurer',
            'level_up_bonuses': cls_data.get('level_up_bonuses', {
                'hp': 10, 'mp': 2, 'attack': 2, 'defense': 1, 'speed': 1
            }),
            'comfort_points': 0,
            'housing_owned': [],
            'building_slots': {},
            'crops': {},
            'pet': None,
            'explore_count': 0,
        }
        save_player(player)
        session['messages'] = []
        session['current_area'] = 'starting_village'
        session['completed_missions'] = []
        session['visited_areas'] = ['starting_village']
        session['quest_progress'] = {}
        add_message(f'Welcome, {name} the {cls}! Your legend begins.', 'var(--gold)')
        add_message('You stand at the gates of the Starting Village. Adventure awaits.', 'var(--text-light)')
        return redirect(url_for('game'))

    return render_template('create.html', data=GAME_DATA)


@app.route('/game')
def game():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    # Ensure equipment has all slots
    if 'equipment' not in player:
        player['equipment'] = {}
    for slot in ('weapon', 'armor', 'offhand', 'accessory'):
        player['equipment'].setdefault(slot, None)

    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})
    area_name = area.get('name', area_key.replace('_', ' ').title())

    connections = []
    for conn_key in area.get('connections', []):
        conn_area = GAME_DATA['areas'].get(conn_key, {})
        connections.append({
            'key': conn_key,
            'name': conn_area.get('name', conn_key.replace('_', ' ').title()),
            'has_danger': bool(conn_area.get('possible_enemies')),
            'visited': conn_key in session.get('visited_areas', []),
        })

    # Shop items
    shop_items = []
    shop_name = ''
    for shop_key in area.get('shops', []):
        if shop_key == 'pet_shop':
            continue
        shop_data = GAME_DATA['shops'].get(shop_key, {})
        shop_name = shop_data.get('name', 'Shop')
        for item_name in shop_data.get('items', []):
            item_data = GAME_DATA['items'].get(item_name, {})
            if not isinstance(item_data, dict):
                continue
            price = item_data.get('price', item_data.get('value', 20))
            shop_items.append({
                'name': item_name,
                'price': price,
                'rarity': item_data.get('rarity', 'common'),
                'description': item_data.get('description', ''),
                'type': item_data.get('type', 'misc'),
                'stats': _item_stat_summary(item_data),
                'can_afford': player['gold'] >= price,
            })

    # Inventory
    inventory_items = []
    counts = {}
    for item_name in player.get('inventory', []):
        counts[item_name] = counts.get(item_name, 0) + 1
    for item_name, count in counts.items():
        item_data = GAME_DATA['items'].get(item_name, {})
        if not isinstance(item_data, dict):
            item_data = {}
        sell_price = max(1, int(item_data.get('price', item_data.get('value', 10)) * 0.5))
        item_type = item_data.get('type', '')
        inventory_items.append({
            'name': item_name,
            'count': count,
            'rarity': item_data.get('rarity', 'common'),
            'description': item_data.get('description', ''),
            'sell_price': sell_price,
            'type': item_type,
            'equippable': item_type in EQUIPPABLE_TYPES,
            'stats': _item_stat_summary(item_data),
        })

    # Equipment info
    equipped_details = {}
    for slot, item_name in player.get('equipment', {}).items():
        if item_name:
            item_data = GAME_DATA['items'].get(item_name, {})
            if isinstance(item_data, dict):
                equipped_details[slot] = {
                    'name': item_name,
                    'rarity': item_data.get('rarity', 'common'),
                    'description': item_data.get('description', ''),
                    'stats': _item_stat_summary(item_data),
                }

    # Missions — filter by level and prerequisites, compute progress
    completed = session.get('completed_missions', [])
    completed_set = set(completed)
    available_missions = []
    for mid, mission in GAME_DATA['missions'].items():
        if mid in completed_set:
            continue
        unlock_level = mission.get('unlock_level', 1)
        prereqs = mission.get('prerequisites', [])
        prereqs_met = all(p in completed_set for p in prereqs)
        level_ok = player.get('level', 1) >= unlock_level

        progress_items = get_mission_progress_display(mid, player)
        can_complete, status_msg = check_mission_completable(mid, player)

        reward = mission.get('reward', {})
        exp_reward = reward.get('experience', mission.get('experience_reward', 0))
        gold_reward = reward.get('gold', mission.get('gold_reward', 0))
        item_rewards = reward.get('items', [])

        available_missions.append({
            'id': mid,
            'name': mission.get('name', mid),
            'description': mission.get('description', ''),
            'type': mission.get('type', 'kill'),
            'exp_reward': exp_reward,
            'gold_reward': gold_reward,
            'item_rewards': item_rewards,
            'unlock_level': unlock_level,
            'prereqs_met': prereqs_met,
            'level_ok': level_ok,
            'eligible': level_ok and prereqs_met,
            'can_complete': can_complete,
            'status_msg': status_msg,
            'progress': progress_items,
            'area': mission.get('area', 'any'),
        })

    available_missions.sort(key=lambda m: (not m['eligible'], m['unlock_level']))

    # Your Land data
    land_data = None
    if area_key == 'your_land':
        housing_data = GAME_DATA['housing']
        farming_data = GAME_DATA['farming'].get('crops', {})
        pets_data = GAME_DATA['pets']
        owned_set = set(player.get('housing_owned', []))
        building_slots = player.get('building_slots', {})
        crops = player.get('crops', {})

        housing_by_type = {}
        for h_key, h_item in housing_data.items():
            h_type = h_item.get('type', 'decoration')
            if h_type not in housing_by_type:
                housing_by_type[h_type] = []
            housing_by_type[h_type].append({
                'key': h_key,
                'name': h_item.get('name', h_key),
                'description': h_item.get('description', ''),
                'price': h_item.get('price', 100),
                'comfort': h_item.get('comfort_points', 5),
                'rarity': h_item.get('rarity', 'common'),
                'owned': h_key in owned_set,
                'can_afford': player['gold'] >= h_item.get('price', 100),
            })

        placed_by_type = {}
        for slot_id, h_key in building_slots.items():
            if h_key:
                slot_type = slot_id.rsplit('_', 1)[0]
                h_item = housing_data.get(h_key, {})
                if slot_type not in placed_by_type:
                    placed_by_type[slot_type] = []
                placed_by_type[slot_type].append({
                    'slot_id': slot_id,
                    'key': h_key,
                    'name': h_item.get('name', h_key),
                    'comfort': h_item.get('comfort_points', 0),
                })

        farm_crops = []
        for i in range(1, 5):
            slot_id = f'farm_{i}'
            crop_info = crops.get(slot_id)
            if crop_info:
                crop_def = farming_data.get(crop_info['crop_key'], {})
                farm_crops.append({
                    'slot_id': slot_id,
                    'crop_key': crop_info['crop_key'],
                    'name': crop_def.get('name', crop_info['crop_key']),
                    'ready': crop_info.get('ready', False),
                    'turns': crop_info.get('turns', 0),
                    'growth_time': crop_info.get('growth_time', 5),
                    'sell_price': crop_def.get('sell_price', 15),
                    'harvest_amount': crop_def.get('harvest_amount', 3),
                })
            else:
                farm_crops.append({'slot_id': slot_id, 'crop_key': None})

        pet_data_current = None
        if player.get('pet'):
            pd = pets_data.get(player['pet'], {})
            pet_data_current = {'key': player['pet'], 'name': pd.get('name', player['pet']), 'boosts': pd.get('boosts', {})}

        land_data = {
            'housing_by_type': housing_by_type,
            'placed_by_type': placed_by_type,
            'comfort_points': player.get('comfort_points', 0),
            'building_slots': building_slots,
            'building_types': BUILDING_TYPES,
            'farm_crops': farm_crops,
            'farming_crops': farming_data,
            'pets': {
                k: {
                    'key': k,
                    'name': v.get('name', k),
                    'description': v.get('description', ''),
                    'price': v.get('price', 500),
                    'boosts': v.get('boosts', {}),
                    'can_afford': player['gold'] >= v.get('price', 500)
                }
                for k, v in pets_data.items()
            },
            'current_pet': pet_data_current,
            'owned_housing': owned_set,
        }

    save_player(player)
    return render_template(
        'game.html',
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
        land_data=land_data,
    )


def _item_stat_summary(item_data):
    if not isinstance(item_data, dict):
        return ''
    parts = []
    for bonus_key, label in [
        ('attack_bonus', 'ATK'), ('defense_bonus', 'DEF'), ('speed_bonus', 'SPD'),
        ('hp_bonus', 'HP'), ('mp_bonus', 'MP'), ('defense_penalty', '-DEF'), ('speed_penalty', '-SPD'),
    ]:
        val = item_data.get(bonus_key)
        if val:
            sign = '+' if 'penalty' not in bonus_key else '-'
            parts.append(f'{sign}{abs(int(val))} {label}')
    return ', '.join(parts)


# ─── Exploration ─────────────────────────────────────────────────────────────


@app.route('/action/explore', methods=['POST'])
def action_explore():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})
    possible_enemies = area.get('possible_enemies', [])

    player['explore_count'] = player.get('explore_count', 0) + 1
    advance_crops(player)

    roll = random.random()
    if possible_enemies and roll < 0.55:
        enemy_key = random.choice(possible_enemies)
        enemy_data = GAME_DATA['enemies'].get(enemy_key, {})
        if not isinstance(enemy_data, dict):
            enemy_data = {}
        lvl = player['level']
        scale = 1 + (lvl - 1) * 0.12
        enemy = {
            'key': enemy_key,
            'name': enemy_data.get('name', enemy_key.replace('_', ' ').title()),
            'hp': int(enemy_data.get('hp', 50) * scale),
            'max_hp': int(enemy_data.get('hp', 50) * scale),
            'attack': int(enemy_data.get('attack', 10) * scale),
            'defense': int(enemy_data.get('defense', 5) * scale),
            'speed': enemy_data.get('speed', 10),
            'exp_reward': int(enemy_data.get('experience_reward', 30) * scale),
            'gold_reward': max(1, int(enemy_data.get('gold_reward', 10)) + random.randint(-3, 10)),
            'loot_table': enemy_data.get('loot_table', []),
        }
        session['battle_enemy'] = enemy
        session['battle_log'] = [f'A {enemy["name"]} emerges from the shadows! (HP: {enemy["hp"]})']
        session.modified = True
        save_player(player)
        return redirect(url_for('battle'))
    elif roll < 0.70:
        gold_found = random.randint(5, 25)
        player['gold'] += gold_found
        add_message(f'You search the area and find {gold_found} gold coins.', 'var(--gold)')
    elif roll < 0.82:
        heal = random.randint(10, 30)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        add_message(f'You discover an herb and recover {heal} HP.', 'var(--green-bright)')
    elif roll < 0.90:
        player['inventory'].append('Health Potion')
        add_message('You find a discarded Health Potion on the ground.', 'var(--text-light)')
    else:
        add_message('You explore thoroughly but find nothing of note.', 'var(--text-dim)')

    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/rest', methods=['POST'])
def action_rest():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})

    if not area.get('can_rest', False):
        add_message('There is nowhere suitable to rest here.', 'var(--red)')
        return redirect(url_for('game'))

    cost = area.get('rest_cost', 10)
    if cost > 0 and player['gold'] < cost:
        add_message(f'You need {cost} gold coins to rest here.', 'var(--red)')
        return redirect(url_for('game'))

    player['gold'] = player['gold'] - cost
    player['hp'] = player['max_hp']
    player['mp'] = player['max_mp']
    advance_crops(player)

    if cost > 0:
        add_message(f'You rest for {cost} gold. HP and MP fully restored.', 'var(--green-bright)')
    else:
        add_message('You rest peacefully on your land. HP and MP restored.', 'var(--green-bright)')

    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/travel', methods=['POST'])
def action_travel():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    dest_key = request.form.get('dest', '')
    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})

    if dest_key in area.get('connections', []):
        session['current_area'] = dest_key
        dest_area = GAME_DATA['areas'].get(dest_key, {})
        dest_name = dest_area.get('name', dest_key.replace('_', ' ').title())
        visited = session.get('visited_areas', [])
        if dest_key not in visited:
            visited.append(dest_key)
            session['visited_areas'] = visited
        add_message(f'You travel to {dest_name}.', 'var(--wood-light)')
        session.modified = True
    else:
        add_message('That path is not accessible from here.', 'var(--red)')

    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/buy', methods=['POST'])
def action_buy():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    item_name = request.form.get('item', '')
    item_data = GAME_DATA['items'].get(item_name, {})
    if not isinstance(item_data, dict):
        item_data = {}
    price = item_data.get('price', item_data.get('value', 20))

    if player['gold'] < price:
        add_message(f'You cannot afford {item_name}. Cost: {price} gold.', 'var(--red)')
    else:
        player['gold'] -= price
        player['inventory'].append(item_name)
        add_message(f'You purchase {item_name} for {price} gold.', 'var(--gold)')

    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/sell', methods=['POST'])
def action_sell():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    item_name = request.form.get('item', '')
    if item_name in player['inventory']:
        item_data = GAME_DATA['items'].get(item_name, {})
        if not isinstance(item_data, dict):
            item_data = {}
        sell_price = max(1, int(item_data.get('price', item_data.get('value', 10)) * 0.5))
        player['inventory'].remove(item_name)
        player['gold'] += sell_price
        add_message(f'You sell {item_name} for {sell_price} gold.', 'var(--gold)')
    else:
        add_message('You do not have that item.', 'var(--red)')

    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/use_item', methods=['POST'])
def action_use_item():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    item_name = request.form.get('item', '')
    if item_name not in player['inventory']:
        add_message('You do not have that item.', 'var(--red)')
        return redirect(url_for('game'))

    item_data = GAME_DATA['items'].get(item_name, {})
    if not isinstance(item_data, dict):
        item_data = {}
    item_type = item_data.get('type', '')

    # Equippable items — equip them
    if item_type in EQUIPPABLE_TYPES:
        ok, msg = equip_item(player, item_name)
        color = 'var(--green-bright)' if ok else 'var(--red)'
        add_message(msg, color)
        save_player(player)
        return redirect(url_for('game'))

    lower = item_name.lower()
    if 'health' in lower or ('potion' in lower and 'mana' not in lower):
        heal = random.randint(40, 70)
        if 'large' in lower or 'greater' in lower:
            heal = random.randint(70, 130)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(f'You drink the {item_name} and recover {heal} HP.', 'var(--green-bright)')
    elif 'mana' in lower:
        restore = random.randint(25, 50)
        player['mp'] = min(player['max_mp'], player['mp'] + restore)
        player['inventory'].remove(item_name)
        add_message(f'You drink the {item_name} and restore {restore} MP.', 'var(--mana-bright)')
    elif 'elixir' in lower or 'tears' in lower:
        heal = random.randint(50, 100)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(f'You use the {item_name} and feel its power (+{heal} HP).', 'var(--gold)')
    else:
        add_message(f'You cannot use {item_name} outside of battle.', 'var(--text-dim)')

    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/equip', methods=['POST'])
def action_equip():
    player = get_player()
    if not player:
        return redirect(url_for('index'))
    item_name = request.form.get('item', '')
    ok, msg = equip_item(player, item_name)
    add_message(msg, 'var(--green-bright)' if ok else 'var(--red)')
    save_player(player)
    return redirect(url_for('game'))


@app.route('/action/unequip', methods=['POST'])
def action_unequip():
    player = get_player()
    if not player:
        return redirect(url_for('index'))
    slot = request.form.get('slot', '')
    ok, msg = unequip_item(player, slot)
    add_message(msg, 'var(--text-dim)' if ok else 'var(--red)')
    save_player(player)
    return redirect(url_for('game'))


# ─── Missions ─────────────────────────────────────────────────────────────────


@app.route('/action/complete_mission', methods=['POST'])
def action_complete_mission():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    mission_id = request.form.get('mission_id', '')
    completed = session.get('completed_missions', [])

    if mission_id in completed:
        add_message('That mission is already completed.', 'var(--text-dim)')
        return redirect(url_for('game'))

    can_complete, reason = check_mission_completable(mission_id, player)
    if not can_complete:
        add_message(f'Cannot complete mission: {reason}', 'var(--red)')
        return redirect(url_for('game'))

    mission = GAME_DATA['missions'].get(mission_id, {})
    completed.append(mission_id)
    session['completed_missions'] = completed

    reward = mission.get('reward', {})
    exp = reward.get('experience', mission.get('experience_reward', 0))
    gold = reward.get('gold', mission.get('gold_reward', 0))
    item_rewards = reward.get('items', [])

    player['gold'] += gold
    leveled = gain_experience(player, exp)

    for item in item_rewards:
        player['inventory'].append(item)

    add_message(f'Quest Complete: {mission.get("name", mission_id)}', 'var(--gold)')
    add_message(f'Reward: +{exp} EXP, +{gold} gold.', 'var(--text-light)')
    if item_rewards:
        add_message(f'Items received: {", ".join(item_rewards)}', 'var(--gold-bright)')
    if leveled:
        add_message(f'Level Up! You are now level {player["level"]}!', 'var(--gold)')

    # Remove progress tracking for completed mission
    quest_progress = session.get('quest_progress', {})
    quest_progress.pop(mission_id, None)
    session['quest_progress'] = quest_progress

    save_player(player)
    return redirect(url_for('game'))


# ─── Your Land Routes ────────────────────────────────────────────────────────


@app.route('/action/land/buy_housing', methods=['POST'])
def land_buy_housing():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    h_key = request.form.get('housing_key', '')
    h_data = GAME_DATA['housing'].get(h_key)
    if not h_data:
        add_message('That structure does not exist.', 'var(--red)')
        return redirect(url_for('game'))

    price = h_data.get('price', 100)
    if player['gold'] < price:
        add_message(f'Not enough gold. {h_data["name"]} costs {price} gold.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game'))

    player['gold'] -= price
    owned = player.get('housing_owned', [])
    owned.append(h_key)
    player['housing_owned'] = owned
    add_message(f'You purchase {h_data["name"]} for {price} gold.', 'var(--gold)')
    save_player(player)
    return redirect(url_for('game') + '#land')


@app.route('/action/land/place_housing', methods=['POST'])
def land_place_housing():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    h_key = request.form.get('housing_key', '')
    slot_id = request.form.get('slot_id', '')

    if h_key not in player.get('housing_owned', []):
        add_message('You do not own that structure.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    h_data = GAME_DATA['housing'].get(h_key, {})
    comfort = h_data.get('comfort_points', 0)
    slots = player.get('building_slots', {})

    if slot_id in slots and slots[slot_id]:
        old_h = GAME_DATA['housing'].get(slots[slot_id], {})
        old_cp = old_h.get('comfort_points', 0)
        player['comfort_points'] = max(0, player.get('comfort_points', 0) - old_cp)

    slots[slot_id] = h_key
    player['building_slots'] = slots
    player['comfort_points'] = player.get('comfort_points', 0) + comfort
    add_message(f'You place {h_data.get("name", h_key)} at {slot_id}. +{comfort} comfort', 'var(--green-bright)')
    save_player(player)
    return redirect(url_for('game') + '#land')


@app.route('/action/land/remove_housing', methods=['POST'])
def land_remove_housing():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    slot_id = request.form.get('slot_id', '')
    slots = player.get('building_slots', {})

    if slot_id in slots and slots[slot_id]:
        h_key = slots[slot_id]
        h_data = GAME_DATA['housing'].get(h_key, {})
        cp = h_data.get('comfort_points', 0)
        player['comfort_points'] = max(0, player.get('comfort_points', 0) - cp)
        slots[slot_id] = None
        player['building_slots'] = slots
        add_message(f'Removed {h_data.get("name", h_key)} from {slot_id}.', 'var(--text-dim)')
    else:
        add_message('That slot is already empty.', 'var(--text-dim)')

    save_player(player)
    return redirect(url_for('game') + '#land')


@app.route('/action/land/plant', methods=['POST'])
def land_plant():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    crop_key = request.form.get('crop_key', '')
    slot_id = request.form.get('slot_id', '')
    crops_db = GAME_DATA['farming'].get('crops', {})
    crop_def = crops_db.get(crop_key)

    if not crop_def:
        add_message('Unknown crop.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    crops = player.get('crops', {})
    if crops.get(slot_id, {}).get('crop_key'):
        add_message(f'Slot {slot_id} is already occupied. Harvest or clear it first.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    crops[slot_id] = {
        'crop_key': crop_key,
        'growth_time': crop_def.get('growth_time', 5),
        'turns': 0,
        'ready': False,
    }
    player['crops'] = crops
    add_message(f'You plant {crop_def["name"]} in {slot_id}. Ready in {crop_def["growth_time"]} turns.', 'var(--green-bright)')
    save_player(player)
    return redirect(url_for('game') + '#land')


@app.route('/action/land/harvest', methods=['POST'])
def land_harvest():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    slot_id = request.form.get('slot_id', '')
    crops = player.get('crops', {})
    crop_info = crops.get(slot_id)

    if not crop_info or not crop_info.get('crop_key'):
        add_message('Nothing planted in that slot.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    if not crop_info.get('ready', False):
        turns_left = crop_info.get('growth_time', 5) - crop_info.get('turns', 0)
        add_message(f'Crop is not ready yet. About {turns_left} turns remaining.', 'var(--text-dim)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    crops_db = GAME_DATA['farming'].get('crops', {})
    crop_def = crops_db.get(crop_info['crop_key'], {})
    amount = crop_def.get('harvest_amount', 3)
    sell_each = crop_def.get('sell_price', 15)
    gold_earned = amount * sell_each

    player['gold'] += gold_earned
    crops[slot_id] = {}
    player['crops'] = crops
    add_message(f'You harvest {amount}x {crop_def.get("name", crop_info["crop_key"])} and earn {gold_earned} gold!', 'var(--gold)')
    save_player(player)
    return redirect(url_for('game') + '#land')


@app.route('/action/land/buy_pet', methods=['POST'])
def land_buy_pet():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    pet_key = request.form.get('pet_key', '')
    pet_data = GAME_DATA['pets'].get(pet_key)

    if not pet_data:
        add_message('Unknown pet.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    price = pet_data.get('price', 500)
    if player['gold'] < price:
        add_message(f'Not enough gold. {pet_data["name"]} costs {price} gold.', 'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    if player.get('pet'):
        old_pet = GAME_DATA['pets'].get(player['pet'], {})
        old_price = old_pet.get('price', 500)
        refund = old_price // 2
        player['gold'] += refund
        add_message(f'Your old companion ({old_pet.get("name", player["pet"])}) is released. Refund: {refund} gold.', 'var(--text-dim)')
        for stat, val in old_pet.get('boosts', {}).items():
            if stat in ('attack', 'defense', 'speed'):
                player[stat] = max(1, player.get(stat, 0) - val)
            elif stat in ('hp', 'max_hp'):
                player['max_hp'] = max(1, player.get('max_hp', 0) - val)
            elif stat in ('mp', 'max_mp'):
                player['max_mp'] = max(1, player.get('max_mp', 0) - val)

    player['gold'] -= price
    player['pet'] = pet_key
    boosts = pet_data.get('boosts', {})
    for stat, val in boosts.items():
        if stat in ('attack', 'defense', 'speed'):
            player[stat] = player.get(stat, 0) + val
        elif stat in ('hp', 'max_hp'):
            player['max_hp'] = player.get('max_hp', 0) + val
            player['hp'] = min(player['hp'] + val, player['max_hp'])
        elif stat in ('mp', 'max_mp'):
            player['max_mp'] = player.get('max_mp', 0) + val
            player['mp'] = min(player['mp'] + val, player['max_mp'])

    add_message(f'You adopt {pet_data["name"]} as your companion!', 'var(--gold)')
    if boosts:
        boost_str = ', '.join(f'+{v} {k}' for k, v in boosts.items() if isinstance(v, int))
        if boost_str:
            add_message(f'Pet bonus: {boost_str}', 'var(--green-bright)')

    save_player(player)
    return redirect(url_for('game') + '#land')


# ─── Battle Routes ────────────────────────────────────────────────────────────


@app.route('/battle')
def battle():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    battle_log = session.get('battle_log', [])
    usable_items = [
        i for i in player.get('inventory', [])
        if any(x in i.lower() for x in ['potion', 'elixir', 'tears', 'tonic'])
    ]
    weapon = player.get('equipment', {}).get('weapon')
    available_spells = get_available_spells(weapon, GAME_DATA['items'], GAME_DATA['spells'])

    return render_template(
        'battle.html',
        player=player,
        enemy=enemy,
        battle_log=battle_log[-14:],
        usable_items=usable_items,
        available_spells=available_spells,
    )


@app.route('/battle/spell', methods=['POST'])
def battle_spell():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    spell_name = request.form.get('spell', '')
    spells_data = GAME_DATA['spells']
    items_data = GAME_DATA['items']
    weapon = player.get('equipment', {}).get('weapon')
    available_spells = get_available_spells(weapon, items_data, spells_data)
    available_names = [s['name'] for s in available_spells]
    log = session.get('battle_log', [])

    if spell_name not in available_names:
        log.append('That spell is unavailable with your current weapon.')
        session['battle_log'] = log
        return redirect(url_for('battle'))

    spell_data = spells_data.get(spell_name, {})
    effects_data = spell_data.get('effects_data', {})
    result = cast_spell(player, enemy, spell_name, spell_data, effects_data)

    for msg in result.get('messages', []):
        log.append(msg['text'])

    if not result.get('ok', True):
        session['battle_log'] = log
        save_player(player)
        return redirect(url_for('battle'))

    session['battle_enemy'] = enemy

    if enemy.get('hp', 1) <= 0:
        return _handle_victory(player, enemy, log)

    e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(-2, 4))
    player['hp'] = max(0, player['hp'] - e_dmg)
    log.append(f'The {enemy["name"]} strikes back for {e_dmg} damage!')

    if player['hp'] <= 0:
        return _handle_defeat(player, enemy, log)

    session['battle_log'] = log
    session['battle_enemy'] = enemy
    save_player(player)
    return redirect(url_for('battle'))


@app.route('/battle/attack', methods=['POST'])
def battle_attack():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    log = session.get('battle_log', [])

    p_dmg = max(1, player['attack'] - enemy['defense'] + random.randint(-3, 6))
    crit = random.random() < 0.10
    if crit:
        p_dmg = int(p_dmg * 1.6)
        log.append(f'CRITICAL STRIKE! You deal {p_dmg} damage to the {enemy["name"]}!')
    else:
        log.append(f'You attack the {enemy["name"]} for {p_dmg} damage.')
    enemy['hp'] = max(0, enemy['hp'] - p_dmg)

    if enemy['hp'] <= 0:
        return _handle_victory(player, enemy, log)

    e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(-2, 4))
    player['hp'] = max(0, player['hp'] - e_dmg)
    log.append(f'The {enemy["name"]} strikes you for {e_dmg} damage.')

    if player['hp'] <= 0:
        return _handle_defeat(player, enemy, log)

    session['battle_enemy'] = enemy
    session['battle_log'] = log
    save_player(player)
    return redirect(url_for('battle'))


@app.route('/battle/defend', methods=['POST'])
def battle_defend():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    log = session.get('battle_log', [])
    log.append('You brace yourself, raising your guard.')
    e_dmg = max(0, enemy['attack'] - int(player['defense'] * 2) + random.randint(-2, 2))
    player['hp'] = max(0, player['hp'] - e_dmg)

    if e_dmg > 0:
        log.append(f'The {enemy["name"]} attacks, but you reduce the blow to {e_dmg} damage.')
    else:
        log.append(f'You block the {enemy["name"]}\'s attack completely!')

    if player['hp'] <= 0:
        return _handle_defeat(player, enemy, log)

    session['battle_enemy'] = enemy
    session['battle_log'] = log
    save_player(player)
    return redirect(url_for('battle'))


@app.route('/battle/use_item', methods=['POST'])
def battle_use_item():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    log = session.get('battle_log', [])
    item_name = request.form.get('item', '')

    if item_name not in player['inventory']:
        log.append('You reach for the item but it is not there.')
    else:
        lower = item_name.lower()
        if 'health' in lower or ('potion' in lower and 'mana' not in lower):
            heal = random.randint(40, 70)
            if 'large' in lower or 'greater' in lower:
                heal = random.randint(70, 130)
            player['hp'] = min(player['max_hp'], player['hp'] + heal)
            player['inventory'].remove(item_name)
            log.append(f'You quaff the {item_name}, recovering {heal} HP.')
        elif 'mana' in lower:
            restore = random.randint(25, 50)
            player['mp'] = min(player['max_mp'], player['mp'] + restore)
            player['inventory'].remove(item_name)
            log.append(f'You drink the {item_name}, restoring {restore} MP.')
        else:
            heal = random.randint(50, 100)
            player['hp'] = min(player['max_hp'], player['hp'] + heal)
            player['inventory'].remove(item_name)
            log.append(f'You use the {item_name}, regaining {heal} HP.')

        e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(-1, 3))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(f'The {enemy["name"]} seizes the moment and strikes for {e_dmg} damage.')

    if player['hp'] <= 0:
        return _handle_defeat(player, enemy, log)

    session['battle_enemy'] = enemy
    session['battle_log'] = log
    save_player(player)
    return redirect(url_for('battle'))


@app.route('/battle/flee', methods=['POST'])
def battle_flee():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    log = session.get('battle_log', [])

    if random.random() < 0.55:
        log.append('You break away from combat and escape!')
        add_message(f'You fled from the {enemy["name"]}.', 'var(--wood-light)')
        session.pop('battle_enemy', None)
        session['battle_log'] = []
        save_player(player)
        return redirect(url_for('game'))
    else:
        e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(0, 5))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(f'You try to flee but the {enemy["name"]} cuts you off, dealing {e_dmg} damage!')

    if player['hp'] <= 0:
        return _handle_defeat(player, enemy, log)

    session['battle_enemy'] = enemy
    session['battle_log'] = log
    save_player(player)
    return redirect(url_for('battle'))


def _handle_victory(player, enemy, log):
    log.append(f'The {enemy["name"]} falls! Victory!')
    exp = enemy.get('exp_reward', enemy.get('experience_reward', 30))
    gold = enemy.get('gold_reward', 10)
    log.append(f'You gain {exp} experience and {gold} gold.')

    player['gold'] += gold
    leveled = gain_experience(player, exp)

    loot = enemy.get('loot_table', [])
    loot_item = None
    if loot and random.random() < 0.35:
        loot_item = random.choice(loot)
        player['inventory'].append(loot_item)
        log.append(f'The enemy drops: {loot_item}.')

    if leveled:
        log.append(f'You have reached level {player["level"]}! Your strength grows.')
        add_message(f'Level Up! You are now level {player["level"]}.', 'var(--gold)')

    add_message(f'Defeated the {enemy["name"]}. +{exp} EXP, +{gold} gold.', 'var(--green-bright)')

    # Update quest kill progress
    enemy_key = enemy.get('key', enemy.get('name', '').lower().replace(' ', '_'))
    enemy_name = enemy.get('name', '')
    update_quest_kills(enemy_key, enemy_name)

    session['battle_log'] = log
    session['battle_enemy'] = None
    save_player(player)

    return render_template(
        'victory.html',
        player=player,
        enemy=enemy,
        log=log,
        exp=exp,
        gold=gold,
        loot_item=loot_item,
        leveled=leveled,
    )


def _handle_defeat(player, enemy, log):
    log.append('You fall in battle...')
    player['hp'] = max(1, int(player['max_hp'] * 0.25))
    log.append(f'You awaken later, battered. HP: {player["hp"]}')
    add_message(f'You were defeated by the {enemy["name"]}.', 'var(--red)')
    add_message('You recover with a fraction of your health.', 'var(--text-dim)')

    session['battle_log'] = log
    session['battle_enemy'] = None
    save_player(player)

    return render_template('defeat.html', player=player, enemy=enemy, log=log)


# ─── Save / Load ───────────────────────────────────────────────────────────────


@app.route('/api/save', methods=['POST'])
def api_save():
    player = session.get('player')
    if not player:
        return jsonify({'error': 'No active character.'}), 400

    save_data = {
        'player': player,
        'current_area': session.get('current_area', 'starting_village'),
        'completed_missions': session.get('completed_missions', []),
        'visited_areas': session.get('visited_areas', []),
        'quest_progress': session.get('quest_progress', {}),
        'save_version': '5.0',
    }

    player_name = (player.get('name') or 'save').replace(' ', '_')
    filename = f'our_legacy_{player_name}_lv{player.get("level", 1)}.json'
    raw = json.dumps(save_data, indent=2)
    response = make_response(raw)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@app.route('/api/load', methods=['POST'])
def api_load():
    data = request.get_json(force=True, silent=True) or {}
    player = data.get('player')
    if not player or not player.get('name'):
        return jsonify({'error': 'Invalid save file: missing player data.'}), 400

    # Ensure equipment has all slots
    if 'equipment' not in player:
        player['equipment'] = {}
    for slot in ('weapon', 'armor', 'offhand', 'accessory'):
        player['equipment'].setdefault(slot, None)

    session['player'] = player
    session['current_area'] = data.get('current_area', 'starting_village')
    session['completed_missions'] = data.get('completed_missions', [])
    session['visited_areas'] = data.get('visited_areas', [session['current_area']])
    session['quest_progress'] = data.get('quest_progress', {})
    session['messages'] = []
    session.modified = True
    return jsonify({'ok': True, 'player_name': player.get('name')})


# ─── Crafting Routes ──────────────────────────────────────────────────────────


@app.route('/crafting')
def crafting():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    crafting_data = GAME_DATA.get('crafting', {})
    recipes = get_recipes(crafting_data)
    categories = get_recipe_categories(crafting_data)

    enriched = []
    for recipe in recipes:
        check = check_recipe_craftable(player, recipe)
        enriched.append({**recipe, 'can_craft': check['ok'], 'missing': check.get('missing', [])})

    return render_template(
        'crafting.html',
        player=player,
        recipes=enriched,
        categories=categories,
        messages=list(reversed(get_messages()))[:15],
    )


@app.route('/action/craft', methods=['POST'])
def action_craft():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    recipe_id = request.form.get('recipe_id', '')
    crafting_data = GAME_DATA.get('crafting', {})
    result = craft_item(player, recipe_id, crafting_data)
    color = 'var(--green-bright)' if result['ok'] else 'var(--red)'
    add_message(result['message'], color)
    save_player(player)
    return redirect(url_for('crafting'))


# ─── Dungeon Routes ────────────────────────────────────────────────────────────


@app.route('/dungeons')
def dungeons():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    area_key = session.get('current_area', 'starting_village')
    dungeons_data = GAME_DATA.get('dungeons', {})
    available = get_available_dungeons(dungeons_data, area_key, player.get('level', 1))
    active = session.get('active_dungeon')

    return render_template(
        'dungeons.html',
        player=player,
        dungeons=available,
        active_dungeon=active,
        messages=list(reversed(get_messages()))[:15],
    )


@app.route('/action/dungeon/enter', methods=['POST'])
def dungeon_enter():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    dungeon_id = request.form.get('dungeon_id', '')
    dungeons_data = GAME_DATA.get('dungeons', {})
    all_dungeons = dungeons_data.get('dungeons', [])
    dungeon = next((d for d in all_dungeons if d.get('id') == dungeon_id), None)

    if not dungeon:
        add_message('Unknown dungeon.', 'var(--red)')
        return redirect(url_for('dungeons'))

    difficulty = dungeon.get('difficulty', [1, 3])
    min_level = max(1, difficulty[0] * 2)
    if player.get('level', 1) < min_level:
        add_message(f'You need to be level {min_level} to enter this dungeon.', 'var(--red)')
        return redirect(url_for('dungeons'))

    rooms = generate_dungeon_rooms(dungeon, dungeons_data)
    session['active_dungeon'] = {
        'dungeon': dungeon,
        'rooms': rooms,
        'room_index': 0,
        'current_challenge': None,
        'challenge_answered': False,
    }
    session.modified = True
    add_message(f'You enter {dungeon.get("name", "the dungeon")}! Steel yourself.', 'var(--gold)')
    save_player(player)
    return redirect(url_for('dungeon_room'))


@app.route('/dungeon/room')
def dungeon_room():
    player = get_player()
    active = session.get('active_dungeon')
    if not player or not active:
        return redirect(url_for('dungeons'))

    rooms = active['rooms']
    idx = active['room_index']
    if idx >= len(rooms):
        return redirect(url_for('dungeon_complete'))

    room = rooms[idx]
    dungeon = active.get('dungeon', {})
    current_challenge = active.get('current_challenge')

    # If interactive room and no challenge set yet, generate it
    room_type = room.get('type', 'empty')
    if room_type in ('question', 'multi_choice') and not current_challenge:
        dungeons_data = GAME_DATA.get('dungeons', {})
        if room_type == 'question':
            current_challenge = room.get('challenge') or process_question_room(dungeons_data)
        else:
            current_challenge = room.get('challenge') or _pick_multi_choice(dungeons_data)
        active['current_challenge'] = current_challenge
        session['active_dungeon'] = active

    return render_template(
        'dungeon_room.html',
        player=player,
        room=room,
        room_num=idx + 1,
        total_rooms=len(rooms),
        dungeon=dungeon,
        current_challenge=current_challenge,
        messages=list(reversed(get_messages()))[:10],
    )


@app.route('/action/dungeon/proceed', methods=['POST'])
def dungeon_proceed():
    player = get_player()
    active = session.get('active_dungeon')
    if not player or not active:
        return redirect(url_for('dungeons'))

    rooms = active['rooms']
    idx = active['room_index']
    if idx >= len(rooms):
        return redirect(url_for('dungeon_complete'))

    room = rooms[idx]
    room_type = room.get('type', 'empty')

    dungeons_data = GAME_DATA.get('dungeons', {})
    items_data = GAME_DATA.get('items', {})
    enemies_data = GAME_DATA.get('enemies', {})
    areas_data = GAME_DATA.get('areas', {})
    area_key = session.get('current_area', 'starting_village')

    if room_type == 'battle':
        result = process_battle_room(player, room, enemies_data, areas_data, area_key)
        if result['type'] == 'battle':
            enemy = result['enemy']
            session['battle_enemy'] = enemy
            session['battle_log'] = [f'A {enemy.get("name", "enemy")} confronts you in the dungeon!']
            active['room_index'] = idx + 1
            active['current_challenge'] = None
            session['active_dungeon'] = active
            save_player(player)
            return redirect(url_for('battle'))
        else:
            for msg in result.get('messages', []):
                add_message(msg['text'], msg.get('color', 'var(--text-light)'))

    elif room_type == 'chest':
        result = process_chest_room(player, room, dungeons_data, items_data)
        for msg in result.get('messages', []):
            add_message(msg['text'], msg.get('color', 'var(--text-light)'))

    elif room_type == 'trap_chest':
        roll = random.randint(1, 20)
        result = process_trap_chest_room(player, room, dungeons_data, items_data, roll)
        for msg in result.get('messages', []):
            add_message(msg['text'], msg.get('color', 'var(--text-light)'))

    elif room_type == 'boss':
        boss_id = room.get('boss_id', active.get('dungeon', {}).get('boss_id', ''))
        bosses_data = GAME_DATA.get('bosses', {})
        boss_data = bosses_data.get(boss_id, {})
        if boss_data:
            difficulty = room.get('difficulty', 1)
            scale = 0.8 + difficulty * 0.2
            enemy = {
                'key': boss_id,
                'name': boss_data.get('name', boss_id.replace('_', ' ').title()),
                'hp': int(boss_data.get('hp', 200) * scale),
                'max_hp': int(boss_data.get('hp', 200) * scale),
                'attack': int(boss_data.get('attack', 20) * scale),
                'defense': int(boss_data.get('defense', 10) * scale),
                'speed': boss_data.get('speed', 12),
                'exp_reward': int(boss_data.get('experience_reward', 200) * scale),
                'gold_reward': int(boss_data.get('gold_reward', 100) * scale),
                'loot_table': boss_data.get('loot_table', []),
                'is_boss': True,
            }
        else:
            # Generic boss
            lvl = player.get('level', 1)
            enemy = {
                'key': 'dungeon_boss',
                'name': 'Dungeon Boss',
                'hp': 200 + lvl * 30,
                'max_hp': 200 + lvl * 30,
                'attack': 20 + lvl * 3,
                'defense': 12 + lvl * 2,
                'speed': 12,
                'exp_reward': 300 + lvl * 50,
                'gold_reward': 100 + lvl * 20,
                'loot_table': [],
                'is_boss': True,
            }
        session['battle_enemy'] = enemy
        session['battle_log'] = [f'The guardian {enemy["name"]} awakens! This is the final battle!']
        active['room_index'] = idx + 1
        active['current_challenge'] = None
        session['active_dungeon'] = active
        save_player(player)
        return redirect(url_for('battle'))

    elif room_type == 'question':
        # Question room — redirect back to show it
        add_message('A riddle challenge awaits in the chamber!', 'var(--gold)')
        return redirect(url_for('dungeon_room'))

    elif room_type == 'multi_choice':
        add_message('A fateful choice confronts you!', 'var(--gold)')
        return redirect(url_for('dungeon_room'))

    else:
        result = process_empty_room(room)
        for msg in result.get('messages', []):
            add_message(msg['text'], msg.get('color', 'var(--text-light)'))

    active['room_index'] = idx + 1
    active['current_challenge'] = None
    session['active_dungeon'] = active
    save_player(player)

    if active['room_index'] >= len(rooms):
        return redirect(url_for('dungeon_complete'))
    return redirect(url_for('dungeon_room'))


@app.route('/dungeon/answer', methods=['POST'])
def dungeon_answer():
    player = get_player()
    active = session.get('active_dungeon')
    if not player or not active:
        return redirect(url_for('dungeons'))

    answer_text = request.form.get('answer', '').strip()
    challenge = active.get('current_challenge', {})
    result = answer_question(player, challenge, answer_text)

    for msg in result.get('messages', []):
        add_message(msg['text'], msg.get('color', 'var(--text-light)'))

    # Advance room regardless of success/fail
    active['room_index'] = active.get('room_index', 0) + 1
    active['current_challenge'] = None
    session['active_dungeon'] = active
    save_player(player)

    if active['room_index'] >= len(active['rooms']):
        return redirect(url_for('dungeon_complete'))
    return redirect(url_for('dungeon_room'))


@app.route('/dungeon/choose', methods=['POST'])
def dungeon_choose():
    player = get_player()
    active = session.get('active_dungeon')
    if not player or not active:
        return redirect(url_for('dungeons'))

    choice_idx = int(request.form.get('choice', 0))
    challenge = active.get('current_challenge', {})
    result = answer_multi_choice(player, challenge, choice_idx)

    for msg in result.get('messages', []):
        add_message(msg['text'], msg.get('color', 'var(--text-light)'))

    active['room_index'] = active.get('room_index', 0) + 1
    active['current_challenge'] = None
    session['active_dungeon'] = active
    save_player(player)

    if active['room_index'] >= len(active['rooms']):
        return redirect(url_for('dungeon_complete'))
    return redirect(url_for('dungeon_room'))


@app.route('/dungeon/complete')
def dungeon_complete():
    player = get_player()
    active = session.get('active_dungeon')
    if not player:
        return redirect(url_for('index'))

    if active:
        dungeon = active.get('dungeon', {})
        result = complete_dungeon(player, dungeon)
        for msg in result.get('messages', []):
            add_message(msg['text'], msg.get('color', 'var(--gold)'))
        session.pop('active_dungeon', None)
        save_player(player)

    return redirect(url_for('game'))


@app.route('/dungeon/abandon', methods=['POST'])
def dungeon_abandon():
    session.pop('active_dungeon', None)
    add_message('You retreat from the dungeon.', 'var(--text-dim)')
    return redirect(url_for('dungeons'))


# ─── Elite Market Routes ───────────────────────────────────────────────────────


@app.route('/market')
def market():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    market_api = get_market_api()
    result = market_api.fetch_market_data()
    market_items = []
    cooldown_msg = None

    if result.get('ok') and result.get('data', {}).get('ok'):
        market_items = result['data'].get('items', [])
    elif result.get('cooldown'):
        cooldown_msg = result.get('message', 'Market is closed.')
    elif not result.get('ok'):
        cooldown_msg = result.get('message', 'Could not reach the market.')

    return render_template(
        'market.html',
        player=player,
        market_items=market_items,
        cooldown_msg=cooldown_msg,
        messages=list(reversed(get_messages()))[:15],
    )


@app.route('/action/market/buy', methods=['POST'])
def market_buy():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    item_name = request.form.get('item_name', '')
    item_price = int(request.form.get('item_price', 0))

    if player['gold'] < item_price:
        add_message(f'Not enough gold. Need {item_price} gold.', 'var(--red)')
    else:
        player['gold'] -= item_price
        player['inventory'].append(item_name)
        add_message(f'Purchased {item_name} from the Elite Market for {item_price} gold!', 'var(--gold)')

    save_player(player)
    return redirect(url_for('market'))


# ─── Server-side Save / Load ──────────────────────────────────────────────────


@app.route('/api/server_save', methods=['POST'])
def api_server_save():
    player = get_player()
    if not player:
        return jsonify({'ok': False, 'message': 'No active character.'})

    result = save_game(
        player=player,
        current_area=session.get('current_area', 'starting_village'),
        visited_areas=session.get('visited_areas', []),
        completed_missions=session.get('completed_missions', []),
    )
    return jsonify(result)


@app.route('/api/server_saves', methods=['GET'])
def api_server_saves():
    saves = list_saves()
    return jsonify({'saves': saves})


@app.route('/api/server_load', methods=['POST'])
def api_server_load():
    data = request.get_json(force=True, silent=True) or {}
    filepath = data.get('filepath', '')
    if not filepath:
        return jsonify({'ok': False, 'message': 'No file path provided.'})

    result = load_save(filepath)
    if result.get('ok'):
        session['player'] = result['player']
        session['current_area'] = result['current_area']
        session['visited_areas'] = result['visited_areas']
        session['completed_missions'] = result['completed_missions']
        session['messages'] = []
        session.modified = True

    return jsonify({'ok': result.get('ok'), 'message': result.get('message', '')})


# ─── Utility API ─────────────────────────────────────────────────────────────


@app.route('/api/player_stats')
def api_player_stats():
    player = get_player()
    if not player:
        return jsonify({'ok': False})
    return jsonify({'ok': True, 'player': player})


@app.route('/new_game')
def new_game():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
