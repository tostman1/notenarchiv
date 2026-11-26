"""Synthetic source-page identity and geometry constraints."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.archive.models import SourceFile, SourceFolder, SourcePage, SourceVersion
from core.page_geometry import PageGeometry

pytestmark = pytest.mark.django_db


@pytest.fixture
def source_version():
    folder = SourceFolder.objects.create(relative_path="")
    source = SourceFile.objects.create(folder=folder, relative_path="synthetic.pdf")
    return SourceVersion.objects.create(
        source_file=source,
        sha256="1" * 64,
        byte_size=100,
        pdf_state="VALID",
        page_info=[
            {
                "media_box": [0, 0, 100, 100],
                "crop_box": [0, 20, 100, 80],
                "user_unit": 1,
                "rotation": 90,
                "width_points": 60,
                "height_points": 100,
            }
        ],
    )


def create_page(version, **overrides):
    metadata = version.page_info[0]
    fields = {
        "source_version": version,
        "page_index": 0,
        "media_box": metadata["media_box"],
        "effective_crop_box": metadata["crop_box"],
        "rotation": metadata["rotation"],
        "user_unit": metadata["user_unit"],
    }
    return SourcePage.objects.create(**(fields | overrides))


def test_page_identity_is_unique_within_an_exact_source_version(source_version):
    first = create_page(source_version)
    successor = SourceVersion.objects.create(
        source_file=source_version.source_file,
        sha256="2" * 64,
        byte_size=100,
        pdf_state="VALID",
        page_info=source_version.page_info,
    )
    second = create_page(successor)
    assert first.pk != second.pk
    assert first.geometry_fingerprint == second.geometry_fingerprint
    assert source_version.pages.get(page_index=0) == first

    first.pk = None
    with pytest.raises(IntegrityError), transaction.atomic():
        SourcePage.objects.bulk_create([first])


def test_old_geometry_does_not_claim_an_original_crop_box(source_version):
    legacy = create_page(source_version)
    legacy.refresh_from_db()
    assert legacy.original_crop_box is None
    assert legacy.effective_crop_box == [0, 20, 100, 80]
    exact = PageGeometry(legacy.media_box, [-10, 20, 110, 80], legacy.rotation, legacy.user_unit)
    assert legacy.geometry_fingerprint != exact.fingerprint


def test_exact_original_crop_is_bound_to_effective_geometry(source_version):
    with pytest.raises(ValidationError, match="Original source page geometry is inconsistent"):
        create_page(source_version, original_crop_box=[10, 20, 90, 80])
    exact = create_page(source_version, original_crop_box=[-10, 20, 110, 80])
    assert (
        exact.geometry_fingerprint
        == PageGeometry(exact.media_box, exact.original_crop_box, exact.rotation, exact.user_unit).fingerprint
    )


def test_page_requires_recorded_index_and_cannot_be_changed_or_deleted(source_version):
    with pytest.raises(ValidationError, match="recorded valid PDF page"):
        create_page(source_version, page_index=1)
    with pytest.raises(ValidationError, match="match the recorded PDF page"):
        create_page(source_version, rotation=0)

    page = create_page(source_version)
    page.original_crop_box = list(page.effective_crop_box)
    with pytest.raises(ValidationError, match="immutable"):
        page.save()
    with pytest.raises(ValidationError, match="history is retained"):
        page.delete()
    with pytest.raises(ProtectedError):
        SourceVersion.objects.filter(pk=source_version.pk).delete()
