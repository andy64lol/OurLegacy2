# TODO: Our Legacy 2 — tasks & plans

## completed

1. flask app structure ✅
   - admin routes moved to routes/admin.py as a blueprint
   - registered in app.py via register_blueprint(admin_bp)
   - templates/, static/, routes/ all organised

2. spa shell and routing ✅
   - base.html is the spa shell — single page, tab-based nav
   - switchTab() in game.js handles all view transitions without reload

3. api endpoints ✅
   - /api/action/* json routes (explore, rest, travel, mine, buy, sell, equip, use_item…)
   - /api/battle/* json routes (attack, defend, flee, spell, use_item)
   - /api/game/state returns full player snapshot + area + messages
   - /api/player/*, /api/social/*, /api/world/*, /api/catalog/* all json
   - spa_action_response() on legacy /action/* routes

4. game ui integration ✅
   - static/js/spa.js — form interceptor + live polling
   - static/js/game.js — tabs, toasts, music, battle keys, themes
   - ajax intercepts /action/* forms, updates bars/gold/stats without reload

5. jinja2 template enhancements ✅
   - base.html is the server-rendered shell with auth layout
   - initial state injected as window._gameMessages for spa bootstrap

6. assets and static files ✅
   - static/css/, static/js/, static/fonts/ served by flask
   - cache-busting via query strings where needed

7. testing and validation ✅
   - spa.js polls /api/game/state every 5s, updates all bars and stats live
   - sidebar stat elements have stable ids for targeted dom updates

8. extras ✅
   - wiki page (admin-only) with enemies, bosses, items, classes, races, spells, crafting, areas, missions, companions
   - items debug page (/items) in admin blueprint
   - vue 3 beta (/beta) admin-only with real-time polling, visibility api, battle-speed polling

---

## planned: desktop launcher

### goal
native desktop app that wraps the game in a webview and adds extra local systems on top.

### stack options
- **electron** — js/ts, easiest webview integration, large ecosystem
- **tauri** — rust + webview, much smaller binary, better performance
- recommendation: start with **electron** for speed of dev, migrate to tauri later if bundle size matters

### core features

**webview shell**
- embed https://ourlegacy2.onrender.com/ in a full-screen chromium webview
- handle session persistence (cookies passed through)
- custom title bar with game branding, draggable window
- min window size: 1024×768

**auto-updater**
- check github releases on launch, prompt user to update
- silent download + apply on next launch

**local notification system**
- system tray icon with badge for unread events
- native desktop notifications for: level up, battle started, quest complete, friends online
- injected via window.postMessage bridge between webview and electron main process

**game overlay (electron only)**
- transparent overlay window anchored to main window
- shows: current hp/mp, active quests, party status
- data sourced from /api/game/state polled every 5s (same as vue beta)
- toggle with global hotkey (e.g. ctrl+shift+o)

**settings panel**
- launch on startup toggle
- notification preferences
- overlay position (tl/tr/bl/br)
- window opacity
- default zoom level for webview

**music controls** (optional)
- persist music volume/mute state across sessions via local storage
- accessible from system tray menu without opening main window

### extra systems (phase 2)

**offline character cache**
- cache last known player state to localStorage/sqlite
- show character stats in tray tooltip while offline

**macro/keybind manager**
- global hotkeys that trigger game actions (explore, rest, attack) via /api/* calls
- runs in background, works even when window is minimised

**session manager**
- support multiple accounts with quick-switch from tray
- each account gets its own cookie jar / session partition

### file structure (electron)
```
desktop/
  main.js          — electron main process, creates BrowserWindow with webview
  preload.js       — context bridge for overlay ↔ webview communication
  overlay.html     — transparent overlay ui
  tray.js          — system tray icon and menu
  updater.js       — auto-update logic
  settings.js      — persistent settings via electron-store
  package.json     — electron + electron-builder deps
  assets/          — icon files for each platform
```

### build targets
- windows: nsis installer + portable exe
- macos: dmg
- linux: appimage

### next steps
1. scaffold electron project in desktop/ folder
2. implement webview shell with session persistence
3. add system tray + basic notifications
4. implement overlay window with /api/game/state polling
5. wire up auto-updater
6. package and test on all platforms
