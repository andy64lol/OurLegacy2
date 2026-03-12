"""
Our Legacy 2 - Flask Web Interface
Medieval fantasy RPG playable in the browser.
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
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
}

CLASS_ICONS = {
    'Warrior': 'Warrior',
    'Mage': 'Mage',
    'Rogue': 'Rogue',
    'Hunter': 'Hunter',
    'Bard': 'Bard',
    'Paladin': 'Paladin',
    'Druid': 'Druid',
    'Priest': 'Priest',
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
        stats = cls_data.get('base_stats', {'hp': 100, 'mp': 50, 'attack': 10, 'defense': 8, 'speed': 10})

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
            'equipment': {'weapon': None, 'armor': None, 'offhand': None},
            'companions': [],
            'rank': 'F-Tier Adventurer',
            'level_up_bonuses': cls_data.get('level_up_bonuses', {'hp': 10, 'mp': 2, 'attack': 2, 'defense': 1, 'speed': 1}),
        }
        save_player(player)
        session['messages'] = []
        session['current_area'] = 'starting_village'
        session['completed_missions'] = []
        session['visited_areas'] = ['starting_village']
        add_message(f'Welcome, {name} the {cls}! Your legend begins.', 'var(--gold)')
        add_message('You stand at the gates of the Starting Village. Adventure awaits.', 'var(--text-light)')
        return redirect(url_for('game'))

    return render_template('create.html', data=GAME_DATA)


@app.route('/game')
def game():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})
    connections = []
    for conn_key in area.get('connections', []):
        conn_area = GAME_DATA['areas'].get(conn_key, {})
        connections.append({
            'key': conn_key,
            'name': conn_area.get('name', conn_key.replace('_', ' ').title()),
            'has_danger': bool(conn_area.get('possible_enemies')),
            'visited': conn_key in session.get('visited_areas', []),
        })

    shop_items = []
    shop_name = ''
    for shop_key in area.get('shops', []):
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

    inventory_items = []
    counts = {}
    for item_name in player.get('inventory', []):
        counts[item_name] = counts.get(item_name, 0) + 1
    for item_name, count in counts.items():
        item_data = GAME_DATA['items'].get(item_name, {})
        sell_price = max(1, int(item_data.get('price', item_data.get('value', 10)) * 0.5))
        inventory_items.append({
            'name': item_name,
            'count': count,
            'rarity': item_data.get('rarity', 'common'),
            'description': item_data.get('description', ''),
            'sell_price': sell_price,
            'type': item_data.get('type', ''),
        })

    available_missions = []
    completed = session.get('completed_missions', [])
    for mid, mission in GAME_DATA['missions'].items():
        if mid not in completed:
            available_missions.append({
                'id': mid,
                'name': mission.get('name', mid),
                'description': mission.get('description', ''),
                'exp_reward': mission.get('experience_reward', 0),
                'gold_reward': mission.get('gold_reward', 0),
            })

    return render_template('game.html',
        player=player,
        area=area,
        area_key=area_key,
        area_name=area.get('name', area_key.replace('_', ' ').title()),
        connections=connections,
        shop_items=shop_items,
        shop_name=shop_name,
        inventory_items=inventory_items,
        missions=available_missions[:12],
        messages=list(reversed(get_messages()))[:25],
        completed_count=len(completed),
    )


@app.route('/action/explore', methods=['POST'])
def action_explore():
    player = get_player()
    if not player:
        return redirect(url_for('index'))

    area_key = session.get('current_area', 'starting_village')
    area = GAME_DATA['areas'].get(area_key, {})
    possible_enemies = area.get('possible_enemies', [])

    roll = random.random()
    if possible_enemies and roll < 0.55:
        enemy_key = random.choice(possible_enemies)
        enemy_data = GAME_DATA['enemies'].get(enemy_key, {})
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
        add_message(f'You discover a herb and recover {heal} HP.', 'var(--green)')
    elif roll < 0.90:
        player['inventory'].append('Health Potion')
        add_message('You find a discarded Health Potion on the ground.', 'var(--text-light)')
    else:
        add_message('You explore the area thoroughly but find nothing of note.', 'var(--text-dim)')

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
    if player['gold'] < cost:
        add_message(f'You need {cost} gold coins to rest at the inn.', 'var(--red)')
        return redirect(url_for('game'))

    player['gold'] -= cost
    player['hp'] = player['max_hp']
    player['mp'] = player['max_mp']
    add_message(f'You rest at the inn for {cost} gold. HP and MP fully restored.', 'var(--green)')
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
        add_message(f'You cannot afford {item_name}. You need {price} gold.', 'var(--red)')
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

    lower = item_name.lower()
    if 'health' in lower or ('potion' in lower and 'mana' not in lower):
        heal = random.randint(40, 70)
        if 'large' in lower or 'greater' in lower:
            heal = random.randint(70, 130)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(f'You drink the {item_name} and recover {heal} HP.', 'var(--green)')
    elif 'mana' in lower:
        restore = random.randint(25, 50)
        player['mp'] = min(player['max_mp'], player['mp'] + restore)
        player['inventory'].remove(item_name)
        add_message(f'You drink the {item_name} and restore {restore} MP.', 'var(--mana-blue)')
    elif 'elixir' in lower or 'tears' in lower or 'potion' in lower:
        heal = random.randint(50, 100)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(f'You use the {item_name} and feel its power (+{heal} HP).', 'var(--gold)')
    else:
        add_message(f'You cannot use {item_name} outside of battle.', 'var(--text-dim)')

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

    add_message(f'Mission complete: {mission.get("name", mission_id)}', 'var(--gold)')
    add_message(f'Reward: {exp} experience, {gold} gold.', 'var(--text-light)')
    if leveled:
        add_message(f'You have reached level {player["level"]}! Your power grows.', 'var(--gold)')

    save_player(player)
    return redirect(url_for('game'))


# ─── Battle Routes ───────────────────────────────────────────────────────────

@app.route('/battle')
def battle():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    battle_log = session.get('battle_log', [])
    usable_items = [i for i in player.get('inventory', [])
                    if any(x in i.lower() for x in ['potion', 'elixir', 'tears', 'tonic'])]

    return render_template('battle.html',
        player=player,
        enemy=enemy,
        battle_log=battle_log[-12:],
        usable_items=usable_items,
    )


@app.route('/battle/attack', methods=['POST'])
def battle_attack():
    player = get_player()
    enemy = session.get('battle_enemy')
    if not player or not enemy:
        return redirect(url_for('game'))

    log = session.get('battle_log', [])

    # Player attacks
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
        log.append(f'The {enemy["name"]} attacks but you absorb most of it, taking {e_dmg} damage.')
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

        # Enemy counter-attacks during item use
        e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(-1, 3))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(f'The {enemy["name"]} seizes the moment and strikes you for {e_dmg} damage.')

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
        log.append(f'You have reached level {player["level"]}! Your strength grows.')
        add_message(f'Level Up! You are now level {player["level"]}.', 'var(--gold)')

    add_message(f'Defeated the {enemy["name"]}. +{exp} EXP, +{gold} gold.', 'var(--green)')

    session['battle_log'] = log
    session['battle_enemy'] = None
    save_player(player)

    return render_template('victory.html',
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

    return render_template('defeat.html',
        player=player,
        enemy=enemy,
        log=log,
    )


@app.route('/new_game')
def new_game():
    session.clear()
    return redirect(url_for('index'))


@app.route('/static/fonts/<path:filename>')
def serve_font(filename):
    return send_from_directory('static/fonts', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
