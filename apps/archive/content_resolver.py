"""Uniform edition selection using the existing pure explicit/preferred rules.

Project/export activation is deliberately separate from this additive adapter.
"""

from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive.content_contract import ContentResolution, confirmed_content_edition, legacy_content_edition
from apps.archive.edition_services import compatible, select_edition
from apps.archive.services import ArchiveConflict


@dataclass(frozen=True)
class Candidate:
    pk: UUID
    legacy: bool


def resolve_content(arrangement_id, part_id, *, explicit_edition_id=None, using="default"):
    """No unavailable explicit or archived preferred choice silently falls back."""
    preference = m.PreferredEdition.objects.using(using).filter(arrangement_id=arrangement_id, part_id=part_id).first()
    preferred = preference.assignment_id if preference else None
    selected = explicit_edition_id if explicit_edition_id is not None else preferred
    legacy = compatible(arrangement_id, part_id, using=using)
    content = m.ContentEdition.objects.using(using).filter(arrangement_id=arrangement_id, part_id=part_id)
    if selected is not None:
        try:
            selected = UUID(str(selected))
        except (ValueError, TypeError, AttributeError):
            return ContentResolution("UNAVAILABLE", "EXPLICIT" if explicit_edition_id is not None else "ARCHIVE")
        legacy = legacy.filter(pk=selected)
        content = content.filter(pk=selected)
    # Two eligible candidates suffice to establish ambiguity. Do not hash unrelated files.
    candidates = [Candidate(pk, True) for pk in legacy.values_list("pk", flat=True)[:2]]
    content_ids = list(content.values_list("pk", flat=True)[:1001])
    if len(content_ids) > 1000:
        raise ValidationError("Content edition selection exceeds the supported bound.")
    for edition_id in content_ids:
        try:
            confirmed_content_edition(edition_id, using=using, verify=False)
        except (ValidationError, ArchiveConflict):
            continue
        candidates.append(Candidate(edition_id, False))
        if len(candidates) >= 2:
            break
    result = select_edition(candidates, explicit_assignment_id=explicit_edition_id, preferred_assignment_id=preferred)
    if result.assignment is None:
        return ContentResolution(result.status, result.origin)
    adapter = legacy_content_edition if result.assignment.legacy else confirmed_content_edition
    try:
        edition = adapter(result.assignment.pk, using=using)
    except (ValidationError, ArchiveConflict):
        return ContentResolution("UNAVAILABLE", result.origin)
    return ContentResolution(result.status, result.origin, edition)
