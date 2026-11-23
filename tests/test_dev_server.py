"""Actual launcher lifecycle with synthetic isolated state and no process killing."""

import os
import socket
import subprocess
import sys
import time
import urllib.request

from scripts import dev


def test_live_launcher_confirm_stop_and_stale_state(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    script = f"""
from pathlib import Path
from scripts import dev
dev.STATE=Path({str(tmp_path / "launcher.json")!r})
dev.LOCAL_ROOT=Path({str(tmp_path / "synthetic")!r})
dev.start({port},True,False)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.5) as response:
                    assert response.status == 200
                break
            except OSError:
                if process.poll() is not None:
                    raise AssertionError(process.stderr.read()) from None
                time.sleep(0.1)
        else:
            raise AssertionError("Launcher did not start")
        for asset in ("css/base.css", "favicon.svg", "vendor/htmx/htmx.min.js"):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/static/{asset}", timeout=2) as response:
                assert response.status == 200
        import http.cookiejar
        import json

        state = json.loads((tmp_path / "launcher.json").read_text())
        previous_state = dev.STATE
        try:
            dev.STATE = tmp_path / "launcher.json"
            assert dev.control("status")
            import pytest

            with pytest.raises(OSError):
                dev.start(port, False, False)
        finally:
            dev.STATE = previous_state
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        with opener.open(f"http://127.0.0.1:{port}/dev-login/?token={state['token']}", timeout=3) as response:
            assert response.status == 200
            assert b"synthetic-local-developer" in response.read()
        process.stdin.write("kill\nno\n")
        process.stdin.flush()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
            assert response.status == 200
        process.stdin.write("kill\nyes\n")
        process.stdin.flush()
        output, errors = process.communicate(timeout=15)
        assert process.returncode == 0, errors
        assert "Stop the development server? (yes/no)" in output
        assert not (tmp_path / "launcher.json").exists()
        previous_state = dev.STATE
        try:
            dev.STATE = tmp_path / "launcher.json"
            assert not dev.control("stop")
        finally:
            dev.STATE = previous_state
    finally:
        if process.poll() is None:
            process.kill()  # Exact test-owned process only, not a port/PID-state lookup.
            process.communicate()


def test_stale_state_never_kills_unrelated_process(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    path.write_text('{"control":1,"token":"synthetic","identity":"synthetic","pid":1}')
    monkeypatch.setattr(dev, "STATE", path)
    assert not dev.control("stop")
    assert path.exists()


def test_port_conflict_never_starts_django_or_kills_listener():
    import pytest

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(OSError):
            dev.start(listener.getsockname()[1], False, False)
        assert listener.fileno() >= 0


def test_ctrl_c_cleanup_and_stop_reports_no_server(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    script = f"""
import _thread,threading
from pathlib import Path
from scripts import dev
dev.STATE=Path({str(tmp_path / "state.json")!r})
dev.LOCAL_ROOT=Path({str(tmp_path / "synthetic")!r})
def interrupt():
    import time
    for _ in range(300):
        if dev.STATE.exists():
            time.sleep(.5);_thread.interrupt_main();return
        time.sleep(.1)
threading.Thread(target=interrupt,daemon=True).start()
dev.start({port},False,False)
assert not dev.STATE.exists()
assert not dev.control('stop')
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr
    assert "No managed development server is running" in result.stdout
