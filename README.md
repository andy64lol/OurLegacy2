# ⚔️ Our Legacy 2

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web%20GUI-blueviolet.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📑 Quick Links
- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation)
- [Game Controls](#game-controls)
- [File Structure](#file-structure)
- [Contributing](#contributing)

## Overview

"Our Legacy 2" is a comprehensive fantasy RPG game focused on exploration, grinding, and adventure. Built with Python/Flask and driven by modular JSON data, the game features a full **medieval-themed web GUI** playable in any browser, with rich **Alchemy & Crafting**, **Dungeons**, **Housing/Farming**, and more.

## Features

### Core Gameplay (All Implemented)
- **Character Classes**: 8 classes (Warrior, Mage, Rogue, Hunter, Bard, Paladin, Druid, Priest) with unique stats/gear.
- **Exploration**: Multiple areas (travel, random encounters, loot/events).
- **Combat/Grinding**: Turn-based battles, leveling, stat growth.
- **Missions/Quests**: Kill/collect objectives with progress tracking.
- **Boss Battles**: In dungeons/world.

### Advanced Systems (All Implemented)
- **Crafting/Alchemy**: Full recipes/materials system (dedicated page).
- **Dungeons**: Procedural rooms (battles/chests/traps/questions/bosses).
- **Housing/Farming**: Buy/place buildings, plant/harvest crops.
- **Pets/Companions**: Stat-boosting pets.
- **Equipment**: Weapon/Armor/Offhand/Accessory slots w/ bonuses.
- **Elite Market**: Special items (10min cooldown).
- **Shops/Inventory**: Buy/sell/equip/use.
- **Buffs/Spells**: Via items/spells in combat.

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
- **Flask** (auto-installed below)

### Installation & Run
```bash
cd our_legacy_2
pip install flask cryptography
python app.py
```
Open http://localhost:5000 - play in browser!


## Game Controls

### Web Interface
- **Game screen**: Explore, Travel, Rest, Shop, Missions, Land (Housing/Farm/Pets), Market, Dungeons.
- **Dedicated pages**: Battle, Crafting, Dungeons.
- **Actions**: Buttons/forms for all gameplay.

## File Structure

```
our_legacy_2/
├── app.py                  # Flask web app (main entry)
├── main.py                 # Placeholder
├── data/                   # JSON game data
│   ├── areas.json          # Areas & connections
│   ├── bosses.json         # Bosses
│   ├── classes.json        # Classes
│   ├── crafting.json       # Recipes
│   ├── dungeons.json       # Dungeons
│   ├── effects.json
│   ├── enemies.json
│   ├── farming.json
│   ├── housing.json
│   ├── items.json
│   ├── missions.json
│   ├── pets.json
│   ├── shops.json
│   ├── spells.json
│   └── ... (more)
├── static/                 # CSS/JS/images
├── templates/              # HTML pages (game.html, battle.html, etc.)
├── utilities/              # Game logic modules
│   ├── battle.py
│   ├── character.py
│   ├── crafting.py
│   ├── dungeons.py
│   └── ...
└── README.md
```

## Data File Overview

### Data-Driven
Edit `data/*.json` to mod content (classes, items, areas, enemies, bosses, missions, spells, crafting, dungeons, housing, farming, pets, shops).

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
  <strong>Forge your destiny in this browser-based RPG!</strong><br>
  <em>Built with ❤️ using Python/Flask</em>
</p>
