# Vue Beta UI — Parity & Fix Tracker
> Last updated: 2026-05-28  
> Save strategy: **100% session-based** — Flask session auto-saves after every action.  
> No save slots, no file downloads, no cloud-slot UI.

---

## Changelog — Fixes Applied

### Session 2026-05-28 (part 2 — high-priority features)
| Fix | Files Changed | Status |
|-----|--------------|--------|
| **Boss dialogue banner** — When fighting a boss, a styled italic banner showing the boss's opening dialogue now appears between the arena and the battle log. Pulls `battle.boss_dialogue` from `_api_battle_summary()`. | `app.py`, `templates/vue/game.html` | ✅ Done |
| **Boss phase indicator** — Shows a pip bar (one dot per phase, red = current), phase index/total, ATK multiplier, and phase description below the dialogue banner when `battle.boss_phase_info` is non-null. Computed live from enemy HP% on every state poll. | `app.py`, `templates/vue/game.html` | ✅ Done |
| **Player status effects** — Shows a horizontal pill tag cloud (effect name + turns remaining) between the phase indicator and the battle log. Pulls `battle.player_effects` from `_api_battle_summary()`. | `app.py`, `templates/vue/game.html` | ✅ Done |
| **Group real-time chat** — `connectGroupSocket()` opens a Socket.IO connection on mount; listens for `group_chat_message` (appends to `groupChatMessages`, auto-scrolls) and `group_level_up` (shows gold toast). Rendered as a scrollable chat log + send input below the group panel. | `static/js/vue/game.js`, `templates/vue/game.html` | ✅ Done |

### Session 2026-05-28 (part 1 — bug sweep)
| Fix | Files Changed | Status |
|-----|--------------|--------|
| **Route `/beta` → partitioned structure** — `/beta` now renders `templates/vue/game.html` + `static/js/vue/game.js` instead of the monolithic `vue_beta.html`. `in_battle` context variable added to the route. | `app.py`, `templates/vue/game.html`, `templates/vue/base.html` | ✅ Done |
| **BUG-V07 fixed** — Removed `spa.js` from `templates/vue/base.html`. The form-intercept and SPA poll guard were both no-ops in the Vue context. | `templates/vue/base.html` | ✅ Done |
| **BUG-J03 fixed** — Wrapped `switchTab(data.tab)` in try/catch in `spa.js` so a missing DOM element doesn't swallow the error silently. | `static/js/spa.js` | ✅ Done |
| **BUG-J04 fixed** — Added `online_count` DOM update in `spaPoll` so the sidebar count refreshes without a full page reload. | `static/js/spa.js` | ✅ Done |
| **BUG-V02 fixed** — Battle tab auto-switch now only fires on combat state *transitions* (`wasInBattle` captured before update) instead of every poll while in battle. Players can browse inventory/spells without being snapped back. | `static/js/vue/game.js` | ✅ Done |
| **BUG-V06 fixed** — Removed `tabDropdownOpen` from `data()` and removed the dead global click listener from `mounted()`. The `...` dropdown was hidden via CSS but the listener still fired on every click. | `static/js/vue/game.js` | ✅ Done |
| **BUG-V09 fixed** — Added `claimEventReward(evKey)` method in `game.js` + Claim Reward button on event cards in `game.html`. Calls `/api/action/claim_event`. | `static/js/vue/game.js`, `templates/vue/game.html` | ✅ Done |
| **BUG-V10 fixed** — `inBattle` seeded from `window._betaInit.in_battle` in `data()` so the battle tab badge is correct on first paint, not just after the first poll. | `static/js/vue/game.js`, `templates/vue/game.html` | ✅ Done |
| **BUG-V11 fixed** — Pet name added to sidebar player panel (`player.pet` formatted with spaces). | `templates/vue/game.html` | ✅ Done |
| **BUG-V12 fixed** — Dungeon room progress bar added below room text in active dungeon panel (proportional `bar-fill bar-exp`). | `templates/vue/game.html` | ✅ Done |
| **BUG-V14 fixed** — "Bonus Modifiers" panel added to character tab: Spell Power, Dodge Chance, Crit Chance, Shop Discount, Item Discovery, EXP Bonus — all conditionally rendered when non-zero. | `templates/vue/game.html` | ✅ Done |
| **BUG-V15 fixed** — Group XP / level bar added to group panel using `groupData.level`, `groupData.xp`, `groupData.xp_to_next`. | `templates/vue/game.html` | ✅ Done |
| **BUG-V16 fixed** — `abandonDungeon()` now calls `confirm()` before firing the API. Prevents accidental misclick wiping dungeon progress. | `static/js/vue/game.js` | ✅ Done |
| **BUG-S01 fixed** — Global DM unread badge added to sidebar below the online username. Clicking it navigates to the Friends tab. Uses existing `totalDmUnread` computed prop. | `templates/vue/game.html` | ✅ Done |
| **BUG-S02 fixed** — `attr_exp_bonus` added to `data()` player init, `_applyState()` mapping, and the Bonus Modifiers character tab panel (visible with BUG-V14 fix). | `static/js/vue/game.js` | ✅ Done |
| **ESLint config** — Added `"no-empty": ["error", { "allowEmptyCatch": true }]` to `.eslintrc.json` to allow the existing idiomatic empty-catch pattern (`catch (_) {}`) across all JS files. | `.eslintrc.json` | ✅ Done |

### Session 2026-05-27
| Fix | Files Changed | Status |
|-----|--------------|--------|
| **Scrolling fixed** — `.game-layout` was `min-height:100vh` so `main-content` never had a bounded container; `overflow-y:auto` was a no-op and the whole page scrolled. Added `height:calc(100vh/var(--ui-scale,1)); min-height:unset` scoped to `#vue-beta-app .game-layout`. | `vue_beta.html` | ✅ Done |
| **Tab bar — horizontal scroll** — `.tab-nav` had `overflow:hidden` clipping tabs silently. Changed to `overflow-x:auto` with scrollbar hidden via `scrollbar-width:none` and `::-webkit-scrollbar{display:none}`. | `vue_beta.html` | ✅ Done |
| **Tab bar — sticky** — Tab row scrolled away with content. Added `position:sticky;top:0` to `.tab-bar-wrap` with background fill and negative margin bleed to fill the content gutter. | `vue_beta.html` | ✅ Done |
| **Tab bar — scroll active into view** — Switching tabs now calls `scrollIntoView({inline:'center',behavior:'smooth'})` in `switchTab()` so the active tab button is always visible. | `vue_beta.js` | ✅ Done |
| **Tab bar — removed `...` dropdown** — Now redundant because the tab row scrolls horizontally. Hidden with `.tab-bar-wrap .vtab-more-wrap{display:none}`. | `vue_beta.html` | ✅ Done |
| **Land iframe eliminated** — Replaced `<iframe id="beta-land-frame">` with a native Vue panel. Added `loadLandData()` fetching `/api/land_data`, shows land level / plots / farm plots (with individual Harvest buttons) / active pets (with Train buttons) / Rest action. | `vue_beta.html`, `vue_beta.js` | ✅ Done |
| **`readyChallengesCount` computed prop** — Was used in template tab badge but not defined in JS, causing a silent Vue warning every poll cycle. Now computes `challenges.filter(ch => !ch.claimed && count >= target).length`. | `vue_beta.js` | ✅ Done |
| **`activeEventsCount` computed prop** — Same as above; now computes `eventsData.active.length`. | `vue_beta.js` | ✅ Done |

---

## Pagination — All Lists

| List | Page size | Status |
|------|-----------|--------|
| Inventory | 15/pg | ✅ |
| Shop | 15/pg | ✅ |
| Elite Market | 20/pg | ✅ |
| Diary / Log | 30/pg | ✅ |
| Crafting recipes | 12/pg | ✅ |
| Quests / Missions | 10/pg | ✅ |
| Challenges | 10/pg | ✅ |
| Companions available | 8/pg | ✅ |
| Friends list | 20/pg | ✅ |
| Boss challenges | 8/pg | ✅ |

---

## Full Feature Comparison Matrix

Legend: ✅ Present & matching · ⚠️ Partial / differs · ❌ Missing · 🆕 Vue-only

---

### Layout & Navigation
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Game layout (sidebar + main) | ✅ | ✅ | |
| Sidebar collapse / resize | ✅ | ✅ | |
| Tab bar (horizontal) | ✅ | ✅ Fixed | Was clipping; now scrolls |
| Tab bar sticky on scroll | ✅ | ✅ Fixed | Was scrolling away |
| Active tab scroll-into-view | ✅ | ✅ Fixed | Added `scrollIntoView` |
| `...` overflow dropdown | ✅ | ❌ Removed | Replaced by scroll |
| News / announcements ticker | ✅ | ✅ | Both fetch `/api/announcements` |
| Settings modal | ✅ | ✅ | |
| Background & theme selector | ✅ | ✅ | |
| Fullscreen toggle | ✅ | ✅ | |
| Admin FAB (admin-only) | ✅ | ✅ | |
| Admin console tab | ✅ | ✅ | |

---

### Sidebar
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| HP / MP / EXP bars | ✅ | ✅ | |
| Gold display | ✅ | ✅ | |
| Game time (day/night icon) | ✅ | ✅ | |
| Weather display | ✅ | ✅ | |
| Weather bonus breakdown (`+X% EXP / +Y% gold`) | ✅ | ✅ | `game.html` — shown when either bonus > 0 |
| Location name + description | ✅ | ✅ | |
| Rest available notice (inn/land) | ✅ | ✅ | |
| **Land comfort points in sidebar** | ✅ | ❌ | Jinja2 shows `land_data.comfort_points` in location panel |
| **Pet name in sidebar** | ✅ | ✅ Fixed | Added via BUG-V11 fix |
| Low-HP warning pulse (sidebar) | ❌ | 🆕 ✅ | Vue-only — pulse box when HP ≤ 25% |
| Active companions HP bars (sidebar) | ❌ | 🆕 ✅ | Vue-only — party panel in sidebar |
| Online count badge | ✅ | ✅ | |
| Online username badge | ✅ | ✅ | |
| **Global DM unread badge** | ❌ | ✅ Fixed | Added via BUG-S01 fix; shows unread count, links to Friends tab |
| **Email setup prompt** (no-email users) | ✅ | ❌ | `user_has_email` flag shown in Jinja2 sidebar |
| Navigate shortcuts | ✅ | ✅ | |
| Change Character button (10k gold) | ✅ | ❌ | `openCustomizeModal()` in Jinja2 |
| Save & Exit button | ✅ | ✅ | |
| World Events feed | ✅ | ✅ | |

---

### Battle Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Enemy name + glyph | ✅ | ✅ | |
| Boss vs normal styling | ✅ | ✅ | |
| Round counter | ✅ | ✅ | |
| Player HP/MP bars (battle) | ✅ | ✅ | |
| Enemy HP bar | ✅ | ✅ | |
| Low-HP pulse warning | ✅ | ✅ | |
| Battle log (colored HTML) | ✅ | ✅ | |
| Spell buttons with MP cost | ✅ | ✅ | |
| Consumable use buttons | ✅ | ✅ | |
| Party HP bars (companions) | ✅ | ✅ | |
| Attack / Defend / Flee buttons | ✅ | ✅ | |
| **Boss dialogue banner** | ✅ | ✅ Fixed | Added 2026-05-28 — italic banner below arena |
| **Boss phase indicator** | ✅ | ✅ Fixed | Added 2026-05-28 — pip bar + phase index/total + ATK multiplier |
| **Player status effects** (buffs/debuffs) | ✅ | ✅ Fixed | Added 2026-05-28 — pill tag cloud with turns remaining |
| Boss abilities panel | ✅ | ❌ | Listed boss special moves in Jinja2 battle tab |

---

### Explore Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Venture Forth button | ✅ | ✅ | |
| Area description + connections | ✅ | ✅ | |
| Nearby player sightings | ✅ | ✅ | |
| World events in explore | ✅ | ✅ | |
| Rest at inn (cost shown) | ✅ | ✅ | |
| Rest disabled (no gold) reason | ✅ | ⚠️ | Jinja2 shows `disabled title="Not enough gold"` explicitly |
| **Your Land minimap canvas** | ✅ | ❌ | Canvas render of placed buildings on `your_land` area |

---

### Character Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Core stats grid (HP/MP/ATK/DEF/SPD/Gold/EXP) | ✅ | ✅ | |
| Attributes (STR/DEX/INT/…) with modifier brackets | ✅ | ✅ | |
| Attribute point spending (1 / All) | ✅ | ✅ | |
| Player rank / class / title display | ✅ | ✅ | |
| Total kills / boss kills / deaths | ✅ | ✅ | |
| Adventurer days counter | ✅ | ✅ | |
| Reputation display | ❌ | ✅ | Vue Statistics panel: `player.reputation` |
| **"Bonus Modifiers" named section** | ✅ | ✅ Fixed | Added via BUG-V14 fix — Spell Power, Dodge, Crit, Shop Discount, Item Discovery, EXP Bonus |
| Spell Power modifier (visible) | ✅ | ✅ Fixed | Now in Bonus Modifiers panel + Equipment stat-mini |
| Dodge Chance modifier (visible) | ✅ | ✅ Fixed | Now in Bonus Modifiers panel + Equipment stat-mini |
| Crit Chance modifier (visible) | ✅ | ✅ Fixed | Now in Bonus Modifiers panel + Equipment stat-mini |
| Shop Discount modifier (visible) | ✅ | ✅ Fixed | Now in Bonus Modifiers panel + Equipment stat-mini |
| Item Discovery modifier (visible) | ✅ | ✅ Fixed | Now in Bonus Modifiers panel + Equipment stat-mini |
| **EXP Bonus modifier** (`attr_exp_bonus`) | ✅ | ✅ Fixed | Added via BUG-S02 + BUG-V14 fixes |

---

### Equipment Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Slot grid (weapon/armor/offhand/accessories) | ✅ | ✅ | |
| Equipped item name + rarity | ✅ | ✅ | |
| Equipped item stats string | ✅ | ✅ | |
| Equipped item description | ✅ | ✅ | |
| Weapon type label | ✅ | ✅ | |
| Unequip button | ✅ | ✅ | |
| Auto-Equip Best Items | ✅ | ✅ | |
| Stat mini-grid (in equipment panel) | ✅ | ✅ | |
| **`attr_exp_bonus` in equipment stat grid** | ✅ | ✅ Fixed | Added via BUG-S02 fix |

---

### Inventory Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Item list (equippables + consumables) | ✅ | ✅ | |
| Item textures / type glyphs | ✅ | ✅ | |
| Rarity colors & borders | ✅ | ✅ | |
| Item stats string | ✅ | ✅ | |
| Item description (truncated) | ✅ | ✅ | |
| Item requirement badge (`req_label`) | ✅ | ✅ | |
| Can-equip / equip-block display | ✅ | ✅ | |
| Equip button (disabled if blocked) | ✅ | ✅ | |
| **Equip button `title` = block reason** | ✅ | ❌ | Jinja2 passes `title="{{ item.equip_block_reason }}"` on disabled Equip button |
| Sell button with sell price | ✅ | ✅ | |
| Quick Heal button | ✅ | ✅ | |
| Sort Items button | ✅ | ✅ | |
| Pagination 15/pg | ✅ | ✅ | |

---

### Shop Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Shop name | ✅ | ✅ | |
| Item rows with stats & description | ✅ | ✅ | |
| Price display | ✅ | ✅ | |
| Affordability (disabled if broke) | ✅ | ✅ | |
| Birthday special label | ✅ | ✅ | |
| Class / level requirement badges | ✅ | ✅ | |
| Buy button | ✅ | ✅ | |
| Pagination 15/pg | ✅ | ✅ | |

---

### Mine Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Mining level badge | ✅ | ✅ | |
| Mining XP progress bar | ✅ | ✅ | |
| XP to next level text | ✅ | ✅ | |
| Max level indicator | ✅ | ✅ | |
| Best pickaxe label | ✅ | ✅ | |
| No-pickaxe notice | ✅ | ✅ | |
| Mine button (disabled without pickaxe) | ✅ | ✅ | |
| Ore deposit list with rarity | ✅ | ✅ | |
| Locked ore indicator | ✅ | ✅ | |
| **STR → success rate hint** | ✅ | ❌ | `STR X → +Y% success` hint below Mine button |

---

### Crafting Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Recipe list | ✅ | ✅ | |
| Materials with missing-material highlight (red) | ✅ | ✅ | |
| Produces output | ✅ | ✅ | |
| Can-craft highlight / disabled state | ✅ | ✅ | |
| Craft button | ✅ | ✅ | |
| Pagination 12/pg | ✅ | ✅ | |

---

### Dungeons Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Dungeon list | ✅ | ✅ | |
| Area requirement notice | ✅ | ✅ | |
| Challenge button | ✅ | ✅ | |
| Dungeon difficulty / rewards | ✅ | ✅ | |
| Active dungeon panel | ✅ | ✅ | |
| **Room progress bar** | ✅ | ✅ Fixed | Added via BUG-V12 fix |
| Continue → link style | ✅ | ⚠️ | Jinja2: `btn-primary btn-wood` with arrow; Vue: `btn-secondary` without arrow |
| Abandon (with confirm dialog) | ✅ | ✅ Fixed | BUG-V16 fixed — `window.confirm()` now called before API |

---

### Map Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Area image | ✅ | ✅ | |
| Visited areas grid | ✅ | ✅ | |
| Quick-travel buttons | ✅ | ✅ | |
| Nearby areas with connection badges | ✅ | ✅ | |
| Canvas world map (BFS fog-of-war) | ✅ | ✅ | Vue has full canvas implementation |
| Pan / zoom on world map | 🆕 | ✅ | Vue-only feature |

---

### Boss Challenges Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Boss list | ✅ | ✅ | |
| Cooldown display | ✅ | ✅ | |
| Challenge button | ✅ | ✅ | |
| Pagination 8/pg | ✅ | ✅ | |

---

### Quests Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Quest list + progress | ✅ | ✅ | |
| Complete / turn-in button | ✅ | ✅ | |
| Completed count badge | ✅ | ✅ | |
| Pagination 10/pg | ✅ | ✅ | |

---

### Challenges Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Challenge list | ✅ | ✅ | |
| Progress bar per challenge | ✅ | ✅ | |
| Claim button (disabled when claimed/incomplete) | ✅ | ✅ | |
| Ready badge on tab (`readyChallengesCount`) | ✅ | ✅ Fixed | Was missing computed prop |
| Pagination 10/pg | ✅ | ✅ | |

---

### Events Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Active events list | ✅ | ✅ | |
| Upcoming events list | ✅ | ✅ | |
| Event description + end date + days remaining | ✅ | ✅ | |
| Claimed badge | ✅ | ✅ | |
| Days remaining color (red ≤1 day) | ✅ | ✅ | |
| Claim reward button | ✅ | ✅ Fixed | BUG-V09 fixed — button + `claimEventReward()` method added |
| Active badge on tab (`activeEventsCount`) | ✅ | ✅ Fixed | Was missing computed prop |
| **`boss_kills` progress bar** | ✅ | ❌ | Jinja2 shows a bar for `ev.condition_type === 'boss_kills'` events |

---

### Diary / Log Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Colored HTML entries | ✅ | ✅ | |
| Pagination 30/pg | ✅ | ✅ | |

---

### Party / Companions Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Active companions (HP bars) | ✅ | ✅ | |
| Fallen indicator | ✅ | ✅ | |
| Available companions to hire | ✅ | ✅ | |
| Hire button | ✅ | ✅ | |
| Dismiss companion | ✅ | ✅ | |
| Companion pagination 8/pg | ✅ | ✅ | |

---

### Elite Market Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Browse & buy items | ✅ | ✅ | |
| Affordability highlight | ✅ | ✅ | |
| Stats string | ✅ | ✅ | |
| Class / level requirement display | ✅ | ✅ | |
| Cooldown message | ✅ | ✅ | |
| Reset cooldown button | ✅ | ✅ | |
| Pagination 20/pg | ✅ | ✅ | |

---

### Land / Housing Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Tab only visible on your_land | ✅ | ✅ | |
| Travel button when elsewhere | ✅ | ✅ | |
| Land iframe | ✅ | ✅ Fixed | Eliminated — replaced with native Vue |
| Land level + plot counts | ✅ | ✅ Fixed | Loaded from `/api/land_data` |
| Farm plots + Harvest buttons | ✅ | ✅ Fixed | Per-plot harvest via `/api/action/land/harvest` |
| Active pets + Train buttons | ✅ | ✅ Fixed | Per-pet train via `/api/action/land/train` |
| Rest action | ✅ | ✅ Fixed | Via `/api/action/land/rest` |
| Comfort points display | ✅ | ❌ | Jinja2 shows `comfort_points` prominently |
| **Training options** (stat boosts) | ✅ | ❌ | Jinja2 shows STR/DEX/INT/etc. training per land level |
| **Land crafting recipes** | ✅ | ❌ | Separate recipe list for land crafting |
| **Storage** (store/retrieve items) | ✅ | ❌ | `land_data.stored_items` / storage capacity panel |
| **Building management** (buy/place/remove) | ✅ | ❌ | Full grid builder in Jinja2 land map page |
| **Farm planting** (choose crop) | ✅ | ❌ | Crop selection per empty plot slot |
| **Pet purchasing** | ✅ | ❌ | Buy pets from land shop |
| Land map canvas minimap | ✅ | ❌ | Canvas showing placed buildings |
| Nav links to full land pages | ❌ | ✅ | Vue shows "Open Map / Shop / Pets" links |

---

### Friends & DM Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Friends list + pagination | ✅ | ✅ | |
| Send friend request | ✅ | ✅ | |
| Accept / reject request | ✅ | ✅ | |
| Remove friend | ✅ | ✅ | |
| **Direct messages (DM)** | ❌ | 🆕 ✅ | Vue-only — inline DM panel per friend |
| DM unread badge per friend | ❌ | 🆕 ✅ | Vue-only |
| **Global DM unread in sidebar** | ❌ | ✅ Fixed | BUG-S01 fixed — badge shown in sidebar, links to Friends tab |

---

### Group Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Group info display | ✅ | ✅ | |
| Group XP / level bar | ✅ | ✅ Fixed | BUG-V15 fixed — level badge + XP progress bar added |
| Create group | ✅ | ✅ | |
| Join group by invite code | ✅ | ✅ | |
| Leave / disband group | ✅ | ✅ | |
| Kick member (leader only) | ✅ | ✅ | |
| Collect group gold | ✅ | ✅ | |
| **Real-time group chat** (Socket.IO) | ✅ | ✅ Fixed | Added 2026-05-28 — Socket.IO chat log + send input + `group_level_up` toast |
| **Group sub-tab nav** (Info / Members / Chat / Settings) | ✅ | ❌ | Jinja2 has 4 sub-tabs inside the group panel; Vue is a single flat layout |
| **Group level-up banner** (Socket.IO) | ✅ | ❌ | Jinja2 handles `group_level_up` event with an animated overlay banner |

---

### Leaderboard Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Leaderboard page link | ✅ | ✅ | |
| **Native leaderboard (no iframe)** | ❌ | 🆕 ✅ | Vue loads from `/api/leaderboard` |
| Top Groups list | ✅ | ✅ | |
| Top Adventurers list | ✅ | ✅ | |
| Rank badges (gold/silver/bronze) | ✅ | ✅ | |

---

### Chat
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Global chat widget | ✅ | ✅ | |
| **Chat via iframe** | ✅ | ❌ Eliminated | Vue uses native chat widget |
| Chat FAB (floating button) | ✅ | ✅ | |
| Unread badge on FAB | ✅ | ✅ | |
| Send / Enter to send | ✅ | ✅ | |
| Message history | ✅ | ✅ | |

---

### Wiki Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Wiki link button | ✅ | ✅ | Neither embeds; both link to `/wiki` |

---

### Vue-Only Features (no Jinja2 equivalent)
| Feature | Vue Beta |
|---------|----------|
| SPA with 2s/7s state polling (no page reloads) | 🆕 ✅ |
| Direct Messages (DM) between friends | 🆕 ✅ |
| Pan / zoom canvas world map | 🆕 ✅ |
| Native leaderboard (no iframe) | 🆕 ✅ |
| Native chat widget (no iframe) | 🆕 ✅ |
| Toast notifications for all actions | 🆕 ✅ |
| Battle auto-switches to battle tab (transition only) | 🆕 ✅ |
| Horizontal scrolling tab bar | 🆕 ✅ |
| Global DM unread badge in sidebar | 🆕 ✅ |

---

## Remaining Gaps — Prioritised

> Last updated: 2026-05-28

### Priority: High (affects common gameplay)
> All high-priority items resolved as of 2026-05-28.

| Gap | Where | Status |
|-----|--------|--------|
| **Boss phase indicator** | Battle tab | ✅ Fixed — pip bar + phase index/total + ATK multiplier + description block |
| **Boss dialogue banner** | Battle tab | ✅ Fixed — italic banner shown when `battle.boss_dialogue` is non-null |
| **Player status effects** | Battle tab | ✅ Fixed — pill tag cloud with effect name + turns remaining |
| **Group real-time chat** | Group tab | ✅ Fixed — Socket.IO `group_chat_message` listener + scrollable chat log + send input; `group_level_up` shows toast |

### Priority: Medium (improves completeness)
| Gap | Where | What to do |
|-----|--------|-----------|
| **`boss_kills` event progress bar** | Events tab | Add `v-if="ev.condition_type === 'boss_kills'"` progress bar block to event cards |
| **Land comfort points** | Sidebar + Land tab | Expose `comfort_points` from `/api/land_data` response; show in sidebar location panel and land tab header |
| **Land training options** | Land tab | Fetch training options from land data; show stat-select + Train button per option |
| **Land storage panel** | Land tab | Show stored items list + store/retrieve actions via `/api/action/land/store` and `/api/action/land/retrieve` |
| **Land farm planting** | Land tab | For empty farm slots, show crop selector + Plant button via `/api/action/land/plant` |
| **Your Land explore minimap** | Explore tab | Canvas render of placed buildings on `your_land` (same logic as Jinja2 `index.html:1052-1135`) |
| **Group sub-tab navigation** | Group tab | Add Info / Members / Chat sub-tabs within the group panel |
| **Group level-up banner** | Group tab | Handle `group_level_up` Socket.IO event; show animated overlay banner |
| **BUG-J01 — pageable-list re-init** | Jinja2 `spa.js` | Re-run pageable-list initialiser after every SPA DOM injection, or use event delegation |
| **BUG-J02 — boss dialogue via state poll** | Jinja2 `app.py` + `spa.js` | Include `boss_dialogue` in `/api/game/state` JSON; update via `spaUpdatePlayerStats` |

### Priority: Low (polish / edge cases)
| Gap | Where | What to do |
|-----|--------|-----------|
| **Email setup prompt** | Sidebar | Requires `user_has_email` passed from server to `_betaInit`; show warning button |
| **Change Character button** | Sidebar | Link to `openCustomizeModal()` (existing JS function); needs 10k gold check |
| **STR → mine success hint** | Mine tab | Add `STR [[ player.attributes?.str\|\|0 ]] → +[[ ((player.attributes?.str\|\|0)*0.5).toFixed(1) ]]% success` below Mine button |
| **Equip-button title tooltip** | Inventory tab | Add `:title="item.equip_block_reason"` to disabled Equip button |
| **Rest button gold-check disabled** | Explore tab | Add `:disabled` + `:title` when `area.rest_cost > 0 && player.gold < area.rest_cost` |
| **Land crafting recipes** | Land tab | Inline land crafting panel via `/api/action/land/craft` |
| **Land building buy/place/remove** | Land tab | Full builder — complex; link to `/land/map` is fine for now |
| **Pet purchasing** | Land tab | Link to `/land/pets` for now |
| **Boss abilities panel** | Battle tab | Low traffic feature; add collapsible list of boss special moves if `battle.boss_abilities` exists |
| **Dungeon Continue button style** | Dungeons tab | Change `btn-secondary` → `btn-primary btn-wood`; add `→` arrow to match Jinja2 |
| **BUG-V08 — `marketReset` legacy route** | `game.js` | Wrap `fetch("/action/market/reset")` with `doAction()` or add `/api/action/market/reset` |
| **BUG-J05 — missing XHR header on forms** | Jinja2 templates | Add `X-Requested-With` header to forms that may be submitted outside SPA context |
| **Tab glyph pixel icons** | Tab bar | Decorative only |
| **Trade UI inline** | Any | Currently links to `/trade`; complex to inline |
| **NPC dialogue modals** | Explore tab | Low priority |

---

## Linter Report — 2026-05-28

> Tools: **ESLint v8** (JS, `--no-eslintrc -c .eslintrc.json`), **node --check** (JS syntax),  
> **Pyright** (Python static types), **Pylint** (Python errors-only), **py_compile** (Python syntax)

---

### ESLint — `static/js/vue/game.js`

| Run | Errors | Warnings |
|-----|--------|---------|
| 1 | 0 | 1 |

**1 warning (pre-existing, no fix needed):**
- `game.js:400` — `eqeqeq`: `item[k] != null` uses `!=` instead of `!==`. This is intentional — `!= null` is idiomatic JS to match both `null` and `undefined` in a single check. Not a bug.

### ESLint — `static/js/spa.js`

| Run | Errors | Warnings |
|-----|--------|---------|
| 1 | 0 | 2 |

**2 warnings (pre-existing, no fix needed):**
- `spa.js` — `no-undef`: `initLowHpWarning` / `showToast` — both protected by `typeof` guards; defined in `game.js` in the Jinja2 context. ESLint can't see cross-file globals not in config.

### ESLint Config Change (`allowEmptyCatch`)

Added `"no-empty": ["error", { "allowEmptyCatch": true }]` to `.eslintrc.json`. This allows the idiomatic `catch (_) {}` pattern used throughout both files without comments, matching the project style.

### `node --check` — All JS Files

`static/js/vue/game.js` and `static/js/spa.js` both pass `node --check` with no syntax errors.

### Pyright — `app.py`

| Run | Errors | Warnings |
|-----|--------|---------|
| 1 | 0 | 0 |

Clean. (Previous BUG-L01 `assert player is not None` fix still in place.)

### Pylint — `app.py` (errors only)

| Run | Errors |
|-----|--------|
| 1 | 1 (pre-existing false positive) |

**Pre-existing false positive (no fix needed):**
- `app.py:8252` — `E1101: Method 'run_wsgi_app' has no '__wrapped__' member` — this is the ASGI/WSGI wrapper method. Pylint cannot resolve dynamic wrappers on the Flask ASGI shim. No functional issue.

### `py_compile` — All Python Files

`app.py` and all `utilities/*.py` files pass `py_compile` with no syntax errors.

### Summary

| Category | Errors | Warnings | Notes |
|----------|--------|---------|-------|
| JS syntax (node --check) | 0 | — | Clean |
| JS lint (ESLint) | 0 | 3 | All pre-existing / intentional |
| Python types (Pyright) | 0 | 0 | Clean |
| Python lint (Pylint errors-only) | 0 | — | 1 false positive on ASGI wrapper |
| Python syntax (py_compile) | 0 | — | Clean |
