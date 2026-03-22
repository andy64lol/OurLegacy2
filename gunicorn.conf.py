# gunicorn.conf.py

# Patch everything first, at the very top
from gevent import monkey

monkey.patch_all()

worker_class = "gevent"
workers = 1


# You can keep post_fork if needed, but don't patch here
def post_fork(server, worker):
    pass
