"""One web writer, bounded threads, private reverse-proxy backend only."""

from config.container import ensure_database_ready
from config.env import env
from core.locking import ProcessLock

bind = "0.0.0.0:8000"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 60
graceful_timeout = 30
worker_tmp_dir = "/tmp"
preload_app = False
reload = False
max_requests = 0  # No overlapping automatic reload of the single Debug file writer.
umask = 0o077
accesslog = None
errorlog = "-"
loglevel = "debug" if env.debug_mode else "info"
logger_class = "config.gunicorn_logging.StructuredLogger"
# The Compose port is loopback-only on a dedicated network. DSM overwrites this header.
forwarded_allow_ips = "*"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190


def on_starting(server):
    server.maintenance_lock = ProcessLock(env.database_path.parent / ".maintenance.lock")
    server.maintenance_lock.__enter__()
    ensure_database_ready(env)


def on_exit(server):
    lock = getattr(server, "maintenance_lock", None)
    if lock is not None:
        lock.__exit__()
