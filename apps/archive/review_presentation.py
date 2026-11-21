"""Translate bounded recognition/audit codes without logging business evidence."""

from django.utils.translation import gettext_lazy as _

REASONS = {
    "work_conflict_between_sources": _("Dateiname und Inhalt nennen unterschiedliche Werke."),
    "part_conflict_between_sources": _("Dateiname und Inhalt nennen unterschiedliche Stimmen."),
    "instrument_conflict_between_sources": _("Dateiname und Inhalt nennen unterschiedliche Instrumente."),
    "work_unresolved": _("Werk nicht eindeutig erkannt."),
    "instrument_unresolved": _("Instrument nicht eindeutig erkannt."),
    "instrument_ambiguous": _("Instrumentenvariante mehrdeutig."),
    "sources:filename+text": _("Dateiname und Textschicht wurden verglichen."),
    "sources:filename": _("Nur Dateiname als Hinweis; tatsächlichen Inhalt visuell prüfen."),
}
EVENTS = {
    "PROPOSAL_CREATED": _("Zuordnung gespeichert"),
    "INSPECTED": _("Visuell geprüft"),
    "APPROVAL_REQUESTED": _("Freigabe beauftragt"),
    "CONFIRMED": _("Bestätigt"),
    "REJECTED": _("Vorschlag verworfen"),
    "WITHDRAWN": _("Freigabe zurückgezogen"),
}
