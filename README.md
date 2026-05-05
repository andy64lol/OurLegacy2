# Our Legacy 2

A browser-based medieval fantasy RPG built with Python and Flask. Play entirely in your browser — no downloads required.

---

## Description

Our Legacy 2 is a medieval fantasy RPG featuring turn-based combat, dungeon crawling, crafting, housing, companions, pets, spells, and social features. Supports both offline (local save) and online play with cloud saves, global chat, friends, and real-time multiplayer elements.

---

## Setup

**Requirements:** Python 3.11+

```bash
pip install -r requirements.txt
bash init.sh
```

Open `http://localhost:5000` in your browser.

---

## Builds

### Development

```bash
python app.py
```

Starts the Flask development server on port 5000 with debug output.

### Production

```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port app:app
```

Runs the app via Gunicorn (WSGI). For ASGI/SocketIO support, Uvicorn is also available:

```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 5000
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service-role secret key |
| `SECRET_KEY` | Yes | Flask session secret (any long random string) |
| `SUPABASE_DB_URL` | Optional | PostgreSQL URL — enables auto-migration in `init.sh` |
| `RESEND_API` | Optional | Resend API key for email verification |
| `RESEND_EMAIL` | Optional | Sender address for outbound email |

---

## Database

Run [`setup.sql`](setup.sql) in your Supabase SQL Editor, or let `init.sh` apply it automatically when `SUPABASE_DB_URL` is set.

---

*All game data is moddable via the JSON files in `data/`.*
