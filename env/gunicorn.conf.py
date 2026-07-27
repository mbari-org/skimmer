from os import getenv

accesslog = "None"  # no access log
errorlog = "-"  # log errors to stdout
loglevel = "info"

# Use threaded workers so each gunicorn worker process can serve multiple
# concurrent requests while waiting on I/O (upstream image/video fetch,
# disk cache reads) instead of blocking one request at a time.
worker_class = "gthread"
threads = int(getenv("APP_THREADS", 4))
