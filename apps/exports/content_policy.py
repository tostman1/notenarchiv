"""Explicit shared-page consequences, retaining all musical occurrence receipts."""

from django.core.exceptions import ValidationError

POLICIES = {"REGIONS", "PAGES_ONCE", "PAGES_REPEAT"}


def plan(entries, policy="REGIONS"):
    if policy not in POLICIES:
        raise ValidationError("Invalid shared-page policy")
    seen, result = set(), []
    for entry in entries:
        pages = []
        for item in entry["content"]["inputs"]:
            key = (item["file_id"], item["source_page_id"])
            emit = policy != "PAGES_ONCE" or key not in seen
            seen.add(key)
            pages.append({"occurrence_id": item["occurrence_id"], "emit": emit})
        result.append(pages)
    return result
