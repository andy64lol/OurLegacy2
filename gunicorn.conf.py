# gunicorn.conf.py

# Patch everything first, at the very top
from gevent import monkey

monkey.patch_all()

worker_class = "gevent"
workers = 1


def post_fork(server, worker):
    import app as _app
    if not _app._bg_started:
        _app._bg_started = True
        _app.socketio.start_background_task(_app._world_tick)
