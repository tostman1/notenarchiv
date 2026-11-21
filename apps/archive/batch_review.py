"""Signed per-reviewer selections; all-or-nothing metadata, existing durable effects."""

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q

from apps.archive import models as m
from apps.archive import publication as p
from apps.archive import review_services as review
from apps.archive import services as s
from core.naming import with_suffix
from core.paths import storage_key

SALT = "archive.inspected-batch.v1"
MAX_BATCH = 25


def inspected(file, actor):
    proposal = file.current_proposal
    return bool(
        proposal
        and proposal.state == "DRAFT"
        and proposal.inspections.filter(
            reviewer=actor, explicit_attestation=True, inspected_sha256=file.sha256
        ).exists()
    )


def selection(file, actor):
    if (
        not inspected(file, actor)
        or file.publication_state != "AVAILABLE"
        or file.source_version.source_file.current_version_id != file.source_version_id
    ):
        return ""
    return signing.dumps(
        {
            "file": str(file.pk),
            "actor": str(actor.pk),
            "revision": file.revision,
            "version": str(file.source_version_id),
            "sha256": file.sha256,
            "proposal": str(file.current_proposal_id),
            "source_revision": file.source_version.source_file.revision,
        },
        salt=SALT,
    )


def _load(token, actor):
    try:
        values = signing.loads(token, salt=SALT, max_age=3600)
        file = review.review_file(values["file"])
        if values != {
            "file": str(file.pk),
            "actor": str(actor.pk),
            "revision": file.revision,
            "version": str(file.source_version_id),
            "sha256": file.sha256,
            "proposal": str(file.current_proposal_id),
            "source_revision": file.source_version.source_file.revision,
        }:
            raise ValueError
        if file.source_version.source_file.current_version_id != file.source_version_id:
            raise ValueError
        if (
            not inspected(file, actor)
            or file.operations.filter(Q(state="REVIEW_REQUIRED") | Q(job__status="REVIEW_REQUIRED")).exists()
        ):
            raise ValueError
        return file
    except (signing.BadSignature, ValueError, KeyError, TypeError, m.ArchiveFile.DoesNotExist):
        raise s.ArchiveConflict() from None


def approve_batch(tokens, *, actor, explicit):
    if explicit is not True or not isinstance(tokens, list) or not 1 <= len(tokens) <= MAX_BATCH:
        raise ValidationError("Choose 1-25 individually inspected versions and explicitly approve them.")
    files = [_load(token, actor) for token in tokens]
    if len({file.pk for file in files}) != len(files):
        raise ValidationError("Duplicate batch selections are not allowed.")
    # Bounded I/O/planning outside the short write transaction. Every file is
    # independently checked again by the publication worker before any effect.
    targets = []
    for file in files:
        review.verify_version(
            file,
            {
                "source_version": file.source_version_id,
                "sha256": file.sha256,
                "proposal": file.current_proposal_id,
                "expected_revision": file.revision,
            },
        )
        preferred = p.canonical_path(file.current_proposal)
        target = p.choose_target(file.root_kind, preferred, file.source_version_id, exclude=file.pk)
        for number in range(MAX_BATCH):
            if storage_key(target) not in {storage_key(path) for path in targets}:
                break
            target = p.choose_target(
                file.root_kind,
                with_suffix(preferred, file.source_version_id.hex, number),
                file.source_version_id,
                exclude=file.pk,
            )
        else:
            raise ValidationError("Batch targets conflict.")
        targets.append(target)
    with transaction.atomic():
        # SQLite write-first serialization before revalidating every signed item.
        m.ArchiveFile.objects.filter(pk=files[0].pk).update(revision=F("revision"))
        current = [_load(token, actor) for token in tokens]
        jobs = []
        for file, path in zip(current, targets, strict=True):
            proposal = s.request_approval(file.current_proposal_id, actor=actor, expected_revision=file.revision)
            file.refresh_from_db()
            jobs.append(p._enqueue(file, path, proposal=proposal, using="default"))
        return jobs
