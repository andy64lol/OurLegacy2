# TODO — OLD TUI vs GUI Feature Parity

Features that exist in the original TUI (Our_Legacy) but are missing or incomplete in the GUI. For more use git clone https://github.com/andy64lol/Our_Legacy.git to see the repository.

---

## 🗓 Weekly Challenges
The TUI has a challenges system (`data/weekly_challenges.json`) with kill count, dungeon complete, boss defeat, level reach, and mission count challenges. Each awards EXP + gold on completion. The GUI has no challenge tracking or challenge screen.

## 🌦 Weather System
Each area has `weather_probabilities` (sunny/rainy/snowy/stormy). The weather updates on every explore and gives EXP/gold bonuses (e.g. stormy = +20% EXP and gold). The GUI has the data file but no weather is ever shown or applied.

## 🕰 Time-of-Day System
Time advances as you play (Dawn → Morning → Noon → Afternoon → Dusk → Evening → Night → Midnight). The TUI shows the current time period and uses it for immersion. The GUI has `data/times.json` but never uses it.

## ⚔ Manual Boss Challenge Menu
The TUI has a dedicated "Fight Boss" option (menu option 6) letting you pick a specific boss in the current area and fight it directly — with an 8-hour cooldown per boss. The GUI only has random boss encounters during exploration, with no way to intentionally challenge a boss.

## 💬 Boss Dialogue (Start & Defeat)
Bosses speak when battle begins and when they are defeated (`data/dialogues.json`, 30 entries). The GUI's battle screen never shows boss dialogue lines.

## 🎬 Cutscenes
Three cutscenes exist: `welcome_cutscene`, `first_area_enter`, `mission_accept_tutorial`. They support text, wait, and branching choices. The GUI never triggers any cutscene.

## 🪙 Claim Rewards (Explicit)
In the TUI, completing a mission does not automatically give rewards — you must go to the "Claim Rewards" menu option to collect EXP, gold, and items. The GUI auto-completes missions with no separation between completion and reward collection.

## 📊 Active Mission Progress Tracking
The TUI tracks kill-type and collect-type mission progress in real time (counting kills and collected items toward targets). The GUI only marks missions done all-at-once when the condition is met, with no incremental progress display.

## 🪨 Material Gathering During Exploration
When an explore action has no combat encounter, the TUI gives a 40% chance to gather crafting materials (1–3 items scaled to the area's difficulty tier). The GUI gives no loot on non-combat explores.

## 🏋 Training (Your Land)
The TUI has a Training menu option available at Your Land, letting the player train stats. The GUI's Your Land tab has no training system.

## 🏗 Build Structures (Your Land)
The TUI separates "Build Home" (furniture/housing items) from "Build Structures" (land structures like wells, stables, workshops). The GUI combines everything into one housing section.

## ✨ Status Effects in Battle
`data/effects.json` defines: poison, stun, blind, slow, defense_boost, speed_boost, shield, reveal, burn, freeze. Companion abilities and spells can apply these. The GUI battle system does not apply or display any status effects.

## 🔢 Multiple Accessory Slots
The TUI supports `accessory_1`, `accessory_2`, `accessory_3` — three accessory slots. The GUI only supports a single `accessory` slot.

## 🗺 Area Difficulty Display
The TUI shows each area's `difficulty` rating during travel, helping players gauge danger. The GUI's travel tab shows connections but not difficulty levels.

## 💰 Gold Finding During Exploration
On non-combat explores in the TUI, there is a 30% chance to find 5–20 gold on the ground. The GUI gives nothing on non-combat explores.

---

## Extra:
On saving and loading game, the game looks for a locally saved game but notice that we are playing on browser, which means player has to donwload and upload these save files.