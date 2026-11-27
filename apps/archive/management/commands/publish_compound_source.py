"""Queue a neutral byte-identical compound CLEAN publication without musical approval."""

from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.archive.publication import queue_compound_copy
from core.files import FileError


class Command(BaseCommand):
    help = "Queue a neutral compound CLEAN copy; this does not confirm any music."

    def add_arguments(self, parser):
        parser.add_argument("version_id", type=UUID, help="Validated immutable source version UUID")
        parser.add_argument("--title", required=True, help="Human-readable source or collection title")

    def handle(self, *args, **options):
        try:
            job = queue_compound_copy(options["version_id"], title=options["title"])
        except (ObjectDoesNotExist, ValidationError):
            raise CommandError("Source version or compound title is not eligible for CLEAN publication.") from None
        except (FileError, OSError):
            raise CommandError("Storage could not be verified for compound CLEAN publication.") from None
        self.stdout.write(str(job.pk))
