"""Queue selected/all archive indexing without performing filesystem effects."""

from django.core.management.base import BaseCommand, CommandError

from apps.archive.indexing import queue_index


class Command(BaseCommand):
    help = "Queue RAW indexing. Run the validated worker separately; never approves files."

    def add_arguments(self, parser):
        parser.add_argument("--folder", default="", help="Canonical RAW-relative folder; omit for the whole archive")

    def handle(self, *args, **options):
        try:
            job = queue_index(options["folder"])
        except ValueError:
            raise CommandError("Invalid or conflicting archive selection.") from None
        self.stdout.write(str(job.pk))
