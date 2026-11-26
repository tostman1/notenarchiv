"""Persistent exact-part choices across legacy and inspected content editions."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive.content_contract import confirmed_content_edition
from apps.archive.edition_services import set_preference
from apps.archive.services import ArchiveConflict, _actor
from apps.catalog.models import Arrangement, Part


def set_content_preference(arrangement_id, part_id, edition_id, *, actor, expected_revision, using="default"):
    if edition_id is None:
        return set_preference(
            arrangement_id, part_id, None, actor=actor, expected_revision=expected_revision, using=using
        )
    selected = confirmed_content_edition(edition_id, using=using)
    if (str(selected.arrangement_id), str(selected.part_id)) != (str(arrangement_id), str(part_id)):
        raise ValidationError("Choose inspected content for this exact arrangement and playable part.")
    with transaction.atomic(using=using):
        if type(expected_revision) is not int or not Arrangement.objects.using(using).filter(
            pk=arrangement_id, revision=expected_revision, active=True, work__active=True
        ).update(revision=F("revision") + 1):
            raise ArchiveConflict()
        reviewer = _actor(actor, using)
        if not Part.objects.using(using).filter(pk=part_id, active=True, instrument__active=True).exists():
            raise ValidationError("An active playable part is required.")
        if selected != confirmed_content_edition(edition_id, using=using, verify=False):
            raise ArchiveConflict()
        preference, _ = m.PreferredEdition.objects.using(using).get_or_create(
            arrangement_id=arrangement_id, part_id=part_id
        )
        previous, previous_content = preference.assignment_id, preference.content_edition_id
        preference.assignment_id = None
        preference.content_edition_id = selected.edition_id
        preference.save(using=using)
        if previous is not None or previous_content != selected.edition_id:
            m.EditionPreferenceChange.objects.using(using).create(
                preference=preference,
                actor=reviewer,
                previous_id=previous,
                previous_content_id=previous_content,
                selected_content_id=selected.edition_id,
                arrangement_revision=expected_revision + 1,
            )
        return preference
