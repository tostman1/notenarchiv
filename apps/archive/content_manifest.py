"""Bounded canonical manifests; occurrence identity is never inferred from location."""

import hashlib
import json
from uuid import UUID

from django.core.exceptions import ValidationError


def manifest_fingerprint(manifest):
    if not isinstance(manifest, list) or not 1 <= len(manifest) <= 1000:
        raise ValidationError("Content manifest requires between one and 1000 explicit occurrences.")
    seen = set()
    fields = {"occurrence_id", "logical_page_revision_id", "archive_file_id", "file_revision"}
    for item in manifest:
        if not isinstance(item, dict) or set(item) != fields:
            raise ValidationError("Invalid content manifest schema.")
        for field in fields - {"file_revision"}:
            try:
                if str(UUID(item[field])) != item[field]:
                    raise ValueError
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValidationError("Manifest identities must be canonical UUIDs.") from exc
        if item["occurrence_id"] in seen or type(item["file_revision"]) is not int or item["file_revision"] < 1:
            raise ValidationError("Occurrence identities must be unique and publication revisions positive.")
        seen.add(item["occurrence_id"])
    payload = json.dumps({"schema": "content-sequence-v1", "inputs": manifest}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
