"""One read-only library/completeness engine; candidates never become assignments."""

from django.conf import settings
from django.db.models import Exists, F, OuterRef, Q
from django.utils.translation import gettext_lazy as _

from apps.archive import models as m
from apps.catalog.models import Arrangement, ExpectedPart, normalized
from core import preview

LABELS = {
    "UNKNOWN": _("Erwartung unbekannt"),
    "NOT_REQUIRED": _("Nicht erforderlich"),
    "AVAILABLE": _("Bestätigt verfügbar laut Archivstatus"),
    "UNREVIEWED": _("Ungeprüft"),
    "MISSING": _("Fehlend"),
    "COMPLETE": _("Erforderliche Stimmen bestätigt"),
    "INCOMPLETE": _("Erforderliche Stimmen fehlen oder sind ungeprüft"),
}


def pending_files():
    return m.ArchiveFile.objects.filter(review_state__in=["PENDING", "REJECTED", "APPROVAL_REQUESTED"])


def _part_filter(values, prefix=""):
    conditions = Q()
    if values.get("instrument"):
        conditions &= Q(**{prefix + "part__instrument_id": values["instrument"].pk})
    if values.get("part"):
        conditions &= Q(**{prefix + "part_id": values["part"].pk})
    return conditions


def search(values):
    query = Arrangement.objects.filter(active=True, work__active=True).select_related("work")
    if values.get("q"):
        text = normalized(values["q"])
        query = query.filter(
            Q(work__title_key__contains=text) | Q(work__aliases__alias_key__contains=text, work__aliases__active=True)
        ).distinct()
    if values.get("arrangement"):
        query = query.filter(pk=values["arrangement"].pk)
    confirmed = m.ArchiveAssignment.objects.usable().filter(archive_file__arrangement_id=OuterRef("pk"))
    # Current controlled proposals and immutable recognition candidates are distinct.
    pending = pending_files().filter(
        Q(current_proposal__arrangement_id=OuterRef("pk"))
        | Q(current_proposal__isnull=True, candidates__proposed_arrangement_id=OuterRef("pk"))
    )
    if values.get("instrument") or values.get("part"):
        filtered_confirmed = confirmed.filter(_part_filter(values))
        pending = pending.filter(
            Q(current_proposal__parts__in=m.ProposalPart.objects.filter(_part_filter(values)))
            | Q(
                current_proposal__isnull=True,
                candidates__parts__in=m.CandidatePart.objects.filter(_part_filter(values)),
            )
        )
        expectations = ExpectedPart.objects.filter(arrangement_id=OuterRef("pk")).filter(_part_filter(values))
        query = query.annotate(
            has_matching_confirmed=Exists(filtered_confirmed),
            has_matching_pending=Exists(pending),
            has_matching_expected=Exists(expectations),
        ).filter(Q(has_matching_confirmed=True) | Q(has_matching_pending=True) | Q(has_matching_expected=True))
    else:
        filtered_confirmed = confirmed
    query = query.annotate(
        has_confirmed=Exists(filtered_confirmed),
        has_pending=Exists(pending),
        has_uncertain=Exists(pending.filter(candidate_state__in=["UNKNOWN", "CONFLICT"])),
    )
    if values.get("review"):
        query = query.filter(
            **{
                {"CONFIRMED": "has_confirmed", "PENDING": "has_pending", "UNCERTAIN": "has_uncertain"}[
                    values["review"]
                ]: True
            }
        )
    expected = ExpectedPart.objects.filter(arrangement_id=OuterRef("pk"), required=True)
    exact_confirmed = m.ArchiveAssignment.objects.usable().filter(
        archive_file__arrangement_id=OuterRef("arrangement_id"), part_id=OuterRef("part_id")
    )
    missing = expected.annotate(available=Exists(exact_confirmed)).filter(available=False)
    query = query.annotate(has_required=Exists(expected), has_missing=Exists(missing))
    completeness = values.get("completeness")
    if completeness == "UNKNOWN":
        query = query.filter(expectations_defined=False)
    elif completeness == "NOT_REQUIRED":
        query = query.filter(expectations_defined=True, has_required=False)
    elif completeness == "COMPLETE":
        query = query.filter(expectations_defined=True, has_required=True, has_missing=False)
    elif completeness == "INCOMPLETE":
        query = query.filter(expectations_defined=True, has_missing=True)
    return query.order_by("work__title_key", "arranger_key", "edition_key", "pk")


def completeness(arrangement):
    if not arrangement.expectations_defined:
        return "UNKNOWN"
    if not arrangement.has_required:
        return "NOT_REQUIRED"
    return "INCOMPLETE" if arrangement.has_missing else "COMPLETE"


def part_rows(arrangement):
    expected = {entry.part_id: entry for entry in arrangement.expected_parts.select_related("part__instrument")}
    confirmed = list(
        m.ArchiveAssignment.objects.usable()
        .filter(archive_file__arrangement=arrangement)
        .select_related("part__instrument", "archive_file")
    )
    pending = pending_files().filter(
        Q(current_proposal__arrangement=arrangement)
        | Q(current_proposal__isnull=True, candidates__proposed_arrangement=arrangement)
    )
    proposals = list(
        m.ProposalPart.objects.filter(
            proposal__archive_file__in=pending,
            proposal__arrangement=arrangement,
            proposal_id=F("proposal__archive_file__current_proposal_id"),
        ).select_related("part__instrument")
    )
    candidates = list(
        m.CandidatePart.objects.filter(
            candidate__archive_file__in=pending,
            candidate__proposed_arrangement=arrangement,
            candidate__archive_file__current_proposal__isnull=True,
        ).select_related("part__instrument")
    )
    parts = {entry.part_id: entry.part for entry in [*expected.values(), *confirmed, *proposals, *candidates]}
    available = {entry.part_id for entry in confirmed}
    unreviewed = {entry.part_id for entry in [*proposals, *candidates]}
    rows = []
    for identifier, part in parts.items():
        expectation = expected.get(identifier)
        expectation_state = (
            "UNKNOWN"
            if not arrangement.expectations_defined
            else ("REQUIRED" if expectation and expectation.required else "NOT_REQUIRED")
        )
        material = "AVAILABLE" if identifier in available else "UNREVIEWED" if identifier in unreviewed else "MISSING"
        rows.append(
            {
                "part": part,
                "expectation": expectation_state,
                "state": material,
                "label": LABELS[material],
                "optional": bool(expectation and not expectation.required),
                "confirmed_count": sum(entry.part_id == identifier for entry in confirmed),
                "pending_count": sum(entry.part_id == identifier for entry in [*proposals, *candidates]),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["part"].instrument.name_key,
            row["part"].instrument.transposition_key,
            row["part"].instrument.clef,
            row["part"].code_key,
        ),
    )


def verify_file(file):
    """Read-only actual-byte verification of one eligible displayed edition."""
    if not m.ArchiveFile.objects.usable().filter(pk=file.pk).exists():
        return False
    try:
        preview.snapshot(
            settings.CURATED_DIR if file.root_kind == "CLEAN" else settings.PROCESSED_DIR,
            file.relative_path,
            maximum=min(settings.PDF_MAX_BYTES, 104_857_600),
            sha256=file.sha256,
            size=file.byte_size,
        )
    except (ValueError, OSError):
        return False
    return True
