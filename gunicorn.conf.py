# gunicorn.conf.py
#
# Do NOT call monkey.patch_all() here (master process).
# The gevent worker class patches each worker automatically in its own process.
# Patching in the master causes gunicorn's internal Timer threads to become
# greenlets; when those timers finish they try to remove themselves from
# threading._active but gevent has already cleaned them up, producing:
#   KeyError: <ident>  in threading._delete
# Removing the master-level patch eliminates that error entirely.

worker_class = "gevent"
workers = 1


def post_fork(server, worker):
    import app as _app
    if not _app._bg_started:
        _app._bg_started = True
        _app.socketio.start_background_task(_app._world_tick)
