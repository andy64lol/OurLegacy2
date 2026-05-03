#!/bin/bash

PYFILE="$1"

if [ -z "$PYFILE" ]; then
  echo "Usage: $0 <python_script.py>"
  exit 1
fi

if ! python3 -c "import gevent" &> /dev/null; then
  echo "[*] Installing gevent..."
  pip install gevent
fi

cp "$PYFILE" "${PYFILE}.bak"
echo "[*] Backup created at ${PYFILE}.bak"

if ! grep -q "gevent.monkey.patch_all()" "$PYFILE"; then
  echo "[*] Adding gevent monkey-patch..."
  sed -i '1i\
from gevent import monkey; monkey.patch_all()\n' "$PYFILE"
fi

echo "[*] Replacing threading.Timer with gevent.spawn_later..."
sed -i -E 's/threading\.Timer\(([^,]+), *([^)]+)\)/gevent.spawn_later(\1, \2)/g' "$PYFILE"

echo "[*] Done! Your script is now gevent-compatible."