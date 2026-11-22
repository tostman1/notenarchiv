"""Version-bound manual cell edits with short SQLite revision and archive fences."""

from django.core import signing
from django.core.exceptions import ValidationError

from apps.archive import edition_services, library_services
from apps.archive import models as archive
from apps.projects import models as m
from apps.projects.services import ProjectConflict, edit, reviewer

SALT = "project.matrix-edition.v1"


def choice_token(assignment, actor):
    file = assignment.archive_file
    return signing.dumps(
        {
            "actor": str(actor.pk),
            "assignment": str(assignment.pk),
            "part": str(assignment.part_id),
            "file": str(file.pk),
            "revision": file.revision,
            "sha256": file.sha256,
            "arrangement": str(file.arrangement_id),
        },
        salt=SALT,
        compress=True,
    )


def selected_choice(token, actor):
    if not isinstance(token, str) or len(token) > 4096:
        raise ValidationError("Invalid exact matrix choice.")
    try:
        payload = signing.loads(token, salt=SALT, max_age=900)
        if payload["actor"] != str(actor.pk):
            raise ValueError
        selected = (
            archive.ArchiveAssignment.objects.usable()
            .filter(
                pk=payload["assignment"],
                part_id=payload["part"],
                archive_file_id=payload["file"],
                archive_file__revision=payload["revision"],
                archive_file__sha256=payload["sha256"],
                archive_file__arrangement_id=payload["arrangement"],
            )
            .select_related("archive_file", "part__instrument")
            .first()
        )
        if selected is None or not library_services.verify_file(selected.archive_file):
            raise ValueError
    except (signing.BadSignature, ValueError, TypeError, KeyError, ValidationError):
        raise ValidationError("Exact edition changed, expired or is not confirmed and compatible.") from None
    return selected


def set_cell(project_id, position_id, participant_id, token, *, actor, expected_revision):
    selected = selected_choice(token, actor)
    file_revision = selected.archive_file.revision
    with edit(project_id, expected_revision, actor=actor, event="MATRIX_CELL_SAVED") as project:
        position = project.positions.filter(
            pk=position_id, active=True, arrangement__active=True, arrangement__work__active=True
        ).first()
        participant = project.participants.filter(pk=participant_id, active=True).first()
        if position is None or participant is None or position.arrangement_id != selected.archive_file.arrangement_id:
            raise ValidationError("Cell belongs to another project, reserve or incompatible arrangement.")
        if (
            not edition_services.compatible(position.arrangement_id, selected.part_id)
            .filter(pk=selected.pk, archive_file__revision=file_revision)
            .exists()
        ):
            raise ProjectConflict()
        record, created = m.PartOverride.objects.get_or_create(
            project=project,
            position=position,
            participant=participant,
            defaults={"desired_part": selected.part, "edition": selected},
        )
        previous_part = None if created else record.desired_part_id
        previous_edition = None if created else record.edition_id
        record.desired_part, record.edition, record.needs_revalidation = selected.part, selected, False
        record.save()
        m.MatrixChange.objects.create(
            project=project,
            project_revision=project.revision,
            actor=reviewer(actor),
            participant=participant,
            position=position,
            override=record,
            event="CELL_SAVED",
            previous_part_id=previous_part,
            selected_part=selected.part,
            previous_edition_id=previous_edition,
            selected_edition=selected,
        )
        return record
