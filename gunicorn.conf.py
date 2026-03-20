worker_class = "gevent"
workers = 1


def post_fork(server, worker):
    from gevent import monkey
    monkey.patch_all()
