"""Verify and restore a complete bundle only into a new isolated directory."""

import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.jobs.services.backup import restore
from core.backup import BackupError, Limits
from core.files import FileError


class Command(BaseCommand):
    help = "Verify and restore a bundle without overwriting live state or RAW."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path)
        parser.add_argument("destination", type=Path)
        parser.add_argument("--manifest-sha256", required=True)
        parser.add_argument("--max-bytes", type=int, default=Limits().bytes)
        parser.add_argument("--timeout", type=int, default=Limits().seconds)

    def handle(self, *args, **options):
        from config.env import env

        try:
            restore(
                env,
                options["source"],
                options["destination"],
                expected_manifest=options["manifest_sha256"],
                limits=Limits(bytes=options["max_bytes"], seconds=options["timeout"]),
            )
        except (BackupError, FileError, OSError, ValueError, TypeError, sqlite3.Error) as error:
            code = str(error) if isinstance(error, (BackupError, FileError)) else "RESTORE_REJECTED"
            raise CommandError(code) from None
        self.stdout.write("Isolated restore verified; live roots unchanged. Reconfigure before starting services.")
