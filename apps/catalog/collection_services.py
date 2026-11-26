"""Explicit musical relationships and reproducible inheritance receipts."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.catalog.collection_models import validate_metadata
from apps.catalog.models import Collection, CollectionMembership, Work, WorkRelationship


def metadata_snapshot(collection, work, overrides, *, membership_id, membership_revision=0):
    validate_metadata(collection.metadata)
    validate_metadata(overrides)
    values = {
        key: {"value": value, "origin": "COLLECTION", "identity": str(collection.pk), "revision": collection.revision}
        for key, value in collection.metadata.items()
    }
    if work.composer:
        values["composer"] = {
            "value": work.composer,
            "origin": "WORK",
            "identity": str(work.pk),
            "revision": work.revision,
        }
    for key, value in overrides.items():
        values[key] = {
            "value": value,
            "origin": "LOCAL",
            "identity": str(membership_id),
            "revision": membership_revision,
        }
    return {"schema": "collection-metadata-v2", "values": values}


def current_associations(kind, *, using="default"):
    """Use current rows for new catalog reads; historical reverse relations stay intact."""
    from apps.catalog.models import WorkAlternativeTitle

    targets = {
        "membership": CollectionMembership,
        "relationship": WorkRelationship,
        "alternative_title": WorkAlternativeTitle,
    }
    if kind not in targets:
        raise ValidationError("Unsupported association type.")
    return targets[kind].objects.using(using).filter(withdrawal__isnull=True)


def add_membership(collection_id, work_id, *, position, original_song_number="", local_overrides=None, using="default"):
    with transaction.atomic(using=using):
        if not Collection.objects.using(using).filter(pk=collection_id, active=True).update(revision=F("revision")):
            raise ValidationError("An active collection is required.")
        collection = Collection.objects.using(using).get(pk=collection_id)
        work = Work.objects.using(using).get(pk=work_id, active=True)
        if (
            CollectionMembership.objects.using(using)
            .filter(collection=collection, position=position, withdrawal__isnull=True)
            .exists()
        ):
            raise ValidationError("The active collection position is already occupied.")
        overrides = local_overrides or {}
        membership = CollectionMembership(
            collection=collection,
            work=work,
            position=position,
            original_song_number=original_song_number,
            local_overrides=overrides,
        )
        membership.metadata_snapshot = metadata_snapshot(
            collection, work, overrides, membership_id=membership.pk, membership_revision=membership.revision
        )
        membership.save(using=using)
        return membership


def validate_relationship(row, *, using):
    if row.parent_id == row.component_id:
        raise ValidationError("A work cannot contain or relate to itself.")
    arrangements = (row.parent_arrangement_id, row.component_arrangement_id)
    if row.kind == WorkRelationship.Kind.RELATED:
        if not all(arrangements):
            raise ValidationError("Related editions require both explicit arrangements.")
        if row.parent_arrangement.work_id != row.parent_id or row.component_arrangement.work_id != row.component_id:
            raise ValidationError("Related arrangements must belong to their explicit works.")
        if not row.parent_arrangement.active or not row.component_arrangement.active:
            raise ValidationError("Related editions require active arrangements.")
    elif any(arrangements):
        raise ValidationError("Composition hierarchy cannot imply arrangement relationships.")
    if row.kind not in WorkRelationship.Kind.values:
        raise ValidationError("Unsupported work relationship type.")
    if row.kind == WorkRelationship.Kind.RELATED:
        return
    # Bound traversal, with no filename/title identity inference.
    edges = list(
        WorkRelationship.objects.using(using)
        .filter(kind__in=(WorkRelationship.Kind.MOVEMENT, WorkRelationship.Kind.MEDLEY), withdrawal__isnull=True)
        .values_list("parent_id", "component_id")[:10001]
    )
    if len(edges) > 10000:
        raise ValidationError("Relationship graph exceeds the supported validation bound.")
    adjacency = {}
    for parent, component in edges:
        adjacency.setdefault(parent, set()).add(component)
    pending, seen = [row.component_id], set()
    while pending:
        current = pending.pop()
        if current == row.parent_id:
            raise ValidationError("Work relationships must not contain cycles.")
        if current not in seen:
            seen.add(current)
            pending.extend(adjacency.get(current, ()))


def add_relationship(
    parent_id,
    component_id,
    *,
    kind,
    position,
    parent_arrangement_id=None,
    component_arrangement_id=None,
    using="default",
):
    with transaction.atomic(using=using):
        # SQLite's database-wide writer lock serializes graph validation and insertion.
        if not Work.objects.using(using).filter(pk=parent_id, active=True).update(revision=F("revision")):
            raise ValidationError("An active parent work is required.")
        if not Work.objects.using(using).filter(pk=component_id, active=True).exists():
            raise ValidationError("An active component work is required.")
        if (
            WorkRelationship.objects.using(using)
            .filter(parent_id=parent_id, kind=kind, position=position, withdrawal__isnull=True)
            .exists()
        ):
            raise ValidationError("The active relationship position is already occupied.")
        return WorkRelationship.objects.using(using).create(
            parent_id=parent_id,
            component_id=component_id,
            kind=kind,
            position=position,
            parent_arrangement_id=parent_arrangement_id,
            component_arrangement_id=component_arrangement_id,
        )


def withdraw_association(kind, identifier, *, actor, reason, expected_revision, using="default"):
    """Serialize explicit withdrawal; never edit or delete an old association."""
    from apps.catalog.models import AssociationWithdrawal, WorkAlternativeTitle

    targets = {
        "membership": CollectionMembership,
        "relationship": WorkRelationship,
        "alternative_title": WorkAlternativeTitle,
    }
    if kind not in targets or type(expected_revision) is not int:
        raise ValidationError("A supported association and exact revision are required.")
    with transaction.atomic(using=using):
        rows = targets[kind].objects.using(using).filter(pk=identifier, revision=expected_revision)
        if kind == "membership":
            locked = (
                Collection.objects.using(using)
                .filter(pk__in=rows.values("collection_id"))
                .update(revision=F("revision"))
            )
        else:
            field = "parent_id" if kind == "relationship" else "work_id"
            locked = Work.objects.using(using).filter(pk__in=rows.values(field)).update(revision=F("revision"))
        if not locked:
            raise ValidationError("The association revision is unavailable or stale.")
        if AssociationWithdrawal.objects.using(using).filter(**{f"{kind}_id": identifier}).exists():
            raise ValidationError("The association has already been withdrawn.")
        return AssociationWithdrawal.objects.using(using).create(
            **{f"{kind}_id": identifier}, actor=actor, reason=reason
        )


def correct_membership(
    identifier,
    *,
    actor,
    reason,
    expected_revision,
    work_id,
    position,
    original_song_number="",
    local_overrides=None,
    using="default",
):
    """Withdraw and replace atomically; an invalid replacement preserves the old row."""
    with transaction.atomic(using=using):
        event = withdraw_association(
            "membership", identifier, actor=actor, reason=reason, expected_revision=expected_revision, using=using
        )
        return add_membership(
            event.membership.collection_id,
            work_id,
            position=position,
            original_song_number=original_song_number,
            local_overrides=local_overrides,
            using=using,
        )
