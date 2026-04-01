# Our Legacy 2

A browser-based medieval fantasy RPG built with Python and Flask. Play entirely in your browser — no downloads required.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Character Creation](#character-creation)
- [Classes](#classes)
- [Combat](#combat)
- [World & Exploration](#world--exploration)
- [Dungeons](#dungeons)
- [Missions & Quests](#missions--quests)
- [Weekly Challenges](#weekly-challenges)
- [Shops & Inventory](#shops--inventory)
- [Elite Market](#elite-market)
- [Crafting & Alchemy](#crafting--alchemy)
- [Your Land (Housing & Farming)](#your-land-housing--farming)
- [Pets](#pets)
- [Companions](#companions)
- [Spells & Magic](#spells--magic)
- [Equipment](#equipment)
- [Online & Social Features](#online--social-features)
- [Events](#events)
- [Books](#books)
- [File Structure](#file-structure)

---

## Quick Start

**Requirements:** Python 3.11+

```bash
# Clone the repo and install dependencies
pip install -r requirements.txt

# Set required environment variables (see below)
cp .env.example .env   # or export them directly

# Apply the database schema (once, see Database Setup below)

# Start the server
bash init.sh
```

Open `http://localhost:5000` in your browser.

The `init.sh` script handles dependency installation and server startup in one step. If `SUPABASE_DB_URL` is set and `psql` is available it will also apply the schema automatically.

---

## Environment Variables

Create a `.env` file in the project root (or set these in your hosting platform):

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Your Supabase project URL (`https://<ref>.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase **service-role** secret key |
| `SECRET_KEY` | Yes | Flask session secret (any long random string) |
| `SUPABASE_DB_URL` | Optional | PostgreSQL connection string for auto-migration via `init.sh` |
| `RESEND_API` | Optional | Resend API key (enables email verification / password reset) |
| `RESEND_EMAIL` | Optional | Sender address for outbound email (`From: …`) |
| `PORT` | Optional | Port to bind (default `5000`) |
| `WEB_CONCURRENCY` | Optional | Number of Gunicorn workers (default `1`) |

---

## Database Setup

The game uses **Supabase (PostgreSQL)** for user accounts, cloud saves, chat, and social features.

### Option A — Supabase SQL Editor (recommended)

1. Open your Supabase project → **SQL Editor**
2. Paste the contents of [`setup.sql`](setup.sql) and run it
3. All tables, indexes, and triggers are created with `IF NOT EXISTS` guards — safe to re-run

### Option B — psql (command line)

```bash
psql "$SUPABASE_DB_URL" -f setup.sql
```

Or let `init.sh` do it automatically if `SUPABASE_DB_URL` is set and `psql` is installed.

### Tables created by `setup.sql`

| Table | Description |
|---|---|
| `ol2_users` | Player accounts (username, hashed password, optional email) |
| `ol2_saves` | Encrypted cloud save blobs (one slot per user) |
| `ol2_characters` | Persistent character state for the autosave / MMO system |
| `ol2_chat` | Global chat messages |
| `ol2_dms` | Private messages between players |
| `ol2_friends` | Friend relationships and pending requests |
| `ol2_blocks` | Blocked-user list |
| `ol2_groups` | Adventure groups |
| `ol2_group_members` | Group membership and XP contribution |
| `ol2_group_log` | Activity log for each group |
| `ol2_tick_lock` | Distributed world-tick lock (required for multiple workers) |

---

## Character Creation

When starting a new game you choose:

### Race (10 options)
Each race provides different starting stat bonuses across HP, MP, ATK, DEF, SPD, and Gold.

| Race | Bonus Focus |
|------|------------|
| Human | Balanced all-rounder |
| Elf | Speed & Magic |
| Dwarf | Defense & HP |
| Lycanthrope | Attack & Speed |
| Orc | Attack & HP |
| Gnome | Magic & Intelligence |
| Tiefling | Magic & Charisma |
| Dragonborn | Fire power & HP |
| Goblin | Speed & Gold |
| Troll | HP & Defense |

### Gender (3 options)
- **Male** — Bonus ATK, MP, HP
- **Female** — Bonus SPD, Gold, MP
- **Non-binary** — Bonus ATK, SPD, HP

### Background (11 options)
Backgrounds grant initial stat boosts to reflect your character's history.

| Background | Bonus Focus |
|-----------|------------|
| Soldier | ATK & DEF |
| Scholar | INT & MP |
| Noble | Gold & CHA |
| Street Rat | SPD & Dodge |
| Blacksmith | DEF & STR |
| Merchant | Gold & CHA |
| Farmer | CON & HP |
| Sailor | SPD & STR |
| Herbalist | WIS & MP |
| Hunter | ATK & SPD |
| Priest | WIS & MP |

### Attribute System (S.D.I.C.W.C.)
You gain **3 points per level** to allocate freely:

| Attribute | Abbreviation | Effect |
|-----------|-------------|--------|
| Strength | STR | +2 ATK per point |
| Dexterity | DEX | +1 SPD, +1% Dodge |
| Intelligence | INT | +3 MP, +2 Spell Power |
| Charisma | CHA | +1% Shop Discount |
| Wisdom | WIS | +2 MP, +2% Item Discovery |
| Constitution | CON | +5 HP, +1 DEF |

---

## Classes

| Class | Description | Playstyle |
|-------|-------------|-----------|
| **Warrior** | Heavy melee fighter | High HP & DEF, frontline brawler |
| **Mage** | Arcane spellcaster | High MP & Spell Power, glass cannon |
| **Rogue** | Agile assassin | High SPD & Crit, burst damage |
| **Hunter** | Ranged tracker | High ATK & Aim, consistent damage |
| **Bard** | Support performer | High SPD, buffs and debuffs |
| **Paladin** | Holy warrior | High DEF & Holy Power, hybrid tank/healer |
| **Druid** | Nature guardian | High MP & Shapeshift abilities |
| **Priest** | Devoted healer | High MP & Healing, support role |

---

## Combat

Turn-based battles with the following actions:

- **Attack** — Standard physical strike
- **Defend** — Reduce incoming damage this turn
- **Spell** — Cast a magic spell (requires a magic weapon equipped)
- **Use Item** — Consume a potion or buff item from inventory
- **Flee** — Attempt to escape the battle

### Combat Mechanics
- **D20 Roll System** — Roll 1 = critical miss, roll 20 = critical hit
- **Status Effects** — Poison, Stun, Blind, Slow, Defense Boost, Shield
- **Boss Phases** — Bosses shift through phases at HP thresholds, gaining new abilities
- **Weather Bonuses** — Current weather affects EXP and Gold earned
- **Time of Day Bonuses** — Day/night cycle (8 stages from Dawn to Midnight) affects gameplay

---

## World & Exploration

The world is a network of connected areas. Navigate by travelling between them.

### Actions in the World
- **Explore** — Search the current area for encounters, loot, and events
- **Travel** — Move to a connected area
- **Rest** — Stay at an inn to restore HP and MP (cost varies by area)
- **Talk to NPCs** — Unlock quests and lore

### Notable Areas (partial list)
Starting Village, Dark Forest, Ancient Ruins, Crystal Caves, Dragon's Lair, Port Lesbèn, The Abyss Gate, and many more.

### Dynamic Systems
- **Weather** — Sunny, Rainy, Snowy, Stormy — changes periodically and affects rewards
- **Day/Night Cycle** — 8 stages (Dawn → Morning → Midday → Afternoon → Dusk → Evening → Night → Midnight)

---

## Dungeons

Procedurally generated dungeon runs with a variety of room types:

| Room Type | Description |
|-----------|-------------|
| Battle | Fight a random enemy |
| Boss | Face a powerful dungeon boss |
| Chest | Find loot and gold |
| Trap | Avoid or disarm a hazard |
| Shrine | Receive a blessing or curse |
| Riddle/Question | Answer correctly for a reward |
| Ambush | Surprise encounter with multiple enemies |

Progress is saved between rooms. Abandoning a dungeon forfeits your progress.

---

## Missions & Quests

### Mission Types
- **Kill** — Slay a set number of specific enemies
- **Collect** — Gather a set number of materials
- **Multi** — Combined kill and collect objectives

Many missions are unlocked by talking to specific NPCs in the world. Active missions track progress automatically during combat and exploration.

---

## Weekly Challenges

Long-term goals that reset weekly. Current challenges:

| Challenge | Goal | Reward |
|-----------|------|--------|
| Monster Slayer | Kill 50 enemies | EXP + Gold |
| Veteran Slayer | Kill 100 enemies | EXP + Gold |
| Champion of Slaughter | Kill 250 enemies | EXP + Gold |
| Quest Starter | Complete 5 missions | EXP + Gold |
| Quest Master | Complete 10 missions | EXP + Gold |
| Grand Quester | Complete 25 missions | EXP + Gold |
| Dungeon Delver | Complete 1 dungeon | EXP + Gold |
| Dungeon Runner | Complete 3 dungeons | EXP + Gold |
| Dungeon Conqueror | Complete 10 dungeons | EXP + Gold |
| Dungeon Lord | Complete 25 dungeons | EXP + Gold |
| Seasoned Adventurer | Reach Level 20 | EXP + Gold |
| Elite Warrior | Reach Level 35 | EXP + Gold |
| Legendary Hero | Reach Level 50 | EXP + Gold |
| Boss Hunter | Defeat 5 bosses | EXP + Gold |
| Boss Nemesis | Defeat 15 bosses | EXP + Gold |
| Treasure Seeker | Accumulate 10,000 Gold | EXP + Gold |
| Wealthy Merchant | Accumulate 50,000 Gold | EXP + Gold |
| Gold Baron | Accumulate 200,000 Gold | EXP + Gold |

---

## Shops & Inventory

- Each area has its own shop with locally available items
- **Buy** items with gold
- **Sell** items from your inventory
- **Equip/Unequip** gear directly from inventory
- **Use** consumables (potions, scrolls, food)
- Charisma stat gives a percentage discount on all purchases

---

## Elite Market

A global server-side market offering rare items unavailable in normal shops.

- Stock rotates on a **10-minute cooldown**
- Items display their **level and class requirements** with usability indicators (green = can use, red = cannot use)
- Prices fluctuate based on server-side supply

---

## Crafting & Alchemy

Craft items using materials gathered from combat and exploration.

### Material Categories
- **Ores** — Iron Ore, Coal, Steel Ingot, Gold Nugget
- **Herbs** — Herbs, Mana Herbs, Spring Water
- **Crystals** — Crystal Shards, Dark Crystals, Fire Gems
- **Monster Parts** — Goblin Ears, Orc Teeth, Wolf Fangs, Venom Sacs
- **Magical** — Phoenix Feathers, Dragon Scales, Ancient Relics

### Recipe Categories
| Category | Examples |
|----------|---------|
| Potions | Health Potion (Basic → Greater), Mana Potion, Frost Potion |
| Elixirs | Elixir of Giant Strength, Swiftness Elixir |
| Enchantments | Steel Dagger, Swamp Scale Armor, enchanted gear |
| Utility | Luck Charms, Elemental Essences, Gems |
| Consumables | Field rations, special foods |

---

## Your Land (Housing & Farming)

A personal area you can build and grow over time.

### Housing
Build and upgrade your residence from basic to grand:
- Small Tent → Cottage → Manor → Castle → Imperial Palace
- Place decorations, fencing, and functional buildings
- Functional buildings include: Dwarven Forge, Training Dummy, Alchemist's Table, and more

### Farming
- 4 farm slots to plant and harvest crops
- Crops grow over game ticks (time-based)
- Crops include: Wheat, Dragon Fruit, Jade Lotus, and others
- Harvested crops can be used in crafting or sold

---

## Pets

Over 30 adoptable pets that provide passive bonuses. Examples:

| Pet | Bonus Type |
|-----|-----------|
| Slime | Gold find |
| Phoenix Chick | Fire resistance & ATK |
| Void Firefly | Item discovery |
| Shadow Cat | SPD & Crit |
| Stone Golem | DEF & HP |
| ... and many more | |

Each pet has a unique passive effect that applies at all times once adopted.

---

## Companions

Hire NPC allies to fight alongside you in battle.

| Companion | Special Ability |
|-----------|----------------|
| Borin the Brave | Shield Bash |
| Nyx the Shadow | Shadow Strike |
| ... and others | Healing, buffs, and more |

Companions provide combat bonuses and unique battle actions. Only one companion can be active at a time. Dismissing a companion requires confirmation.

---

## Spells & Magic

Spells are unlocked by class and require a **magic-capable weapon** (Wand, Staff, Orb, etc.) to cast.

### Spell Types
- **Offensive** — Fireball, Ice Shard, Lightning Bolt, Shadow Bolt
- **Healing** — Heal, Greater Heal, Holy Light
- **Buffs** — Shield, Haste, Strength Aura
- **Debuffs** — Slow, Blind, Poison Cloud

Spell Power scales with the **Intelligence** attribute.

---

## Equipment

Four equipment slots:

| Slot | Types |
|------|-------|
| Weapon | Swords, Daggers, Bows, Wands, Staffs, Lutes, and more |
| Armor | Light, Medium, and Heavy armour sets |
| Offhand | Shields, Tomes, Quivers |
| Accessories | Rings, Amulets, Charms (3 accessory slots) |

Items have level and class requirements. The Elite Market shows whether each item is usable by your character with a clear indicator.

---

## Online & Social Features

Sign in with a free online account to access:

### Cloud Save
- Progress saved to the cloud automatically
- Continue your adventure on any device

### Friends System
- Send and receive friend requests
- View online/offline status of friends
- Accept or decline pending requests

### Direct Messages
- Private DM conversations with friends
- Full message history per conversation

### Global Chat
- Chat with all online players in real time
- Access via the chat button in the bottom-right corner of every page

### Block System
- Block users to prevent messages and friend requests

---

## Events

Time-limited server events appear periodically and offer special rewards, bonus drop rates, or unique encounters. Examples include:
- **The Primordial One's Gift** — Special drop bonuses from ancient enemies
- Seasonal and holiday events

Check the Events tab in-game for currently active events.

---

## Books

A library of 18+ lore books found during exploration, covering the world history of Eldenmoor and its factions. Reading them deepens the lore and may unlock rewards.

Examples:
- *Chronicles of Byzantra*
- *The Fall of the Old Kingdoms*
- *A Traveller's Guide to Port Lesbèn*

---

## File Structure

```
our_legacy_2/
├── app.py                        # Main Flask application & all routes
├── setup.sql                     # Full PostgreSQL/Supabase schema setup script
├── init.sh                       # Server initialization script (install + migrate + start)
├── requirements.txt              # Python dependencies
├── data/
│   ├── areas.json                # World areas and connections
│   ├── bosses.json               # Boss definitions and phases
│   ├── classes.json              # Class stats and gear
│   ├── crafting.json             # Crafting recipes
│   ├── dungeons.json             # Dungeon layouts and rooms
│   ├── effects.json              # Status effects
│   ├── enemies.json              # Enemy definitions
│   ├── events.json               # Server events
│   ├── farming.json              # Crops and farm data
│   ├── housing.json              # Buildings and decorations
│   ├── items.json                # All items
│   ├── missions.json             # Quests and missions
│   ├── pets.json                 # Pet definitions
│   ├── races.json                # Race stat bonuses
│   ├── shops.json                # Shop inventories per area
│   ├── spells.json               # Spell definitions
│   └── weekly_challenges.json    # Challenge definitions
├── static/
│   ├── css/style.css             # All game styling
│   ├── js/game.js                # Client-side game logic
│   └── game_assets/             # Images, icons, backgrounds, music
├── templates/
│   ├── base.html                 # Base layout with nav, modals, and chat FAB
│   ├── index.html                # Main game screen
│   ├── create.html               # Character creation
│   ├── chat.html                 # Full-page global chat
│   ├── friends.html              # Friends & DMs page
│   ├── dungeon_room.html         # Dungeon room screen
│   ├── groups.html               # Adventure groups page
│   └── ...                       # Other pages
└── utilities/
    ├── battle.py                 # Battle logic
    ├── dungeons.py               # Dungeon generation
    ├── email_sender.py           # Outbound email via Resend
    ├── save_load.py              # Local save encryption/decryption
    ├── spellcasting.py           # Spell system
    ├── supabase_db.py            # Online account, cloud save & social features
    └── ...                       # Other utility modules
```

---

*Built with Python / Flask. All game data is moddable via the JSON files in the `data/` folder.*
