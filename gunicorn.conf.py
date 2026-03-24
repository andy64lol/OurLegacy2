# gunicorn.conf.py

# Patch the master process with gevent so the app module can be imported in
# post_fork (workers inherit the patched stdlib via fork).
from gevent import monkey
monkey.patch_all()

worker_class = "gevent"
workers = 1

# Disable the gunicorn control-socket server.  In newer gunicorn versions the
# control server tries to use asyncio inside a gevent worker where no asyncio
# event loop exists, which produces:
#   [ERROR] Control server error: no running event loop
# followed by a threading KeyError when the Timer it creates is cleaned up.
# The control socket is only needed for live-reload / signal forwarding via
# `gunicorn --reload`, which we don't use.  Disabling it silences both errors
# with no loss of functionality.
control_socket_disable = True


def post_fork(server, worker):
    import app as _app
    if not _app._bg_started:
        _app._bg_started = True
        _app.socketio.start_background_task(_app._world_tick)
