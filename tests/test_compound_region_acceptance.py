"""Reviewed card regions differ across instruments without inventing musical identity."""

import hashlib
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from pypdf import PdfReader

from apps.archive import models as m
from apps.archive import services as s
from apps.archive.content_contract import confirmed_content_edition
from apps.archive.content_geometry_services import append_region
from apps.archive.content_rendering import render_content
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.exports.content_inputs import capture_content, load_content
from core.pdf import Processor
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import pdf
from tests.test_archive_workflow import receipt
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_instrument_specific_cards_require_exact_review_and_preserve_history(edition_inputs, settings, tmp_path):
    actor, arrangement, parts, *_ = edition_inputs
    folder = m.SourceFolder.objects.create(relative_path="Synthetic card booklets")
    data = pdf()
    files = []
    for index in range(2):
        version, _ = s.observe_version(
            folder.pk,
            f"Synthetic card booklets/{index}.pdf",
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            pdf_state="UNCHECKED",
        )
        s.record_validation(
            version.pk,
            expected_revision=version.revision,
            pdf_state="VALID",
            page_info=[PAGE],
            original_crop_boxes=[PAGE["crop_box"]],
        )
        file, _ = receipt(s.register_base(version.pk, f"_Ungeprueft/cards-{index}.pdf"))
        path = settings.CURATED_DIR / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        files.append(file)
    editions, regions, captures = [], [], []
    for index, part in enumerate(parts):
        source = files[index].source_version.pages.get()
        x0, y0, x1, y1 = source.effective_crop_box
        width, height = (x1 - x0) / 2, (y1 - y0) / 2
        logicals = []
        for cell in range(4):
            # The second instrumental source explicitly orders the same card
            # identity differently; equality of page index never assigns music.
            location = cell if index == 0 else 3 - cell
            left, bottom = x0 + (location % 2) * width, y0 + (location // 2) * height
            region = m.PageRegion.objects.create(source_page=source)
            revision = append_region(
                region.pk, expected_number=0, bounds_points=[left, bottom, left + width, bottom + height]
            )
            logicals.append(
                m.LogicalPageRevision.objects.create(
                    logical_page=m.LogicalPage.objects.create(),
                    number=1,
                    region_revision=revision,
                )
            )
            regions.append(region)
        edition = m.ContentEdition.objects.create(arrangement=arrangement, part=part)
        proposal = propose_content(
            edition.pk, expected_number=0, inputs=[(logical.pk, files[index].pk) for logical in logicals]
        )
        with pytest.raises(ValidationError):
            confirmed_content_edition(edition.pk)
        inspection = inspect_content(
            proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
        )
        confirm_content(inspection.pk, actor=actor)
        editions.append(edition)
        captures.append(capture_content(edition.pk))
    scratch = tmp_path / "private-region-worker"
    scratch.mkdir(mode=0o700)
    for edition in editions:
        output = render_content(edition.pk, processor=Processor(scratch))
        pages = PdfReader(BytesIO(output)).pages
        assert len(pages) == 4
        assert all(float(page.mediabox.width) == pytest.approx(width) for page in pages)
        assert all(float(page.mediabox.height) == pytest.approx(height) for page in pages)
    assert captures[0]["inputs"][0]["bounds_points"] != captures[1]["inputs"][0]["bounds_points"]
    old = regions[0].revisions.get()
    append_region(regions[0].pk, expected_number=1, bounds_points=old.bounds_points)
    from apps.archive.services import ArchiveConflict

    with pytest.raises(ArchiveConflict):
        confirmed_content_edition(editions[0].pk)
    assert len(confirmed_content_edition(editions[1].pk).inputs) == 4
    assert len(load_content(captures[0]).inputs) == 4
    assert all(file.review_state != "CONFIRMED" and not file.assignments.exists() for file in files)
