"""Fixed German business messages; payloads and exception texts never reach UI."""

from django.utils.translation import gettext_lazy as _

KINDS = {
    "INDEX_SCAN": _("Indizierung"),
    "OCR": _("Texterkennung"),
    "INTEGRITY_CHECK": _("Integritätsprüfung"),
    "ARCHIVE_PUBLISH": _("Archivfreigabe"),
    "GENERATE": _("Ausgabe erstellen"),
    "SCAN_PROCESS": _("Scanaufbereitung"),
    "PRINT": _("Druckauftrag"),
}
STATUSES = {
    "QUEUED": _("Wartend"),
    "RUNNING": _("Läuft"),
    "SUCCEEDED": _("Abgeschlossen"),
    "FAILED": _("Fehlgeschlagen"),
    "CANCELLED": _("Abgebrochen"),
    "REVIEW_REQUIRED": _("Prüfung erforderlich"),
}
ERRORS = {
    "PROCESS_CLEANUP_UNCERTAIN": _(
        "Die Beendigung aller Teilprozesse konnte nicht bestätigt werden. Eine Prüfung ist erforderlich."
    ),
    "HANDLER_FAILED": _("Die Verarbeitung ist fehlgeschlagen."),
    "HANDLER_UNAVAILABLE": _("Diese Verarbeitung ist noch nicht verfügbar."),
    "PAYLOAD_INVALID": _("Die gespeicherten Auftragsdaten sind ungültig."),
    "PRINT_ACCEPTANCE_UNKNOWN": _(
        "Die Druckannahme ist unklar. Prüfen Sie den Drucker. Es erfolgt keine automatische Wiederholung."
    ),
    "OPERATION_UNCERTAIN": _("Eine externe Änderung muss vor weiteren Schritten geprüft werden."),
    "RECOVERY_UNSAFE": _("Der unterbrochene Auftrag kann nicht sicher automatisch fortgesetzt werden."),
    "RETRY_EXHAUSTED": _("Die zulässigen Verarbeitungsversuche sind ausgeschöpft."),
    "INTERRUPTED": _("Die Verarbeitung wurde unterbrochen."),
    "CANCELLED": _("Die Verarbeitung wurde beendet. Bereits abgeschlossene Änderungen bleiben erhalten."),
}


def describe(job):
    job.kind_label = KINDS.get(getattr(job, "kind", ""), _("Auftrag"))
    job.status_label = STATUSES.get(job.status, _("Unbekannter Status"))
    if job.status == "RUNNING" and getattr(job, "cancel_requested", False):
        job.status_label = _("Abbruch angefordert")
    job.error_message = (
        ERRORS.get(job.error_code, _("Ein technischer Fehler ist aufgetreten.")) if job.error_code else ""
    )
    job.can_cancel = job.status in {"QUEUED", "RUNNING"} and not getattr(job, "cancel_requested", False)
    return job
