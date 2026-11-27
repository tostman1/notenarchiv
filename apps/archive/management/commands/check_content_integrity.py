"""Emit sanitized relational integrity evidence; never repair or approve content."""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.archive.content_integrity import report


class Command(BaseCommand):
    help = "Report additive content history integrity without modifying data or reading PDFs."

    def handle(self, *args, **options):
        result = report()
        self.stdout.write(json.dumps(result, sort_keys=True))
        if not result["ok"]:
            raise CommandError("Content integrity check failed; retain evidence and reconcile manually.")
