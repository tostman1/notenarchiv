"""Loopback-only foreground development server and authenticated lifecycle control."""
# ruff: noqa: T201

import argparse
import json
import os
import secrets
import socket
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATE = ROOT / ".dev" / "launcher.json"
LOCAL_ROOT = ROOT / ".dev" / "launcher"


def control(action):
    if not STATE.exists():
        print("No managed development server is running.")
        return False
    try:
        state = json.loads(STATE.read_text())
        request = urllib.request.Request(
            f"http://127.0.0.1:{state['control']}/{action}", headers={"Authorization": state["token"]}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            if response.read(128) != state["identity"].encode():
                raise ValueError("Unrelated control endpoint")
        print("Managed development server " + ("stopping." if action == "stop" else "running."))
        return True
    except (OSError, ValueError, KeyError):
        print("No verified managed server is running (stale state or unavailable control).")
        return False


def confirmed(line, answer):
    return line.strip().lower() == "kill" and answer.strip().lower() == "yes"


def start(port, auto_login=True, open_browser=True):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Development port must be between 1 and 65535")
    # Detect conflicts before migrations/provisioning; never stop the listener.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    from core.locking import ProcessLock

    STATE.parent.mkdir(exist_ok=True)
    with ProcessLock(STATE.parent / "launcher.lock"):
        _start(port, auto_login, open_browser)


def _start(port, auto_login=True, open_browser=True):
    if control("status"):
        raise RuntimeError("Already running; use dev stop first.")
    os.chdir(ROOT)
    # A fixed isolated synthetic profile prevents account provisioning into another DB.
    for key in (
        "DATABASE_PATH",
        "DJANGO_SECRET_KEY_FILE",
        "APP_ALLOWED_HOSTS",
        "APP_CSRF_TRUSTED_ORIGINS",
        "SOURCE_DIR",
        "CURATED_DIR",
        "PROCESSED_DIR",
        "STATUS_DIR",
        "EXPORT_DIR",
        "LOG_DIR",
        "NOTENARCHIV_SERVICE",
        "APP_PORT",
    ):
        os.environ.pop(key, None)
    os.environ.update(
        NOTENARCHIV_PROFILE="local",
        NOTENARCHIV_LOCAL_ROOT=str(LOCAL_ROOT),
        APP_BIND="127.0.0.1",
        DEBUG_MODE="FALSE",
        DJANGO_SETTINGS_MODULE="config.settings",
    )
    token = secrets.token_urlsafe(32)
    os.environ["DEV_LOGIN_TOKEN"] = token if auto_login else ""
    import django

    django.setup()
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application

    call_command("migrate", interactive=False, verbosity=0)
    call_command("collectstatic", interactive=False, verbosity=0)

    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass  # Structured Django diagnostics retain failures, never raw query strings.

    server = make_server("127.0.0.1", port, get_wsgi_application(), server_class=Server, handler_class=Quiet)
    stopped = threading.Event()
    identity = secrets.token_hex(16)

    class Control(BaseHTTPRequestHandler):
        def handle(self):
            self.connection.settimeout(3)
            super().handle()

        def do_POST(self):
            self.connection.settimeout(3)
            if not secrets.compare_digest(self.headers.get("Authorization", ""), token) or self.path not in {
                "/status",
                "/stop",
            }:
                self.send_error(403)
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(identity.encode())
            if self.path == "/stop":
                stopped.set()

        def log_message(self, *args):
            pass

    manager = HTTPServer(("127.0.0.1", 0), Control)
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(
        json.dumps(
            {"control": manager.server_port, "token": token, "identity": identity, "pid": os.getpid(), "port": port}
        ),
        encoding="utf-8",
    )
    os.chmod(STATE, 0o600)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=manager.serve_forever, daemon=True).start()

    def console():
        while not stopped.is_set():
            try:
                line = input()
                if line.strip().lower() == "kill":
                    answer = input("Stop the development server? (yes/no) ")
                    if confirmed(line, answer):
                        stopped.set()
            except EOFError:
                return

    threading.Thread(target=console, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print(f"Development server: {url} (no autoreload; use dev restart after source changes)")
    try:
        if open_browser:
            webbrowser.open(url + ("dev-login/?token=" + token if auto_login else ""))
        while not stopped.wait(0.2):
            pass  # Periodic wake allows Windows Ctrl+C delivery during Event.wait.
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        manager.shutdown()
        server.server_close()
        manager.server_close()
        try:
            if STATE.exists() and json.loads(STATE.read_text()).get("identity") == identity:
                STATE.unlink()
        except (OSError, ValueError):
            pass  # Never delete replaced/malformed state belonging to another launcher.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "restart", "status"])
    parser.add_argument("--port", type=int, default=8085)
    parser.add_argument("--manual-auth", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        dispatch(args)
    except (OSError, RuntimeError, ValueError) as exc:
        # No raw configuration/secret errors; ordinary port and state failures are clear.
        print("Development command failed: port conflict, running launcher or invalid local configuration.")
        raise SystemExit(1) from exc


def dispatch(args):
    if args.action in {"stop", "status"}:
        control(args.action)
    else:
        if args.action == "restart" and control("stop"):
            # Bounded acknowledgement wait, not PID/port-based process termination.
            import time

            for _ in range(50):
                if not STATE.exists():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Previous server did not finish shutdown")
        start(args.port, not args.manual_auth, not args.no_browser)


if __name__ == "__main__":
    main()
