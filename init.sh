#!/bin/bash
set -e

echo "=== Our Legacy 2 — Server Initialization ==="

ask_credential() {
    local var_name="$1"
    local description="$2"
    local is_secret="${3:-false}"
    local is_optional="${4:-false}"

    if [ -n "${!var_name}" ]; then
        echo "      $var_name: already set, skipping."
        return
    fi

    if [ "$is_optional" = "true" ]; then
        local prompt_text="      $description (optional — press Enter to skip): "
    else
        local prompt_text="      $description: "
    fi

    if [ "$is_secret" = "true" ]; then
        read -rsp "$prompt_text" value
        echo
    else
        read -rp "$prompt_text" value
    fi

    if [ -n "$value" ]; then
        export "$var_name"="$value"
    fi
}

echo ""
echo "[0/3] Credential setup"
echo "      (Press Enter to skip optional items or those already set as env vars)"
echo ""
ask_credential "SECRET_KEY"          "Flask secret key — signs session cookies (required)"              true  false
ask_credential "SECRET_SALT"         "Save encryption salt — secures cloud saves (recommended)"         true  true
ask_credential "SUPABASE_URL"        "Supabase project URL, e.g. https://xyz.supabase.co (optional)"    false true
ask_credential "SUPABASE_SERVICE_KEY" "Supabase service/anon key (optional)"                            true  true
ask_credential "SUPABASE_DB_URL"     "Supabase PostgreSQL connection string — for schema setup (optional)" true true
ask_credential "RESEND_API"          "Resend API key — enables email features (optional)"               true  true
ask_credential "RESEND_EMAIL"        "Resend sender address, e.g. noreply@yourdomain.com (optional)"    false true
echo ""
echo "      Credentials configured."

echo "[1/3] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "      Done."

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

PORT="${PORT:-5000}"
WORKERS="${WEB_CONCURRENCY:-1}"
echo "[3/3] Starting Gunicorn on port ${PORT} with ${WORKERS} worker(s)..."
exec gunicorn app:app \
    --bind "0.0.0.0:${PORT}" \
    --worker-class gevent \
    --workers "${WORKERS}" \
    --timeout 120 \
    --log-level info
