# Our Legacy 2

A browser-based medieval fantasy RPG built with Flask + Python and a Node.js API gateway. Play entirely in your browser — no downloads required.

---

## Architecture

```
Client → Node.js gateway (port 5000) → Python backend (port 8000, internal)
```

- **Gateway**: Node.js (Express 4, Socket.IO 4) — HTTP reverse proxy + WebSocket bridge — port 5000 (public)
- **Backend**: Python 3.12, Flask 3.x, asgiref, uvicorn — all game logic + session — port 8000 (internal)
- **Session**: Flask-Session (filesystem)
- **Database**: Supabase (cloud saves, user accounts, global chat)
- **Frontend**: Jinja2 templates, vanilla JS, custom pixel-art CSS

---

## Description

Our Legacy 2 is a medieval fantasy RPG featuring turn-based combat, dungeon crawling, crafting, housing, companions, pets, spells, and social features. Supports both offline (local save) and online play with cloud saves, global chat, friends, and real-time multiplayer elements.

---

## Setup

**Requirements:** Python 3.12+, Node.js 18+

```bash
pip install -r requirements.txt
npm install
bash start.sh
```

Open `http://localhost:5000` in your browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service-role secret key |
| `SECRET_KEY` | Yes | Flask session secret (any long random string) |
| `SECRET_SALT` | Yes | Salt for save file encryption |
| `RESEND_API` | Optional | Resend API key for email verification |
| `RESEND_EMAIL` | Optional | Sender address for outbound email |

---

## Database

Run [`setup.sql`](setup.sql) in your Supabase SQL Editor to create all required tables.

---

## Project Structure

- `server.js` — Node.js API gateway (HTTP proxy + Socket.IO bridge)
- `start.sh` — Startup script: launches Python backend then Node.js gateway
- `app.py` — Python backend (Flask routes, SocketIO events, all game systems)
- `gunicorn.conf.py` — Gunicorn config (uvicorn worker, binds to 127.0.0.1:8000)
- `utilities/` — Game logic modules (battle, crafting, dungeons, spells, market, save/load, supabase_db, etc.)
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, fonts, JS assets
- `data/` — JSON game data files (items, classes, enemies, dungeons, spells, etc.)

---

*All game data is moddable via the JSON files in `data/`.*
