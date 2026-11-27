"""Read-only, bounded additive-model integrity evidence without private values."""

from django.core.exceptions import ValidationError
from django.db import connections, transaction

from apps.archive import models as m
from apps.archive.content_manifest import manifest_fingerprint


def report(*, using="default", limit=10000):
    """Inspect relational/history integrity, not current musical eligibility or bytes.

    Stale historical confirmations are valid history. No PDF paths, titles, actors,
    hashes or database rows are returned, and no reconciliation is performed.
    """
    if type(limit) is not int or not 1 <= limit <= 100000:
        raise ValidationError("Integrity report limit must be one to 100000.")
    connection = connections[using]
    if connection.vendor != "sqlite":
        raise ValidationError("Content integrity reporting requires SQLite.")
    failures = []
    counts = {}
    with transaction.atomic(using=using):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA quick_check")
            if any(row[0] != "ok" for row in cursor.fetchmany(100)):
                failures.append("SQLITE_INTEGRITY")
            cursor.execute("PRAGMA foreign_key_check")
            if cursor.fetchone() is not None:
                failures.append("FOREIGN_KEY_INTEGRITY")
        for model in (m.SourceDocument, m.SourcePage, m.LogicalPageRevision, m.ContentEditionRevision):
            counts[model._meta.model_name] = model.objects.using(using).count()
        versions = m.SourceVersion.objects.using(using).filter(pdf_state="VALID").order_by("pk")
        for index, version in enumerate(versions.iterator(chunk_size=100)):
            if index >= limit:
                failures.append("VERSION_LIMIT")
                break
            pages = list(version.pages.order_by("page_index").values_list("page_index", flat=True)[:1001])
            if pages != list(range(len(version.page_info))):
                failures.append("SOURCE_PAGE_MAPPING")
                break
        revisions = m.ContentEditionRevision.objects.using(using).order_by("pk")
        for index, revision in enumerate(revisions.iterator(chunk_size=100)):
            if index >= limit:
                failures.append("REVISION_LIMIT")
                break
            try:
                if manifest_fingerprint(revision.manifest) != revision.fingerprint:
                    raise ValidationError("Fingerprint mismatch.")
                references = list(revision.references.order_by("sequence")[:1001])
                if len(references) != len(revision.manifest):
                    raise ValidationError("Reference inventory mismatch.")
                for reference in references:
                    reference.validate_input()
            except (ValidationError, ValueError, TypeError, KeyError, IndexError):
                failures.append("CONTENT_HISTORY_INTEGRITY")
                break
    return {
        "schema": "content-integrity-v1",
        "ok": not failures,
        "counts": counts,
        "failures": failures,
        "scope": "sqlite-and-relational-history-only",
    }
