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

## Routes Serving Vue Templates

At the time of this audit, **no routes in `app.py` serve the Vue templates** — all `render_template(...)` calls reference the original Jinja2 templates. The Vue templates exist in `templates/vue/` as prepared replacements but are not yet wired up to any route.

To enable a Vue page, the corresponding route needs to render `vue/<template_name>.html` instead of `<template_name>.html`.
