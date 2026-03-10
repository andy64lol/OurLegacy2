# ⚔️ Our Legacy - Text-Based CLI Fantasy RPG Game

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Node.js](https://img.shields.io/badge/Node.js-Required-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📑 Quick Links
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation--setup)
- [Web Download](#web-download)
- [Game Controls](#game-controls)
- [File Structure](#file-structure)
- [Mod System](#mod-system)
- [Contributing](#contributing)

## Overview

"Our Legacy" is a comprehensive text-based CLI fantasy RPG game focused on exploration, grinding, and adventure. Built with Python and driven by modular JSON data, the game offers a rich, extensible experience for players and modders alike. Now featuring a powerful **JavaScript Scripting Engine** powered by Node.js and a new **Alchemy & Crafting** system.

## Features

### Core Gameplay
- **Character Classes**: Choose from **Warrior**, **Mage**, **Rogue**, **Hunter**, **Bard**, **Paladin**, **Druid**, or **Priest** classes.
- **Exploration**: 7 diverse areas including the Starting Village, Dark Forest, Ancient Ruins, and more.
- **Alchemy & Crafting**: Collect materials from monsters and the environment to brew potent potions or forge powerful equipment.
- **Grinding System**: Level up through combat, gaining stats and unlocking new equipment.
- **Mission System**: Complete main story and side quests for gold and experience rewards.
- **Boss Battles**: Face legendary bosses like the **Ancient Fire Dragon** with multi-phase mechanics and HP thresholds.
- **Scripting Engine**: Extend and automate your journey using JavaScript (Node.js).

### Advanced Systems
- **Companions**: Hire unique companions at the Tavern with active abilities and passive party bonuses.
- **Buff & Effect System**: Manage temporary status effects, magical shields, and per-turn HP/MP regeneration.
- **Offhand & Accessories**: Deep equipment customization with dedicated offhand slots and up to 3 accessory slots.
- **Real-time Cooldowns**: Bosses feature an 8-hour real-time cooldown after defeat.

## Character Classes

| Class | Description | Key Stats | Starting Gear |
|-------|-------------|-----------|---------------|
| **Warrior** | Strong melee fighter | High HP & Defense | Iron Sword, Leather Armor |
| **Mage** | Powerful spellcaster | High MP & Magic | Wooden Wand, Cloth Tunic |
| **Rogue** | Agile assassin | High Speed & Crit | Steel Dagger, Leather Armor |
| **Hunter** | Experienced tracker | High Attack & Aim | Hunter's Bow, Hunting Knife |
| **Bard** | Master of melodies | High Speed & Support | Enchanting Lute, Colourful Robe |
| **Paladin** | Holy warrior | High Defense & Holy Power | Paladin's Sword, Holy Shield |
| **Druid** | Nature guardian | High MP & Shapeshift | Druidic Staff, Nature's Robe |
| **Priest** | Devoted healer | High MP & Healing | Priest's Staff, Devout's Robe |

## Alchemy & Crafting

The new Crafting system allows you to create items using materials gathered during your travels.

### Material Collection
Materials are found by defeating enemies or exploring specific areas:
- **Ores**: Iron Ore, Coal, Steel Ingot, Gold Nugget.
- **Herbs**: Herbs, Mana Herbs, Spring Water.
- **Crystals**: Crystal Shards, Dark Crystals, Fire Gems.
- **Monster Parts**: Goblin Ears, Orc Teeth, Wolf Fangs, Venom Sacs.
- **Magical**: Phoenix Feathers, Dragon Scales, Ancient Relics.

### Alchemy Recipes
- **Potions**: Brew Health and Mana potions (Basic to Greater), or specialized Frost Potions.
- **Elixirs**: Create powerful boosters like the *Elixir of Giant Strength*.
- **Enchantments**: Forge weapons and armor like *Steel Daggers* or *Swamp Scale Armor*.
- **Utility**: Craft Luck Charms or extract pure Elemental Essences into Gems.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js** (for scripting features)

### Installation
```bash
# Clone or download the repository
git clone https://github.com/andy64lol/our-legacy.git

# Navigate to the project directory
cd our-legacy

# Run the game
python3 main.py

# Or use the launcher for all tools
python3 launcher.py
```

## 🌐 Web Download

You can also download Our Legacy directly from the web interface:

1. Open `index.html` in your browser
2. Click the **"Download Our Legacy (ZIP)"** button
3. Extract the ZIP file
4. Run `python3 main.py` to start playing

The web interface also includes:
- 📖 Full documentation display
- 🎮 Feature highlights
- 📦 One-click ZIP download

## Game Controls

### Main Menu
- **Explore**: Engage in random encounters and collect crafting materials.
- **Inventory**: Manage items and access the **Crafting** menu.
- **View Character**: Check stats, equipment, and active buffs.
- **Travel**: Move between connected world areas.
- **Missions**: Track and accept quests.
- **Tavern**: Hire and manage your party members.
- **Shop**: Browse multiple specialized shops in each area, each with unique items and purchase limits.
- **Save/Load**: Persist your progress to JSON save files.

## File Structure

```
Our_Legacy/
├── launcher.py             # Unified launcher for all tools
├── storyland.py            # Download and manage mods from GitHub
├── storywrite.py           # Submit mods to the community
├── main.py                 # Core game engine (Python 3.11+)
├── chat.py                 # The chat client for Global chat
├── gui_all.py              # Experimental GUI version of launcher.py using Tkinter
├── README.md               # Quick start guide and overview
├── documentation.md        # Complete modding guide with parameters & examples
├── package.json            # Node.js project configuration (for scripting)
├── data/                   # Base Game Content (JSON)
│   ├── classes.json        # Player character classes and progression
│   ├── items.json          # Weapons, armor, consumables, accessories
│   ├── crafting.json       # Alchemy recipes and material categories
│   ├── areas.json          # World locations, shops, connections
│   ├── shops.json          # Shop definitions with items and limits
│   ├── enemies.json        # Regular combat encounters
│   ├── bosses.json         # Boss mechanics with multi-phase support
│   ├── missions.json       # Quests with objectives and rewards
│   ├── spells.json         # Magic spells and abilities
│   ├── effects.json        # Status effects and buffs
│   ├── companions.json     # Hireable companion definitions
│   ├── dialogues.json      # NPC and boss dialogue text
│   ├── dungeons.json       # Procedural dungeons with challenges
│   ├── weekly_challenges.json  # Recurring challenges
│   └── saves/              # Player save files (.json)
├── mods/                   # Installed mods (downloaded and custom)
│   └── The Ether/          # Example mod structure
│       ├── mod.json        # Mod metadata
│       ├── bosses.json     # New bosses
│       ├── areas.json      # New areas
│       ├── enemies.json    # New enemies
│       ├── items.json      # New items
│       ├── dungeons.json   # New dungeons
│       ├── dialogues.json  # New dialogue text
│       └── ...other files
├── api/                    # API modules for marketplace
│   ├── market.js
│   ├── ping.js
│   ├── upload_test.js
│   ├── send_message.js
│   ├── create_user.js
│   └── data/
└── LICENSE                 # Project license
```

## Mod System

### Creating a Mod
1. Create a folder in `mods/` with your mod name
2. Create `mod.json` with metadata:
```json
{
  "name": "Your Mod Name",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What your mod adds",
  "enabled": true
}
```
3. Add any data files you want to modify:
   - `bosses.json` - New or override bosses
   - `areas.json` - New areas or area changes
   - `items.json` - New items
   - `dungeons.json` - New dungeons
   - `dialogues.json` - Dialogue text
   - Any other data files from `data/`

### How Mods Load
- Base game data loads first from `data/`
- Enabled mods load sequentially, merging data
- Arrays (dungeons) are extended with new entries
- Objects (items, bosses) are updated/overridden
- Mod data takes precedence over base data for same IDs

---

## Data File Overview

### Core Data Files
| File | Purpose | Contains |
|------|---------|----------|
| **classes.json** | Character classes | Warrior, Mage, Rogue, Hunter, Bard |
| **items.json** | Equipment & consumables | Weapons, armor, potions, materials |
| **enemies.json** | Regular encounters | Goblin, Orc, Skeleton, etc. |
| **bosses.json** | Boss battles | Multi-phase encounters with abilities |
| **areas.json** | World locations | Starting Village, Dungeons, Towns |
| **missions.json** | Quests | Main story and side quests |
| **spells.json** | Magic abilities | Spells for different classes |
| **effects.json** | Status effects | Buffs, debuffs, conditions |
| **companions.json** | Party members | Hireable companions with abilities |
| **crafting.json** | Alchemy system | Recipes and material categories |
| **dialogues.json** | Text dialogue | Boss speeches and NPC dialogue |
| **dungeons.json** | Procedural dungeons | Dungeon definitions and challenges |

### Parameter Reference
For complete parameter documentation, see [documentation.md](documentation.md):
- **All JSON parameters** with type information
- **Complete examples** for each file type
- **Mod creation guide** with step-by-step instructions
- **Best practices** for mod development

## 🤝 Contributing

Contributions are welcome! Whether it's:
- 🐛 Bug fixes
- ✨ New features
- 🔧 Mod creation
- 📚 Documentation improvements
- 🌍 Translation support

Please ensure your code follows the existing style and includes appropriate documentation.

## 📄 License

This project is open source under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Forge your destiny and leave behind a legend that will never be forgotten!</strong><br>
  <em>Built with ❤️ using Python & Node.js</em>
</p>
