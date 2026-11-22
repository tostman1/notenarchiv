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
    if explicit_assignment_id is not None:
        origin, selected = "EXPLICIT", explicit_assignment_id
    else:
        preference = (
            m.PreferredEdition.objects.using(using).filter(arrangement_id=arrangement_id, part_id=part_id).first()
        )
        if preference and preference.assignment_id:
            origin, selected = "ARCHIVE", preference.assignment_id
        else:
            candidates = list(choices[:2])
            if not candidates:
                return EditionResolution("MISSING", "NONE")
            if len(candidates) != 1:
                return EditionResolution("AMBIGUOUS", "NONE")
            origin, selected = "SOLE", candidates[0].pk
    try:
        assignment = choices.filter(pk=selected).first()
    except (ValueError, ValidationError):
        assignment = None
    if assignment is None or not library_services.verify_file(assignment.archive_file):
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
        preference.assignment_id = selected.pk if selected else None
        preference.save(using=using)
        if previous != preference.assignment_id:
            m.EditionPreferenceChange.objects.using(using).create(
                preference=preference,
                actor=reviewer,
                previous_id=previous,
                selected_id=preference.assignment_id,
                arrangement_revision=expected_revision + 1,
            )
        return preference
