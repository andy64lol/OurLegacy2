from typing import Dict, List, Any

BUILDING_TYPES = {
    "house": {
        "label": "House",
        "slots": 3
    },
    "decoration": {
        "label": "Decoration",
        "slots": 10
    },
    "fencing": {
        "label": "Fencing",
        "slots": 1
    },
    "garden": {
        "label": "Garden",
        "slots": 3
    },
    "farm": {
        "label": "Farm",
        "slots": 2
    },
    "farming": {
        "label": "Farming",
        "slots": 2
    },
    "training_place": {
        "label": "Training Place",
        "slots": 3
    },
}

def get_building_status(player: Dict[str, Any],
                        housing_data: Dict[str, Any]) -> Dict[str, Any]:
    building_slots = player.get('building_slots', {})
    slots_info = {}

    for b_type, info in BUILDING_TYPES.items():
        type_slots = []
        for i in range(1, info['slots'] + 1):
            slot_id = f"{b_type}_{i}"
            item_id = building_slots.get(slot_id)
            item_info = None
            if item_id and item_id in housing_data:
                h = housing_data[item_id]
                item_info = {
                    'id': item_id,
                    'name': h.get('name', item_id),
                    'rarity': h.get('rarity', 'common'),
                    'comfort_points': h.get('comfort_points', 0),
                }
            type_slots.append({'slot_id': slot_id, 'item': item_info})
        slots_info[b_type] = {
            'label': info['label'],
            'max_slots': info['slots'],
            'slots': type_slots
        }

    return {
        'building_slots': slots_info,
        'comfort_points': player.get('comfort_points', 0),
        'housing_owned': player.get('housing_owned', []),
    }

def get_available_slots_for_type(player: Dict[str, Any],
                                 item_type: str) -> List[str]:
    info = BUILDING_TYPES.get(item_type, {})
    if not info:
        return []
    building_slots = player.get('building_slots', {})
    empty = []
    for i in range(1, info['slots'] + 1):
        slot_id = f"{item_type}_{i}"
        if not building_slots.get(slot_id):
            empty.append(slot_id)
    return empty

def place_housing_item(player: Dict[str, Any], item_id: str, slot_id: str,
                       housing_data: Dict[str, Any]) -> Dict[str, Any]:
    if item_id not in player.get('housing_owned', []):
        return {'ok': False, 'message': 'You do not own that structure.'}

    h_data = housing_data.get(item_id)
    if not h_data:
        return {'ok': False, 'message': 'Housing item data not found.'}

    building_slots = player.setdefault('building_slots', {})
    old_item_id = building_slots.get(slot_id)

    if old_item_id:
        old_data = housing_data.get(old_item_id, {})
        player['comfort_points'] = max(
            0,
            player.get('comfort_points', 0) -
            old_data.get('comfort_points', 0))

    building_slots[slot_id] = item_id
    comfort = h_data.get('comfort_points', 0)
    player['comfort_points'] = player.get('comfort_points', 0) + comfort
    player['building_slots'] = building_slots

    name = h_data.get('name', item_id)
    return {
        'ok':
        True,
        'message':
        f'Placed {name} in slot {slot_id}. Comfort: +{comfort}. Total: {player["comfort_points"]}'
    }

def remove_housing_item_slot(player: Dict[str, Any], slot_id: str,
                             housing_data: Dict[str, Any]) -> Dict[str, Any]:
    building_slots = player.get('building_slots', {})
    item_id = building_slots.get(slot_id)
    if not item_id:
        return {'ok': False, 'message': 'No item in that slot.'}

    h_data = housing_data.get(item_id, {})
    comfort = h_data.get('comfort_points', 0)
    player['comfort_points'] = max(0,
                                   player.get('comfort_points', 0) - comfort)
    building_slots[slot_id] = None
    player['building_slots'] = building_slots

    name = h_data.get('name', item_id)
    return {'ok': True, 'message': f'Removed {name} from slot {slot_id}.'}

def get_home_status(player: Dict[str, Any],
                    housing_data: Dict[str, Any]) -> Dict[str, Any]:
    building_slots = player.get('building_slots', {})
    placed = [item_id for item_id in building_slots.values() if item_id]
    item_comforts: Dict[str, Dict[str, Any]] = {}

    for item_id in placed:
        h_data = housing_data.get(item_id, {})
        name = h_data.get('name', item_id)
        comfort = h_data.get('comfort_points', 0)
        if name not in item_comforts:
            item_comforts[name] = {'count': 0, 'total_comfort': 0}
        item_comforts[name]['count'] += 1
        item_comforts[name]['total_comfort'] += comfort

    sorted_items = sorted(item_comforts.items(),
                          key=lambda x: x[1]['total_comfort'],
                          reverse=True)

    return {
        'comfort_points': player.get('comfort_points', 0),
        'total_placed': len(placed),
        'unique_placed': len(set(placed)),
        'top_items': [{
            'name': n,
            **info
        } for n, info in sorted_items[:10]],
    }

def plant_crop(player: Dict[str, Any], farm_slot_id: str, crop_key: str,
               farming_data: Dict[str, Any]) -> Dict[str, Any]:
    building_slots = player.get('building_slots', {})
    if not building_slots.get(farm_slot_id):
        return {
            'ok': False,
            'message': 'You need to build a farm in that slot first.'
        }

    crops = player.setdefault('crops', {})
    if crops.get(farm_slot_id):
        crop_info = crops[farm_slot_id]
        if crop_info.get('ready'):
            return {
                'ok': False,
                'message': 'There is a ready crop here. Harvest it first!'
            }
        return {'ok': False, 'message': 'A crop is already growing here.'}

    crops_data = farming_data.get('crops', {})
    crop_data = crops_data.get(crop_key)
    if not crop_data:
        return {'ok': False, 'message': f'Unknown crop: {crop_key}'}

    gold_cost = crop_data.get('seed_cost', 10)
    if player.get('gold', 0) < gold_cost:
        return {
            'ok': False,
            'message': f'Not enough gold. Seeds cost {gold_cost} gold.'
        }

    player['gold'] = player.get('gold', 0) - gold_cost
    crops[farm_slot_id] = {
        'crop_key': crop_key,
        'name': crop_data.get('name', crop_key),
        'growth_time': crop_data.get('growth_time', 5),
        'turns': 0,
        'ready': False,
        'yield_item': crop_data.get('yield_item', crop_key),
        'yield_quantity': crop_data.get('yield_quantity', 1),
    }
    player['crops'] = crops

    return {
        'ok': True,
        'message':
        f'Planted {crop_data.get("name", crop_key)} in {farm_slot_id}.'
    }

def harvest_crop(player: Dict[str, Any], farm_slot_id: str) -> Dict[str, Any]:
    crops = player.get('crops', {})
    crop_info = crops.get(farm_slot_id)
    if not crop_info:
        return {'ok': False, 'message': 'No crop planted here.'}
    if not crop_info.get('ready'):
        return {'ok': False, 'message': 'Crop is not ready yet.'}

    yield_item = crop_info.get('yield_item', 'Unknown')
    qty = crop_info.get('yield_quantity', 1)
    for _ in range(qty):
        player.setdefault('inventory', []).append(yield_item)

    crops[farm_slot_id] = None
    player['crops'] = crops

    return {
        'ok': True,
        'message': f'Harvested {qty}x {yield_item}!',
        'item': yield_item,
        'quantity': qty
    }
