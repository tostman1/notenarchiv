import pytest
from django.core.exceptions import ValidationError

from apps.catalog.collection_services import add_membership, add_relationship
from apps.catalog.models import Collection, Work, WorkAlternativeTitle, WorkRelationship

pytestmark = pytest.mark.django_db


def test_125_independent_pieces_retain_song_numbers_and_provenance():
    collection = Collection.objects.create(
        title="Synthetic booklet", metadata={"publisher": "Fixture", "composer": "Shared"}
    )
    for position in range(125):
        work = Work.objects.create(title="Repeated title", composer="Local" if position == 0 else "")
        add_membership(
            collection.pk,
            work.pk,
            position=position,
            original_song_number=str(position + 1),
            local_overrides={"section": "Marches"},
        )
    assert collection.memberships.count() == 125
    first = collection.memberships.get(position=0)
    last = collection.memberships.get(position=124)
    assert first.original_song_number == "1"
    assert last.original_song_number == "125"
    assert first.metadata_snapshot["values"]["composer"]["origin"] == "WORK"
    assert last.metadata_snapshot["values"]["composer"]["origin"] == "COLLECTION"
    assert first.metadata_snapshot["values"]["section"]["origin"] == "LOCAL"
    collection.metadata = {"publisher": "Changed"}
    collection.save()
    last.refresh_from_db()
    assert last.metadata_snapshot["values"]["publisher"]["value"] == "Fixture"


def test_messe_hierarchy_cycles_and_alternative_titles():
    parent = Work.objects.create(title="Deutsche Messe")
    first = Work.objects.create(title="Zum Eingang")
    second = Work.objects.create(title="Zum Eingang")
    add_relationship(parent.pk, first.pk, kind=WorkRelationship.Kind.MOVEMENT, position=0)
    add_relationship(parent.pk, second.pk, kind=WorkRelationship.Kind.MOVEMENT, position=1)
    WorkAlternativeTitle.objects.create(work=first, title="Wohin soll ich mich wenden")
    assert parent.component_relationships.count() == 2
    assert first.pk != second.pk
    with pytest.raises(ValidationError, match="cycles"):
        add_relationship(first.pk, parent.pk, kind=WorkRelationship.Kind.MEDLEY, position=0)
    with pytest.raises(ValidationError, match="explicit arrangements"):
        add_relationship(first.pk, second.pk, kind=WorkRelationship.Kind.RELATED, position=0)
    assert WorkRelationship.objects.count() == 2
