import os
import sys

workers = 1
bind = "0.0.0.0:5000"
timeout = 120

if os.environ.get("RENDER") or "asgi_app" in " ".join(sys.argv):
    worker_class = "uvicorn.workers.UvicornWorker"
else:
    worker_class = "sync"
