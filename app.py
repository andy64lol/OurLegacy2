"""
Our Legacy 2 - Flask Web Interface
Medieval fantasy RPG playable in the browser.
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from cryptography.fernet import Fernet
import pickle
import base64
import json
import random
import os

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
}

BUILDING_TYPES = {
    'house': {
        'label': 'House',
        'slots': 3
    },
    'decoration': {
        'label': 'Decoration',
        'slots': 10
    },
    'fencing': {
        'label': 'Fencing',
        'slots': 1
    },
    'garden': {
        'label': 'Garden',
        'slots': 3
    },
    'farm': {
        'label': 'Farm',
        'slots': 2
    },
    'training_place': {
        'label': 'Training Place',
        'slots': 3
    },
}

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
    """Advance all planted crop growth by 1 turn."""
    crops = player.get('crops', {})
    for slot_id, crop_info in crops.items():
        if not crop_info.get('ready', False):
            crop_info['turns'] = crop_info.get('turns', 0) + 1
            growth_time = crop_info.get('growth_time', 5)
            if crop_info['turns'] >= growth_time:
                crop_info['ready'] = True


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
            return render_template('create.html',
                                   data=GAME_DATA,
                                   error='Please enter a character name.')

        cls_data = GAME_DATA['classes'].get(cls, {})
        stats = cls_data.get('base_stats', {
            'hp': 100,
            'mp': 50,
            'attack': 10,
            'defense': 8,
            'speed': 10
        })

        player = {
            'name':
            name,
            'class':
            cls,
            'level':
            1,
            'experience':
            0,
            'experience_to_next':
            100,
            'hp':
            stats['hp'],
            'max_hp':
            stats['hp'],
            'mp':
            stats['mp'],
            'max_mp':
            stats['mp'],
            'attack':
            stats['attack'],
            'defense':
            stats['defense'],
            'speed':
            stats['speed'],
            'gold':
            cls_data.get('starting_gold', 100),
            'inventory':
            list(cls_data.get('starting_items', ['Health Potion'])),
            'equipment': {
                'weapon': None,
                'armor': None,
                'offhand': None
            },
            'companions': [],
            'rank':
            'F-Tier Adventurer',
            'level_up_bonuses':
            cls_data.get('level_up_bonuses', {
                'hp': 10,
                'mp': 2,
                'attack': 2,
                'defense': 1,
                'speed': 1
            }),
            # Land
            'comfort_points':
            0,
            'housing_owned': [],
            'building_slots': {},
            'crops': {},  # slot_id -> {crop_key, growth_time, turns, ready}
            'pet':
            None,
            'explore_count':
            0,
        }
        save_player(player)
        session['messages'] = []
        session['current_area'] = 'starting_village'
        session['completed_missions'] = []
        session['visited_areas'] = ['starting_village']
        add_message(f'Welcome, {name} the {cls}! Your legend begins.',
                    'var(--gold)')
        add_message(
            'You stand at the gates of the Starting Village. Adventure awaits.',
            'var(--text-light)')
        return redirect(url_for('game'))

    return render_template('create.html', data=GAME_DATA)


@app.route('/game')
def game():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})
    area_name = area.get('name', area_key.replace('_', ' ').title())

    connections = []
    for conn_key in area.get('connections', []):
        conn_area = GAME_DATA['areas'].get(conn_key, {})
        connections.append({
            'key':
            conn_key,
            'name':
            conn_area.get('name',
                          conn_key.replace('_', ' ').title()),
            'has_danger':
            bool(conn_area.get('possible_enemies')),
            'visited':
            conn_key in session.get('visited_areas', []),
        })

    # Shop items
    shop_items = []
    shop_name = ''
    for shop_key in area.get('shops', []):
        if shop_key == 'pet_shop':
            continue  # handled in land tab
        shop_data = GAME_DATA['shops'].get(shop_key, {})
        shop_name = shop_data.get('name', 'Shop')
        for item_name in shop_data.get('items', []):
            item_data = GAME_DATA['items'].get(item_name, {})
            price = item_data.get('price', item_data.get('value', 20))
            shop_items.append({
                'name': item_name,
                'price': price,
                'rarity': item_data.get('rarity', 'common'),
                'description': item_data.get('description', ''),
                'can_afford': player['gold'] >= price,
            })

    # Inventory
    inventory_items = []
    counts = {}
    for item_name in player.get('inventory', []):
        counts[item_name] = counts.get(item_name, 0) + 1
    for item_name, count in counts.items():
        item_data = GAME_DATA['items'].get(item_name, {})
        sell_price = max(
            1, int(item_data.get('price', item_data.get('value', 10)) * 0.5))
        inventory_items.append({
            'name': item_name,
            'count': count,
            'rarity': item_data.get('rarity', 'common'),
            'description': item_data.get('description', ''),
            'sell_price': sell_price,
            'type': item_data.get('type', ''),
        })

    # Missions
    available_missions = []
    completed = session.get('completed_missions', [])
    for mid, mission in GAME_DATA['missions'].items():
        if mid not in completed:
            available_missions.append({
                'id':
                mid,
                'name':
                mission.get('name', mid),
                'description':
                mission.get('description', ''),
                'exp_reward':
                mission.get('experience_reward', 0),
                'gold_reward':
                mission.get('gold_reward', 0),
            })

    # Your Land data
    land_data = None
    if area_key == 'your_land':
        housing_data = GAME_DATA['housing']
        farming_data = GAME_DATA['farming'].get('crops', {})
        pets_data = GAME_DATA['pets']
        owned_set = set(player.get('housing_owned', []))
        building_slots = player.get('building_slots', {})
        crops = player.get('crops', {})

        # Build a flat list of all housing items grouped by type
        housing_by_type = {}
        for h_key, h_item in housing_data.items():
            h_type = h_item.get('type', 'decoration')
            if h_type not in housing_by_type:
                housing_by_type[h_type] = []
            housing_by_type[h_type].append({
                'key':
                h_key,
                'name':
                h_item.get('name', h_key),
                'description':
                h_item.get('description', ''),
                'price':
                h_item.get('price', 100),
                'comfort':
                h_item.get('comfort_points', 5),
                'rarity':
                h_item.get('rarity', 'common'),
                'owned':
                h_key in owned_set,
                'can_afford':
                player['gold'] >= h_item.get('price', 100),
            })

        # Placed items per slot type
        placed_by_type = {}
        for slot_id, h_key in building_slots.items():
            if h_key:
                slot_type = slot_id.rsplit('_', 1)[0]
                h_item = housing_data.get(h_key, {})
                if slot_type not in placed_by_type:
                    placed_by_type[slot_type] = []
                placed_by_type[slot_type].append({
                    'slot_id':
                    slot_id,
                    'key':
                    h_key,
                    'name':
                    h_item.get('name', h_key),
                    'comfort':
                    h_item.get('comfort_points', 0),
                })

        # Farm slots
        farm_crops = []
        for i in range(1, 5):
            slot_id = f'farm_{i}'
            crop_info = crops.get(slot_id)
            if crop_info:
                crop_def = farming_data.get(crop_info['crop_key'], {})
                farm_crops.append({
                    'slot_id':
                    slot_id,
                    'crop_key':
                    crop_info['crop_key'],
                    'name':
                    crop_def.get('name', crop_info['crop_key']),
                    'ready':
                    crop_info.get('ready', False),
                    'turns':
                    crop_info.get('turns', 0),
                    'growth_time':
                    crop_info.get('growth_time', 5),
                    'sell_price':
                    crop_def.get('sell_price', 15),
                    'harvest_amount':
                    crop_def.get('harvest_amount', 3),
                })
            else:
                farm_crops.append({'slot_id': slot_id, 'crop_key': None})

        pet_data_current = None
        if player.get('pet'):
            pd = pets_data.get(player['pet'], {})
            pet_data_current = {
                'key': player['pet'],
                'name': pd.get('name', player['pet']),
                'boosts': pd.get('boosts', {})
            }

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
        missions=available_missions[:12],
        messages=list(reversed(get_messages()))[:25],
        completed_count=len(completed),
        land_data=land_data,
    )


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
        lvl = player['level']
        scale = 1 + (lvl - 1) * 0.12
        enemy = {
            'key':
            enemy_key,
            'name':
            enemy_data.get('name',
                           enemy_key.replace('_', ' ').title()),
            'hp':
            int(enemy_data.get('hp', 50) * scale),
            'max_hp':
            int(enemy_data.get('hp', 50) * scale),
            'attack':
            int(enemy_data.get('attack', 10) * scale),
            'defense':
            int(enemy_data.get('defense', 5) * scale),
            'speed':
            enemy_data.get('speed', 10),
            'exp_reward':
            int(enemy_data.get('experience_reward', 30) * scale),
            'gold_reward':
            max(
                1,
                int(enemy_data.get('gold_reward', 10)) +
                random.randint(-3, 10)),
            'loot_table':
            enemy_data.get('loot_table', []),
        }
        session['battle_enemy'] = enemy
        session['battle_log'] = [
            f'A {enemy["name"]} emerges from the shadows! (HP: {enemy["hp"]})'
        ]
        session.modified = True
        save_player(player)
        return redirect(url_for('battle'))
    elif roll < 0.70:
        gold_found = random.randint(5, 25)
        player['gold'] += gold_found
        add_message(f'You search the area and find {gold_found} gold coins.',
                    'var(--gold)')
    elif roll < 0.82:
        heal = random.randint(10, 30)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        add_message(f'You discover a herb and recover {heal} HP.',
                    'var(--green-bright)')
    elif roll < 0.90:
        player['inventory'].append('Health Potion')
        add_message('You find a discarded Health Potion on the ground.',
                    'var(--text-light)')
    else:
        add_message(
            'You explore the area thoroughly but find nothing of note.',
            'var(--text-dim)')

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
        add_message(f'You rest for {cost} gold. HP and MP fully restored.',
                    'var(--green-bright)')
    else:
        add_message('You rest peacefully on your land. HP and MP restored.',
                    'var(--green-bright)')

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
    price = item_data.get('price', item_data.get('value', 20))

    if player['gold'] < price:
        add_message(f'You cannot afford {item_name}. Cost: {price} gold.',
                    'var(--red)')
    else:
        player['gold'] -= price
        player['inventory'].append(item_name)
        add_message(f'You purchase {item_name} for {price} gold.',
                    'var(--gold)')

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
        sell_price = max(
            1, int(item_data.get('price', item_data.get('value', 10)) * 0.5))
        player['inventory'].remove(item_name)
        player['gold'] += sell_price
        add_message(f'You sell {item_name} for {sell_price} gold.',
                    'var(--gold)')
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

    lower = item_name.lower()
    if 'health' in lower or ('potion' in lower and 'mana' not in lower):
        heal = random.randint(40, 70)
        if 'large' in lower or 'greater' in lower:
            heal = random.randint(70, 130)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(f'You drink the {item_name} and recover {heal} HP.',
                    'var(--green-bright)')
    elif 'mana' in lower:
        restore = random.randint(25, 50)
        player['mp'] = min(player['max_mp'], player['mp'] + restore)
        player['inventory'].remove(item_name)
        add_message(f'You drink the {item_name} and restore {restore} MP.',
                    'var(--mana-bright)')
    elif 'elixir' in lower or 'tears' in lower:
        heal = random.randint(50, 100)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(
            f'You use the {item_name} and feel its power (+{heal} HP).',
            'var(--gold)')
    else:
        add_message(f'You cannot use {item_name} outside of battle.',
                    'var(--text-dim)')

    save_player(player)
    return redirect(url_for('game'))


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

    mission = GAME_DATA['missions'].get(mission_id)
    if not mission:
        return redirect(url_for('game'))

    completed.append(mission_id)
    session['completed_missions'] = completed
    exp = mission.get('experience_reward', 0)
    gold = mission.get('gold_reward', 0)
    player['gold'] += gold
    leveled = gain_experience(player, exp)

    add_message(f'Mission complete: {mission.get("name", mission_id)}',
                'var(--gold)')
    add_message(f'Reward: {exp} experience, {gold} gold.', 'var(--text-light)')
    if leveled:
        add_message(
            f'You have reached level {player["level"]}! Your power grows.',
            'var(--gold)')

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
        add_message(f'Not enough gold. {h_data["name"]} costs {price} gold.',
                    'var(--red)')
        save_player(player)
        return redirect(url_for('game'))

    player['gold'] -= price
    owned = player.get('housing_owned', [])
    owned.append(h_key)
    player['housing_owned'] = owned
    add_message(f'You purchase {h_data["name"]} for {price} gold.',
                'var(--gold)')
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

    # Remove old item from slot if present
    if slot_id in slots and slots[slot_id]:
        old_h = GAME_DATA['housing'].get(slots[slot_id], {})
        old_cp = old_h.get('comfort_points', 0)
        player['comfort_points'] = max(
            0,
            player.get('comfort_points', 0) - old_cp)

    slots[slot_id] = h_key
    player['building_slots'] = slots
    player['comfort_points'] = player.get('comfort_points', 0) + comfort
    add_message(
        f'You place {h_data.get("name", h_key)} at {slot_id}. Comfort: +{comfort}',
        'var(--green-bright)')
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
        add_message(f'Removed {h_data.get("name", h_key)} from {slot_id}.',
                    'var(--text-dim)')
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
        add_message(
            f'Slot {slot_id} is already occupied. Harvest or clear it first.',
            'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    crops[slot_id] = {
        'crop_key': crop_key,
        'growth_time': crop_def.get('growth_time', 5),
        'turns': 0,
        'ready': False,
    }
    player['crops'] = crops
    add_message(
        f'You plant {crop_def["name"]} in {slot_id}. It will be ready in {crop_def["growth_time"]} turns.',
        'var(--green-bright)')
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
        turns_left = crop_info.get('growth_time', 5) - crop_info.get(
            'turns', 0)
        add_message(
            f'Crop is not ready yet. About {turns_left} turns remaining.',
            'var(--text-dim)')
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
    add_message(
        f'You harvest {amount}x {crop_def.get("name", crop_info["crop_key"])} and sell for {gold_earned} gold!',
        'var(--gold)')
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
        add_message(f'Not enough gold. {pet_data["name"]} costs {price} gold.',
                    'var(--red)')
        save_player(player)
        return redirect(url_for('game') + '#land')

    # Sell old pet back for 50%
    if player.get('pet'):
        old_pet = GAME_DATA['pets'].get(player['pet'], {})
        old_price = old_pet.get('price', 500)
        refund = old_price // 2
        player['gold'] += refund
        add_message(
            f'Your old companion ({old_pet.get("name", player["pet"])}) is released. Refund: {refund} gold.',
            'var(--text-dim)')

        # Remove old pet stat boosts
        for stat, val in old_pet.get('boosts', {}).items():
            if stat in ('attack', 'defense', 'speed'):
                player[stat] = max(1, player.get(stat, 0) - val)
            elif stat in ('hp', 'max_hp'):
                player['max_hp'] = max(1, player.get('max_hp', 0) - val)
            elif stat in ('mp', 'max_mp'):
                player['max_mp'] = max(1, player.get('max_mp', 0) - val)

    player['gold'] -= price
    player['pet'] = pet_key

    # Apply new pet stat boosts
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

    add_message(f'You adopt {pet_data["name"]} as your companion!',
                'var(--gold)')
    if boosts:
        boost_str = ', '.join(f'+{v} {k}' for k, v in boosts.items()
                              if isinstance(v, int))
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

    return render_template(
        'battle.html',
        player=player,
        enemy=enemy,
        battle_log=battle_log[-14:],
        usable_items=usable_items,
    )


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
        log.append(
            f'CRITICAL STRIKE! You deal {p_dmg} damage to the {enemy["name"]}!'
        )
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
    e_dmg = max(
        0,
        enemy['attack'] - int(player['defense'] * 2) + random.randint(-2, 2))
    player['hp'] = max(0, player['hp'] - e_dmg)

    if e_dmg > 0:
        log.append(
            f'The {enemy["name"]} attacks, but you reduce the blow to {e_dmg} damage.'
        )
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

        e_dmg = max(
            1, enemy['attack'] - player['defense'] + random.randint(-1, 3))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(
            f'The {enemy["name"]} seizes the moment and strikes for {e_dmg} damage.'
        )

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
        e_dmg = max(1,
                    enemy['attack'] - player['defense'] + random.randint(0, 5))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(
            f'You try to flee but the {enemy["name"]} cuts you off, dealing {e_dmg} damage!'
        )

    if player['hp'] <= 0:
        return _handle_defeat(player, enemy, log)

    session['battle_enemy'] = enemy
    session['battle_log'] = log
    save_player(player)
    return redirect(url_for('battle'))


def _handle_victory(player, enemy, log):
    log.append(f'The {enemy["name"]} falls! Victory!')
    exp = enemy['exp_reward']
    gold = enemy['gold_reward']
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
        log.append(
            f'You have reached level {player["level"]}! Your strength grows.')
        add_message(f'Level Up! You are now level {player["level"]}.',
                    'var(--gold)')

    add_message(f'Defeated the {enemy["name"]}. +{exp} EXP, +{gold} gold.',
                'var(--green-bright)')

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
    add_message('You recover with a fraction of your health.',
                'var(--text-dim)')

    session['battle_log'] = log
    session['battle_enemy'] = None
    save_player(player)

    return render_template('defeat.html', player=player, enemy=enemy, log=log)


# ─── Save / Load (client-side encrypted) ────────────────────────────────────


@app.route('/api/generate_key', methods=['POST'])
def api_generate_key():
    key = Fernet.generate_key()
    return jsonify({'key': key.decode('utf-8')})


@app.route('/api/save', methods=['POST'])
def api_save():
    data = request.get_json()
    key_b64 = data.get('key', '')
    try:
        fernet = Fernet(key_b64.encode('utf-8'))
    except Exception:
        return jsonify({'error': 'Invalid key'}), 400

    save_data = {
        'player': session.get('player'),
        'messages': session.get('messages', []),
        'current_area': session.get('current_area', 'starting_village'),
        'completed_missions': session.get('completed_missions', []),
        'visited_areas': session.get('visited_areas', []),
    }

    raw = pickle.dumps(save_data)
    encrypted = fernet.encrypt(raw)
    encoded = base64.b64encode(encrypted).decode('utf-8')
    return jsonify({'data': encoded})


@app.route('/api/load', methods=['POST'])
def api_load():
    data = request.get_json()
    key_b64 = data.get('key', '')
    encoded_data = data.get('data', '')

    try:
        fernet = Fernet(key_b64.encode('utf-8'))
        encrypted = base64.b64decode(encoded_data.encode('utf-8'))
        raw = fernet.decrypt(encrypted)
        save_data = pickle.loads(raw)
    except Exception as e:
        return jsonify({'error': f'Failed to load: {str(e)}'}), 400

    session['player'] = save_data.get('player')
    session['messages'] = save_data.get('messages', [])
    session['current_area'] = save_data.get('current_area', 'starting_village')
    session['completed_missions'] = save_data.get('completed_missions', [])
    session['visited_areas'] = save_data.get('visited_areas', [])
    session.modified = True

    return jsonify({'ok': True})


@app.route('/new_game')
def new_game():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
