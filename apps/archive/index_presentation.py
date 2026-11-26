"""Read-only business status, independent of review/completeness and text markers."""

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.archive import models as m
from apps.archive.status import _content, _path
from core import preview

STATES = {
    "NEW": _("Neu"),
    "INDEXING": _("Wird indiziert"),
    "INDEXED": _("Inventar verarbeitet"),
    "PARTIAL_FAILURE": _("Teilweise fehlgeschlagen"),
}
ERRORS = {
    "INVENTORY_FAILED": _("Ordnerinventar nicht lesbar; keine fehlenden Quellen daraus abgeleitet."),
    "SOURCE_CHANGED": _("Quelle während des Auftrags geändert. Erneut indizieren."),
    "INVALID_PDF": _("Defekte oder nicht unterstützte PDF."),
    "ENCRYPTED_PDF": _("Verschlüsselte PDF."),
    "LIMIT_EXCEEDED": _("Verarbeitungslimit überschritten."),
    "UNSAFE_FILE": _("Unsicherer Dateityp oder Link."),
    "FILE_IO": _("Quelldatei nicht sicher lesbar."),
    "COPY_MISMATCH": _("Kopie stimmt nicht mit dem Quellhash überein."),
    "DESTINATION_EXISTS": _("Zielkonflikt; vorhandene Datei bleibt erhalten."),
    "CLEAN_MISSING": _("Die gespeicherte CLEAN-Kopie fehlt. Den Ablagepfad prüfen."),
    "CLEAN_CORRUPT": _("Die CLEAN-Kopie weicht vom gespeicherten Prüfsummenwert ab. Die Datei prüfen."),
    "INDEX_FILE_FAILED": _("Dateiverarbeitung fehlgeschlagen. Quelle und Auftrag prüfen."),
}
REVIEW = {
    "PENDING": _("Visuell zu prüfen"),
    "REJECTED": _("Vorschlag verworfen"),
    "APPROVAL_REQUESTED": _("Freigabe beauftragt"),
}
CANDIDATES = {
    "UNASSESSED": _("Noch nicht analysiert"),
    "UNKNOWN": _("Unbekannte Zuordnung"),
    "PROPOSED": _("Erkennungsvorschlag"),
    "CONFLICT": _("Erkennungskonflikt"),
}


def review_files():
    return m.ArchiveFile.objects.filter(kind="BASE", review_state__in=["PENDING", "REJECTED", "APPROVAL_REQUESTED"])


def json_published(record):
    """A text marker alone is never evidence. Verify the JSON receipt and bytes."""
    import hashlib
    from uuid import uuid5

    if not record or not record.snapshot or not record.scan.completed or record.scan.job.status != "SUCCEEDED":
        return False
    data = _content(record, "INDEXSTATUS.json")
    path = _path(record, "INDEXSTATUS.json")
    digest = hashlib.sha256(data).hexdigest()
    intent = record.scan.job.operations.filter(
        state="APPLIED",
        key="index-status:" + str(uuid5(record.pk, "INDEXSTATUS.json")),
    ).first()
    if (
        not intent
        or intent.payload
        != {
            "record_id": str(record.pk),
            "name": "INDEXSTATUS.json",
            "sha256": digest,
            "size": len(data),
            "path": path,
        }
        or intent.result != {"sha256": digest, "size": len(data)}
    ):
        return False
    try:
        preview.snapshot(settings.STATUS_DIR, path, maximum=16_384, sha256=digest, size=len(data))
    except (ValueError, OSError):
        return False
    return True
