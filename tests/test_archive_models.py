"""Synthetic archive identity/state constraints; no filesystem publication claimed."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import services
from core.paths import relative_path
from tests.archive_fixtures import PAGE


def test_same_content_is_not_a_global_musical_identity(archive):
    folder, version, file, data = archive
    other, created = services.observe_version(
        folder.pk,
        "Synthetic/another.pdf",
        sha256=version.sha256,
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[PAGE],
    )
    assert created and version.pk != other.pk
    reused, created = services.observe_version(
        folder.pk,
        "Synthetic/scan.pdf",
        sha256=version.sha256,
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[PAGE],
    )
    assert not created and reused.pk == version.pk
    assert file.arrangement_id is None and not m.ArchiveFile.objects.usable().exists()


def test_missing_source_keeps_copy_and_version_history(archive):
    _folder, version, file, _data = archive
    source = m.SourceFile.objects.get(pk=version.source_file_id)
    services.mark_source_missing(source.pk, expected_revision=source.revision)
    source.refresh_from_db()
    file.refresh_from_db()
    assert source.presence == "MISSING" and source.current_version_id == version.pk
    assert file.source_version_id == version.pk and file.review_state == "PENDING"
    assert file.publication_state == "UNPUBLISHED"


@pytest.mark.parametrize(
    "path",
    ["/absolute.pdf", "../escape.pdf", "a/../escape.pdf", "a//b", "a/./b", "C:/file.pdf", "x\\y", ".", "", "a\x00b"],
)
def test_noncanonical_source_references_are_denied(path):
    with pytest.raises(ValueError):
        relative_path(path)


def test_publication_cannot_be_claimed_without_a_receipt(archive):
    _folder, _version, file, _data = archive
    file.publication_state = "AVAILABLE"
    with pytest.raises(ValidationError):
        file.save()
    file.refresh_from_db()
    assert file.publication_state == "UNPUBLISHED"
