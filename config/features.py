"""Current integrated capability inventory; presentation never replaces authorization."""

from django.utils.translation import gettext_lazy as _

FEATURES = (
    ("archive", _("Archiv indizieren, visuell prüfen und bestätigen"), "AVAILABLE", "WP-15/20", "archive_index"),
    (
        "library",
        _("Notenbibliothek, konkrete Ausgaben und Originaldownloads"),
        "AVAILABLE",
        "WP-21/23",
        "archive_library",
    ),
    (
        "projects",
        _("Projekte, Stückliste/Reserven, Personen und Ensemble-Mappings"),
        "AVAILABLE",
        "WP-29–35",
        "project_list",
    ),
    (
        "matrix",
        _("Matrix bearbeiten, Vorprüfung und unveränderliche Freigabe"),
        "AVAILABLE",
        "WP-33/36",
        "project_list",
    ),
    (
        "pdf",
        _("Persönliche Mappen, Auszüge, Inhaltsverzeichnis und reguläre Druck-PDF"),
        "AVAILABLE",
        "WP-37/38",
        "export_library",
    ),
    (
        "exports",
        _("Ausgabebibliothek, gezielte Neuerstellung und Veraltungsstatus"),
        "AVAILABLE",
        "WP-39",
        "export_library",
    ),
    ("integrity", _("Vollständige Archiv-Integritätsprüfung"), "UNAVAILABLE", "WP-27", None),
    ("ocr", _("Lokale OCR"), "UNAVAILABLE", "WP-24–28", None),
    ("enhancement", _("Scanaufbereitung"), "UNAVAILABLE", "WP-40/41", None),
    ("marchbook", _("Marschbuch-Konfiguration / spezifisches Drucklayout"), "PARTIAL", "WP-42", None),
    ("printing", _("Physisch drucken / Drucker auswählen"), "UNAVAILABLE", "WP-44–46", None),
    ("nas", _("Produktionsfreigabe auf echter Synology-Hardware"), "PARTIAL", "WP-22/52/53", None),
)


def availability(request):
    from django.conf import settings

    return {"feature_availability": FEATURES, "test_distribution": settings.TEST_DISTRIBUTION}
