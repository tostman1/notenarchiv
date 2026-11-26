"""Explicit musical relationships and reproducible inheritance receipts."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.catalog.collection_models import validate_metadata
from apps.catalog.models import Collection, CollectionMembership, Work, WorkRelationship


def metadata_snapshot(collection, work, overrides):
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
        values[key] = {"value": value, "origin": "LOCAL", "identity": str(work.pk), "revision": work.revision}
    return {"schema": "collection-metadata-v1", "values": values}


def add_membership(collection_id, work_id, *, position, original_song_number="", local_overrides=None, using="default"):
    with transaction.atomic(using=using):
        if not Collection.objects.using(using).filter(pk=collection_id, active=True).update(revision=F("revision")):
            raise ValidationError("An active collection is required.")
        collection = Collection.objects.using(using).get(pk=collection_id)
        work = Work.objects.using(using).get(pk=work_id, active=True)
        overrides = local_overrides or {}
        return CollectionMembership.objects.using(using).create(
            collection=collection,
            work=work,
            position=position,
            original_song_number=original_song_number,
            local_overrides=overrides,
            metadata_snapshot=metadata_snapshot(collection, work, overrides),
        )


def validate_relationship(row, *, using):
    if row.parent_id == row.component_id:
        raise ValidationError("A work cannot contain or relate to itself.")
    arrangements = (row.parent_arrangement_id, row.component_arrangement_id)
    if row.kind == WorkRelationship.Kind.RELATED:
        if not all(arrangements):
            raise ValidationError("Related editions require both explicit arrangements.")
        if row.parent_arrangement.work_id != row.parent_id or row.component_arrangement.work_id != row.component_id:
            raise ValidationError("Related arrangements must belong to their explicit works.")
    elif any(arrangements):
        raise ValidationError("Composition hierarchy cannot imply arrangement relationships.")
    if row.kind not in WorkRelationship.Kind.values:
        raise ValidationError("Unsupported work relationship type.")
    # Bound traversal, with no filename/title identity inference.
    edges = list(WorkRelationship.objects.using(using).values_list("parent_id", "component_id")[:10001])
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
        return WorkRelationship.objects.using(using).create(
            parent_id=parent_id,
            component_id=component_id,
            kind=kind,
            position=position,
            parent_arrangement_id=parent_arrangement_id,
            component_arrangement_id=component_arrangement_id,
        )
