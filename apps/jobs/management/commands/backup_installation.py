"""Explicit local-only consistent backup; no destination is inferred."""

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.jobs.services.backup import create
from core.backup import BackupError, Limits
from core.files import FileError


class Command(BaseCommand):
    help = "Back up stopped application state into a new private directory."

    def add_arguments(self, parser):
        parser.add_argument("destination", type=Path)
        parser.add_argument("--config-dir", type=Path, required=True)
        parser.add_argument("--raw-backup", type=Path, required=True)
        parser.add_argument("--image", required=True)
        parser.add_argument("--include-exports", action="store_true")
        parser.add_argument("--max-bytes", type=int, default=Limits().bytes)
        parser.add_argument("--timeout", type=int, default=Limits().seconds)

    def handle(self, *args, **options):
        try:
            seal = create(
                settings.env,
                options["destination"],
                config_dir=options["config_dir"],
                raw_backup=options["raw_backup"],
                image=options["image"],
                include_exports=options["include_exports"],
                limits=Limits(bytes=options["max_bytes"], seconds=options["timeout"]),
            )
        except (BackupError, FileError, OSError, ValueError, TypeError, sqlite3.Error) as error:
            code = str(error) if isinstance(error, (BackupError, FileError)) else "BACKUP_REJECTED"
            raise CommandError(code) from None
        self.stdout.write("Backup verified; private manifest SHA-256: " + seal)
