# Vue Beta UI — Parity & Fix Tracker
> Last updated: 2026-05-27  
> Save strategy: **100% session-based** — Flask session auto-saves after every action.  
> No save slots, no file downloads, no cloud-slot UI.

---

## Changelog — Fixes Applied

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
| **Weather bonus breakdown** (`+X% EXP / +Y% gold`) | ✅ | ❌ | `weatherBonusExp/Gold` in data; not shown in sidebar |
| Location name + description | ✅ | ✅ | |
| Rest available notice (inn/land) | ✅ | ✅ | |
| **Land comfort points in sidebar** | ✅ | ❌ | Jinja2 shows `land_data.comfort_points` in location panel |
| Party HP bars (companions) | ✅ | ✅ | |
| Online count badge | ✅ | ✅ | |
| Online username badge | ✅ | ✅ | |
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
| **Boss dialogue banner** | ✅ | ❌ | `battle.boss_dialogue` — flavor text from boss on phase change |
| **Boss phase indicator** | ✅ | ❌ | `battle.boss_phase` — pip bar, phase index/total, ATK×multiplier |
| **Player status effects** (buffs/debuffs) | ✅ | ❌ | `battle.player_effects` dict — shows active effect name + turns remaining |
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
| Spell Power bonus modifier | ✅ | ✅ | |
| Dodge Chance bonus modifier | ✅ | ✅ | |
| Crit Chance bonus modifier | ✅ | ✅ | |
| Shop Discount bonus modifier | ✅ | ✅ | |
| Item Discovery bonus modifier | ✅ | ✅ | |
| **EXP Bonus modifier** (`attr_exp_bonus`) | ✅ | ❌ | In Jinja2 bonus modifiers section; `player` data has it but Vue template never renders it |
| Player rank / title display | ✅ | ⚠️ | Sidebar shows rank; character tab stat grid omits title |
| Total kills / boss kills / deaths | ✅ | ⚠️ | Vue sidebar shows some; character tab omits summary counts |
| Adventurer days counter | ✅ | ⚠️ | In Jinja2 character sheet; Vue omits it |

---

### Equipment Tab (Vue splits Jinja2's combined "Equipment" tab)
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
| **`attr_exp_bonus` in equipment stat grid** | ✅ | ❌ | Same gap as character tab |

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
| Room progress bar | ✅ | ✅ | |
| Continue → link | ✅ | ✅ | |
| Abandon (with confirm) | ✅ | ✅ | |

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
| Claim reward button | ✅ | ✅ | |
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
| **Global DM unread in sidebar** | ❌ | ❌ | Neither version shows a sidebar badge for total unread DMs |

---

### Group Tab
| Feature | Jinja2 | Vue Beta | Notes |
|---------|--------|----------|-------|
| Group info display | ✅ | ✅ | |
| Create group | ✅ | ✅ | |
| Join group by invite code | ✅ | ✅ | |
| Leave group | ✅ | ✅ | |
| Kick member (leader only) | ✅ | ✅ | |
| Collect group gold | ✅ | ✅ | |
| Group XP / level bar | ✅ | ✅ | |

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
| Battle auto-switches to battle tab | 🆕 ✅ |
| Horizontal scrolling tab bar | 🆕 ✅ |

---

## Remaining Gaps — Prioritised

### Priority: High (affects common gameplay)
| Gap | Where | What to do |
|-----|--------|-----------|
| **Boss phase indicator** | Battle tab | Add `battle.boss_phase` block: pip bar, index/total, ATK multiplier, phase description. Check `/api/game/state/extended` for `boss_phase` key. |
| **Boss dialogue banner** | Battle tab | Add `battle.boss_dialogue` banner below round badge (only when `battle.is_boss`). |
| **Player status effects** | Battle tab | Add `battle.player_effects` tag cloud (effect name + turns left). |
| **Weather bonus breakdown** | Sidebar | `weatherBonusExp` and `weatherBonusGold` already in `data()`; add a row in the sidebar status panel when either > 0. |
| **`attr_exp_bonus` modifier** | Character + Equipment tabs | Add to bonus modifiers stat-mini-grid; also add `attr_exp_bonus: 0` to player init in `data()`. |

### Priority: Medium (improves completeness)
| Gap | Where | What to do |
|-----|--------|-----------|
| **`boss_kills` event progress bar** | Events tab | Add `v-if="ev.condition_type === 'boss_kills'"` progress bar block to event cards. |
| **Land comfort points** | Sidebar + Land tab | Expose `comfort_points` from `/api/land_data` response; show in sidebar location panel and land tab header. |
| **Land training options** | Land tab | Fetch training options from land data; show stat-select + Train button per option. |
| **Land storage panel** | Land tab | Show stored items list + store/retrieve actions via `/api/action/land/store` and `/api/action/land/retrieve`. |
| **Land farm planting** | Land tab | For empty farm slots, show crop selector + Plant button via `/api/action/land/plant`. |
| **Your Land explore minimap** | Explore tab | Canvas render of placed buildings on `your_land` (same logic as Jinja2 lines 1052-1135 of index.html). |
| **STR → mine success hint** | Mine tab | Add `STR [[ player.attributes?.str || 0 ]] → +[[ ((player.attributes?.str||0)*0.5).toFixed(1) ]]% success` below Mine button. |
| **Equip-button title tooltip** | Inventory tab | Add `:title="item.equip_block_reason"` to disabled Equip button. |

### Priority: Low (polish / edge cases)
| Gap | Where | What to do |
|-----|--------|-----------|
| **Email setup prompt** | Sidebar | Requires `user_has_email` passed from server to `_betaInit`; show warning button. |
| **Change Character button** | Sidebar | Link to `openCustomizeModal()` (existing JS function); needs 10k gold check. |
| **Player title in character tab** | Character tab | `player.title` is in data; add a row to character stat grid. |
| **Adventurer days / total kills / deaths** | Character tab | In data; add compact summary row to character sheet. |
| **Land crafting recipes** | Land tab | Inline land crafting panel via `/api/action/land/craft`. |
| **Land building buy/place/remove** | Land tab | Full builder — complex; link to `/land/map` is fine for now. |
| **Pet purchasing** | Land tab | Link to `/land/pets` for now. |
| **Global DM unread badge in sidebar** | Sidebar | `totalDmUnread` computed already exists; show a small badge in sidebar nav. |
| **Boss abilities panel** | Battle tab | Low traffic feature; add collapsible list of boss special moves if `battle.boss_abilities` exists. |
| **Tab glyph pixel icons** | Tab bar | Decorative only. |
| **Trade UI inline** | Any | Currently links to `/trade`; complex to inline. |
| **NPC dialogue modals** | Explore tab | Low priority. |
