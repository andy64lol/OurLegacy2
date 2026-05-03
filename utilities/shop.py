from typing import Dict, List, Any

def get_shop_items(shop_data: Dict[str, Any], items_data: Dict[str, Any],
                   player: Dict[str, Any]) -> Dict[str, Any]:
    items = shop_data.get('items', [])
    max_buy = shop_data.get('max_buy', 99)
    item_details = []

    for item_id in items:
        if item_id not in items_data:
            continue
        item = items_data[item_id]
        owned_count = player.get('inventory', []).count(item_id)
        can_buy_more = owned_count < max_buy
        price = item.get('price', item.get('value', 0))
        item_details.append({
            'id': item_id,
            'name': item.get('name', item_id),
            'type': item.get('type', 'misc'),
            'rarity': item.get('rarity', 'common'),
            'price': price,
            'description': item.get('description', ''),
            'owned_count': owned_count,
            'can_buy_more': can_buy_more,
            'can_afford': player.get('gold', 0) >= price,
        })

    return {
        'shop_name': shop_data.get('name', 'Shop'),
        'welcome_message': shop_data.get('welcome_message', ''),
        'max_buy': max_buy,
        'items': item_details,
        'player_gold': player.get('gold', 0),
    }

def buy_item(player: Dict[str, Any], item_id: str, items_data: Dict[str, Any],
             shop_data: Dict[str, Any]) -> Dict[str, Any]:
    if item_id not in items_data:
        return {
            'ok': False,
            'message': f'Item {item_id} not found.',
            'color': 'var(--red)'
        }

    item = items_data[item_id]
    price = item.get('price', item.get('value', 0))
    max_buy = shop_data.get('max_buy', 99)
    owned = player.get('inventory', []).count(item_id)

    if owned >= max_buy:
        return {
            'ok': False,
            'message':
            f'You already own the maximum ({max_buy}) of this item.',
            'color': 'var(--red)'
        }
    if player.get('gold', 0) < price:
        return {
            'ok': False,
            'message':
            f'Not enough gold. Need {price}, have {player.get("gold", 0)}.',
            'color': 'var(--red)'
        }

    player['gold'] = player.get('gold', 0) - price
    player.setdefault('inventory', []).append(item_id)
    return {
        'ok': True,
        'message': f'Purchased {item.get("name", item_id)} for {price} gold.',
        'color': 'var(--green-bright)'
    }

def sell_item(player: Dict[str, Any], item_id: str,
              items_data: Dict[str, Any]) -> Dict[str, Any]:
    inventory = player.get('inventory', [])
    if item_id not in inventory:
        return {
            'ok': False,
            'message': 'You do not have that item.',
            'color': 'var(--red)'
        }

    equipment = player.get('equipment', {})
    if item_id in equipment.values():
        return {
            'ok': False,
            'message': 'Unequip the item before selling it.',
            'color': 'var(--red)'
        }

    item = items_data.get(item_id, {})
    price = item.get('price', item.get('value', 10))
    sell_price = max(1, price // 2)

    inventory.remove(item_id)
    player['inventory'] = inventory
    player['gold'] = player.get('gold', 0) + sell_price

    return {
        'ok': True,
        'message': f'Sold {item.get("name", item_id)} for {sell_price} gold.',
        'color': 'var(--gold)'
    }

def get_sellable_inventory(player: Dict[str, Any],
                           items_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    equipment_items = set(v for v in player.get('equipment', {}).values() if v)
    sellable = []
    for item_id in player.get('inventory', []):
        item = items_data.get(item_id, {})
        price = item.get('price', item.get('value', 10))
        sell_price = max(1, price // 2)
        sellable.append({
            'id': item_id,
            'name': item.get('name', item_id),
            'rarity': item.get('rarity', 'common'),
            'sell_price': sell_price,
            'equipped': item_id in equipment_items,
        })
    return sellable

def get_housing_shop_items(shop_data: Dict[str, Any], housing_data: Dict[str,
                                                                         Any],
                           player: Dict[str, Any]) -> Dict[str, Any]:
    items = shop_data.get('items', [])
    owned_set = set(player.get('housing_owned', []))
    item_details = []

    for item_id in items:
        if item_id not in housing_data:
            continue
        item = housing_data[item_id]
        price = item.get('price', 100)
        item_details.append({
            'id': item_id,
            'name': item.get('name', item_id),
            'type': item.get('type', 'decoration'),
            'rarity': item.get('rarity', 'common'),
            'price': price,
            'description': item.get('description', ''),
            'comfort_points': item.get('comfort_points', 0),
            'owned': item_id in owned_set,
            'can_afford': player.get('gold', 0) >= price,
        })

    return {
        'shop_name': shop_data.get('name', 'Housing Shop'),
        'welcome_message': shop_data.get('welcome_message', ''),
        'items': item_details,
        'player_gold': player.get('gold', 0),
    }
