"""Presentation adapter only: every musical outcome is the central WP-32 resolver."""

from django.core.paginator import Paginator
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.projects.models import Project
from apps.projects.resolution_services import ResolutionSession

ROWS_PER_PAGE = 25
COLUMNS_PER_PAGE = 10
REASONS = {
    "INACTIVE_ARRANGEMENT": _("Arrangement oder Werk ist inaktiv."),
    "OVERRIDE_REVALIDATION_REQUIRED": _("Persönlichen Override nach Arrangementwechsel erneut prüfen."),
    "EDITION_REVALIDATION_REQUIRED": _("Positions-Ausgabe nach Arrangementwechsel erneut prüfen."),
    "EXPLICIT_EDITION_UNAVAILABLE": _(
        "Feste Ausgabenwahl ist unbestätigt, zurückgezogen oder unpassend; keine Ersatzwahl."
    ),
    "AMBIGUOUS_EDITIONS": _("Mehrere bestätigte Ausgaben ohne eindeutige Bevorzugung."),
    "NO_CONFIRMED_EDITION": _("Keine bestätigte Ausgabe für die gewünschte Stimme."),
    "INACTIVE_DESIRED_PART": _("Gespeicherte gewünschte Stimme oder Notation ist inaktiv."),
    "ENSEMBLE_MISSING": _("Für diese Rolle und Instrumentenvariante fehlt eine explizite Zuordnung."),
    "ENSEMBLE_INVALID_ROLE": _("Musikalische Rolle fehlt oder ist inaktiv."),
    "ENSEMBLE_INVALID_MAPPING": _("Die explizite Rollen-Zuordnung ist nicht gültig."),
    "INVALID_REPLACEMENT_RULE": _("Die explizite Ersatzregel ist nicht kompatibel oder nicht verfügbar."),
    "CYCLIC_REPLACEMENT_RULE": _("Zyklische Ersatzregeln sind gesperrt."),
    "REPLACEMENT_GRAPH_LIMIT": _("Ersatzregelbestand überschreitet die Prüfgrenze."),
    "INPUT_INTEGRITY_FAILURE": _("Kopie fehlt oder Hash stimmt nicht; Archiv prüfen."),
    "ARCHIVE_SELECTION_CHANGED": _("Archivfreigabe hat sich geändert; Seite neu laden."),
}
WARNINGS = {
    "EXPLICIT_PART_SUBSTITUTION": _("Bewusste Ersatzstimme; gewünschte und tatsächliche Stimme sind getrennt."),
    "SOURCE_MISSING_RETAINED_COPY": _("RAW-Quelle fehlt; unveränderte bestätigte Archivkopie ist erhalten."),
}
REPLACEMENT_ORIGINS = {
    "NONE": _("Kein Ersatz"),
    "POSITION": _("Positions-Ersatzregel"),
    "PROJECT": _("Projekt-Ersatzregel"),
    "GLOBAL": _("Globale Ersatzregel"),
}


def cell_context(session, result):
    return {
        "resolution": result,
        "desired_part": session.parts.get(result.desired_part_id),
        "effective_part": session.parts.get(result.effective_part_id),
        "reasons": [REASONS.get(code, _("Zuordnung prüfen.")) for code in result.reasons],
        "warnings": [WARNINGS.get(code, _("Hinweis zur Zuordnung prüfen.")) for code in result.warnings],
        "replacement_label": REPLACEMENT_ORIGINS[result.replacement_origin],
    }


def matrix_page(project_id, *, row_page=None, column_page=None):
    # Pagination IDs and resolver inputs share one SQLite read snapshot. File
    # verification remains outside the short read transaction, once per file.
    with transaction.atomic():
        project = Project.objects.get(pk=project_id)
        row_ids = Paginator(
            project.positions.filter(active=True).order_by("order", "pk").values_list("pk", flat=True), ROWS_PER_PAGE
        ).get_page(row_page)
        column_ids = Paginator(
            project.participants.filter(active=True).order_by("display_name", "pk").values_list("pk", flat=True),
            COLUMNS_PER_PAGE,
        ).get_page(column_page)
        session = ResolutionSession(project.pk, position_ids=list(row_ids), participant_ids=list(column_ids))
    rows, people = [], list(session.participants.values())
    for position in session.positions.values():
        cells = [cell_context(session, session.verified_resolution(position.pk, person.pk)) for person in people]
        rows.append({"position": position, "cells": cells})
    return {
        "project": session.project,
        "rows": rows,
        "participants": people,
        "row_page": row_ids,
        "column_page": column_ids,
        "session": session,
    }
