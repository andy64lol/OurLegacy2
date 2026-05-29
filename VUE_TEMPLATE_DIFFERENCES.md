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

**No functional bugs found.** Differences:
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

**No functional bugs found.** Differences:
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

**No functional bugs found.** Differences are cosmetic:
- Vue adds a search bar that filters entries client-side
- Jinja2 links to individual wiki entry pages; Vue renders expanded content inline via `v-show`

---

### `create.html` / `vue/create.html`

**No functional bugs found.** The Vue version uses the same `/api/create_character` endpoint as `index.js`. Differences are cosmetic (styling, class selection UI).

---

### `admin.html` / `vue/admin.html`

**No functional bugs found.** Both versions use the same admin action endpoints. Vue adds reactive search/filter on the player list.

---

### `reset_password.html` / `vue/reset_password.html`

**No functional bugs found.** Both use the same `/api/reset_password` flow.

---

## Routes Serving Vue Templates

At the time of this audit, **no routes in `app.py` serve the Vue templates** — all `render_template(...)` calls reference the original Jinja2 templates. The Vue templates exist in `templates/vue/` as prepared replacements but are not yet wired up to any route.

To enable a Vue page, the corresponding route needs to render `vue/<template_name>.html` instead of `<template_name>.html`.
