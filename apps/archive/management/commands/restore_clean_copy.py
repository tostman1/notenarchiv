"""Queue reconstruction of one missing acknowledged CLEAN publication."""

from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.archive.recovery import queue_restore
from core.files import FileError


class Command(BaseCommand):
    help = "Queue exact-byte restoration of a missing CLEAN copy at its acknowledged path."

    def add_arguments(self, parser):
        parser.add_argument("file_id", type=UUID, help="Archive file UUID with an acknowledged CLEAN publication")

    def handle(self, *args, **options):
        try:
            job = queue_restore(options["file_id"])
        except (ObjectDoesNotExist, ValidationError):
            raise CommandError("Archive file does not have an eligible CLEAN publication to restore.") from None
        except (FileError, OSError):
            raise CommandError("CLEAN storage could not be verified for restoration.") from None
        self.stdout.write(str(job.pk))
