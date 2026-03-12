"""
Our Legacy 2 - Web Interface (Streamlit)
A web-based interface for the Our Legacy 2 RPG game.
"""

import streamlit as st
import json
import random
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Page configuration
st.set_page_config(
    page_title="Our Legacy 2",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for RPG theme
st.markdown("""
<style>
    .stApp {
        background-color: #1a1612;
        color: #d4c4a8;
    }
    .main-title {
        color: #ffd700;
        text-align: center;
        font-size: 2.5em;
        text-shadow: 2px 2px 4px #000;
        margin-bottom: 0;
    }
    .sub-title {
        color: #b87333;
        text-align: center;
        font-size: 1.1em;
        margin-top: 0;
    }
    .stat-box {
        background: #2a2420;
        border: 1px solid #6a6050;
        border-radius: 5px;
        padding: 8px 12px;
        margin: 4px 0;
    }
    .message-log {
        background: #0d0a08;
        border: 1px solid #3a342a;
        border-radius: 5px;
        padding: 10px;
        height: 300px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.9em;
    }
    .hp-bar { color: #cc3333; }
    .mp-bar { color: #3366cc; }
    .exp-bar { color: #9966cc; }
    .gold { color: #ffd700; }
    .rarity-common { color: #a0a0a0; }
    .rarity-uncommon { color: #50cc50; }
    .rarity-rare { color: #4088cc; }
    .rarity-epic { color: #c040ff; }
    .rarity-legendary { color: #ffdd00; }
    div[data-testid="stSidebar"] {
        background-color: #0d0a08;
    }
</style>
""", unsafe_allow_html=True)


# ─── Data Loading ───────────────────────────────────────────────────────────

@st.cache_data
def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def get_game_data():
    return {
        'classes': load_json('data/classes.json'),
        'areas': load_json('data/areas.json'),
        'enemies': load_json('data/enemies.json'),
        'items': load_json('data/items.json'),
        'missions': load_json('data/missions.json'),
        'bosses': load_json('data/bosses.json'),
        'spells': load_json('data/spells.json'),
        'shops': load_json('data/shops.json'),
        'companions': load_json('data/companions.json'),
        'crafting': load_json('data/crafting.json'),
    }


# ─── Session State Initialization ───────────────────────────────────────────

def init_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.screen = 'welcome'   # welcome | create | game | battle
        st.session_state.player = None
        st.session_state.messages = []
        st.session_state.current_area = 'starting_village'
        st.session_state.battle_enemy = None
        st.session_state.battle_log = []
        st.session_state.completed_missions = []
        st.session_state.mission_progress = {}
        st.session_state.visited_areas = set()
        st.session_state.data = get_game_data()
        st.session_state.shop_items = []
        st.session_state.active_tab = 'explore'


def add_message(msg, color=None):
    if color:
        st.session_state.messages.append(f'<span style="color:{color}">{msg}</span>')
    else:
        st.session_state.messages.append(msg)
    if len(st.session_state.messages) > 100:
        st.session_state.messages = st.session_state.messages[-100:]


# ─── Player / Character ─────────────────────────────────────────────────────

def create_player(name, cls):
    data = st.session_state.data
    cls_data = data['classes'].get(cls, {})
    stats = cls_data.get('base_stats', {'hp': 100, 'mp': 50, 'attack': 10, 'defense': 8, 'speed': 10})
    starting_items = cls_data.get('starting_items', ['Health Potion'])
    gold = cls_data.get('starting_gold', 100)

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
        'gold': gold,
        'inventory': list(starting_items),
        'equipment': {'weapon': None, 'armor': None, 'offhand': None},
        'companions': [],
        'active_buffs': [],
        'rank': 'F-tier Adventurer',
        'level_up_bonuses': cls_data.get('level_up_bonuses', {'hp': 10, 'mp': 2, 'attack': 2, 'defense': 1, 'speed': 1}),
    }
    return player


def gain_experience(player, amount):
    player['experience'] += amount
    leveled = False
    while player['experience'] >= player['experience_to_next']:
        player['experience'] -= player['experience_to_next']
        player['level'] += 1
        player['experience_to_next'] = int(player['experience_to_next'] * 1.5)
        bonuses = player.get('level_up_bonuses', {})
        player['max_hp'] += bonuses.get('hp', 10)
        player['max_mp'] += bonuses.get('mp', 2)
        player['attack'] += bonuses.get('attack', 2)
        player['defense'] += bonuses.get('defense', 1)
        player['speed'] += bonuses.get('speed', 1)
        player['hp'] = player['max_hp']
        player['mp'] = player['max_mp']
        leveled = True
        update_rank(player)
    return leveled


def update_rank(player):
    level = player['level']
    if level < 5:
        player['rank'] = 'F-tier Adventurer'
    elif level < 10:
        player['rank'] = 'E-tier Adventurer'
    elif level < 15:
        player['rank'] = 'D-tier Adventurer'
    elif level < 20:
        player['rank'] = 'C-tier Adventurer'
    elif level < 30:
        player['rank'] = 'B-tier Adventurer'
    elif level < 40:
        player['rank'] = 'A-tier Adventurer'
    elif level < 50:
        player['rank'] = 'S-tier Adventurer'
    else:
        player['rank'] = 'Legendary Hero'


# ─── Battle System ──────────────────────────────────────────────────────────

def start_battle(enemy_key):
    data = st.session_state.data
    enemy_data = data['enemies'].get(enemy_key, {})
    if not enemy_data:
        add_message("No enemy found to fight.", '#cc4444')
        return

    # Scale enemy with player level
    player = st.session_state.player
    lvl = player['level']
    scale = 1 + (lvl - 1) * 0.1

    enemy = {
        'key': enemy_key,
        'name': enemy_data.get('name', enemy_key.title()),
        'hp': int(enemy_data.get('hp', 50) * scale),
        'max_hp': int(enemy_data.get('hp', 50) * scale),
        'attack': int(enemy_data.get('attack', 10) * scale),
        'defense': int(enemy_data.get('defense', 5) * scale),
        'speed': enemy_data.get('speed', 10),
        'exp_reward': int(enemy_data.get('experience_reward', 30) * scale),
        'gold_reward': int(enemy_data.get('gold_reward', 10) + random.randint(-5, 15)),
        'loot_table': enemy_data.get('loot_table', []),
    }
    st.session_state.battle_enemy = enemy
    st.session_state.battle_log = [f"⚔️ A {enemy['name']} appears! (HP: {enemy['hp']})"]
    st.session_state.screen = 'battle'


def battle_attack():
    player = st.session_state.player
    enemy = st.session_state.battle_enemy
    log = st.session_state.battle_log

    # Player attacks
    p_dmg = max(1, player['attack'] - enemy['defense'] + random.randint(-3, 5))
    crit = random.random() < 0.1
    if crit:
        p_dmg = int(p_dmg * 1.5)
        log.append(f"💥 Critical hit! You deal {p_dmg} damage to {enemy['name']}!")
    else:
        log.append(f"⚔️ You deal {p_dmg} damage to {enemy['name']}.")
    enemy['hp'] = max(0, enemy['hp'] - p_dmg)

    if enemy['hp'] <= 0:
        _handle_victory()
        return

    # Enemy attacks
    e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(-2, 4))
    player['hp'] = max(0, player['hp'] - e_dmg)
    log.append(f"🗡️ {enemy['name']} deals {e_dmg} damage to you.")

    if player['hp'] <= 0:
        log.append("💀 You have been defeated...")
        player['hp'] = int(player['max_hp'] * 0.3)
        log.append(f"You wake up with {player['hp']} HP.")
        st.session_state.screen = 'game'


def battle_defend():
    player = st.session_state.player
    enemy = st.session_state.battle_enemy
    log = st.session_state.battle_log

    log.append("🛡️ You take a defensive stance, reducing incoming damage!")
    e_dmg = max(0, enemy['attack'] - player['defense'] * 2 + random.randint(-2, 2))
    player['hp'] = max(0, player['hp'] - e_dmg)
    log.append(f"🗡️ {enemy['name']} deals {e_dmg} damage (reduced).")

    if player['hp'] <= 0:
        player['hp'] = int(player['max_hp'] * 0.3)
        log.append(f"You collapse but survive with {player['hp']} HP.")
        st.session_state.screen = 'game'


def battle_use_item(item_name):
    player = st.session_state.player
    enemy = st.session_state.battle_enemy
    log = st.session_state.battle_log

    if item_name in player['inventory']:
        player['inventory'].remove(item_name)
        if 'Health Potion' in item_name or 'health' in item_name.lower():
            heal = random.randint(30, 60)
            if 'Large' in item_name or 'Greater' in item_name:
                heal = random.randint(60, 120)
            player['hp'] = min(player['max_hp'], player['hp'] + heal)
            log.append(f"💊 You used {item_name} and restored {heal} HP.")
        elif 'Mana Potion' in item_name or 'mana' in item_name.lower():
            restore = random.randint(20, 40)
            player['mp'] = min(player['max_mp'], player['mp'] + restore)
            log.append(f"🔵 You used {item_name} and restored {restore} MP.")
        else:
            log.append(f"📦 You used {item_name}.")

        # Enemy counter-attack
        e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(-2, 4))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(f"🗡️ {enemy['name']} deals {e_dmg} damage while you fumble with the item.")
    else:
        log.append("You don't have that item.")


def battle_flee():
    log = st.session_state.battle_log
    enemy = st.session_state.battle_enemy
    player = st.session_state.player

    if random.random() < 0.6:
        log.append("🏃 You successfully flee from battle!")
        add_message(f"Fled from {enemy['name']}.", '#ccaa33')
        st.session_state.screen = 'game'
    else:
        log.append("🚫 Couldn't escape!")
        e_dmg = max(1, enemy['attack'] - player['defense'] + random.randint(0, 5))
        player['hp'] = max(0, player['hp'] - e_dmg)
        log.append(f"🗡️ {enemy['name']} deals {e_dmg} damage as you try to flee.")
        if player['hp'] <= 0:
            player['hp'] = int(player['max_hp'] * 0.3)
            log.append(f"You collapse. You wake up with {player['hp']} HP.")
            st.session_state.screen = 'game'


def _handle_victory():
    player = st.session_state.player
    enemy = st.session_state.battle_enemy
    log = st.session_state.battle_log

    log.append(f"✅ You defeated {enemy['name']}!")
    exp = enemy['exp_reward']
    gold = enemy['gold_reward']
    log.append(f"📊 Gained {exp} EXP and {gold} gold!")

    player['gold'] += gold
    leveled = gain_experience(player, exp)

    if leveled:
        log.append(f"🎉 LEVEL UP! You are now level {player['level']}!")
        add_message(f"Level Up! Now level {player['level']}!", '#ffd700')

    # Loot drop
    loot = enemy.get('loot_table', [])
    if loot and random.random() < 0.4:
        item = random.choice(loot)
        player['inventory'].append(item)
        log.append(f"🎁 Loot: {item}!")

    add_message(f"Defeated {enemy['name']}! +{exp} EXP, +{gold} gold", '#50cc50')
    st.session_state.screen = 'game'


# ─── Exploration ─────────────────────────────────────────────────────────────

def explore_area():
    player = st.session_state.player
    area_key = st.session_state.current_area
    data = st.session_state.data
    area = data['areas'].get(area_key, {})

    st.session_state.visited_areas.add(area_key)
    possible_enemies = area.get('possible_enemies', [])

    # Random encounter chance
    roll = random.random()
    if possible_enemies and roll < 0.6:
        enemy_key = random.choice(possible_enemies)
        add_message(f"You encountered a {enemy_key.replace('_', ' ').title()}!", '#cc3333')
        start_battle(enemy_key)
    elif roll < 0.75:
        # Find gold/items
        gold_found = random.randint(5, 30)
        player['gold'] += gold_found
        add_message(f"You found {gold_found} gold while exploring!", '#ffd700')
    elif roll < 0.85:
        # Find a random healing
        heal = random.randint(10, 30)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        add_message(f"You found a herb and restored {heal} HP.", '#50cc50')
    else:
        add_message("You explore the area but find nothing of interest.", '#8a8070')


def rest():
    player = st.session_state.player
    area_key = st.session_state.current_area
    data = st.session_state.data
    area = data['areas'].get(area_key, {})

    if not area.get('can_rest', False):
        add_message("There is nowhere to rest here.", '#cc4444')
        return

    cost = area.get('rest_cost', 10)
    if player['gold'] < cost:
        add_message(f"You need {cost} gold to rest here.", '#cc4444')
        return

    player['gold'] -= cost
    player['hp'] = player['max_hp']
    player['mp'] = player['max_mp']
    add_message(f"You rest and recover fully. (-{cost} gold)", '#50cc50')


def travel_to(area_key):
    data = st.session_state.data
    current = data['areas'].get(st.session_state.current_area, {})
    connections = current.get('connections', [])

    if area_key in connections:
        st.session_state.current_area = area_key
        area = data['areas'].get(area_key, {})
        add_message(f"You travel to {area.get('name', area_key.replace('_', ' ').title())}.", '#b87333')
        st.session_state.visited_areas.add(area_key)
    else:
        add_message("You can't travel there directly from here.", '#cc4444')


def visit_shop():
    area_key = st.session_state.current_area
    data = st.session_state.data
    area = data['areas'].get(area_key, {})
    shops = area.get('shops', [])

    if not shops:
        add_message("There is no shop here.", '#cc4444')
        return

    shop_key = shops[0]
    shop_data = data['shops'].get(shop_key, {})
    items_for_sale = shop_data.get('items', [])

    if not items_for_sale:
        # Fallback: show some common items
        items_for_sale = ['Health Potion', 'Mana Potion', 'Iron Sword', 'Leather Armor']

    st.session_state.shop_items = items_for_sale
    st.session_state.active_tab = 'shop'
    add_message(f"You enter the {shop_data.get('name', 'Shop')}.", '#b87333')


def buy_item(item_name):
    player = st.session_state.player
    data = st.session_state.data
    item_data = data['items'].get(item_name, {})
    price = item_data.get('buy_price', item_data.get('value', 20))

    if player['gold'] < price:
        add_message(f"Not enough gold! You need {price} gold.", '#cc4444')
        return

    player['gold'] -= price
    player['inventory'].append(item_name)
    add_message(f"Bought {item_name} for {price} gold.", '#50cc50')


def sell_item(item_name):
    player = st.session_state.player
    data = st.session_state.data

    if item_name not in player['inventory']:
        return

    item_data = data['items'].get(item_name, {})
    sell_price = int(item_data.get('buy_price', item_data.get('value', 10)) * 0.5)
    sell_price = max(1, sell_price)

    player['inventory'].remove(item_name)
    player['gold'] += sell_price
    add_message(f"Sold {item_name} for {sell_price} gold.", '#ffd700')


def use_item(item_name):
    player = st.session_state.player

    if item_name not in player['inventory']:
        return

    lower = item_name.lower()
    if 'health' in lower or 'potion' in lower and 'mana' not in lower:
        heal = random.randint(30, 60)
        if 'large' in lower or 'greater' in lower:
            heal = random.randint(60, 120)
        player['hp'] = min(player['max_hp'], player['hp'] + heal)
        player['inventory'].remove(item_name)
        add_message(f"Used {item_name}. Restored {heal} HP.", '#50cc50')
    elif 'mana' in lower:
        restore = random.randint(20, 40)
        player['mp'] = min(player['max_mp'], player['mp'] + restore)
        player['inventory'].remove(item_name)
        add_message(f"Used {item_name}. Restored {restore} MP.", '#3366cc')
    else:
        add_message(f"You can't use {item_name} here.", '#8a8070')


# ─── UI Helpers ─────────────────────────────────────────────────────────────

def progress_bar(current, maximum, color='#cc3333', width=200):
    pct = max(0, min(1, current / maximum)) * 100
    return f"""<div style="background:#3a342a;border-radius:3px;height:14px;width:100%;border:1px solid #6a6050;">
  <div style="background:{color};height:100%;width:{pct:.1f}%;border-radius:3px;"></div>
</div>"""


def render_stat_panel():
    p = st.session_state.player
    if not p:
        return

    st.markdown(f"**{p['name']}** — *{p['class']}*")
    st.markdown(f"🏆 {p['rank']} | Level {p['level']}")
    st.markdown(f"❤️ HP: {p['hp']}/{p['max_hp']}")
    st.markdown(progress_bar(p['hp'], p['max_hp'], '#cc3333'), unsafe_allow_html=True)
    st.markdown(f"🔵 MP: {p['mp']}/{p['max_mp']}")
    st.markdown(progress_bar(p['mp'], p['max_mp'], '#3366cc'), unsafe_allow_html=True)
    st.markdown(f"⭐ EXP: {p['experience']}/{p['experience_to_next']}")
    st.markdown(progress_bar(p['experience'], p['experience_to_next'], '#9966cc'), unsafe_allow_html=True)
    st.markdown(f"💰 Gold: **{p['gold']}**")
    st.markdown("---")
    st.markdown(f"⚔️ ATK: {p['attack']} | 🛡️ DEF: {p['defense']} | 💨 SPD: {p['speed']}")


# ─── Screens ─────────────────────────────────────────────────────────────────

def screen_welcome():
    st.markdown('<h1 class="main-title">⚔️ Our Legacy 2</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">A Comprehensive Fantasy RPG Adventure</p>', unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("data/assets/game_title_our_legacy_2.png", use_container_width=True)
        st.markdown("### Welcome, Adventurer!")
        st.markdown("""
        Embark on an epic journey through diverse lands.  
        Fight monsters, complete missions, craft items, and become a legend!
        """)
        st.markdown("")
        if st.button("🗡️ New Game", use_container_width=True, type="primary"):
            st.session_state.screen = 'create'
            st.rerun()

        st.markdown("")
        st.markdown("---")
        st.markdown("*Our Legacy 2 — Python RPG*")


def screen_create():
    st.markdown('<h1 class="main-title">⚔️ Create Your Character</h1>', unsafe_allow_html=True)
    st.markdown("---")

    data = st.session_state.data
    classes = list(data['classes'].keys())

    col1, col2 = st.columns([1, 1])

    with col1:
        name = st.text_input("Character Name", placeholder="Enter your name...")
        selected_class = st.selectbox("Choose Your Class", classes)

        if selected_class:
            cls_data = data['classes'][selected_class]
            stats = cls_data.get('base_stats', {})
            st.markdown(f"**{selected_class}** — {cls_data.get('description', '')}")
            st.markdown("**Starting Stats:**")
            st.markdown(f"❤️ HP: {stats.get('hp', '?')} | 🔵 MP: {stats.get('mp', '?')}")
            st.markdown(f"⚔️ ATK: {stats.get('attack', '?')} | 🛡️ DEF: {stats.get('defense', '?')} | 💨 SPD: {stats.get('speed', '?')}")
            starting_items = cls_data.get('starting_items', [])
            if starting_items:
                st.markdown(f"**Starting Items:** {', '.join(starting_items)}")
            st.markdown(f"**Starting Gold:** {cls_data.get('starting_gold', 100)}")

    with col2:
        st.markdown("### Class Descriptions")
        class_icons = {
            'Warrior': '⚔️', 'Mage': '🔮', 'Rogue': '🗡️', 'Hunter': '🏹',
            'Bard': '🎵', 'Paladin': '⚡', 'Druid': '🌿', 'Priest': '✨'
        }
        for cls in classes:
            icon = class_icons.get(cls, '🧙')
            desc = data['classes'][cls].get('description', '')
            st.markdown(f"{icon} **{cls}** — {desc}")

    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_b:
        if st.button("⚔️ Start Adventure!", use_container_width=True, type="primary"):
            if not name or not name.strip():
                st.error("Please enter a character name!")
            else:
                player = create_player(name.strip(), selected_class)
                st.session_state.player = player
                st.session_state.screen = 'game'
                st.session_state.current_area = 'starting_village'
                add_message(f"Welcome, {name}! Your adventure begins in the Starting Village.", '#ffd700')
                add_message(f"You are a level 1 {selected_class}. Good luck!", '#d4c4a8')
                st.rerun()

        if st.button("← Back", use_container_width=True):
            st.session_state.screen = 'welcome'
            st.rerun()


def screen_game():
    data = st.session_state.data
    player = st.session_state.player
    area_key = st.session_state.current_area
    area = data['areas'].get(area_key, {})
    area_name = area.get('name', area_key.replace('_', ' ').title())

    # Sidebar: Character Stats
    with st.sidebar:
        st.markdown("## 🧙 Character")
        render_stat_panel()
        st.markdown("---")
        st.markdown("## 📍 Location")
        st.markdown(f"**{area_name}**")
        st.markdown(area.get('description', '')[:120] + '...' if len(area.get('description', '')) > 120 else area.get('description', ''))

    # Main area
    st.markdown(f'<h2 style="color:#ffd700">📍 {area_name}</h2>', unsafe_allow_html=True)

    # Tabs
    tab_names = ["🗺️ Explore", "🎒 Inventory", "🗺️ Travel", "🛒 Shop", "📜 Missions"]
    tab_explore, tab_inv, tab_travel, tab_shop, tab_missions = st.tabs(tab_names)

    # ── Explore Tab
    with tab_explore:
        st.markdown(f"*{area.get('description', 'A mysterious place.')}*")
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⚔️ Explore", use_container_width=True, type="primary"):
                explore_area()
                if st.session_state.screen != 'battle':
                    st.rerun()
                else:
                    st.rerun()

        with col2:
            can_rest = area.get('can_rest', False)
            cost = area.get('rest_cost', 10)
            if st.button(f"💤 Rest ({cost}g)", use_container_width=True, disabled=not can_rest):
                rest()
                st.rerun()

        with col3:
            if area.get('shops'):
                if st.button("🏪 Visit Shop", use_container_width=True):
                    visit_shop()
                    st.rerun()

        # Possible enemies
        enemies = area.get('possible_enemies', [])
        if enemies:
            st.markdown("**⚠️ Danger:** " + ', '.join(e.replace('_', ' ').title() for e in enemies))

        # Message log
        st.markdown("---")
        st.markdown("### 📋 Game Log")
        log_html = "<br>".join(reversed(st.session_state.messages[-20:])) if st.session_state.messages else "<i>No messages yet.</i>"
        st.markdown(f'<div class="message-log">{log_html}</div>', unsafe_allow_html=True)

    # ── Inventory Tab
    with tab_inv:
        st.markdown("### 🎒 Inventory")
        inv = player.get('inventory', [])
        if not inv:
            st.info("Your inventory is empty.")
        else:
            st.markdown(f"**{len(inv)} items** | Gold: {player['gold']} 💰")
            # Group by name
            counts = {}
            for item in inv:
                counts[item] = counts.get(item, 0) + 1

            for item_name, count in counts.items():
                item_data = data['items'].get(item_name, {})
                rarity = item_data.get('rarity', 'common')
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    label = f"{item_name}" + (f" x{count}" if count > 1 else "")
                    st.markdown(f'<span class="rarity-{rarity}">**{label}**</span>', unsafe_allow_html=True)
                    if item_data.get('description'):
                        st.caption(item_data['description'][:80])
                with col_b:
                    if st.button("Use", key=f"use_{item_name}", use_container_width=True):
                        use_item(item_name)
                        st.rerun()
                with col_c:
                    sell_price = max(1, int(item_data.get('buy_price', item_data.get('value', 10)) * 0.5))
                    if st.button(f"Sell {sell_price}g", key=f"sell_{item_name}", use_container_width=True):
                        sell_item(item_name)
                        st.rerun()

        st.markdown("---")
        st.markdown("### ⚔️ Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"❤️ Max HP: {player['max_hp']}")
            st.markdown(f"🔵 Max MP: {player['max_mp']}")
            st.markdown(f"⚔️ Attack: {player['attack']}")
        with col2:
            st.markdown(f"🛡️ Defense: {player['defense']}")
            st.markdown(f"💨 Speed: {player['speed']}")
            st.markdown(f"📊 Level: {player['level']}")

    # ── Travel Tab
    with tab_travel:
        st.markdown("### 🗺️ Travel")
        connections = area.get('connections', [])
        if not connections:
            st.info("No connected areas from here.")
        else:
            for dest_key in connections:
                dest = data['areas'].get(dest_key, {})
                dest_name = dest.get('name', dest_key.replace('_', ' ').title())
                visited = dest_key in st.session_state.visited_areas
                visited_str = " ✅" if visited else ""
                enemies_in_dest = dest.get('possible_enemies', [])
                danger = "⚠️ Danger" if enemies_in_dest else "🕊️ Safe"
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{dest_name}**{visited_str} — {danger}")
                    if dest.get('description'):
                        st.caption(dest['description'][:80])
                with col_b:
                    if st.button(f"Travel →", key=f"travel_{dest_key}", use_container_width=True):
                        travel_to(dest_key)
                        st.rerun()

    # ── Shop Tab
    with tab_shop:
        st.markdown("### 🛒 Shop")
        shop_items = st.session_state.get('shop_items', [])
        if not shop_items:
            has_shop = bool(area.get('shops'))
            if has_shop:
                st.info("Click 'Visit Shop' in the Explore tab to browse items.")
            else:
                st.info("There is no shop in this area.")
        else:
            st.markdown(f"💰 Your gold: **{player['gold']}**")
            for item_name in shop_items:
                item_data = data['items'].get(item_name, {})
                price = item_data.get('buy_price', item_data.get('value', 20))
                rarity = item_data.get('rarity', 'common')
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f'<span class="rarity-{rarity}">**{item_name}**</span> — {price} gold', unsafe_allow_html=True)
                    if item_data.get('description'):
                        st.caption(item_data['description'][:80])
                with col_b:
                    if st.button(f"Buy", key=f"buy_{item_name}", use_container_width=True,
                                 disabled=player['gold'] < price):
                        buy_item(item_name)
                        st.rerun()

    # ── Missions Tab
    with tab_missions:
        st.markdown("### 📜 Missions")
        missions = data.get('missions', {})
        completed = st.session_state.completed_missions

        available = [(mid, m) for mid, m in missions.items()
                     if mid not in completed and m.get('area', area_key) == area_key]
        all_missions = [(mid, m) for mid, m in missions.items() if mid not in completed]

        show_missions = available if available else all_missions[:10]

        if not show_missions:
            st.info("No missions available right now.")
        else:
            for mid, mission in show_missions[:15]:
                exp = mission.get('experience_reward', 0)
                gold = mission.get('gold_reward', 0)
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{mission.get('name', mid)}**")
                    st.caption(mission.get('description', '')[:120])
                    st.caption(f"Reward: {exp} EXP, {gold} gold")
                with col_b:
                    if st.button("Complete", key=f"mission_{mid}", use_container_width=True):
                        # Simple: complete mission and reward
                        st.session_state.completed_missions.append(mid)
                        player['gold'] += gold
                        gain_experience(player, exp)
                        add_message(f"Completed mission: {mission.get('name', mid)}! +{exp} EXP, +{gold} gold", '#ffd700')
                        st.rerun()


def screen_battle():
    enemy = st.session_state.battle_enemy
    player = st.session_state.player
    log = st.session_state.battle_log

    # Sidebar
    with st.sidebar:
        st.markdown("## ⚔️ Battle!")
        st.markdown(f"**{player['name']}** vs **{enemy['name']}**")
        st.markdown("---")
        st.markdown("### Your Status")
        st.markdown(f"❤️ HP: {player['hp']}/{player['max_hp']}")
        st.markdown(progress_bar(player['hp'], player['max_hp'], '#cc3333'), unsafe_allow_html=True)
        st.markdown(f"🔵 MP: {player['mp']}/{player['max_mp']}")
        st.markdown(progress_bar(player['mp'], player['max_mp'], '#3366cc'), unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### Enemy Status")
        st.markdown(f"❤️ HP: {enemy['hp']}/{enemy['max_hp']}")
        st.markdown(progress_bar(enemy['hp'], enemy['max_hp'], '#cc3333'), unsafe_allow_html=True)

    st.markdown(f'<h2 style="color:#cc3333">⚔️ Battle: {enemy["name"]}</h2>', unsafe_allow_html=True)

    # Battle log
    log_html = "<br>".join(log[-15:])
    st.markdown(f'<div class="message-log">{log_html}</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Actions
    st.markdown("### Choose Your Action:")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("⚔️ Attack", use_container_width=True, type="primary"):
            battle_attack()
            st.rerun()

    with col2:
        if st.button("🛡️ Defend", use_container_width=True):
            battle_defend()
            st.rerun()

    with col3:
        # Use item dropdown
        usable = [i for i in player['inventory'] if 'potion' in i.lower() or 'Potion' in i]
        if usable:
            item_choice = st.selectbox("Use Item", usable, label_visibility='collapsed')
            if st.button("💊 Use Item", use_container_width=True):
                battle_use_item(item_choice)
                st.rerun()
        else:
            st.button("💊 No Items", disabled=True, use_container_width=True)

    with col4:
        if st.button("🏃 Flee", use_container_width=True):
            battle_flee()
            st.rerun()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    init_state()

    screen = st.session_state.screen

    if screen == 'welcome':
        screen_welcome()
    elif screen == 'create':
        screen_create()
    elif screen == 'game':
        screen_game()
    elif screen == 'battle':
        screen_battle()
    else:
        st.session_state.screen = 'welcome'
        st.rerun()


if __name__ == '__main__':
    main()
