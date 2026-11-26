"""Additive archive page migration preserves legacy validation and stable identities."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.archive import models, services
from apps.archive.source_pages import record_source_pages

LEGACY = ("archive", "0003_preferrededition_editionpreferencechange_and_more")
SCHEMA = ("archive", "0004_sourcepage")
BACKFILL = ("archive", "0005_backfill_source_pages")
PAGE = {
    "media_box": [0, 0, 80, 100],
    "crop_box": [10, 20, 70, 90],
    "width_points": 60,
    "height_points": 70,
    "rotation": 0,
    "user_unit": 1,
}


@pytest.mark.django_db(transaction=True)
def test_backfill_reuses_completed_pages_and_retains_legacy_metadata():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        executor = MigrationExecutor(connection)
        executor.migrate([LEGACY])
        legacy = executor.loader.project_state([LEGACY]).apps
        folder = legacy.get_model("archive", "SourceFolder").objects.create(relative_path="Scores")
        source = legacy.get_model("archive", "SourceFile").objects.create(folder=folder, relative_path="Scores/a.pdf")
        versions = legacy.get_model("archive", "SourceVersion").objects
        first = versions.create(source_file=source, sha256="1" * 64, byte_size=100, pdf_state="VALID", page_info=[PAGE])
        second = versions.create(
            source_file=source, sha256="2" * 64, byte_size=100, pdf_state="VALID", page_info=[PAGE, PAGE]
        )

        executor = MigrationExecutor(connection)
        executor.migrate([SCHEMA])
        schema = executor.loader.project_state([SCHEMA]).apps
        pages = schema.get_model("archive", "SourcePage")
        record_source_pages(pages, first, using=connection.alias)
        preexisting = pages.objects.get(source_version_id=first.pk).pk

        MigrationExecutor(connection).migrate([BACKFILL])
        first_page = models.SourcePage.objects.get(source_version_id=first.pk)
        assert first_page.pk == preexisting
        assert first_page.original_crop_box is None
        assert first_page.effective_crop_box == PAGE["crop_box"]
        assert list(
            models.SourcePage.objects.filter(source_version_id=second.pk).values_list("page_index", flat=True)
        ) == [
            0,
            1,
        ]
        assert models.SourceVersion.objects.get(pk=first.pk).page_info == [PAGE]

        MigrationExecutor(connection).migrate([LEGACY])
        MigrationExecutor(connection).migrate([BACKFILL])
        assert models.SourcePage.objects.get(source_version_id=first.pk).pk == preexisting
        assert models.SourcePage.objects.count() == 3
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db
def test_new_validation_records_source_pages_with_exact_version():
    folder = models.SourceFolder.objects.create(relative_path="Scores")
    source = models.SourceFile.objects.create(folder=folder, relative_path="Scores/a.pdf")
    version = models.SourceVersion.objects.create(source_file=source, sha256="3" * 64, byte_size=100)
    page_info = [PAGE, {**PAGE, "media_box": [0, 0, 15000, 100]}]

    version = services.record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=page_info,
        original_crop_boxes=[PAGE["crop_box"], PAGE["crop_box"]],
    )
    pages = list(version.pages.order_by("page_index"))
    assert [(page.page_index, page.effective_crop_box) for page in pages] == [
        (0, PAGE["crop_box"]),
        (1, PAGE["crop_box"]),
    ]
    assert all(page.original_crop_box == PAGE["crop_box"] for page in pages)
    assert pages[1].media_box == [0, 0, 15000, 100]
    services.record_validation(version.pk, expected_revision=version.revision, pdf_state="VALID", page_info=page_info)
    assert list(version.pages.order_by("page_index")) == pages

    observed, created = services.observe_version(
        folder.pk, source.relative_path, sha256="4" * 64, byte_size=100, pdf_state="VALID", page_info=[PAGE]
    )
    assert created
    observed_page = observed.pages.get()
    assert observed_page.original_crop_box is None
    assert observed_page.pk != pages[0].pk
