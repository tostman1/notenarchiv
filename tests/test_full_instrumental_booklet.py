"""Complete synthetic booklet indexing uses reviewed regions, not page equality."""

import hashlib

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import services as s
from apps.archive.content_contract import confirmed_content_edition
from apps.archive.content_geometry_services import append_region
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.catalog.collection_services import add_membership
from apps.catalog.models import Arrangement, Collection, Work
from apps.exports.content_inputs import capture_content, load_content
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import A4, pdf
from tests.test_archive_workflow import receipt
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_all_125_works_have_independently_reviewed_instrumental_locations(edition_inputs, settings):
    actor, _, parts, *_ = edition_inputs
    collection = Collection.objects.create(title="Synthetic complete instrumental booklet")
    arrangements = []
    for position in range(125):
        work = Work.objects.create(title="Repeated synthetic title")
        add_membership(collection.pk, work.pk, position=position, original_song_number=str(position + 1))
        arrangements.append(Arrangement.objects.create(work=work))
    data = pdf(sizes=(A4,) * 32)
    folder = m.SourceFolder.objects.create(relative_path="Synthetic complete booklets")
    files, logicals = [], []
    for instrument in range(2):
        version, _ = s.observe_version(
            folder.pk,
            f"Synthetic complete booklets/{instrument}.pdf",
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            pdf_state="UNCHECKED",
        )
        s.record_validation(
            version.pk,
            expected_revision=version.revision,
            pdf_state="VALID",
            page_info=[PAGE] * 32,
            original_crop_boxes=[PAGE["crop_box"]] * 32,
        )
        file, _ = receipt(s.register_base(version.pk, f"Sammlungen/synthetic-complete-{instrument}.pdf"))
        path = settings.CURATED_DIR / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        files.append(file)
        instrument_logicals = []
        for page in version.pages.order_by("page_index"):
            x0, y0, x1, y1 = page.effective_crop_box
            width, height = (x1 - x0) / 2, (y1 - y0) / 2
            for card in range(4):
                left, bottom = x0 + card % 2 * width, y0 + card // 2 * height
                region = m.PageRegion.objects.create(source_page=page)
                revision = append_region(
                    region.pk, expected_number=0, bounds_points=[left, bottom, left + width, bottom + height]
                )
                instrument_logicals.append(
                    m.LogicalPageRevision.objects.create(
                        logical_page=m.LogicalPage.objects.create(), number=1, region_revision=revision
                    )
                )
        logicals.append(instrument_logicals)
    first_capture = None
    for work_index, arrangement in enumerate(arrangements):
        for instrument, part in enumerate(parts):
            # Reversed instrumental ordering deliberately changes page AND region.
            location = work_index if instrument == 0 else 124 - work_index
            selected = [logicals[instrument][location]]
            if work_index % 25 == 0:
                selected.append(logicals[instrument][location + 1])
            identity = m.ContentEdition.objects.create(arrangement=arrangement, part=part)
            proposal = propose_content(
                identity.pk, expected_number=0, inputs=[(logical.pk, files[instrument].pk) for logical in selected]
            )
            with pytest.raises(ValidationError):
                confirmed_content_edition(identity.pk, verify=False)
            inspection = inspect_content(
                proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
            )
            confirm_content(inspection.pk, actor=actor)
            resolved = confirmed_content_edition(identity.pk, verify=False)
            assert resolved.arrangement_id == arrangement.pk and resolved.part_id == part.pk
            assert [item.logical_page_revision_id for item in resolved.inputs] == [item.pk for item in selected]
            assert resolved.inputs[0].page_index == location // 4
            assert len({item.occurrence_id for item in resolved.inputs}) == len(selected)
            if work_index == 0 and instrument == 0:
                first_capture = capture_content(identity.pk)
    assert collection.memberships.count() == 125
    assert m.ContentEdition.objects.filter(arrangement__in=arrangements).count() == 250
    assert len(load_content(first_capture).inputs) == 2
    assert all(file.review_state != "CONFIRMED" and not file.assignments.exists() for file in files)
