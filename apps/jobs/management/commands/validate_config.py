"""Startup validation mode (WP-02).

``python manage.py validate_config`` checks the deployment configuration
before a service starts. It re-validates the environment contract (config
was already parsed at settings import) and reports service-relevant
writability:

- ``--service web``: only the data directory (DB location) must be writable.
- ``--service worker``: the managed roots (CLEAN, PROCESSED, STATUS, EXPORT)
  and the data directory must be writable.

Writability is probed with a temporary file that is removed again; no
existing file is ever modified. The RAW source root is intentionally never
write-probed (GR-01). Mount topology and service-aware negative checks
belong to WP-09.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Validate deployment configuration (profile, secrets, roots, writability)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--service", choices=["web", "worker"], help="Check service-specific writable roots.")

    def handle(self, *args, **options) -> None:
        from config.env import env

        if env.profile == "nas":
            from apps.jobs.services.storage import StorageError, validate_storage

            try:
                validate_storage(env, options["service"] or env.service)
            except (StorageError, OSError):
                raise CommandError(
                    "NAS storage validation failed; check mount topology and service permissions"
                ) from None
            self.stdout.write("profile: nas")
            self.stdout.write(f"DEBUG_MODE: {'TRUE' if env.debug_mode else 'FALSE'} (Django DEBUG is always False)")
            self.stdout.write("configuration OK")
            return

        self.stdout.write(f"profile: {env.profile}")
        self.stdout.write(f"DEBUG_MODE: {'TRUE' if env.debug_mode else 'FALSE'} (Django DEBUG is always False)")
        self.stdout.write(f"allowed hosts: {', '.join(env.allowed_hosts)}")
        self.stdout.write(f"database: {env.database_path}")

        checks: list[tuple[str, Path, bool]] = [("DATA (database dir)", env.database_path.parent, True)]
        if options["service"] == "worker":
            checks.extend(
                [
                    ("CURATED (CLEAN)", env.curated_dir, True),
                    ("PROCESSED", env.processed_dir, True),
                    ("STATUS", env.status_dir, True),
                    ("EXPORT", env.export_dir, True),
                ]
            )
        else:
            self.stdout.write(f"SOURCE (RAW, read-only by design): {env.source_dir}")

        failures: list[str] = []
        for label, path, must_exist in checks:
            status = self._check_path(label, path, must_exist)
            if status == "error":
                failures.append(label)

        if failures:
            raise CommandError("configuration validation failed for: " + ", ".join(failures))
        self.stdout.write(self.style.SUCCESS("configuration OK"))

    def _check_path(self, label: str, path: Path, must_exist: bool) -> str:
        if not path.exists():
            if must_exist:
                self.stderr.write(self.style.ERROR(f"{label} missing: {path}"))
                return "error"
            self.stdout.write(f"{label} not present: {path} (created on first use)")
            return "ok"
        if not path.is_dir():
            self.stderr.write(self.style.ERROR(f"{label} is not a directory: {path}"))
            return "error"
        fd, name = tempfile.mkstemp(prefix=".notenarchiv-probe-", dir=str(path))
        os.close(fd)  # must release before reopening for the write probe (Windows)
        probe = Path(name)
        try:
            probe.write_bytes(b"ok")
            probe.unlink()
        except OSError as exc:
            probe.unlink(missing_ok=True)
            self.stderr.write(self.style.ERROR(f"{label} not writable: {path} ({exc.strerror or exc})"))
            return "error"
        self.stdout.write(f"{label} writable: {path}")
        return "ok"
