#!/bin/bash
set -e

# Start Python backend (internal, port 8000)
gunicorn -c gunicorn.conf.py app:asgi_app &
PYTHON_PID=$!

# Wait for Python to be ready
echo "[start] Waiting for Python backend on port 8000..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/ping > /dev/null 2>&1; then
    echo "[start] Python backend ready."
    break
  fi
  sleep 1
done

# Start Node.js gateway (public, port 5000)
echo "[start] Starting Node.js gateway on port 5000..."
node server.js &
NODE_PID=$!

# Wait for either process to exit
wait -n $PYTHON_PID $NODE_PID
EXIT_CODE=$?

# Kill the other one on exit
kill $PYTHON_PID $NODE_PID 2>/dev/null || true
exit $EXIT_CODE
