"""Review orchestration reuses protected domain transitions and safe managed reads."""

from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import preview_services, publication, services


def review_file(identifier):
    return m.ArchiveFile.objects.select_related(
        "source_version__source_file",
        "current_proposal__arrangement__work",
        "publication_operation__intent",
        "arrangement__work",
        "approved_proposal",
    ).get(pk=identifier, kind="BASE", root_kind="CLEAN")


def verify_version(file, values):
    if (
        values["source_version"] != file.source_version_id
        or values["sha256"] != file.sha256
        or values.get("proposal") != file.current_proposal_id
        or values["expected_revision"] != file.revision
    ):
        raise services.ArchiveConflict()
    # Read-only bounded handle/hash verification. The worker independently
    # verifies publication again; opening this route never records an inspection.
    services._available(file)
    preview_services.preview_bytes(file)


def act(file, action, values, actor):
    verify_version(file, values)
    if (
        file.operations.filter(job__status="REVIEW_REQUIRED").exists()
        or file.operations.filter(state="REVIEW_REQUIRED").exists()
    ):
        raise ValidationError("Resolve uncertain publication before changing or repeating this review.")
    common = {"actor": actor, "expected_revision": values["expected_revision"]}
    if action == "save":
        return services.create_proposal(
            file.pk, arrangement_id=values["arrangement"].pk, part_ids=[part.pk for part in values["parts"]], **common
        )
    if not file.current_proposal_id:
        raise ValidationError("Save a controlled proposal before reviewing it.")
    if action == "inspect":
        return services.record_inspection(
            file.current_proposal_id, inspected_sha256=file.sha256, explicit=values["explicit"], **common
        )
    if action == "approve":
        return publication.queue_canonical(file.current_proposal_id, **common)
    if action == "reject":
        return services.reject_proposal(file.current_proposal_id, **common)
    raise ValidationError("Unsupported review action.")
