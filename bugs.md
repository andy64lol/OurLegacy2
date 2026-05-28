# Our Legacy 2 — Bug Tracker
> Last updated: 2026-05-27  
> Status legend: `TODO` · `IN PROGRESS` · `FIXED` · `WONTFIX`

---

## Vue Beta (`/beta`) Bugs

---

### BUG-V01 — Player attribute bonus fields reset on every state poll `FIXED`
**File:** `static/js/vue_beta.js` — `data()` init & `_applyState()`  
**Severity:** High — affects combat and stat display  
**Description:**  
`_applyState()` rebuilds the `player` object from scratch on every poll (every 2-7 s). The hardcoded
mapping only included `attr_gold_discount` and `attr_spell_power`. The fields `dodge_chance`,
`attr_crit_chance`, `attr_discovery`, and `attr_exp_bonus` were **never copied**, so they silently
reset to `undefined` after the first poll. The Equipment tab stat grid and Character tab both render
these fields conditionally (`v-if="player.dodge_chance"` etc.) — so they would flash on load then
disappear forever once the first poll fired.  
**Fix:** Added all four missing fields to both `data()` player initialiser and `_applyState()` mapping.

---

### BUG-V02 — Battle tab hijacks navigation every 2 s while in combat `FIXED`
**File:** `static/js/vue_beta.js` — `_applyState()`  
**Severity:** High — makes inventory/spells browsing during battle impossible  
**Description:**  
The auto-switch logic was:
```js
if (data.in_battle && this.activeTab !== "battle") this.activeTab = "battle";
```
This fires on **every poll** (every 2 s in combat). If a player navigated away from the Battle tab to
check inventory or cast a spell from another tab, the next poll would immediately force them back to
the Battle tab. Effectively locked players into the Battle tab for the entire fight.  
**Fix:** Capture `wasInBattle = this.inBattle` *before* updating `this.inBattle`, then switch tabs
only when the battle state **changes** (transition only):
```js
if (!wasInBattle && data.in_battle) this.activeTab = "battle";       // just entered battle
if (wasInBattle && !data.in_battle && this.activeTab === "battle") this.activeTab = "explore";
```

---

### BUG-V03 — Land harvest sends `plot_index` but API expects `slot_id` `FIXED`
**File:** `templates/vue_beta.html` — land tab farm section  
**Severity:** High — harvest button always fails silently (API looks up `crops.get("")`)  
**Description:**  
The Harvest button on farm plots sent `{ plot_index: idx }` (a numeric loop index). The
`/api/action/land/harvest` endpoint does `slot_id = str(body.get("slot_id", ""))` and then
`crops.get(slot_id)`. With `slot_id=""`, it always returns `None` → "Nothing planted in that slot."
error. The `/api/land_data` response farm_plots already include a `slot_id` field per plot.  
**Fix:** Changed to `{ slot_id: plot.slot_id }` to use the correct key.

---

### BUG-V04 — Land pet "Train" button calls stat-training endpoint with wrong params `FIXED`
**File:** `templates/vue_beta.html` — land tab pets section  
**Severity:** Medium — button does nothing useful; misleading UX  
**Description:**  
The Train button on each pet called `/api/action/land/train` with `{ pet_name: pet.name }`. That
endpoint is for **player stat training** (STR/DEX/INT boosts costing gold via `TRAINING_OPTIONS`) and
completely ignores `pet_name` — it expects `training_key`. Pet-specific training is a separate
mechanic not yet exposed via the API tab. The button would always return "Unknown training option."  
**Fix:** Removed the non-functional Train button from the pets panel. Pets are now display-only in
the Vue land tab until a proper pet-train panel is built (tracked in `VUE_BETA_TODO.md`).

---

### BUG-V05 — Dead reactive state `iframeLoaded` still in `data()` `FIXED`
**File:** `static/js/vue_beta.js` — `data()`  
**Severity:** Low — dead code / minor memory noise  
**Description:**  
`iframeLoaded: { leaderboard: false, wiki: false }` remained in `data()` after the land iframe was
eliminated and the leaderboard was rebuilt as a native Vue panel. Neither key is referenced anywhere
in the current template. Dead reactive state wastes Vue's observer budget and causes confusion when
reading the data model.  
**Fix:** Removed `iframeLoaded` entirely from `data()`.

---

### BUG-V06 — Dead `tabDropdownOpen` state + pointless global click listener `FIXED`
**File:** `static/js/vue_beta.js` — `data()` & `mounted()`  
**Severity:** Low — unnecessary event listener fires on every click anywhere on the page  
**Description:**  
The `...` overflow dropdown was hidden with `display:none` in CSS after the tab bar was made
horizontally scrollable, but `tabDropdownOpen: false` remained in `data()` and `mounted()` still
registered:
```js
document.addEventListener("click", () => { this.tabDropdownOpen = false; });
```
This listener fires on every document click and triggers a Vue reactivity update — setting
`tabDropdownOpen` to `false` when it was already `false`. Small overhead, but also a sign of dead
code that could confuse future developers.  
**Fix:** Removed `tabDropdownOpen` from `data()` and removed the global click listener from
`mounted()`.

---

### BUG-V07 — `spa.js` form-intercept loads in Vue beta (harmless but wasteful) `FIXED`
**File:** `templates/vue_beta.html` — script includes  
**Severity:** Low — extra script loaded, form-interceptor runs but never triggers  
**Description:**  
`vue_beta.html` loads `spa.js`, which on `DOMContentLoaded` calls `initSpaForms()` (hooks all forms
with `action` containing "/action/") and `spaStartPolling()`. The polling guard checks for
`#sidebar-level-val` or `#sidebar-atk-val` DOM elements — neither exist in Vue beta, so the
`setInterval` poll never starts. However `initSpaForms()` still registers a capturing `submit`
listener on the entire document. Vue beta uses `fetch()` not form POSTs, so the intercept never
fires, but it's still a waste and could cause confusing interactions if any native form is added.  
**Fix needed:** Remove the `<script src="/static/js/spa.js">` tag from `vue_beta.html`.  
Also applies to `game.js` which defines Jinja2-specific globals (`switchTab`, etc.) that don't
apply to Vue beta's DOM but load nonetheless.

---

### BUG-V08 — `marketReset()` calls old Jinja2 `/action/market/reset` route `WONTFIX`
**File:** `static/js/vue_beta.js` — `marketReset()`  
**Severity:** Low — works because the old route checks for XHR header and returns JSON, but  
it bypasses the standard `doAction()` wrapper (no `actionPending` lock, no unified error toast)  
**Description:**  
```js
const r = await fetch("/action/market/reset", { ... });
```
All other Vue beta actions use `doAction("/api/action/...")`. This one calls the legacy Jinja2 route
directly. The route does support XHR JSON responses so it works, but the double-invocation risk
(no `actionPending` guard) could cause race conditions if tapped repeatedly.  
**Fix needed:** Either add a `/api/action/market/reset` route that mirrors the Jinja2 one, or wrap
the existing call with the `doAction()` helper.

---

### BUG-V09 — Events tab has no Claim Reward button `FIXED`
**File:** `templates/vue_beta.html` — events tab  
**Severity:** Medium — players cannot claim event rewards from the Vue beta UI  
**Description:**  
The events tab shows active events with progress and claimed status, but there is no button to
actually claim a reward. The Jinja2 version has a form POST to `/action/event/claim`. No
`claimEventReward` method exists in `vue_beta.js` either. Players must use the Jinja2 UI to claim.  
**Fix needed:** Add claim button to event cards in template + `claimEventReward(evId)` method in JS
calling `/api/action/claim_event` (or equivalent endpoint).

---

### BUG-V10 — `inBattle` flag not in `data()` initial player; relies solely on first poll `FIXED`
**File:** `static/js/vue_beta.js` — `data()`  
**Severity:** Low — on first load, battle tab badge is always hidden until first poll (~0.5 s)  
**Description:**  
`window._betaInit` passed from server includes `in_battle` flag but `_applyState` is the only
place that reads `data.in_battle`. The initial `inBattle: false` in `data()` means users actively
in a battle see the non-battle UI briefly on page load until the first poll resolves.  
**Fix needed:** Read `window._betaInit.in_battle` in `data()` to set initial `inBattle` state.

---

### BUG-V11 — Pet name missing from Vue sidebar `FIXED`
**File:** `templates/vue_beta.html` — sidebar player panel  
**Severity:** Low — players with active pets can't see pet name at a glance  
**Description:**  
`templates/index.html:815-817` shows `Pet: {{ player.pet.replace('_',' ').title() }}` in the
sidebar if `player.pet` is set. Vue's sidebar player panel has no equivalent. The `player` object
already contains the `pet` field from the state poll.  
**Fix needed:** Add `<div v-if="player.pet" style="font-size:11px;color:var(--text-dim);margin-top:2px;">Pet: [[ player.pet.replace(/_/g,' ') ]]</div>` inside the sidebar player panel.

---

### BUG-V12 — Dungeon room progress bar missing in Vue `FIXED`
**File:** `templates/vue_beta.html` — dungeons tab active dungeon panel  
**Severity:** Medium — players can't see how far through a dungeon they are  
**Description:**  
`templates/index.html:1675-1676` renders a `bar-fill bar-exp` progress bar sized proportionally to
`room_index / rooms.length`. The Vue active dungeon panel (vue_beta.html ~line 1704) only shows
the text "Room X / Y" with no visual bar. The `activeDungeon.room_index` and
`activeDungeon.rooms.length` are already available in Vue state.  
**Fix needed:** Add progress bar below room text:
```html
<div class="bar-track" style="width:160px;margin-top:6px;">
  <div class="bar-fill bar-exp"
       :style="{ width: Math.round(((activeDungeon.room_index+1) / (activeDungeon.rooms?.length||1))*100)+'%' }">
  </div>
</div>
```

---

### BUG-V13 — Group tab missing real-time chat, sub-tabs, and level-up banner `FIXED`
**File:** `templates/vue_beta.html` + `static/js/vue_beta.js` — group tab  
**Severity:** Medium — major group feature gap vs Jinja2  
**Description:**  
The Jinja2 group tab (`templates/index.html:2915-3190`) has three features entirely absent from
the Vue beta:

1. **Real-time group chat** — Jinja2 spawns its own `io()` Socket.IO client and listens on
   `group_chat_message` + `group_chat_error` events. It renders a scrolling message list and a
   send-message input box in a dedicated "Group Chat" sub-panel.
2. **Sub-tab navigation** — Jinja2 has an Info / Members / Chat / Settings tab bar within the
   group panel (`.ag-tab-btn` elements). Vue renders everything as a single flat panel.
3. **Group level-up banner** — Jinja2 handles a `group_level_up` Socket.IO event and shows an
   animated fixed overlay banner with the new level + bonus XP/Gold.

The Vue group tab only shows: group name, invite code, member list (with kick), collect gold,
leave group, and create/join flows.  
**Fix needed (incremental):**
- Add Socket.IO connection to group namespace in `vue_beta.js` `mounted()` (same as existing `sio` connection for global chat)
- Listen for `group_chat_message` → push to `groupMessages` array
- Render message list + input in group panel template
- Handle `group_level_up` → show toast notification (or banner)

---

### BUG-V14 — "Bonus Modifiers" section absent from character tab `FIXED`
**File:** `templates/vue_beta.html` — character tab  
**Severity:** Low — players must navigate to Equipment tab to see Spell Power, Dodge, etc.  
**Description:**  
`templates/index.html:2621-2651` has a dedicated "Bonus Modifiers" named panel in the character
tab showing: Spell Power, Dodge Chance, Shop Discount, Item Discovery, EXP Bonus — all
conditionally rendered only if non-zero. Vue's character tab (vue_beta.html ~line 2010-2115)
has no equivalent section. These bonuses are only visible in the Vue Equipment tab stat-mini-grid
(vue_beta.html:1401-1405 shows Spell Power, Dodge, Crit, Shop Discount, Item Discovery, but NOT
`attr_exp_bonus`). Players who want to check their bonuses must know to look in Equipment, not
Character.  
**Fix needed:** Add a "Bonus Modifiers" panel to the character tab, mirroring `index.html:2621-2651`.
Also add `attr_exp_bonus` to the equipment stat-mini-grid (it's the one bonus still missing from
both tabs in Vue despite BUG-V01 fix — see BUG-S02).

---

### BUG-V15 — Group XP / level bar missing from group panel `FIXED`
**File:** `templates/vue_beta.html` — group tab  
**Severity:** Low — players can't track group progression  
**Description:**  
The Jinja2 group tab shows a group level badge, XP progress bar, and XP-to-next label. Vue shows
only `member_count` and `gold_pool` — no level or XP at all. The `/api/groups/my` endpoint likely
returns `level`, `xp`, and `xp_to_next` in the group object (used by the Jinja2 version).  
**Fix needed:** Add group level badge + XP bar to the Vue group panel using `groupData.level`,
`groupData.xp`, and `groupData.xp_to_next`.

---

### BUG-V16 — Dungeon abandon has no confirmation dialog `FIXED`
**File:** `templates/vue_beta.html` — dungeons tab  
**Severity:** Low — misclick can silently wipe all dungeon progress  
**Description:**  
Jinja2 uses `gameConfirm('Abandon this dungeon run? All progress will be lost.', ...)` before
submitting the abandon form. Vue's `@click="abandonDungeon"` fires the API call immediately
with no confirmation.  
**Fix needed:** Wrap `abandonDungeon` with a confirmation check:
```js
if (!confirm('Abandon this dungeon run? All progress will be lost.')) return;
```
Or use the existing `gameConfirm()` if it's available in the Vue context.

---

## Jinja2 (`/`) Bugs

---

### BUG-J01 — `pageable-list` pagination loses state after SPA AJAX DOM injection `FIXED`
**File:** `static/js/game.js` + `static/js/spa.js`  
**Severity:** Medium — page 2+ of a list becomes inaccessible after any action  
**Description:**  
`game.js` initialises all `.pageable-list` elements on `DOMContentLoaded` using `querySelectorAll`.
When `spa.js` intercepts a form POST, receives JSON, and injects updated HTML (e.g. new inventory
items), any `.pageable-list` in the injected HTML is **not re-initialised** because
`DOMContentLoaded` has already fired. The pagination controls render but clicking Next/Prev does
nothing because the event listeners were never attached.  
**Fix needed:** Call the pageable-list initialiser function again after every SPA DOM update, or use
event delegation rather than direct `addEventListener` on each list.

---

### BUG-J02 — Boss dialogue is a static template variable; never updates on SPA actions `FIXED`
**File:** `templates/index.html` + `app.py` — boss dialogue banner  
**Severity:** Low — boss dialogue shows only at page load, not after each attack/defend  
**Description:**  
`boss_dialogue` is injected at render time by Jinja2 from the server session. Once the page loads,
the dialogue is frozen. When `spa.js` handles an action and returns a JSON diff, the dialogue section
is not updated. So if a boss taunts on phase change after the page has been loaded, the dialogue
never appears unless the page is refreshed.  
**Fix needed:** Include `boss_dialogue` in the `/api/game/state` JSON response and update it via
`spaUpdatePlayerStats` or a dedicated DOM update in `spa.js`.

---

### BUG-J03 — `spa.js` calls `switchTab(data.tab)` using Jinja2 global — fails silently on errors `FIXED`
**File:** `static/js/spa.js`, `static/js/game.js`  
**Severity:** Low — cosmetic; wrong tab shown after some actions  
**Description:**  
After a SPA form POST succeeds, `spa.js` checks `if (data.tab && typeof switchTab === 'function')`.
`switchTab` is the Jinja2 version defined in `game.js`. If `switchTab` throws (because a referenced
DOM element doesn't exist at that moment), the error is swallowed silently and the user sees the
wrong tab.  
**Fix needed:** Wrap the `switchTab` call in a try/catch, or migrate to a more robust tab-switching
approach that verifies the target tab element exists first.

---

### BUG-J04 — Online player count in sidebar never updates without a full page reload `FIXED`
**File:** `templates/base.html` / `templates/index.html` — sidebar online count  
**Severity:** Low — cosmetic staleness  
**Description:**  
The Jinja2 sidebar shows online player count injected at render time (`{{ online_count }}`). The
`/api/game/state` polling response includes `online_count` but `spaUpdatePlayerStats` in `spa.js`
only updates HP/MP/EXP bars and gold, not the online count element. So the number shown is always
the count at page load time.  
**Fix needed:** Add `online_count` update to `spaUpdatePlayerStats` (or a sibling function), and
update the DOM element with id `sidebar-online-count` (or equivalent).

---

### BUG-J05 — Missing `X-Requested-With` header on some Jinja2 `/action/*` forms `TODO`
**File:** Various `templates/*.html` — action forms  
**Severity:** Low — affects SPA JSON fallback  
**Description:**  
`spa.js` intercepts form `submit` events and adds the `X-Requested-With: XMLHttpRequest` header on
the XHR. Flask routes check this header to return JSON vs redirect. However, any form that
bypasses `spa.js` (e.g. opened in a new tab, or if `spa.js` fails to load) will receive an HTML
redirect response instead of JSON, causing the SPA to break and fall back to `form.submit()` (a
full reload). This is the intended fallback, but could be avoided by adding the header to forms
directly.

---

## Shared / Both Versions

---

### BUG-S01 — No global unread DM badge in sidebar `FIXED`
**File:** `templates/vue_beta.html`, `templates/base.html`  
**Severity:** Low — DMs can go unnoticed  
**Description:**  
Neither version shows a global "You have X unread DMs" badge in the sidebar or navigation header.
The Vue beta has `totalDmUnread` computed and the Friends tab badge, but it's easy to miss if the
player is on another tab. The Jinja2 version has no DM feature at all.  
**Fix needed (Vue beta):** Show a small badge or glow on the sidebar Friends nav shortcut when
`totalDmUnread > 0`.

---

### BUG-S02 — `attr_exp_bonus` not shown anywhere in the UI `FIXED`
**File:** `templates/vue_beta.html`, `templates/index.html`  
**Severity:** Low — players can't see their EXP bonus from equipment  
**Description:**  
`attr_exp_bonus` is a valid player field (grants bonus EXP from kills) set by certain equipment.
The Jinja2 character sheet lists it in the "Bonus Modifiers" section. The Vue beta was missing the
field entirely from its player mapping (fixed in BUG-V01 above), but neither version prominently
surfaces it during combat or on level-up — it's buried in the character stat grid.

---

## Linter Report — 2026-05-27 (3 passes each)

> Tools run: **pyright** (Python static types), **eslint v10** (JS), **node \-\-check** (JS syntax),  
> **py_compile** (Python syntax), **manual grep** (anti-patterns), **Vue template audit** (Node.js)  
> Passes: 3 independent runs, results identical across all passes.

---

### Pyright — `app.py` + `utilities/`

| Pass | Errors | Warnings |
|------|--------|---------|
| 1 | 1 | 0 |
| 2 | 1 | 0 |
| 3 | **0** | **0** |

**BUG-L01 — `api_land_data`: `player` typed as `dict | None` passed to `_build_land_data`** `FIXED`  
`app.py:10682` — `_api_resolve_player()` returns `(None, err)` on failure and `(player, None)` on  
success. Pyright couldn't narrow the type after `if err: return err`, and `_build_land_data()`  
has a strict non-optional dict param. Added `assert player is not None` after the guard (matching  
the pattern already used on lines 9299 and 9479). Pass 3 confirms 0 errors.

### ESLint v10 — `static/js/vue_beta.js`

| Pass | Errors | Warnings |
|------|--------|---------|
| 1 | 0 | 25 |
| 2 | 0 | 25 |
| 3 | 0 | 25 |

All 25 warnings are `no-unused-vars` on intentional silent-catch placeholders (`catch (_) {}` and  
`catch (e) {}`). This is idiomatic JS for "we know an error can happen, we don't care".  
No action needed. Can be silenced with ESLint rule `"caughtErrorsIgnorePattern": "^_"`.

### ESLint v10 — `static/js/spa.js`

| Pass | Errors | Warnings |
|------|--------|---------|
| 1 | 0 | 3 |
| 2 | 0 | 3 |
| 3 | 0 | **1** |

**BUG-L02 — `spaUpdateMessages`: identical ternary branches, `onlyNew` param had no effect** `FIXED`  
`spa.js:102` — Both branches did `messages.slice(_lastMsgCount)`:
```js
// Before (bug):
var toShow = onlyNew ? messages.slice(_lastMsgCount) : messages.slice(_lastMsgCount);
// After (fixed):
var toShow = onlyNew ? messages.slice(_lastMsgCount) : messages;
```
When called with `onlyNew=false` the function would skip all existing messages and show nothing.  
Low-impact (only called with `onlyNew=true` currently), but would silently fail if the false branch  
were ever used.

**Remaining 2 warnings (cosmetic — no fix needed):**
- `spa.js:16` — `_pollTimer` assigned but not exposed: intentional module-private timer
- `spa.js:90` — `initLowHpWarning` not in ESLint globals: protected by `typeof` guard; defined in `game.js` in the Jinja2 context
- `spa.js:117` — `showToast` not in ESLint globals: protected by `typeof` guard; globally defined in `game.js`

### ESLint v10 — `static/js/game.js`

| Pass | Errors | Warnings |
|------|--------|---------|
| 1 | 0 | 13 |
| 2 | 0 | 13 |
| 3 | 0 | 13 |

All 13 warnings are false positives:

| Lines | Warning | Verdict |
|-------|---------|---------|
| 39, 185 | `history` not defined | `window.history` — valid browser global, missing from ESLint config |
| 339, 346, 839, 846, 911, 915 | `URL` not defined | `window.URL` — valid browser global, missing from ESLint config |
| 422, 1079, 1083 | `_e` defined but never used | `catch(_e){}` — intentional silent catch |
| 895 | `e` defined but never used | `catch(e){}` — intentional silent catch |
| 899 | `exitToMenu` never used | Called via `onclick="exitToMenu()"` in `templates/index.html:902` — ESLint can't see HTML |

No fixes needed for game.js. Add `URL`, `history`, `AudioContext` to ESLint globals to eliminate future false positives.

### `node --check` — All JS Files

All three files passed `node --check` (no syntax errors) across all three passes.

### `py_compile` — All Python Files

`app.py` and all 15 `utilities/*.py` files passed `py_compile` (no syntax errors) across all three passes.

### Vue Template Method Audit

All `@click` / `@submit` handler method names in `templates/vue_beta.html` verified against  
`vue_beta.js` — **zero genuinely missing method references**. All apparent "missing" results from  
grep-based scanning were v-for iteration variables (`attr`, `item`, `ev`, `plot`, `m`, etc.).

### Three-Pass Summary

| Category | Found | Fixed | False Positives | Remaining `TODO` |
|----------|-------|-------|-----------------|-----------------|
| Python type errors (pyright) | 1 | 1 | 0 | 0 |
| Python syntax errors | 0 | — | 0 | 0 |
| JS errors (eslint hard) | 0 | — | 0 | 0 |
| JS logic bugs (manual) | 1 (ternary) | 1 | 0 | 0 |
| JS warnings (eslint) | 41 | 1 | 38 | 2 (timer, `_pollTimer`) |
| JS syntax errors (node) | 0 | — | 0 | 0 |
| Vue template method refs | 0 missing | — | 24 (loop vars) | 0 |

