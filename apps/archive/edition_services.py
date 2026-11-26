"""Reusable edition resolution component; never guess or replace explicit inputs."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.archive import library_services
from apps.archive import models as m
from apps.archive.services import ArchiveConflict, _actor
from apps.catalog.models import Arrangement, Part

LABELS = {
    "AVAILABLE": _("Ausgabe eindeutig gewählt"),
    "AMBIGUOUS": _("Mehrere passende Ausgaben; bitte ausdrücklich wählen"),
    "MISSING": _("Keine bestätigte passende Ausgabe vorhanden"),
    "UNAVAILABLE": _("Gewählte Ausgabe zurückgezogen, nicht verfügbar oder beschädigt; keine Ersatzwahl"),
}
ORIGINS = {
    "EXPLICIT": _("Explizite Ausgabenwahl"),
    "ARCHIVE": _("Archivweite Bevorzugung"),
    "SOLE": _("Einzige passende bestätigte Ausgabe"),
    "NONE": _("Keine Ausgabenwahl"),
}


@dataclass(frozen=True)
class EditionResolution:
    status: str
    origin: str
    assignment: m.ArchiveAssignment | None = None

    @property
    def label(self):
        return LABELS[self.status]

    @property
    def origin_label(self):
        return ORIGINS[self.origin]


def compatible(arrangement_id, part_id, *, using="default"):
    return (
        m.ArchiveAssignment.objects.using(using)
        .usable()
        .filter(archive_file__arrangement_id=arrangement_id, part_id=part_id)
        .select_related("archive_file__publication_operation__intent", "part__instrument")
        .order_by("pk")
    )


def resolve(arrangement_id, part_id, *, explicit_assignment_id=None, using="default"):
    """Exact part includes notation/transposition; same number is never compatibility."""
    choices = compatible(arrangement_id, part_id, using=using)
    preference = m.PreferredEdition.objects.using(using).filter(arrangement_id=arrangement_id, part_id=part_id).first()
    preferred = (preference.content_edition_id or preference.assignment_id) if preference else None
    selected = explicit_assignment_id if explicit_assignment_id is not None else preferred
    try:
        candidates = list(choices.filter(pk=selected)[:1]) if selected is not None else list(choices[:2])
    except (ValidationError, ValueError):
        candidates = []
    result = select_edition(
        candidates,
        explicit_assignment_id=explicit_assignment_id,
        preferred_assignment_id=preferred,
    )
    if result.assignment is not None and not library_services.verify_file(result.assignment.archive_file):
        return EditionResolution("UNAVAILABLE", result.origin)
    return result


def select_edition(choices, *, explicit_assignment_id=None, preferred_assignment_id=None):
    """Pure edition choice over eligible exact-part assignments; shared with WP-32."""
    if explicit_assignment_id is not None:
        origin, selected = "EXPLICIT", explicit_assignment_id
    elif preferred_assignment_id is not None:
        origin, selected = "ARCHIVE", preferred_assignment_id
    else:
        if not choices:
            return EditionResolution("MISSING", "NONE")
        if len(choices) != 1:
            return EditionResolution("AMBIGUOUS", "NONE")
        origin, selected = "SOLE", choices[0].pk
    assignment = next((item for item in choices if str(item.pk) == str(selected)), None)
    if assignment is None:
        return EditionResolution("UNAVAILABLE", origin)
    return EditionResolution("AVAILABLE", origin, assignment)


def set_preference(arrangement_id, part_id, assignment_id, *, actor, expected_revision, using="default"):
    # Bounded hash verification outside the short SQLite write transaction.
    selected = None
    if assignment_id is not None:
        selected = compatible(arrangement_id, part_id, using=using).filter(pk=assignment_id).first()
        if selected is None or not library_services.verify_file(selected.archive_file):
            raise ValidationError(_("Wählen Sie eine bestätigte, hash-geprüfte Ausgabe für genau diese Stimme."))
        file_revision = selected.archive_file.revision
    with transaction.atomic(using=using):
        if type(expected_revision) is not int or not Arrangement.objects.using(using).filter(
            pk=arrangement_id, revision=expected_revision, active=True, work__active=True
        ).update(revision=F("revision") + 1):
            raise ArchiveConflict()
        reviewer = _actor(actor, using)
        part = Part.objects.using(using).filter(pk=part_id).first()
        if selected is not None and part is not None and (not part.active or not part.instrument.active):
            raise ValidationError(_("Wählen Sie eine aktive spielbare Stimme."))
        if part is None:
            raise ValidationError(_("Wählen Sie eine aktive spielbare Stimme."))
        if (
            selected is not None
            and not compatible(arrangement_id, part_id, using=using)
            .filter(pk=selected.pk, archive_file__revision=file_revision)
            .exists()
        ):
            raise ArchiveConflict()
        preference, _created = m.PreferredEdition.objects.using(using).get_or_create(
            arrangement_id=arrangement_id, part_id=part_id
        )
        previous = preference.assignment_id
        previous_content = preference.content_edition_id
        preference.content_edition_id = None
        preference.assignment_id = selected.pk if selected else None
        preference.save(using=using)
        if previous != preference.assignment_id or previous_content is not None:
            m.EditionPreferenceChange.objects.using(using).create(
                preference=preference,
                actor=reviewer,
                previous_id=previous,
                previous_content_id=previous_content,
                selected_id=preference.assignment_id,
                arrangement_revision=expected_revision + 1,
            )
        return preference
