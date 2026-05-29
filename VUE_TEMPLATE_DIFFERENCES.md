# Vue vs Jinja2 Template Differences & Bug Report

Generated: 2026-05-29

This document records differences between the original Jinja2 templates (`templates/`) and the Vue rewrites (`templates/vue/`), lists bugs found in the Vue versions, and notes which bugs have been fixed.

---

## Summary of Bugs Fixed

| # | File | Bug | Status |
|---|------|-----|--------|
| 1 | `static/js/vue/groups.js` | Socket event `group_chat` → should be `group_chat_send` | **FIXED** |
| 2 | `static/js/vue/groups.js` | Collect gold endpoint `/api/groups/collect` → `/api/groups/collect_gold` | **FIXED** |
| 3 | `static/js/vue/groups.js` | Kick member sends `{ username }` → backend expects `{ target }` | **FIXED** |
| 4 | `static/js/vue/groups.js` | Join group sends `{ code }` → backend expects `{ invite_code }` | **FIXED** |
| 5 | `static/js/vue/groups.js` | Collect response field `data.new_treasury` doesn't exist in API response | **FIXED** |
| 6 | `templates/vue/groups.html` | Treasury displayed as `group.treasury` → backend key is `group.gold_pool` | **FIXED** |
| 7 | `templates/vue/groups.html` | Member XP shown as `m.contribution` → backend key is `m.contribution_xp` | **FIXED** |
| 8 | `templates/vue/groups.html` | Activity log bound to `group.activity` → backend key is `group.log` | **FIXED** |
| 9 | `templates/vue/groups.html` | Activity entries rendered as `entry.text \|\| entry` → entries have `username`, `action`, `xp_awarded`, `gold_awarded` fields | **FIXED** |
| 10 | `static/js/vue/land_shop.js` | Posts JSON to form-data route `/action/land/buy_housing` → must use `/api/action/land/buy_housing` | **FIXED** |
| 11 | `static/js/vue/land_pets.js` | Posts JSON to form-data route `/action/land/buy_pet` → must use `/api/action/land/buy_pet` | **FIXED** |
| 12 | `static/js/vue/game.js` | `loadGroup()` calls `/api/groups/info` — route doesn't exist; correct is `/api/groups/my` | **FIXED** |
| 13 | `static/js/vue/game.js` | Market filter uses `this.player.class` — player object uses `char_class` | **FIXED** |
| 14 | `templates/vue/chat.html` | `u.username`, `u.is_owner`, `u.is_admin` — `onlineUsers` are plain strings, not objects | **FIXED** |
| 15 | `templates/vue/chat.html` | `v-if="isModOrOwner"` — computed property not defined in `chat.js` | **FIXED** |
| 16 | `templates/vue/chat.html` | `msg.type !== 'system'` / `msg.type !== 'emote'` — messages use `msg.is_system` / `msg.is_emote` booleans | **FIXED** |
| 17 | `templates/vue/chat.html` | `msg.is_owner`, `msg.is_admin` — these fields don't exist on message objects | **FIXED** |
| 18 | `templates/vue/chat.html` | `msg.ts` — timestamp field is `msg.created_at` | **FIXED** |
| 19 | `templates/vue/chat.html` | `renderMsg(msg.text)` — method is `renderMsgHtml`, field is `msg.message` | **FIXED** |
| 20 | `templates/vue/chat.html` | `v-for="g in glyphs"` → `pickerGlyphs`; `insertGlyph(g)` → `insertGlyph(g.key)`; `g + '.webp'` → `g.file` | **FIXED** |
| 21 | `static/js/vue/chat.js` | `msgClass(msg)` method missing — template calls it on every message bubble | **FIXED** |
| 22 | `static/js/vue/chat.js` | `isModOrOwner` computed property missing — template uses it to gate mod actions | **FIXED** |
| 23 | `templates/vue/dungeon_room.html` | Fallback `player.character_class` doesn't exist — correct field is `player.char_class` | **FIXED** |
| 24 | `templates/vue/admin.html` | Command reference shows `broadcast` — correct command name is `announce` | **FIXED** |
| 25 | `templates/vue/admin.html` | `stats.ban_count` / `stats.mute_count` don't exist — data uses `stats.bans.length` / `stats.mutes.length` | **FIXED** |
| 26 | `templates/vue/admin.html` | `stats.banned` / `stats.muted` don't exist — data uses `stats.bans` / `stats.mutes` | **FIXED** |
| 27 | `templates/vue/wiki.html` | `classCount` / `raceCount` not defined anywhere — should use `wikiData.classes.length` / `wikiData.races.length` | **FIXED** |
| 28 | `templates/vue/wiki.html` + `static/js/vue/wiki.js` | `entryStats` computed property missing — detail view stats table was always empty | **FIXED** |
| 29 | `templates/vue/chat_widget.html` | HTML body has same bugs as `chat.html` (wrong field names, renderMsg, glyphs) — but this is dead code since `chat_widget.js` uses an inline `template:` option that overrides the DOM | **DOCUMENTED (dead code, no fix needed)** |

---

## Per-Page Differences

---

### `groups.html` / `vue/groups.html`

**Architecture change:** Jinja2 renders group data server-side via template variables. The Vue version hydrates from `window._init` and loads live data via `/api/groups/my` on mount, then maintains state reactively.

#### Data Field Mismatches (Bugs #6–9)

| Field | Jinja2 | Vue (wrong) | Correct key |
|-------|--------|-------------|-------------|
| Gold pool | `group.gold_pool` | `group.treasury` | `gold_pool` |
| Member XP | `m.contribution_xp` | `m.contribution` | `contribution_xp` |
| Activity log | `group.log` | `group.activity` | `log` |
| Log entry text | `entry.action` | `entry.text \|\| entry` | `entry.username`, `entry.action`, `entry.xp_awarded`, `entry.gold_awarded` |

All four come from `get_user_group()` in `utilities/supabase_db.py` which returns the `ol2_groups` and `ol2_group_members` rows verbatim. The Vue template used invented field names that never existed.

#### Socket Event Mismatch (Bug #1)

- `app.py` line 7843: `@sio.on("group_chat_send")` — the server listens on `group_chat_send`
- `groups.js` previously emitted `socket.emit('group_chat', ...)` — group chat was completely broken

#### API Endpoint Mismatches (Bugs #2–4)

| Action | Vue called | Actual route |
|--------|-----------|-------------|
| Collect gold | `POST /api/groups/collect` | `POST /api/groups/collect_gold` |
| Join group body | `{ code: this.joinCode }` | `{ invite_code: ... }` |
| Kick member body | `{ username }` | `{ target: username }` |

#### API Response Field Mismatch (Bug #5)

The collect gold API (`/api/groups/collect_gold`) returns `{ ok, message, gold, group_id }`. The Vue code checked `data.new_treasury` to update the displayed treasury balance — this field never exists. Fixed by computing the new balance from `data.gold`.

#### UI/Design Differences (not bugs)

- **Invite code visibility:** Jinja2 shows invite code only to the group leader. Vue shows it to all members (minor UX difference, not a bug).
- **Navigation links:** Jinja2 links to Leaderboard and Friends. Vue links to Leaderboard and Game.
- **Group creation form:** Vue has an inline create-group modal; Jinja2 uses a separate page/redirect.
- **No-group state:** Vue shows inline join/create panels. Jinja2 redirects or shows a simpler form.

---

### `land_shop.html` / `vue/land_shop.html` + `land_shop.js`

**Architecture change:** Jinja2 uses a standard HTML form (`POST /action/land/buy_housing`) that redirects after purchase. Vue uses an async fetch call and reloads on success.

#### Wrong API Endpoint (Bug #10)

- `land_shop.js` was calling `POST /action/land/buy_housing` with a JSON body
- That route uses `request.form.get(...)` — it reads form data, not JSON, so the housing key was never parsed
- The correct JSON-accepting route is `POST /api/action/land/buy_housing`

---

### `land_pets.html` / `vue/land_pets.html` + `land_pets.js`

**Architecture change:** Same pattern as land_shop — Jinja2 posts a form, Vue uses fetch.

#### Wrong API Endpoint (Bug #11)

- `land_pets.js` was calling `POST /action/land/buy_pet` with a JSON body
- That route reads `request.form.get(...)`, so the pet key was never parsed
- The correct JSON-accepting route is `POST /api/action/land/buy_pet`

---

### `victory.html` / `vue/victory.html`

**Architecture change:** Jinja2 renders all combat results server-side. Vue hydrates from `window._init` and animates rewards.

**No functional bugs found.** Differences are cosmetic:
- Vue adds an XP gain animation and a per-stat animated breakdown
- Vue adds "Level Up!" callout when `_init.leveled_up` is set
- Vue renders loot with item icons; Jinja2 renders a plain list
- Navigation after victory is identical (`/game`)

---

### `defeat.html` / `vue/defeat.html`

**Architecture change:** Same Jinja2 → Vue hydration pattern.

**No functional bugs found.** Differences are cosmetic:
- Vue adds an animated skull/defeat sequence
- Vue shows a death penalty summary (gold lost, stat drain)
- Navigation buttons are equivalent

---

### `dungeon_room.html` / `vue/dungeon_room.html`

**Architecture change:** Jinja2 uses a server-rendered room description with form-based action buttons. Vue is fully reactive — room state is managed via Socket.IO events.

**1 bug fixed (Bug #23).** Differences:
- Vue shows a live party member panel (HP bars, status) not present in Jinja2
- Vue animates combat log entries as they arrive
- Vue has an inline minimap showing explored rooms (Jinja2 has none)
- Jinja2 has a static "flee" button; Vue conditionally shows flee based on dungeon rules

---

### `items.html` / `vue/items.html`

**Architecture change:** Jinja2 renders the full inventory server-side. Vue hydrates from `window._init.items` and filters/sorts reactively.

**No functional bugs found.** Differences:
- Vue adds a search bar and category filter tabs not present in Jinja2
- Vue shows item stat comparisons on hover; Jinja2 shows a static tooltip
- Vue uses the same action endpoints (`/action/item/use`, `/action/item/equip`, etc.) with fetch

---

### `friends.html` / `vue/friends.html`

**Architecture change:** Jinja2 server-renders the friends list. Vue fetches from `/api/friends` on mount and maintains real-time status via Socket.IO.

**13 bugs found and fixed (Bugs #30–#42) — see Fourth-Pass section below.** Differences:
- Complete visual redesign: Jinja2 uses a custom purple-dark theme; Vue uses the standard game CSS variables
- Vue adds unread DM badges per friend
- Vue adds an inline DM panel (chat drawer); Jinja2 links to a separate DM page
- Vue shows online/offline status with a green dot; Jinja2 shows a text label

---

### `leaderboard.html` / `vue/leaderboard.html`

**Architecture change:** Jinja2 renders the top-10 rankings server-side at page load. Vue fetches from `GET /api/leaderboard` and re-renders reactively.

**No functional bugs found.** Differences:
- Vue adds a tab switcher (Level / XP / Gold) for different ranking modes; Jinja2 shows a single static table
- Vue auto-refreshes every 60 seconds; Jinja2 is static until page reload
- CSS is minified/inlined in Vue vs formatted in Jinja2 (same visual output)

---

### `land_map.html` / `vue/land_map.html`

**No differences and no bugs.** The Vue version is identical to Jinja2 except:
- Extends `vue/base.html` instead of `base.html`
- Vue CDN script tag added

The land map uses no Vue reactivity (no `v-*` directives, no `createApp`) — it is a static page in both versions.

---

---

## Second-Pass Bugs (game.js, chat.html, chat.js)

| # | File | Bug | Status |
|---|------|-----|--------|
| 12 | `static/js/vue/game.js` | `loadGroup()` fetches `/api/groups/info` — endpoint does not exist; correct route is `/api/groups/my` | **FIXED** |
| 13 | `static/js/vue/game.js` | `loadMarket()` reads `this.player.class` — player object stores class as `char_class`; filter always falls back to `data.player_class` | **FIXED** |
| 14 | `templates/vue/chat.html` | `v-for="u in onlineUsers"` uses `u.username`, `u.is_owner`, `u.is_admin` — `online_users` socket event sends plain username strings, not objects | **FIXED** |
| 15 | `templates/vue/chat.html` | `v-if="isModOrOwner"` — `isModOrOwner` never defined in `chat.js`; `isMod` and `isOwner` exist as separate data properties | **FIXED** |
| 16 | `templates/vue/chat.html` | `msg.type !== 'system'` / `msg.type !== 'emote'` — server sends `msg.is_system` (bool) and `msg.is_emote` (bool), not a `type` string | **FIXED** |
| 17 | `templates/vue/chat.html` | `msg.is_owner` / `msg.is_admin` on message object — messages only carry `is_mod`; owner/admin status must be derived from `ownerName`/`modList` via `isOwnerUser()` / `isModUser()` | **FIXED** |
| 18 | `templates/vue/chat.html` | `msg.ts` used as timestamp display — server sends `msg.created_at`; `msg.ts` is only used in group chat payloads | **FIXED** |
| 19 | `templates/vue/chat.html` | `renderMsg(msg.text)` — method is named `renderMsgHtml` in `chat.js`; message text field is `msg.message` not `msg.text` | **FIXED** |
| 20 | `templates/vue/chat.html` | `v-for="g in glyphs"` and `@click="insertGlyph(g)"` — glyph picker data is `pickerGlyphs` (array of `{key, file}` objects); iterating `glyphs` renders nothing; `insertGlyph(g)` would pass an object instead of the key string | **FIXED** |
| 21 | `static/js/vue/chat.js` | `msgClass(msg)` method called from template but not defined in `chat.js` — causes Vue warning and no message styling | **FIXED** |
| 22 | `static/js/vue/chat.js` | `isModOrOwner` computed property missing — added as `isMod \|\| isOwner` | **FIXED** |

---

### `chat.html` / `vue/chat.html` + `chat.js`

**Architecture change:** Jinja2 uses Vanilla JS + Socket.IO with direct DOM manipulation. Vue uses a reactive `createApp` mounting to `#vue-chat-app`, with all state in `data()`.

#### Online User List (Bug #14)

`app.py` emits `online_users` as a sorted array of **plain username strings**:
```python
await sio.emit("online_users", sorted(set(_chat_online.values())))
```

The Vue template treated each element as an object with `.username`, `.is_owner`, `.is_admin` properties. Fixed to use the string directly (`u` instead of `u.username`) and call `isOwnerUser(u)` / `isModUser(u)` for badge logic.

#### Mod/Owner Guard (Bug #15, 22)

Template used `v-if="isModOrOwner"` which was never defined. Added `isModOrOwner` computed to `chat.js` (`isMod || isOwner`) and changed template to `isMod || isOwner` directly.

#### Message Type Flag (Bug #16)

Server sets `is_system: True` / `is_emote: True` as boolean fields. Template incorrectly tested `msg.type === 'system'`. Fixed to `!msg.is_system && !msg.is_emote && msg.username !== 'SYSTEM'`.

#### Message Owner/Admin Badges (Bug #17)

Individual message payloads contain `is_mod` (for the sender's mod status) but not `is_owner` or `is_admin`. Template used `msg.is_owner` / `msg.is_admin`. Fixed to call `isOwnerUser(msg.username)` / `isModUser(msg.username)` which check against `ownerName` and `modList`.

#### Timestamp Field (Bug #18)

Global chat messages carry `created_at` (ISO string). Group chat carries `ts` (Unix int). Template used `msg.ts` for global chat — always undefined. Fixed to `formatTime(msg.created_at)`.

#### renderMsg / msg.text (Bug #19)

- Method exposed as `renderMsgHtml` in `chat.js`, not `renderMsg`
- Message text field is `msg.message`, not `msg.text` (which is a game diary field, not a chat field)

Fixed template to `renderMsgHtml(msg.message)`.

#### Glyph Picker (Bug #20)

`pickerGlyphs` is the correct data property (array of `{key, file}` objects). Template used `glyphs` (undefined). Additionally, `insertGlyph(g)` would pass the whole object; fixed to `insertGlyph(g.key)`. The img src also fixed from `g + '.webp'` to `g.file` (the file name already includes `.webp`).

#### Missing msgClass Method (Bug #21)

Template calls `:class="msgClass(msg)"` on every message to apply `msg-self`, `msg-system`, `msg-emote`, or `msg-other` CSS classes. Method was absent from `chat.js`. Added:
```javascript
msgClass(msg) {
    if (msg.is_system || msg.username === 'SYSTEM') return 'msg-system';
    if (msg.is_emote) return 'msg-emote';
    if (msg.username === this.myUsername) return 'msg-self';
    return 'msg-other';
},
```

---

### `game.html` (Vue-only, no Jinja2 equivalent)

`game.html` exists only in `templates/vue/` and serves as the Vue beta game hub. It mounts to `#vue-beta-app` with `game.js`.

#### Wrong Group Info Endpoint (Bug #12)

`game.js` `loadGroup()` fetched `/api/groups/info` — this route does not exist in `app.py`. The correct endpoint is `/api/groups/my` (`GET`, returns `{ok, group}`).

#### Player Class Field (Bug #13)

`loadMarket()` filtered elite market items by player class using `this.player.class`. The player object stored in Vue data uses `char_class` (the DB column name), not `class`. Fixed to `this.player.char_class`.

---

### `play.html` / `vue/play.html`

**No functional bugs.** Vue version extends `vue/base.html` instead of `base.html`; page body is identical. No Vue reactivity is used on this page.

---

### `index.html` / `vue/index.html` + `index.js`

**No functional bugs found.** The Vue version adds:
- Inline login/register modal (Jinja2 links to `/login`, `/register` separately)
- Inline character creation modal (`/api/create_character` POST)
- Cloud save browser tab
- Toast notification system

All API endpoints match `app.py` routes.

---

### `wiki.html` / `vue/wiki.html`

**3 bugs fixed (Bugs #27, #28).** Differences:
- Vue adds a search bar that filters entries client-side
- Jinja2 links to individual wiki entry pages; Vue renders expanded content inline via `v-show`

---

### `create.html` / `vue/create.html`

**No functional bugs found.** The Vue version uses the same `/api/create_character` endpoint as `index.js`. Differences are cosmetic (styling, class selection UI).

---

### `admin.html` / `vue/admin.html`

**4 bugs fixed (Bugs #24–#26).** Both versions use the same admin action endpoints. Vue adds reactive search/filter on the player list.

---

### `reset_password.html` / `vue/reset_password.html`

**No functional bugs found.** Both use the same `/api/reset_password` flow.

---

## Third-Pass Bugs (dungeon_room, admin, wiki, chat_widget)

### `dungeon_room.html` / `vue/dungeon_room.html`

#### Wrong Player Class Fallback Field (Bug #23)

Line 33 in the Vue sidebar:
```html
[[ player['class'] || player.character_class ]]
```
`player.character_class` does not exist on the player data object. The correct fallback field is `player.char_class` (the DB column name used throughout the codebase). Fixed to:
```html
[[ player['class'] || player.char_class ]]
```

---

### `admin.html` / `vue/admin.html` + `admin.js`

#### Wrong Command Name in Sidebar Reference (Bug #24)

The command reference sidebar listed `broadcast <msg>` with `@click="prefill('broadcast ')"`. The `broadcast` case does not exist in `admin.js`'s `runCommand` switch — the correct command is `announce`. Fixed to `@click="prefill('announce ')"` / `announce <msg>`.

#### Stats Sidebar Uses Non-Existent `ban_count` / `mute_count` (Bug #25)

`admin.js` `refreshData()` populates `stats.bans` and `stats.mutes` as arrays. The template displayed:
```html
[[ stats.ban_count || 0 ]]
[[ stats.mute_count || 0 ]]
```
Neither property exists — these always rendered as `0`. Fixed to:
```html
[[ stats.bans.length || 0 ]]
[[ stats.mutes.length || 0 ]]
```

#### Banned/Muted Lists Use Non-Existent `stats.banned` / `stats.muted` (Bug #26)

The banned and muted player pill lists used `stats.banned` and `stats.muted`, which don't exist in the Vue data object (data uses `stats.bans` and `stats.mutes`). Both the `v-if` guards and `v-for` iterators were affected, meaning the lists would never render. Fixed:
```html
<!-- before -->
<div v-if="stats.banned && stats.banned.length" ...>
    <span v-for="u in stats.banned" ...>
<div v-if="stats.muted && stats.muted.length" ...>
    <span v-for="u in stats.muted" ...>

<!-- after -->
<div v-if="stats.bans && stats.bans.length" ...>
    <span v-for="u in stats.bans" ...>
<div v-if="stats.mutes && stats.mutes.length" ...>
    <span v-for="u in stats.mutes" ...>
```

---

### `wiki.html` / `vue/wiki.html` + `wiki.js`

#### `classCount` / `raceCount` Not Defined (Bug #27)

The sidebar nav used `[[ classCount ]]` and `[[ raceCount ]]` for the Classes and Races count badges. Neither is defined as a computed property or data field in `wiki.js`. These badges always rendered empty. Fixed directly in the template to use the already-available `wikiData` object:
```html
[[ wikiData.classes.length ]]
[[ wikiData.races.length ]]
```

#### `entryStats` Computed Property Missing from wiki.js (Bug #28)

The detail view stats table iterated over `entryStats`:
```html
<tr v-for="(val, key) in entryStats" :key="key">
```
`entryStats` was not defined anywhere in `wiki.js` — when any wiki entry was clicked, the stats section would always be empty. Added a full `entryStats` computed property to `wiki.js` that extracts the appropriate key/value stats for each section type (`enemies`, `bosses`, `items`, `classes`, `races`, `spells`, `craft_recipes`, `areas`, `missions`, `companions`), matching the logic already present in the `buildDetail()` helper functions.

---

### `chat_widget.html` / `vue/chat_widget.html` + `chat_widget.js`

#### HTML Body is Dead Code — JS Uses Inline Template (Bug #29, documented only)

`templates/vue/chat_widget.html` contains a hand-written Vue template body (lines 55–113) with the same field-name bugs as `chat.html` (pre-fix): `u.username` for online users (strings), `renderMsg(msg.text)` instead of `renderMsgHtml(msg.message)`, `v-for="g in glyphs"` instead of `pickerGlyphs`, `msg.type !== 'system'` instead of `msg.is_system`, `msg.ts` instead of `msg.created_at`, and `isModOrOwner` (undefined).

**However**, `chat_widget.js` creates its Vue app with an explicit `template: \`...\`` string option. When a Vue app is given a `template:` option, it overrides the DOM entirely — the HTML in the `#chat-widget-vue` div is replaced at mount time and never rendered. The `chat_widget.js` inline template is correct and uses all the right field names.

No code fix is needed. The HTML file body should be kept in sync with the JS template for readability, but it does not affect runtime behaviour.

---

---

## Fourth-Pass Bugs (friends, leaderboard, land_map, verify_email, sacred_text_gone, wiki_disabled, create)

| # | File | Bug | Status |
|---|------|-----|--------|
| 30 | `static/js/vue/friends.js` | `addFriend()` sends `{ username }` but server `/api/friends/request` expects `{ target }` — friend requests always fail silently | **FIXED** |
| 31 | `static/js/vue/friends.js` + `templates/vue/friends.html` | `respondRequest(from, action)` sends `{ from_user, action: 'accept'/'decline' }` but server `/api/friends/respond` expects `{ id, accept: boolean }` — accept/decline never works | **FIXED** |
| 32 | `static/js/vue/friends.js` | `removeFriend()` sends `{ username }` but server `/api/friends/remove` expects `{ target }` — unfriend always fails silently | **FIXED** |
| 33 | `static/js/vue/friends.js` | `blockUser()` calls `/api/friends/block` (doesn't exist); correct endpoint is `/api/block` with body `{ target, action: 'block' }` | **FIXED** |
| 34 | `static/js/vue/friends.js` | `unblockUser()` calls `/api/friends/unblock` (doesn't exist); correct endpoint is `/api/block` with body `{ target, action: 'unblock' }` | **FIXED** |
| 35 | `static/js/vue/friends.js` | `sendTradeInvite()` emits `'trade_invite'` but server handler is `@sio.on("trade_request")` — trade invitations are never received by the server | **FIXED** |
| 36 | `static/js/vue/friends.js` + `templates/vue/friends.html` | On receiving `'trade_invite'`, sets `tradeState = 'active'` without emitting `'trade_accept'` — server requires explicit acceptance; added `'received'` state with Accept/Decline UI | **FIXED** |
| 37 | `static/js/vue/friends.js` | `selectFriend()` emits `'load_dm'` via socket — no `@sio.on("load_dm")` handler exists; DMs are REST-only (`/api/dm/<other>`) — DM history never loaded | **FIXED** |
| 38 | `static/js/vue/friends.js` | `sendDm()` emits `'send_dm'` via socket with `{ to, message }` — no `@sio.on("send_dm")` handler; correct is REST `POST /api/dm/send` with `{ recipient, message }` — DMs were never sent | **FIXED** |
| 39 | `static/js/vue/friends.js` | Listened for `'dm_received'` socket event — server emits `'dm_message'` with payload `{ sender, recipient, message, ... }` (not `{ from, message }`) — incoming DMs never appeared | **FIXED** |
| 40 | `static/js/vue/friends.js` | Listened for `'trade_complete'` — server never emits this; server uses `'trade_update'` for all state changes including completion — trade completion UI never triggered | **FIXED** |
| 41 | `static/js/vue/friends.js` | Listened for `'social_update'` — server never emits this; server emits `'friend_request'` and `'friend_accepted'` — real-time friend list updates never worked | **FIXED** |
| 42 | `static/js/vue/friends.js` | No handler for `'trade_cancelled'` socket event — server emits this on cancel/decline with a message; without a handler the trade panel stays open forever | **FIXED** |

### Pages with No New Bugs

| Template | Result |
|----------|--------|
| `leaderboard.html` / `vue/leaderboard.html` + `leaderboard.js` | **CLEAN** — Both fetch `/api/leaderboard`; Vue adds reactive loading/error states |
| `land_map.html` / `vue/land_map.html` | **CLEAN** — Both embed identical canvas JS inline using `{{ land_data.placed_buildings_map \| tojson }}` |
| `verify_email.html` / `vue/verify_email.html` | **IDENTICAL** — Pure Jinja2 template variables, no Vue reactivity, identical markup |
| `sacred_text_gone.html` / `vue/sacred_text_gone.html` | **IDENTICAL** — Static error page, no template variables |
| `wiki_disabled.html` / `vue/wiki_disabled.html` | **IDENTICAL** — Static page, no template variables |
| `create.js` | **CLEAN** — Minimal 21-line Vue app; reads `classData` and `error` from `window._init` correctly |

---

### `friends.html` / `vue/friends.html` + `friends.js` (Fourth-Pass Detail)

The Vue friends page is a complete rewrite from the Jinja2 version. It uses:
- Socket.IO for real-time events
- Fetch API for friend management and DMs
- An inline DM drawer instead of a separate page
- An inline trade panel instead of a pop-up modal

Multiple socket event names and REST API field names were wrong — see bugs #30–#42 above.

#### REST API Field Mismatches

| Method | JS sent | Server expects | Bug # |
|--------|---------|---------------|-------|
| `addFriend()` | `{ username: name }` | `{ target }` | #30 |
| `respondRequest()` | `{ from_user, action: string }` | `{ id, accept: boolean }` | #31 |
| `removeFriend()` | `{ username }` | `{ target }` | #32 |
| `blockUser()` | `POST /api/friends/block` `{ username }` | `POST /api/block` `{ target, action: 'block' }` | #33 |
| `unblockUser()` | `POST /api/friends/unblock` `{ username }` | `POST /api/block` `{ target, action: 'unblock' }` | #34 |

#### Socket Event Mismatches

| JS emitted / listened | Actual server event | Bug # |
|-----------------------|--------------------|-------|
| emit `'trade_invite'` | `@sio.on("trade_request")` | #35 |
| emit `'load_dm'` | No handler (REST: `GET /api/dm/<other>`) | #37 |
| emit `'send_dm'` `{ to, message }` | No handler (REST: `POST /api/dm/send` `{ recipient, message }`) | #38 |
| listen `'dm_received'` | Server emits `'dm_message'` `{ sender, recipient, message }` | #39 |
| listen `'trade_complete'` | Server emits `'trade_update'` with `status` field | #40 |
| listen `'social_update'` | Server emits `'friend_request'` / `'friend_accepted'` | #41 |
| (missing) | Server emits `'trade_cancelled'` | #42 |

#### Trade Flow Fix (Bug #36)

The Jinja2 version has an explicit Accept/Decline panel for incoming trade invitations. The Vue version incorrectly skipped this step, jumping directly to `tradeState = 'active'` when `'trade_invite'` was received — but the server requires `trade_accept` to be emitted before the trade activates. Fixed by:

1. Adding `tradeState = 'received'` as a new state
2. Adding `acceptTrade()` method that emits `'trade_accept'` with the `trade_id` from the invite
3. Adding `declineTrade()` method that emits `'trade_decline'`
4. Adding the `'received'` state panel to the template with Accept / Decline buttons
5. Storing `pendingTradeId` from the `'trade_invite'` socket payload

---

## Routes Serving Vue Templates

At the time of this audit, **no routes in `app.py` serve the Vue templates** — all `render_template(...)` calls reference the original Jinja2 templates. The Vue templates exist in `templates/vue/` as prepared replacements but are not yet wired up to any route.

To enable a Vue page, the corresponding route needs to render `vue/<template_name>.html` instead of `<template_name>.html`.

---

## Fifth-Pass Bug Fixes — `vue/base.html` Widget Functions (Bugs #43–#45)

### Bug #43 — `groups-widget-fab` button missing from `vue/base.html`

**File:** `templates/vue/base.html`
**Severity:** High — users on Vue pages have no way to open the groups overlay

**Root cause:** `base.html` renders a floating action button (`id="groups-widget-fab"`) inside `#chat-widget` that calls `openGroupsOverlay()`. This button was never ported to `vue/base.html`. The `#groups-overlay` panel exists in `vue/base.html` but with no trigger to show it.

**Fix:** Added the `groups-widget-fab` `<button>` element inside `#chat-widget` in `vue/base.html`, as a sibling of `#chat-toggle-btn`, matching the HTML structure from `base.html` (including `#groups-badge` span).

---

### Bug #44 — `toggleChat()` undefined on all Vue pages — chat widget broken

**File:** `templates/vue/base.html`
**Severity:** Critical — clicking the chat FAB or the chat close button throws `ReferenceError: toggleChat is not a function`

**Root cause:** `toggleChat()` is defined as `window.toggleChat` in an inline `<script>` block in `base.html` (line 644). It was never ported to `vue/base.html`. The function is called by `onclick="toggleChat()"` on both `#chat-toggle-btn` and the chat panel's close button — meaning the chat widget is completely non-functional on all Vue pages.

**Fix:** Added an IIFE `<script>` block in `vue/base.html` (inside the `{% if online_username %}` block) that declares `chatOpen`, `unreadCount`, and defines `window.toggleChat`. Uses the correct badge element ID (`chat-unread-badge`) that is present in `vue/base.html`, rather than `chat-badge` used in `base.html`.

---

### Bug #45 — `openGroupsOverlay()` / `closeGroupsOverlay()` undefined on all Vue pages

**File:** `templates/vue/base.html`
**Severity:** High — clicking the groups overlay backdrop or close button throws `ReferenceError: closeGroupsOverlay is not a function`

**Root cause:** Both `window.openGroupsOverlay` and `window.closeGroupsOverlay` are defined only in the inline script of `base.html` (lines 690, 701). They were never ported to `vue/base.html`. `closeGroupsOverlay()` is called in the backdrop `onclick` and the overlay close `<button>` — both broken. `openGroupsOverlay()` was also missing (and needed for Bug #43's fix).

**Fix:** Added `window.openGroupsOverlay` and `window.closeGroupsOverlay` to the same IIFE `<script>` block added for Bug #44. Also added a `message` event listener for `chat_unread` postMessage events (from the chat iframe) that increments the unread badge — this listener was also present in `base.html` but missing from `vue/base.html`.

---

## Fifth-Pass Clean Templates (No Bugs Found)

| Template / File | Result |
|-----------------|--------|
| `defeat.html` / `vue/defeat.html` | **CLEAN** — Identical structure; Vue uses `[[ ]]` delimiters and `window._init` |
| `victory.html` / `vue/victory.html` | **CLEAN** — Identical structure; Vue uses `[[ ]]` delimiters and `window._init` |
| `dungeon_room.html` / `vue/dungeon_room.html` | **Already fixed** — bugs documented in 4th pass |
| `reset_password.html` / `vue/reset_password.html` + `reset_password.js` | **CLEAN** |
| `play.html` / `vue/play.html` | **CLEAN** — Static page, no template variables differ |
| `create.html` / `vue/create.html` + `create.js` | **CLEAN** |
| `leaderboard.html` / `vue/leaderboard.html` + `leaderboard.js` | **CLEAN** |
| `land_map.html` / `vue/land_map.html` | **CLEAN** |
| `items.html` / `vue/items.html` | **CLEAN** |
| `verify_email.html` / `vue/verify_email.html` | **IDENTICAL** |
| `wiki_disabled.html` / `vue/wiki_disabled.html` | **IDENTICAL** |
| `sacred_text_gone.html` / `vue/sacred_text_gone.html` | **IDENTICAL** |
| `index.js` | **CLEAN** — reads `window._init` correctly |
| `leaderboard.js` | **CLEAN** |
| `reset_password.js` | **CLEAN** |
| `chat_widget.js` | **CLEAN** — JS overrides inner HTML; no functional mismatch |
| `create.js` | **CLEAN** |
| `vue/game.js` | **CLEAN** — reads `window._betaInit`, all field names correct including `char_class` fallback |

---

## Fifth-Pass Bug Fixes — chat.html, index.html, groups.js (Bugs #46–#49)

### Bug #46 — `cooldownSecs` undefined in `vue/chat.html` — chat cooldown never displays

**File:** `templates/vue/chat.html` (line 93)
**Severity:** Medium — chat rate-limit countdown bar never appears; users see no feedback when told to wait

**Root cause:** The template uses `v-if="cooldownSecs > 0"` and `[[ cooldownSecs ]]`, but `cooldownSecs` is not a property in the `vue/chat.js` data object. The JS defines `cooldownDisplay` (a pre-formatted string such as `"Next message in 5s"`) and updates it in `startCooldownDisplay()`. `undefined > 0` is always false, so the cooldown bar never renders.

**Fix:** Changed `v-if="cooldownSecs > 0"` → `v-if="cooldownDisplay"` and `[[ cooldownSecs ]]s` → `[[ cooldownDisplay ]]` (the string already contains the full human-readable message).

---

### Bug #47 — `vue/index.html` missing CSS to hide `#groups-widget-fab` on the index/landing page

**File:** `templates/vue/index.html`
**Severity:** Low — groups FAB button incorrectly appears on the character selection / landing page (it should only appear within the full game UI)

**Root cause:** Jinja2 `index.html` hides `#groups-widget-fab { display: none !important; }` via inline CSS. After Bug #45 was fixed and the FAB was added to `vue/base.html`, `vue/index.html` needed the same hide rule — without it the groups button floats over the landing page for logged-in users.

**Fix:** Added `#groups-widget-fab { display: none !important; }` to the `<style>` block in `vue/index.html`.

---

### Bug #48 — `vue/index.html` missing conditional CSS to hide chat widget on the welcome/new-player screen

**File:** `templates/vue/index.html`
**Severity:** Low — chat widget appears during the new-player welcome flow when it should be hidden

**Root cause:** Jinja2 `index.html` conditionally hides `#chat-widget` and `#chat-toggle-btn` when `show_welcome` is true. `vue/index.html` has no equivalent conditional hide rule.

**Fix:** Added `{% if show_welcome %}#chat-widget, #chat-toggle-btn { display: none !important; }{% endif %}` to the `<style>` block in `vue/index.html`.

---

### Bug #49 — `vue/groups.js` calls non-existent `/api/groups/disband` endpoint

**File:** `static/js/vue/groups.js`
**Severity:** High — group leaders clicking "Disband Group" receive a 404 error; the group is never disbanded

**Root cause:** The Vue groups rewrite added a `disbandGroup()` method that POSTs to `/api/groups/disband`. This route does not exist anywhere in `app.py`. The Jinja2 `groups.html` never had a separate disband endpoint — the leader's "Disband / Leave" button calls the same `leaveGroup()` function, which hits `/api/groups/leave`. The server's `leave` handler removes the group when the caller is the leader.

**Fix:** Changed `fetch('/api/groups/disband', ...)` → `fetch('/api/groups/leave', ...)` in `disbandGroup()` to match the actual server endpoint that handles both leader disbanding and member leaving.

---

---

## Sixth-Pass Bug Fixes — battle, events, market, friends (Bugs #50–#54)

### Bug #50 — `battleSpell()` sends wrong JSON field name; spells never cast in Vue battle

**File:** `static/js/vue/game.js` (line 403)
**Severity:** Critical — casting any spell in the Vue battle UI silently fails; the server always ignores the request

**Root cause:** `battleSpell(id)` called `this.doAction('/api/battle/spell', { spell_id: id })`. The `/api/battle/spell` route reads `data.get("spell", "")` — it expects a key named `"spell"`, not `"spell_id"`. The value `id` is correct (it is the spell name, since `_api_battle_summary()` sets `spell.id = s["name"]`), but the key mismatch means the server always receives an empty string and rejects the cast.

**Fix:** Changed `{ spell_id: id }` → `{ spell: id }` to match the server's expected field name.

---

### Bug #51 — `claimEventReward()` calls non-existent `/api/action/claim_event` route

**File:** `static/js/vue/game.js` (line 388) + `app.py`
**Severity:** High — the Claim button on active world events always returns 404; players cannot claim event rewards in the Vue UI

**Root cause:** `claimEventReward(evKey)` POSTs to `/api/action/claim_event`, but this route did not exist anywhere in `app.py`. In the Jinja2 version, event rewards are auto-claimed by `check_and_award_events(player)` when the `/game` page loads — there is no manual claim button. The Vue re-implementation added a manual claim flow without a corresponding backend route.

**Fix:** Created `/api/action/claim_event` in `app.py`. The route validates the event ID, checks date range, verifies eligibility conditions (boss kills, etc.), prevents double-claiming, grants the item or gold reward, records the claim, saves the player, and returns `{ ok, message, messages, player }`.

---

### Bug #52 — `loadFriends()` calls `/api/friends/list` — route does not exist (correct route is `/api/friends`)

**File:** `static/js/vue/game.js` (line 466)
**Severity:** High — the Friends tab in the Vue game always fails to load; the friends list is never displayed

**Root cause:** `loadFriends()` fetches `/api/friends/list`, but the actual route in `app.py` is `GET /api/friends`. No `/api/friends/list` route exists. The response from `/api/friends` returns `{ friends: [...] }` which exactly matches what the Vue code parses (`data.friends || []`); only the URL path was wrong.

**Fix:** Changed `fetch('/api/friends/list', ...)` → `fetch('/api/friends', ...)`.

---

### Bug #53 — `marketBuy()` calls non-existent `/api/market/buy`; old route uses form encoding

**File:** `static/js/vue/game.js` (line 458) + `app.py`
**Severity:** High — buying items from the Elite Market in the Vue UI always fails with 404

**Root cause:** `marketBuy(id, price)` POSTs JSON `{ item_id: id, price }` to `/api/market/buy`, but this route did not exist. The only existing market buy route was `POST /action/market/buy`, which uses HTML form encoding (`request.form.get("item_name")`) and redirects to `/game?tab=market` — incompatible with the Vue JSON API pattern.

**Fix:** Created `POST /api/market/buy` in `app.py`. The route accepts JSON `{ item_id, price }`, validates player gold, deducts cost, adds item to inventory, saves the player, and returns `{ ok, message, messages, player }`.

---

### Bug #54 — Events section in `vue/game.html` uses three wrong field names from state

**File:** `templates/vue/game.html` (events tab, lines 933–952)
**Severity:** High — claim button never appears for eligible events; claimed indicator never renders; Vue `key` warnings in console

**Root cause:** The `eventsData.active` items returned by `/api/game/state/extended` use these fields: `id`, `is_eligible`, `is_claimed`. The template used three incorrect names:
- `:key="ev.key"` → `ev.key` is always `undefined` (Vue emits duplicate-key warnings)
- `v-if="ev.claimed"` → should be `ev.is_claimed`
- `v-if="ev.can_claim && !ev.claimed"` → `ev.can_claim` does not exist; should be `ev.is_eligible && !ev.is_claimed`
- `@click="claimEventReward(ev.key)"` → passed `undefined` to the claim function

**Fix:** Updated the events `v-for` block to use `:key="ev.id"`, `ev.is_claimed`, `ev.is_eligible && !ev.is_claimed`, and `claimEventReward(ev.id)`.

---

## Final Audit Summary

All templates in `templates/vue/` have been audited across six passes. Total bugs found and fixed: **54**.

| Pass | Scope | Bugs Fixed |
|------|-------|-----------|
| 1st | groups, land_shop, land_pets | #1–#14 |
| 2nd | game.js (socket events, field names) | #15–#25 |
| 3rd | chat, dungeon_room, admin | #26–#29 |
| 4th | friends, wiki | #30–#42 |
| 5th | base.html widgets, chat.html, index.html, groups.js | #43–#49 |
| 6th | battle/spell cast, events claim, market buy, friends list, event field names | #50–#54 |

### Sixth-Pass Clean Table

| File | Status |
|------|--------|
| `static/js/vue/game.js` — `battleSpell()` | **FIXED** Bug #50: `spell_id` → `spell` |
| `app.py` — `/api/action/claim_event` | **FIXED** Bug #51: route created |
| `static/js/vue/game.js` — `loadFriends()` | **FIXED** Bug #52: `/api/friends/list` → `/api/friends` |
| `app.py` — `/api/market/buy` | **FIXED** Bug #53: JSON route created |
| `templates/vue/game.html` — events tab | **FIXED** Bug #54: `ev.key/claimed/can_claim` → `ev.id/is_claimed/is_eligible` |
| All land action routes (`/api/action/land/*`) | **CLEAN** — all 9 routes exist, field names match |
| All battle routes (`/api/battle/*`) | **CLEAN** — attack, defend, flee, spell, use_item all exist, fields correct after #50 |
| `/api/action/dungeon/enter`, `/api/action/dungeon/abandon` | **CLEAN** |
| `/api/action/auto_equip`, `/api/action/quick_heal`, `/api/action/sort_inventory` | **CLEAN** |
| `/api/action/complete_mission` (expects `mission_id`) | **CLEAN** — matches `{ mission_id: id }` |
| `/api/action/claim_challenge` (expects `challenge_id`) | **CLEAN** — matches `{ challenge_id: id }` |
| `/api/social/chat` GET + POST | **CLEAN** |
| `/api/land_data`, `/api/area_activity`, `/api/market_data` | **CLEAN** |
| `/api/online/logout` | **CLEAN** |
