# TODO: Convert Game to Flask + Jinja2 SPA

## Goal
Create a modern single-page application (SPA) experience using Flask for the backend and Jinja2 for server-rendered templates, while preserving the existing game logic and assets.

## High-level tasks

1. Flask app structure ✅
   - Admin routes moved out of `app.py` into `routes/admin.py` as a Flask Blueprint.
   - Blueprint registered in `app.py` via `app.register_blueprint(admin_bp)`.
   - `templates/` and `static/` already organised; `routes/` package added.

2. SPA shell and routing ✅
   - `base.html` is the SPA shell — single page load, tab-based navigation.
   - `switchTab()` in `game.js` handles all in-page view transitions without reloads.

3. API endpoints ✅
   - Full `/api/action/*` JSON routes (explore, rest, travel, mine, buy, sell, equip, use_item…).
   - Full `/api/battle/*` JSON routes (attack, defend, flee, spell, use_item).
   - `/api/game/state` returns complete player snapshot + area + messages.
   - `/api/player/*`, `/api/social/*`, `/api/world/*`, `/api/catalog/*` — all JSON.
   - `spa_action_response()` on legacy `/action/*` routes: returns JSON for AJAX, redirect for plain forms.

4. Game UI integration ✅
   - `static/js/spa.js` — dedicated SPA module (form interceptor + live polling).
   - `static/js/game.js` — core game UI (tabs, toasts, music, battle keys, themes…).
   - AJAX intercepts `/action/*` forms; on success updates bars, gold, and ATK/DEF/SPD without reload.

5. Jinja2 template enhancements ✅
   - `base.html` is the server-rendered shell with authenticated layout.
   - Initial player state / messages injected as `window._gameMessages` JSON for SPA bootstrap.

6. Assets and static files ✅
   - `static/css/`, `static/js/`, `static/fonts/` served by Flask.
   - `game.js` + `spa.js` loaded in `base.html`; cache-busting via query strings where needed.

7. Testing and validation ✅
   - **Live UI update bug fixed**: `spa.js` polls `/api/game/state` every 5 s and applies the latest
     HP/MP/EXP bars, gold, ATK/DEF/SPD, level, class/rank without any page refresh.
   - Sidebar stat elements now have stable IDs (`sidebar-level-val`, `sidebar-atk-val`, etc.)
     so the poller can target them precisely.
   - Navigation (tabs), game flows (explore, rest, shop, battle), and admin commands all
     reflect live without reload.

8. Extras (from original list)
   - Wiki page added (admin-only, accessible from main menu).
   - Items debug page (`/items`) retained in admin Blueprint.
   - Enemy glyph display — pending (nice-to-have, not yet done).

## Notes
- Keep the existing game logic in `utilities/` and `game_data/` where possible.
- Focus on incremental migration: start with one major screen (e.g. play or dashboard) and expand.
- Maintain compatibility with current Flask/Jinja2 patterns used by the app.
