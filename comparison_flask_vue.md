# Flask Classic (`/game`) vs Vue Beta (`/beta`) — Full Differences

## Architecture

| Aspect | Flask Classic (`/game`) | Vue Beta (`/beta`) |
|---|---|---|
| Template | `templates/index.html` (extends `base.html`) | `templates/vue_beta.html` (standalone) |
| Rendering | Server-side Jinja2; full-page reload on every action | Vue 3 (Options API) SPA; state polled via JSON, no reloads |
| State delivery | Session variables injected at render time as Jinja2 variables | Single JSON blob from `GET /api/game/state/extended`, polled every 2–7 s |
| Template delimiters | `{{ }}` (Jinja2) | `[[ ]]` (Vue, to avoid Jinja2 conflict) |
| Navigation | Standard HTTP links + form POSTs → redirect | Tab switching, no page reloads |
| Action submission | HTML `<form>` POST → server redirect | `fetch()` AJAX to `/api/action/*` endpoints |
| Entry route | `/game` (all accounts) | `/beta` (admin/beta-flagged accounts only) |
| JS file | `static/js/game.js` | `static/js/vue_beta.js` |
| State polling | `spa.js` polling (5 s flat) | `vue_beta.js` polling (2 s in battle, 7 s out of battle) |

---

## Persistence & Session Model

| Aspect | Flask Classic | Vue Beta |
|---|---|---|
| Primary persistence | `ol2_characters` (JSONB game_state) via `_autosave()` | `ol2_characters` (JSONB game_state) via `_autosave()` + 30 s heartbeat |
| Save on login | Login API calls `character_autoload()`, restores full session from DB | Same — shared backend |
| Save on logout | `logoutAndSave()` calls `POST /api/online/logout` which calls `_autosave()` | Same |
| Save on every action | Server calls `_autosave()` on every significant event | Server calls `_autosave()` on every significant event |
| Save on heartbeat | 5-minute `setInterval` → `POST /api/online/autosave` (silent) | 30-second `setInterval` → `POST /api/online/autosave` (silent) |
| Save buttons | None — progress saved automatically | None — progress saved automatically |
| Save indicator | `● Progress saved automatically` in sidebar + Settings | `● Progress auto-saves` in sidebar |
| Exit button label | "Exit to Menu" | Sidebar "Exit to Menu" link |
| Guest persistence | None — guests have no account to save to | N/A (requires login) |
| Old encrypted blob system (`ol2_saves`) | Deprecated — routes exist but not called by UI | Deprecated — routes exist but not called by UI |
| Session slots (`_save_slots`) | Removed from `_autosave()` and DB state | Not present |
| `_AUTOSAVE_DIARY_INTERVAL` spam | Removed — no "Progress autosaved." diary entry | Not present |

---

## Pages / Tabs

### Flask Classic — Multiple pages, tab bar within `/game`

| URL | Purpose |
|---|---|
| `/` | Main menu / landing |
| `/play` | Server selection |
| `/create` | Character creation wizard |
| `/game` | Main SPA hub — tab bar with all gameplay tabs |
| `/dungeon/room` | Active dungeon room (full page) |
| `/land/map` | Player land / housing map |
| `/land/shop` | Land shop (buy housing) |
| `/land/pets` | Pet management |
| `/friends` | Friends list & DMs |
| `/groups` | Group management |
| `/leaderboard` | Global leaderboard |
| `/wiki` | In-game wiki |
| `/chat` | Standalone chat |
| `/admin` | Admin dashboard |
| `/battle` | Battle page (integrated in game tab bar) |
| `/dungeons` | Dungeon list (integrated in game tab bar) |
| `/crafting` | Crafting (integrated in game tab bar) |
| `/market` | Elite Market (integrated in game tab bar) |
| `/victory`, `/defeat` | Post-battle screens |

### Vue Beta — Tabs inside one page (`/beta`)

| Tab key | Label | Notes |
|---|---|---|
| `explore` | Explore | Default; area description, action buttons, boss panel, nearby players, event log |
| `battle` | Battle! | Auto-activates when combat starts; auto-returns to explore on end |
| `equipment` | Equipment | Gear slots, unequip, auto-equip, quick-heal, sort inventory |
| `inventory` | Inventory | Full inventory with equip / use / sell per item |
| `travel` | Travel | Area connections with difficulty, enemy & shop indicators |
| `shop` | Shop | Area shop; only shown when area has a shop |
| `mine` | Mine | Mining interface; only shown when area has a mine |
| `crafting` | Crafting | Recipe list with ingredient checks and craft button |
| `dungeons` | Dungeons | Available dungeons, active dungeon panel, abandon button |
| `market` | Market | Elite Market — lazy-loaded on first visit |
| `party` | Party | Companion hire/dismiss; companion HP/status |
| `quests` | Quests | Active missions with progress and claim button |
| `challenges` | Challenges | Active challenges with claim button |
| `diary` | Diary | Scrollable game diary log |
| `character` | Character | Stats, attribute point spending, XP progress |
| `events` | Events | Seasonal/timed events with eligibility and claim |
| `friends` | Friends | Friends list, incoming/outgoing requests — lazy-loaded |
| `group` | Group | Group info, member list, gold collection — lazy-loaded |

**Only in Flask Classic (no Vue tab equivalent):**
- Land / Housing (`/land/map`, `/land/shop`, `/land/pets`)
- Wiki (`/wiki`)
- Leaderboard (separate page; Vue has `/api/social/leaderboard` data but no tab)
- Standalone Chat (`/chat`)
- Admin dashboard (`/admin`)

---

## UI Elements — Sidebar

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Player name + class glyph | Jinja2 rendered, static | Reactive `[[ player.name ]]` + dynamic glyph |
| Rank badge | Injected server-side | Reactive |
| Level | Static at render time | Reactive |
| HP bar | CSS bar, static width from server | Animated CSS bar with `:style` binding + colour transitions |
| MP bar | Static CSS bar | Animated |
| EXP bar | Static | Animated with `[[ player.experience ]]/[[ player.experience_to_next ]]` |
| Gold | Static | Reactive |
| ATK/DEF/SPD | Mini grid in sidebar | Mini grid in sidebar |
| Race | Shown below class | Shown below class |
| Pending attr points notice | Banner in game page | Inline notice in Equipment + Character tabs |
| Current area name | Separate Location panel | Location panel in sidebar |
| Area short description | Location panel (first 110 chars) | Location panel (first 110 chars) |
| Time of day | Text + icon | Text + day/night glyph image |
| Weather | Text + bonus EXP/Gold display | Text + bonus EXP/Gold percentages inline |
| Active companions panel | Sidebar section with HP bars | Sidebar section with HP bars + fallen state |
| Online indicator | Username + chat glyph + `● Progress saved automatically` | Username + chat glyph + `● Progress auto-saves` |
| Navigate shortcuts | Dungeons / Crafting / Elite Market buttons | Same |
| Exit button | "Exit to Menu" (`logoutAndSave()` for online / `saveAndQuit()` for guest) | "Exit to Menu" link (`href="/"`) |
| Settings button | Present (`openSettings()`) | Not present in Vue sidebar |
| Resize handle | Draggable sidebar resize handle | Same |

---

## UI Elements — Battle

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Layout | Tab panel within `/game` | Tab panel within `/beta` |
| Enemy name + HP | Static bar | Animated HP bar + percentage |
| Boss indicator | Text label | Red `BOSS` badge |
| Battle log | Scrollable, max 14 entries shown | Scrollable, max-height 180 px, `v-html` text with colors |
| Companion HP in battle | Listed below enemy | Listed below enemy with fallen state |
| Attack | Form POST | `@click="battleAttack"` AJAX |
| Defend | Form POST | `@click="battleDefend"` AJAX |
| Flee | Form POST | `@click="battleFlee"` AJAX |
| Spell | Dropdown + form POST | Spell buttons, one per available spell |
| Consumable | Dropdown + form POST | Inline consumable buttons |
| Victory / Defeat | Redirects to `/victory` or `/defeat` | Toast + in-place state update, no redirect |

---

## UI Elements — Inventory & Equipment

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Inventory list | Table in game tab | Card grid in Inventory tab |
| Item icon | Shown | Shown |
| Item stats/description | Shown | Shown |
| Equip | Button → form POST | `Equip` button → AJAX |
| Use consumable | Button → form POST | `Use` button → AJAX |
| Sell item | Button → form POST | `Sell` button → AJAX |
| Equipment slots grid | In game tab | In Equipment tab |
| Unequip | Form POST per slot | `Unequip` button → AJAX |
| Auto-equip | Button | Button in Equipment tab |
| Quick Heal | Button | Button in Equipment tab |
| Sort inventory | Button | Button in Equipment tab |
| Item rarity colours | Rendered server-side | CSS classes: `.rarity-common`, `.rarity-rare`, etc. |

---

## UI Elements — Character / Progression

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Attribute spending | Buttons in game page | Character tab; also notice in Equipment tab |
| Stats overview | Sidebar | Character tab — full 3-column stat-card grid |
| Derived stats (crit, dodge, etc.) | Not in sidebar | Shown in Character tab |
| Class / Race | Shown at top of character panel | Shown in Character tab |
| Spell list | Listed in game page | Listed in Character tab with MP cost |
| Mission list | Game page section | Quests tab with progress bars |
| Challenge list | Game page section | Challenges tab with progress bars |
| Event list | Game page section | Events tab with active/upcoming, eligibility, claim |

---

## UI Elements — Settings Panel

| Element | Flask Classic | Vue Beta |
|---|---|---|
| Accessible via | `openSettings()` button in sidebar | Not exposed |
| Themes | Full list (default, parchment, night, crimson, midnight, amethyst) | Not exposed |
| Background image | Selectable | Not exposed |
| Button style | Selectable | Not exposed |
| UI scale | Selectable | Not exposed |
| Music volume | Slider | Not exposed |
| Music muted | Toggle | Not exposed |
| BGM track | Selectable | Not exposed |
| Account section | "Save & Log Out" button | Not exposed |
| Save slots | **Removed** — no longer in Settings | Not present |
| Cloud download | Available in settings | Not exposed |

---

## Diary / Event Log Text Rendering

| Aspect | Flask Classic | Vue Beta |
|---|---|---|
| Diary entry format | `{"text": "...", "color": "..."}` objects | Same |
| Diary rendering | Jinja2: `{{ entry.text }}` + style | Vue: `v-html="typeof entry === 'object' ? entry.text : entry"` + `:style` |
| Battle log rendering | Jinja2: `{{ entry }}` | Vue: `v-html="msg.text"` + `:style="{ color: msg.color }"` |
| Recent events rendering | Jinja2: `{{ entry }}` | Vue: `v-html="typeof entry === 'object' ? entry.text : entry"` + merged `:style` |
| Diary fallback messages | Jinja2 text | Vue: `v-html` fallback |
| HTML in diary entries | Rendered by browser (Jinja2 raw) | Rendered by `v-html` |

---

## State Polling & Real-time Behaviour

| Behaviour | Flask Classic (`spa.js`) | Vue Beta (`vue_beta.js`) |
|---|---|---|
| Poll interval | 5 s flat | 2 s in battle, 7 s out of battle |
| Poll endpoint | `GET /api/game/state` | `GET /api/game/state/extended` |
| Battle auto-switch | `switchTab` called if `data.tab` arrives | `activeTab` set to `'battle'` when `in_battle` becomes true |
| Battle auto-return | On victory/defeat redirect | `activeTab` returns to `'explore'` automatically |
| Shop/mine tab auto-hide | No | Yes — tab switches away if area loses shop or mine |
| Toast notifications | `showToast()` from `game.js` | Built-in Vue toast array with `v-for` |
| HP low warning | `initLowHpWarning()` from `game.js` (CSS `.low-hp`) | Not implemented |
| Diary quick-link | `switchTab('diary')` button in event log | `switchTab('diary')` button in event log |
| Event log | Sidebar section, updated on poll | Scrollable panel on Explore tab, updated on poll |
| Nearby players | Not shown in game | Shown in Explore tab (up to 5 players) |
| Boss cooldown display | In game page | Inline on Explore tab per boss |
| Session check interval | 30 s (`checkSession` in `spa.js`) | Not explicit (handled by state polls) |
| Autosave heartbeat | 5-minute silent `POST /api/online/autosave` | 30-second silent `POST /api/online/autosave` |

---

## Login / Character Load Flow

| Step | Flask Classic | Vue Beta |
|---|---|---|
| 1. User submits credentials | `onlineLogin()` → `POST /api/online/login` | Same form → Same endpoint |
| 2. Backend on login | `login_user()` verifies password → sets session tokens → calls `character_autoload()` → calls `_apply_game_state()` | Same backend |
| 3. Response | `{ ok, username, character_loaded }` | Same response |
| 4. Frontend routing | `autoPlayAfterLogin(json)`: if `character_loaded` → `/game`, else → `/create` | `autoPlayAfterLogin(json)`: if `character_loaded` → `/beta` (or `/game`) |
| 5. On page load | `GET /game` checks session → already has player in session | `GET /beta` → Vue polls `/api/game/state/extended` |
| Old flow (removed) | `cloud_meta` → `cloud_load` manual calls after login | `cloud_save` / `cloud_load` manual calls |

---

## Functions / Actions

### Exploration & World

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Explore | POST `/action/explore` → redirect | AJAX `/api/action/explore` |
| Rest | POST `/action/rest` → redirect | AJAX `/api/action/rest` |
| Mine | POST `/action/mine` → redirect | AJAX `/api/action/mine` |
| Travel | POST `/action/travel` → redirect | AJAX `/api/action/travel` (Travel tab) |
| Challenge boss | POST `/action/challenge_boss` → redirect | AJAX `/api/action/challenge_boss` (Explore tab) |

### Shopping & Economy

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Buy from shop | POST `/action/buy` → redirect | AJAX `/api/action/buy` (Shop tab) |
| Sell item | POST `/action/sell` → redirect | AJAX `/api/action/sell` (Inventory tab) |
| View Elite Market | Market tab (lazy-loaded from `/api/market_data`) | Market tab (lazy-loaded from `/api/market_data`) |
| Buy from Elite Market | POST `/api/market/buy` | AJAX `/api/market/buy` |
| Reset Elite Market | POST `/action/market/reset` (Settings) | Not exposed |

### Crafting

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View recipes | Crafting tab | Crafting tab |
| Craft item | POST `/action/craft` → redirect | AJAX `/api/action/craft` |

### Dungeons

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View dungeon list | Dungeons tab | Dungeons tab |
| Enter dungeon | POST `/action/dungeon/enter` → redirect to `/dungeon/room` | AJAX `/api/action/dungeon/enter`; opens `/dungeon/room` |
| Dungeon room navigation | `GET /dungeon/room` (full page) | `GET /dungeon/room` (full page, not SPA-ified) |
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
| Hire companion | POST `/action/hire_companion` → redirect | AJAX `/api/action/hire_companion` (Party tab) |
| Dismiss companion | POST `/action/dismiss_companion` → redirect | AJAX `/api/action/dismiss_companion` (Party tab) |

### Missions & Challenges

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Complete mission | POST `/action/complete_mission` → redirect | AJAX `/api/action/complete_mission` (Quests tab) |
| Claim challenge reward | POST `/action/claim_challenge` → redirect | AJAX `/api/action/claim_challenge` (Challenges tab) |

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
| Store item | POST `/action/land/store_item` | **Not available** |
| Retrieve item | POST `/action/land/retrieve_item` | **Not available** |
| Craft at land | POST `/action/land/craft` | **Not available** |
| Buy pet | POST `/action/land/buy_pet` | **Not available** |
| Train pet | POST `/action/land/train` | **Not available** |

### Social

| Action | Flask Classic | Vue Beta |
|---|---|---|
| View friends | Friends tab (lazy-loaded from `/api/friends/list`) | Friends tab (lazy-loaded from `/api/friends/list`) |
| Send friend request | POST via form in `/friends` page | Not exposed |
| Respond to request | POST via form | Not exposed |
| Remove friend | POST via form | Not exposed |
| Direct messages | `/api/dm/<other>` via friends page | Not exposed |
| View group | Group tab (lazy-loaded from `/api/groups/info`) | Group tab (lazy-loaded from `/api/groups/info`) |
| Create group | POST via `/groups` form | Not exposed |
| Join group | POST via `/groups` form | Not exposed |
| Leave group | POST via `/groups` form | Not exposed |
| Kick member | POST via `/groups` form | Not exposed |
| Collect group gold | POST `/api/groups/collect_gold` | Not exposed |
| Nearby players | Not shown | Shown in Explore tab (up to 5 players from `/api/area_activity`) |

### Account / Save

| Action | Flask Classic | Vue Beta |
|---|---|---|
| Save game (file download) | Available for guests via `saveAndQuit()` | Not exposed |
| Load game (file upload) | **Removed** — no longer in sidebar | Not exposed |
| Cloud save manual | **Removed** — automatic only | **Removed** — automatic only |
| Cloud load manual | **Removed** — automatic on login | **Removed** — automatic on login |
| Settings (theme, music) | `openSettings()` button in sidebar | Not exposed |
| Customize character | POST `/action/customize_character` | Not exposed |
| Spend attribute point | POST `/api/spend_attr_point` | AJAX `/api/spend_attr_point` (Character tab) |
| Log Out | "Save & Log Out" in Settings → `logoutAndSave()` | Not exposed (use `/` link) |

---

## API Endpoints: Vue Beta Uses vs Does Not Use

### Vue Beta calls these endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/game/state/extended` | Full state poll |
| `POST /api/action/explore` | Explore area |
| `POST /api/action/rest` | Rest / inn |
| `POST /api/action/mine` | Mine ore |
| `POST /api/action/travel` | Travel |
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
| `POST /api/action/claim_challenge` | Claim challenge |
| `POST /api/action/challenge_boss` | Challenge boss |
| `POST /api/action/dungeon/enter` | Enter dungeon |
| `POST /api/action/dungeon/abandon` | Abandon dungeon |
| `POST /api/battle/attack` | Battle: attack |
| `POST /api/battle/defend` | Battle: defend |
| `POST /api/battle/flee` | Battle: flee |
| `POST /api/battle/spell` | Battle: spell |
| `POST /api/battle/use_item` | Battle: item |
| `POST /api/spend_attr_point` | Spend attribute point |
| `GET /api/market_data` | Market listings |
| `POST /api/market/buy` | Buy from Market |
| `GET /api/area_activity` | Nearby players |
| `GET /api/friends/list` | Friends list |
| `GET /api/groups/info` | Group info |
| `POST /api/online/autosave` | Heartbeat (silent, every 30 s) |

### Endpoints available but NOT used by Vue Beta

| Endpoint | Notes |
|---|---|
| `POST /api/action/land/*` (12 endpoints) | Full land/housing/farming/pets system |
| `POST /api/action/market/reset` | Market reset not exposed |
| `POST /api/online/register` / `login` / `logout` | Auth on landing page, not in Vue |
| `POST /api/online/cloud_save` / `cloud_load` | Deprecated — UI removed from both versions |
| `GET /api/save` / `POST /api/load` | Guest file save/load — Classic only |
| `GET /api/saves/list` / `write` / `restore` | Save slot system — still in backend but no UI |
| `POST /api/friends/request` / `respond` / `remove` | Friend management not in Vue Beta |
| `GET /api/dm/<other>` / `POST /api/dm/send` | DM system not in Vue Beta |
| `POST /api/block` | Block not in Vue Beta |
| `POST /api/groups/create` / `join` / `leave` / `kick` / `collect_gold` | Group management not in Vue Beta |
| `GET /api/social/leaderboard` | Data available, no tab in Vue Beta |
| `GET /api/social/chat` | Chat widget not in Vue Beta |
| `POST /api/settings` | Theme/music settings not in Vue Beta |
| `POST /action/customize_character` | Character customisation not in Vue Beta |
| `GET /api/catalog/*` (10 endpoints) | Wiki/catalog not in Vue Beta |
| `GET /api/player/land` | Land data not in Vue Beta |
| `GET /api/world/challenges` / `events` / `weather` | Redundant with extended state |

---

## Tiny Differences: Flask Classic vs Vue Beta

### Login flow
- Classic: `onlineLogin()` → `POST /api/online/login` → `autoPlayAfterLogin(json)` reads `json.character_loaded` → `/game` or `/create`
- Vue: Same login API → `autoPlayAfterLogin(json)` → `/beta` or `/create`
- **Old flow (removed from both):** After login, JS called `GET /api/online/cloud_meta` then `POST /api/online/cloud_load` manually. Now the login endpoint itself calls `character_autoload()` + `_apply_game_state()` server-side and returns `character_loaded: true/false`.

### `autoPlayAfterLogin()` signature
- Classic: `function autoPlayAfterLogin(loginJson)` — synchronous, no `async`/`await`, reads `loginJson.character_loaded`
- Vue Beta: Same pattern

### Autosave heartbeat interval
- Classic: 5 minutes (300,000 ms)
- Vue Beta: 30 seconds (30,000 ms)

### `_autosave()` diary log
- **Removed from both**: No longer appends "Progress autosaved." to diary at any interval

### `_autosave()` save slot update
- **Removed**: No longer calls `_update_save_slot(1, "Auto Save", state)` on every autosave

### `_save_slots` injection into game_state
- **Removed**: `_autosave()` no longer injects `_save_slots` into the JSONB blob before writing to DB

### `_apply_game_state()` save slot restore
- **Removed**: No longer reads `_save_slots` from the DB blob and sets `session["_save_slots"]`

### Sidebar save indicator
- Classic: `● Progress saved automatically` (green, 11 px, below username)
- Vue Beta: `● Progress auto-saves` (green, below username)

### Sidebar "Load Game" button
- Classic: **Removed** — no longer shown for any user
- Vue Beta: Never present

### Settings save slots section
- Classic: **Removed** — `#saves-slot-list` div gone; no "Save Slots" heading in Settings modal
- Vue Beta: Never present

### Settings account section text
- Classic: "Save & Log Out" button (calls `logoutAndSave()`)
- Vue Beta: Settings modal not exposed at all

### Sidebar exit button
- Classic: "Exit to Menu" (`logoutAndSave()` for online / `saveAndQuit()` for guest)
- Vue Beta: `<a href="/">Exit to Menu</a>` link

### "Save to Exit" label (old) vs "Exit to Menu" (new)
- Old Classic label was "Save to Exit" — renamed to "Exit to Menu" for both online and guest buttons

### `cloud-save-status` div
- Classic: **Removed** — `<div id="cloud-save-status">` no longer in sidebar
- Vue Beta: Never present

### `logoutAndSave()` implementation
- **Old:** `POST /api/online/cloud_save` → wait → toast → redirect after 1.2 s
- **New (Classic):** `POST /api/online/logout` (triggers `_autosave()` server-side) → redirect to `/` immediately; shows "Saving & exiting..." toast for 1.5 s
- Vue Beta: Same new pattern

### `onlineLogout()` function (landing page)
- Still exists as `await fetch('/api/online/logout', {method:'POST'}); window.location.reload();` — used only if you want to log out without saving (from Settings)

### Session heartbeat toast
- Classic: **Removed** — heartbeat `setInterval` no longer calls `showToast()`; it silently fires `POST /api/online/autosave`
- Vue Beta: Same — no toast on autosave

### Battle log text rendering
- Classic: `{{ entry }}` — strings rendered via Jinja2
- Vue Beta: `v-html="msg.text"` + `:style="{ color: msg.color }"` — HTML-safe with inline color

### Diary entry rendering
- Classic: `{{ entry.text }}` + `style` attribute from Jinja2
- Vue Beta: `v-html="typeof entry === 'object' ? entry.text : entry"` + `:style` for color

### Recent events log rendering
- Classic: String entries rendered inline
- Vue Beta: `v-html` + merged `:style` (avoids dual-style conflict)

### HP low warning
- Classic: `initLowHpWarning()` adds CSS class `.low-hp` to HP bars ≤ 25%
- Vue Beta: Not implemented — no low-HP visual warning

### `_AUTOSAVE_DIARY_INTERVAL` constant
- Classic: Still defined in `app.py` (300 s) but unused — diary spam removed
- Vue Beta: Not referenced

### Battle tab animation
- Classic: Tab pulses red using CSS `@keyframes pulse-tab` on `.vtab-battle`
- Vue Beta: Same class and animation

### Polling endpoint
- Classic: `GET /api/game/state` (base state)
- Vue Beta: `GET /api/game/state/extended` (extended state including shop, mine, dungeon, spell data)

### Victory / Defeat handling
- Classic: Server redirects to `/victory` or `/defeat` (full pages)
- Vue Beta: No redirect — state update triggers in-page toast + tab switch back to `explore`

### `_save_slots` DB column
- `_autosave()` no longer writes `_save_slots` into the `game_state` JSONB column
- `_apply_game_state()` no longer reads `_save_slots` from DB
- Result: clean JSONB blob with no slot metadata noise

### `character_autosave()` stat columns
- Now also writes `hp`, `gold`, `experience` to dedicated integer columns for fast leaderboard/display queries

### `ol2_characters` new columns (DB schema)
- Added: `hp INTEGER`, `gold INTEGER`, `experience INTEGER` — fast-query mirrors
- Added: `is_online BOOLEAN DEFAULT FALSE` — real-time presence
- Added: `last_login TIMESTAMPTZ`, `last_logout TIMESTAMPTZ`
- Added: `playtime_seconds BIGINT DEFAULT 0`

### `ol2_sessions` table (new)
- One row per session token: `user_id`, `session_token`, `ip_address`, `user_agent`, `started_at`, `last_seen_at`, `ended_at`, `is_active`
- `session_start()` called on login — closes stale sessions, opens new row, marks `is_online=TRUE`, sets `last_login`
- `session_end()` called on logout — closes row, marks `is_online=FALSE`, sets `last_logout`, increments `playtime_seconds`
- `session_heartbeat()` called on autosave — updates `last_seen_at`
- Enables: server-side forced logout, duplicate session detection, playtime calculation, admin audit trail

### `ol2_saves` table
- Marked **LEGACY / deprecated** in schema comments
- `cloud_save()` / `cloud_load()` Python functions still exist for data migration
- No UI in either Classic or Vue Beta writes to it anymore

---

## What Vue Beta Has That Flask Classic Lacks

- Adaptive polling (faster in battle)
- Auto-tab switch to battle on combat start; auto-return to explore on end
- Auto-hide of Shop / Mine tabs when not in relevant area
- Boss cooldown display inline on Explore tab
- Nearby players on Explore tab
- Seasonal Events tab with eligibility checking
- All actions without full page reload (no flash/scroll-jump)
- `v-html` safe rendering of diary/log entries with inline colours
- Battle: spell buttons per-spell instead of dropdown

## What Flask Classic Has That Vue Beta Lacks

- Full land, housing, farming, and pet systems
- Friend request send / respond / remove
- Direct messaging (DMs)
- User blocking
- Group creation / join / leave / kick / gold-collection
- Settings panel (theme, music, background, UI scale)
- Character customization
- Wiki / item catalog
- Leaderboard page
- Standalone chat page
- HP low warning animation
- Guest file save/download (`.olsave`)
- Battle: dropdown spell selector (easier on mobile with many spells)
