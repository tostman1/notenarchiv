"""Fail closed before executing an explicitly supported container operation."""

import json
import os
import subprocess
import sys


def main():
    os.umask(0o077)
    command = sys.argv[1:] or ["web"]
    try:
        if os.geteuid() == 0 or os.getegid() == 0:
            raise RuntimeError("A non-root service identity is required")
        if command == ["gateway"]:
            from pathlib import Path

            from core.mounts import parse_mountinfo
            from scripts.gateway import main as gateway_main

            if not parse_mountinfo(Path("/proc/self/mountinfo").read_text())[Path("/")].readonly:
                raise RuntimeError("The gateway root filesystem must be read-only")
            return gateway_main()
        from config.env import env

        if env.profile != "nas" or env.bind != "127.0.0.1" or env.print_enabled:
            raise RuntimeError("Preview requires the NAS profile, loopback binding and disabled printing")
        if "*" in env.allowed_hosts or "127.0.0.1" not in env.allowed_hosts or len(env.secret_key) < 50:
            raise RuntimeError("Explicit hosts, loopback health and a strong secret are required")
        if not env.csrf_trusted_origins or any(
            not origin.startswith("https://") for origin in env.csrf_trusted_origins
        ):
            raise RuntimeError("A private HTTPS proxy origin is required")
        from apps.jobs.services.storage import validate_storage
        from core.locking import ProcessLock

        validate_storage(env, "web")
    except Exception:
        sys.stderr.write(
            json.dumps({"event": "startup_rejected", "error": "Invalid identity, storage or configuration"}) + "\n"
        )
        return 1
    if command == ["web"]:
        os.execvp("gunicorn", ["gunicorn", "--config", "config/gunicorn.conf.py", "config.wsgi:application"])
    if command not in (["migrate"], ["provision"], ["provision", "--set-password"], ["check"]):
        sys.stderr.write("Unsupported container operation\n")
        return 1
    if command == ["check"]:
        return 0
    if command[0] == "provision" and not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.stderr.write("Provisioning requires an interactive terminal; no password arguments are accepted\n")
        return 1
    operation = ["migrate", "--noinput"] if command[0] == "migrate" else ["create_archivist", *command[1:]]
    try:
        with ProcessLock(env.database_path.parent / ".maintenance.lock"):
            return subprocess.call([sys.executable, "manage.py", *operation])
    except OSError:
        sys.stderr.write("Stop the web service before maintenance and verify DATA permissions\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
