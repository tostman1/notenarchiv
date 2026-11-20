"""Check worker heartbeat freshness independently of the current job."""

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.jobs.services.queue import worker_is_healthy


class Command(BaseCommand):
    help = "Fail when the worker heartbeat or global lease is not fresh."

    def handle(self, *args, **options):
        try:
            healthy = worker_is_healthy()
        except DatabaseError:
            healthy = False
        if not healthy:
            raise CommandError("Worker heartbeat is unavailable or stale")
        self.stdout.write("Worker heartbeat is fresh")
