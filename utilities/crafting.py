"""
Crafting System for Our Legacy 2 - Flask Edition
Pure functions that operate on player dicts.
"""
from typing import Dict, List, Any, Optional


def get_crafting_materials(player: Dict[str, Any], crafting_data: Dict[str, Any]) -> Dict[str, int]:
    """Return dict of material_id -> count in player inventory."""
    material_categories = crafting_data.get('material_categories', {})
    all_materials: set = set()
    for materials in material_categories.values():
        all_materials.update(materials)

    counts: Dict[str, int] = {}
    for item in player.get('inventory', []):
        if item in all_materials:
            counts[item] = counts.get(item, 0) + 1
    return counts


def get_recipes(crafting_data: Dict[str, Any], category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return list of recipe dicts, optionally filtered by category."""
    recipes = crafting_data.get('recipes', {})
    result = []
    for rid, rdata in recipes.items():
        if category and rdata.get('category') != category:
            continue
        result.append({
            'id': rid,
            'name': rdata.get('name', rid),
            'category': rdata.get('category', 'Unknown'),
            'rarity': rdata.get('rarity', 'common'),
            'description': rdata.get('description', ''),
            'materials': rdata.get('materials', {}),
            'output': rdata.get('output', {}),
            'skill_requirement': rdata.get('skill_requirement', 1),
        })
    return result


def check_recipe_craftable(player: Dict[str, Any], recipe: Dict[str, Any]) -> Dict[str, Any]:
    """Check if player can craft a recipe. Returns {'ok': bool, 'missing': list}."""
    level = player.get('level', 1)
    req = recipe.get('skill_requirement', 1)
    if level < req:
        return {'ok': False, 'missing': [], 'reason': f'Level {req} required (you are level {level}).'}

    inventory = player.get('inventory', [])
    missing = []
    for material, qty in recipe.get('materials', {}).items():
        have = inventory.count(material)
        if have < qty:
            missing.append({'material': material, 'need': qty, 'have': have})

    return {'ok': len(missing) == 0, 'missing': missing, 'reason': None}


def craft_item(player: Dict[str, Any], recipe_id: str, crafting_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Craft an item from a recipe. Modifies player dict in place.
    Returns {'ok': bool, 'message': str, 'items_crafted': list}
    """
    recipes = crafting_data.get('recipes', {})
    recipe = recipes.get(recipe_id)
    if not recipe:
        return {'ok': False, 'message': f'Recipe {recipe_id} not found.', 'items_crafted': []}

    check = check_recipe_craftable(player, recipe)
    if not check['ok']:
        if check.get('reason'):
            return {'ok': False, 'message': check['reason'], 'items_crafted': []}
        missing_str = ', '.join(f"{m['need'] - m['have']}x {m['material']}" for m in check['missing'])
        return {'ok': False, 'message': f'Missing materials: {missing_str}', 'items_crafted': []}

    inventory = player.get('inventory', [])
    for material, qty in recipe.get('materials', {}).items():
        for _ in range(qty):
            inventory.remove(material)

    items_crafted = []
    for item, qty in recipe.get('output', {}).items():
        for _ in range(qty):
            inventory.append(item)
        items_crafted.append({'item': item, 'quantity': qty})

    player['inventory'] = inventory
    name = recipe.get('name', recipe_id)
    items_str = ', '.join(f"{ic['quantity']}x {ic['item']}" for ic in items_crafted)
    return {
        'ok': True,
        'message': f"Successfully crafted {name}! Received: {items_str}",
        'items_crafted': items_crafted,
        'recipe_name': name,
    }


def get_recipe_categories(crafting_data: Dict[str, Any]) -> List[str]:
    """Return list of unique recipe categories."""
    recipes = crafting_data.get('recipes', {})
    cats = set()
    for rdata in recipes.values():
        cat = rdata.get('category')
        if cat:
            cats.add(cat)
    return sorted(cats)
