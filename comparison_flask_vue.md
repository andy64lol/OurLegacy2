# Flask Classic vs Vue Beta — Full Comparison

## Architecture

| Aspect | Flask Classic | Vue Beta |
|---|---|---|
| Rendering | Server-side Jinja2 — full page reload on every action | Client-side Vue 3 (Options API) — single page, reactive |
| State delivery | Session + direct template variables per render | Unified JSON from `/api/game/state/extended`, polled every 2–7 s |
| Navigation | Standard HTTP links / redirects between pages | Tab switching within one layout, no page reloads |
| Action submission | HTML `<form>` POST → redirect | `fetch()` AJAX to `/api/action/*` → state refresh |
| Real-time events | Page reload or manual refresh | Auto-poll detects new messages, battle state, weather |
| Entry route | `/game` | `/beta` (admin/beta-flagged accounts only) |
| JS files | `game.js`, `spa.js` (progressive enhancement layer) | `vue_beta.js` |
| Template | `templates/game.html` + many sub-pages | `templates/vue_beta.html` (single monolithic template) |

---

## Pages / Tabs

### Flask Classic — Separate Pages

| URL | Purpose |
|---|---|
| `/` | Main menu / landing |
| `/play` | Server selection |
| `/create` | Character creation wizard |
| `/game` | Main gameplay hub (explore, rest, mine, shop, etc.) |
| `/battle` | Combat page |
| `/dungeons` | Dungeon selection list |
| `/dungeon/room` | Active dungeon room |
| `/crafting` | Crafting interface |
| `/market` | Elite Market trading |
| `/land/map` | Player land / housing map |
| `/land/shop` | Land shop (buy housing) |
| `/land/pets` | Pet management |
| `/friends` | Friends list & DMs |
| `/groups` | Group management |
| `/leaderboard` | Global leaderboard |
| `/wiki` | In-game wiki |
| `/chat` | Standalone chat |
| `/admin` | Admin dashboard |

### Vue Beta — Tabs Inside One Page

| Tab key | Label | Notes |
|---|---|---|
| `explore` | Explore | Default tab; area description, action buttons, boss panel, nearby players, event log |
| `battle` | Battle! | Auto-activates when combat starts; auto-returns to explore on victory/defeat |
| `equipment` | Equipment | Equipped gear slots, unequip buttons, auto-equip, quick-heal, sort inventory |
| `inventory` | Inventory | Full inventory list with equip / use / sell per item |
| `travel` | Travel | Connection list with difficulty, enemy & shop indicators |
| `shop` | Shop | Area shop; only shown when area has a shop |
| `mine` | Mine | Mining interface; only shown when area has a mine |
| `crafting` | Crafting | Recipe list with ingredient checks and craft button |
| `dungeons` | Dungeons | Available dungeons, active dungeon panel, abandon button |
| `market` | Market | Elite Market — lazy-loaded on first visit |
| `party` | Party | Companion hire/dismiss; companion HP/status |
| `quests` | Quests | Active missions with progress and claim button |
| `challenges` | Challenges | Active challenges with claim button |
| `diary` | Diary | Scrollable game diary log |
| `character` | Character | Stats, attribute points spending, XP progress |
| `events` | Events | Seasonal/timed events with eligibility and claim |
| `friends` | Friends | Friends list, incoming/outgoing requests — lazy-loaded |
| `group` | Group | Group info, member list, gold collection — lazy-loaded |

**Tabs missing from Vue Beta (Flask-only):**
- Land / Housing (`/land/map`, `/land/shop`, `/land/pets`) — no equivalent tab
- Wiki (`/wiki`)
- Leaderboard (separate page; Vue has `/api/social/leaderboard` data but no tab)
- Standalone Chat page (`/chat`)
- Admin dashboard (`/admin`)

---

## UI Elements

### Sidebar

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Player name + rank badge | Static text, rendered on page load | Reactive `[[ player.name ]]` + rank badge |
| Level | Static | Reactive |
| HP bar | Static bar, no animation | Animated CSS bar with colour transitions |
| MP bar | Static | Animated |
| EXP bar | Static | Animated with `[[ player.xp ]]/[[ player.xp_next ]]` |
| Gold | Static | Reactive |
| ATK / DEF / SPD stats | Listed in sidebar | Listed in sidebar |
| Pending attr points notice | Banner on game page | Inline notice in Equipment tab + Character tab |
| Current area name | Static | Reactive |
| Time of day | Text + icon | Text + icon (day/night glyph image) |
| Weather | Text | Text + bonus EXP/Gold percentages shown inline |
| Area description | Part of main panel | Short blurb under area name in sidebar |
| Active companions panel | Sidebar section | Sidebar section with HP bars and fallen state |
| Online indicator | Separate friends/status page | Sidebar badge with username when logged in |

### Battle UI

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Layout | Dedicated `/battle` page | Inline panel within the Explore tab; tab auto-switches |
| Enemy name + HP | Static bar | Animated HP bar |
| Boss indicator | Text label | Red `BOSS` badge |
| Battle log | Full log, re-rendered on reload | Scrollable log, updated each state poll |
| Companion HP in battle | Listed below enemy | Listed below enemy with fallen state |
| Attack button | Form POST | `@click="battleAttack"` AJAX |
| Defend button | Form POST | `@click="battleDefend"` AJAX |
| Flee button | Form POST | `@click="battleFlee"` AJAX |
| Use spell | Dropdown + form POST | Spell buttons appear only when player has MP; one click |
| Use consumable item | Dropdown + form POST | Consumable buttons shown inline; one click |
| Victory / Defeat | Redirects to `/victory` or `/defeat` page | Toast notification; state updates in place |

### Inventory & Equipment

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Inventory list | Table in `/game` page | `Inventory` tab — card grid with icons |
| Item stats | Shown in list | Shown in card |
| Item description | Shown in list | Shown in card |
| Equip item | Button per item → POST | `Equip` button per item → AJAX |
| Use consumable | Button per item → POST | `Use` button per item → AJAX |
| Sell item | Button per item → POST | `Sell` button per item → AJAX |
| Equipment slots | Listed in sidebar/game page | `Equipment` tab — slot grid with glyph icons |
| Unequip slot | Form POST per slot | `Unequip` button per slot → AJAX |
| Auto-equip | Button on game page | Button in Equipment tab |
| Quick Heal | Button on game page | Button in Equipment tab |
| Sort inventory | Button on game page | Button in Equipment tab |

### Character / Progression

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Attribute spending | Buttons on game page sidebar | Dedicated `Character` tab; attr points notice also shows in Equipment tab |
| Stats overview | Sidebar | `Character` tab — full stat table including derived stats |
| Class / Race | Shown on create page, static in game | Shown in Character tab |
| Spell list | Listed in game page | Listed in Character tab with MP cost |
| Mission list | Game page section | `Quests` tab with progress bars |
| Challenge list | Game page section | `Challenges` tab with progress bars |
| Event list | No equivalent UI in classic | `Events` tab with active/upcoming, eligibility, claim |

---

## Functions / Actions

### Exploration & World

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Explore | POST `/action/explore` → redirect | AJAX `/api/action/explore` |
| Rest | POST `/action/rest` → redirect | AJAX `/api/action/rest` |
| Mine | POST `/action/mine` → redirect | AJAX `/api/action/mine` |
| Travel | POST `/action/travel` → redirect | AJAX `/api/action/travel` (Travel tab) |
| Challenge boss | POST `/action/challenge_boss` → redirect | AJAX `/api/action/challenge_boss` (button on Explore tab) |

### Shopping & Economy

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Buy item from shop | POST `/action/buy` → redirect | AJAX `/api/action/buy` (Shop tab) |
| Sell item | POST `/action/sell` → redirect | AJAX `/api/action/sell` (Inventory tab) |
| View Elite Market | GET `/market` | `Market` tab lazy-loaded from `/api/market_data` |
| Buy from Elite Market | POST `/action/market/buy` | AJAX `/api/market/buy` |
| Reset Elite Market | POST `/action/market/reset` | Not exposed in Vue Beta |

### Crafting

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View recipes | GET `/crafting` | `Crafting` tab (inline) |
| Craft item | POST `/action/craft` → redirect | AJAX `/api/action/craft` |

### Dungeons

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View dungeon list | GET `/dungeons` | `Dungeons` tab (inline) |
| Enter dungeon | POST `/action/dungeon/enter` → redirect to `/dungeon/room` | AJAX `/api/action/dungeon/enter`; room URL pops up |
| Dungeon room navigation | GET `/dungeon/room` (full page) | Opens classic page via redirect (not yet SPA-ified) |
| Abandon dungeon | POST `/dungeon/abandon` | AJAX `/api/action/dungeon/abandon` |

### Combat

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Attack | POST `/battle/attack` | AJAX `/api/battle/attack` |
| Defend | POST `/battle/defend` | AJAX `/api/battle/defend` |
| Flee | POST `/battle/flee` | AJAX `/api/battle/flee` |
| Cast spell | POST `/battle/spell` | AJAX `/api/battle/spell` |
| Use item in battle | POST `/battle/use_item` | AJAX `/api/battle/use_item` |

### Companions

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Hire companion | POST `/action/hire_companion` | AJAX `/api/action/hire_companion` (Party tab) |
| Dismiss companion | POST `/action/dismiss_companion` | AJAX `/api/action/dismiss_companion` (Party tab) |

### Missions & Challenges

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Complete mission | POST `/action/complete_mission` | AJAX `/api/action/complete_mission` (Quests tab) |
| Claim challenge reward | POST `/action/claim_challenge` | AJAX `/api/action/claim_challenge` (Challenges tab) |

### Land / Housing (Flask Classic only)

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View land map | GET `/land/map` | **Not available** |
| Buy housing | POST `/action/land/buy_housing` | **Not available** |
| Place housing | POST `/action/land/place_housing` | **Not available** |
| Remove housing | POST `/action/land/remove_housing` | **Not available** |
| Plant crop | POST `/action/land/plant` | **Not available** |
| Harvest crop | POST `/action/land/harvest` | **Not available** |
| Rest at land | POST `/action/land/rest` | **Not available** |
| Store item in land | POST `/action/land/store_item` | **Not available** |
| Retrieve item from land | POST `/action/land/retrieve_item` | **Not available** |
| Craft at land | POST `/action/land/craft` | **Not available** |
| Buy pet | POST `/action/land/buy_pet` | **Not available** |
| Train pet | POST `/action/land/train` | **Not available** |

### Social

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View friends | GET `/friends` | `Friends` tab (lazy-loaded from `/api/friends/list`) |
| Send friend request | POST via `/friends` form | Not exposed in Vue Beta |
| Respond to request | POST via `/friends` form | Not exposed in Vue Beta |
| Remove friend | POST via `/friends` form | Not exposed in Vue Beta |
| Direct messages | GET `/api/dm/<other>` via friends page | Not exposed in Vue Beta |
| View group | GET `/groups` | `Group` tab (lazy-loaded from `/api/groups/info`) |
| Create group | POST via `/groups` form | Not exposed in Vue Beta |
| Join group | POST via `/groups` form | Not exposed in Vue Beta |
| Leave group | POST via `/groups` form | Not exposed in Vue Beta |
| Kick member | POST via `/groups` form | Not exposed in Vue Beta |
| Collect group gold | POST `/api/groups/collect_gold` | Not exposed in Vue Beta |
| Nearby players | Not shown on game page | Shown on Explore tab (up to 5 players) |

### Account / Save

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Save game (browser) | Button on game page → `/api/save` | Not exposed |
| Load game (browser) | Button on game page → `/api/load` | Not exposed |
| Cloud save | Button on game page | Not exposed |
| Cloud load | Button on game page | Not exposed |
| Settings (theme, music) | Settings panel on game page | Not exposed |
| Customize character | POST `/action/customize_character` | Not exposed |
| Spend attribute point | POST `/api/spend_attr_point` | AJAX `/api/spend_attr_point` (Character tab) |

---

## State Polling & Real-time Behaviour

| Behaviour | Flask Classic (`spa.js`) | Vue Beta |
|---|---|---|
| Poll interval | 5 s flat | 2 s in battle, 7 s out of battle |
| Battle auto-switch | `switchTab` called if `data.tab` arrives | `activeTab` set to `'battle'` when `in_battle` becomes true |
| Shop/mine tab auto-hide | No | Yes — tab switches away if area loses shop or mine |
| Toast notifications | `showToast()` from `game.js` | Built-in Vue toast system |
| HP warning | `initLowHpWarning()` from `game.js` | Not implemented |
| Diary quick-link | `switchTab('diary')` button in event log | `switchTab('diary')` button in event log |
| Event log | Sidebar section, updated on poll | Scrollable panel on Explore tab, updated on poll |

---

## API Endpoints: Vue Beta Uses vs Does Not Use

### Vue Beta calls these endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/game/state/extended` | Full state poll (player, battle, area, shop, mine, dungeon, etc.) |
| `POST /api/action/explore` | Explore area |
| `POST /api/action/rest` | Rest / use inn |
| `POST /api/action/mine` | Mine ore |
| `POST /api/action/travel` | Travel to area |
| `POST /api/action/buy` | Buy from shop |
| `POST /api/action/sell` | Sell item |
| `POST /api/action/equip` | Equip item |
| `POST /api/action/unequip` | Unequip slot |
| `POST /api/action/auto_equip` | Auto-equip best gear |
| `POST /api/action/use_item` | Use consumable |
| `POST /api/action/quick_heal` | Quick heal |
| `POST /api/action/sort_inventory` | Sort inventory |
| `POST /api/action/craft` | Craft item |
| `POST /api/action/hire_companion` | Hire companion |
| `POST /api/action/dismiss_companion` | Dismiss companion |
| `POST /api/action/complete_mission` | Complete mission |
| `POST /api/action/claim_challenge` | Claim challenge reward |
| `POST /api/action/challenge_boss` | Challenge a boss |
| `POST /api/action/dungeon/enter` | Enter dungeon |
| `POST /api/action/dungeon/abandon` | Abandon dungeon |
| `POST /api/battle/attack` | Battle: attack |
| `POST /api/battle/defend` | Battle: defend |
| `POST /api/battle/flee` | Battle: flee |
| `POST /api/battle/spell` | Battle: cast spell |
| `POST /api/battle/use_item` | Battle: use item |
| `POST /api/spend_attr_point` | Spend attribute point |
| `GET /api/market_data` | Load Elite Market listings |
| `POST /api/market/buy` | Buy from Elite Market |
| `GET /api/area_activity` | Nearby players |
| `GET /api/friends/list` | Friends list |
| `GET /api/groups/info` | Group info |

### Endpoints available but NOT used by Vue Beta

| Endpoint | Notes |
|---|---|
| `POST /api/action/land/*` (12 endpoints) | Full land/housing/farming/pets system |
| `POST /api/action/market/reset` | Market reset not exposed |
| `POST /api/online/register` / `login` / `logout` | Auth handled on classic login page |
| `POST /api/online/cloud_save` / `cloud_load` | Cloud save not in Vue Beta |
| `GET /api/save` / `POST /api/load` | Local browser save/load not exposed |
| `GET /api/saves/list` / `write` / `restore` | Save slot management not exposed |
| `POST /api/friends/request` / `respond` / `remove` | Friend management read-only in Vue Beta |
| `GET /api/dm/<other>` / `POST /api/dm/send` | DM system not in Vue Beta |
| `POST /api/block` | Block user not in Vue Beta |
| `POST /api/groups/create` / `join` / `leave` / `kick` / `collect_gold` | Group management not exposed |
| `GET /api/social/leaderboard` | Data available, no tab |
| `GET /api/social/chat` | Chat widget not in Vue Beta |
| `POST /api/settings` | Theme/music settings not in Vue Beta |
| `POST /action/customize_character` | Character customisation not in Vue Beta |
| `GET /api/catalog/*` (10 endpoints) | Wiki/catalog not in Vue Beta |
| `GET /api/player/land` | Land data not in Vue Beta |
| `GET /api/world/challenges` / `events` / `weather` | Some redundant with extended state |

---

## Summary: What Vue Beta Has That Flask Classic Lacks

- Reactive animated HP/MP/EXP bars
- Auto-tab switching on battle start/end
- Auto-hide of Shop/Mine tabs when not in relevant area
- Boss cooldown display inline on Explore tab
- Nearby players on Explore tab
- Seasonal Events tab
- Per-poll adaptive polling interval (faster in battle)
- All actions without page reload (no flash/jump)

## Summary: What Flask Classic Has That Vue Beta Lacks

- Full land, housing, farming, and pet systems
- Friend request send/respond/remove
- Direct messaging (DMs)
- User blocking
- Group creation/join/leave/kick/gold-collection
- Local browser save/load and cloud save/load
- Save slot management
- Theme, music, and UI settings panel
- Character customization
- Wiki / item catalog
- Leaderboard page
- Standalone chat page
- HP low warning system
