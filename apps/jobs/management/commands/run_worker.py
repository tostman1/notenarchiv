"""Run one durable worker with a global OS lock and database lease."""

import math
import os
import signal
import threading
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.jobs.services.queue import StaleAttempt
from apps.jobs.services.worker import WorkerUnavailable, run_worker
from config.env import env


class Command(BaseCommand):
    help = "Run the durable single-job worker (set NOTENARCHIV_SERVICE=worker)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Inspect the queue once, then stop.")
        parser.add_argument("--poll-seconds", type=float, default=1)

    def handle(self, *args, **options):
        if env.service != "worker":
            raise CommandError("run_worker requires NOTENARCHIV_SERVICE=worker")
        interval = options["poll_seconds"]
        if not math.isfinite(interval) or not 0.1 <= interval <= 10:
            raise CommandError("poll-seconds must be between 0.1 and 10")
        database = settings.DATABASES["default"]["NAME"]
        if not database or str(database) == ":memory:" or str(database).startswith("file:"):
            raise CommandError("Worker requires a local file-backed SQLite database")
        if env.profile == "nas":
            from apps.jobs.services.storage import StorageError, validate_storage
            from config.container import ensure_database_ready

            try:
                if os.name != "posix" or os.geteuid() == 0 or os.getegid() == 0:
                    raise RuntimeError("A non-root service identity is required")
                validate_storage(env, "worker")
                ensure_database_ready(env)
            except (StorageError, OSError, RuntimeError):
                raise CommandError("Worker startup validation failed; check storage and migrations") from None
        shutdown = threading.Event()
        previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
        try:
            for number in previous:
                signal.signal(number, lambda *_: shutdown.set())
            run_worker(
                Path(database).resolve().parent / "worker.lock",
                once=options["once"],
                poll_seconds=interval,
                shutdown=shutdown,
            )
        except (WorkerUnavailable, StaleAttempt, DatabaseError):
            raise CommandError("Worker stopped safely; check worker ownership and unfinished jobs") from None
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
