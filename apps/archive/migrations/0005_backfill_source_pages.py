"""Populate additive page identities from the existing validated PDF metadata."""

import hashlib
import json
from uuid import UUID, uuid5

from django.db import migrations, transaction

PAGE_NAMESPACE = UUID("7d590e59-ff59-434b-8e52-9ee66a10eedd")


def _backfill_version(pages, version):
    # Freeze the legacy conversion independently of future geometry code.
    existing = {page.page_index: page for page in pages.filter(source_version_id=version.pk)}
    missing = []
    for index, recorded in enumerate(version.page_info):
        fields = {
            "media_box": recorded["media_box"],
            "effective_crop_box": recorded["crop_box"],
            "rotation": recorded["rotation"],
            "user_unit": recorded["user_unit"],
        }
        signature = {
            **fields,
            "schema": "pdf-page-legacy-effective-v1",
            "original_crop_box": None,
            "user_unit": float(fields["user_unit"]),
        }
        for field in ("media_box", "effective_crop_box"):
            signature[field] = [float(value) or 0.0 for value in fields[field]]
        encoded = json.dumps(signature, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fingerprint = hashlib.sha256(encoded.encode("ascii")).hexdigest()
        page = existing.pop(index, None)
        if page is None:
            missing.append(
                pages.model(
                    id=uuid5(PAGE_NAMESPACE, f"{version.pk}:{index}"),
                    source_version_id=version.pk,
                    page_index=index,
                    geometry_fingerprint=fingerprint,
                    **fields,
                )
            )
        elif any(getattr(page, name) != value for name, value in fields.items()) or (
            page.original_crop_box is None and page.geometry_fingerprint != fingerprint
        ):
            raise ValueError("Existing source page does not match legacy validation.")
    if existing:
        raise ValueError("Existing source page index is outside legacy validation.")
    pages.bulk_create(missing, batch_size=100)


def backfill(apps, schema_editor):
    using = schema_editor.connection.alias
    pages = apps.get_model("archive", "SourcePage").objects.using(using)
    versions = apps.get_model("archive", "SourceVersion").objects.using(using)
    versions = versions.filter(pdf_state="VALID").only("id", "page_info").order_by("pk")
    last = None
    while True:
        batch = list((versions if last is None else versions.filter(pk__gt=last))[:16])
        if not batch:
            break
        for version in batch:
            with transaction.atomic(using=using):
                _backfill_version(pages, version)
        last = batch[-1].pk


class Migration(migrations.Migration):
    atomic = False
    dependencies = [("archive", "0004_sourcepage")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
