"""Withdrawal and replacement retain exact historical associations and receipts."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction

from apps.catalog.collection_services import (
    add_membership,
    add_relationship,
    correct_membership,
    current_associations,
    withdraw_association,
)
from apps.catalog.models import AssociationWithdrawal, Collection, CollectionMembership, Work, WorkRelationship


@pytest.mark.django_db
def test_membership_correction_preserves_receipt_and_current_position():
    actor = get_user_model().objects.create_user(username="synthetic-corrector")
    collection = Collection.objects.create(title="Synthetic collection")
    first, second = Work.objects.create(title="First"), Work.objects.create(title="Second")
    old = add_membership(collection.pk, first.pk, position=0, local_overrides={"composer": "Original"})
    receipt = old.metadata_snapshot
    with pytest.raises(ValidationError):
        correct_membership(
            old.pk, actor=actor, reason="Correction", expected_revision=old.revision, work_id=second.pk, position=-1
        )
    assert not AssociationWithdrawal.objects.exists()
    with pytest.raises(ValidationError):
        withdraw_association("membership", old.pk, actor=actor, reason="Stale", expected_revision=old.revision + 1)
    second.active = False
    second.save()
    with pytest.raises(ObjectDoesNotExist):
        correct_membership(
            old.pk,
            actor=actor,
            reason="Inactive replacement",
            expected_revision=old.revision,
            work_id=second.pk,
            position=0,
        )
    assert not AssociationWithdrawal.objects.exists()
    assert current_associations("membership").get().pk == old.pk
    old.refresh_from_db()
    assert old.metadata_snapshot == receipt
    second.active = True
    second.save()
    new = correct_membership(
        old.pk, actor=actor, reason="Correction", expected_revision=old.revision, work_id=second.pk, position=0
    )
    old.refresh_from_db()
    assert old.metadata_snapshot == receipt
    assert old.work_id == first.pk
    assert new.work_id == second.pk
    assert CollectionMembership.objects.filter(collection=collection, withdrawal__isnull=True).get() == new
    with pytest.raises(ValidationError):
        withdraw_association("membership", old.pk, actor=actor, reason="Again", expected_revision=old.revision)
    with pytest.raises(IntegrityError, match="Active association position"), transaction.atomic():
        CollectionMembership.objects.bulk_create(
            [CollectionMembership(collection=collection, work=first, position=0, metadata_snapshot=receipt)]
        )
    with pytest.raises(IntegrityError, match="Immutable catalog"), transaction.atomic():
        AssociationWithdrawal.objects.all().delete()


@pytest.mark.django_db
def test_withdrawal_reopens_relationship_position_without_historical_cycle():
    actor = get_user_model().objects.create_user(username="synthetic-relationship-corrector")
    first, second = Work.objects.create(title="First"), Work.objects.create(title="Second")
    old = add_relationship(first.pk, second.pk, kind=WorkRelationship.Kind.MOVEMENT, position=0)
    with pytest.raises(ValidationError):
        withdraw_association("relationship", old.pk, actor=actor, reason="", expected_revision=old.revision)
    with pytest.raises(ValidationError):
        withdraw_association("relationship", old.pk, actor=actor, reason="Correction", expected_revision=False)
    assert not AssociationWithdrawal.objects.exists()
    withdraw_association("relationship", old.pk, actor=actor, reason="Wrong direction", expected_revision=old.revision)
    new = add_relationship(second.pk, first.pk, kind=WorkRelationship.Kind.MOVEMENT, position=0)
    assert new.parent_id == second.pk
    assert WorkRelationship.objects.count() == 2
    assert WorkRelationship.objects.filter(withdrawal__isnull=True).count() == 1


@pytest.mark.django_db
def test_alternative_title_withdrawal_requires_active_actor_and_retains_history():
    from apps.catalog.models import WorkAlternativeTitle

    actor = get_user_model().objects.create_user(username="synthetic-title-corrector", is_active=False)
    work = Work.objects.create(title="Synthetic title")
    title = WorkAlternativeTitle.objects.create(work=work, title="Wrong alternative")
    with pytest.raises(ValidationError):
        withdraw_association(
            "alternative_title", title.pk, actor=actor, reason="Correction", expected_revision=title.revision
        )
    assert current_associations("alternative_title").get() == title
    actor.is_active = True
    actor.save()
    withdraw_association(
        "alternative_title", title.pk, actor=actor, reason="Correction", expected_revision=title.revision
    )
    assert not current_associations("alternative_title").exists()
    assert WorkAlternativeTitle.objects.get().title == "Wrong alternative"
    with pytest.raises(IntegrityError, match="Immutable catalog"), transaction.atomic():
        WorkAlternativeTitle.objects.filter(pk=title.pk).update(title="Changed")
