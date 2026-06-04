import os
import subprocess
import sys

print("Starting...")

# Auto-install any missing dependencies before launching
_missing = []
for _pkg in ["flask", "flask_socketio", "gunicorn", "uvicorn", "supabase"]:
    try:
        __import__(_pkg)
    except ImportError:
        _missing.append(_pkg)

if _missing:
    print(f"Missing packages detected ({', '.join(_missing)}) — installing from requirements.txt...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("Dependencies installed.")
    except Exception as e:
        print(f"Warning: auto-install failed: {e}")

os.system("gunicorn -c gunicorn.conf.py app:asgi_app")
