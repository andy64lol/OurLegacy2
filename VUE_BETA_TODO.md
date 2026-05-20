# Vue Beta vs Jinja2 — Feature Comparison & TODO

> **Status key:** ✅ Done · 🔧 Partial · ❌ Missing · ⚠️ Broken

---

## Core UI Shell

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Sidebar with player stats | ✅ | ✅ | ✅ Done | HP/MP/EXP/Gold bars |
| Sidebar HP/MP/EXP bars animate | ✅ | ✅ | ✅ Done | |
| Low-HP pulse on bars | ✅ | ✅ | ✅ Done | |
| Day/night glyph in sidebar | ✅ | ✅ | ✅ Done | |
| Weather bonus display | ✅ | ✅ | ✅ Done | |
| Companion HP bars in sidebar | ✅ | ✅ | ✅ Done | |
| Sidebar collapsible (toggle btn) | ✅ | ✅ | ✅ Done | game.js `initSidebarToggle` |
| News ticker | ✅ | ✅ | ✅ Done | Loads `/api/announcements` |
| Tab bar with overflow "..." dropdown | ✅ | 🔧 | ✅ Fixed | Added `id="main-tabs"` + `data-tab` attrs |
| Toast notifications (HTML-formatted) | ✅ | ⚠️ | ✅ Fixed | Was text-only; now `v-html` |
| Settings modal (audio/bg/theme/fullscreen) | ✅ | ✅ | ✅ Done | Modal present, `openSettings()` wired |
| Background music | ✅ | ✅ | ✅ Done | `<audio id="bg-music">` present |
| Floating chat button | ✅ | ⚠️ | ✅ Fixed | `toggleChat()` was undefined; now defined |
| Global chat panel (iframe) | ✅ | ⚠️ | ✅ Fixed | Now loads `/chat_widget` on open |
| Resize handle for sidebar | ✅ | ✅ | ✅ Done | `#sidebar-resize-handle` present |

---

## Map & Navigation

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Area map image (per-zone) | ✅ | ⚠️ | ✅ Fixed | `map_image` now returned from API |
| Dedicated Map tab | ✅ | ❌ | ✅ Fixed | New Map tab with area image + explored areas |
| Visited areas list on map | ✅ | ❌ | ✅ Fixed | Shows all explored zones with quick-travel |
| Connections/nearby areas | ✅ | ✅ | ✅ Done | In Travel tab and now also in Map tab |
| Travel between areas | ✅ | ✅ | ✅ Done | |
| Fog of war (unvisited = ???) | ✅ | ✅ | ✅ Done | |

---

## Explore & Combat

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Explore action | ✅ | ✅ | ✅ Done | |
| Rest at inn / on land | ✅ | ✅ | ✅ Done | |
| Boss challenges | ✅ | ✅ | ✅ Done | Cooldown timers shown |
| Nearby player sightings | ✅ | ✅ | ✅ Done | Online only |
| Battle tab (auto-switch on battle) | ✅ | ✅ | ✅ Done | |
| Enemy glyph/image in battle | ✅ | ✅ | ✅ Done | |
| Enemy HP bar + % | ✅ | ✅ | ✅ Done | |
| Round counter + boss badge | ✅ | ✅ | ✅ Done | |
| Spell type color buttons | ✅ | ✅ | ✅ Done | |
| Battle log auto-scroll | ✅ | ✅ | ✅ Done | Vue watcher |
| Use consumable in battle | ✅ | ✅ | ✅ Done | |
| Companion display in battle | ✅ | ✅ | ✅ Done | |
| Critical HP warning banner | ✅ | ✅ | ✅ Done | |

---

## Inventory, Equipment & Items

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Inventory list with rarity colors | ✅ | ✅ | ✅ Done | |
| Inventory pagination | ❌ | ✅ | ✅ Done | Vue has 15 items/page |
| Item type glyphs | ✅ | ✅ | ✅ Done | |
| Equip/Use/Sell buttons | ✅ | ✅ | ✅ Done | |
| Equipment slot grid | ✅ | ✅ | ✅ Done | |
| Auto-equip button | ✅ | ✅ | ✅ Done | |
| Quick heal button | ✅ | ✅ | ✅ Done | |
| Sort inventory button | ✅ | ✅ | ✅ Done | |
| Equipped item details | ✅ | ✅ | ✅ Done | |

---

## Economy

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Shop with rarity colors | ✅ | ✅ | ✅ Done | |
| Shop pagination | ❌ | ✅ | ✅ Done | Vue has 15 items/page |
| "Can't afford" indicator | ✅ | ✅ | ✅ Done | |
| Sale/discount badge | ✅ | ✅ | ✅ Done | |
| Market (player-to-player) | ✅ | ✅ | ✅ Done | |
| Market pagination | ❌ | ✅ | ✅ Done | Vue has 20 items/page |
| Market refresh button | ✅ | ✅ | ✅ Done | |
| Market admin reset | ✅ | ✅ | ✅ Done | |

---

## Crafting & Mining

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Recipe list with materials | ✅ | ✅ | ✅ Done | |
| Recipe pagination | ❌ | ✅ | ✅ Done | Vue has 12 recipes/page |
| Recipe rarity colors | ✅ | ✅ | ✅ Done | |
| "Missing" label when can't craft | ✅ | ✅ | ✅ Done | |
| Mine tab (conditional) | ✅ | ✅ | ✅ Done | |

---

## Housing / Land

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Land tab only shows in Your Land area | ✅ | ❌ | ✅ Fixed | Now uses `area.key === 'your_land'` |
| Land map iframe | ✅ | ✅ | ✅ Done | |
| Land shop iframe | ✅ | ✅ | ✅ Done | |
| Land pets iframe | ✅ | ✅ | ✅ Done | |
| "Travel to Your Land" prompt when not there | ✅ | ❌ | ✅ Fixed | Shows travel button when not in land |
| Housing build/remove controls | ✅ | 🔧 | ❌ TODO | Currently iframe only; no native Vue UI |

---

## Social

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Friends list | ✅ | ✅ | ✅ Done | |
| Group info | ✅ | ✅ | ✅ Done | |
| Online player count | ✅ | 🔧 | ❌ TODO | `onlineCount` in data but not displayed in sidebar |
| World events feed | ✅ | 🔧 | ❌ TODO | `worldEvents` stored but no tab for it |

---

## Quests, Challenges & Progression

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Missions/Quests tab | ✅ | ✅ | ✅ Done | |
| Weekly challenges | ✅ | ✅ | ✅ Done | Progress bars |
| Events (active/upcoming) | ✅ | ✅ | ✅ Done | |
| Diary/journal with pagination | ✅ | ✅ | ✅ Done | 30 entries/page |
| Character stats & attributes | ✅ | ✅ | ✅ Done | Spend attribute points |
| Companion hire/dismiss | ✅ | ✅ | ✅ Done | |
| Dungeons | ✅ | ✅ | ✅ Done | |
| Party tab | ✅ | ✅ | ✅ Done | |

---

## Save System

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Auto-save heartbeat | ✅ | ✅ | ✅ Done | |
| Save slot UI (cloud slots 1–5) | ✅ | ❌ | ❌ TODO | Not implemented in Vue beta |
| Download save file (.json) | ✅ | ❌ | ❌ TODO | `game.js` has this; not wired in Vue |
| Upload/restore save file | ✅ | ❌ | ❌ TODO | |
| Save & exit to main menu | ✅ | ❌ | ❌ TODO | Only "Exit to Menu" link, no server save |

---

## Leaderboard & Wiki

| Feature | Jinja2 | Vue Beta | Status | Notes |
|---|---|---|---|---|
| Leaderboard (iframe) | ✅ | ✅ | ✅ Done | |
| Wiki (iframe) | ✅ | ✅ | ✅ Done | |

---

## Remaining TODOs (Prioritized)

### 🔴 High Priority
- [ ] **Save slots UI** — Surface the cloud save system (slots 1–5, download, upload) in the Vue beta sidebar or a dedicated Settings sub-panel
- [ ] **Online player count** — Show `onlineCount` in sidebar status row
- [ ] **World events feed** — Display `worldEvents` (e.g. in Explore or Events tab)
- [ ] **Save & exit button** — Add server-side save + menu redirect in sidebar

### 🟡 Medium Priority
- [ ] **Native housing controls** — Replace pure iframe with native Vue build/manage UI using `/api/player/land`
- [ ] **Party tab content** — Currently a stub; wire to group combat API
- [ ] **Paginate diary newest-page-last option** — Let user toggle sort order
- [ ] **More glyph coverage** — Tab buttons for Quests, Crafting, Diary, Events could use glyphs from `/game_assets/glyphs/`

### 🟢 Low Priority / Polish
- [ ] **Keyboard shortcuts** — E=explore, B=battle, I=inventory etc.
- [ ] **Mobile optimisation** — Sidebar auto-collapse on small screens (partially done via `initSidebarToggle`)
- [ ] **Dungeon room transitions** — Currently redirects to full page; could be inline modal
- [ ] **Item texture preview** — Items have `texture` field from API; show small thumb in inventory rows
