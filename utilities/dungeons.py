import random
from typing import Dict, List, Any, Optional

def get_available_dungeons(dungeons_data: Dict[str, Any], current_area: str,
                           player_level: int,
                           visited_areas: Optional[List[str]] = None,
                           areas_data: Optional[Dict[str, Any]] = None
                           ) -> List[Dict[str, Any]]:
    all_dungeons = dungeons_data.get('dungeons', [])
    visited_set = set(visited_areas or [])
    areas_data = areas_data or {}
    result = []
    for dungeon in all_dungeons:
        difficulty = dungeon.get('difficulty', [1, 3])
        min_level = max(1, difficulty[0] * 2)
        allowed = dungeon.get('allowed_areas', [])

        discovered = any(a in visited_set for a in allowed)
        in_area = current_area in allowed
        level_ok = player_level >= min_level

        hint_area_id = allowed[0] if allowed else ""
        area_info = areas_data.get(hint_area_id, {})
        hint_area_name = (area_info.get("name") or
                          hint_area_id.replace("_", " ").title())

        result.append({
            'id': dungeon.get('id', dungeon.get('name', '').lower().replace(' ', '_')),
            'name': dungeon.get('name', 'Unknown Dungeon'),
            'description': dungeon.get('description', ''),
            'difficulty': difficulty,
            'rooms': dungeon.get('rooms', 5),
            'min_level': min_level,
            'allowed_areas': allowed,
            'completion_reward': dungeon.get('completion_reward', {}),
            'boss_id': dungeon.get('boss_id', ''),
            'discovered': discovered,
            'in_area': in_area,
            'available': discovered and in_area and level_ok,
            'hint_area_name': hint_area_name,
            'hint_area_id': hint_area_id,
        })
    result.sort(key=lambda d: d['min_level'])
    return result

def _pick_riddle(dungeons_data: Dict[str, Any]) -> Dict[str, Any]:
    templates = dungeons_data.get('challenge_templates', {})
    q_types = templates.get('question', {}).get('types', [])
    if q_types:
        return random.choice(q_types)
    return {
        'question':
        'What has four legs in the morning, two at noon, and three at night?',
        'answer': 'human',
        'hints': ['Think of life stages'],
        'failure_damage': 15,
        'success_reward': {
            'gold': 50,
            'experience': 100
        },
    }

def _pick_multi_choice(dungeons_data: Dict[str, Any]) -> Dict[str, Any]:
    templates = dungeons_data.get('challenge_templates', {})
    s_types = templates.get('selection', {}).get('types', [])
    if s_types:
        return random.choice(s_types)
    return {
        'question':
        'Which path do you take?',
        'options': [
            {
                'text': 'Left',
                'correct': True,
                'reason': 'Fortune favors the bold!'
            },
            {
                'text': 'Right',
                'correct': False,
                'reason': 'A dead end.'
            },
        ],
        'failure_damage':
        10,
        'success_reward': {
            'gold': 75,
            'experience': 150
        },
    }

def _pick_trap(dungeons_data: Dict[str, Any]) -> Dict[str, Any]:
    templates = dungeons_data.get('challenge_templates', {})
    trap_types = templates.get('trap', {}).get('types', [])
    if trap_types:
        t = random.choice(trap_types)
    else:
        t = {
            'id': 'generic_trap',
            'name': 'Pressure Trap',
            'description': 'The floor shifts!',
            'base_damage': 20,
            'difficulty': 'normal'
        }
    difficulty_map = {'easy': 8, 'normal': 10, 'hard': 13}
    threshold = difficulty_map.get(t.get('difficulty', 'normal'), 10)
    return {
        'trap_id': t.get('id', 'trap'),
        'name': t.get('name', 'Trap'),
        'description': t.get('description', 'A hidden trap activates!'),
        'base_damage': t.get('base_damage', 20),
        'threshold': threshold,
        'success_reward': {
            'gold': 30,
            'experience': 75
        },
    }

def generate_dungeon_rooms(
        dungeon: Dict[str, Any],
        dungeons_data: Optional[Dict[str,
                                     Any]] = None) -> List[Dict[str, Any]]:
    room_weights = dungeon.get('room_weights', {})
    total_rooms = dungeon.get('rooms', 5)
    if dungeons_data is None:
        dungeons_data = {}

    if not room_weights or sum(room_weights.values()) == 0:
        room_weights = {
            'battle': 35,
            'question': 20,
            'chest': 15,
            'empty': 10,
            'trap_chest': 5,
            'multi_choice': 5,
            'shrine': 5,
            'ambush': 5
        }

    if total_rooms <= 0:
        total_rooms = 5

    room_types = list(room_weights.keys())
    weights = list(room_weights.values())

    rooms = []
    for i in range(total_rooms):
        if i == total_rooms - 1:
            room_type = 'boss'
        else:
            room_type = random.choices(room_types, weights=weights, k=1)[0]

        difficulty = dungeon.get('difficulty', [1, 3])[0] + (i * 0.5)
        room: Dict[str, Any] = {
            'type': room_type,
            'room_number': i + 1,
            'difficulty': difficulty,
        }

        if room_type == 'question':
            room['challenge'] = _pick_riddle(dungeons_data)
        elif room_type == 'multi_choice':
            room['challenge'] = _pick_multi_choice(dungeons_data)
        elif room_type in ('trap_chest', 'trap'):
            room['challenge'] = _pick_trap(dungeons_data)
        elif room_type == 'boss':
            room['boss_id'] = dungeon.get('boss_id', '')

        rooms.append(room)
    return rooms

def process_chest_room(player: Dict[str, Any], room: Dict[str, Any],
                       dungeons_data: Dict[str, Any],
                       items_data: Dict[str, Any]) -> Dict[str, Any]:
    messages = []
    difficulty = room.get('difficulty', 1)

    if difficulty >= 8:
        chest_type = 'legendary'
    elif difficulty >= 5:
        chest_type = 'large'
    elif difficulty >= 3:
        chest_type = 'medium'
    else:
        chest_type = 'small'

    chest_templates = dungeons_data.get('chest_templates', {})
    chest_data = chest_templates.get(chest_type,
                                     chest_templates.get('small', {}))
    if not chest_data:
        chest_data = {
            'gold_range': [20, 60],
            'item_count_range': [1, 1],
            'experience': 50,
            'item_rarity': ['common']
        }

    gold_min, gold_max = chest_data.get('gold_range', [50, 150])
    gold_reward = random.randint(gold_min, gold_max)
    exp_reward = chest_data.get('experience', 100)

    player['gold'] = player.get('gold', 0) + gold_reward
    player['experience'] = player.get('experience', 0) + exp_reward

    messages.append({
        'text': f'You crack open the chest — {gold_reward} gold inside!',
        'color': 'var(--gold)'
    })
    messages.append({
        'text': f'+{exp_reward} experience!',
        'color': 'var(--exp-purple)'
    })

    item_count_min, item_count_max = chest_data.get('item_count_range', [1, 2])
    item_count = random.randint(item_count_min, item_count_max)
    item_rarities = chest_data.get('item_rarity', ['common'])
    items_found = []

    for _ in range(item_count):
        rarity = random.choice(item_rarities)
        possible = [(name, item) for name, item in items_data.items()
                    if isinstance(item, dict) and item.get('rarity') == rarity]
        if possible:
            name, _ = random.choice(possible)
            items_found.append(name)
            player.setdefault('inventory', []).append(name)
        else:
            bonus = random.randint(25, 75)
            player['gold'] = player.get('gold', 0) + bonus

    if items_found:
        messages.append({
            'text': f'Items found: {", ".join(items_found)}',
            'color': 'var(--gold-bright)'
        })

    return {
        'type': 'chest',
        'messages': messages,
        'gold': gold_reward,
        'exp': exp_reward,
        'items': items_found
    }

def process_trap_chest_room(player: Dict[str, Any], room: Dict[str, Any],
                            dungeons_data: Dict[str,
                                                Any], items_data: Dict[str,
                                                                       Any],
                            roll: int) -> Dict[str, Any]:
    trap = room.get('challenge', {})
    messages = []
    threshold = trap.get('threshold', 10)

    if roll >= threshold:
        messages.append({
            'text': f'You spot the trap and disarm it! (Rolled {roll})',
            'color': 'var(--green-bright)'
        })
        result = process_chest_room(player, room, dungeons_data, items_data)
        messages.extend(result['messages'])
    else:
        dmg = int(trap.get('base_damage', 20) * random.uniform(0.8, 1.2))
        player['hp'] = max(1, player.get('hp', 0) - dmg)
        messages.append({
            'text':
            f'TRAP! {trap.get("name", "Trap")} — you take {dmg} damage! (Rolled {roll})',
            'color': 'var(--red)'
        })
        if random.random() < 0.5:
            gold = random.randint(20, 80)
            player['gold'] = player.get('gold', 0) + gold
            messages.append({
                'text': f'Shaken but not broken, you find {gold} gold.',
                'color': 'var(--gold)'
            })

    return {'type': 'trap_chest', 'messages': messages}

def process_empty_room(_room: Dict[str, Any]) -> Dict[str, Any]:
    msgs = [
        'The chamber is silent. You breathe and press on.',
        'Nothing here but dust and shadow.',
        'An empty room. You find a moment of quiet.',
        'The walls carry old carvings but nothing of note.',
    ]
    small_events = [
        {
            'text': 'You find a small coin pouch — 10 gold!',
            'color': 'var(--gold)',
            'gold': 10
        },
        {
            'text': 'A cracked health vial restores 15 HP.',
            'color': 'var(--green-bright)',
            'heal': 15
        },
        None,
    ]
    event = random.choice(small_events)
    messages = [{'text': random.choice(msgs), 'color': 'var(--text-dim)'}]
    if event:
        if 'gold' in event:
            messages.append({'text': str(event['text']), 'color': str(event['color'])})
        elif 'heal' in event:
            messages.append({'text': str(event['text']), 'color': str(event['color'])})
    return {'type': 'empty', 'messages': messages}

def process_battle_room(_player: Dict[str, Any], room: Dict[str, Any],
                        enemies_data: Dict[str, Any], areas_data: Dict[str,
                                                                       Any],
                        current_area: str,
                        dungeon: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    possible: List[str] = []
    if dungeon:
        possible = dungeon.get('possible_enemies', [])
    if not possible:
        area = areas_data.get(current_area, {})
        possible = area.get('possible_enemies', [])
    if not possible:
        possible = [
            k for k in enemies_data.keys()
            if isinstance(enemies_data[k], dict)
        ][:8]
    if not possible:
        return {
            'type':
            'empty',
            'messages': [{
                'text': 'The chamber is strangely empty.',
                'color': 'var(--text-dim)'
            }]
        }

    enemy_key = random.choice(possible)
    enemy_data = enemies_data.get(enemy_key, {})
    if not isinstance(enemy_data, dict):
        return {
            'type':
            'empty',
            'messages': [{
                'text': 'The chamber is clear.',
                'color': 'var(--text-dim)'
            }]
        }

    difficulty = room.get('difficulty', 1)
    scaled = dict(enemy_data)
    scale = 0.8 + difficulty * 0.2
    scaled['key'] = enemy_key
    scaled['hp'] = int(scaled.get('hp', 50) * scale)
    scaled['max_hp'] = scaled['hp']
    scaled['attack'] = int(scaled.get('attack', 5) * scale)
    scaled['defense'] = int(scaled.get('defense', 2) * scale)
    scaled['speed'] = scaled.get('speed', 10)
    scaled['exp_reward'] = int(scaled.get('experience_reward', 30) * scale)
    scaled['gold_reward'] = max(
        1,
        int(scaled.get('gold_reward', 10)) + random.randint(-2, 8))
    scaled['loot_table'] = scaled.get('loot_table', [])

    return {
        'type':
        'battle',
        'enemy':
        scaled,
        'messages': [{
            'text': f'A {scaled.get("name", "foe")} blocks your path!',
            'color': 'var(--red)'
        }],
    }

def process_shrine_room(player: Dict[str, Any]) -> Dict[str, Any]:
    max_hp = player.get('max_hp', 100)
    max_mp = player.get('max_mp', 50)
    current_hp = player.get('hp', max_hp)
    current_mp = player.get('mp', max_mp)

    heal_amount = int(max_hp * 0.25)
    mp_amount = int(max_mp * 0.25)
    heal_amount = min(heal_amount, max_hp - current_hp)
    mp_amount = min(mp_amount, max_mp - current_mp)

    player['hp'] = current_hp + heal_amount
    player['mp'] = current_mp + mp_amount

    shrine_flavors = [
        'A ancient stone shrine hums with divine energy.',
        'Soft golden light bathes the chamber from a sacred altar.',
        'A forgotten deity blesses you from this crumbling shrine.',
        'The shrine pulses with healing warmth as you approach.',
    ]
    messages = [{'text': random.choice(shrine_flavors), 'color': 'var(--gold)'}]
    if heal_amount > 0:
        messages.append({
            'text': f'The shrine restores {heal_amount} HP!',
            'color': 'var(--green-bright)'
        })
    if mp_amount > 0:
        messages.append({
            'text': f'The shrine restores {mp_amount} MP!',
            'color': 'var(--mp-blue)'
        })
    if heal_amount == 0 and mp_amount == 0:
        messages.append({
            'text': 'You are already at full strength. The shrine nods in approval.',
            'color': 'var(--text-dim)'
        })
    return {'type': 'shrine', 'messages': messages, 'heal': heal_amount, 'mp': mp_amount}

def process_ambush_room(_player: Dict[str, Any], room: Dict[str, Any],
                        enemies_data: Dict[str, Any], areas_data: Dict[str, Any],
                        current_area: str,
                        dungeon: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    possible: List[str] = []
    if dungeon:
        possible = dungeon.get('possible_enemies', [])
    if not possible:
        area = areas_data.get(current_area, {})
        possible = area.get('possible_enemies', [])
    if not possible:
        possible = [k for k in enemies_data.keys() if isinstance(enemies_data[k], dict)][:8]
    if not possible:
        return {
            'type': 'empty',
            'messages': [{'text': 'The shadows hold nothing.', 'color': 'var(--text-dim)'}]
        }

    enemy_key = random.choice(possible)
    enemy_data = enemies_data.get(enemy_key, {})
    if not isinstance(enemy_data, dict):
        return {
            'type': 'empty',
            'messages': [{'text': 'The ambush melts away.', 'color': 'var(--text-dim)'}]
        }

    difficulty = room.get('difficulty', 1)
    scale = 1.0 + difficulty * 0.25
    scaled = dict(enemy_data)
    scaled['key'] = enemy_key
    scaled['hp'] = int(scaled.get('hp', 50) * scale)
    scaled['max_hp'] = scaled['hp']
    scaled['attack'] = int(scaled.get('attack', 5) * scale)
    scaled['defense'] = int(scaled.get('defense', 2) * scale)
    scaled['speed'] = scaled.get('speed', 10)
    scaled['exp_reward'] = int(scaled.get('experience_reward', 30) * scale * 1.5)
    scaled['gold_reward'] = max(1, int(scaled.get('gold_reward', 10) * 1.5) + random.randint(5, 15))
    scaled['loot_table'] = scaled.get('loot_table', [])
    scaled['is_ambush'] = True

    player_level = _player.get('level', 1)
    if player_level >= 10:
        level_buff = 1.0 + (player_level - 10) * 0.05
        scaled['hp'] = int(scaled['hp'] * level_buff)
        scaled['max_hp'] = scaled['hp']
        scaled['attack'] = int(scaled['attack'] * level_buff)

    return {
        'type': 'ambush',
        'enemy': scaled,
        'messages': [{
            'text': f'AMBUSH! A powerful {scaled.get("name", "foe")} leaps from the shadows!',
            'color': 'var(--red)'
        }],
    }

def process_question_room(dungeons_data: Dict[str, Any]) -> Dict[str, Any]:
    riddle = _pick_riddle(dungeons_data)
    return {
        'type':
        'question',
        'question':
        riddle.get('question', ''),
        'answer':
        riddle.get('answer', '').lower().strip(),
        'hints':
        riddle.get('hints', []),
        'success_reward':
        riddle.get('success_reward', {}),
        'failure_damage':
        riddle.get('failure_damage', 15),
        'messages': [{
            'text': 'A mystical pedestal presents a riddle...',
            'color': 'var(--gold)'
        }],
    }

def answer_question(player: Dict[str, Any], question_data: Dict[str, Any],
                    answer: str) -> Dict[str, Any]:
    correct = question_data.get('answer', '').lower().strip()
    given = answer.lower().strip()
    if given == correct or (len(given) > 2 and correct.startswith(given)):
        reward = question_data.get('success_reward', {})
        gold = reward.get('gold', 0)
        exp = reward.get('experience', 0)
        player['gold'] = player.get('gold', 0) + gold
        player['experience'] = player.get('experience', 0) + exp
        msgs = [{
            'text': 'Correct! The way forward is revealed!',
            'color': 'var(--green-bright)'
        }]
        if gold:
            msgs.append({'text': f'+{gold} gold!', 'color': 'var(--gold)'})
        if exp:
            msgs.append({
                'text': f'+{exp} experience!',
                'color': 'var(--exp-purple)'
            })
        return {'correct': True, 'messages': msgs}
    else:
        dmg = question_data.get('failure_damage', 15)
        player['hp'] = max(1, player.get('hp', 0) - dmg)
        return {
            'correct':
            False,
            'messages': [
                {
                    'text': f'Wrong! The rune sears you for {dmg} damage.',
                    'color': 'var(--red)'
                },
                {
                    'text': f'The answer was: "{correct}"',
                    'color': 'var(--text-dim)'
                },
            ],
            'player_alive':
            player['hp'] > 0,
        }

def answer_multi_choice(player: Dict[str, Any], choice_data: Dict[str, Any],
                        choice_index: int) -> Dict[str, Any]:
    options = choice_data.get('options', [])
    if choice_index < 0 or choice_index >= len(options):
        return {
            'correct': False,
            'messages': [{
                'text': 'Invalid choice.',
                'color': 'var(--red)'
            }]
        }

    chosen = options[choice_index]
    if chosen.get('correct', False):
        reward = choice_data.get('success_reward', {})
        gold = reward.get('gold', 0)
        exp = reward.get('experience', 0)
        player['gold'] = player.get('gold', 0) + gold
        player['experience'] = player.get('experience', 0) + exp
        msgs = [
            {
                'text': chosen.get('reason', 'A good choice!'),
                'color': 'var(--green-bright)'
            },
        ]
        if gold:
            msgs.append({'text': f'+{gold} gold!', 'color': 'var(--gold)'})
        if exp:
            msgs.append({
                'text': f'+{exp} experience!',
                'color': 'var(--exp-purple)'
            })
        return {'correct': True, 'messages': msgs}
    else:
        dmg = choice_data.get('failure_damage', 10)
        player['hp'] = max(1, player.get('hp', 0) - dmg)
        return {
            'correct':
            False,
            'messages': [
                {
                    'text': chosen.get('reason', 'A poor choice.'),
                    'color': 'var(--red)'
                },
                {
                    'text': f'You suffer {dmg} damage for your mistake.',
                    'color': 'var(--red)'
                },
            ],
        }

def complete_dungeon(player: Dict[str, Any],
                     dungeon: Dict[str, Any]) -> Dict[str, Any]:
    reward = dungeon.get('completion_reward', {})
    gold = reward.get('gold', 100)
    exp = reward.get('experience', 200)
    items = reward.get('items', [])
    player['gold'] = player.get('gold', 0) + gold
    player['experience'] = player.get('experience', 0) + exp
    for item in items:
        player.setdefault('inventory', []).append(item)

    msgs = [
        {
            'text': f'Dungeon Cleared: {dungeon.get("name", "the dungeon")}!',
            'color': 'var(--gold)'
        },
        {
            'text': f'Rewards: {gold} gold, {exp} experience.',
            'color': 'var(--text-light)'
        },
    ]
    if items:
        msgs.append({
            'text': f'Items received: {", ".join(items)}',
            'color': 'var(--gold-bright)'
        })

    return {'messages': msgs, 'gold': gold, 'exp': exp, 'items': items}
