"""Real-browser explicit corrections retain history without music/export side effects."""

import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.collection_services import add_membership
from apps.catalog.models import AssociationWithdrawal, Collection, CollectionMembership, Work
from apps.exports.models import GenerationSnapshot


@pytest.mark.django_db(transaction=True)
def test_catalog_correction_in_browser(settings, tmp_path, request):
    get_user_model().objects.create_user(username="synthetic-correction-browser", password="Synthetic-content-135")
    first, second = (
        Work.objects.create(title="First synthetic work"),
        Work.objects.create(title="Second synthetic work"),
    )
    old = add_membership(Collection.objects.create(title="Synthetic collection").pk, first.pk, position=0)
    receipt = old.metadata_snapshot
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("catalog_correction.cjs")), server.url, str(old.pk), str(second.pk)],
        check=True,
        timeout=90,
    )
    old.refresh_from_db()
    assert old.work_id == first.pk and old.metadata_snapshot == receipt
    assert AssociationWithdrawal.objects.count() == 2
    assert CollectionMembership.objects.count() == 2
    assert not CollectionMembership.objects.filter(withdrawal__isnull=True).exists()
    assert not GenerationSnapshot.objects.exists()
