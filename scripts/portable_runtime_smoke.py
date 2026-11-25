"""Synthetic shared-runtime proof; not a desktop launcher or production server.

Run this script in a fresh interpreter. It accepts no installation/data paths,
uses an owned temporary workspace and ignores inherited application settings.
WSGI reference serving is used only for this bounded local test.
"""

import contextlib
import io
import json
import logging
import os
import sqlite3
import sys
import tempfile
import threading
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

REPOSITORY = Path(__file__).resolve().parents[1]
SYSTEM_ENVIRONMENT = {
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LD_LIBRARY_PATH",
}


class ProofError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise ProofError(code)


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *_):
        pass


class BoundedServer(WSGIServer):
    timeout = 0.1

    def get_request(self):
        connection, peer = super().get_request()
        connection.settimeout(5)
        return connection, peer


def prove(root):
    # All Django imports occur after fresh, synthetic configuration is installed.
    inherited = {key: value for key, value in os.environ.items() if key.upper() in SYSTEM_ENVIRONMENT}
    os.environ.clear()
    os.environ.update(inherited)
    os.environ.update(
        NOTENARCHIV_PROFILE="local",
        NOTENARCHIV_LOCAL_ROOT=str(root),
        DJANGO_SETTINGS_MODULE="config.settings",
        DEBUG_MODE="FALSE",
    )
    sys.path.insert(0, str(REPOSITORY))
    sys.dont_write_bytecode = True
    from config import runtime

    runtime.management_command = "portable_runtime_smoke"
    import django

    django.setup()
    # No request bodies, fixture credentials, paths or ORM contents enter output.
    logging.disable(logging.CRITICAL)
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from django.db import connections

    from apps.jobs.models import WorkerLease
    from apps.jobs.services.worker import run_worker
    from config.env import env
    from core.locking import ProcessLock

    require(not settings.DEBUG and env.bind == "127.0.0.1", "SECURITY_CONFIGURATION")
    require(env.database_path.parent == root and not env.print_enabled, "SYNTHETIC_CONFIGURATION")
    with contextlib.redirect_stdout(io.StringIO()):
        call_command("migrate", interactive=False, verbosity=0)
    get_user_model().objects.create_user("synthetic-runtime", password="Synthetic-runtime-135")
    errors = []
    shutdown = threading.Event()

    def work():
        try:
            run_worker(root / "worker.lock", poll_seconds=0.1, shutdown=shutdown)
        except BaseException:
            errors.append("WORKER_FAILED")
        finally:
            connections.close_all()

    with ProcessLock(root / "application.lock"):
        try:
            with ProcessLock(root / "application.lock"):
                raise ProofError("DUPLICATE_INSTANCE_ACCEPTED")
        except OSError:
            pass
        with make_server(
            "127.0.0.1", 0, get_wsgi_application(), server_class=BoundedServer, handler_class=QuietHandler
        ) as server:

            def serve():
                try:
                    while not shutdown.is_set():
                        server.handle_request()
                finally:
                    connections.close_all()

            worker = threading.Thread(target=work, daemon=True)
            web = threading.Thread(target=serve, daemon=True)
            worker.start()
            web.start()
            try:
                check_http(f"http://127.0.0.1:{server.server_port}")
            finally:
                shutdown.set()
                web.join(timeout=10)
                worker.join(timeout=15)
            require(not web.is_alive() and not worker.is_alive() and not errors, "SHUTDOWN_FAILED")
        lease = WorkerLease.objects.get(pk=1)
        require(lease.owner is None and lease.generation > 0, "WORKER_LEASE_NOT_RELEASED")
    with ProcessLock(root / "application.lock"), ProcessLock(root / "worker.lock"):
        pass
    connections.close_all()
    check_restore(env.database_path, root / "restored.sqlite3")


def check_http(origin):
    cookies = CookieJar()
    opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(cookies))
    with opener.open(origin + "/healthz", timeout=5) as response:
        require(response.status == 200, "LIVENESS_FAILED")
    with opener.open(origin + "/", timeout=5) as response:
        require(response.geturl().startswith(origin + "/login/"), "AUTHENTICATION_REQUIRED")
        require(response.headers["X-Frame-Options"] == "DENY", "SECURITY_HEADERS")
    try:
        with opener.open(Request(origin + "/login/", data=b"username=synthetic&password=invalid"), timeout=5):
            raise ProofError("CSRF_NOT_ENFORCED")
    except HTTPError as error:
        error.close()
        require(error.code == 403, "CSRF_NOT_ENFORCED")
    token = next(cookie.value for cookie in cookies if cookie.name == "notenarchiv_csrftoken")
    payload = urlencode(
        {
            "username": "synthetic-runtime",
            "password": "Synthetic-runtime-135",
            "csrfmiddlewaretoken": token,
        }
    ).encode()
    with opener.open(Request(origin + "/login/", data=payload), timeout=5) as response:
        require(response.status == 200 and response.geturl() == origin + "/", "LOGIN_FAILED")


def check_restore(source_path, restored_path):
    with (
        contextlib.closing(sqlite3.connect(source_path)) as source,
        contextlib.closing(sqlite3.connect(restored_path)) as restored,
    ):
        source.backup(restored)
        require(restored.execute("PRAGMA integrity_check").fetchone() == ("ok",), "RESTORE_INTEGRITY")
        require(not restored.execute("PRAGMA foreign_key_check").fetchall(), "RESTORE_FOREIGN_KEYS")
        for query in (
            "SELECT COUNT(*) FROM django_migrations",
            "SELECT username, password FROM auth_user ORDER BY id",
            "SELECT owner, generation FROM jobs_workerlease",
        ):
            require(source.execute(query).fetchall() == restored.execute(query).fetchall(), "RESTORE_MISMATCH")


def main():
    try:
        with tempfile.TemporaryDirectory(prefix="notenarchiv-runtime-proof-") as temporary:
            try:
                prove(Path(temporary).absolute())
            finally:
                if "django.db" in sys.modules:
                    sys.modules["django.db"].connections.close_all()
    except Exception as error:
        code = str(error) if isinstance(error, ProofError) else "RUNTIME_PROOF_FAILED"
        emit({"result": "failed", "error": code})
        return 1
    emit(
        {
            "result": "success",
            "scope": "synthetic shared runtime",
            "checks": [
                "initialization",
                "single_instance",
                "loopback",
                "auth_csrf",
                "worker_shutdown",
                "sqlite_restore",
            ],
            "native_archive_storage": "not exercised",
            "packaged_desktop": "not exercised",
        }
    )
    return 0


def emit(result):
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
