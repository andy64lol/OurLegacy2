"""
Dungeon System for Our Legacy 2 - Flask Edition
Stateless dungeon functions that return result dicts.
"""
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from utilities.entities import Enemy


def get_available_dungeons(dungeons_data: Dict[str, Any], current_area: str, player_level: int) -> List[Dict[str, Any]]:
    """Return list of dungeons available in the current area."""
    all_dungeons = dungeons_data.get('dungeons', [])
    result = []
    for dungeon in all_dungeons:
        allowed_areas = dungeon.get('allowed_areas', [])
        if allowed_areas and current_area not in allowed_areas:
            continue
        difficulty = dungeon.get('difficulty', [1, 3])
        min_level = difficulty[0] * 5
        result.append({
            'id': dungeon.get('id', dungeon.get('name', '').lower().replace(' ', '_')),
            'name': dungeon.get('name', 'Unknown Dungeon'),
            'description': dungeon.get('description', ''),
            'difficulty': difficulty,
            'rooms': dungeon.get('rooms', 5),
            'min_level': min_level,
            'available': player_level >= min_level,
            'allowed_areas': allowed_areas,
        })
    return result


def generate_dungeon_rooms(dungeon: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate a list of dungeon rooms based on dungeon definition."""
    room_weights = dungeon.get('room_weights', {})
    total_rooms = dungeon.get('rooms', 5)

    if not room_weights or sum(room_weights.values()) == 0:
        room_weights = {'battle': 40, 'question': 20, 'chest': 15, 'empty': 15, 'trap_chest': 5, 'multi_choice': 5}

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
        rooms.append({
            'type': room_type,
            'room_number': i + 1,
            'difficulty': dungeon.get('difficulty', [1, 3])[0] + (i * 0.5),
        })
    return rooms


def process_chest_room(player: Dict[str, Any], room: Dict[str, Any],
                       dungeons_data: Dict[str, Any], items_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a treasure chest room. Modifies player in place."""
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
    chest_data = chest_templates.get(chest_type, chest_templates.get('small', {}))

    if not chest_data:
        chest_data = {'gold_range': [20, 60], 'item_count_range': [1, 1], 'experience': 50, 'item_rarity': ['common']}

    gold_min, gold_max = chest_data.get('gold_range', [50, 150])
    gold_reward = random.randint(gold_min, gold_max)
    exp_reward = chest_data.get('experience', 100)

    player['gold'] = player.get('gold', 0) + gold_reward
    player['experience'] = player.get('experience', 0) + exp_reward

    messages.append({'text': f'You found {gold_reward} gold!', 'color': 'var(--gold)'})
    messages.append({'text': f'You gained {exp_reward} experience!', 'color': 'var(--magenta)'})

    item_count_min, item_count_max = chest_data.get('item_count_range', [1, 2])
    item_count = random.randint(item_count_min, item_count_max)
    item_rarities = chest_data.get('item_rarity', ['common'])
    items_found = []

    for _ in range(item_count):
        rarity = random.choice(item_rarities)
        possible = [item for item in items_data.values() if item.get('rarity') == rarity]
        if possible:
            item = random.choice(possible)
            items_found.append(item.get('name', 'Unknown'))
            player.setdefault('inventory', []).append(item.get('name', 'Unknown'))
        else:
            bonus = random.randint(25, 75)
            player['gold'] = player.get('gold', 0) + bonus

    if items_found:
        messages.append({'text': f'Items found: {", ".join(items_found)}', 'color': 'var(--yellow)'})

    return {'type': 'chest', 'messages': messages, 'gold': gold_reward, 'exp': exp_reward, 'items': items_found}


def process_empty_room(room: Dict[str, Any]) -> Dict[str, Any]:
    """Process an empty room."""
    msgs = [
        "The room is empty... You rest briefly.",
        "Nothing here but shadows and silence.",
        "An empty chamber. You press forward.",
    ]
    return {'type': 'empty', 'messages': [{'text': random.choice(msgs), 'color': 'var(--text-dim)'}]}


def process_battle_room(player: Dict[str, Any], room: Dict[str, Any], enemies_data: Dict[str, Any],
                        areas_data: Dict[str, Any], current_area: str) -> Dict[str, Any]:
    """Prepare a battle room encounter. Returns enemy dict to fight."""
    area = areas_data.get(current_area, {})
    possible = area.get('possible_enemies', [])
    if not possible:
        possible = [k for k in enemies_data.keys()][:5]
    if not possible:
        return {'type': 'empty', 'messages': [{'text': 'No enemies found. You proceed safely.', 'color': 'var(--text-dim)'}]}

    enemy_key = random.choice(possible)
    enemy_data = enemies_data.get(enemy_key)
    if not enemy_data:
        return {'type': 'empty', 'messages': [{'text': 'No enemies found. You proceed safely.', 'color': 'var(--text-dim)'}]}

    difficulty = room.get('difficulty', 1)
    scaled = dict(enemy_data)
    scaled['hp'] = int(scaled.get('hp', 50) * (0.8 + difficulty * 0.2))
    scaled['attack'] = int(scaled.get('attack', 5) * (0.8 + difficulty * 0.2))
    scaled['defense'] = int(scaled.get('defense', 2) * (0.8 + difficulty * 0.2))

    return {
        'type': 'battle',
        'enemy': scaled,
        'messages': [{'text': f'A {scaled.get("name", "enemy")} blocks your path!', 'color': 'var(--red)'}],
    }


def process_question_room(dungeons_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a question room challenge."""
    templates = dungeons_data.get('challenge_templates', {})
    q_template = templates.get('question', {})
    types = q_template.get('types', [])
    if not types:
        return {'type': 'empty', 'messages': [{'text': 'The mystical pedestal is silent.', 'color': 'var(--text-dim)'}]}

    question = random.choice(types)
    return {
        'type': 'question',
        'question': question.get('question', ''),
        'answer': question.get('answer', '').lower(),
        'hints': question.get('hints', []),
        'max_attempts': question.get('max_attempts', 3),
        'success_reward': question.get('success_reward', {}),
        'failure_damage': question.get('failure_damage', 15),
        'messages': [{'text': 'A mystical pedestal presents a riddle...', 'color': 'var(--yellow)'}],
    }


def answer_question(player: Dict[str, Any], question_data: Dict[str, Any], answer: str) -> Dict[str, Any]:
    """Check a question room answer. Returns result."""
    correct = question_data.get('answer', '').lower().strip()
    if answer.lower().strip() == correct:
        reward = question_data.get('success_reward', {})
        gold = reward.get('gold', 0)
        exp = reward.get('experience', 0)
        player['gold'] = player.get('gold', 0) + gold
        player['experience'] = player.get('experience', 0) + exp
        msgs = [{'text': 'Correct! The way forward is revealed!', 'color': 'var(--green-bright)'}]
        if gold:
            msgs.append({'text': f'Gained {gold} gold!', 'color': 'var(--gold)'})
        if exp:
            msgs.append({'text': f'Gained {exp} experience!', 'color': 'var(--magenta)'})
        return {'correct': True, 'messages': msgs}
    else:
        dmg = question_data.get('failure_damage', 15)
        player['hp'] = max(0, player.get('hp', 0) - dmg)
        return {
            'correct': False,
            'messages': [{'text': f'Wrong! You take {dmg} damage.', 'color': 'var(--red)'}],
            'player_alive': player['hp'] > 0,
        }


def complete_dungeon(player: Dict[str, Any], dungeon: Dict[str, Any]) -> Dict[str, Any]:
    """Handle dungeon completion rewards."""
    reward = dungeon.get('completion_reward', {})
    gold = reward.get('gold', 100)
    exp = reward.get('experience', 200)
    player['gold'] = player.get('gold', 0) + gold
    player['experience'] = player.get('experience', 0) + exp
    return {
        'messages': [
            {'text': f'You completed {dungeon.get("name", "the dungeon")}!', 'color': 'var(--gold)'},
            {'text': f'Rewards: {gold} gold, {exp} experience.', 'color': 'var(--text-light)'},
        ],
        'gold': gold,
        'exp': exp,
    }
