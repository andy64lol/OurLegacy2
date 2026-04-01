#!/bin/bash
set -e

echo "=== Our Legacy 2 — Server Initialization ==="

# ── 1. Install Python dependencies ──────────────────────────────
echo "[1/3] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "      Done."

# ── 2. Apply database schema (optional) ─────────────────────────
# Set SUPABASE_DB_URL to your Supabase PostgreSQL connection string
# (found in Supabase Dashboard → Project Settings → Database → Connection string)
# Example: postgres://postgres:<password>@db.<ref>.supabase.co:5432/postgres
echo "[2/3] Database setup..."
if [ -n "$SUPABASE_DB_URL" ]; then
    if command -v psql &>/dev/null; then
        echo "      Applying setup.sql..."
        psql "$SUPABASE_DB_URL" -f setup.sql
        echo "      Schema applied."
    else
        echo "      psql not found. Run setup.sql manually in the Supabase SQL editor."
    fi
else
    echo "      SUPABASE_DB_URL not set. Run setup.sql manually in the Supabase SQL editor."
fi

# ── 3. Start the server ──────────────────────────────────────────
PORT="${PORT:-5000}"
WORKERS="${WEB_CONCURRENCY:-1}"
echo "[3/3] Starting Gunicorn on port ${PORT} with ${WORKERS} worker(s)..."
exec gunicorn app:app \
    --bind "0.0.0.0:${PORT}" \
    --worker-class gevent \
    --workers "${WORKERS}" \
    --timeout 120 \
    --log-level info
