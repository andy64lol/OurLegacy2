#!/bin/bash

# gevent_timer_fix.sh
# Usage: ./gevent_timer_fix.sh myscript.py

PYFILE="$1"

if [ -z "$PYFILE" ]; then
  echo "Usage: $0 <python_script.py>"
  exit 1
fi

# 1. Install gevent if not installed
if ! python3 -c "import gevent" &> /dev/null; then
  echo "[*] Installing gevent..."
  pip install gevent
fi

# 2. Backup original file
cp "$PYFILE" "${PYFILE}.bak"
echo "[*] Backup created at ${PYFILE}.bak"

# 3. Insert monkey-patch at top
if ! grep -q "gevent.monkey.patch_all()" "$PYFILE"; then
  echo "[*] Adding gevent monkey-patch..."
  sed -i '1i\
from gevent import monkey; monkey.patch_all()\n' "$PYFILE"
fi

# 4. Replace threading.Timer with gevent.spawn_later
echo "[*] Replacing threading.Timer with gevent.spawn_later..."
sed -i -E 's/threading\.Timer\(([^,]+), *([^)]+)\)/gevent.spawn_later(\1, \2)/g' "$PYFILE"

echo "[*] Done! Your script is now gevent-compatible."